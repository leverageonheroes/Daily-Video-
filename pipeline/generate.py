"""Reference images -> keyframes -> clips. Every file is cached on disk, so a rerun never pays twice."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, fal_api, ltx_api, prompts

COLORS = ["0x2b6777", "0x8e3b46", "0x4d6a2c", "0x6b4e9b", "0x9c6b1f", "0x1f5f8b"]


def load_bible(channel: str) -> dict:
    return json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text())


def _first_image_url(result: dict) -> str:
    imgs = result.get("images") or ([result["image"]] if "image" in result else [])
    if not imgs:
        raise fal_api.GenerationError(f"no image in result: {str(result)[:300]}")
    return imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]


def reference_image(channel: str, bible: dict, char_id: str, char: dict) -> Path:
    """One reference image per character, generated once and committed to the repo (assets/)."""
    sub = "" if char_id in bible["characters"] else "guests/"
    dest = config.ASSETS / channel / f"{sub}{char_id}.png"
    if dest.exists():
        return dest
    print(f"   reference image: {char['name']}")
    if config.MOCK:
        return fal_api.mock_image(dest, f"REF {char['name']}", COLORS[hash(char_id) % len(COLORS)], "1024x1024")
    res = fal_api.run(config.IMAGE_T2I, {
        "prompt": prompts.reference_prompt(bible, char),
        "num_images": 1, "aspect_ratio": "1:1", "output_format": "png",
    })
    return fal_api.download(_first_image_url(res), dest)


def ensure_references(channel: str, bible: dict, episode: dict | None = None):
    cast = prompts.cast(bible, episode or {})
    wanted = bible["characters"] if episode is None else {
        c: cast[c] for s in episode["shots"] for c in s["chars"]}
    return {cid: reference_image(channel, bible, cid, cast[cid]) for cid in wanted}


def keyframe(channel, bible, episode, shot, refs, workdir: Path) -> Path:
    dest = workdir / f"shot{shot['n']:02d}_key.png"
    if dest.exists():
        return dest
    print(f"   keyframe shot {shot['n']}")
    if config.MOCK:
        return fal_api.mock_image(dest, f"{episode['id']} shot {shot['n']}: {shot['keyframe']}",
                                  COLORS[shot["n"] % len(COLORS)])
    cast = prompts.cast(bible, episode)
    names = [cast[c]["name"] for c in shot["chars"]]
    urls = [fal_api.upload(refs[c]) for c in shot["chars"]]
    model = config.IMAGE_EDIT if urls else config.IMAGE_KEY_T2I
    args = {"prompt": prompts.keyframe_prompt(bible, episode, shot, names), "num_images": 1, "output_format": "png"}
    if "nano-banana" in model:
        args["aspect_ratio"] = "9:16"
    else:   # flux-style endpoints take an explicit size
        args["image_size"] = config.KEYFRAME_SIZE
    if urls:
        args["image_urls"] = urls
    res = fal_api.run(model, args)
    return fal_api.download(_first_image_url(res), dest)


def clip(bible, episode, shot, key: Path, workdir: Path) -> Path:
    dest = workdir / f"shot{shot['n']:02d}.mp4"
    if dest.exists():
        return dest
    print(f"   clip shot {shot['n']} ({shot['dur']}s)")
    if config.MOCK:
        return fal_api.mock_clip(dest, key, shot["dur"], 220 + 40 * shot["n"])
    prompt = prompts.clip_prompt(bible, episode, shot)
    order = [config.VIDEO_PROVIDER] + ([config.VIDEO_FALLBACK] if config.VIDEO_FALLBACK
                                       and config.VIDEO_FALLBACK != config.VIDEO_PROVIDER else [])
    errors = []
    for provider in order:
        try:
            if provider == "ltx":
                if not config.LTX_API_KEY:
                    raise ltx_api.LTXError("LTX_API_KEY is not set")
                return ltx_api.image_to_video(key, prompt, shot["dur"], dest)
            if provider == "fal":
                args = {"image_url": fal_api.upload(key), "prompt": prompt,
                        "fps": config.VIDEO_FPS, "generate_audio": config.GENERATE_AUDIO}
                if "ltx-2-19b" in config.VIDEO_I2V:   # frame-count API, size follows the keyframe
                    args.update(num_frames=shot["dur"] * config.VIDEO_FPS + 1, video_size="auto",
                                enable_prompt_expansion=False,
                                negative_prompt="subtitles, captions, on-screen text, letters, watermark, logo, "
                                                "blurry, distorted faces, extra limbs, flicker, off-sync audio")
                else:
                    args.update(duration=shot["dur"], resolution=config.VIDEO_RESOLUTION, aspect_ratio="9:16")
                res = fal_api.run(config.VIDEO_I2V, args)
                return fal_api.download(res["video"]["url"], dest)
            raise ValueError(f"unknown VIDEO_PROVIDER '{provider}'")
        except Exception as e:
            errors.append(f"{provider}: {e}")
            if provider != order[-1]:
                print(f"   shot {shot['n']}: {provider} failed ({str(e)[:120]}), falling back to {order[-1]}")
    raise fal_api.GenerationError("all video providers failed -> " + " | ".join(errors))


def estimate_cost(episode) -> float:
    from . import narration
    secs = sum(s["dur"] for s in episode["shots"])
    return (secs * config.PRICE_PER_VIDEO_SECOND + len(episode["shots"]) * config.PRICE_PER_IMAGE
            + narration.estimate_cost(episode))


def render_shots(channel: str, episode: dict, workdir: Path) -> list:
    bible = load_bible(channel)
    workdir.mkdir(parents=True, exist_ok=True)
    refs = ensure_references(channel, bible, episode)

    def one(shot):
        key = keyframe(channel, bible, episode, shot, refs, workdir)
        return clip(bible, episode, shot, key, workdir)

    # shots are independent once the reference images exist -> generate several at once
    with ThreadPoolExecutor(max_workers=config.PARALLEL_SHOTS) as pool:
        return list(pool.map(one, episode["shots"]))
