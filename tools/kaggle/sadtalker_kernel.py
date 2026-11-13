# Hard Truths lip-sync on a FREE Kaggle GPU (about 30 GPU hours/week per account).
# Pushed and filled in by pipeline/kaggle_lipsync.py on every run - do not edit the copy on Kaggle.
# Downloads the padded portrait + 16 kHz voice from the public GitHub Release hardtruths-kaggle, runs SadTalker
# (same pinned commit + deps as the GitHub CPU fallback, but CUDA torch) and leaves talking_raw.mp4 in the output.
import glob
import os
import shutil
import subprocess
import sys
import urllib.request

IMG_URL = "__IMG_URL__"
AUD_URL = "__AUD_URL__"
COMMIT = "__COMMIT__"
SIZE = "__SIZE__"
ENHANCER = "__ENHANCER__"
EXPRESSION = "__EXPRESSION__"
REQS = """__REQS__"""

OUT = "/kaggle/working"
T, ST, VENV = "/tmp/ht", "/tmp/sadtalker", "/tmp/stvenv"


def sh(cmd, cwd=None):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)


os.makedirs(T, exist_ok=True)
subprocess.run("nvidia-smi -L", shell=True)
urllib.request.urlretrieve(IMG_URL, f"{T}/src.png")
urllib.request.urlretrieve(AUD_URL, f"{T}/voice.wav")

sh(f"git clone -q https://github.com/OpenTalker/SadTalker.git {ST} && git -C {ST} checkout -q {COMMIT}")
# SadTalker's pinned deps need Python 3.10; uv fetches a standalone 3.10 in seconds
sh(f"{sys.executable} -m pip install -q uv")
sh(f"{sys.executable} -m uv venv --seed -q -p 3.10 {VENV}")
with open(f"{T}/req.txt", "w") as f:
    f.write(REQS)
sh(f"{VENV}/bin/pip install -q -r {T}/req.txt")

REL = "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc"
os.makedirs(f"{ST}/checkpoints", exist_ok=True)
os.makedirs(f"{ST}/gfpgan/weights", exist_ok=True)
for f in ["mapping_00109-model.pth.tar", "mapping_00229-model.pth.tar", f"SadTalker_V0.0.2_{SIZE}.safetensors"]:
    sh(f"curl -sSfL {REL}/{f} -o {ST}/checkpoints/{f}")
for u in ["https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth",
          "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
          "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
          "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth"]:
    sh(f"curl -sSfL {u} -o {ST}/gfpgan/weights/{os.path.basename(u)}")

gpu = subprocess.run([f"{VENV}/bin/python", "-c", "import torch;print(torch.cuda.is_available())"],
                     capture_output=True, text=True).stdout.strip() == "True"
print("CUDA available:", gpu, flush=True)
cmd = (f"{VENV}/bin/python inference.py --driven_audio {T}/voice.wav --source_image {T}/src.png "
       f"--result_dir {T}/res --still --preprocess full --size {SIZE} --expression_scale {EXPRESSION}")
if ENHANCER and ENHANCER != "none":
    cmd += f" --enhancer {ENHANCER}"
if not gpu:
    cmd += " --cpu"
sh(cmd, cwd=ST)

mp4s = sorted(glob.glob(f"{T}/res/**/*.mp4", recursive=True), key=os.path.getmtime)
if not mp4s:
    sys.exit("SadTalker produced no video")
shutil.copy(mp4s[-1], f"{OUT}/talking_raw.mp4")
print("DONE talking_raw.mp4", os.path.getsize(f"{OUT}/talking_raw.mp4"), "bytes, gpu =", gpu, flush=True)
