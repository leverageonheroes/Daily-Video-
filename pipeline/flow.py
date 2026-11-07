"""Google Flow channels (channel.json "source": "flow"): a human makes the clips, the pipeline does the rest.

Daily loop (free, uses the 50 daily Google Flow credits = 5 x Veo 3.1 Lite 8 s clips):
  1. `flow-prompts <ch>`  -> writes inbox/<ch>/PROMPTS.md for the next episode (also posted as a GitHub issue)
  2. Human: paste each prompt into Google Flow (Veo 3.1 Lite, 9:16, 1 output), download the 5 clips,
     upload them to inbox/<ch>/ on GitHub.
  3. `flow-import <ch>`   -> once 5 clips are there: order them, assemble (captions, hook, music, loudness),
     store the clean copy, upload to YouTube, delete the clips from inbox/.

Clip order: a leading number in the file name wins (1.mp4, 2_clip.mp4, clip-3.mp4 ...). Otherwise the order
they were added to git (upload them one at a time, in order). Otherwise alphabetical.
"""
import json
import re
import subprocess

from . import assemble, config, state

VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}


def is_flow(channel: str) -> bool:
    try:
        return json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text()).get("source") == "flow"
    except FileNotFoundError:
        return False


def flow_channels():
    return [p.name for p in sorted(config.CHANNELS_DIR.iterdir()) if is_flow(p.name)]


def inbox(channel: str):
    d = config.INBOX / channel
    d.mkdir(parents=True, exist_ok=True)
    return d


def current_episode(s, channel):
    """Strict order, never date-based: the lowest-numbered episode that has not been assembled yet.
    A missed day (or a failed import, however many times) never skips an episode - the same prompts
    stay current until their 5 clips have been imported."""
    eps = s["channels"][channel]["episodes"]
    for ep_id in sorted(eps, key=lambda k: int(k.rsplit("-", 1)[-1])):
        if eps[ep_id]["status"] in ("scripted", "failed"):
            return ep_id
    return None


def prompts_markdown(s, channel) -> str:
    ep_id = current_episode(s, channel)
    if not ep_id:
        return f"## {channel}: no scripts left\nOpen the Codespace and ask Claude Code to write the next batch (CLAUDE.md)."
    bible = json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text())
    ep = state.get_episode(channel, ep_id)
    f = bible.get("flow", {})
    out = [f"## {bible['show_title']} - {ep_id}: {ep['title'].replace(' #shorts', '')}",
           "",
           f"**Google Flow settings:** {f.get('model', 'Veo 3.1 Lite')} | aspect **{f.get('aspect', '9:16')}** | "
           f"outputs per prompt **{f.get('outputs_per_prompt', 1)}** | {f.get('clip_seconds', 8)} s. "
           "Generate before 14:00 UTC (free tier is paused ~14:00-17:00 UTC).",
           "",
           f"**Then:** download the clips and upload them to `inbox/{channel}/` "
           "(GitHub website > inbox > " + channel + " > Add file > Upload files). "
           "Name them 1.mp4 to 5.mp4, OR upload them one at a time in order. "
           "The video is assembled and posted automatically when the 5th clip arrives.",
           ""]
    for shot in ep["shots"]:
        out += [f"### Clip {shot['n']}", "```", shot["flow_prompt"], "```", ""]
    return "\n".join(out)


def write_prompts(s, channel):
    md = prompts_markdown(s, channel)
    (inbox(channel) / "PROMPTS.md").write_text(md + "\n")
    return md


def _git_added_time(path):
    try:
        r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ct", "-1", "--", str(path)],
                           cwd=config.ROOT, capture_output=True, text=True, timeout=30)
        return int(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None
    except Exception:
        return None


def ordered_clips(channel):
    files = [p for p in inbox(channel).iterdir() if p.suffix.lower() in VIDEO_EXT and p.stat().st_size > 0]
    numbered = {}
    for p in files:
        m = re.match(r"^(?:clip|shot|part|scene)?[\s_-]*(\d{1,2})(?:\D|$)", p.stem, re.I)
        if m:
            numbered.setdefault(int(m.group(1)), p)
    if files and sorted(numbered) == list(range(1, len(files) + 1)):
        return [numbered[k] for k in sorted(numbered)], "file-name numbers"
    times = {p: _git_added_time(p) for p in files}
    if files and all(times.values()) and len(set(times.values())) == len(files):
        return sorted(files, key=lambda p: times[p]), "upload order"
    return sorted(files, key=lambda p: p.name.lower()), "alphabetical"


def import_episode(s, channel):
    """Returns (ep_id, final_path, clips) when an episode was assembled, else None."""
    ep_id = current_episode(s, channel)
    if not ep_id:
        print(f"!! {channel}: no scripts left")
        return None
    ep = state.get_episode(channel, ep_id)
    need = len(ep["shots"])
    clips, how = ordered_clips(channel)
    print(f"   {channel} {ep_id}: {len(clips)}/{need} clips in inbox/{channel}/ (order by {how})")
    if len(clips) < need:
        print("   waiting for the rest of the clips")
        return None
    if len(clips) > need:
        print(f"   more than {need} clips - using the first {need}: " + ", ".join(p.name for p in clips[:need]))
        clips = clips[:need]
    for p in clips:
        d = assemble.duration(p)
        if d < 2:
            raise RuntimeError(f"{p.name} looks broken ({d:.1f}s). Delete it and upload it again.")
        if not assemble.has_audio(p):
            print(f"   note: {p.name} has no audio track (silence will be used)")
    wd = config.OUTPUT / channel / ep_id
    wd.mkdir(parents=True, exist_ok=True)
    local = []
    for shot, p in zip(ep["shots"], clips):
        dest = wd / f"clip{shot['n']:02d}{p.suffix.lower()}"
        dest.write_bytes(p.read_bytes())
        local.append(dest)
        print(f"   clip {shot['n']} <- {p.name}")
    rec = s["channels"][channel]["episodes"][ep_id]
    rec["attempts"] = rec.get("attempts", 0) + 1
    bible = json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text())
    final = assemble.assemble(ep, local, wd, bible)
    state.mark(s, channel, ep_id, "rendered", f"{assemble.duration(final):.1f}s from Google Flow clips",
               final=str(final.relative_to(config.ROOT)), clips=[p.name for p in clips])
    state.save(s)
    return ep_id, final, clips


def clear_inbox(clips):
    for p in clips:
        p.unlink(missing_ok=True)
