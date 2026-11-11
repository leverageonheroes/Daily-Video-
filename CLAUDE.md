# Shorts Studio — instructions for Claude Code

This repo runs five YouTube Shorts channels (three rendered by paid APIs, two from free Google Flow clips). Read this file first in every session.
Everything you need to resume is on disk: never rely on chat memory.

| Channel | Folder | Show | Format |
|---|---|---|---|
| 1 | `channels/flat4b/` | **One In A Thousand** (was Flat 4B; old scripts in `archive/`) — true survival stories of creatures and cells | Narrated cinematic explainer, 7 shots = 64 s, one narrator voice (pipeline/narration.py) |
| 2 | `channels/coldhearts/` | **Fridge Hearts** (folder still `coldhearts`) — a soap opera inside a fridge | Melodramatic micro-soap, 60–85 s, flash-forward cold open + cliffhanger + TO BE CONTINUED card |
| 3 | `channels/drizzlepudge/` | **Drizzle & Pudge** — a baby rain cloud and her hedgehog best friend | Wordless kids cartoon, 30–45 s, ends with the Puddle Jump |
| 4 | `channels/elders/` | **Ask The Elders** — realistic AI elders, one life lesson each | 8 elders × 8 s = 64 s, one theme per Short (2 Flow accounts). **Google Flow channel** (see below) |
| 5 | `channels/cribcommittee/` | **The Crib Committee** — babies hold a meeting about parenting | 8 babies × 8 s = 64 s, one topic per Short (2 Flow accounts). **Google Flow channel** (see below) |

Channels 1–2, 4 and 5 are **general audience, NOT "made for kids"**. Keep humour clean (no swearing,
sexual content, gore, cruelty, real brands, real people, or copyrighted characters).
Channel 3 is **MADE FOR KIDS** (ages 2–7): `made_for_kids: true` in its channel.json sets it on every upload.

## Resume checklist (do this at the start of every session)

1. `python tools/state.py status` — shows what is scripted / rendered / uploaded / published.
2. If it prints `ACTION NEEDED` for a channel → write the next script batch (section below).
3. `python tools/validate.py` must print `RESULT: OK` before anything is rendered.
4. Production is automated: `python -m pipeline.run daily` (GitHub Actions runs it every day) renders
   the next episode per channel and uploads it. Statuses: scripted → rendered → uploaded → published (or failed).
   Test for free with `MOCK=1 python -m pipeline.run daily` (writes to output_mock/, never touches real state).
   Human setup steps live in SETUP.md. Each rendered episode also gets a clean copy (no hook text) stored in
   the GitHub Release `episodes-<channel>`; `python -m pipeline.run weekly` (Sundays) compiles a channel once its
   episodes after `last_compiled_weekly` reach 8.5 min; `monthly` (1st) compiles everything after `last_compiled`.
   Both make long 16:9 videos with chapters; toggles live in channel.json `compilations`.
   Every finished Short + a TikTok caption is also kept in Release `tiktok-<channel>` for manual TikTok posting (SETUP.md §12).

## File layout

```
channels/<channel>/channel.json        # bible: style prompt, characters, locations, lore
channels/<channel>/episodes/eps_NNN-MMM.json   # scripts, 15 episodes per file
state/state.json                       # production state (written by tools/state.py only)
assets/<channel>/<character>.png       # one reference image per character (generate once, reuse forever)
output/<channel>/<episode_id>/         # keyframes, clips, final.mp4, metadata.json (cached: reruns never pay twice)
pipeline/                              # config, prompts, fal.ai calls, ffmpeg assembly, YouTube upload, CLI
```

## Episode format (one object inside `{"episodes": [...]}`)

```json
{
  "id": "F4B-031", "number": 31,
  "title": "YouTube title, <= 90 chars, ends with #shorts",
  "logline": "One sentence premise - must be different from every earlier logline",
  "hook_text": "On-screen text for the first 2 seconds (<= 45 chars)",
  "description": "1-2 sentence YouTube description",
  "tags": ["...", "..."],
  "music": "one of channel.json music_moods",
  "guests": {"guest_id": {"name": "...", "ref_prompt": "...", "voice": "..."}},
  "shots": [
    {"n": 1, "dur": 6, "loc": "kitchen", "chars": ["dougie", "margo"],
     "keyframe": "what the FIRST frame looks like (composition, poses, expressions)",
     "action": "what moves/happens during the clip",
     "camera": "framing and movement",
     "lines": [{"c": "dougie", "t": "Spoken line.", "tone": "excited"}],
     "sfx": "sound effects"}
  ],
  "loop_note": "how the last frame connects back to the first"
}
```

Hard rules (enforced by `tools/validate.py`):
- `dur` is 6, 8 or 10 seconds (every recommended video model supports these lengths).
- Dialogue ≤ 2.6 words per second of shot (≤ 15 words in 6 s, ≤ 20 in 8 s, ≤ 26 in 10 s).
- Total ≤ 90 s. Flat 4B target 30–50 s, Fridge Hearts target 60–85 s.
- Every speaker must be in that shot's `chars`; every char/loc must exist in channel.json or `guests`.
- Channels with `"nonverbal": true` must have empty `lines`.
- Max 2 speaking characters per shot (video models lip-sync two faces reliably, not three).
- Episode numbers continuous; ids `OIT-NNN` (was `F4B-NNN`) / `CH-NNN`.

## Writing the next batch (when status says ACTION NEEDED)

1. Read `channel.json` and ALL existing loglines for that channel (titles + loglines only, to save context):
   `python -c "import json,glob;[print(e['id'],e['logline']) for f in sorted(glob.glob('channels/<ch>/episodes/*.json')) for e in json.load(open(f))['episodes']]"`
2. Write 15 new episodes into a new file `eps_<first>-<last>.json` continuing the numbering.
3. Uniqueness: no premise, punchline or cliffhanger may repeat an earlier one. Vary locations,
   character pairings and music moods. Rotate the lead character every episode.
4. One In A Thousand: see its section at the end (generator script, not hand-written JSON).
   (Archived Flat 4B rule:) one relatable adult-life situation (work, money, flat-sharing, dating, gym, admin),
   escalation, a twist punchline in the final shot, and a last frame that loops to the first.
5b. Drizzle & Pudge: NO dialogue (`lines` always empty; giggles/gasps/hiccups go in `sfx`). Drizzle's surprise
   rain (bubbles, petals, colours, snow...) causes a small problem, friends fix it kindly, one gentle good thing is
   modelled (sharing, helping, trying again, sorry, counting, colours, shapes), and the LAST shot is always the
   6-second Puddle Jump. Obey every rule in `kids_safety_rules` (nothing unsafe a child could copy, nobody left
   sad or scared, no products). Titles are honest, not clickbait. Rotate locations and which friend stars.
5. Fridge Hearts: open on the most dramatic line, 3–4 beats of melodrama played straight,
   end on a cliffhanger. Each episode must make sense to a first-time viewer.
   Keep the running arc moving (see the last 5 loglines) and introduce at most one guest per episode.
6. Run `python tools/validate.py` and fix every ERROR (and most WARNs). Then `python tools/state.py sync`.
7. Commit: `git add -A && git commit -m "scripts: <channel> <first>-<last>"`.

## How a shot becomes video (implemented in pipeline/ — prompts live in pipeline/prompts.py)

Video provider: `VIDEO_PROVIDER=ltx` (Lightricks API, pipeline/ltx_api.py, 720x1280) with automatic fallback to fal.ai
(pipeline/fal_api.py). Still images always come from fal.ai.


1. **Reference images (once):** for each character, generate `assets/<ch>/<char>.png` from
   `style_prompt + ref_prompt` on a plain background. Reuse forever → consistent faces.
2. **Keyframe image (per shot):** image model with the reference images of `chars` as inputs;
   prompt = `style_prompt` + location description + `keyframe`.
3. **Clip (per shot):** image-to-video with the keyframe as first frame; prompt =
   `action` + `camera` + each line formatted `Name (tone, voice description): "text"` + `sfx` + `audio_prompt`.
   Request duration `dur`, aspect 9:16.
4. **Assemble (ffmpeg):** concat clips → hook_text overlay 0–2 s → burned captions from the script lines
   (no transcription needed) → music bed for `music` mood at -20 dB under dialogue → loudness -14 LUFS →
   1080×1920, 30 fps, H.264.
5. **Upload:** title, description (+ "Made with AI-generated animation."), tags; `selfDeclaredMadeForKids=false`;
   `containsSyntheticMedia=true`; uploaded **private** with `publishAt` = now + REVIEW_HOURS (→ `uploaded`).
   `sync-youtube` marks it `published` once YouTube shows it public.

If a clip comes back broken (wrong character, garbled mouth), retry that shot once with a new seed,
then mark the episode `failed` with a note instead of publishing a bad video.

## Google Flow channel: Ask The Elders (`"source": "flow"` in channel.json)

No paid API is ever called for this channel; `daily` skips it. The human makes the clips with the free
50 daily Google Flow credits per Google account (5 × Veo 3.1 Lite, 8 s, 9:16, 1 output per prompt).
Each Flow channel uses TWO accounts (channel.json `flow.accounts`): clips 1-5 on the first, 6-8 on the second,
so 8 clips = 64 s (over one minute, which TikTok's Creator Rewards require). PROMPTS.md labels each clip with its account.
Episodes made before the switch (ELD-001..003, CC-001..002) keep their original 5-clip scripts.

1. `flow-prompts.yml` (05:41 UTC) runs `python -m pipeline.run flow-prompts` → `inbox/elders/PROMPTS.md`
   and a GitHub issue labelled `flow-clips` with the 8 prompts.
2. The human uploads the 8 clips to `inbox/elders/` (named 1–8, or one at a time in order).
3. `flow-import.yml` runs on every upload: `python -m pipeline.run flow-import` waits until all of the episode's clips exist,
   orders them (file-name number > git upload order > alphabetical), assembles with captions/hook/music,
   stores clean.mp4 in Releases, uploads (secret `YT_TOKEN_ELDERS`), deletes the clips, closes the issue.
4. Weekly/monthly compilations include it like any other channel.

End card: every Ask The Elders Short ends with a 4 s card (`end_card` in channel.json → `assets/elders/endcard.png`,
appended in pipeline/assemble.py to final.mp4 only, not clean.mp4/compilations). To change its text, colours or logo
(`assets/elders/logo.png`), edit channel.json then run `pip install pillow && python tools/make_endcard.py elders` and commit the PNG.

Writing the next Ask The Elders batch: edit/extend `tools/generators/build_elders_001-030.py` (copy it to
`build_elders_031-060.py`): every line ≤ 18 words, line 1 states the age ("I'm {age}. ...") and promises the
theme, lines 2-7 are six lessons, line 8 is the emotional closer, 8 different elders per episode, original lines (no famous quotes),
no specific investment/medical/legal advice. Every shot needs a `flow_prompt` that contains the exact spoken
line (the validator checks this, because captions are burned from `lines`). Never name the elders or claim
they are real people.

## Google Flow channel 2: The Crib Committee (`channels/cribcommittee/`)

Works exactly like Ask The Elders (same flow-prompts / flow-import workflows; its own issue labelled
`flow-cribcommittee`, inbox `inbox/cribcommittee/`, secret `YT_TOKEN_CRIBCOMMITTEE`, end card from
`assets/cribcommittee/logo.png`). It publishes `review_hours` (channel.json, 11 h) after upload, about 1 h after Elders.
Each Short: 8 different babies (never named): Chair (tiny tie + reading glasses) opens the meeting,
six members make one wish each (sassy / wise / dramatic tones), then the Closer ends "Motion carried." while a newborn reacts (burp,
hiccup, sneeze...). Kind humour, mainstream evidence-based parenting ideas, no products or medical advice.

Writing the next batch: copy `tools/generators/build_cribcommittee_001-030.py` to `build_cribcommittee_031-060.py`
(8 clips, each line ≤ 18 words; readable copy of the scripts in `channels/cribcommittee/scripts_001-030.md`),
run it, then validate + `state.py sync`.

WARNING (both Flow channels): do NOT re-run the `_001-030` generators. They rewrite channel.json (dropping
`end_card` and the old crib characters) and the episode files (replacing the kept 5-clip ELD-001..003 / CC-001..002).
New-batch generators must write only their own new episode file, not channel.json.

## One In A Thousand (channels/flat4b, ids OIT-NNN)

Generator: `tools/generators/build_oneinathousand_001-030.py` (copy to `_031-060.py` for the next batch).
- 7 shots, durations 6/10/10/10/10/10/8 = 64 s. Each shot: `narration` (<= 2.4 words/s), `lines: []`.
- Arc: shock hook (stat + action, <= 14 words) -> escalating threats -> explainer mid-chase -> heartbreak ->
  triumph -> last line loops to the start / next generation.
- Facts: mainstream biology only, hedged numbers, a `fact_note` per episode goes in the description. No fake
  rescues, no talking animals, no gore (deaths off-screen).
- Creatures are episode `guests` and places are episode `locations`, ids prefixed `oitNNN_` (so reference
  images never collide). Narrator: channel.json `narrator` (ElevenLabs Turbo v2.5 via fal, voice "George",
  Kokoro "bm_george" fallback). Clip audio is kept at 45% under the narrator.
- When scripts are replaced with a new id prefix, `state.sync` moves the old records to `archived` and
  restarts the compilation trackers (old values kept in `archived_trackers`).

## Fridge Hearts drama engine (channels/coldhearts)

`channel.json` `cold_open` takes the first 3.5 s of the LAST shot (desaturated, white flash cut) as a
flash-forward, then a card ("12 HOURS EARLIER..."), then the story; `end_card` (a text string here) shows
"TO BE CONTINUED..." for the last 1.9 s. clean.mp4 (compilations) has neither. Per-episode override:
`"cold_open": {"shot": 6, "start": 0, "seconds": 4}` or `false`. Writing rules: see `drama_rules` in
channel.json. Above all, the last shot must open on its most shocking beat.
`end_card` in channel.json is either a text string (drawn as a caption, Fridge Hearts) or an object with an
image (a 4 s still appended to final.mp4, Elders / Crib Committee); pipeline/assemble.py handles both.

## Daily carousel videos (second daily Short for elders + cribcommittee)

`python -m pipeline.run carousel [ch]` makes a 66 s vertical video: 8 AI images (free FLUX via Cloudflare
Workers AI, fallbacks Together AI / Pollinations: pipeline/images.py) full-screen with Ken Burns and soft
crossfades, the day's 8 lines scrolling up OVER the images inside the Shorts safe zone (y 380-1240: the bottom ~35%
is hidden by YouTube's title/buttons), music from music/ (moods in carousel.json; `calm-piano` / `gentle-lullaby`
are our own synthesised tracks from tools/make_music.py, replace with Audio Library tracks of the same name any time),
and a hook card for the last 8 s. Content: `channels/<ch>/carousel.json` (look, image prompt pools, 30 episodes), written by
`tools/generators/build_carousel_content.py`. Progress: `state/carousel.json` (only the carousel writes it).
Uploads private with a fixed `publishAt` (carousel.json `publish_local`, Europe/London): Elders 13:30, Crib 14:30.
Runs daily on GitHub Actions ("Carousel" workflow, cron 05:17 UTC; moved off Railway 2026-11-11, tools/railway/ is
unused). A channel that already uploaded a carousel today (UTC) is skipped, except catch-up runs (YT_PUBLISH_NOW=1). Next batch: append 30 new episodes (8 new lines + hook, never
repeating a line from the main scripts or earlier carousels) and run tools/validate.py.
