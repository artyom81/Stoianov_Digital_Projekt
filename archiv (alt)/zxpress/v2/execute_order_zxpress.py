import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://zxpress.ru"
CATALOG_URL = f"{BASE_URL}/ezines.php"
HEADERS = {
    "User-Agent": "DigitProjectScraper/1.0 (+your-university.example) Python-Requests",
    "Accept-Language": "ru,en;q=0.8,de;q=0.7",
}
RU_MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04", "мая": "05", "июня": "06",
    "июля": "07", "августа": "08", "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
}
DATE_RE = re.compile(r"(?P<d>\d{1,2})\s+(?P<m>[А-Яа-яёЁ]+)\s+(?P<y>\d{4})")

DATA_ROOT = Path("data/zxpress/magazines")
LOG_DIR = Path("logs")
ERROR_LOG = LOG_DIR / "zxpress_errors.log"

def ensure_dirs():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_err(msg: str):
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    print(f"❌ {msg}")

def mk_session(max_retries: int, timeout: int):
    s = requests.Session()
    s.headers.update(HEADERS)
    s.timeout = timeout
    s.max_retries = max_retries
    return s

def fetch_html(url: str, sess: requests.Session, max_retries: int = 3, pause: float = 0.5) -> Optional[BeautifulSoup]:
    for attempt in range(1, max_retries + 1):
        try:
            r = sess.get(url, timeout=sess.timeout)
            r.raise_for_status()
            r.encoding = "utf-8"
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log_err(f"Fetch-Fehler (Versuch {attempt}/{max_retries}) {url} :: {e}")
            time.sleep(pause * attempt)
    return None

def abspath(href: str) -> str:
    if href.startswith("http"):
        return href
    return f"{BASE_URL}/{href.lstrip('/')}"

def parse_ru_date(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    human = text.strip()
    m = DATE_RE.search(human.lower())
    if not m:
        return human, None
    d = int(m.group("d"))
    mru = m.group("m")
    y = int(m.group("y"))
    mm = RU_MONTHS.get(mru)
    return human, (f"{y:04d}-{mm}-{d:02d}" if mm else None)

def safe_name(s: str) -> str:
    return re.sub(r"[^\w\-\.А-Яа-яёЁ]+", "_", s, flags=re.UNICODE)

@dataclass
class MagazineMD:
    magazine_id: int
    magazine_name: str
    issue_url: str
    city: Optional[str]
    form: Optional[str]
    years: Optional[str]
    issues_expected_count: Optional[int]

@dataclass
class IssueMD:
    issue_label: str
    issue_date_human: Optional[str]
    issue_date_iso: Optional[str]
    issue_anchor_url: Optional[str]
    expected_articles: int

@dataclass
class ArticleMD:
    article_id: int
    article_url: str
    print_url: str
    title_link: Optional[str]
    title_h1: Optional[str]
    og_title: Optional[str]
    og_desc: Optional[str]
    date_iso: Optional[str]
    mismatch_title: bool
    notes: Optional[str]

def parse_catalog(sess) -> List[MagazineMD]:
    soup = fetch_html(CATALOG_URL, sess)
    if not soup:
        raise SystemExit("Katalogseite konnte nicht geladen werden.")
    table = soup.select_one("table")
    mags: List[MagazineMD] = []

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        name_td, city_td, form_td, years_td = tds[1], tds[2], tds[3], tds[4]
        a = name_td.find("a", href=True)
        if not a or "issue.php?id=" not in a["href"]:
            continue
        name = a.get_text(strip=True)
        mag_id = int(a["href"].split("=")[-1])
        small = name_td.find("span", class_="number")
        expected_issues = int(small.get_text(strip=True)) if small else None

        mags.append(MagazineMD(
            magazine_id=mag_id,
            magazine_name=name,
            issue_url=abspath(a["href"]),
            city=city_td.get_text(" ", strip=True) if city_td else None,
            form=form_td.get_text(strip=True) if form_td else None,
            years=years_td.get_text(strip=True) if years_td else None,
            issues_expected_count=expected_issues
        ))
    return mags

def parse_magazine_page(mag: MagazineMD, sess) -> Tuple[Dict[str, IssueMD], Dict[str, List[ArticleMD]]]:
    """Liest alle Ausgaben & Artikel eines Magazins (Ebene 2 + 3 Metadaten, kein Text)."""
    soup = fetch_html(mag.issue_url, sess)
    if not soup:
        log_err(f"Magazinseite nicht geladen: {mag.issue_url}")
        return {}, {}

    left = soup.find("div", class_="col-left") or soup
    issues: Dict[str, IssueMD] = {}
    arts_by_issue: Dict[str, List[ArticleMD]] = defaultdict(list)

    # Wir gehen alle Artikel-Links durch und ordnen sie dem zuletzt gesehenen Ausgabe-Anker <a name="NN"> zu
    for a in left.find_all("a", href=True):
        href = a["href"]
        if "article.php?id=" not in href:
            continue
        # Ausgabe-Label & Datum rückwärts suchen
        anchor = a.find_all_previous("a", attrs={"name": True}, limit=1)
        issue_label = anchor[0]["name"].strip() if anchor else "unknown"

        date_divs = a.find_all_previous("div", string=re.compile(r"\d{4}"), limit=3)
        date_human, date_iso = parse_ru_date(date_divs[0].get_text(strip=True) if date_divs else None)
        if issue_label not in issues:
            header_link = left.find("a", href=re.compile(r"issue\.php\?id=\d+#" + re.escape(issue_label)))
            issue_anchor_url = abspath(header_link["href"]) if header_link else None
            issues[issue_label] = IssueMD(
                issue_label=issue_label,
                issue_date_human=date_human,
                issue_date_iso=date_iso,
                issue_anchor_url=issue_anchor_url,
                expected_articles=0  # füllen wir unten
            )

        art_url = abspath(href)
        art_id = int(href.split("=")[-1])
        print_url = f"{BASE_URL}/print.php?id={art_id}"

        title_link = a.get_text(" ", strip=True)
        # Artikel-Seite öffnen (für H1/OG)
        art_soup = fetch_html(art_url, sess)
        title_h1 = None
        og_title = None
        og_desc = None
        notes = None
        mismatch = False

        if art_soup:
            h1 = art_soup.find("h1")
            title_h1 = h1.get_text(strip=True) if h1 else None
            mt = art_soup.find("meta", attrs={"property": "og:title"})
            md = art_soup.find("meta", attrs={"property": "og:description"})
            og_title = mt.get("content") if mt else None
            og_desc = md.get("content") if md else None

            canon = (title_h1 or og_title or "").strip()
            if canon:
                mismatch = (title_link.strip() != canon)
                if mismatch:
                    notes = "title_link != title_h1/og"
            else:
                notes = "no h1/og; using link title"
        else:
            notes = "article page fetch failed"

        arts_by_issue[issue_label].append(ArticleMD(
            article_id=art_id,
            article_url=art_url,
            print_url=print_url,
            title_link=title_link,
            title_h1=title_h1,
            og_title=og_title,
            og_desc=og_desc,
            date_iso=date_iso,
            mismatch_title=mismatch,
            notes=notes
        ))
    # gezählte Links je Label
    for label, lst in arts_by_issue.items():
        if label in issues:
            issues[label].expected_articles = len(lst)

    return issues, arts_by_issue

def fetch_article_text(print_url: str, sess) -> Optional[str]:
    soup = fetch_html(print_url, sess)
    if not soup:
        return None
    pre = soup.find("pre", id="text")
    if pre:
        return pre.get_text("\n", strip=True)
    return soup.get_text("\n", strip=True)

def save_json(path: Path, obj: dict, dry: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    if dry:
        return
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def save_text(path: Path, text: str, dry: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    if dry:
        return
    with path.open("w", encoding="utf-8") as f:
        f.write(text)

def run_scrape(mode: str, mag_id: Optional[int], rate_limit: float, max_retries: int, timeout: int, dry_run: bool) -> str:
    ensure_dirs()
    sess = mk_session(max_retries=max_retries, timeout=timeout)
    magazines = parse_catalog(sess)
    if mode == "seeds":
        magazines = [m for m in magazines if m.magazine_id == (mag_id or 1)]
        if not magazines:
            raise SystemExit(f"Magazin mit id={mag_id} nicht gefunden.")

    grand_summary = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "magazines_total": len(magazines),
        "dry_run": dry_run,
        "items": []
    }

    for mag in magazines:
        print(f"\n===  {mag.magazine_name} (id={mag.magazine_id}) ===")
        print(f"   city={mag.city} | form={mag.form} | years={mag.years} | expected_issues={mag.issues_expected_count}")

        issues, arts_by_issue = parse_magazine_page(mag, sess)
        print(f"   gefundene Ausgaben: {len(issues)}  | Artikel (gezählt): {sum(len(v) for v in arts_by_issue.values())}")

        mag_dir = DATA_ROOT / safe_name(mag.magazine_name)
        save_json(mag_dir / "magazine.json", asdict(mag), dry_run)
        idx_issues = []
        idx_articles = []
        saved_texts = 0
        saved_meta = 0
        skipped_existing = 0
        article_errors = 0

        for label, issue in sorted(issues.items(), key=lambda x: x[0], reverse=True):
            issue_dir = mag_dir / "issues" / f"{label}_{(issue.issue_date_iso or 'unknown')}"
            save_json(issue_dir / "issue.json", asdict(issue), dry_run)
            per_issue_count_expected = issue.expected_articles
            per_issue_count_saved = 0
            per_issue_count_seen = 0

            for art in arts_by_issue.get(label, []):
                per_issue_count_seen += 1
                art_dir = issue_dir / "articles" / str(art.article_id)
                text_path = art_dir / "text.txt"
                meta_path = art_dir / "meta.json"
                if text_path.exists() and meta_path.exists():
                    skipped_existing += 1
                    idx_articles.append({
                        "article_id": art.article_id,
                        "path": str(art_dir),
                        "issue_label": label
                    })
                    continue

                text = fetch_article_text(art.print_url, sess)
                if not text:
                    article_errors += 1
                    log_err(f"Kein Text: {art.print_url}")
                    continue

                save_json(meta_path, asdict(art), dry_run)
                save_text(text_path, text, dry_run)
                saved_meta += 1
                saved_texts += 1
                per_issue_count_saved += 1

                print(f"✅ gespeichert: {text_path}")
                time.sleep(rate_limit)

            idx_issues.append({
                "issue_label": label,
                "issue_date_iso": issue.issue_date_iso,
                "expected_articles": per_issue_count_expected,
                "seen_in_listing": per_issue_count_seen,
                "saved": per_issue_count_saved
            })

        save_json(mag_dir / "indexes" / "issues.json", idx_issues, dry_run)
        save_json(mag_dir / "indexes" / "articles.json", idx_articles, dry_run)

        mismatches = sum(
            1 for lst in arts_by_issue.values() for a in lst if a.mismatch_title
        )
        if mismatches:
            print(f"   ⚠️ Titel-Abweichungen: {mismatches} (Link vs. H1/OG)")
        else:
            print("   ✅ Keine Titel-Abweichungen erkannt")

        mag_report = {
            "magazine": asdict(mag),
            "issues_found": len(issues),
            "articles_listed": sum(len(v) for v in arts_by_issue.values()),
            "saved_texts": saved_texts,
            "saved_meta": saved_meta,
            "skipped_existing": skipped_existing,
            "article_errors": article_errors,
            "mismatches": mismatches,
            "issue_breakdown": idx_issues
        }
        grand_summary["items"].append(mag_report)

    grand_summary["finished"] = datetime.now().isoformat(timespec="seconds")
    return json.dumps(grand_summary, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="ZXPress Full Scraper (mit Summary & Error-Log)")
    ap.add_argument("--mode", choices=["all", "seeds"], default="seeds",
                    help="Kompletter Katalog oder nur ein Magazin (seeds)")
    ap.add_argument("--mag-id", type=int, default=1, help="Nur bei mode=seeds: Magazin-ID (Default 1 = #Z80)")
    ap.add_argument("--rate-limit", type=float, default=0.35, help="Sekunden Pause pro Artikel (Server schonen)")
    ap.add_argument("--max-retries", type=int, default=3, help="HTTP-Retries")
    ap.add_argument("--timeout", type=int, default=30, help="HTTP-Timeout (Sekunden)")
    ap.add_argument("--dry-run", action="store_true", help="Nur zählen od. prüfen, nichts speichern")
    ap.add_argument("--summary-out", default="", help="Summary als JSON-Datei speichern")
    args = ap.parse_args()

    try:
        summary_json = run_scrape(
            mode=args.mode,
            mag_id=args.mag_id,
            rate_limit=args.rate_limit,
            max_retries=args.max_retries,
            timeout=args.timeout,
            dry_run=args.dry_run
        )
        print("\n SUMMARY ")
        print(summary_json)

        if args.summary_out:
            out_path = Path(args.summary_out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(summary_json, encoding="utf-8")
            print(f"\n Summary gespeichert: {out_path}")
    except KeyboardInterrupt:
        print("\n… abgebrochen (Ctrl-C). Teil-Ergebnisse bleiben erhalten.")
    except Exception as e:
        log_err(f"Fataler Fehler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()