import os, csv, json, argparse, lucene
from datetime import datetime, timezone
from java.nio.file import Paths

from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import (
    Document, Field, TextField, StringField, StoredField, LongPoint
)
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.store import FSDirectory

def iso_to_epoch_ms(date_iso: str | None):
    #Tolerant zu YYYY, YYYY-MM, YYYY-MM-DD -> epoch millis (UTC)
    if not date_iso:
        return None
    s = date_iso.strip()
    if not s:
        return None
    parts = s.split("-")
    if len(parts) == 1:
        s = f"{parts[0]}-01-01"
    elif len(parts) == 2:
        s = f"{parts[0]}-{parts[1]}-01"
    try:
        dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

# magazine,issue,article mit JSON + text.txt
def _iter_legacy_articles(corpus_root: str):
    for mag in sorted(os.listdir(corpus_root)):
        mag_path = os.path.join(corpus_root, mag)
        if not os.path.isdir(mag_path):
            continue

        mag_meta = {}
        mp = os.path.join(mag_path, "magazine.json")
        if os.path.exists(mp):
            with open(mp, "r", encoding="utf-8") as f:
                mag_meta = json.load(f) or {}

        magazine_name = mag_meta.get("magazine_name") or mag_meta.get("magazine_id") or mag
        form          = mag_meta.get("form") or ""
        language      = (mag_meta.get("language") or "ru").lower()
        issues_path = os.path.join(mag_path, "issues")
        if not os.path.isdir(issues_path):
            continue

        for issue in sorted(os.listdir(issues_path)):
            issue_path = os.path.join(issues_path, issue)
            if not os.path.isdir(issue_path):
                continue

            issue_meta = {}
            ip = os.path.join(issue_path, "issue.json")
            if os.path.exists(ip):
                with open(ip, "r", encoding="utf-8") as f:
                    issue_meta = json.load(f) or {}

            issue_label    = issue_meta.get("issue_label") or ""
            issue_date_iso = issue_meta.get("issue_date_iso") or ""

            articles_path = os.path.join(issue_path, "articles")
            if not os.path.isdir(articles_path):
                continue

            for art in sorted(os.listdir(articles_path)):
                art_path  = os.path.join(articles_path, art)
                meta_path = os.path.join(art_path, "meta.json")
                txt_path  = os.path.join(art_path, "text.txt")

                if not (os.path.exists(meta_path) and os.path.exists(txt_path)):
                    continue

                meta = {}
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f) or {}

                title = (
                    meta.get("title_h1")
                    or meta.get("title_link")
                    or os.path.basename(txt_path)
                )

                yield {
                    "title":           " ".join((title or "").split()),
                    "filename":        os.path.basename(txt_path),
                    "magazine":        magazine_name,
                    "form":            form,
                    "language":        language,
                    "issue_date_iso":  issue_date_iso,
                    "article_url":     meta.get("article_url") or "",
                    "content_path":    txt_path,
                    "issue_label":     issue_label,
                }

def _read_articles_from_catalog(articles_csv_path: str):
    rows = []
    with open(articles_csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            rows.append(row)
    return rows

def _iter_catalog_articles(articles_csv_path: str, data_root: str | None = None):
    for r in _read_articles_from_catalog(articles_csv_path):
        content_path = (r.get("content_path") or "").strip()

        if content_path and data_root and not os.path.isabs(content_path):
            content_path = os.path.join(data_root, content_path)

        yield {
            "title":           r.get("title") or r.get("filename") or "",
            "filename":        r.get("filename") or r.get("article_id") or "",
            "magazine":        r.get("magazine_id") or "",
            "form":            r.get("form") or "",
            "language":        (r.get("language") or "ru").lower(),
            "issue_date_iso":  r.get("issue_date_iso") or "",
            "article_url":     r.get("article_url") or "",
            "content_path":    content_path,
            "issue_label":     r.get("issue_id") or "",
        }


# Index Aufbau
def build_index(index_dir: str,
                data_root: str | None = None,
                from_catalog: bool = False,
                catalog_articles: str | None = None):

    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    print("✅ JVM bereit – starte Indexaufbau")

    os.makedirs(index_dir, exist_ok=True)
    store    = FSDirectory.open(Paths.get(index_dir))
    analyzer = StandardAnalyzer()
    config   = IndexWriterConfig(analyzer)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    writer   = IndexWriter(store, config)

    if from_catalog:
        if not catalog_articles:
            raise SystemExit("--catalog-articles ist erforderlich mit --from-catalog")
        if not data_root:
            raise SystemExit("--data-root ist erforderlich mit --from-catalog, wenn content_path relativ ist")
        iterator = _iter_catalog_articles(catalog_articles, data_root=data_root)
    else:
        if not data_root:
            raise SystemExit("--data-root ist erforderlich ohne --from-catalog")
        iterator = _iter_legacy_articles(data_root)

    count = 0
    for a in iterator:
        content_path = a.get("content_path")
        if not content_path or not os.path.exists(content_path):
            continue
        with open(content_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Pflichtfelder
        title   = a.get("title") or a.get("filename") or ""
        mag     = a.get("magazine") or ""
        form    = a.get("form") or ""
        lang    = (a.get("language") or "ru").lower()
        dateiso = a.get("issue_date_iso") or ""
        url     = a.get("article_url") or ""
        fname   = a.get("filename") or os.path.basename(content_path)

        # Dokument schreiben, genau die Felder, die Searcher und FCS nutzen
        doc = Document()
        doc.add(TextField("content", content, Field.Store.YES))
        doc.add(TextField("title",   title,   Field.Store.YES))

        doc.add(StringField("magazine", mag, Field.Store.YES))
        doc.add(StringField("form",     form, Field.Store.YES))
        doc.add(StringField("language", lang, Field.Store.YES))

        doc.add(StoredField("filename",       fname))
        if dateiso:
            doc.add(StoredField("issue_date_iso", dateiso))
        if url:
            doc.add(StoredField("article_url", url))

        epoch = iso_to_epoch_ms(dateiso)
        if epoch is not None:
            doc.add(LongPoint("issue_date_epoch_ms", epoch))
            doc.add(StoredField("issue_date_epoch_ms", epoch))

        issue_label = a.get("issue_label")
        if issue_label:
            doc.add(StoredField("issue_label", issue_label))

        writer.addDocument(doc)
        count += 1
        if count % 500 == 0:
            print(f"… {count} Artikel indexiert")

    writer.commit()
    writer.close()
    print(f"✅ Fertig: {count} Artikel indexiert → {index_dir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="DigitProject Indexer")
    ap.add_argument("--index-dir", required=True)
    ap.add_argument("--data-root", help="Legacy JSON/Datei-Baum (magazines/*/issues/*/articles/*)")
    ap.add_argument("--from-catalog", action="store_true",
                    help="Aus CSV-Katalog indexieren (statt Legacy-Baum)")
    ap.add_argument("--catalog-articles", default="_catalog/articles.csv",
                    help="Pfad zu _catalog/articles.csv (bei --from-catalog)")
    args = ap.parse_args()

    build_index(
        index_dir=args.index_dir,
        data_root=args.data_root,
        from_catalog=args.from_catalog,
        catalog_articles=args.catalog_articles,
    )