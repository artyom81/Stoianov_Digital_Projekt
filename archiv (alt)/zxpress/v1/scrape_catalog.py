import os
import json
from datetime import datetime
from typing import List, Dict
import yaml
from archive.zxpress.v1.utils import get_soup, ensure_dir, absolute_url, safe_filename
from archive.zxpress.v1.models import Magazine

def parse_catalog_row(tr) -> Dict:
    tds = tr.find_all("td")
    if len(tds) < 5:
        return {}
    name_td = tds[1]
    city_td = tds[2]
    form_td = tds[3]
    years_td = tds[4]
    a = name_td.find("a", href=True)
    if not a or "issue.php?id=" not in a["href"]:
        return {}

    name = a.get_text(strip=True)
    href = a["href"]
    issues_count = None
    num_span = name_td.find("span", class_="number")
    if num_span:
        try:
            issues_count = int(num_span.get_text(strip=True))
        except:
            issues_count = None

    city = city_td.get_text(" ", strip=True)
    country = None
    if "(" in city and ")" in city:
        try:
            c_name = city
            city = c_name[:c_name.index("(")].strip()
            country = c_name[c_name.index("(")+1:c_name.index(")")].strip()
        except Exception:
            pass

    form = form_td.get_text(strip=True)
    years = years_td.get_text(strip=True)
    mag_id = int(href.split("=")[-1])
    return {
        "id": mag_id,
        "name": name,
        "city": city,
        "country": country,
        "form": form,
        "years": years,
        "issues_count": issues_count,
        "issue_url": href
    }

def scrape_catalog(cfg_path: str) -> List[Magazine]:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base = cfg["site"]["base_url"]
    start_url = cfg["site"]["start_url"]
    rate = int(cfg["site"].get("rate_limit_ms", 0))
    data_root = cfg["data_root"]

    soup = get_soup(start_url, rate_limit_ms=rate)
    table = soup.select_one(cfg["site"]["selectors"]["catalog_table"]) or soup

    magazines: List[Magazine] = []
    for tr in table.find_all("tr"):
        info = parse_catalog_row(tr)
        if not info:
            continue
        info["issue_url"] = absolute_url(base, info["issue_url"])
        info["collected_at"] = datetime.utcnow().isoformat()
        m = Magazine(**info)
        magazines.append(m)

    ensure_dir(os.path.join(data_root, "magazines"))
    catalog_index = []
    for m in magazines:
        mag_dir = os.path.join(data_root, "magazines", safe_filename(m.name, 80))
        ensure_dir(mag_dir)
        with open(os.path.join(mag_dir, "magazine.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(m.model_dump(), ensure_ascii=False, indent=2))
        catalog_index.append(m.dict())

    with open(os.path.join(data_root, "magazines", "_catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog_index, f, ensure_ascii=False, indent=2)

    return magazines