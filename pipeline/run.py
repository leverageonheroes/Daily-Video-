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
  python -m pipeline.run stories <ch> <id>     # post a rendered episode to Facebook + Instagram Stories
  python -m pipeline.run check                 # test YouTube, Meta, LTX and fal.ai connections (free)
  python -m pipeline.run status
  python -m pipeline.run flow-prompts [ch]     # Google Flow channels: write today's 5 prompts to inbox/<ch>/PROMPTS.md
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


def render(s, ch, ep_id):
    ep = state.get_episode(ch, ep_id)
    wd = workdir(ch, ep_id)
    print(f"\n== Rendering {ep_id}: {ep['title']}  (est. ${generate.estimate_cost(ep):.2f})")
    clips = generate.render_shots(ch, ep, wd)
    bible = generate.load_bible(ch)
    from . import narration
    narr = narration.render(ch, ep, wd, bible)
    final = assemble.assemble(ep, clips, wd, bible, narration=narr)
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
    """Facebook + Instagram Stories (live and public immediately). Skips platforms already posted."""
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
                cost = generate.estimate_cost(state.get_episode(ch, ep_id))
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
