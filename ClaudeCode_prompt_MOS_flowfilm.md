# Paste into Claude Code: Moral Of The Story TV, "flow-film" format

I uploaded `MOS-001_flowfilm.json` to the repo root. It replaces `MOS-001_fix.json` and `MOS-001_scenes.json` (delete both).

## The new strategy
- **I make the clips by hand in Google Flow** (free, Veo 3.1 Lite, Frames to Video) from start frames the pipeline makes.
- **The pipeline does everything else:** fixed character voices, lip-sync onto the one visible speaker, and a film-style edit.
- **Target:** about $1 per episode, about 77 s, faces consistent, the right person speaking, and the same voice per character in every part.

## Rules
- I'm on a PHONE. Send short messages, give numbered choices, and do one step at a time.
- No paid API calls until I type **"go ahead"** for that stage.
- Never commit `.env`, keys, tokens or zips. Never print a key.
- Add this as a new episode format, `"format": "flow-film"`. Ask The Elders, The Crib Committee, Hard Truths, One In A Thousand and Fridge Hearts must keep working exactly as now. Run their mock tests at the end to prove it.
- Reuse what exists: `pipeline/flow.py` (prompts, issues, inbox, import), the keyframe and reference code in `generate.py`, `narration.py` (fal ElevenLabs), the lip-sync code in `hardtruths.py`, and `assemble.py` (grade, cards, recap, freeze, end card, captions) and `compile.py` (arc movie).
- Explain any fix to existing code in one line.
- Keep `"paused": true` on drizzlepudge, so nothing goes to YouTube until I approve Episode 1.

---

## 1. Data
1. Install MOS-001 from the JSON:
   - Keep the existing MOS-001 metadata: title, hook_text, part_label, end_card, captions, description, tags, arc fields.
   - Replace its `shots` with `format`, `voices`, `scenes`, `clips`, `edit` and `accounts`.
2. Update `channel.json` (drizzlepudge):
   - `"source": "flow"`
   - `"flow": {"model": "Veo 3.1 Lite", "mode": "Frames to Video", "aspect": "9:16", "clip_seconds": 8, "outputs_per_prompt": 1, "daily_free_credits": 50, "credits_per_clip": 10, "accounts": ["MOS-A", "MOS-B", "MOS-C"]}`
   - `"cast_voices": {}` (filled in step 3)
   - `"lipsync": {"endpoint": "fal-ai/kling-video/lipsync/audio-to-video", "fallbacks": ["fal-ai/sync-lipsync/v2", "fal-ai/latentsync"]}`
   - grain `noise=alls=3`, plus `unsharp=5:5:0.6` after `eq`.
3. Update `tools/validate.py` for flow-film. It must check:
   - exactly 15 clips, each with a keyframe and a flow_prompt;
   - every edit item points to an existing clip, and `in + dur <= 8.0`;
   - each line fits its segment, at 2.6 words/s from its `at`;
   - the total is 75–90 s (parts 2–6 get the 3 s recap added on top);
   - every clip with `speaks: true` has `faces: 1`;
   - the keyframe and flow_prompt text never mention a nationality, ethnicity or accent.

## 2. Start frames: `python -m pipeline.run frames drizzlepudge MOS-001`
1. Use the arc's cast and location reference portraits. Reuse the ones made for the first MOS-001 render if they still exist; otherwise make them once per arc.
2. For each clip, generate a 9:16 keyframe with the reference-image model already used for keyframes. Pass only the refs for `chars` plus the location ref.
   - Prompt = `keyframe` + "Exactly the people described, nobody else, no extra figures, no text."
3. **Quality check** (free, mediapipe or OpenCV face detection): the number of clearly visible frontal faces must equal `faces`.
   - Over-the-shoulder shots count only the visible face. Hands-only inserts must have 0 faces.
   - Re-roll up to 2 times with a new seed, and log every re-roll.
   - Also reject any frame with visible text or letters (simple OCR check if easy; otherwise flag it for me).
4. Upload the frames to a GitHub release `mos-frames` as `MOS-001_01.jpg` … `_15.jpg`.
5. Estimated cost: about $0.60–0.80. Report the real cost.

## 3. Voice casting (once per arc): `python -m pipeline.run voices drizzlepudge a1`
1. Find out which ElevenLabs endpoints exist on fal right now:
   - Prefer Eleven v3, because it supports tags like `[whispers]` and `[trembling]`.
   - Otherwise use Turbo v2.5 and strip the tags.
2. For each character in `voices`, pick 3 candidate voices that fit the brief. Render each speaking one of that character's real lines from MOS-001.
3. Publish a page with 15 samples (5 characters × 3), labelled 1–3 per character. I'll reply with my picks, for example "mama 2, tobi 1…".
4. Save the picks in `channel.json` → `cast_voices` as `{voice, endpoint}`. They never change for the arc.
5. Cost: a few cents.

## 4. The Flow issue (the daily phone routine)
For flow-film episodes, `flow-prompts` must post an issue that works on a phone.

**At the top, a 5-line guide:**
1. Open Flow with the account named in the section.
2. Choose New project → Frames to Video → Veo 3.1 Lite, 9:16, 1 output.
3. For each clip: long-press the image → Save. Upload it as the start frame, copy the prompt, then Generate.
4. If a clip has an extra person, a changed face or text on screen, generate it again (it's free).
5. Download it, name it with the clip number (`1.mp4`), and upload it to `inbox/drizzlepudge/`.

**Then 3 sections:** MOS-A (clips 1–5), MOS-B (6–10), MOS-C (11–15). Each clip has:
- the start frame shown inline, from the release URL;
- a direct download link;
- the prompt in a code block.

**Workflow timing:** generate the next episode's start frames right after the previous episode is imported, so the issue is ready the next morning. The existing rule stays: episodes never skip, and the issue reminds me daily.

## 5. Import and assembly (when all 15 clips are in the inbox)
### a) Check the clips
- Each clip must be about 8 s, vertical, with audio.
- Sample 5 frames inside each edit segment and count faces. They must match the clip's `faces`; a speaking segment needs exactly 1.
- If a clip fails, don't assemble. Comment on the issue: "Clip 6: 2 faces found, please regenerate clip 6", and keep the other clips.

### b) Voices
- For every `line` and `vo`, make TTS with the cast voice, then cache it and measure it.
- Fit each line inside its segment:
  1. move `at` earlier;
  2. then extend `dur`, up to `8 - in`;
  3. then speed it up, at most 1.12×;
  4. otherwise warn me.
- Keep word timings: use ElevenLabs timestamps if returned, otherwise spread the line's length by characters.

### c) Picture
- Trim each segment, scale to 1080×1920, 30 fps.
- Add a very slow digital push-in (1.00 → 1.03) on segments with little camera movement.

### d) Lip-sync (segments with a `line` only)
- The audio fed to lip-sync is ONLY that speaker's line, placed at `at` and padded with silence to the segment length. Never include the `vo` or other voices.
- Endpoint order: Kling LipSync → sync-lipsync v2 → LatentSync.
  - Check each endpoint's current input schema and price on fal first.
  - Kling needs 2–10 s video; pad very short segments to 2 s and trim afterwards.
- After lip-sync, re-check: duration unchanged and still 1 face. On failure, use the fallback.

### e) Sound mix (this is what makes it feel like a film)
- **Scene background bed:** take the audio of the scene's `ambience_clip`, loop it with crossfades and run it under the whole scene.
- **Speaking segments:** mute their own Flow audio, because it contains made-up speech.
- **Silent segments:** keep their own Flow audio at -6 dB on top of the bed (Foley).
- **Dialogue:** about -16 LUFS. `vo` lines play over the shot (L-cut). The next scene's background sound starts 0.5 s before the cut (J-cut).
- **Music** (from `music/`, by scene mood): ducked under dialogue with sidechaincompress.
  - `"rising"` swells through scene C.
  - `"cut-on-last-line"` stops the music 0.2 s before "He knows", with a deep boom on the word.
- **Sound effects:** `riser`, `heartbeat`, `boom`, `whoosh`, `footsteps`. Add a small CC0/self-made library in `assets/sfx/`; ffmpeg-synthesised is fine for riser, boom and whoosh.
- Final loudness about -14 LUFS, true peak -1 dB.

### f) Transitions and finish
- Hard cuts inside a scene.
- Between scenes: `dip` = 0.4 s through black with a soft whoosh; `flash` = 6 white frames with a whoosh.
- Ending: freeze-frame 1.5 s, desaturated, then the end card.
- One grade across the whole episode (`cinema_vf`).

### g) Text on screen
- Hook text for the first 2.5 s.
- Part card at 2.8–5.6 s.
- Captions at 62–70% of the height, max 2 lines, current word highlighted, timed from the real audio.
- The "PREVIOUSLY…" recap on parts 2–6 and the moral card on part 6 work as now.

### h) Output
- `final.mp4` (75–90 s), `clean.mp4` (story only, for the arc movie) and metadata.
- Print a cost line: frames + TTS + lip-sync.

## 6. Order of work, with a stop at each step
1. **Build and run a full MOCK test (free).**
   - Use 15 generated placeholder clips, mock TTS and mock lip-sync.
   - Run the other channels' mock tests too.
   - Report the segment count, the length, and that the audio rules worked.
   - Then stop.
2. **"go ahead" → voice casting.** Publish the samples, stop, and wait for my picks.
3. **"go ahead" → 15 start frames + the Flow issue.** Publish the frames on a review page, stop, and wait for my OK on the frames before I start Flow.
4. When my 15 clips arrive, **assemble MOS-001**:
   - Publish a review page with the video, 1 frame per segment, the cost, and a copy under 4 MB (`MOS-001_small.mp4`, `-vf scale=540:-2 -crf 30`) so Claude in chat can watch it.
   - Don't upload to YouTube.
5. **When I approve:** set the daily loop going (frames → issue → import → scheduled upload), but only for episodes in flow-film format. Don't convert MOS-002…036 yourself; Claude in chat will write them in this format arc by arc.

Commit after each step with a clear message.
