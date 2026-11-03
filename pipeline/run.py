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
  python -m pipeline.run status

Env: MOCK=1 (free test mode, no API calls), YT_UPLOAD=0 (render only), REVIEW_HOURS, DAILY_BUDGET_USD.
"""
import json
import os
import sys
import traceback

from . import assemble, config, generate, state, storage


def workdir(ch, ep_id):
    return config.OUTPUT / ch / ep_id


def render(s, ch, ep_id):
    ep = state.get_episode(ch, ep_id)
    wd = workdir(ch, ep_id)
    print(f"\n== Rendering {ep_id}: {ep['title']}  (est. ${generate.estimate_cost(ep):.2f})")
    clips = generate.render_shots(ch, ep, wd)
    final = assemble.assemble(ep, clips, wd, generate.load_bible(ch))
    state.mark(s, ch, ep_id, "rendered", f"{assemble.duration(final):.1f}s", final=str(final.relative_to(config.ROOT)))
    state.save(s)
    try:
        storage.save_episode(ch, ep_id, wd / "clean.mp4")   # kept for the weekly/monthly compilations
    except Exception as e:
        print(f"   (could not store {ep_id} in GitHub Releases: {e})")
    print(f"   -> {final}")
    return final


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
        # 1) finish anything rendered but not uploaded (e.g. an upload failed yesterday)
        pending = state.next_episode(s, ch, wanted=("rendered",), max_attempts=99) if do_upload else None
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
                upload(s, ch, ep_id)
        except Exception as e:
            failures += 1
            traceback.print_exc()
            if s["channels"][ch]["episodes"][ep_id]["status"] != "rendered":
                state.mark(s, ch, ep_id, "failed", str(e)[:300])
            state.save(s)
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
