"""Shorts Studio pipeline CLI.

  python -m pipeline.run daily                 # one new episode per channel: render -> upload (the scheduled job)
  python -m pipeline.run refs <channel>        # generate character reference images (do this first, check the look)
  python -m pipeline.run keyframes <ch> <id>   # cheap preview: still frames only, no video
  python -m pipeline.run render <ch> <id>      # full render to output/<ch>/<id>/final.mp4
  python -m pipeline.run upload <ch> <id>      # upload a rendered episode
  python -m pipeline.run compile <ch> [first last]  # stitch episodes into one long 16:9 video
  python -m pipeline.run weekly                # Sundays: compile a channel once it has 8.5+ min of new episodes
  python -m pipeline.run monthly               # 1st of month: compile all of last month's episodes
  python -m pipeline.run sync-youtube          # mark uploaded episodes that went public as published
  python -m pipeline.run stories <ch> <id>     # post a rendered episode to Facebook + Instagram (Stories, Reels, feed)
  python -m pipeline.run reels-backfill [ch]   # add FB/IG Reels to already-posted episodes (video from Release tiktok-<ch>)
  python -m pipeline.run check                 # test YouTube, Meta, LTX and fal.ai connections (free)
  python -m pipeline.run status
  python -m pipeline.run flow-prompts [ch]     # Google Flow channels: write today's 5 prompts to inbox/<ch>/PROMPTS.md
  python -m pipeline.run hardtruths [elders]     # Hard Truths: one lip-synced elder, 8 lines (free tools)
  python -m pipeline.run carousel [ch]         # second daily video: image carousel + scrolling words (Railway)
  python -m pipeline.run flow-import [ch]      # Google Flow channels: once 5 clips are in inbox/<ch>/, assemble + upload

Env: MOCK=1 (free test mode, no API calls), YT_UPLOAD=0 (render only), REVIEW_HOURS, DAILY_BUDGET_USD.
"""
import json
import os
import sys
import traceback

from . import assemble, config, flow, generate, state, storage


def workdir(ch, ep_id):
    return config.OUTPUT / ch / ep_id


def recap_for(ch, ep, bible):
    """Story arcs: a 3 s flash of the previous part's cliffhanger (reused from its stored clean copy, free)."""
    if not bible.get("recaps") or ep.get("part", 1) <= 1:
        return None
    prev = next((e for e in state.episodes(ch) if e.get("arc") == ep.get("arc")
                 and e.get("part") == ep["part"] - 1), None)
    if not prev:
        return None
    try:
        src = storage.fetch_episode(ch, prev["id"], config.OUTPUT / ch / "_recap" / f"{prev['id']}.mp4")
    except FileNotFoundError as e:
        print(f"   (no recap for {ep['id']}: {e})")
        return None
    start = max(assemble.duration(src) - prev["shots"][-1]["dur"], 0)
    return {"src": src, "start": start, "seconds": float(bible.get("recap_seconds", 3.0))}


def render(s, ch, ep_id):
    ep = state.get_episode(ch, ep_id)
    wd = workdir(ch, ep_id)
    print(f"\n== Rendering {ep_id}: {ep['title']}  (est. ${generate.estimate_cost(ep, generate.load_bible(ch)):.2f})")
    clips = generate.render_shots(ch, ep, wd)
    bible = generate.load_bible(ch)
    from . import narration
    narr = narration.render(ch, ep, wd, bible)
    final = assemble.assemble(ep, clips, wd, bible, narration=narr, recap=recap_for(ch, ep, bible))
    state.mark(s, ch, ep_id, "rendered", f"{assemble.duration(final):.1f}s", final=str(final.relative_to(config.ROOT)))
    state.save(s)
    try:
        storage.save_episode(ch, ep_id, wd / "clean.mp4")   # kept for the weekly/monthly compilations
    except Exception as e:
        print(f"   (could not store {ep_id} in GitHub Releases: {e})")
    keep_for_tiktok(ch, ep_id, ep)
    print(f"   -> {final}")
    return final


def keep_for_tiktok(ch, ep_id, ep):
    try:
        storage.save_tiktok(ch, ep_id, workdir(ch, ep_id) / "final.mp4", ep)
    except Exception as e:
        print(f"   (could not store {ep_id} for TikTok: {e})")


def upload(s, ch, ep_id):
    from . import youtube
    wd = workdir(ch, ep_id)
    meta = json.loads((wd / "metadata.json").read_text())
    print(f"   uploading {ep_id} to YouTube ({ch})")
    res = youtube.upload(ch, wd / "final.mp4", meta)
    note = f"https://youtu.be/{res['youtube_id']}" + (f" publishes {res['publish_at']}" if res["publish_at"] else " (private)")
    state.mark(s, ch, ep_id, "uploaded", note, **res)
    state.save(s)
    print(f"   -> {note}")


def stories(s, ch, ep_id):
    """Facebook + Instagram Stories, Reels and feed (live and public immediately). Skips placements already posted."""
    from . import meta
    if not meta.enabled(ch):
        print(f"   (no Meta token/page IDs for {ch}: stories skipped)")
        return True
    rec = s["channels"][ch]["episodes"][ep_id]
    final = workdir(ch, ep_id) / "final.mp4"
    res = meta.post_stories(ch, final, state.get_episode(ch, ep_id), assemble.duration(final), rec.get("stories", {}))
    errors = res.pop("errors", [])
    rec["stories"] = res
    state.save(s)
    for e in errors:
        print(f"!! {ch} {ep_id} stories: {e}")
    return not errors


def reels_backfill(s, chs):
    """Episodes posted to Stories before Reels existed: fetch the finished Short from Release tiktok-<ch>
    and post only the missing Facebook/Instagram Reels."""
    import subprocess
    from . import meta
    failed = False
    for ch in chs:
        if not meta.enabled(ch):
            print(f"   (no Meta token/page IDs for {ch}: skipped)")
            continue
        for ep_id, rec in s["channels"][ch]["episodes"].items():
            done = rec.get("stories") or {}
            if rec.get("status") not in ("uploaded", "published") or not done:
                continue
            fb, ig, _ = meta.ids(ch)
            if (not fb or done.get("facebook_reel")) and (not ig or done.get("instagram_reel")):
                continue
            wd = config.OUTPUT / "backfill" / ch / ep_id
            wd.mkdir(parents=True, exist_ok=True)
            video = wd / "final.mp4"
            if not video.exists():
                r = subprocess.run(["gh", "release", "download", f"tiktok-{ch}", "-p", f"{ep_id}.mp4", "-O", str(video),
                                    "--clobber"], capture_output=True, text=True)
                if r.returncode != 0:
                    print(f"!! {ch} {ep_id}: no video in release tiktok-{ch}: {r.stderr.strip()[:200]}")
                    failed = True
                    continue
            print(f"== {ch} {ep_id}: posting Reels")
            try:
                res = meta.post_stories(ch, video, state.get_episode(ch, ep_id), assemble.duration(video), done,
                                        placements=("facebook_reel", "instagram_reel"))
            except Exception as e:
                print(f"!! {ch} {ep_id}: {e}")
                failed = True
                continue
            for err in res.pop("errors", []):
                print(f"!! {ch} {ep_id}: {err}")
                failed = True
            rec["stories"] = res
            state.save(s)
    return failed


def check():
    """Free connection test for every channel: YouTube login, Meta page/IG access, LTX + fal keys."""
    from . import meta, youtube
    for ch in config.CHANNELS:
        try:
            print(f"{ch:13} YouTube  OK -> {youtube.channel_title(ch)}")
        except Exception as e:
            print(f"{ch:13} YouTube  MISSING/BROKEN: {str(e)[:150]}")
        fb, ig, token = meta.ids(ch)
        if not token:
            print(f"{ch:13} Meta     MISSING: no META_TOKEN")
            continue
        pt = meta.page_token(fb, token)
        for kind, oid, fields in (("Facebook", fb, "name"), ("Instagram", ig, "username")):
            try:
                r = meta._call("GET", f"{meta.GRAPH}/{oid}", {"fields": fields, "access_token": pt})
                print(f"{ch:13} {kind:9}OK -> {r.get(fields)}")
            except Exception as e:
                print(f"{ch:13} {kind:9}BROKEN: {str(e)[:200]}")
    print("LTX key  :", "set" if config.LTX_API_KEY else "MISSING")
    print("fal key  :", "set" if config.FAL_KEY else "MISSING (needed for character + keyframe images)")


def sync_youtube(s):
    from . import youtube
    for ch in config.CHANNELS:
        ids = {rec["youtube_id"]: ep for ep, rec in s["channels"].get(ch, {}).get("episodes", {}).items()
               if rec["status"] == "uploaded" and rec.get("youtube_id")}
        if not ids:
            continue
        for vid, priv in youtube.privacy(ch, list(ids)).items():
            if priv == "public":
                state.mark(s, ch, ids[vid], "published", f"https://youtu.be/{vid}")
                print(f"   {ids[vid]} is public")
    state.save(s)


def rendered_today(s, ch):
    """True if this channel already rendered an episode today (UTC). Lets backup cron times re-run
    the workflow safely when GitHub delays or drops the first scheduled run."""
    today = state.now()[:10]
    return any(h["status"] == "rendered" and h["at"].startswith(today)
               for rec in s["channels"].get(ch, {}).get("episodes", {}).values() for h in rec.get("history", []))


def daily(s, channels):
    do_upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
    spent, failures = 0.0, 0
    if do_upload:
        try:
            sync_youtube(s)
        except Exception as e:
            print(f"   (sync-youtube skipped: {e})")
    for ch in channels:
        if flow.is_flow(ch):
            print(f"   {ch}: Google Flow channel - made by flow-import, skipped by daily (never paid)")
            continue
        if generate.load_bible(ch).get("paused"):
            print(f"   {ch}: paused in channel.json (\"paused\": true) -> skipped")
            continue
        if os.environ.get("ONCE_PER_DAY") == "1" and rendered_today(s, ch):
            print(f"   {ch}: already made an episode today (UTC) -> skipped (backup schedule)")
            continue
        # 1) finish anything rendered but not uploaded (e.g. an upload failed yesterday).
        #    Runners are ephemeral, so the files are restored from the GitHub Release (no paid re-render).
        pending = state.next_episode(s, ch, wanted=("rendered",), max_attempts=99) if do_upload else None
        if pending and not storage.fetch_final(ch, pending, workdir(ch, pending)):
            print(f"   {ch}: {pending} was rendered earlier but its files are gone -> rendering again")
            ep_id, pending = pending, None
        else:
            ep_id = pending or state.next_episode(s, ch, max_attempts=config.MAX_ATTEMPTS)
        if not ep_id:
            print(f"!! {ch}: no scripts left. Write the next batch (see CLAUDE.md).")
            continue
        try:
            if not pending:
                cost = generate.estimate_cost(state.get_episode(ch, ep_id), generate.load_bible(ch))
                if spent + cost > config.DAILY_BUDGET_USD:
                    print(f"!! {ch}: skipping {ep_id}, would exceed DAILY_BUDGET_USD={config.DAILY_BUDGET_USD}")
                    continue
                s["channels"][ch]["episodes"][ep_id]["attempts"] += 1
                state.save(s)
                render(s, ch, ep_id)
                spent += cost
                if do_upload:
                    try:
                        storage.save_final(ch, ep_id, workdir(ch, ep_id))
                    except Exception as e:
                        print(f"   (could not keep {ep_id} for an upload retry: {e})")
        except Exception as e:
            failures += 1
            traceback.print_exc()
            if s["channels"][ch]["episodes"][ep_id]["status"] != "rendered":
                state.mark(s, ch, ep_id, "failed", str(e)[:300])
            state.save(s)
            continue
        if do_upload:
            # YouTube and Facebook/Instagram are independent: one failing must not block the other.
            try:
                upload(s, ch, ep_id)
                storage.drop_final(ch, ep_id)
            except Exception:
                failures += 1
                print(f"!! {ch} {ep_id}: YouTube upload failed (stays 'rendered', retried next run)")
                traceback.print_exc()
            try:
                if not stories(s, ch, ep_id):
                    failures += 1
            except Exception:
                failures += 1
                traceback.print_exc()
        ep = state.get_episode(ch, ep_id)
        if ep.get("arc_finale") and generate.load_bible(ch).get("arc_movies"):
            try:     # the movie never affects the finale's own status
                from . import compile as comp
                comp.compile_arc(s, ch, ep, upload=do_upload)
            except Exception as e:
                traceback.print_exc()
                print(f"!! {ch}: arc movie failed ({e}). Retry: python -m pipeline.run movie {ch} {ep_id}")
        if state.buffer_low(s, ch):
            print(f"!! {ch}: script buffer low. Write the next batch (see CLAUDE.md).")
    print(f"\nDone. Estimated spend this run: ${spent:.2f}")
    return failures


def main(argv):
    cmd = argv[0] if argv else "status"
    s = state.load()
    if cmd == "daily":
        chs = argv[1:] or config.CHANNELS
        sys.exit(1 if daily(s, chs) else 0)
    elif cmd == "refs":
        bible = generate.load_bible(argv[1])
        for cid, p in generate.ensure_references(argv[1], bible).items():
            print(f"   {cid}: {p}")
    elif cmd == "keyframes":
        ch, ep_id = argv[1], argv[2]
        ep, bible = state.get_episode(ch, ep_id), generate.load_bible(ch)
        refs = generate.ensure_references(ch, bible, ep)
        for shot in ep["shots"]:
            print("  ", generate.keyframe(ch, bible, ep, shot, refs, workdir(ch, ep_id)))
    elif cmd == "render":
        render(s, argv[1], argv[2])
    elif cmd == "upload":
        upload(s, argv[1], argv[2])
    elif cmd == "stories":
        stories(s, argv[1], argv[2])
    elif cmd == "reels-backfill":
        sys.exit(1 if reels_backfill(s, argv[1:] or list(s["channels"])) else 0)
    elif cmd == "check":
        check()
    elif cmd in ("compile", "weekly", "monthly"):
        from . import compile as comp
        do_upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
        if cmd == "compile":
            if len(argv) >= 4:
                jobs = [(argv[1], "range", int(argv[2]), int(argv[3]))]
            else:
                jobs = [(argv[1], "monthly", None, None)]
        else:
            jobs = [(ch, cmd, None, None) for ch in (argv[1:] or config.CHANNELS)
                    if comp.enabled(ch, cmd) or print(f"   {ch}: {cmd} compilations switched off in channel.json")]
        for ch, kind, a, b in jobs:
            res = comp.compile_channel(s, ch, kind, a, b)
            if res:
                out, meta, last, eps = res
                comp.finish(s, ch, kind, out, meta, last, eps, upload=do_upload)
    elif cmd == "flow-prompts":
        for ch in argv[1:] or flow.flow_channels():
            print(flow.write_prompts(s, ch))
    elif cmd == "flow-import":
        do_upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
        failed = False
        result = {}     # per-channel status -> flow_result.json (the workflow reports on each channel's issue)
        for ch in argv[1:] or flow.flow_channels():
            result[ch] = {"status": "waiting"}
            try:
                if do_upload:   # finish an earlier import whose upload failed
                    pending = state.next_episode(s, ch, wanted=("rendered",), max_attempts=99)
                    if pending:
                        upload(s, ch, pending)
                        rec = s["channels"][ch]["episodes"][pending]
                        result[ch] = {"status": "uploaded", "episode": pending, "note": rec["history"][-1]["note"]}
                res = flow.import_episode(s, ch)
                if not res:
                    continue
                ep_id, final, clips = res
                result[ch] = {"status": "assembled", "episode": ep_id}
                try:
                    storage.save_episode(ch, ep_id, workdir(ch, ep_id) / "clean.mp4")
                except Exception as e:
                    print(f"   (could not store {ep_id} in GitHub Releases: {e})")
                keep_for_tiktok(ch, ep_id, state.get_episode(ch, ep_id))
                flow.clear_inbox(clips)
                print(f"   -> {final}")
                if do_upload:
                    # YouTube and Facebook/Instagram are independent: one failing must not block the other.
                    try:
                        upload(s, ch, ep_id)
                        rec = s["channels"][ch]["episodes"][ep_id]
                        result[ch] = {"status": "uploaded", "episode": ep_id, "note": rec["history"][-1]["note"]}
                    except Exception as e:
                        failed = True
                        result[ch] = {"status": "error", "episode": ep_id, "error": f"YouTube upload failed: {e}"}
                        traceback.print_exc()
                        print(f"!! {ch} {ep_id}: YouTube upload failed (stays 'rendered', retried next import): {e}")
                    try:
                        if not stories(s, ch, ep_id):
                            failed = True
                    except Exception as e:
                        failed = True
                        traceback.print_exc()
                        print(f"!! {ch} {ep_id} stories: {e}")
                flow.write_prompts(s, ch)   # tomorrow's prompts are ready straight away
            except Exception as e:
                failed = True
                traceback.print_exc()
                print(f"!! {ch}: {e}")
                result[ch] = {"status": "error", "error": str(e)[:300]}
            state.save(s)
        (config.ROOT / "flow_result.json").write_text(json.dumps(result, indent=1) + "\n")
        if failed:
            state.save(s)
            sys.exit(1)
    elif cmd == "movie":          # rebuild an arc movie by hand: movie <channel> <finale episode id>
        from . import compile as comp
        do_upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
        comp.compile_arc(s, argv[1], state.get_episode(argv[1], argv[2]), upload=do_upload)
    elif cmd == "carousel":
        from . import carousel
        sys.exit(1 if carousel.run(argv[1:]) else 0)
    elif cmd == "hardtruths":
        from . import hardtruths
        sys.exit(1 if hardtruths.run(argv[1:]) else 0)
    elif cmd == "extras":
        from . import extras
        sys.exit(1 if extras.run(argv[1:]) else 0)
    elif cmd == "engage":
        from . import engage
        sys.exit(1 if engage.run_engage(argv[1:]) else 0)
    elif cmd == "insights":
        from . import engage
        sys.exit(1 if engage.run_insights(argv[1:]) else 0)
    elif cmd == "sync-youtube":
        sync_youtube(s)
    elif cmd == "status":
        for ch in s["channels"]:
            print(ch, state.counts(s, ch), "next:", state.next_episode(s, ch))
    else:
        print(__doc__)
    state.save(s)


if __name__ == "__main__":
    main(sys.argv[1:])
