"""Turns the bible + a shot into prompts. Keep all prompt wording here so it stays consistent."""


def cast(bible: dict, episode: dict) -> dict:
    """All characters available to this episode: bible characters + episode guests."""
    c = dict(bible["characters"])
    for gid, g in episode.get("guests", {}).items():
        c[gid] = {**g, "species": "guest", "personality": "", "catchphrase": ""}
    return c


def reference_prompt(bible: dict, char: dict) -> str:
    return (
        f"Character reference sheet. {char['ref_prompt']}. "
        f"Single character only, full body, standing, facing the camera, neutral friendly expression, "
        f"centred on a plain light grey background, even lighting. "
        f"Style: {bible['style_prompt']}. No text, no labels, no watermark."
    )


def keyframe_prompt(bible: dict, episode: dict, shot: dict, ref_names: list) -> str:
    chars = cast(bible, episode)
    refs = "; ".join(f"image {i + 1} is {n}" for i, n in enumerate(ref_names))
    who = "; ".join(f"{chars[c]['name']}: {chars[c]['ref_prompt']}" for c in shot["chars"] if c in chars)
    return (
        f"Create one vertical 9:16 film frame. Reference images: {refs}. "
        f"Every character must look exactly like their reference image (same colours, clothing, proportions). "
        f"Scene: {shot['keyframe']}. "
        f"Setting: {bible['locations'][shot['loc']]}. "
        f"Characters in frame: {who}. "
        f"Camera: {shot['camera']}. "
        f"Style: {bible['style_prompt']}. "
        + ("Leave the top 15% and bottom 25% of the frame free of faces (captions go there). "
           if bible.get("overlays", {}).get("captions", True) else "")
        + "No text, no subtitles, no speech bubbles, no watermark."
        + (" A gentle, safe, friendly scene for young children." if bible.get("made_for_kids") else "")
    )


def clip_prompt(bible: dict, episode: dict, shot: dict) -> str:
    chars = cast(bible, episode)
    parts = [shot["action"].rstrip(".") + ".", f"Camera: {shot['camera']}."]
    for ln in shot.get("lines", []):
        ch = chars[ln["c"]]
        parts.append(f'{ch["name"]} the {ch.get("species", "character")} speaks in a {ch["voice"]} voice, '
                     f'{ln.get("tone", "")}: "{ln["t"]}"')
    if bible.get("nonverbal"):
        parts.append("No spoken words at all: characters only make cute non-verbal sounds (giggles, gasps, "
                     "hiccups, 'ooh', 'uh-oh', 'yay') as described in Sound. Mouths move only for those sounds.")
    elif not shot.get("lines"):
        parts.append("No dialogue.")
    parts.append(f"Sound: {shot['sfx']}. {bible['audio_prompt']}")
    parts.append(f"Style: {bible['style_prompt']}. Smooth natural motion, mouths move only for the speaking character. "
                 "No on-screen text, subtitles or captions.")
    if bible.get("made_for_kids"):
        parts.append("Gentle, calm, friendly motion suitable for young children; no scary or unsafe actions.")
    return " ".join(parts)[:2400]
