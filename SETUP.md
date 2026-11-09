# Setup: from zero to three channels posting daily

Takes about an hour, once. After that, GitHub Actions runs everything every day. Your Codespace
doesn't need to be open.

## 1. Put the project on GitHub and open a Codespace
1. Create a new **private** GitHub repository, e.g. `shorts-studio`.
2. Upload this folder's contents (or `git push` them). Keep the `.github` and `.devcontainer` folders.
3. On the repo page: **Code → Codespaces → Create codespace**. It installs ffmpeg, Python packages
   and Claude Code automatically (first start takes a few minutes).

## 2. fal.ai (video + image generation)
1. Sign up at fal.ai, add credit (start with $20), and create an API key.
2. In the Codespace: `cp .env.example .env` and paste the key after `FAL_KEY=`.
3. On GitHub: **Settings → Secrets and variables → Actions → New repository secret**:
   name `FAL_KEY`, value = the key.

## 2b. Lightricks LTX API (the cheapest video route)
1. Sign up at ltx.io → developer / API section, add credit, create an API key.
2. Put it in `.env` as `LTX_API_KEY=...` and add a GitHub secret `LTX_API_KEY`.
3. That's it: videos now render on Lightricks' own API at 720p ($0.03 per second) instead of fal.ai at 1080p
   ($0.06). fal.ai is still used for the still images, and as an automatic backup if an LTX job fails.
   Prefer sharper video? Set the GitHub variable `LTX_MODEL` to `ltx-2-3-pro` ($0.04/s at 720p).

## 3. Google Cloud (YouTube upload permission)
1. Go to console.cloud.google.com, create a project (e.g. "Shorts Studio").
2. **APIs & Services → Library →** enable **YouTube Data API v3**.
3. **OAuth consent screen:** User type **External**, fill in the app name and your email.
   Then set Publishing status to **In production**. (In "Testing" mode Google expires your login
   every 7 days and the daily job would break.) Google shows an "unverified app" warning when you
   log in. That's expected for a personal app: click *Advanced → Go to (app)*.
4. **Credentials → Create credentials → OAuth client ID → Desktop app.** Then either:
   - **(easiest)** GitHub → your profile → **Settings → Codespaces → Secrets → New secret**: add
     `YT_CLIENT_ID` and `YT_CLIENT_SECRET` (give both access to this repo), then **restart the Codespace**
     so they load; or
   - download the JSON and upload it into the Codespace as `secrets/client_secret.json`.

## 4. Create the two YouTube channels
In YouTube: profile picture → **Settings → Add or manage your channels → Create a channel**.
Make three: *Flat 4B*, *Fridge Hearts* and *Drizzle & Pudge*. Then go to
**YouTube Studio → Settings → Channel → Advanced** on each and set the audience:
- Flat 4B and Fridge Hearts: **"No, it's not made for kids"**
- Drizzle & Pudge: **"Yes, set this channel as made for kids"** (required by law for content aimed at children;
  the pipeline also marks every Drizzle & Pudge upload as made for kids)

## 5. Connect each channel (once per channel)
```bash
python tools/auth_youtube.py all                                  # prints a login link per channel
python tools/auth_youtube.py flat4b "http://localhost:8765/?..."  # finish each one with the pasted URL
```
Open the link, **choose the matching channel** when Google asks, click Allow, then copy the
`http://localhost:8765/?...` address from your browser bar (the page itself may not load) and paste it.
The script confirms the channel name and prints a token. Add each one as a GitHub secret:
`YT_TOKEN_FLAT4B`, `YT_TOKEN_COLDHEARTS` and `YT_TOKEN_DRIZZLEPUDGE`.

## 5b. Facebook + Instagram Stories (optional)
Every new episode is also posted to each channel's Facebook Page story and Instagram story. API stories go live
for everyone straight away. Stories are capped at 60 s, so longer Fridge Hearts episodes post as 2 story frames cut between shots.
1. Meta Business Suite → Settings → Users → **System users**: assign the 3 Pages and 3 Instagram accounts to the
   system user (full control), then **Generate token** (never expires) with `pages_manage_posts`,
   `pages_read_engagement`, `pages_show_list`, `instagram_basic`, `instagram_content_publish`.
2. Put it in `.env` as `META_TOKEN=...` and as the GitHub secret `META_TOKEN`. Add the page/IG IDs
   (`FLAT_4B_FB_ID`, `FLAT_4B_IG_ID`, `FRIDGE_HEARTS_…`, `DRIZZLE_AND_PUDGE_…`) as GitHub variables.
3. `python -m pipeline.run check` shows every connection (YouTube, Facebook, Instagram, LTX, fal) for free.

## 6. Test for free, then for real
```bash
MOCK=1 python -m pipeline.run daily   # placeholder pictures, $0, checks the whole chain (results in output_mock/)

python -m pipeline.run refs flat4b                  # character reference images (~$0.04 each)
python -m pipeline.run refs coldhearts
python -m pipeline.run refs drizzlepudge
```
Open `assets/` and look at every character. Don't like one? Delete its PNG (and tweak its
`ref_prompt` in `channel.json` if you want), then rerun the command. **Commit `assets/` when you're
happy.** Every future video uses these images, so this is where the channel's look gets locked in.

```bash
python -m pipeline.run keyframes flat4b F4B-001     # stills only, ~$0.20: check composition
YT_UPLOAD=0 python -m pipeline.run daily            # one full episode per channel (~$7), no upload
```
Watch `output/*/*/final.mp4`. If it looks right: `git add -A && git commit -m "ready" && git push`.

## 7. Music (optional but recommended)
Download tracks from **YouTube Studio → Audio Library** into `music/` using the file names in
`music/README.md`, then commit them. Only use Audio Library or other properly licensed music.
A Content ID claim blocks a Short over 60 seconds worldwide.

## 8. Switch on autopilot
GitHub → **Actions** tab → enable workflows → open **Daily Shorts** → **Run workflow** once by hand.
After that it runs every day at 06:23 UTC on its own.

Optional settings (**Settings → Secrets and variables → Actions → Variables**):
| Variable | Default | Meaning |
|---|---|---|
| `REVIEW_HOURS` | 10 | Video uploads private and goes public after this many hours. Delete it in YouTube Studio before then if you don't like it. `0` = never auto-publish |
| `DAILY_BUDGET_USD` | 15 | Safety cap per run |
| `YT_UPLOAD` | 1 | `0` = render only |

### Weekly and monthly long videos (automatic)
- **Weekly (Sundays):** each channel gets a long 16:9 compilation as soon as its new episodes add up to
  8.5 minutes (YouTube only allows mid-video ads from 8 minutes). Fridge Hearts qualifies every week; Flat 4B
  and Drizzle & Pudge roughly every two weeks.
- **Monthly (1st of the month):** a bigger "marathon" of all the month's episodes (*Season 1* when it covers 1-30).
Both have chapter timestamps and upload the same way as the Shorts. Switch either off per channel in its
`channel.json`: `"compilations": {"weekly": true, "monthly": false}`. Change the weekly threshold with the
GitHub variable `WEEKLY_MIN_SECONDS` (default 510). Long videos earn far more per view than Shorts.
Nothing to set up: the daily job already keeps a copy of each episode in a GitHub Release called
`episodes-<channel>` (Releases are free storage; don't delete them). Want one sooner? Actions → Weekly (or Monthly)
compilation → Run workflow, or locally `python -m pipeline.run compile coldhearts 1 30`.

### About the kids channel
Made-for-kids videos have comments, notifications and personalised ads switched off, so they earn less per
view. YouTube also demonetises kids channels that are low-quality, so the scripts follow YouTube's quality
principles (kind, playful, a little learning, nothing unsafe to copy). Long compilations (the monthly job)
are the biggest earner for kids cartoons because children rewatch them. Want to run only some channels?
Set the GitHub variable `CHANNELS`, e.g. `flat4b,drizzlepudge`.

## 9. Important: the YouTube API audit
Google keeps every video uploaded through a **new, unaudited** API project **private**, whatever the
code asks for. Until your project passes the free YouTube API compliance audit:
- the pipeline still renders and uploads every day, and the videos land in YouTube Studio as private;
- you publish them yourself (Studio → Content → Visibility → Public), which takes a few seconds per video
  and doubles as your quality check.

Apply by filling in Google's **"YouTube API Services – Audit and Quota Extension Form"** (search that name).
Describe it honestly: an internal tool that uploads your own original animated Shorts to your own channels.
Once approved, `REVIEW_HOURS` auto-publishing works with no manual step.

## 10. New scripts when the 30 run out
The daily job opens a GitHub issue "Write next script batch" when fewer than 7 scripts are left. Either:
- open the Codespace, run `claude`, and say **"write the next batch"** (CLAUDE.md tells it how), or
- add an `ANTHROPIC_API_KEY` repository secret (recommended), and the daily **Write next script batch** workflow
  does it automatically: each channel is refilled with 15 new episodes whenever it drops below 7, forever.
  If a run fails it retries the next day and opens a "Script writer failed" issue.

## Costs at 2 videos/day
| Item | Approx. |
|---|---|
| | LTX API 720p (default) | fal.ai 1080p (backup) |
|---|---|---|
| Flat 4B episode (~36 s video + 5 keyframes) | ~$1.30 | ~$2.40 |
| Fridge Hearts episode (~71 s video + 8 keyframes) | ~$2.45 | ~$4.60 |
| Drizzle & Pudge episode (~39 s video + 5 keyframes) | ~$1.35 | ~$2.55 |
| Per day (all three) | ~$5.10 | ~$9.50 |
| Per month (incl. ~30% retakes) | **~$190** | ~$340–370 |
| GitHub Actions | free tier is usually enough (~15–30 min per day) |

Defaults (cheapest tested): LTX API `ltx-2-3-fast` at 720p ($0.03/s) for video, fal `ltx-2-19b/distilled` (~$0.02/s) as the video fallback, `flux-2/flash/edit` (~$0.015) for keyframes, `nano-banana` once per character for reference images.
To switch model, set `VIDEO_I2V` (and `PRICE_PER_VIDEO_SECOND`) in `.env` and as GitHub Actions variables. Prices change, so check fal.ai model pages occasionally.

## 11. Ask The Elders (free Google Flow channel)

1. Create the YouTube channel (name **Ask The Elders**, handle e.g. @AskTheEldersTV), category People & Blogs.
2. Connect it: `python tools/auth_youtube.py elders`, then add the token as the GitHub secret **YT_TOKEN_ELDERS**.
3. If you set a repository variable `CHANNELS`, add `elders` to it (weekly/monthly compilations).
4. Facebook + Instagram Stories: put the Page and Instagram IDs in `.env` as `FB_ID_ELDERS` / `IG_ID_ELDERS` (or `ELDERS_FB_ID` / `ELDERS_IG_ID`) and add the same names as GitHub secrets, or put both ids in the secret `FACEBOOK_INSTAGRAM_PAGE_IDS_ELDERS` (any form: `FB_ID=.. IG_ID=..`, `Facebook: .. Instagram: ..`, or two numbers, Facebook first). The shared `META_TOKEN` posts to them after each flow import.
4. Actions tab → **Flow prompts (Google Flow channels)** → Run workflow. An issue with 5 prompts appears.
5. Daily, on your phone (about 5 minutes, before 14:00 UK time):
   - Open labs.google/flow → New project → model **Veo 3.1 Lite**, aspect **9:16**, outputs **1**.
   - Paste prompt 1 → generate → download. Repeat for 2–5 (5 × 10 credits = your free 50).
   - Rename the files 1.mp4 … 5.mp4 if you can (or upload them one at a time in order).
   - github.com → your repo → `inbox/elders` → Add file → Upload files → Commit.
   - The Short is assembled and scheduled automatically; the issue closes with the YouTube link.
6. If a clip comes out wrong (bad face, wrong words), just regenerate it in Flow before uploading.
Note: free Flow clips carry a visible "Made with Veo" watermark. Don't crop it out.

## 11b. The Crib Committee (second free Google Flow channel)

Same daily routine as Ask The Elders, with its own issue (label `flow-cribcommittee`) and inbox `inbox/cribcommittee/`.
Use a **different Google account** in Flow so each channel gets its own 50 free credits.
1. Create the YouTube channel: name **The Crib Committee**, handle **@TheCribCommittee**, category People & Blogs,
   audience **"No, it's not made for kids"** (it's for parents).
2. Connect it: `python tools/auth_youtube.py cribcommittee`, then add the token as the GitHub secret **YT_TOKEN_CRIBCOMMITTEE** (or **YT_TOKEN_CRIB**).
3. If you set a repository variable `CHANNELS`, add `cribcommittee` to it.
4. Optional music in `music/`: playful-pizzicato.mp3, boardroom-jazz.mp3, gentle-music-box.mp3, light-marimba.mp3.
5. Publishes `review_hours` (11, in channel.json) after upload, about 1 hour after Ask The Elders.
6. Facebook/Instagram Stories (optional): `CRIBCOMMITTEE_FB_ID` / `CRIBCOMMITTEE_IG_ID` like section 11, or put both ids in the
   secret `FACEBOOK_INSTAGRAM_PAGE_IDS_CRIB` (any form: `FB_ID=.. IG_ID=..`, `Facebook: .. Instagram: ..`, or two numbers, Facebook first).

## 12. TikTok (manual posting)

TikTok's posting API needs an app review, so TikTok is posted by hand. The pipeline keeps every finished video
(with hook text and captions) plus a paste-ready caption, forever, in one GitHub Release per channel:
`tiktok-flat4b`, `tiktok-coldhearts`, `tiktok-drizzlepudge`, `tiktok-elders`, `tiktok-cribcommittee`
(github.com/leverageonheroes/Daily-Video-/releases).

Phone links (repo is public, no login needed; bookmark them):
- Elders: https://github.com/leverageonheroes/Daily-Video-/releases/tag/tiktok-elders
- Crib Committee: https://github.com/leverageonheroes/Daily-Video-/releases/tag/tiktok-cribcommittee
- Direct download: `https://github.com/leverageonheroes/Daily-Video-/releases/download/tiktok-<channel>/<ID>.mp4`
  (e.g. `.../tiktok-elders/ELD-003.mp4`, `.../tiktok-cribcommittee/CC-002.mp4`). If it plays instead of
  downloading, long-press the link → "Download link".

Daily, on your phone: open the release → tap `<ID>.mp4` to download → open `<ID>.txt` and copy the caption →
TikTok app → + → Upload → paste caption → **More options → switch ON "AI-generated content"** → Post.
Leave the "Made with Veo" watermark on Elders clips. Drizzle & Pudge is made for under-7s and TikTok is 13+,
so expect it to be restricted there.

## 13. One In A Thousand (replaces Flat 4B on the same YouTube channel)

1. YouTube Studio → Customisation: rename the channel to **One In A Thousand**, new handle (e.g.
   @OneInAThousandTV), new description, new logo (`logos/OneInAThousand_logo_800x800.png`). Category: Education.
   Same login, so the existing YT_TOKEN_FLAT4B secret keeps working. Nothing to reconnect.
2. The narrator voice uses your existing FAL_KEY (about $0.03-0.05 per Short).
3. Music (optional): add epic-nature-strings.mp3, tense-drums.mp3, tragic-piano.mp3, hopeful-swell.mp3 to music/.
4. Cost: about $2.20-2.40 per 64 s Short on LTX 720p (video $1.92 + images $0.30 + narrator $0.04).
