import os, re, json, time, argparse, unicodedata
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://zxpress.ru"

def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "ZXPressScraper/1.0 (+for research; contact: student)",
        "Accept-Language": "ru,en;q=0.8,de;q=0.7",
    })
    s.timeout = 30
    return s

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def load_json(p):
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(p, obj, dry=False):
    if dry:
        print(f"  (dry) would write {p}")
        return
    ensure_dir(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def save_text(p, text, dry=False):
    if dry:
        print(f"  (dry) would write {p} ({len(text)} chars)")
        return
    ensure_dir(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)

def slugify(text, maxlen=60):
    if not text:
        return "article"
    s = unicodedata.normalize("NFKC", text)
    s = s.replace(os.sep, "-").replace("\\", "-")
    s = "".join(ch for ch in s if ch.isalnum() or ch in (" ","_","-"))
    s = re.sub(r"\s+", "_", s).strip("_")
    if len(s) > maxlen:
        s = s[:maxlen].rstrip("_- .")
    return s or "article"

def extract_h1_or_title(soup):
    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(" ", strip=True)
        if t: return t
    ogt = soup.find("meta", attrs={"property": "og:title"})
    if ogt and ogt.get("content"):
        return ogt["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None

def fetch_print_text(sess, article_id):
    url = f"{BASE_URL}/print.php?id={article_id}"
    r = sess.get(url)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    pre = soup.find("pre", id="text")
    if pre:
        text = pre.get_text("\n", strip=True)
    else:
        text = soup.get_text("\n", strip=True)
    title_h1 = extract_h1_or_title(soup)
    return url, title_h1, text

def infer_ids_from_paths(issue_dir):
    mag_dir = os.path.dirname(os.path.dirname(issue_dir))
    mag = load_json(os.path.join(mag_dir, "magazine.json")) or {}
    issue = load_json(os.path.join(issue_dir, "issue.json")) or {}
    return mag, issue

def split_city_country(meta: dict):
    city = meta.get("city")
    country = meta.get("country")
    if city and country:
        return city, country
    cc = meta.get("city_country") or meta.get("place")
    if isinstance(cc, str):
        m = re.match(r"\s*(.+?)\s*\((.+?)\)\s*$", cc)
        if m:
            return city or m.group(1), country or m.group(2)
    return city, country

def process_issue(sess, issue_dir, dry=False, retry_missing=False, pause=0.3):
    listing_path = os.path.join(issue_dir, "listing.json")
    listing = load_json(listing_path)
    if not listing:
        print(f"  ⚠️ listing.json fehlt: {issue_dir}")
        return

    mag_meta, issue_meta = infer_ids_from_paths(issue_dir)
    mag_name = (mag_meta.get("magazine_name") or mag_meta.get("name") or "").strip()
    mag_id = mag_meta.get("magazine_id")
    city, country = split_city_country(mag_meta)
    issue_label = (issue_meta.get("issue_label") or "00").strip()
    issue_iso = (issue_meta.get("issue_date_iso") or "").strip()
    if not issue_iso or issue_iso == "0000-01-01":
        folder_name = os.path.basename(issue_dir)
        if "_" in folder_name:
            _, folder_iso = folder_name.split("_", 1)
            if re.match(r"^\d{4}-\d{2}-\d{2}$", folder_iso):
                issue_iso = folder_iso
            else:
                issue_iso = "0000-01-01"

    articles_dir = ensure_dir(os.path.join(issue_dir, "articles"))
    ok, skipped, failed = 0, 0, 0
    for idx, item in enumerate(listing, 1):
        # Felder aus listing.json
        order = item.get("order") or idx
        art_id = item.get("article_id")
        print_url = item.get("print_url")
        title_link = item.get("title_link") or ""
        short_slug = item.get("short_slug") or slugify(title_link, 60)

        if not print_url and art_id:
            print_url = f"{BASE_URL}/print.php?id={art_id}"
        article_url = item.get("article_url")
        if not article_url and art_id:
            article_url = f"{BASE_URL}/article.php?id={art_id}"

        folder_name = f"{order:02d}_{art_id}_{short_slug}"
        if len(folder_name) > 120:
            # keep prefix stable, trim slug further if needed
            keep = f"{order:02d}_{art_id}_"
            folder_name = keep + short_slug[: max(20, 120 - len(keep))]
        art_dir = os.path.join(articles_dir, folder_name)
        text_path = os.path.join(art_dir, "text.txt")
        meta_path = os.path.join(art_dir, "meta.json")

        if os.path.exists(text_path) and os.path.exists(meta_path) and not retry_missing:
            print(f"    ↪︎ skip vorhanden: {folder_name}")
            skipped += 1
            continue

        try:
            print(f"    ⇢ hole Artikel {order:02d} (id={art_id}) …")
            url_used, title_h1, text = fetch_print_text(sess, art_id)

            if not text or len(text) < 10:
                print(f"    ⚠️ leer/kurz: id={art_id}")
                failed += 1
                continue

            meta = {
                "magazine_id": mag_id,
                "magazine_name": mag_name,
                "city": city,
                "country": country,
                "issue_label": issue_label,
                "issue_date_iso": issue_iso or "0000-01-01",
                "order": order,
                "article_id": art_id,
                "title_link": title_link,
                "title_h1": title_h1,
                "print_url": print_url,
                "article_url": article_url,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            save_text(text_path, text, dry=dry)
            save_json(meta_path, meta, dry=dry)
            print(f"    ✅ gespeichert: {os.path.relpath(art_dir)}")
            ok += 1
            time.sleep(pause)
        except Exception as e:
            print(f"    ❌ Fehler bei id={art_id}: {e}")
            failed += 1

    print(f"  Ergebnis Issue {issue_label} ({issue_iso or '0000-01-01'}): ok={ok}, skip={skipped}, fail={failed}")

def process_magazine(mag_root, dry=False, retry_missing=False):
    issues_root = os.path.join(mag_root, "issues")
    if not os.path.isdir(issues_root):
        print(f"⚠️ kein issues/-Ordner: {mag_root}")
        return
    sess = make_session()
    print(f"===  Magazin: {os.path.basename(mag_root)} ===")
    for issue_name in sorted(os.listdir(issues_root)):
        issue_dir = os.path.join(issues_root, issue_name)
        if not os.path.isdir(issue_dir):
            continue
        print(f"  • Issue: {issue_name}")
        process_issue(sess, issue_dir, dry=dry, retry_missing=retry_missing)

def main():
    ap = argparse.ArgumentParser(description="ZXPress – Artikeltexte speichern (Text + Meta)")
    ap.add_argument("--mag-root", help="Pfad zu einem Magazin (z. B. data/zxpress/magazines/Z80)")
    ap.add_argument("--root", default="data/zxpress/magazines", help="Wurzelordner aller Magazine")
    ap.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts schreiben")
    ap.add_argument("--retry-missing", action="store_true", help="Nur fehlende Texte nachladen")
    args = ap.parse_args()

    if args.mag_root:
        mags = [args.mag_root]
    else:
        if not os.path.isdir(args.root):
            print(f"⚠️ root nicht gefunden: {args.root}")
            return
        mags = [os.path.join(args.root, d) for d in os.listdir(args.root)
                if os.path.isdir(os.path.join(args.root, d))]

    for mag_dir in sorted(mags):
        process_magazine(mag_dir, dry=args.dry_run, retry_missing=args.retry_missing)

    print("✅ Fertig.")

if __name__ == "__main__":
    main()