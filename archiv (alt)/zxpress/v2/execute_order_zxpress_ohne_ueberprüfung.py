import os
import argparse
import yaml
from archive.zxpress import scrape_issue_articles
from archive.zxpress.v1 import build_indexes, fill_missing, scrape_catalog, scrape_magazine
from archive.zxpress import safe_filename

def main():
    parser = argparse.ArgumentParser(description="ZXpress Scraper")
    parser.add_argument("--config", default="config/zxpress.yaml", help="Pfad zur YAML-Konfig")
    parser.add_argument("--mode", choices=["seeds", "all"], default="seeds", help="Nur Seeds aus YAML oder kompletten Katalog scrapen")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_root = cfg["data_root"]
    os.makedirs(os.path.join(data_root, "magazines"), exist_ok=True)

    if args.mode == "all":
        magazines = scrape_catalog(args.config)
    else:
        magazines = []
        for s in cfg.get("seeds", []):
            magazines.append(type("M", (), {
                "id": s["magazine_id"],
                "name": s["magazine_name"],
                "issue_url": s["issue_url"],
                "city": None, "country": None, "form": None
            }))

    # Pro Magazin: Ausgaben parsen, Artikel scrapen, Indexe bauen, Lücken füllen
    for m in magazines:
        mag_dir = os.path.join(data_root, "magazines", safe_filename(m.name, 80))
        print(f"\n===  Magazin: {m.name} (id={m.id}) ===") # ZUM TESTEN nur #Z80 Magazin nehmen, dann --mode all
        issue_root = scrape_magazine(args.config, m.name, m.issue_url, m.id, data_root)

        form = getattr(m, "form", None)
        city = getattr(m, "city", None)
        country = getattr(m, "country", None)

        for issue_id in sorted(os.listdir(issue_root)):
            issue_dir = os.path.join(issue_root, issue_id)
            if not os.path.isdir(issue_dir):
                continue
            print(f"→ Ausgabe {issue_id}")
            scrape_issue_articles(args.config, issue_dir, m.id, form=form, city=city, country=country)

        build_indexes(mag_dir)
        fill_missing(args.config, mag_dir, m.id, form=form, city=city, country=country)

    print("\n✅ Fertig.")

if __name__ == "__main__":
    main()