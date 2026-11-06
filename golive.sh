#!/usr/bin/env bash
# Go live: check every connection, push the code, start today's runs on GitHub Actions.
set -e
python tools/validate.py | tail -1 | grep -q "RESULT: OK" || { echo "validate.py failed"; exit 1; }
python -m pipeline.run check
git push
gh workflow run "Flow prompts (Ask The Elders)"   # today's 5 Flow prompts -> issue + inbox/elders/PROMPTS.md
gh workflow run "Daily Shorts"                    # render + upload channels 1-3 (+ FB/IG Stories)
echo "Started. Watch: gh run list --limit 5"
