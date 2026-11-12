#!/usr/bin/env bash
# Installs SadTalker (Apache-2.0 talking-head lip-sync) + weights for Hard Truths (pipeline/hardtruths.py).
# Idempotent: a cached install is reused. Needs python3.10 on PATH (GitHub: actions/setup-python 3.10).
#   SADTALKER_DIR (default ~/sadtalker)
set -euo pipefail
DIR="${SADTALKER_DIR:-$HOME/sadtalker}"
COMMIT=cd4c0465ae0b54a6f85af57f5c65fec9fe23e7f8
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$DIR/inference.py" ]; then
  git clone -q https://github.com/OpenTalker/SadTalker.git "$DIR"
  git -C "$DIR" checkout -q "$COMMIT"
fi
PY310="${PYTHON310:-python3.10}"
if [ ! -x "$DIR/venv/bin/python" ]; then
  "$PY310" -m venv "$DIR/venv"
  "$DIR/venv/bin/pip" install -q --upgrade pip
  "$DIR/venv/bin/pip" install -q -r "$HERE/sadtalker_requirements.txt"
fi
mkdir -p "$DIR/checkpoints" "$DIR/gfpgan/weights"
REL=https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc
for f in mapping_00109-model.pth.tar mapping_00229-model.pth.tar SadTalker_V0.0.2_256.safetensors; do
  [ -s "$DIR/checkpoints/$f" ] || curl -sSfL "$REL/$f" -o "$DIR/checkpoints/$f"
done
for u in https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth \
         https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth \
         https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth \
         https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth; do
  f="$DIR/gfpgan/weights/$(basename "$u")"
  [ -s "$f" ] || curl -sSfL "$u" -o "$f"
done
echo "SadTalker ready in $DIR"
