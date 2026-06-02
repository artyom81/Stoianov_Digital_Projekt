import argparse
import subprocess
import sys
from pathlib import Path

def run_step(label, cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    ok = res.returncode == 0
    return {
        "label": label,
        "cmd": " ".join(cmd),
        "returncode": res.returncode,
        "ok": ok,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
    }

def append_block(lines, title, content):
    lines.append(f"=== {title} ===")
    if content:
        lines.append(content)
    else:
        lines.append("(keine Ausgabe)")
    lines.append("")

def main():
    ap = argparse.ArgumentParser(description="Vollständiger Healthcheck für TextSearch.")
    ap.add_argument("--index-dir", required=True, help="Pfad zum Lucene-Index")
    ap.add_argument(
        "--tools-dir",
        default="scripts/TextSearch/_tools",
        help="Pfad zum _tools-Verzeichnis",
    )
    ap.add_argument(
        "--log-dir",
        default="logs/textsearch",
        help="Zielordner für Healthcheck-Logs",
    )
    ap.add_argument(
        "--log-file",
        default="full_healthcheck.txt",
        help="Name der zusammengefassten Ergebnisdatei",
    )
    args = ap.parse_args()
    tools_dir = Path(args.tools_dir)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / args.log_file
    feld = tools_dir / "feldabdeckung.py"
    idx = tools_dir / "indexueberpruefen.py"

    if not feld.exists():
        print(f"❌ Nicht gefunden: {feld}")
        sys.exit(2)
    if not idx.exists():
        print(f"❌ Nicht gefunden: {idx}")
        sys.exit(2)

    steps = [
        (
            "Feldabdeckung",
            [sys.executable, str(feld), "--index-dir", args.index_dir],
        ),
        (
            "Index-Basisprüfung",
            [sys.executable, str(idx), "--index-dir", args.index_dir],
        ),
    ]

    results = [run_step(label, cmd) for label, cmd in steps]

    lines = []
    lines.append("TextSearch Healthcheck")
    lines.append("======================")
    lines.append(f"Index-Verzeichnis: {args.index_dir}")
    lines.append(f"Tools-Verzeichnis: {tools_dir}")
    lines.append("")
    for r in results:
        lines.append(f"--- Schritt: {r['label']} ---")
        lines.append(f"Befehl: {r['cmd']}")
        lines.append(f"Returncode: {r['returncode']}")
        lines.append(f"Status: {'OK' if r['ok'] else 'FEHLER'}")
        lines.append("")

        append_block(lines, f"{r['label']} / STDOUT", r["stdout"])
        if r["stderr"]:
            append_block(lines, f"{r['label']} / STDERR", r["stderr"])

    all_ok = all(r["ok"] for r in results)
    lines.append("=== Gesamtfazit ===")
    if all_ok:
        lines.append("✅ TextSearch-Healthcheck erfolgreich.")
        lines.append("Der Lucene-Index ist lesbar und die Basispruefungen fuer Searcher/Index sind erfolgreich.")
    else:
        lines.append("❌ TextSearch-Healthcheck mit Fehlern.")
        lines.append("Mindestens ein Teilcheck ist fehlgeschlagen. Details siehe oben.")
    lines.append("")

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Log geschrieben: {log_path}")
    print()
    print("=== Gesamtfazit ===")
    if all_ok:
        print("✅ TextSearch-Healthcheck erfolgreich.")
        print("Wenn dieser Check erfolgreich ist, kann der Searcher lokal ausgeführt werden.")
        sys.exit(0)
    else:
        print("❌ TextSearch-Healthcheck mit Fehlern.")
        print(f"Details: {log_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()