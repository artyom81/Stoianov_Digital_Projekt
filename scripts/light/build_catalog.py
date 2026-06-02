"""
Liest die JSON-Metadaten (magazine.json, issue.json, articles/*/meta.json)
und erzeugt drei flache CSVs: magazines.csv, issues.csv, articles.csv

Wichtig:
- content_path wird relativ zu --root geschrieben
- dadurch bleibt der Katalog zwischen Rechnern portabel

Aufruf:
python scripts/light/build_catalog.py --root "data_test/zxpress" --out "_catalog"
"""

import argparse
import csv
import json
from pathlib import Path


def load_json_safe(p: Path) -> dict:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def guess_content_path(article_dir: Path, root: Path) -> str | None:
    candidates = ["content.txt", "text.txt", "fulltext.txt"]
    for c in candidates:
        p = article_dir / c
        if p.exists() and p.is_file():
            return str(p.relative_to(root))
    return None


def build_catalog(root: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    mags_csv = out_dir / "magazines.csv"
    issues_csv = out_dir / "issues.csv"
    arts_csv = out_dir / "articles.csv"

    with mags_csv.open("w", newline="", encoding="utf-8") as fm, \
         issues_csv.open("w", newline="", encoding="utf-8") as fi, \
         arts_csv.open("w", newline="", encoding="utf-8") as fa:

        mw = csv.DictWriter(fm, fieldnames=["magazine_id", "magazine_title"])
        iw = csv.DictWriter(fi, fieldnames=[
            "magazine_id", "issue_id", "issue_label", "issue_date_iso", "language", "form"
        ])
        aw = csv.DictWriter(fa, fieldnames=[
            "magazine_id", "issue_id", "article_id", "title", "article_url",
            "issue_date_iso", "language", "form", "filename", "content_path"
        ])

        mw.writeheader()
        iw.writeheader()
        aw.writeheader()

        mags_dir = root / "magazines"
        if not mags_dir.exists():
            raise SystemExit(f"Not found: {mags_dir}")

        for mag_dir in sorted([d for d in mags_dir.iterdir() if d.is_dir()]):
            magazine_id = mag_dir.name
            mag_meta = load_json_safe(mag_dir / "magazine.json")
            magazine_title = mag_meta.get("magazine_name") or mag_meta.get("title") or magazine_id

            mw.writerow({
                "magazine_id": magazine_id,
                "magazine_title": magazine_title
            })

            issues_dir = mag_dir / "issues"
            if not issues_dir.exists():
                continue

            for issue_dir in sorted([d for d in issues_dir.iterdir() if d.is_dir()]):
                issue_id = issue_dir.name
                issue_meta = load_json_safe(issue_dir / "issue.json")

                issue_label = issue_meta.get("label") or issue_meta.get("issue_label") or issue_id
                issue_date_iso = issue_meta.get("issue_date_iso") or issue_meta.get("date") or ""
                language = issue_meta.get("language") or "ru"
                form = issue_meta.get("form") or issue_meta.get("type") or ""

                iw.writerow({
                    "magazine_id": magazine_id,
                    "issue_id": issue_id,
                    "issue_label": issue_label,
                    "issue_date_iso": issue_date_iso,
                    "language": language,
                    "form": form
                })

                arts_dir = issue_dir / "articles"
                if not arts_dir.exists():
                    continue

                for art_dir in sorted([d for d in arts_dir.iterdir() if d.is_dir()]):
                    article_id = art_dir.name
                    meta = load_json_safe(art_dir / "meta.json")

                    title = (
                        meta.get("title_h1")
                        or meta.get("title_link")
                        or meta.get("title")
                        or meta.get("article_title")
                        or article_id
                    )
                    article_url = meta.get("article_url") or meta.get("url") or ""
                    filename = meta.get("filename") or ""
                    content_path = guess_content_path(art_dir, root)

                    aw.writerow({
                        "magazine_id": magazine_id,
                        "issue_id": issue_id,
                        "article_id": article_id,
                        "title": title,
                        "article_url": article_url,
                        "issue_date_iso": issue_date_iso,
                        "language": language,
                        "form": form,
                        "filename": filename,
                        "content_path": content_path or ""
                    })

    print("OK ✅  Katalog gebaut:")
    print(f"  {mags_csv}")
    print(f"  {issues_csv}")
    print(f"  {arts_csv}")


def main():
    ap = argparse.ArgumentParser(description="Baut flache CSV-Kataloge aus ZXPress-JSONs.")
    ap.add_argument("--root", required=True, help="Root der Sammlung, z.B. data/zxpress oder data_test/zxpress")
    ap.add_argument("--out", default="_catalog", help="Zielordner für CSVs (default: _catalog)")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    build_catalog(root, out)


if __name__ == "__main__":
    main()