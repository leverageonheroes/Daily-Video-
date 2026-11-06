#!/usr/bin/env bash
# Go live: check every connection, push the code, start today's runs on GitHub Actions.
set -e
python tools/validate.py | tail -1 | grep -q "RESULT: OK" || { echo "validate.py failed"; exit 1; }
python -m pipeline.run check
git push
URL=https://github.com/leverageonheroes/Daily-Video-/actions/workflows
for wf in flow-prompts.yml daily.yml; do   # Elders prompts, then channels 1-3 render + upload (+ FB/IG Stories)
  env -u GITHUB_TOKEN gh workflow run "$wf" 2>/dev/null && echo "started $wf" \
    || echo "could not start $wf from here (Codespace token) -> open $URL/$wf and click 'Run workflow'"
done
