import os, re, json, argparse, unicodedata
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, List

RU_MONTHS_STEMS = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5,
    "июн": 6, "июл": 7, "август": 8, "сентябр": 9,
    "октябр": 10, "ноябр": 11, "декабр": 12,
}

def _month_from_text(txt: str) -> Optional[int]:
    t = (txt or "").lower()
    for stem, m in RU_MONTHS_STEMS.items():
        if stem in t:
            return m
    return None

def parse_ru_date_to_iso(human: str) -> Optional[str]:
    #'09 марта 2000' → '2000-03-09'
    #'ноябрь 1993'   → '1993-11-01'
    #'1997'          → '1997-01-01'
    if not human:
        return None
    s = unicodedata.normalize("NFKC", human).strip().lower()
    # Tag + Monat + Jahr
    m = re.search(r'(\d{1,2})\s+([а-яa-zё]+)\s+((?:19|20)\d{2})', s, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        mon = _month_from_text(m.group(2))
        year = int(m.group(3))
        if mon:
            return f"{year:04d}-{mon:02d}-{day:02d}"
    # Monat + Jahr
    m2 = re.search(r'([а-яa-zё]+)\s+((?:19|20)\d{2})', s, re.IGNORECASE)
    if m2:
        mon = _month_from_text(m2.group(1))
        year = int(m2.group(2))
        if mon:
            return f"{year:04d}-{mon:02d}-01"
    # Nur Jahr
    m3 = re.search(r'((?:19|20)\d{2})', s)
    if m3:
        year = int(m3.group(1))
        return f"{year:04d}-01-01"

    return None

def parse_ru_year_range_to_iso(range_text: str) -> Dict[str, Optional[str]]:

    # 'ноябрь 1993 – июль 1997' → {'start': '1993-11-01', 'end': '1997-07-01'}
    # gegen -, –, — und Whitespaces.
    if not range_text:
        return {"start": None, "end": None}

    s = unicodedata.normalize("NFKC", range_text).strip()
    s = s.replace("—", "–").replace("-", "–")
    parts = [p.strip() for p in s.split("–") if p.strip()]
    if len(parts) == 2:
        start = parse_ru_date_to_iso(parts[0])
        end   = parse_ru_date_to_iso(parts[1])
        return {"start": start, "end": end}

    one = parse_ru_date_to_iso(s)
    return {"start": one, "end": None}

def _is_bogus_iso(d: Optional[str]) -> bool:
    # Erkennt offensichtlichen Quatsch wie '0019-..' oder '0000-..'."""
    if not d or len(d) < 4:
        return True
    try:
        y = int(d[:4])
        return y < 1800
    except Exception:
        return True

def load_json(p: str) -> Optional[Any]:
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(p: str, obj: Any, dry: bool = False) -> None:
    if dry:
        print(f"  (dry) would write: {p}")
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def guess_mag_id(mag: Dict[str, Any]) -> Optional[int]:
    mid = mag.get("magazine_id")
    if isinstance(mid, int):
        return mid
    url = mag.get("magazine_url") or mag.get("issue_url")
    if url:
        q = parse_qs(urlparse(url).query)
        if "id" in q:
            try:
                return int(q["id"][0])
            except Exception:
                pass
    return None

def slugify(text: str, maxlen: int = 60) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(ch for ch in s if ch.isalnum() or ch in (" ", "_", "-"))
    s = re.sub(r"\s+", "_", s).strip("_")
    if len(s) > maxlen:
        s = s[:maxlen].rstrip("_")
    return s or "item"

def patch_magazine(mag_path: str, dry: bool) -> Optional[Dict[str, Any]]:
    mag = load_json(mag_path)
    if not mag:
        print(f"⚠️  keine magazine.json bei {mag_path}")
        return None
    changed = False
    mag_dir = os.path.dirname(mag_path)
    issues_dir = os.path.join(mag_dir, "issues")

    mid = guess_mag_id(mag)
    if mid and mag.get("magazine_id") != mid:
        mag["magazine_id"] = mid
        changed = True

    if os.path.isdir(issues_dir):
        cnt = sum(1 for d in os.listdir(issues_dir) if os.path.isdir(os.path.join(issues_dir, d)))
        if mag.get("issues_count") != cnt:
            mag["issues_count"] = cnt
            changed = True

    if not mag.get("language"):
        mag["language"] = "ru"
        changed = True

    # rights & source (Anforderung von ZXPress.ru)
    if not mag.get("rights"):
        mag["rights"] = "Использование материалов сайта разрешено только при указании обратной ссылки"
        changed = True
    if not mag.get("source"):
        mag["source"] = "ZXPRESS (https://zxpress.ru)"
        changed = True

    src_years = mag.get("years_human") or mag.get("period") or ""
    yrs = parse_ru_year_range_to_iso(src_years)

    # falls Ende vor Start liegt und beides plausibel, tauschen
    def _iso_ymd(s: Optional[str]) -> Optional[tuple]:
        if not s or not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return None
        y, m, d = s.split("-")
        return (int(y), int(m), int(d))
    s_ = _iso_ymd(yrs.get("start"))
    e_ = _iso_ymd(yrs.get("end"))
    if s_ and e_ and e_ < s_:
        yrs["start"], yrs["end"] = yrs["end"], yrs["start"]

    def _with_fallback(d: Optional[str]) -> str:
        return d if d else "0000-01-01"

    need_set = False
    if not mag.get("years_iso"):
        need_set = True
    else:
        yiso = mag["years_iso"]
        if _is_bogus_iso(yiso.get("start")) or _is_bogus_iso(yiso.get("end")):
            need_set = True

    if need_set:
        mag["years_iso"] = {
            "start": _with_fallback(yrs["start"]),
            "end": _with_fallback(yrs["end"]),
        }
        changed = True

    if changed:
        save_json(mag_path, mag, dry=dry)
    return mag


def patch_issue(issue_dir: str, mag_meta: Dict[str, Any], dry: bool) -> None:
    ipath = os.path.join(issue_dir, "issue.json")
    lpath = os.path.join(issue_dir, "listing.json")
    issue = load_json(ipath)
    if not issue:
        print(f"  ⚠️  keine issue.json in {issue_dir}")
        return

    changed_issue = False

    label = (issue.get("issue_label") or "00").strip()
    iso = issue.get("issue_date_iso")

    # Falls ISO-Datum fehlt/Platzhalter ist: aus Ordnernamen ableiten
    folder_name = os.path.basename(issue_dir)
    if "_" in folder_name:
        _lbl, folder_iso = folder_name.split("_", 1)
        if not iso or iso in (None, "0000-01-01"):
            issue["issue_date_iso"] = folder_iso
            iso = folder_iso
            changed_issue = True

    # Wenn immer noch kein valides Datum dann Startmonat des Magazins nehmen
    def _is_placeholder(d: Optional[str]) -> bool:
        return (d or "").strip() in ("", "0000-01-01")

    if _is_placeholder(iso) and isinstance(mag_meta, dict):
        yiso = mag_meta.get("years_iso") or {}
        start_iso = (yiso.get("start") or "").strip()
        # nur verwenden, wenn plausibel Jahr >= 1900
        if re.match(r"^(19|20)\d{2}-\d{2}-\d{2}$", start_iso):
            year, mon, day = start_iso.split("-")
            # auf Monat-genau normalisieren (Tag=01, falls unbekannt)
            if day == "00":
                day = "01"
            inferred = f"{year}-{mon}-01"
            issue["issue_date_iso"] = inferred
            iso = inferred
            # Marker setzen, damit klar ist, dass das Datum abgeleitet wurde
            issue["date_inferred"] = True
            issue["date_precision"] = "month"
            changed_issue = True

    slug = f"{label}_{issue.get('issue_date_iso', '0000-01-01')}"
    if issue.get("issue_slug") != slug:
        issue["issue_slug"] = slug
        changed_issue = True

    # Inherit basics aus magazin-Metadaten
    if mag_meta:
        if issue.get("magazine_id") != mag_meta.get("magazine_id"):
            issue["magazine_id"] = mag_meta.get("magazine_id")
            changed_issue = True
        if mag_meta.get("magazine_name") and issue.get("magazine_name") != mag_meta.get("magazine_name"):
            issue["magazine_name"] = mag_meta.get("magazine_name")
            changed_issue = True
        if not issue.get("language") and mag_meta.get("language"):
            issue["language"] = mag_meta["language"]
            changed_issue = True
        if mag_meta.get("city") and issue.get("city") != mag_meta.get("city"):
            issue["city"] = mag_meta["city"]
            changed_issue = True
        if mag_meta.get("country") and issue.get("country") != mag_meta.get("country"):
            issue["country"] = mag_meta["country"]
            changed_issue = True

    if changed_issue:
        save_json(ipath, issue, dry=dry)

    # listing.json: order + issue_label + optional short_slug
    listing = load_json(lpath)
    if not listing:
        return
    changed_list = False
    for i, item in enumerate(listing, 1):
        if item.get("order") != i:
            item["order"] = i
            changed_list = True
        if item.get("issue_label") != label:
            item["issue_label"] = label
            changed_list = True
        if not item.get("short_slug") and item.get("title_link"):
            item["short_slug"] = slugify(item["title_link"], maxlen=60)
            changed_list = True
    if changed_list:
        save_json(lpath, listing, dry=dry)


def build_mag_listing(mag_dir: str, dry: bool) -> None:
    # Erzeugt/aktualisiert magazine-level listing.json aus den Issue-Ordnern.
    # Format muss sein: {"issues": [{"issue_label": "01", "issue_date_iso": "1998-05-07", "articles_count": 10}, ...]}
    issues_dir = os.path.join(mag_dir, "issues")
    if not os.path.isdir(issues_dir):
        return

    issues: List[Dict[str, Any]] = []
    for folder in sorted(os.listdir(issues_dir)):
        p_issue = os.path.join(issues_dir, folder)
        if not os.path.isdir(p_issue) or "_" not in folder:
            continue
        label, date_iso = folder.split("_", 1)
        meta = load_json(os.path.join(p_issue, "issue.json")) or {}
        # Quelle für articles_count: issue.json oder listing.json-Länge oder Ordnerzählung
        ac = meta.get("articles_count")
        if not isinstance(ac, int):
            lst = load_json(os.path.join(p_issue, "listing.json")) or []
            if isinstance(lst, list):
                ac = len(lst)
            else:
                ac = 0
        issues.append({
            "issue_label": meta.get("issue_label") or label,
            "issue_date_iso": meta.get("issue_date_iso") or date_iso,
            "articles_count": ac,
        })

    def _label_key(lbl: str):
        return (0, int(lbl)) if str(lbl).isdigit() else (1, str(lbl))

    issues.sort(key=lambda it: (_label_key(it.get("issue_label", "")), it.get("issue_date_iso") or "9999-12-31"))

    if issues:
        out_path = os.path.join(mag_dir, "listing.json")
        save_json(out_path, {"issues": issues}, dry=dry)

def main():
    ap = argparse.ArgumentParser(description="Patch ZXPress metadata (magazine/issue/listing)")
    ap.add_argument("--root", default="data/zxpress/magazines", help="Pfad zu allen Magazinen")
    ap.add_argument("--mag-root", help="Nur dieses Magazin patchen (z. B. data/zxpress/magazines/Z80)")
    ap.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht schreiben")
    args = ap.parse_args()
    mags = [args.mag_root] if args.mag_root else \
           [os.path.join(args.root, d) for d in os.listdir(args.root)
            if os.path.isdir(os.path.join(args.root, d))]

    for mag_dir in sorted(mags):
        mag_json = os.path.join(mag_dir, "magazine.json")
        print(f"===  Patch: {mag_dir} ===")
        mag_meta = patch_magazine(mag_json, dry=args.dry_run)

        if mag_meta:
            if not mag_meta.get("magazine_name") and mag_meta.get("name"):
                mag_meta["magazine_name"] = mag_meta["name"]
            # city/country . aus zusammengesetztem Feld splitten
            cc = mag_meta.get("city_country") or mag_meta.get("place")
            if cc and (not mag_meta.get("city") or not mag_meta.get("country")):
                # Stadt/Land Spaltung: "Пермь (Россия)" → city="Пермь", country="Россия"
                m = re.match(r"\s*(.+?)\s*\((.+?)\)\s*$", cc)
                if m:
                    mag_meta.setdefault("city", m.group(1))
                    mag_meta.setdefault("country", m.group(2))

        issues_dir = os.path.join(mag_dir, "issues")
        if not os.path.isdir(issues_dir):
            print("  ⚠️  kein issues/-Ordner, weiter")
            continue

        for issue_name in sorted(os.listdir(issues_dir)):
            issue_path = os.path.join(issues_dir, issue_name)
            if not os.path.isdir(issue_path):
                continue
            print(f"  • Issue: {issue_name}")
            patch_issue(issue_path, mag_meta or {}, dry=args.dry_run)

        build_mag_listing(mag_dir, dry=args.dry_run)

    print("✅ Patch fertig.")

if __name__ == "__main__":
    main()