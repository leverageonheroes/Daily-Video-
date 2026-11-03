#!/usr/bin/env python3
"""Production state CLI (wraps pipeline/state.py).

  python tools/state.py status                      # overview + whether a new script batch is needed
  python tools/state.py next <channel>              # next episode id to render
  python tools/state.py mark <channel> <id> <status> [note]
Statuses: scripted -> rendered -> uploaded -> published  (or failed)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import state as st  # noqa: E402


def main():
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "status"), sys.argv[2:]
    s = st.load()
    if cmd == "status":
        need = False
        for ch in s["channels"]:
            c = st.counts(s, ch)
            print(f"{ch}: " + ", ".join(f"{k}={v}" for k, v in c.items()) + f"  (last scripted: {s['channels'][ch]['last_scripted']})")
            if st.buffer_low(s, ch):
                need = True
                print(f"ACTION NEEDED: {ch} has fewer than {st.BUFFER_MIN} unrendered scripts -> write the next batch (see CLAUDE.md)")
        if not need:
            print("Script buffer OK.")
    elif cmd == "next":
        print(st.next_episode(s, args[0]) or "NONE - write the next batch (see CLAUDE.md)")
    elif cmd == "mark":
        st.mark(s, args[0], args[1], args[2], " ".join(args[3:]))
    elif cmd != "sync":
        sys.exit(__doc__)
    st.save(s)


if __name__ == "__main__":
    main()
