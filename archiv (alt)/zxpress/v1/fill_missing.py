import os
import json
from archive.zxpress.v1.scrape_articles import scrape_issue_articles

def fill_missing(cfg_path: str, mag_dir: str, magazine_id: int, form: str = None, city: str = None, country: str = None):
    idx_articles = os.path.join(mag_dir, "indexes", "articles.json")
    if not os.path.exists(idx_articles):
        print("⚠️ Kein articles.json gefunden – bitte zuerst build_indexes laufen lassen.")
        return

    with open(idx_articles, "r", encoding="utf-8") as f:
        items = json.load(f)

    issue_dirs = {}
    for row in items:
        if not row.get("has_text") or not row.get("has_meta") or row.get("status") != "ok":
            issue_id = row["issue_id"]
            issue_dir = os.path.join(mag_dir, "issues", issue_id)
            issue_dirs[issue_id] = issue_dir

    if not issue_dirs:
        print(" Keine Lücken – alles vollständig.")
        return

    print(f" Fülle {len(issue_dirs)} Ausgabe(n) nach …")
    for issue_id, issue_dir in issue_dirs.items():
        scrape_issue_articles(cfg_path, issue_dir, magazine_id, form=form, city=city, country=country)