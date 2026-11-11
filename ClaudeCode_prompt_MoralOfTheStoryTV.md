# Paste into Claude Code (Codespace, repo Daily-Video-)

I uploaded `mos-addon.zip` to the repo root. It turns the **drizzlepudge** slot into **Moral Of The Story TV**: 6 drama arcs × 6 parts (MOS-001…036, ~80 s each), made with Veo 3.1 Lite on fal. Read `mos-addon/README.md` and CLAUDE.md first.

**Rules:**
- I am on a PHONE. Keep messages short, give numbered choices, do one step at a time, and don't use arrow-key menus.
- Never commit `.env`, `secrets/`, tokens, keys or any `.zip` file. Never print a full key.
- **Make NO paid API calls until I type "go ahead".**
- Don't rewrite the pipeline. Only fix something if it actually fails, and tell me why in one line.
- If the patch doesn't apply, merge by hand. Never overwrite fixes I made myself.

## Step 1: Install
1. Unzip `mos-addon.zip` to /tmp, then run `git apply --3way /tmp/mos-addon/mos.patch`.
2. Copy `/tmp/mos-addon/files/.` over the repo root.
3. Delete `channels/drizzlepudge/episodes/eps_001-015.json` and `eps_016-030.json`. The old Drizzle & Pudge copies stay in `channels/drizzlepudge/archive/`.
4. Run `python tools/validate.py`. It must say RESULT: OK.

## Step 2: Free mock test (no cost)
1. Run `MOCK=1 YT_UPLOAD=0 python -m pipeline.run render drizzlepudge MOS-001` (takes about 8 min).
2. Then render MOS-002 the same way.
3. Check:
   - MOS-001 is about 80 s, shows the "PART 1 OF 6 · THE LIST" card, and ends on a freeze-frame with the end card.
   - MOS-002 opens with a 3 s "PREVIOUSLY..." recap.
4. Report the durations to me in 2 lines.

## Step 3: Check the video model (still no cost)
- The channel uses fal endpoint `fal-ai/veo3.1/lite/image-to-video`. If a shot fails, it falls back to `fal-ai/veo3.1/fast/image-to-video`.
- The pipeline sends: `image_url`, `prompt`, `aspect_ratio "9:16"`, `duration "8s"`, `resolution "720p"`, `generate_audio true`.
- Check fal's model page or OpenAPI schema for both endpoints, without running them, and confirm the ID and these field names.
  - If anything differs, fix only `channels/drizzlepudge/channel.json` and the matching lines in `tools/generators/build_moraloftheStory_s1.py` / `pipeline/generate.py`.
- Background: Google shut the Gemini API Veo *preview* IDs on 22 Oct 2026, so `pipeline/veo_api.py` is optional and not used.
- `FAL_KEY` is already a GitHub secret. Nothing new is needed in `daily.yml`.

## Step 4: Music
- Tell me which of these files exist in the music folder: `nollywood-suspense.mp3`, `tender-strings.mp3`, `tension-drums.mp3`.
- If any are missing, give me 3 royalty-free search tips. Don't download anything yourself.

## Step 5: Commit
Commit the add-on with the message "Moral Of The Story TV: 6 arcs, 36 episodes, arc movies", then push.

## Step 6: Real Episode 1 (only after I type "go ahead")
1. Tell me the cost first: about $4.90 (10 × 8 s clips at $0.05/s = $4.00, plus keyframes and the arc-1 cast/set reference images).
2. Generate the Arc 1 references, then run `YT_UPLOAD=0 python -m pipeline.run render drizzlepudge MOS-001`.
   - If `FAL_KEY` isn't in the Codespace, ask me to put it in `.env` (never commit it).
3. Upload `final.mp4` as an asset on a GitHub **pre-release** called `mos-preview`, and send me the download link.
4. Show me 3 frames from the clip: shot 1, shot 5 and the last frame.
5. Do NOT upload to YouTube and do NOT mark MOS-001 as published in state.

## Step 7: What I'll do in YouTube Studio (just remind me)
- Rename the drizzlepudge channel to **Moral Of The Story TV**.
- Set Audience to **"No, it's not made for kids"**.
- Upload the logo from `assets/logos/MoralOfTheStoryTV_logo_800x800.png`.

Daily posting for this channel starts only once I'm happy with Episode 1.
