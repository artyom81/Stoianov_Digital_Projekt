import os
import re

from archive.zxpress.v1.utils import (
    load_yaml,
    make_session,
    get_soup_session,
    absolute_url,
    safe_filename,
    parse_ru_date,
    dump_json,
    BASE_URL,
)

ISSUE_ANCHOR_RE = re.compile(r'issue\.php\?id=\d+#(?P<label>\d{2})')

def scrape_magazine(config_path, magazine_name, issue_url, magazine_id, data_root):
    """
    Parsed die Magazinseite (Ebene 2) und legt den Ausgabe-Ordner an.
    """
    cfg = load_yaml(config_path)
    sess = make_session(cfg)
    soup = get_soup_session(issue_url, sess)
    if not soup:
        raise RuntimeError(f"Magazinseite nicht geladen: {issue_url}")
    left = soup.find("div", class_="col-left") or soup
    # Ausgaben-Metadaten + Artikel in Fundreihenfolge
    issues_ordered = {}  # label -> {"date_human":..., "date_iso":..., "articles":[{id, url, title_link, print_url}]}
    current_issue_label = None

    for node in left.descendants:
        if getattr(node, "name", None) == "a" and node.has_attr("name"):
            current_issue_label = node["name"].strip()
            if current_issue_label not in issues_ordered:
                issues_ordered[current_issue_label] = {
                    "date_human": None,
                    "date_iso": None,
                    "articles": []
                }
        elif getattr(node, "name", None) == "div":
            txt = node.get_text("", strip=True) or ""
            # divs mit Jahreszahl enthalten meist das Ausgabedatum
            if re.search(r"\b(19|20)\d{2}\b", txt):
                human, iso = parse_ru_date(txt)
                if current_issue_label and human and not issues_ordered[current_issue_label]["date_human"]:
                    issues_ordered[current_issue_label]["date_human"] = human
                    issues_ordered[current_issue_label]["date_iso"] = iso
        elif getattr(node, "name", None) == "a" and node.has_attr("href"):
            href = node["href"]
            if "article.php?id=" in href and current_issue_label:
                url = absolute_url(BASE_URL, href)
                art_id = int(href.split("=")[-1])
                print_url = f"{BASE_URL}/print.php?id={art_id}"
                title_link = node.get_text(" ", strip=True)
                issues_ordered[current_issue_label]["articles"].append({
                    "article_id": art_id,
                    "article_url": url,
                    "print_url": print_url,
                    "title_link": title_link
                })

    mag_dir = os.path.join(data_root, "magazines", safe_filename(magazine_name, 80))
    os.makedirs(mag_dir, exist_ok=True)
    issue_root = os.path.join(mag_dir, "issues")
    os.makedirs(issue_root, exist_ok=True)

    # pro Ausgabe Ordner + issue.json + listing.json (Fundreihenfolge) schreiben
    for label, info in issues_ordered.items():
        iso = info["date_iso"] or "unknown"
        issue_dir = os.path.join(issue_root, f"{label}_{iso}")
        os.makedirs(os.path.join(issue_dir, "articles"), exist_ok=True)

        dump_json(os.path.join(issue_dir, "issue.json"), {
            "magazine_id": magazine_id,
            "magazine_name": magazine_name,
            "issue_label": label,
            "issue_date_human": info["date_human"],
            "issue_date_iso": info["date_iso"],
            "issue_url": issue_url,
            "articles_listed": len(info["articles"])
        })
        dump_json(os.path.join(issue_dir, "listing.json"), info["articles"])

    return issue_root