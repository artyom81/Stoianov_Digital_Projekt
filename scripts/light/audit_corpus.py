import os, json, argparse, csv

def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def count_article_dirs(issue_dir):
    arts = os.path.join(issue_dir, "articles")
    if not os.path.isdir(arts):
        return None
    return sum(
        1 for d in os.listdir(arts)
        if os.path.isdir(os.path.join(arts, d))
    )

def newest_log_for_mag(log_dir, mag_name):
    if not log_dir or not os.path.isdir(log_dir):
        return None

    prefix = f"validate_{mag_name}_"
    candidates = [
        f for f in os.listdir(log_dir)
        if f.startswith(prefix) and f.endswith(".txt")
    ]

    if not candidates:
        return None

    candidates = sorted(
        candidates,
        key=lambda fn: os.path.getmtime(os.path.join(log_dir, fn)),
        reverse=True
    )
    return os.path.join(log_dir, candidates[0])

def parse_validator_status(path):
    if not path or not os.path.exists(path):
        return ("N/A", [])

    status = "UNKNOWN"
    warnings = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()

        if "❌ Validierung: FEHLER" in txt:
            status = "FEHLER"
        elif "✅ Validierung: OK" in txt:
            status = "OK"

        if "(mit Warnungen)" in txt:
            status = "OK+WARN"

        for line in txt.splitlines():
            line = line.strip()
            if not line:
                continue
            if "WARN" in line or "Platzhalter '0000-01-01'" in line:
                warnings.append(line)

    except Exception:
        pass

    return (status, warnings)

def classify_row(row):
    reasons = []

    status = row["validator_status"]
    zero = row["issues_zero_articles"]
    miss = row["issues_missing_articles_dir"]
    issues = row["issues"]
    articles = row["articles"]

    if status == "FEHLER":
        reasons.append("Validator meldet Fehler")
    elif status == "OK+WARN":
        reasons.append("Validator meldet Warnungen")
    elif status == "N/A":
        reasons.append("Kein Validator-Log gefunden")

    if miss > 0:
        reasons.append(f"{miss} Issue(s) ohne articles/-Ordner")

    if zero > 0:
        reasons.append(f"{zero} Issue(s) mit 0 Artikeln")

    if issues == 0:
        reasons.append("Magazin ohne Issues")

    if issues > 0 and articles == 0:
        reasons.append("Issues vorhanden, aber 0 Artikel")

    return reasons

def main():
    ap = argparse.ArgumentParser(description="Audit ZXPress-Korpus")
    ap.add_argument("--root", required=True, help="data/zxpress/magazines")
    ap.add_argument("--logs", required=False, help="logs/validation")
    ap.add_argument("--out", required=False, help="CSV-Ausgabe komplett")
    ap.add_argument("--problems-out", required=False, help="CSV nur Problemfälle")
    ap.add_argument("--problems-log", required=False, help="Textlog nur Problemfälle")
    args = ap.parse_args()

    rows = []
    total_mags = total_issues = total_articles = 0

    mags = [
        os.path.join(args.root, d)
        for d in os.listdir(args.root)
        if os.path.isdir(os.path.join(args.root, d))
    ]

    for mag_dir in sorted(mags):
        mag_name = os.path.basename(mag_dir)
        mag_json = load_json(os.path.join(mag_dir, "magazine.json")) or {}
        issues_dir = os.path.join(mag_dir, "issues")
        has_listing = os.path.isfile(os.path.join(mag_dir, "listing.json"))

        issue_folders = []
        if os.path.isdir(issues_dir):
            issue_folders = sorted([
                d for d in os.listdir(issues_dir)
                if os.path.isdir(os.path.join(issues_dir, d))
            ])

        mag_issue_cnt = 0
        mag_article_cnt = 0
        issues_with_zero_articles = 0
        issues_missing_articles_dir = 0

        for folder in issue_folders:
            mag_issue_cnt += 1
            iid = os.path.join(issues_dir, folder)
            n = count_article_dirs(iid)

            if n is None:
                issues_missing_articles_dir += 1
            else:
                mag_article_cnt += n
                if n == 0:
                    issues_with_zero_articles += 1

        total_mags += 1
        total_issues += mag_issue_cnt
        total_articles += mag_article_cnt

        log_path = newest_log_for_mag(args.logs, mag_name) if args.logs else None
        vstatus, warns = parse_validator_status(log_path)

        row = {
            "magazine": mag_name,
            "magazine_id": mag_json.get("magazine_id"),
            "issues": mag_issue_cnt,
            "articles": mag_article_cnt,
            "issues_missing_articles_dir": issues_missing_articles_dir,
            "issues_zero_articles": issues_with_zero_articles,
            "has_mag_listing_json": int(has_listing),
            "validator_status": vstatus,
            "validator_log": os.path.basename(log_path) if log_path else "",
            "problem_reasons": " | ".join(classify_row({
                "validator_status": vstatus,
                "issues_zero_articles": issues_with_zero_articles,
                "issues_missing_articles_dir": issues_missing_articles_dir,
                "issues": mag_issue_cnt,
                "articles": mag_article_cnt,
            })),
        }
        rows.append(row)

    if not rows:
        print("Keine Magazine gefunden.")
        return

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    problem_rows = [r for r in rows if r["problem_reasons"]]

    if args.problems_out:
        os.makedirs(os.path.dirname(args.problems_out), exist_ok=True)
        with open(args.problems_out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(problem_rows)

    if args.problems_log:
        os.makedirs(os.path.dirname(args.problems_log), exist_ok=True)
        with open(args.problems_log, "w", encoding="utf-8") as f:
            f.write("Problematische Magazine zur manuellen Sichtung\n")
            f.write("=============================================\n\n")
            f.write("Legende:\n")
            f.write("- validator_status: OK / OK+WARN / FEHLER / N/A\n")
            f.write("- issues_zero_articles: Issues mit 0 Artikelordnern\n")
            f.write("- issues_missing_articles_dir: Issues ohne articles/-Ordner\n")
            f.write("- problem_reasons: konkrete Gründe für manuelle Sichtung\n\n")

            for r in problem_rows:
                f.write(f"- {r['magazine']}\n")
                f.write(f"  magazine_id: {r['magazine_id']}\n")
                f.write(f"  validator_status: {r['validator_status']}\n")
                f.write(f"  issues: {r['issues']}\n")
                f.write(f"  articles: {r['articles']}\n")
                f.write(f"  issues_zero_articles: {r['issues_zero_articles']}\n")
                f.write(f"  issues_missing_articles_dir: {r['issues_missing_articles_dir']}\n")
                f.write(f"  validator_log: {r['validator_log']}\n")
                f.write(f"  problem_reasons: {r['problem_reasons']}\n\n")

    print(f"Magazine: {total_mags} | Issues: {total_issues} | Artikel: {total_articles}")
    print(f"Problematische Magazine: {len(problem_rows)}")

    if problem_rows:
        print("\nTop 20 problematische Magazine:")
        ranked = sorted(
            problem_rows,
            key=lambda r: (
                0 if r["validator_status"] == "FEHLER" else
                1 if r["validator_status"] == "OK+WARN" else
                2 if r["validator_status"] == "N/A" else 3,
                -(r["issues_missing_articles_dir"] + r["issues_zero_articles"]),
                -r["issues"],
                -r["articles"],
            )
        )
        for r in ranked[:20]:
            print(
                f"- {r['magazine']}: "
                f"status={r['validator_status']}, "
                f"issues={r['issues']}, "
                f"articles={r['articles']}, "
                f"zero={r['issues_zero_articles']}, "
                f"missing_articles_dir={r['issues_missing_articles_dir']} "
                f"| Gründe: {r['problem_reasons']}"
            )

if __name__ == "__main__":
    main()