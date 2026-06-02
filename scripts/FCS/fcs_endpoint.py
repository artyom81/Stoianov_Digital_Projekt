import os
import re
import atexit
import yaml
import lucene
import traceback
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, Response

from java.nio.file import Paths
from java.io import StringReader
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader, Term
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.search import (
    IndexSearcher,
    BooleanQuery,
    BooleanClause,
    TermQuery,
    MatchAllDocsQuery,
)
from org.apache.lucene.queryparser.classic import QueryParser, MultiFieldQueryParser
from org.apache.lucene.document import LongPoint
from org.apache.lucene.analysis.tokenattributes import CharTermAttribute
import sys as _sys
from pathlib import Path as _Path

_PROJ_ROOT = str(_Path(__file__).resolve().parents[2])
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)

try:
    from .fcs_xml import (
        fcs_searchretrieve_xml,
        fcs_explain_xml,
        sru_explain_xml,
        sru_diagnostic_xml,
    )
except Exception:
    try:
        from scripts.FCS.fcs_xml import (
            fcs_searchretrieve_xml,
            fcs_explain_xml,
            sru_explain_xml,
            sru_diagnostic_xml,
        )
    except Exception:
        from fcs_xml import (
            fcs_searchretrieve_xml,
            fcs_explain_xml,
            sru_explain_xml,
            sru_diagnostic_xml,
        )

try:
    from scripts.FCS.cql_parser import cql_to_lucene
except Exception:
    def cql_to_lucene(q: str) -> str:
        return q or ""

from scripts.TextSearch.Searcher import kwic, _normalize_kwic_term, _fallback_snippet


SRU_VERSION = "2.0"

INDEX_DIR = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"
CONFIG_PATH = "/Users/stoia1/Desktop/Website/DigitProject/config/zxpress.yaml"

app = Flask(__name__)
_LUCENE_READY = False

app.explain_meta = {
    "title": "ZX Press Corpus",
    "description": "SRU/FCS endpoint for the ZX Press corpus",
    "capabilities": ["searchRetrieve", "explain"],
    "supported_data_views": ["hits:kwic-1.0"],
    "collections": [
        {"id": "zx-corpus", "label": "ZX Press Corpus"}
    ],
    "languages": ["ru", "en", "de"],
    "default_language": "ru",
    "fields": [
        {"name": "title", "type": "text", "stored": True, "indexed": True},
        {"name": "content", "type": "text", "stored": True, "indexed": True},
        {"name": "magazine", "type": "keyword", "stored": True, "indexed": True},
        {"name": "form", "type": "keyword", "stored": True, "indexed": True},
        {"name": "language", "type": "keyword", "stored": True, "indexed": True},
        {"name": "issue_date_iso", "type": "keyword", "stored": True, "indexed": True},
        {"name": "issue_date_epoch_ms", "type": "long", "stored": True, "indexed": True},
        {"name": "article_url", "type": "keyword", "stored": True, "indexed": True},
    ],
    "maxPageSize": 50,
    "meta": {
        "rights": "Project prototype endpoint",
        "license": "internal test use",
    },
}

def normalize_sru_version(raw: str | None) -> str:
    if not raw:
        return SRU_VERSION
    v = raw.strip().upper().replace("-", "_")
    if v in {"VERSION_2_0", "SRU_VERSION_2_0", "SRU_2_0", "2", "2.0", "V2", "SRU2"}:
        return "2.0"
    if v in {"VERSION_1_2", "SRU_VERSION_1_2", "1", "1.2", "V1_2"}:
        return "1.2"
    cleaned = re.sub(r"[^0-9.]", "", raw)
    if cleaned.startswith("2"):
        return "2.0"
    if cleaned.startswith("1.2") or cleaned == "12":
        return "1.2"
    return SRU_VERSION

def requested_sru_version() -> str:
    return normalize_sru_version(
        request.args.get("version")
        or request.args.get("sruVersion")
        or request.args.get("sruversion")
    )

def set_sru_headers(resp: Response, version: str = SRU_VERSION) -> Response:
    resp.headers["Content-Type"] = f"application/sru+xml;version={version}; charset=utf-8"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-SRU-Version"] = version
    return resp

def xml_response(xml_bytes: bytes, version: str = SRU_VERSION, status: int = 200) -> Response:
    resp = Response(xml_bytes, status=status, mimetype="application/sru+xml")
    return set_sru_headers(resp, version)

def current_server_info():
    host_header = request.host or "127.0.0.1:8088"
    if ":" in host_header:
        host, port = host_header.rsplit(":", 1)
    else:
        host, port = host_header, "80"
    return host, port, request.path or "/sru"

def ensure_sru_20_or_diagnostic(version: str):
    if version == "2.0":
        return None
    diag = sru_diagnostic_xml(
        code="6",
        message="Unsupported version",
        details=version,
        version=SRU_VERSION,
    )
    return xml_response(diag, SRU_VERSION, 200)

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
        lucene.initVM(vmargs=["-Djava.awt.headless=true"])
        _LUCENE_READY = True

    lucene.getVMEnv().attachCurrentThread()
    if not hasattr(app, "reader"):
        app.reader = DirectoryReader.open(FSDirectory.open(Paths.get(INDEX_DIR)))
        app.searcher = IndexSearcher(app.reader)

    if not hasattr(app, "profile"):
        app.profile = _load_yaml(CONFIG_PATH)

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
        sub.add(TermQuery(Term("title", t)), BooleanClause.Occur.SHOULD)
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

def _title_kwic_if_match(title: str, needle: str):
    if not title or not needle:
        return None
    left, match, right = _split_left_match_right(title, needle)
    if match:
        return {"left": left, "match": match, "right": right}
    return None

def _parse_user_query(raw_query: str) -> dict:
    raw = (raw_query or "").strip()
    if not raw:
        return {
            "mode": "all",
            "field": None,
            "qtext": "",
            "kwic_term": "",
        }

    m = re.match(r'^\s*cql\.serverChoice\s*=\s*"([^"]+)"\s*$', raw, re.I)
    if m:
        term = m.group(1).strip()
        return {
            "mode": "multi",
            "field": None,
            "qtext": term,
            "kwic_term": term,
        }

    m = re.match(r'^\s*title\s*=\s*"([^"]+)"\s*$', raw, re.I)
    if m:
        term = m.group(1).strip()
        return {
            "mode": "field",
            "field": "title",
            "qtext": term,
            "kwic_term": term,
        }

    lucene_q = cql_to_lucene(raw) if raw else ""
    return {
        "mode": "fallback",
        "field": None,
        "qtext": lucene_q,
        "kwic_term": raw,
    }

def build_query(qtext, magazine=None, form=None, lang=None, year_from=None, year_to=None, field=None):
    analyzer = StandardAnalyzer()

    if qtext and qtext.strip():
        if field == "title":
            parser = QueryParser("title", analyzer)
            parser.setDefaultOperator(QueryParser.Operator.AND)
            q = _safe_parse(parser, qtext)

            if isinstance(q, MatchAllDocsQuery):
                terms = _analyze_terms(qtext, analyzer)
                if terms:
                    bq = BooleanQuery.Builder()
                    for t in terms:
                        bq.add(TermQuery(Term("title", t)), BooleanClause.Occur.MUST)
                    q = bq.build()
                else:
                    q = MatchAllDocsQuery()
        else:
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
            sub.add(TermQuery(Term("lang", val)), BooleanClause.Occur.SHOULD)
        b.add(sub.build(), BooleanClause.Occur.FILTER)

    if year_from or year_to:
        start = iso_to_epoch_ms(f"{year_from}-01-01") if year_from else -2**63
        end = iso_to_epoch_ms(f"{year_to}-12-31") if year_to else 2**63 - 1
        b.add(
            LongPoint.newRangeQuery("issue_date_epoch_ms", start, end),
            BooleanClause.Occur.FILTER,
        )

    return b.build()

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
    return set_sru_headers(Response(status=200), SRU_VERSION)

@app.route("/sru", methods=["GET"])
def sru_search():
    _ensure_lucene()
    sru_ver = requested_sru_version()

    try:
        diag_resp = ensure_sru_20_or_diagnostic(sru_ver)
        if diag_resp:
            return diag_resp

        op_raw = request.args.get("operation", "")
        op = (op_raw or "").strip().lower()

        if request.args.get("x-fcs-endpoint-description") is not None:
            xml = fcs_explain_xml(app.explain_meta, version=SRU_VERSION)
            return xml_response(xml, SRU_VERSION, 200)

        if op == "explain":
            host, port, database_path = current_server_info()
            xml = sru_explain_xml(
                app.explain_meta,
                host=host,
                port=port,
                database_path=database_path,
                version=SRU_VERSION,
            )
            return xml_response(xml, SRU_VERSION, 200)

        if op not in {"searchretrieve", ""}:
            diag = sru_diagnostic_xml(
                code="7",
                message="Unsupported operation",
                details=f"operation={op_raw}",
                version=SRU_VERSION,
            )
            return xml_response(diag, SRU_VERSION, 200)

        raw_query = (request.args.get("query") or "").strip()
        query_echo = raw_query
        parsed_query = _parse_user_query(raw_query)
        qtext = parsed_query["qtext"]
        search_field = parsed_query["field"]
        magazine = request.args.get("x-magazine") or None
        form_ = request.args.get("x-form") or None
        language = request.args.get("x-language", "ru")
        year_from = request.args.get("x-yearFrom")
        year_to = request.args.get("x-yearTo")
        kwic_term = request.args.get("x-kwicTerm")

        try:
            kwic_window = int(request.args.get("x-kwicWindow", 5))
        except (TypeError, ValueError):
            kwic_window = 5

        y_from = int(year_from) if year_from else None
        y_to = int(year_to) if year_to else None

        qry = build_query(
            qtext=qtext,
            magazine=magazine,
            form=form_,
            lang=language,
            year_from=y_from,
            year_to=y_to,
            field=search_field,
        )

        maxre_raw = request.args.get("maximumRecords") or request.args.get("maximumrecords")
        try:
            maxre = int(maxre_raw) if maxre_raw is not None else 10
        except (TypeError, ValueError):
            maxre = 10
        if maxre < 0:
            maxre = 0

        start_raw = request.args.get("startRecord") or request.args.get("startrecord")
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
                query_str=query_echo,
                version=SRU_VERSION,
            )
            return xml_response(xml, SRU_VERSION, 200)

        fetch = start - 1 + maxre
        if fetch <= 0:
            fetch = maxre
        if fetch > 1000:
            fetch = 1000

        top = app.searcher.search(qry, fetch)
        hits = top.scoreDocs
        slice_from = max(0, start - 1)
        slice_to = min(len(hits), slice_from + maxre)
        window = hits[slice_from:slice_to]
        raw_kw = (kwic_term or parsed_query["kwic_term"] or "").strip()
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
                    if match:
                        kwic_list.append({"left": left, "match": match, "right": right})

            if not kwic_list:
                title_kwic = _title_kwic_if_match(title, term_for_kwic)
                if title_kwic:
                    kwic_list = [title_kwic]
                else:
                    kwic_list = [{"left": "", "match": "", "right": ""}]

            records.append({
                "id": url or str(sd.doc),
                "title": title,
                "magazine": mag,
                "issue_label": label,
                "issue_date_iso": dateiso,
                "kwic": kwic_list,
            })

        xml = fcs_searchretrieve_xml(
            records=records,
            total=total,
            start_record=start,
            maximum_records=maxre,
            query_str=query_echo,
            version=SRU_VERSION,
        )
        return xml_response(xml, SRU_VERSION, 200)

    except Exception:
        err = traceback.format_exc()
        app.logger.error("SRU error: %s", err)
        diag = sru_diagnostic_xml(
            code="1",
            message="System error",
            details=err,
            version=SRU_VERSION,
        )
        return xml_response(diag, SRU_VERSION, 200)

def _close_lucene():
    try:
        if hasattr(app, "reader"):
            app.reader.close()
    except Exception:
        pass

atexit.register(_close_lucene)

if __name__ == "__main__":
    _ensure_lucene()
    app.run(host="127.0.0.1", port=8088, debug=True, use_reloader=False, threaded=True)