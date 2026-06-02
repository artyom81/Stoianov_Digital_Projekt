import argparse, lucene
from java.nio.file import Paths
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader, LeafReaderContext
from org.apache.lucene.search import IndexSearcher, MatchAllDocsQuery
from org.apache.lucene.document import LongPoint

# Wir importieren build_query direkt aus deinem Endpoint,
# damit Feldnamen/Analyzer 1:1 identisch sind.
from scripts.FCS.fcs_endpoint import build_query

def open_index(index_dir):
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    lucene.getVMEnv().attachCurrentThread()
    reader = DirectoryReader.open(FSDirectory.open(Paths.get(index_dir)))
    searcher = IndexSearcher(reader)
    return reader, searcher

def sample_docs(reader, n=5):
    sf = reader.storedFields()
    maxdoc = reader.maxDoc()
    out = []
    for doc_id in range(min(maxdoc, n)):
        d = sf.document(doc_id)
        if d is None:
            continue
        out.append({
            "doc_id": doc_id,
            "title": d.get("title"),
            "filename": d.get("filename"),
            "magazine": d.get("magazine"),
            "form": d.get("form"),
            "language": d.get("language") or d.get("lang"),
            "issue_date_iso": d.get("issue_date_iso"),
            "content_len": len(d.get("content")) if d.get("content") else 0,
            "url": d.get("article_url")
        })
    return out

def count_field_presence(reader, fields):
    sf = reader.storedFields()
    maxdoc = reader.maxDoc()
    counts = {f: 0 for f in fields}
    for doc_id in range(maxdoc):
        d = sf.document(doc_id)
        if d is None:
            continue
        for f in fields:
            if d.get(f) is not None:
                counts[f] += 1
    return counts, maxdoc

def quick_queries(searcher):
    results = {}
    total_all = searcher.count(MatchAllDocsQuery())
    results["count_all"] = total_all
    try:
        q_any_year = LongPoint.newRangeQuery("issue_date_epoch_ms", -2**63, 2**63 - 1)
        results["count_issue_date_range_any"] = searcher.count(q_any_year)
    except Exception as e:
        results["count_issue_date_range_any"] = f"error: {e}"
    try:
        q1 = build_query(qtext="test")
        results["build_query(test)"] = searcher.count(q1)
    except Exception as e:
        results["build_query(test)"] = f"error: {e}"
    try:
        q2 = build_query(qtext="*", lang="ru")
        results["build_query(*, lang=ru)"] = searcher.count(q2)
    except Exception as e:
        results["build_query(*, lang=ru)"] = f"error: {e}"

    try:
        q3 = build_query(qtext="*", year_from=1990, year_to=2000)
        results["build_query(*, 1990-2000)"] = searcher.count(q3)
    except Exception as e:
        results["build_query(*, 1990-2000)"] = f"error: {e}"

    return results

def main():
    ap = argparse.ArgumentParser(description="DigitProject: Index-Feldcheck")
    ap.add_argument("--index", required=True, help="Pfad zum index_dir")
    ap.add_argument("--sample", type=int, default=5, help="Wie viele Dokumente beispielhaft zeigen")
    args = ap.parse_args()

    reader, searcher = open_index(args.index)
    print("\n BASIS ")
    print(f"maxDoc      : {reader.maxDoc()}")
    print(f"numDocs     : {reader.numDocs()}")

    print("\n FELD-ANWESENHEIT (Stored Fields) ")
    fields = [
        "title", "filename", "magazine", "form",
        "language", "lang", "issue_date_iso",
        "content", "article_url"
    ]
    counts, maxdoc = count_field_presence(reader, fields)
    for f in fields:
        print(f"{f:16s}: {counts[f]:6d} / {maxdoc}")

    print("\n BEISPIEL-DOKUMENTE ")
    for doc in sample_docs(reader, n=args.sample):
        print(f"- doc_id={doc['doc_id']}, title={doc['title']!r}, magazine={doc['magazine']!r}, "
              f"form={doc['form']!r}, lang={doc['language']!r}, date={doc['issue_date_iso']!r}, "
              f"content_len={doc['content_len']}, url={doc['url']!r}")

    print("\n SCHNELLTESTS QUERIES ")
    qr = quick_queries(searcher)
    for k, v in qr.items():
        print(f"{k:28s}: {v}")
    reader.close()

if __name__ == "__main__":
    main()