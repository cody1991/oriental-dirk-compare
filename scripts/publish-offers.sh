#!/usr/bin/env bash
# Refresh offers, commit data, push origin/main, and verify the public GitHub Pages copy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PAGE_URL="https://cody1991.github.io/oriental-dirk-compare/"
DATA_URL="https://cody1991.github.io/oriental-dirk-compare/data/offers.json"

# Close-reminder markers live at the repo root as .ao-close-reminder-sent-YYYY-MM-DD.
# This script never deletes them, and does not stage them during a data refresh.

python3 scripts/refresh-offers.py

# This dashboard is static HTML/JSON; no separate build step.

generated_at="$(python3 -c 'import json; print(json.load(open("data/offers.json"))["generatedAt"])')"
data_date="$(python3 -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Europe/Amsterdam")).date().isoformat())')"

# Stage only refresh/publish artefacts. Do not add node_modules, caches, or reminder markers.
paths=()
for path in \
  data/offers.json \
  data/translations.json \
  scripts/refresh-offers.py \
  scripts/publish-offers.sh \
  scripts/build_offers.py \
  README.md \
  app.js \
  index.html \
  styles.css \
  .gitignore
do
  if [[ -e "$path" ]]; then
    paths+=("$path")
  fi
done

git add -- "${paths[@]}"

if git diff --cached --quiet; then
  echo "No staged changes to publish. Checking the live page anyway."
else
  git commit -m "Refresh Amazing Oriental offers for ${data_date}"
  git push origin main
fi

expected="$generated_at"
ok=0
page_code=""
data_code=""
live_generated=""
# GitHub Pages can lag briefly after a push.
for attempt in $(seq 1 24); do
  stamp="$(date +%s)"
  page_code="$(curl -sS -o /tmp/ao-live-page.html -w "%{http_code}" --max-time 30 "${PAGE_URL}?t=${stamp}")"
  data_code="$(curl -sS -o /tmp/ao-live-offers.json -w "%{http_code}" --max-time 30 -H "Cache-Control: no-cache" "${DATA_URL}?t=${stamp}")"
  if [[ "$data_code" == "200" ]]; then
    live_generated="$(python3 -c 'import json; print(json.load(open("/tmp/ao-live-offers.json")).get("generatedAt",""))' 2>/dev/null || true)"
  else
    live_generated=""
  fi
  echo "verify attempt ${attempt}/24: page=${page_code} data=${data_code} liveGeneratedAt=${live_generated:-?} expected=${expected}"
  if [[ "$page_code" == "200" && "$data_code" == "200" && "$live_generated" == "$expected" ]]; then
    ok=1
    break
  fi
  sleep 10
done

if [[ "$ok" -ne 1 ]]; then
  echo "Public page check failed. page=${page_code} data=${data_code} liveGeneratedAt=${live_generated:-?} expected=${expected}" >&2
  exit 1
fi

echo "Public page ok: ${PAGE_URL} and ${DATA_URL} returned HTTP 200 with generatedAt=${expected}"
