import os, sys, json, argparse, re
from datetime import datetime
from typing import List, Dict, Any, Optional

def mag_display_name(mag_root: str) -> str:
    p = os.path.join(mag_root, "magazine.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                j = json.load(f)
            n = j.get("magazine_name")
            if n:
                return str(n)
        except Exception:
            pass
    # Fallback: Ordnername
    return os.path.basename(os.path.normpath(mag_root))

def J(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_iso_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False

def is_placeholder_date(s: Optional[str]) -> bool:
    return (s or "").strip() == "0000-01-01"

def find_issue_dirs(mag_root: str) -> List[Dict[str, Any]]:
    """
    Liefert eine Liste erkannter Issues:
      {"dir": <Pfad>, "folder": <Ordnername>, "label": <issue_label>, "date_iso": <YYYY-MM-DD>, "issue_json": <Pfad>}
    Quelle der Wahrheit ist issue.json; der Ordnername dient als Fallback.
    """
    issues_root = os.path.join(mag_root, "issues")
    out = []
    if not os.path.isdir(issues_root):
        return out

    for d in sorted(os.listdir(issues_root)):
        p = os.path.join(issues_root, d)
        if not os.path.isdir(p):
            continue
        # Versuch 1: issue.json lesen
        ip = os.path.join(p, "issue.json")
        label = None
        date_iso = None
        if os.path.exists(ip):
            try:
                issue = J(ip)
                label = (issue.get("issue_label") or "").strip()
                date_iso = (issue.get("issue_date_iso") or "").strip()
            except Exception:
                pass
        # Versuch 2 (Fallback): Ordnername <label>_<YYYY-MM-DD>
        if not label or not date_iso:
            m = re.match(r"^(?P<label>[^_]+)_(?P<date>\d{4}-\d{2}-\d{2})$", d)
            if m:
                label = label or m.group("label")
                date_iso = date_iso or m.group("date")

        if label and date_iso:
            out.append({
                "dir": p,
                "folder": d,
                "label": label,
                "date_iso": date_iso,
                "issue_json": ip if os.path.exists(ip) else None,
            })
        else:
            # Undurchsichtiger Ordner – überspringen (keinen harten Fehler)
            print(f"  - WARN: unklare Issue-Ordnerstruktur bei '{d}' (keine issue.json und kein Label/Datum im Namen)")

    return out

def load_listing(mag_root: str) -> List[Dict[str, Any]]:
    """
    Versucht listing.json zu laden. Akzeptiert:
      - Liste von Issues
      - Objekt mit Key "issues": [...]
    Fallback: rekonstruiert aus Ordnern.
    """
    p_listing = os.path.join(mag_root, "listing.json")
    if os.path.exists(p_listing):
        try:
            data = J(p_listing)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("issues"), list):
                return data["issues"]
            print("  - WARN: listing.json hat ein unerwartetes Format – nutze Ordnerstruktur.")
        except Exception as e:
            print(f"  - WARN: listing.json nicht lesbar ({e}) – nutze Ordnerstruktur.")

    # Fallback: aus Ordnern ableiten
    derived = []
    for it in find_issue_dirs(mag_root):
        derived.append({"issue_label": it["label"], "issue_date_iso": it["date_iso"]})
    return derived

def validate_magazine(mag_root: str) -> int:
    mag_name = mag_display_name(mag_root)
    print(f"  Magazin: {mag_name}")
    errors: List[str] = []
    warnings: List[str] = []
    p_mag_json = os.path.join(mag_root, "magazine.json")
    if os.path.exists(p_mag_json):
        try:
            mag = J(p_mag_json)
            if not mag.get("magazine_name"):
                errors.append("[magazine.json] magazine_name fehlt oder leer")
            if mag.get("magazine_id") is not None and not isinstance(mag.get("magazine_id"), int):
                errors.append("[magazine.json] magazine_id ist kein int")
        except Exception as e:
            errors.append(f"[magazine.json] JSON-Fehler: {e}")
    else:
        print(f"️  Hinweis: Keine magazine.json bei {p_mag_json} (nicht kritisch)")

    # Issues aus listing.json oder Ordnerstruktur
    issues_list = load_listing(mag_root)
    # Wenn listing.json existiert, aber leer ist dann OK mit Warnung (Magazin ohne Issues)
    has_listing_json = os.path.exists(os.path.join(mag_root, "listing.json"))
    if not issues_list:
        if has_listing_json:
            print("   Hinweis: listing.json vorhanden aber ohne Issues – Magazin scheint leer zu sein.")
            # Früh-Exit: OK mit Warnung und kleiner Zusammenfassung
            print("\n✅ Validierung: OK")
            print("   (mit Warnungen)")
            print("  - Magazin hat keine Issues (leerer Eintrag auf der Webseite)")
            print("   ➜ Issues: 0 | Artikel gesamt: 0")
            sys.exit(0)
        else:
            errors.append("Keine Issues auffindbar (weder listing.json noch issues/-Ordner verwertbar)")

    # Issues-Ordner inventarisieren (für Zuordnung)
    found_dirs = find_issue_dirs(mag_root)
    found_map = {(f["label"], f["date_iso"]): f for f in found_dirs}
    # pro Issue prüfen
    issues_root = os.path.join(mag_root, "issues")
    if not os.path.isdir(issues_root):
        errors.append(f"Kein issues/-Ordner bei {issues_root}")
    else:
        for issue in issues_list:
            label = str(issue.get("issue_label", "")).strip()
            date_iso = str(issue.get("issue_date_iso", "")).strip()
            # Datumsprüfung
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_iso):
                errors.append(f"[Issue #{label}] Ungültiges issue_date_iso: '{date_iso}' (YYYY-MM-DD)")
                continue
            elif is_placeholder_date(date_iso):
                warnings.append(f"[Issue #{label}] unbekanntes Datum → Platzhalter '0000-01-01'")
            # Ordner finden
            entry = found_map.get((label, date_iso))
            if entry is None:
                # Fallback: direkter Ordnername <label>_<date>
                folder = f"{label}_{date_iso}"
                candidate = os.path.join(issues_root, folder)
                if os.path.isdir(candidate):
                    entry = {
                        "dir": candidate,
                        "folder": folder,
                        "label": label,
                        "date_iso": date_iso,
                        "issue_json": os.path.join(candidate, "issue.json")
                    }
                else:
                    errors.append(f"[Issue {label}] Ordner fehlt: {candidate}")
                    continue

            p_issue_dir = entry["dir"]
            expected_folder = f"{label}_{date_iso}"
            if os.path.basename(p_issue_dir) != expected_folder:
                warnings.append(f"[Issue {label}] Ordnername weicht ab: '{entry['folder']}' ≠ '{expected_folder}'")

            p_issue_json = os.path.join(p_issue_dir, "issue.json")
            if not os.path.exists(p_issue_json):
                errors.append(f"[Issue {label}] issue.json fehlt: {p_issue_json}")
                article_count_declared = None
            else:
                try:
                    issue_meta = J(p_issue_json)
                    if str(issue_meta.get("issue_label", "")).strip() != label:
                        errors.append(f"[Issue {label}] issue.json: issue_label stimmt nicht: {issue_meta.get('issue_label')!r}")
                    if str(issue_meta.get("issue_date_iso", "")).strip() != date_iso:
                        errors.append(f"[Issue {label}] issue.json: issue_date_iso stimmt nicht: {issue_meta.get('issue_date_iso')!r}")
                    article_count_declared = issue_meta.get("articles_count")
                except Exception as e:
                    errors.append(f"[Issue {label}] issue.json JSON-Fehler: {e}")
                    article_count_declared = None
            # Artikel-Ordner
            p_articles = os.path.join(p_issue_dir, "articles")
            if not os.path.isdir(p_articles):
                errors.append(f"[Issue {label}] articles/-Ordner fehlt")
                continue

            article_dirs = sorted(
                d for d in os.listdir(p_articles)
                if os.path.isdir(os.path.join(p_articles, d))
            )
            if not article_dirs:
                errors.append(f"[Issue {label}] keine Artikelordner gefunden")
                continue

            # Vergleich deklarierte vs. gefundene Anzahl
            if isinstance(article_count_declared, int) and article_count_declared != len(article_dirs):
                warnings.append(f"[Issue {label}] articles_count in issue.json = {article_count_declared}, gefunden = {len(article_dirs)}")

            for a in article_dirs:
                p_a = os.path.join(p_articles, a)
                p_meta = os.path.join(p_a, "meta.json")
                p_text = os.path.join(p_a, "text.txt")

                if not os.path.exists(p_meta):
                    errors.append(f"[Issue {label}] {a}/meta.json fehlt")
                else:
                    try:
                        meta = J(p_meta)
                        if not isinstance(meta.get("article_id"), int):
                            errors.append(f"[Issue {label}] {a}/meta.json: article_id fehlt/kein int")
                        if not meta.get("title_link"):
                            warnings.append(f"[Issue {label}] {a}/meta.json: title_link fehlt/leer")
                        if not meta.get("print_url"):
                            errors.append(f"[Issue {label}] {a}/meta.json: print_url fehlt/leer")
                        if str(meta.get("issue_label", "")).strip() != label:
                            errors.append(f"[Issue {label}] {a}/meta.json: issue_label stimmt nicht")
                        if str(meta.get("issue_date_iso", "")).strip() != date_iso:
                            errors.append(f"[Issue {label}] {a}/meta.json: issue_date_iso stimmt nicht")

                        # Ordnerpräfix vs. meta.order
                        m = re.match(r"^(\d{2})_", a)
                        if m:
                            folder_order = int(m.group(1))
                            if isinstance(meta.get("order"), int) and meta["order"] != folder_order:
                                warnings.append(f"[Issue {label}] {a}: meta.order={meta['order']} ≠ Ordnerpräfix={folder_order}")
                    except Exception as e:
                        errors.append(f"[Issue {label}] {a}/meta.json JSON-Fehler: {e}")

                if not os.path.exists(p_text):
                    errors.append(f"[Issue {label}] {a}/text.txt fehlt")

    # Zusammenfassung
    if errors:
        print(f"\n❌ Validierung: FEHLER - {mag_name}")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    else:
        print(f"\n✅ Validierung: OK - {mag_name}")
        if warnings:
            print("   (mit Warnungen)")
            for w in warnings:
                print("  -", w)
        try:
            issues_cnt = len(load_listing(mag_root))
            total_articles = 0
            for it in find_issue_dirs(mag_root):
                adir = os.path.join(it["dir"], "articles")
                if os.path.isdir(adir):
                    total_articles += len([d for d in os.listdir(adir) if os.path.isdir(os.path.join(adir, d))])
            print(f"   ➜ Issues: {issues_cnt} | Artikel gesamt: {total_articles}")
        except Exception:
            pass
        sys.exit(0)

def main():
    ap = argparse.ArgumentParser(description="Validate ZXPress light corpus")
    ap.add_argument("--mag-root", required=True, help="Pfad zum Magazin-Root (z. B. data/zxpress/magazines/Z80)")
    args = ap.parse_args()

    if not os.path.isdir(args.mag_root):
        print(f"Pfad existiert nicht oder ist kein Ordner: {args.mag_root}")
        sys.exit(2)

    rc = validate_magazine(args.mag_root)
    sys.exit(rc)

if __name__ == "__main__":
    main()