#!/usr/bin/env bash
# health_zxpress.sh — Struktur-/Vollständigkeitscheck für ZXPress-Korpus
# Nutzung: ./health_zxpress.sh [ROOT] [LOGDIR]
#   ROOT   : Basisordner der Magazine (Default: data/zxpress/magazines)
#   LOGDIR : Ziel für Logs (Default: logs/health)

set -euo pipefail

ROOT="${1:-data/zxpress/magazines}"
LOGDIR="${2:-logs/health}"
VALIDATION_LOGDIR="${3:-logs/validation}"

mkdir -p "$LOGDIR"

ISSUES_LOG="$LOGDIR/issues_missing.log"
ARTS_LOG="$LOGDIR/articles_missing.log"
PLACEHOLDER_LOG="$LOGDIR/placeholders_0000-01-01.log"
EMPTY_MAGS_LOG="$LOGDIR/magazines_empty.log"

AUDIT_CSV="$LOGDIR/audit_summary.csv"
AUDIT_PROBLEMS_CSV="$LOGDIR/audit_problematic_magazines.csv"
AUDIT_PROBLEMS_LOG="$LOGDIR/audit_problematic_magazines.log"
AUDIT_STDOUT_LOG="$LOGDIR/audit_stdout.log"

SUMMARY_TXT="$LOGDIR/summary.txt"

: >"$ISSUES_LOG"
: >"$ARTS_LOG"
: >"$PLACEHOLDER_LOG"
: >"$EMPTY_MAGS_LOG"
: >"$AUDIT_STDOUT_LOG"
: >"$SUMMARY_TXT"

echo "▶ Root: $ROOT"
if [[ ! -d "$ROOT" ]]; then
  echo "❌ ROOT nicht gefunden: $ROOT" >&2
  exit 2
fi

mag_count=$(find "$ROOT" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
issue_count=$(find "$ROOT" -type f -name "issue.json" | wc -l | tr -d ' ')
article_count=$(find "$ROOT" -type f -name "text.txt" | wc -l | tr -d ' ')

echo "Magazines: $mag_count" | tee -a "$SUMMARY_TXT"
echo "Issues   : $issue_count" | tee -a "$SUMMARY_TXT"
echo "Articles : $article_count" | tee -a "$SUMMARY_TXT"
echo | tee -a "$SUMMARY_TXT"

echo " Prüfe Issues auf fehlende Dateien/Ordner ..."
while IFS= read -r -d '' issue_json; do
  issue="$(dirname "$issue_json")"
  has_issue_json=1

  [[ -f "$issue/issue.json"   ]] || { echo "❌ fehlt issue.json   : $issue" >> "$ISSUES_LOG"; has_issue_json=0; }
  [[ -f "$issue/listing.json" ]] || echo "❌ fehlt listing.json : $issue" >> "$ISSUES_LOG"
  [[ -d "$issue/articles"     ]] || echo "❌ fehlt articles/    : $issue" >> "$ISSUES_LOG"

  if [[ $has_issue_json -eq 1 ]]; then
    if python - "$issue/issue.json" <<'PY' >/dev/null 2>&1
import json, sys
p = sys.argv[1]
with open(p, "r", encoding="utf-8") as f:
    obj = json.load(f)
sys.exit(0 if obj.get("issue_date_iso") == "0000-01-01" else 1)
PY
    then
      echo "⚠️  Platzhalter-Datum (0000-01-01): $issue" >> "$PLACEHOLDER_LOG"
    fi
  fi
done < <(find "$ROOT" -type f -name "issue.json" -path '*/issues/*' -print0)

echo " Prüfe Artikel auf fehlende meta.json/text.txt ..."
while IFS= read -r -d '' art; do
  [[ -f "$art/meta.json" ]] || echo "❌ fehlt meta.json : $art" >> "$ARTS_LOG"
  [[ -f "$art/text.txt"  ]] || echo "❌ fehlt text.txt  : $art" >> "$ARTS_LOG"
done < <(find "$ROOT" -type d -path '*/articles/*' -print0)

echo " Suche leere Magazine ..."
while IFS= read -r -d '' mag; do
  issues_dir="$mag/issues"
  if [[ -d "$issues_dir" ]]; then
    cnt=$(find "$issues_dir" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    if [[ "$cnt" = "0" ]]; then
      echo "0 Issues: $mag" >> "$EMPTY_MAGS_LOG"
    fi
  else
    echo "kein issues/: $mag" >> "$EMPTY_MAGS_LOG"
  fi
done < <(find "$ROOT" -mindepth 1 -maxdepth 1 -type d -print0)

issues_missing_count=$(wc -l < "$ISSUES_LOG" | tr -d ' ')
arts_missing_count=$(wc -l < "$ARTS_LOG" | tr -d ' ')
placeholders_count=$(wc -l < "$PLACEHOLDER_LOG" | tr -d ' ')
empty_mags_count=$(wc -l < "$EMPTY_MAGS_LOG" | tr -d ' ')

echo "=== SUMMARY =================================" | tee -a "$SUMMARY_TXT"
echo "❗ Issues mit fehlendem issue.json/listing.json/articles/: $issues_missing_count" | tee -a "$SUMMARY_TXT"
echo "❗ Artikel mit fehlender meta.json/text.txt:           $arts_missing_count" | tee -a "$SUMMARY_TXT"
echo "⚠️  Issues mit Platzhalter-Datum (0000-01-01):         $placeholders_count" | tee -a "$SUMMARY_TXT"
echo "⚠️  Leere/inkomplette Magazine:                        $empty_mags_count" | tee -a "$SUMMARY_TXT"

echo | tee -a "$SUMMARY_TXT"
echo "Starte Audit-Zusammenfassung ..." | tee -a "$SUMMARY_TXT"

python scripts/light/audit_corpus.py \
  --root "$ROOT" \
  --logs "$VALIDATION_LOGDIR" \
  --out "$AUDIT_CSV" \
  --problems-out "$AUDIT_PROBLEMS_CSV" \
  --problems-log "$AUDIT_PROBLEMS_LOG" | tee "$AUDIT_STDOUT_LOG"

audit_problem_count=$(python - "$AUDIT_PROBLEMS_CSV" <<'PY'
import csv, sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        print(sum(1 for _ in r))
except Exception:
    print(0)
PY
)

echo | tee -a "$SUMMARY_TXT"
echo "Audit-Ergebnisse:" | tee -a "$SUMMARY_TXT"
echo "- problematische Magazine: $audit_problem_count" | tee -a "$SUMMARY_TXT"
echo "- vollständige Audit-CSV: $AUDIT_CSV" | tee -a "$SUMMARY_TXT"
echo "- Problemfälle CSV:       $AUDIT_PROBLEMS_CSV" | tee -a "$SUMMARY_TXT"
echo "- Problemfälle Log:       $AUDIT_PROBLEMS_LOG" | tee -a "$SUMMARY_TXT"
echo "- Audit-Konsole:          $AUDIT_STDOUT_LOG" | tee -a "$SUMMARY_TXT"

echo | tee -a "$SUMMARY_TXT"
echo "Legende Audit:" | tee -a "$SUMMARY_TXT"
echo "- validator_status: OK / OK+WARN / FEHLER / N/A" | tee -a "$SUMMARY_TXT"
echo "- issues_zero_articles: Issues mit 0 Artikelordnern" | tee -a "$SUMMARY_TXT"
echo "- issues_missing_articles_dir: Issues ohne articles/-Ordner" | tee -a "$SUMMARY_TXT"
echo "- problem_reasons: konkrete Gründe für manuelle Sichtung" | tee -a "$SUMMARY_TXT"

echo "Logs unter: $LOGDIR" | tee -a "$SUMMARY_TXT"

if [[ "$issues_missing_count" -eq 0 && "$arts_missing_count" -eq 0 ]]; then
  echo "✅ Struktur OK."
  exit 0
else
  echo "❌ Struktur hat Lücken. Details in $LOGDIR/."
  exit 1
fi