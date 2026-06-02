import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://zxpress.ru"
CATALOG_URL = f"{BASE_URL}/ezines.php"

HEADERS = {
    "User-Agent": "DigitProjectBot/1.0 (+github.com/your-org) Python-Requests",
    "Accept-Language": "ru,en;q=0.8,de;q=0.7"
}

RU_MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04", "мая": "05", "июня": "06",
    "июля": "07", "августа": "08", "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
}
DATE_RE = re.compile(r"(?P<d>\d{1,2})\s+(?P<m>[А-Яа-яёЁ]+)\s+(?P<y>\d{4})")

def session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def soup_get(url: str, sess=None):
    sess = sess or session()
    r = sess.get(url, timeout=30)
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "html.parser")

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

@dataclass
class MagazineMD:
    magazine_id: int
    magazine_name: str
    issue_url: str
    city: Optional[str]
    form: Optional[str]
    years: Optional[str]
    issues_expected_count: Optional[int]  # von der Katalogseite (kleine Zahl)

@dataclass
class IssueMD:
    magazine_id: int
    magazine_name: str
    issue_label: str           # z.B. "06"
    issue_date_human: Optional[str]
    issue_date_iso: Optional[str]
    issue_anchor_url: Optional[str]  # link wie issue.php?id=189#06

@dataclass
class ArticleMD:
    magazine_id: int
    magazine_name: str
    issue_label: str
    issue_date_iso: Optional[str]
    article_id: int
    article_url: str
    print_url: str
    title_from_link: Optional[str]       # Titel, wie er auf der Ausgabenseite im Link steht
    title_from_article_h1: Optional[str] # Titel aus <h1> der Artikelseite
    og_title: Optional[str]
    og_description: Optional[str]
    mismatch_title: bool                 # True, wenn Link-Titel != H1/OG
    notes: Optional[str]                 # z.B. "no h1, fallback used"

def parse_catalog(sess=None) -> List[MagazineMD]:
    soup = soup_get(CATALOG_URL, sess)
    table = soup.select_one("table")
    mags: List[MagazineMD] = []

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        name_td = tds[1]
        city_td = tds[2]
        form_td = tds[3]
        years_td = tds[4]

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

def extract_issues_and_articles(mag: MagazineMD, limit_issues=None, limit_articles=None, sess=None) -> Tuple[List[IssueMD], List[ArticleMD]]:
    soup = soup_get(mag.issue_url, sess)
    left = soup.find("div", class_="col-left") or soup

    issues: Dict[str, IssueMD] = {}
    articles: List[ArticleMD] = []
    per_issue_counter: Dict[str, int] = {}

    for a in left.find_all("a", href=True):
        href = a["href"]
        if "article.php?id=" not in href:
            continue
        # Issue label rückwärts suchen
        anchor = a.find_all_previous("a", attrs={"name": True}, limit=1)
        issue_label = anchor[0]["name"].strip() if anchor else "unknown"
        date_divs = a.find_all_previous("div", string=re.compile(r"\d{4}"), limit=3)
        date_human, date_iso = parse_ru_date(date_divs[0].get_text(strip=True) if date_divs else None)

        if issue_label not in issues:
            issue_anchor_link = left.find("a", attrs={"name": issue_label})
            issue_anchor_url = None
            header_link = left.find("a", href=re.compile(r"issue\.php\?id=\d+#" + re.escape(issue_label)))
            if header_link:
                issue_anchor_url = abspath(header_link["href"])

            issues[issue_label] = IssueMD(
                magazine_id=mag.magazine_id,
                magazine_name=mag.magazine_name,
                issue_label=issue_label,
                issue_date_human=date_human,
                issue_date_iso=date_iso,
                issue_anchor_url=issue_anchor_url
            )

        per_issue_counter.setdefault(issue_label, 0)
        if limit_issues is not None and len(issues) > limit_issues:
            break
        if limit_articles is not None and per_issue_counter[issue_label] >= limit_articles:
            continue

        art_url = abspath(href)
        art_id = int(href.split("=")[-1])
        print_url = f"{BASE_URL}/print.php?id={art_id}"

        title_from_link = a.get_text(" ", strip=True)

        art_soup = soup_get(art_url, sess)
        h1 = art_soup.find("h1")
        title_from_h1 = h1.get_text(strip=True) if h1 else None

        og_title = art_soup.find("meta", attrs={"property": "og:title"})
        og_desc = art_soup.find("meta", attrs={"property": "og:description"})
        og_title_text = og_title.get("content") if og_title else None
        og_desc_text = og_desc.get("content") if og_desc else None

        canon = (title_from_h1 or og_title_text or "").strip()
        mismatch = False
        notes = None
        if canon:
            mismatch = (title_from_link.strip() != canon)
            if mismatch:
                notes = "title_link != title_h1/og"
        else:
            notes = "no h1/og; using link title"

        articles.append(ArticleMD(
            magazine_id=mag.magazine_id,
            magazine_name=mag.magazine_name,
            issue_label=issue_label,
            issue_date_iso=date_iso,
            article_id=art_id,
            article_url=art_url,
            print_url=print_url,
            title_from_link=title_from_link,
            title_from_article_h1=title_from_h1,
            og_title=og_title_text,
            og_description=og_desc_text,
            mismatch_title=mismatch,
            notes=notes
        ))
        per_issue_counter[issue_label] += 1

    return list(issues.values()), articles

def main():
    ap = argparse.ArgumentParser(description="ZXPress: Metadaten-Inspektor & Validator (keine Speicherung)")
    ap.add_argument("--mode", choices=["seeds", "all"], default="seeds",
                    help="Nur Seeds (#Z80) oder kompletter Katalog")
    ap.add_argument("--mag-id", type=int, default=1,
                    help="Für mode=seeds: Magazin-ID (Standard: 1 = #Z80)")
    ap.add_argument("--limit-issues", type=int, default=None, help="Max. Ausgaben pro Magazin")
    ap.add_argument("--limit-articles", type=int, default=None, help="Max. Artikel pro Ausgabe")
    ap.add_argument("--out-json", default="", help="Optional: JSON schreiben")
    ap.add_argument("--out-csv", default="", help="Optional: CSV schreiben (Artikel-Ebene)")
    args = ap.parse_args()

    sess = session()

    magazines: List[MagazineMD]
    if args.mode == "all":
        magazines = parse_catalog(sess)
    else:
        magazines = [m for m in parse_catalog(sess) if m.magazine_id == args.mag_id]
        if not magazines:
            raise SystemExit(f"Magazin mit id={args.mag_id} nicht gefunden.")

    all_issues: List[IssueMD] = []
    all_articles: List[ArticleMD] = []

    for mag in magazines:
        print(f"\n===  {mag.magazine_name} (id={mag.magazine_id}) ===")
        print(f"   city={mag.city} | form={mag.form} | years={mag.years} | expected_issues={mag.issues_expected_count}")
        issues, articles = extract_issues_and_articles(
            mag, limit_issues=args.limit_issues, limit_articles=args.limit_articles, sess=sess
        )
        all_issues.extend(issues)
        all_articles.extend(articles)

        per_issue = {}
        for a in articles:
            per_issue.setdefault(a.issue_label, 0)
            per_issue[a.issue_label] += 1

        print(f"   gefundene Ausgaben: {len(issues)}  | Artikel: {len(articles)}")
        for i in sorted(issues, key=lambda x: x.issue_label, reverse=True):
            print(f"     • Ausgabe {i.issue_label} ({i.issue_date_iso or i.issue_date_human or ''}) – Artikel: {per_issue.get(i.issue_label,0)}")

        mismatches = [a for a in articles if a.mismatch_title]
        if mismatches:
            print(f"   ⚠️ Titel-Abweichungen: {len(mismatches)} (Link vs. H1/OG)")
        else:
            print(f"   ✅ Keine Titel-Abweichungen erkannt")

    if args.out_json:
        payload = {
            "magazines": [asdict(m) for m in magazines],
            "issues": [asdict(i) for i in all_issues],
            "articles": [asdict(a) for a in all_articles],
        }
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n JSON geschrieben: {args.out_json}")

    if args.out_csv:
        with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([
                "magazine_id","magazine_name","issue_label","issue_date_iso",
                "article_id","article_url","print_url",
                "title_from_link","title_from_article_h1","og_title","mismatch_title","notes"
            ])
            for a in all_articles:
                w.writerow([
                    a.magazine_id, a.magazine_name, a.issue_label, a.issue_date_iso,
                    a.article_id, a.article_url, a.print_url,
                    a.title_from_link or "", a.title_from_article_h1 or "", a.og_title or "",
                    "1" if a.mismatch_title else "0", a.notes or ""
                ])
        print(f" CSV geschrieben: {args.out_csv}")

if __name__ == "__main__":
    main()