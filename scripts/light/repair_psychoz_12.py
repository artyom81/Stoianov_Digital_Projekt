import os
import json
import re
import unicodedata
import sys
import shutil
from pathlib import Path

MAG = "data/zxpress/magazines/Psychoz"
A = os.path.join(MAG, "issues", "12_0000-01-01")
B = os.path.join(MAG, "issues", "12", "12_0000-01-01")


def J(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def slugify(text, maxlen=60):
    if not text:
        return "item"
    s = unicodedata.normalize("NFKD", text)
    s = "".join(ch for ch in s if ch.isalnum() or ch in (" ", "_", "-"))
    s = re.sub(r"\s+", "_", s).strip("_")
    if len(s) > maxlen:
        s = s[:maxlen].rstrip("_")
    return s or "item"


def article_dir_name(order, article_id, short_slug):
    return f"{int(order):02d}_{article_id}_{short_slug}"


def load_listing(issue_dir):
    p = os.path.join(issue_dir, "listing.json")
    if not os.path.isfile(p):
        raise FileNotFoundError(f"listing.json fehlt: {p}")
    data = J(p)
    if not isinstance(data, list):
        raise ValueError(f"Listing-Struktur unerwartet in {p}")
    return data


def normalize_listing_items(items, start_order=1):
    out = []
    for i, it in enumerate(items, start_order):
        obj = dict(it)
        obj["order"] = i
        obj["issue_label"] = "12"
        if not obj.get("short_slug"):
            obj["short_slug"] = slugify(obj.get("title_link", ""), 60)
        out.append(obj)
    return out


def existing_article_dirs(issue_dir):
    articles_dir = os.path.join(issue_dir, "articles")
    if not os.path.isdir(articles_dir):
        return {}
    out = {}
    for name in os.listdir(articles_dir):
        full = os.path.join(articles_dir, name)
        if not os.path.isdir(full):
            continue
        m = re.match(r"^(\d+)_([0-9]+)_(.+)$", name)
        if m:
            article_id = int(m.group(2))
            out[article_id] = full
    return out


def copytree_merge(src, dst):
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_root = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_root, exist_ok=True)
        for d in dirs:
            os.makedirs(os.path.join(target_root, d), exist_ok=True)
        for fn in files:
            s = os.path.join(root, fn)
            t = os.path.join(target_root, fn)
            shutil.copy2(s, t)


def ensure_article_dirs(issue_dir):
    os.makedirs(os.path.join(issue_dir, "articles"), exist_ok=True)


def main():
    if not (os.path.isdir(A) and os.path.isdir(B)):
        print("Nichts zu tun (A oder B fehlt).")
        sys.exit(0)

    la = load_listing(A)
    lb = load_listing(B)

    la = normalize_listing_items(la, start_order=1)
    lb = normalize_listing_items(lb, start_order=len(la) + 1)
    merged = la + lb

    # Artikelordner aus beiden Quellen sammeln
    src_a = existing_article_dirs(A)
    src_b = existing_article_dirs(B)

    ensure_article_dirs(A)
    dst_articles = os.path.join(A, "articles")

    copied = 0
    missing = []

    for item in merged:
        article_id = int(item["article_id"])
        order = int(item["order"])
        short_slug = item.get("short_slug") or slugify(item.get("title_link", ""), 60)
        target_name = article_dir_name(order, article_id, short_slug)
        target_dir = os.path.join(dst_articles, target_name)

        src_dir = None
        if article_id in src_a:
            src_dir = src_a[article_id]
        elif article_id in src_b:
            src_dir = src_b[article_id]

        if src_dir is None:
            missing.append(article_id)
            continue

        if os.path.abspath(src_dir) == os.path.abspath(target_dir):
            continue

        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        copytree_merge(src_dir, target_dir)
        copied += 1

    # Listing + issue.json aktualisieren
    issue_json_path = os.path.join(A, "issue.json")
    ij = J(issue_json_path)
    ij["issue_label"] = "12"
    if not ij.get("issue_date_iso"):
        ij["issue_date_iso"] = "0000-01-01"
    ij["issue_slug"] = f'12_{ij.get("issue_date_iso") or "0000-01-01"}'

    # tatsächliche Zielordner nach Merge zählen
    real_article_dirs = [
        x for x in os.listdir(dst_articles)
        if os.path.isdir(os.path.join(dst_articles, x))
    ]
    ij["articles_count"] = len(real_article_dirs)

    W(os.path.join(A, "listing.json"), merged)
    W(issue_json_path, ij)

    # B entfernen
    shutil.rmtree(B, ignore_errors=True)
    parent = os.path.dirname(B)
    try:
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)
    except Exception:
        pass

    print(f"✅ Merge ok: {A}")
    print(f"   listing entries : {len(merged)}")
    print(f"   article dirs    : {len(real_article_dirs)}")
    print(f"   copied/merged   : {copied}")
    if missing:
        print(f"⚠️  Fehlende Artikelordner für article_id: {missing}")


if __name__ == "__main__":
    main()