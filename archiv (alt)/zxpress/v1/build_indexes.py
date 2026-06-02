import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple


def _safe_read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _sha1_of_file(path: str) -> Optional[str]:
    if not os.path.exists(path) or not os.path.isfile(path):
        return None
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _size_of_file(path: str) -> Optional[int]:
    try:
        return os.path.getsize(path) if os.path.exists(path) else None
    except Exception:
        return None


def _parse_seq_id_slug(dirname: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Versucht Ordnernamen wie '01_1868_Titel' zu parsen.
    """
    if "_" in dirname:
        parts = dirname.split("_", 2)
        if len(parts) >= 2 and parts[0].isdigit():
            try:
                seq = int(parts[0])
            except ValueError:
                seq = None
            art_id = parts[1] if parts[1].isdigit() else None
            slug = parts[2] if len(parts) == 3 else None
            return seq, art_id, slug
    # Fallback: nur ID
    return None, dirname if dirname.isdigit() else None, None


def _collect_articles_from_fs(arts_dir: str) -> List[Dict[str, Any]]:
    """
    Falls kein Manifest existiert: lese Artikelordner direkt vom FS.
    Versuche Reihenfolge aus 'NN_<id>_<slug>' zu entnehmen, sonst alphabetisch.
    """
    rows: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(arts_dir)):
        art_dir = os.path.join(arts_dir, name)
        if not os.path.isdir(art_dir):
            continue
        seq, art_id, _ = _parse_seq_id_slug(name)
        meta_path = os.path.join(art_dir, "meta.json")
        txt_path = os.path.join(art_dir, "text.txt")
        meta = _safe_read_json(meta_path) or {}
        title = meta.get("title")
        rows.append({
            "seq": seq,                        # kann None sein
            "article_id": int(art_id) if art_id and art_id.isdigit() else meta.get("article_id"),
            "title": title,
            "path": art_dir,
            "print_url": meta.get("print_url"),
            "has_text": os.path.exists(txt_path),
            "has_meta": os.path.exists(meta_path),
            "status": meta.get("status", "ok" if os.path.exists(txt_path) else "missing"),
            "sha1": meta.get("sha1") or _sha1_of_file(txt_path),
            "size_bytes": _size_of_file(txt_path),
        })
    # Sortierung: erst nach seq (falls vorhanden), sonst nach article_id, sonst by name via path
    rows.sort(key=lambda r: (
        (r["seq"] if isinstance(r["seq"], int) else 10**9),
        (r["article_id"] if isinstance(r.get("article_id"), int) else 10**9),
        r["path"],
    ))
    return rows


def _collect_articles_from_manifest(issue_dir: str) -> List[Dict[str, Any]]:
    """
    Nutzt articles_order.json als Ground Truth für die Reihenfolge.
    """
    order_path = os.path.join(issue_dir, "articles_order.json")
    arts_dir = os.path.join(issue_dir, "articles")
    listing = _safe_read_json(order_path)
    if not listing:
        # Fallback auf FS
        return _collect_articles_from_fs(arts_dir) if os.path.isdir(arts_dir) else []

    rows: List[Dict[str, Any]] = []
    for row in listing:
        seq = row.get("seq")
        art_id = row.get("article_id")
        # Ordner kann NN_<id>_* sein, aber wir suchen robust nach Verzeichnis, das die id enthält:
        chosen_dir = None
        if os.path.isdir(arts_dir):
            for name in os.listdir(arts_dir):
                if f"_{art_id}_" in name or name.endswith(f"_{art_id}") or name == str(art_id):
                    p = os.path.join(arts_dir, name)
                    if os.path.isdir(p):
                        chosen_dir = p
                        break
        # letzte Chance: es gibt evtl. nur "<id>"
        if chosen_dir is None:
            p = os.path.join(arts_dir, str(art_id))
            if os.path.isdir(p):
                chosen_dir = p

        meta_path = os.path.join(chosen_dir, "meta.json") if chosen_dir else None
        txt_path = os.path.join(chosen_dir, "text.txt") if chosen_dir else None
        meta = _safe_read_json(meta_path) if meta_path and os.path.exists(meta_path) else {}
        title = meta.get("title") or row.get("title")
        rows.append({
            "seq": seq,
            "article_id": art_id,
            "title": title,
            "path": chosen_dir or "",
            "print_url": row.get("print_url") or meta.get("print_url"),
            "has_text": bool(txt_path and os.path.exists(txt_path)),
            "has_meta": bool(meta_path and os.path.exists(meta_path)),
            "status": (meta.get("status") if meta else ("ok" if txt_path and os.path.exists(txt_path) else "missing")),
            "sha1": (meta.get("sha1") if meta else (_sha1_of_file(txt_path) if txt_path else None)),
            "size_bytes": _size_of_file(txt_path) if txt_path else None,
        })

    rows.sort(key=lambda r: (r["seq"] if isinstance(r["seq"], int) else 10**9))
    return rows


def build_indexes(mag_dir: str):
    """
    Erwartete Struktur:
      <mag_dir>/issues/<issue_id>/issue.json
      <mag_dir>/issues/<issue_id>/articles/...
      <mag_dir>/issues/<issue_id>/articles_order.json (optional, bevorzugt)
    """
    indexes: Dict[str, List[Dict[str, Any]]] = {"issues": [], "articles": []}
    issues_root = os.path.join(mag_dir, "issues")

    if not os.path.isdir(issues_root):
        print(f"⚠️ Keine issues/ in {mag_dir}")
        return

    total_issues = 0
    total_articles = 0

    for issue_id in sorted(os.listdir(issues_root)):
        issue_dir = os.path.join(issues_root, issue_id)
        if not os.path.isdir(issue_dir):
            continue

        issue_meta = _safe_read_json(os.path.join(issue_dir, "issue.json")) or {}
        issue_meta_enriched = {
            "issue_id": issue_id,
            "issue_dir": os.path.relpath(issue_dir, mag_dir),
            **issue_meta
        }
        indexes["issues"].append(issue_meta_enriched)
        total_issues += 1

        # Artikel sammeln (Manifest bevorzugt)
        rows = _collect_articles_from_manifest(issue_dir)
        for r in rows:
            indexes["articles"].append({
                "issue_id": issue_id,
                "issue_dir": os.path.relpath(issue_dir, mag_dir),
                "article_dir": os.path.relpath(r["path"], mag_dir) if r["path"] else "",
                "article_id": r.get("article_id"),
                "seq": r.get("seq"),
                "title": r.get("title"),
                "print_url": r.get("print_url"),
                "has_text": bool(r.get("has_text")),
                "has_meta": bool(r.get("has_meta")),
                "status": r.get("status"),
                "sha1": r.get("sha1"),
                "size_bytes": r.get("size_bytes"),
            })
        total_articles += len(rows)

    idx_dir = os.path.join(mag_dir, "indexes")
    os.makedirs(idx_dir, exist_ok=True)

    with open(os.path.join(idx_dir, "issues.json"), "w", encoding="utf-8") as f:
        json.dump(indexes["issues"], f, ensure_ascii=False, indent=2)

    with open(os.path.join(idx_dir, "articles.json"), "w", encoding="utf-8") as f:
        json.dump(indexes["articles"], f, ensure_ascii=False, indent=2)

    print(f" Indexe aktualisiert in {idx_dir}")
    print(f"   • Issues:   {total_issues}")
    print(f"   • Articles: {total_articles}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Baue Indexe für ein Magazinverzeichnis")
    ap.add_argument("mag_dir", help="Pfad zu data/zxpress/magazines/<MAGAZIN>")
    args = ap.parse_args()
    build_indexes(args.mag_dir)