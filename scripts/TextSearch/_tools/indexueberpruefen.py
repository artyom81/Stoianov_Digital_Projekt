import argparse
import lucene
from java.nio.file import Paths
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.search import IndexSearcher, MatchAllDocsQuery
from org.apache.lucene.queryparser.classic import QueryParser

DEFAULT_QUERIES = [
    "спектрум",
    "covox OR ковокс",
    "игра",
]
def total_hits_to_int(total_hits, fallback_len):
    try:
        value_attr = getattr(total_hits, "value", None)
        if callable(value_attr):
            return value_attr()
        if value_attr is not None:
            return value_attr
    except Exception:
        pass
    return fallback_len

def run_query(searcher, analyzer, qtext, limit=3):
    qp_content = QueryParser("content", analyzer)
    qp_title = QueryParser("title", analyzer)

    qc = qp_content.parse(qtext)
    qt = qp_title.parse(qtext)

    hits_c = searcher.search(qc, limit)
    hits_t = searcher.search(qt, limit)
    total_c = total_hits_to_int(hits_c.totalHits, len(hits_c.scoreDocs))
    total_t = total_hits_to_int(hits_t.totalHits, len(hits_t.scoreDocs))

    return total_c, total_t

def main():
    ap = argparse.ArgumentParser(description="Basistest für Lucene-Index.")
    ap.add_argument("--index-dir", required=True, help="Pfad zum Lucene-Index")
    ap.add_argument("--limit", type=int, default=3, help="Anzahl Testtreffer pro Query")
    ap.add_argument(
        "--queries",
        nargs="*",
        default=DEFAULT_QUERIES,
        help="Testqueries",
    )
    args = ap.parse_args()

    lucene.initVM(vmargs=["-Djava.awt.headless=true"])
    reader = DirectoryReader.open(FSDirectory.open(Paths.get(args.index_dir)))
    searcher = IndexSearcher(reader)
    analyzer = StandardAnalyzer()

    print(f"Index: {args.index_dir}")
    print(f"numDocs: {reader.numDocs()}")
    print(f"maxDoc : {reader.maxDoc()}")

    all_hits = searcher.search(MatchAllDocsQuery(), 1)
    total_all = total_hits_to_int(all_hits.totalHits, len(all_hits.scoreDocs))
    print(f"MatchAllDocsQuery: {total_all} Treffer")
    print()
    print("Query-Tests:")
    ok = True
    for q in args.queries:
        try:
            total_c, total_t = run_query(searcher, analyzer, q, limit=args.limit)
            print(f"- {q!r}: content={total_c}, title={total_t}")
        except Exception as e:
            ok = False
            print(f"- {q!r}: FEHLER -> {e}")

    print()
    print("Gesamtstatus:", "OK" if ok else "FEHLER")

    reader.close()

if __name__ == "__main__":
    main()