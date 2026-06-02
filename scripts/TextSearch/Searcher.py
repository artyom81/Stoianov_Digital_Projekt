import argparse
import lucene
from datetime import datetime, timezone
from java.nio.file import Paths
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.search import (
    IndexSearcher,
    BooleanQuery,
    BooleanClause,
    TermQuery,
    MatchAllDocsQuery,
)
from org.apache.lucene.index import Term
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.document import LongPoint

DEFAULT_INDEX_DIR = "index_dir"


def _parse_years(value):
    if not value:
        return None, None
    value = value.strip()
    if "-" in value:
        a, b = value.split("-", 1)
        a = a.strip() or None
        b = b.strip() or None
        return (int(a) if a else None, int(b) if b else None)
    y = int(value)
    return y, y


def _parse_kv_line(line, defaults):
    out = dict(defaults)
    tokens = [t for t in line.strip().split() if t]

    for t in tokens:
        if "=" not in t:
            out["q"] = (out.get("q") or "") + (" " if out.get("q") else "") + t
            continue

        k, v = t.split("=", 1)
        k = k.strip().lower()
        v = v.strip()

        if not v:
            continue

        if k in ("q", "query"):
            out["q"] = v
        elif k in ("mag", "magazine"):
            out["magazine"] = v
        elif k == "form":
            out["form"] = v
        elif k in ("lang", "language"):
            out["lang"] = v
        elif k in ("years", "year", "y"):
            y_from, y_to = _parse_years(v)
            out["year_from"], out["year_to"] = y_from, y_to
        elif k in ("limit", "n", "top"):
            try:
                out["limit"] = int(v)
            except ValueError:
                pass
        elif k in ("kwic", "kw"):
            out["kwic_term"] = v
        elif k in ("win", "kwicwin", "kwic_window"):
            try:
                out["kwic_window"] = int(v)
            except ValueError:
                pass

    return out


def prompt_inputs():
    defaults = dict(
        q="",
        magazine=None,
        form=None,
        lang="ru",
        year_from=None,
        year_to=None,
        limit=10,
        kwic_term=None,
        kwic_window=5,
    )

    print("\n====== Einfache Suche ==============")
    print("Drücken Sie einfach ENTER, um einen Wert zu überspringen.\n")

    q = input("Geben Sie die Suchanfrage ein (leer = alle): ").strip()
    magazine = input("Magazin (exakt, leer = egal): ").strip() or None
    form = input("Form (z.B. Журнал oder Газета, leer = egal): ").strip() or None
    lang = input("Sprache (Standard=ru): ").strip() or "ru"
    years_raw = input("Jahre (z.B. 1996 oder 1995-1997, leer = egal): ").strip()
    limit_raw = input("Max. Treffer (Standard=10): ").strip()
    kwic_term = input("Kontextbegriff (leer = Query verwenden): ").strip() or None
    kwic_win_raw = input("Kontextfenster in Wörtern (Standard=5): ").strip()

    y_from, y_to = (None, None)
    if years_raw:
        try:
            y_from, y_to = _parse_years(years_raw)
        except Exception:
            y_from, y_to = (None, None)

    try:
        limit = int(limit_raw) if limit_raw else defaults["limit"]
    except ValueError:
        limit = defaults["limit"]

    try:
        kwic_window = int(kwic_win_raw) if kwic_win_raw else defaults["kwic_window"]
    except ValueError:
        kwic_window = defaults["kwic_window"]

    return dict(
        q=q,
        magazine=magazine,
        form=form,
        lang=lang or "ru",
        year_from=y_from,
        year_to=y_to,
        limit=limit,
        kwic_term=kwic_term,
        kwic_window=kwic_window,
    )


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


def kwic(txt, term, window=5, max_snips=3):
    words = txt.split()
    term_low = (term or "").lower()
    out = []

    if not term_low:
        return out

    for i, w in enumerate(words):
        if term_low in w.lower():
            s = max(0, i - window)
            e = min(len(words), i + window + 1)
            out.append(" ".join(words[s:e]))
            if len(out) >= max_snips:
                break

    return out


def _normalize_form(value):
    if not value:
        return None

    v = value.strip()
    mapping = {
        "журнал": "Журнал",
        "газета": "Газета",
    }
    return mapping.get(v.lower(), v)


def _normalize_kwic_term(term: str) -> str:
    if not term:
        return ""
    t = term.strip()
    t = t.replace("*", "").replace("?", "")
    return t


def _fallback_snippet(text: str, needle: str, chars: int = 180):
    if not text or not needle:
        return None

    tl = text.lower()
    nl = needle.lower()
    i = tl.find(nl)

    if i == -1:
        return None

    start = max(0, i - chars // 2)
    end = min(len(text), i + len(needle) + chars // 2)
    snippet = text[start:end].replace("\n", " ").replace("\r", " ")
    return snippet.strip()


def _list_magazines(reader):
    mags = set()
    maxdoc = reader.maxDoc()
    sf = reader.storedFields()

    for doc_id in range(maxdoc):
        d = sf.document(doc_id)
        if d is None:
            continue
        m = d.get("magazine")
        if m:
            mags.add(m)

    return sorted(mags)


def _resolve_magazine(reader, user_value):
    if not user_value:
        return None, []

    wanted = user_value.strip()
    if not wanted:
        return None, []

    mags = _list_magazines(reader)
    lower_map = {m.lower(): m for m in mags}

    exact = lower_map.get(wanted.lower())
    if exact:
        return exact, []

    starts = [m for m in mags if m.lower().startswith(wanted.lower())]
    if len(starts) == 1:
        return starts[0], []
    if len(starts) > 1:
        return None, starts[:10]

    contains = [m for m in mags if wanted.lower() in m.lower()]
    if len(contains) == 1:
        return contains[0], []
    if len(contains) > 1:
        return None, contains[:10]

    return None, mags[:10]


def build_query(qtext, magazine, form, lang, year_from, year_to):
    analyzer = StandardAnalyzer()

    if qtext and qtext.strip():
        qp_content = QueryParser("content", analyzer)
        qp_title = QueryParser("title", analyzer)
        qc = qp_content.parse(qtext)
        qt = qp_title.parse(qtext)

        inner = BooleanQuery.Builder()
        inner.add(qc, BooleanClause.Occur.SHOULD)
        inner.add(qt, BooleanClause.Occur.SHOULD)
        q = inner.build()
    else:
        q = MatchAllDocsQuery()

    b = BooleanQuery.Builder()
    b.add(q, BooleanClause.Occur.MUST)

    if magazine:
        b.add(TermQuery(Term("magazine", magazine)), BooleanClause.Occur.FILTER)

    norm_form = _normalize_form(form)
    if norm_form:
        b.add(TermQuery(Term("form", norm_form)), BooleanClause.Occur.FILTER)

    if lang:
        b.add(TermQuery(Term("language", lang)), BooleanClause.Occur.FILTER)

    if year_from or year_to:
        start = iso_to_epoch_ms(f"{year_from}-01-01") if year_from else None
        end = iso_to_epoch_ms(f"{year_to}-12-31") if year_to else None
        if start is None:
            start = -(2**63)
        if end is None:
            end = 2**63 - 1
        b.add(
            LongPoint.newRangeQuery("issue_date_epoch_ms", start, end),
            BooleanClause.Occur.FILTER,
        )

    return b.build()


def _print_hits(hits, reader, limit, kwic_term, kwic_window):
    th = hits.totalHits
    try:
        total = th.value() if callable(getattr(th, "value", None)) else th.value
    except Exception:
        total = len(hits.scoreDocs)

    print(f"Treffer: {total} (zeige bis {limit})")

    term_for_kwic = _normalize_kwic_term(kwic_term)

    for sd in hits.scoreDocs:
        d = reader.storedFields().document(sd.doc)
        title = d.get("title") or d.get("filename")
        mag = d.get("magazine")
        label = d.get("issue_label")
        dateiso = d.get("issue_date_iso")
        url = d.get("article_url")
        txt = d.get("content") or ""

        print(f"\n— {mag} {label} {dateiso} {title}")

        if term_for_kwic:
            snips = kwic(txt, term_for_kwic, window=kwic_window, max_snips=3)
            if snips:
                for s in snips:
                    print(f"   ... {s} ...")
            else:
                fb = _fallback_snippet(txt, term_for_kwic, chars=180)
                if fb:
                    print(f"   … {fb} …  [fallback]")

        if url:
            print(f"   ↪ {url}")


def _run_once(args_map, searcher, reader):
    qtext = args_map.get("q") or ""
    magazine = args_map.get("magazine")
    form = args_map.get("form")
    lang = args_map.get("lang")
    year_from = args_map.get("year_from")
    year_to = args_map.get("year_to")
    limit = int(args_map.get("limit") or 10)
    kwic_term = args_map.get("kwic_term")
    kwic_win = int(args_map.get("kwic_window") or 5)

    resolved_mag, suggestions = _resolve_magazine(reader, magazine)

    if magazine and not resolved_mag:
        print("⚠️ Magazin nicht eindeutig. Meinen Sie eines von:")
        for s in suggestions:
            print(f"   • {s}")
        return

    qry = build_query(qtext, resolved_mag, form, lang, year_from, year_to)
    hits = searcher.search(qry, limit)

    raw_kwic = kwic_term or (qtext if qtext else "")
    _print_hits(hits, reader, limit, raw_kwic, kwic_win)


def main():
    ap = argparse.ArgumentParser(description="ZXpress Volltextsuche (Lucene)")
    ap.add_argument(
        "--index-dir",
        default=DEFAULT_INDEX_DIR,
        help="Pfad zum Lucene-Index (default: index_dir)",
    )
    ap.add_argument(
        "--q",
        default="",
        help="Query (Lucene Syntax, z.B. covox OR ковокс, Wildcards erlaubt)",
    )
    ap.add_argument("--magazine", help="Exakter Magazin-Name (z.B. Spectrofon)")
    ap.add_argument("--form", help="Form (Журнал | Газета)")
    ap.add_argument("--lang", default="ru", help="Sprache (default: ru)")
    ap.add_argument("--year-from", type=int, help="Jahr von")
    ap.add_argument("--year-to", type=int, help="Jahr bis")
    ap.add_argument("--limit", type=int, default=10, help="Max. Treffer")
    ap.add_argument(
        "--kwic-term",
        help="Begriff für KWIC (falls anders als --q; Wildcards werden für Snippets ignoriert)",
    )
    ap.add_argument(
        "--kwic-window",
        type=int,
        default=5,
        help="KWIC Fenster (Wörter)",
    )

    args = ap.parse_args()

    lucene.initVM()
    reader = DirectoryReader.open(FSDirectory.open(Paths.get(args.index_dir)))
    searcher = IndexSearcher(reader)

    if (
        args.q == ""
        and args.magazine is None
        and args.form is None
        and args.lang == "ru"
        and args.year_from is None
        and args.year_to is None
        and args.limit == 10
        and args.kwic_term is None
        and args.kwic_window == 5
    ):
        params = prompt_inputs()
        _run_once(params, searcher, reader)
        reader.close()
        return

    resolved_mag, suggestions = _resolve_magazine(reader, args.magazine)
    if args.magazine and not resolved_mag:
        print("⚠️ Magazin nicht eindeutig. Meinten Sie eines von:")
        for s in suggestions:
            print(f"   • {s}")
        reader.close()
        return

    qry = build_query(
        args.q,
        resolved_mag,
        args.form,
        args.lang,
        args.year_from,
        args.year_to,
    )
    hits = searcher.search(qry, args.limit)

    raw_kwic = args.kwic_term or (args.q if args.q else "")
    _print_hits(hits, reader, args.limit, raw_kwic, args.kwic_window)

    reader.close()


if __name__ == "__main__":
    main()