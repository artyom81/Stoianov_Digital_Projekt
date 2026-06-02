import os, lucene, atexit, re, yaml, traceback
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, Response
from java.nio.file import Paths
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader, Term
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.search import IndexSearcher, BooleanQuery, BooleanClause, TermQuery, MatchAllDocsQuery
from org.apache.lucene.queryparser.classic import QueryParser, MultiFieldQueryParser
from org.apache.lucene.document import LongPoint
from org.apache.lucene.analysis.tokenattributes import CharTermAttribute
from java.io import StringReader
import re as _re

INDEX_DIR   = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"
CONFIG_PATH = "/Users/stoia1/Desktop/Website/DigitProject/config/zxpress.yaml"

import sys as _sys
from pathlib import Path as _Path
_PROJ_ROOT = str(_Path(__file__).resolve().parents[2])
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)

try:
    from .fcs_xml import fcs_searchretrieve_xml, fcs_explain_xml, sru_diagnostic_xml
except Exception:
    try:
        from scripts.FCS.fcs_xml import fcs_searchretrieve_xml, fcs_explain_xml, sru_diagnostic_xml
    except Exception:
        from fcs_xml import fcs_searchretrieve_xml, fcs_explain_xml, sru_diagnostic_xml

try:
    from scripts.FCS.cql_parser import cql_to_lucene
except Exception:
    def cql_to_lucene(q: str) -> str:
        return q or ""
from scripts.TextSearch.Searcher import kwic, _normalize_kwic_term, _fallback_snippet


def _req_sru_version():
    """
    SRU-Version aus Query übernehmen (version oder sruVersion).
    auch Formen wie VERSION_2_0, SRU_VERSION_2_0, 2, 2.0, 1.2 …
    Default: 2.0
    """
    raw = (request.args.get("version")
           or request.args.get("sruVersion")
           or request.args.get("sruversion")
           or "").strip()
    if not raw:
        return "2.0"

    up = raw.upper().strip().replace("-", "_")
    if up in ("VERSION_2_0", "SRU_VERSION_2_0", "V2", "SRU2", "2", "2.0"):
        return "2.0"
    if up in ("VERSION_1_2", "SRU_VERSION_1_2", "V1_2", "1.2", "1"):
        return "1.2"

    cleaned = _re.sub(r"[^0-9.]", "", up)
    if cleaned.startswith("2"):
        return "2.0"
    if cleaned.startswith("1.2") or cleaned == "12":
        return "1.2"
    return "2.0"

def ensure_sru_20(version: str):
    if version != "2.0":
        xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<sru:diagnostics xmlns:sru="http://www.loc.gov/zing/srw/">
  <sru:diagnostic>
    <sru:uri>info:srw/diagnostic/1/6</sru:uri>
    <sru:message>Unsupported version</sru:message>
    <sru:details>{version}</sru:details>
  </sru:diagnostic>
</sru:diagnostics>"""
        resp = Response(xml, status=200, mimetype="application/sru+xml")
        resp.headers["Content-Type"] = "application/sru+xml;version=VERSION_2_0; charset=utf-8"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-SRU-Version"] = "VERSION_2_0"
        return resp
    return None

app = Flask(__name__)
_LUCENE_READY = False

app.explain_meta = {
    "server_info": {
        "base_url": os.environ.get("FCS_BASEURL", "https://starts-human-mph-beyond.trycloudflare.com/sru"),
        "title": "DigitProject FCS Endpoint",
        "description": "FCS 2.0 Test Endpoint (local)",
        "contact": "mailto:you@example.com",
        "version": "2.0",
    },
    "fcs_capabilities": {
        "srwVersion": "2.0",
        "fcsVersion": "2.0",
        "operations": ["explain", "searchRetrieve", "scan"],
        "maximumRecords": 50,
        "supports": {
            "queryLanguages": ["cqlfcs-2.0", "cql"],
            "dataViews": ["hits:snippet", "fcs:resource"]
        },
    },
    "indexes": [
        {"name": "cql.serverChoice", "title": "Default"},
        {"name": "dc.title", "title": "Title"},
        {"name": "text", "title": "Fulltext"},
    ],
    "resources": [
        {"pid": "corpus-1", "title": "Sample Corpus", "languages": ["de", "en"]}
    ],
}

def _load_yaml(path: str | Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _ensure_lucene():
    global _LUCENE_READY
    if not _LUCENE_READY:
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
        _LUCENE_READY = True
    lucene.getVMEnv().attachCurrentThread()
    if not hasattr(app, "reader"):
        app.reader = DirectoryReader.open(FSDirectory.open(Paths.get(INDEX_DIR)))
        app.searcher = IndexSearcher(app.reader)
    if not hasattr(app, "profile"):
        app.profile = _load_yaml(CONFIG_PATH)

@app.route("/health", methods=["GET"])
def health():
    try:
        _ensure_lucene()
        app.searcher.search(MatchAllDocsQuery(), 1)
        return {"status": "ok"}, 200
    except Exception as e:
        return {"status": "error", "detail": str(e)}, 500

@app.route("/sru", methods=["HEAD"])
def sru_head():
    resp = Response(status=200)  # HEAD: leerer Body
    resp.headers["Content-Type"] = "application/sru+xml;version=VERSION_2_0; charset=utf-8"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-SRU-Version"] = "VERSION_2_0"
    return resp

def _safe_parse(parser, qtext: str):
    if not qtext or not qtext.strip():
        return MatchAllDocsQuery()
    try:
        return parser.parse(qtext)
    except Exception:
        try:
            esc = QueryParser.escape(qtext)
            return parser.parse(esc)
        except Exception:
            return MatchAllDocsQuery()

def _analyze_terms(text: str, analyzer) -> list[str]:
    if not text:
        return []
    ts = analyzer.tokenStream("content", StringReader(text))
    term_attr = ts.addAttribute(CharTermAttribute.class_)
    ts.reset()
    terms = []
    while ts.incrementToken():
        terms.append(term_attr.toString())
    ts.end()
    ts.close()
    return terms

def _fallback_boolean_query(terms: list[str]) -> BooleanQuery:
    b = BooleanQuery.Builder()
    for t in terms:
        sub = BooleanQuery.Builder()
        sub.add(TermQuery(Term("content", t)), BooleanClause.Occur.SHOULD)
        sub.add(TermQuery(Term("title",   t)), BooleanClause.Occur.SHOULD)
        b.add(sub.build(), BooleanClause.Occur.MUST)
    return b.build() if terms else MatchAllDocsQuery()

def _split_left_match_right(snippet: str, needle: str):
    if not snippet or not needle:
        return ("", snippet or "", "")
    s_l = snippet.lower()
    n_l = needle.lower()
    i = s_l.find(n_l)
    if i == -1:
        return ("", snippet, "")
    j = i + len(needle)
    return (snippet[:i], snippet[i:j], snippet[j:])

def iso_to_epoch_ms(date_iso):
    if not date_iso:
        return None
    parts = date_iso.split("-")
    if len(parts) == 1:
        date_iso = f"{parts[0]}-01-01"
    elif len(parts) == 2:
        date_iso = f"{parts[0]}-{parts[1]}-01"
    dt = datetime.fromisoformat(date_iso).replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def build_query(qtext, magazine=None, form=None, lang=None, year_from=None, year_to=None):
    analyzer = StandardAnalyzer()
    if qtext and qtext.strip():
        fields = ["content", "title"]
        parser = MultiFieldQueryParser(fields, analyzer)
        parser.setDefaultOperator(QueryParser.Operator.AND)
        q = _safe_parse(parser, qtext)
        if isinstance(q, MatchAllDocsQuery):
            terms = _analyze_terms(qtext, analyzer)
            q = _fallback_boolean_query(terms)
    else:
        q = MatchAllDocsQuery()

    b = BooleanQuery.Builder()
    b.add(q, BooleanClause.Occur.MUST)
    if magazine:
        b.add(TermQuery(Term("magazine", magazine)), BooleanClause.Occur.FILTER)
    if form:
        mapping = {"журнал": "Журнал", "газета": "Газета"}
        b.add(TermQuery(Term("form", mapping.get(form.lower(), form))), BooleanClause.Occur.FILTER)
    if lang:
        lang_norm = (lang or "").strip().lower()
        lang_map = {
            "ru": ["ru", "ru-ru", "russian", "русский"],
            "en": ["en", "en-us", "english"],
            "de": ["de", "de-de", "german", "deutsch"],
        }
        candidates = lang_map.get(lang_norm, [lang_norm])
        sub = BooleanQuery.Builder()
        for val in candidates:
            sub.add(TermQuery(Term("language", val)), BooleanClause.Occur.SHOULD)
            sub.add(TermQuery(Term("lang",     val)), BooleanClause.Occur.SHOULD)
        b.add(sub.build(), BooleanClause.Occur.FILTER)
    if year_from or year_to:
        start = iso_to_epoch_ms(f"{year_from}-01-01") if year_from else -2**63
        end   = iso_to_epoch_ms(f"{year_to}-12-31")   if year_to   else  2**63 - 1
        b.add(LongPoint.newRangeQuery("issue_date_epoch_ms", start, end), BooleanClause.Occur.FILTER)

    return b.build()

def _xml_response(xml_str: str, sru_ver: str, status: int = 200) -> Response:
    resp = Response(xml_str, status=status, mimetype="application/sru+xml")
    ver_token = (sru_ver or "2.0").upper().replace("-", "_")
    if ver_token in ("2.0", "2", "V2", "SRU2", "SRU_VERSION_2_0"):
        ver_token = "VERSION_2_0"

    resp.headers["Content-Type"] = f"application/sru+xml;version={ver_token}; charset=utf-8"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-SRU-Version"] = ver_token
    return resp

@app.route("/sru", methods=["GET"])
def sru_search():
    _ensure_lucene()
    sru_ver = "2.0"
    try:
        op_raw = request.args.get("operation", "searchRetrieve")
        op = (op_raw or "").strip().lower()
        sru_ver = _req_sru_version()

        x_fcs_param = request.args.get("x-fcs-endpoint-description", None)
        if x_fcs_param is not None:
            val = x_fcs_param.strip().lower() if isinstance(x_fcs_param, str) else ""
            if val in ("", "true", "1", "yes"):
                probe_ver = _req_sru_version() or "2.0"
                xml = fcs_explain_xml(app.explain_meta, version=probe_ver)
                return _xml_response(xml, probe_ver, 200)

        diag_resp = ensure_sru_20(sru_ver)
        if diag_resp:
            return diag_resp

        app.logger.info("SRU %s called: args=%s -> responding version=%s", op_raw, dict(request.args), sru_ver)

        if op == "explain":
            xml = fcs_explain_xml(app.explain_meta, version=sru_ver)
            return _xml_response(xml, sru_ver, 200)

        if op != "searchretrieve":
            diag = sru_diagnostic_xml(
                code="7",
                message="Unsupported operation",
                details=f"operation={op_raw}",
                version=sru_ver
            )
            return _xml_response(diag, sru_ver, 200)

        raw_query = (request.args.get("query") or "").strip()
        query = raw_query  # für XML-Echo

        m = re.match(r'^cql\.serverChoice\s*=\s*"(?P<q>.*)"$', raw_query)
        if m:
            qtext_raw = m.group("q")
        else:
            qtext_raw = raw_query

        qtext = cql_to_lucene(qtext_raw) if qtext_raw else ""

        magazine    = request.args.get("x-magazine") or None
        form_       = request.args.get("x-form") or None
        language    = request.args.get("x-language", "ru")
        year_from   = request.args.get("x-yearFrom")
        year_to     = request.args.get("x-yearTo")
        kwic_term   = request.args.get("x-kwicTerm")
        try:
            kwic_window = int(request.args.get("x-kwicWindow", 5))
        except (TypeError, ValueError):
            kwic_window = 5

        y_from = int(year_from) if year_from else None
        y_to   = int(year_to)   if year_to   else None

        qry = build_query(
            qtext=qtext,
            magazine=magazine,
            form=form_,
            lang=language,
            year_from=y_from,
            year_to=y_to
        )

        maxre_raw = request.args.get('maximumRecords') or request.args.get('maximumrecords')
        try:
            maxre = int(maxre_raw) if maxre_raw is not None else 10
        except (TypeError, ValueError):
            maxre = 10
        if maxre < 0:
            maxre = 0

        start_raw = request.args.get('startRecord') or request.args.get('startrecord')
        try:
            start = int(start_raw) if start_raw is not None else 1
        except (TypeError, ValueError):
            start = 1
        if start < 1:
            start = 1

        total = app.searcher.count(qry)
        if maxre == 0:
            xml = fcs_searchretrieve_xml(
                records=[],
                total=total,
                start_record=start,
                maximum_records=0,
                query_str=query,
                version=sru_ver,
            )
            return _xml_response(xml, sru_ver, 200)

        fetch = start - 1 + maxre
        if fetch <= 0:
            fetch = maxre
        if fetch > 1000:
            fetch = 1000

        top = app.searcher.search(qry, fetch)
        hits = top.scoreDocs

        slice_from = max(0, start - 1)
        slice_to   = min(len(hits), slice_from + maxre)
        window = hits[slice_from:slice_to]

        raw_kw = (kwic_term or qtext or "").strip()
        term_for_kwic = _normalize_kwic_term(raw_kw)
        records = []
        sf = app.reader.storedFields()
        for sd in window:
            doc = sf.document(sd.doc)
            title = doc.get("title") or doc.get("filename") or f"doc-{sd.doc}"
            mag = doc.get("magazine") or ""
            label = doc.get("issue_label") or ""
            dateiso = doc.get("issue_date_iso") or ""
            url = doc.get("article_url") or doc.get("print_url") or ""

            kwic_list = []
            if term_for_kwic:
                content = doc.get("content") or ""
                snips = kwic(content, term_for_kwic, window=kwic_window, max_snips=3) or []
                if not snips:
                    fb = _fallback_snippet(content, term_for_kwic, chars=180)
                    if fb:
                        snips = [fb]
                for s in snips:
                    left, match, right = _split_left_match_right(s, term_for_kwic)
                    kwic_list.append({"left": left, "match": match, "right": right})
            if not kwic_list:
                kwic_list = [{"left": "", "match": title, "right": ""}]

            records.append({
                "id": url or str(sd.doc),  # hübscher Identifier, wenn vorhanden
                "title": title,
                "magazine": mag,  # ➜ erscheint als <fcs:extent type="magazine">
                "issue_label": label,  # ➜ <fcs:extent type="issue">
                "issue_date_iso": dateiso,  # ➜ <fcs:extent type="date">
                "kwic": kwic_list,
            })

        xml = fcs_searchretrieve_xml(
            records=records,
            total=total,
            start_record=start,
            maximum_records=maxre,
            query_str=query,
            version=sru_ver,
        )
        return _xml_response(xml, sru_ver, 200)

    except Exception:
        err = traceback.format_exc()
        app.logger.error("SRU error: %s", err)
        diag = sru_diagnostic_xml(
            code="1",
            message="System error",
            details=err,
            version=sru_ver,
        )
        return _xml_response(diag, sru_ver, 200)

def _close_lucene():
    try:
        if hasattr(app, "reader"):
            app.reader.close()
    except Exception:
        pass

atexit.register(_close_lucene)

if __name__ == "__main__":
    import os
    mode = os.environ.get("FCS_MODE", "flask").lower()
    if mode == "clarin":
        from scripts.FCS_Server.clarin_app import main as clarin_main
        clarin_main()
    else:
        _ensure_lucene()
        app.run(host="127.0.0.1", port=8088, debug=True, use_reloader=False, threaded=True)

