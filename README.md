# Shorts Studio

Three YouTube Shorts channels on autopilot: scripts → AI keyframes → AI video with voices → captions + music → YouTube, every day.

- **New here? Follow `SETUP.md`** (about an hour, once).
- **Claude Code reads `CLAUDE.md`** to resume work and write new script batches.

| | Flat 4B | Fridge Hearts | Drizzle & Pudge |
|---|---|---|---|
| Premise | Four animal flatmates in a tiny London flat | A soap opera inside a fridge | A baby rain cloud and her hedgehog best friend |
| Format | Standalone gag, punchline ending, loops | Micro-soap, cliffhanger ending | Wordless kids cartoon, ends with the Puddle Jump |
| Episodes ready | 30 | 30 | 30 |
| Length | 34–38 s | 70–72 s | 38–40 s |
| Audience | General, not made for kids | General, not made for kids | **Made for kids** (2–7) |

## How it works

```
GitHub Actions (daily 06:23 UTC)
  └─ python -m pipeline.run daily
       ├─ next script from state/state.json
       ├─ character reference images (made once, stored in assets/)
       ├─ per shot: keyframe  ← fal-ai/nano-banana/edit (uses the reference images → consistent characters)
       ├─ per shot: video+voice ← LTX API ltx-2-3-fast 720x1280 (fal.ai as backup), 6/8/10 s, native audio
       ├─ ffmpeg: join shots, hook text, captions, music bed, -14 LUFS → 1080×1920 final.mp4
       ├─ YouTube upload: private, auto-publish after REVIEW_HOURS, not-for-kids, AI-content flag
       ├─ keeps a copy of each episode in a GitHub Release (free storage)
       └─ commits progress back to the repo; opens an issue when scripts run low

GitHub Actions (Sundays)            GitHub Actions (1st of each month)
  └─ pipeline.run weekly              └─ pipeline.run monthly
       └─ per channel, once 8.5+ min of new episodes      └─ all of the month's episodes ("marathon")
          → long 16:9 video (blurred sides + chapters) → YouTube
```

## Commands

```bash
python tools/validate.py                      # check all scripts
python tools/state.py status                  # progress per channel
MOCK=1 python -m pipeline.run daily           # free end-to-end test with placeholders
python -m pipeline.run refs flat4b            # make/check character reference images
python -m pipeline.run keyframes flat4b F4B-001   # cheap still-frame preview
python -m pipeline.run render flat4b F4B-001  # full render, no upload
python -m pipeline.run upload flat4b F4B-001
python -m pipeline.run daily                  # what the scheduler runs
python -m pipeline.run compile coldhearts 1 30   # long video from a range of episodes
python -m pipeline.run weekly                 # compile channels with 8.5+ min of new episodes + upload
python -m pipeline.run monthly                # compile the month's episodes + upload
```

## Cost (pay per use)

Video renders on **Lightricks' own LTX API: LTX-2.3 Fast at 720×1280, $0.03 per second** (audio included),
with fal.ai ($0.06/s at 1080p) as an automatic backup. Keyframe images use fal.ai nano-banana (~$0.04 each).
All three channels: **~$5/day, ~$190/month** with retakes. Switch with `VIDEO_PROVIDER` (`ltx`/`fal`) and
`LTX_MODEL` (`ltx-2-3-fast`/`ltx-2-3-pro`).

## Folder map

```
CLAUDE.md, SETUP.md            instructions (Claude Code / you)
channels/<ch>/channel.json     bible: style, characters, locations
channels/<ch>/episodes/*.json  scripts
pipeline/                      the production code
tools/                         validate.py, state.py, auth_youtube.py
assets/                        character reference images (commit these!)
music/                         mood tracks from YouTube Audio Library
state/state.json               progress (written by the pipeline)
.github/workflows/             daily.yml, weekly.yml + monthly.yml (compilations), scripts.yml (daily auto-writing of new script batches)
```
