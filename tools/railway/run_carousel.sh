#!/usr/bin/env bash
# Daily carousel run on Railway. Needs env: GH_TOKEN (fine-grained PAT, Contents read/write on the repo),
# GIT_REPO (owner/name), YT_TOKEN_ELDERS, YT_TOKEN_CRIBCOMMITTEE, CF_ACCOUNT_ID, CF_API_TOKEN
# Facebook/Instagram (optional): META_TOKEN_FACEBOOK_INSTAGRAM (or META_TOKEN), FACEBOOK_INSTAGRAM_PAGE_IDS_ELDERS,
# FACEBOOK_INSTAGRAM_PAGE_IDS_CRIB (same values as the GitHub secrets)
# Optional: TOGETHER_API_KEY, POLLINATIONS_TOKEN, GEMINI_API_KEY, IMAGE_PROVIDERS, CAROUSEL_CHANNELS, YT_UPLOAD=0
set -uo pipefail
: "${GH_TOKEN:?set GH_TOKEN}" "${GIT_REPO:?set GIT_REPO (owner/name)}"
BRANCH="${GIT_BRANCH:-main}"
rm -rf /tmp/repo
git clone --depth 30 --branch "$BRANCH" "https://x-access-token:${GH_TOKEN}@github.com/${GIT_REPO}.git" /tmp/repo || exit 1
cd /tmp/repo
git config user.name "shorts-bot"
git config user.email "shorts-bot@users.noreply.github.com"
status=0
python -m pipeline.run carousel ${CAROUSEL_CHANNELS:+${CAROUSEL_CHANNELS//,/ }} || status=$?
git add state/carousel.json 2>/dev/null
if ! git diff --cached --quiet; then
  git commit -m "carousel: $(date -u +%F)"
  for i in 1 2 3 4; do
    git pull --rebase && git push && break
    sleep $((i * 5))
  done
fi
exit $status
