import argparse
import lucene
from java.nio.file import Paths
from org.apache.lucene.store import FSDirectory
from org.apache.lucene.index import DirectoryReader

DEFAULT_FIELDS = [
    "content",
    "title",
    "magazine",
    "form",
    "language",
    "filename",
    "issue_date_iso",
    "article_url",
    "issue_date_epoch_ms",
    "issue_label",
]

def main():
    ap = argparse.ArgumentParser(description="Prüft Feldabdeckung im Lucene-Index.")
    ap.add_argument("--index-dir", required=True, help="Pfad zum Lucene-Index")
    ap.add_argument(
        "--fields",
        nargs="*",
        default=DEFAULT_FIELDS,
        help="Zu prüfende Stored-Felder",
    )
    args = ap.parse_args()

    lucene.initVM(vmargs=["-Djava.awt.headless=true"])
    reader = DirectoryReader.open(FSDirectory.open(Paths.get(args.index_dir)))
    total_docs = reader.numDocs()
    sf = reader.storedFields()

    counts = {f: 0 for f in args.fields}

    for doc_id in range(reader.maxDoc()):
        d = sf.document(doc_id)
        if d is None:
            continue
        for field in args.fields:
            v = d.get(field)
            if v is not None and str(v).strip() != "":
                counts[field] += 1

    print(f"Index: {args.index_dir}")
    print(f"Dokumente: {total_docs}")
    print()
    print("Feldabdeckung:")
    for field in args.fields:
        n = counts[field]
        pct = (n / total_docs * 100) if total_docs else 0.0
        print(f"- {field}: {n}/{total_docs} ({pct:.1f}%)")

    reader.close()
if __name__ == "__main__":
    main()