import os, json, lucene
from datetime import datetime
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import (
    Document, Field, TextField, StringField,
    StoredField, IntPoint, LongPoint,
    NumericDocValuesField
)
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.store import FSDirectory

CORPUS_ROOT = "/Users/stoia1/Desktop/Website/DigitProject/data/zxpress/magazines"
INDEX_DIR   = "/Users/stoia1/Desktop/Website/DigitProject/index_dir"


def iso_to_epoch(iso_date):
    try:
        dt = datetime.fromisoformat(iso_date)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None

def build_index():
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    print("✅ JVM bereit – starte Indexaufbau")

    store = FSDirectory.open(Paths.get(INDEX_DIR))
    analyzer = StandardAnalyzer()
    config = IndexWriterConfig(analyzer)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    writer = IndexWriter(store, config)
    article_count = 0

    for mag in os.listdir(CORPUS_ROOT):
        mag_path = os.path.join(CORPUS_ROOT, mag)
        if not os.path.isdir(mag_path):
            continue

        mag_meta_path = os.path.join(mag_path, "magazine.json")
        if not os.path.exists(mag_meta_path):
            continue
        with open(mag_meta_path, "r", encoding="utf-8") as f:
            mag_meta = json.load(f)

        magazine_name = mag_meta.get("magazine_name")
        magazine_id   = mag_meta.get("magazine_id")
        form          = mag_meta.get("form")
        language      = mag_meta.get("language")
        city_country  = mag_meta.get("city_country")

        city, country = None, None
        if city_country and "(" in city_country and ")" in city_country:
            city = city_country.split("(")[0].strip()
            country = city_country.split("(")[1].replace(")", "").strip()

        issues_path = os.path.join(mag_path, "issues")
        if not os.path.isdir(issues_path):
            continue

        for issue in os.listdir(issues_path):
            issue_path = os.path.join(issues_path, issue)
            issue_meta_path = os.path.join(issue_path, "issue.json")
            if not os.path.exists(issue_meta_path):
                continue
            with open(issue_meta_path, "r", encoding="utf-8") as f:
                issue_meta = json.load(f)

            issue_label = issue_meta.get("issue_label")
            issue_date_iso = issue_meta.get("issue_date_iso")
            epoch = iso_to_epoch(issue_date_iso) if issue_date_iso else None

            articles_path = os.path.join(issue_path, "articles")
            if not os.path.isdir(articles_path):
                continue

            for art in os.listdir(articles_path):
                art_path = os.path.join(articles_path, art)
                meta_path = os.path.join(art_path, "meta.json")
                text_path = os.path.join(art_path, "text.txt")

                if not (os.path.exists(meta_path) and os.path.exists(text_path)):
                    continue

                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                with open(text_path, "r", encoding="utf-8") as f:
                    content = f.read()

                doc = Document()
                doc.add(TextField("content", content, Field.Store.YES))
                doc.add(StringField("filename", os.path.basename(text_path), Field.Store.YES))
                if magazine_name:
                    doc.add(StringField("magazine", magazine_name, Field.Store.YES))
                if magazine_id:
                    doc.add(IntPoint("magazine_id", int(magazine_id)))
                    doc.add(StoredField("magazine_id_s", int(magazine_id)))
                if form:
                    doc.add(StringField("form", form, Field.Store.YES))
                if language:
                    doc.add(StringField("language", language, Field.Store.YES))
                if city:
                    doc.add(StringField("city", city, Field.Store.YES))
                if country:
                    doc.add(StringField("country", country, Field.Store.YES))
                if issue_label:
                    doc.add(StringField("issue_label", issue_label, Field.Store.YES))
                if issue_date_iso:
                    doc.add(StringField("issue_date_iso", issue_date_iso, Field.Store.YES))
                if epoch:
                    doc.add(LongPoint("issue_date_epoch_ms", epoch))
                    doc.add(NumericDocValuesField("issue_date_epoch_ms", epoch))
                    doc.add(StoredField("issue_date_epoch_ms", epoch))

                article_id = meta.get("article_id")
                if article_id:
                    doc.add(IntPoint("article_id", int(article_id)))
                    doc.add(StoredField("article_id_s", int(article_id)))
                order = meta.get("order")
                if order is not None:
                    o = int(order)
                    doc.add(IntPoint("order", o))
                    doc.add(NumericDocValuesField("order", o))
                    doc.add(StoredField("order_s", o))

                title = meta.get("title_h1") or meta.get("title_link")
                if title:
                    doc.add(StoredField("title", " ".join(title.split())))
                if meta.get("article_url"):
                    doc.add(StoredField("article_url", meta["article_url"]))
                if meta.get("print_url"):
                    doc.add(StoredField("print_url", meta["print_url"]))

                writer.addDocument(doc)
                article_count += 1
                if article_count % 500 == 0:
                    print(f"… {article_count} Artikel indexiert")

    writer.commit()
    writer.close()
    print(f" Fertig: {article_count} Artikel indexiert → {INDEX_DIR}")


if __name__ == "__main__":
    build_index()