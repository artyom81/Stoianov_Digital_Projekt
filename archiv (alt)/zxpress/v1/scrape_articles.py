import os
import json
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from archive.zxpress.v1.utils import safe_filename  # wir nutzen das schon vorhandene helper

BASE_URL = "https://zxpress.ru"

def _sha1(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(data)
    return h.hexdigest()

def _safe_get(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, timeout=20)
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None

def _extract_article_links(issue_dir: str) -> List[Dict[str, Any]]:
    """
    Liest die auf der Ausgabe-Seite gespeicherte Liste der Artikel-Links ein.
    Diese Liste erzeugt dein scrape_magazine() typischerweise.
    wenn keine Liste existiert, wird aus issue.html extrahiert.
    Erwartetes Format von saved list (articles_order.json precursor):
      [{"article_id": 11660, "url": ".../article.php?id=11660", "title_hint": "..."}]
    """
    prepared = os.path.join(issue_dir, "articles_list.json")
    if os.path.exists(prepared):
        with open(prepared, "r", encoding="utf-8") as f:
            rows = json.load(f)
        cleaned = []
        for r in rows:
            aid = r.get("article_id")
            url = r.get("url")
            title_hint = r.get("title_hint")
            if aid and url:
                cleaned.append({"article_id": int(aid), "url": url, "title_hint": title_hint})
        return cleaned

    issue_meta_path = os.path.join(issue_dir, "issue.json")
    if not os.path.exists(issue_meta_path):
        return []
    with open(issue_meta_path, "r", encoding="utf-8") as f:
        issue_meta = json.load(f)
    issue_url = issue_meta.get("issue_url")
    if not issue_url:
        return []

    soup = _safe_get(issue_url)
    if not soup:
        return []

    left = soup.find("div", class_="col-left") or soup
    rows: List[Dict[str, Any]] = []
    seen = set()

    for block in left.find_all("div", style=lambda v: v and "13pt/14pt Times" in v):
        a = block.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if "article.php?id=" not in href:
            continue
        if not href.startswith("http"):
            href = BASE_URL + "/" + href.lstrip("/")
        art_id = href.split("=")[-1]
        if not art_id.isdigit():
            continue
        if art_id in seen:
            continue
        seen.add(art_id)
        title_hint = a.get_text(" ", strip=True)
        rows.append({"article_id": int(art_id), "url": href, "title_hint": title_hint})
    return rows

def _fetch_article_print(article_id: int) -> Dict[str, Any]:
    url = f"{BASE_URL}/print.php?id={article_id}"
    soup = _safe_get(url)
    title = None
    text = ""
    if soup:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        pre = soup.find("pre", id="text")
        if pre:
            text = pre.get_text("\n", strip=True)
        else:
            # fallback: kompletter Text
            text = soup.get_text("\n", strip=True)
    return {"print_url": url, "title": title, "text": text}

def scrape_issue_articles(config_path: str, issue_dir: str, magazine_id: int,
                          form: Optional[str] = None,
                          city: Optional[str] = None,
                          country: Optional[str] = None) -> None:
    """
    Erzeugt für jede Ausgabe die Artikel-Ordner:
      <issue_dir>/articles/01_<id>_<slug>/
    Schreibt/aktualisiert:
      - <article_dir>/meta.json
      - <article_dir>/text.txt
      - <issue_dir>/articles_order.json
    """

    issue_meta_path = os.path.join(issue_dir, "issue.json")
    with open(issue_meta_path, "r", encoding="utf-8") as f:
        issue_meta = json.load(f)

    articles_root = os.path.join(issue_dir, "articles")
    os.makedirs(articles_root, exist_ok=True)
    link_rows = _extract_article_links(issue_dir)
    manifest_path = os.path.join(issue_dir, "articles_order.json")
    manifest: List[Dict[str, Any]] = []

    for seq, row in enumerate(link_rows, start=1):
        article_id = int(row["article_id"])
        url = row["url"]
        fallback_title = row.get("title_hint") or f"Article {article_id}"
        data = _fetch_article_print(article_id)
        title = data.get("title") or fallback_title
        text = data.get("text") or ""
        print_url = data.get("print_url")
        slug = safe_filename(title, 60) if title else str(article_id)
        art_dirname = f"{seq:02d}_{article_id}_{slug}"
        art_dir = os.path.join(articles_root, art_dirname)
        os.makedirs(art_dir, exist_ok=True)

        txt_path = os.path.join(art_dir, "text.txt")
        meta_path = os.path.join(art_dir, "meta.json")

        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✅ gespeichert: {os.path.relpath(txt_path)}")
        except Exception as e:
            print(f"❌ Fehler beim Speichern text.txt ({article_id}): {e}")

        meta = {
            "magazine_id": magazine_id,
            "magazine_name": issue_meta.get("magazine_name"),
            "issue_id": issue_meta.get("issue_id"),
            "issue_num": issue_meta.get("issue_num"),
            "issue_date": issue_meta.get("issue_date"),
            "form": form,
            "city": city,
            "country": country,
            "article_id": article_id,
            "seq": seq,
            "title": title,
            "print_url": print_url,
            "source_url": url,
            "status": "ok" if os.path.exists(txt_path) else "missing",
            "sha1": _sha1(open(txt_path, "rb").read()) if os.path.exists(txt_path) else None,
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Fehler beim Speichern meta.json ({article_id}): {e}")

        # Manifest-Zeile
        manifest.append({
            "seq": seq,
            "article_id": article_id,
            "title": title,
            "print_url": print_url,
            "dir": os.path.relpath(art_dir, issue_dir),
        })

        time.sleep(0.2)  # nett zum Server
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Fehler beim Speichern articles_order.json: {e}")