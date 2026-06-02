import argparse
import subprocess
import sys
import os
import datetime
import time
import re
import requests
from bs4 import BeautifulSoup
import yaml
from urllib.parse import urljoin
import re
import unicodedata

BASE_URL = "https://zxpress.ru"
CATALOG_URL = f"{BASE_URL}/ezines.php"
UA = "ZXPressScraperLight/1.0 (+noncommercial research; contact: you@example.org)"

def sh(cmd: str):
    print(f"\n▶️  {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"⚠️ Fehler bei: {cmd}")
        sys.exit(res.returncode)

def safe_mag_dir_name(name: str, max_len: int = 80) -> str:
    """
    Wandelt Magazinname in einen Verzeichnisnamen um:
      - gefährliche Sonderzeichen entfernen/ersetzen
      - Leerzeichen -> '_'
      - Kürzung auf max_len
    Originalname bleibt in den Metadaten erhalten
    """
    n = unicodedata.normalize("NFKD", name.strip().lstrip("#"))
    # Nur Buchstaben, Zahlen, Unterstrich, Bindestrich
    n = re.sub(r"[^\w\s-]", "_", n, flags=re.UNICODE)
    n = re.sub(r"\s+", "_", n).strip("_")

    if not n:
        n = "mag"
    if len(n) > max_len:
        n = n[:max_len].rstrip("_")

    return n

def run_for_magazine(mag_url: str, out_root: str, retry_missing=False, dry_run=False, validate=False, target_override=None):
    # Scrape (Issue-Listing → magazine.json, issue.json, listing.json)
    mag_name = os.path.basename(out_root)
    sh(
        f'python scripts/light/scrape_issue_listing_light.py '
        f'--mag "{mag_name}" '
        f'--url "{mag_url}" '
        f'--out "{out_root}"'
    )
    # Daten reparieren/normalisieren
    target = target_override or out_root
    sh(
        f'python scripts/light/patch_metadata_light.py '
        f'--mag-root "{target}" '
        + ('--dry-run' if dry_run else '')
    )
    # Fetch Artikeltexte für leere/fehlende Artikel)
    fetch_cmd = f'python scripts/light/fetch_articles_light.py --mag-root "{target}"'
    if retry_missing:
        fetch_cmd += " --retry-missing"
    if dry_run:
        fetch_cmd += " --dry-run"
    sh(fetch_cmd)
    #  Validate
    if validate:
        # Magazinname für Dateinamen ermitteln
        mag_name = os.path.basename(target)
        mag_json = os.path.join(target, "magazine.json")
        try:
            if os.path.exists(mag_json):
                import json
                with open(mag_json, "r", encoding="utf-8") as f:
                    _mj = json.load(f)
                mag_name = _mj.get("magazine_name") or mag_name
        except Exception:
            pass

        def _slug(s: str, maxlen=40):
            s = unicodedata.normalize("NFKD", s)
            s = "".join(ch for ch in s if ch.isalnum() or ch in (" ", "_", "-"))
            s = re.sub(r"\s+", "_", s).strip("_")
            return (s[:maxlen].rstrip("_") or "mag")

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = "logs/validation"
        os.makedirs(report_dir, exist_ok=True)
        report_txt = os.path.join(report_dir, f"validate_{_slug(mag_name)}_{ts}.txt")
        sh(f'python scripts/light/validate_corpus.py --mag-root "{target}" > "{report_txt}"')
        print(f"\n Validierungsreport: {report_txt}")

def fetch_catalog(timeout=25, retries=3, sleep=0.5):
    """
    Liefert eine Liste von Dicts: {magazine_id, magazine_name, issue_url, city, form, years}
    Parst die Tabelle auf /ezines.php (nur die Zeilen mit echten Magazinen).
    """
    headers = {"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"}
    last_exc = None
    for _ in range(retries):
        try:
            r = requests.get(CATALOG_URL, headers=headers, timeout=timeout)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            break
        except Exception as e:
            last_exc = e
            time.sleep(sleep)
    else:
        print(f"❌ Katalogabruf fehlgeschlagen: {last_exc}")
        sys.exit(2)

    rows = []
    table = soup.find("table")
    if not table:
        table = soup

    for tr in table.find_all("tr"):
        tds = tr.find_all("td", class_="catalog")
        if len(tds) >= 3:
            # Spalte 1: Name + Link (issue.php?id=N)
            a = tds[0].find("a", href=True)
            if not a:
                continue
            name = a.get_text(strip=True)
            href = a["href"]
            if not href.startswith("http"):
                href = urljoin(BASE_URL + "/", href.lstrip("/"))
            # id aus URL ziehen
            m = re.search(r"[?&]id=(\d+)", href)
            if not m:
                continue
            mag_id = int(m.group(1))
            # Spalte 2: Stadt (Text)
            city = tds[1].get_text(" ", strip=True)
            # Spalte 3: Form (газета/журнал/…)
            form = tds[2].get_text(" ", strip=True)
            # Spalte 4: Jahre (optional vorhanden)
            years = None
            if len(tds) >= 4:
                years = tds[3].get_text(" ", strip=True)
            rows.append({
                "magazine_id": mag_id,
                "magazine_name": name,
                "issue_url": href,
                "city": city,
                "form": form,
                "years": years
            })
    return rows

def main():
    parser = argparse.ArgumentParser(
        description="ZXPress Light Pipeline (scrape + patch + fetch [+ validate])"
    )
    parser.add_argument("--mode", choices=["seeds", "single", "all"], default="single",
                        help="seeds: YAML-Seeds; single: nur ein Magazin; all: kompletter Katalog von ezines.php")
    parser.add_argument("--config", help="Pfad zu YAML (z.B. config/zxpress.yaml)")
    parser.add_argument("--mag-url", help="URL der Magazinseite (issue.php?id=…)")
    parser.add_argument("--out-root", help="Ausgabe-Ordner (z.B. data/zxpress/magazines/Z80)")
    parser.add_argument("--mag-root", help="Optional: Root-Verzeichnis für Patch/Fetch (überschreibt Ziel)")
    parser.add_argument("--root", default="data/zxpress/magazines", help="Standard-Root, wenn nichts anderes angegeben ist")
    parser.add_argument("--retry-missing", action="store_true", help="Fehlende Artikel erneut laden")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen/patchen, nichts persistentes verändern")
    parser.add_argument("--validate", action="store_true", help="Am Ende Pydantic-Validierung ausführen")
    parser.add_argument("--limit", type=int, default=None, help="Max. Anzahl Magazine (nur für --mode all)")
    parser.add_argument("--start-after-id", type=int, default=None, help="Starte nach Magazin-ID (nur für --mode all)")
    parser.add_argument("--sleep-mag", type=float, default=0.8, help="Pause (Sekunden) zwischen Magazinen")

    args = parser.parse_args()
    # YAML laden (optional, falls vorhanden)
    cfg = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    if args.root:
        mags_root = args.root
    else:
        data_root = cfg.get("project", {}).get("data_root", "data/zxpress")
        mags_root = os.path.join(data_root, "magazines")

    os.makedirs(mags_root, exist_ok=True)

    if args.mode == "seeds":
        seeds = (cfg.get("seeds") or [])
        if not seeds:
            print("⚠️ Keine seeds in der YAML gefunden.")
            sys.exit(0)
        for seed in seeds:
            mag_url = seed["issue_url"]
            mag_name = seed["magazine_name"]
            out_dir_name = safe_mag_dir_name(mag_name)
            out_root = os.path.join(mags_root, out_dir_name)
            print(f"\n=== Seed: {mag_name} ({mag_url}) → {out_root}")
            run_for_magazine(
                mag_url=mag_url,
                out_root=out_root,
                retry_missing=args.retry_missing,
                dry_run=args.dry_run,
                validate=args.validate,
                target_override=out_root
            )
            time.sleep(args.sleep_mag)

    elif args.mode == "all":
        print(f"🌐 Lade Katalog: {CATALOG_URL}")
        catalog = fetch_catalog()
        catalog.sort(key=lambda x: x["magazine_id"])
        if args.start_after_id is not None:
            catalog = [c for c in catalog if c["magazine_id"] > args.start_after_id]
        if args.limit:
            catalog = catalog[:args.limit]

        print(f" Magazine im Katalog (nach Filter): {len(catalog)}")
        for i, item in enumerate(catalog, 1):
            mag_url = item["issue_url"]
            name = item["magazine_name"]
            out_dir_name = safe_mag_dir_name(name)
            out_root = os.path.join(mags_root, out_dir_name)
            print(f"\n=== [{i}/{len(catalog)}] {name} (id={item['magazine_id']}) → {out_root}")
            run_for_magazine(
                mag_url=mag_url,
                out_root=out_root,
                retry_missing=args.retry_missing,
                dry_run=args.dry_run,
                validate=args.validate,
                target_override=out_root
            )
            time.sleep(args.sleep_mag)

    else:  # single
        if not args.mag_url:
            print("❌ Bitte --mag-url angeben (issue.php?id=…).")
            sys.exit(2)
        if args.out_root:
            out_root = args.out_root
        else:
            # Ordnername aus URL (id=XYZ → mag_XYZ)
            import urllib.parse as _u
            q = _u.urlparse(args.mag_url).query
            _id = dict(_u.parse_qsl(q)).get("id", "mag")
            out_root = os.path.join(mags_root, f"mag_{_id}")

        os.makedirs(out_root, exist_ok=True)
        print(f"\n=== Single-Run: {args.mag_url} → {out_root}")
        run_for_magazine(
            mag_url=args.mag_url,
            out_root=out_root,
            retry_missing=args.retry_missing,
            dry_run=args.dry_run,
            validate=args.validate,
            target_override=out_root
        )

    print("\n✅ Pipeline fertig.")
if __name__ == "__main__":
    main()