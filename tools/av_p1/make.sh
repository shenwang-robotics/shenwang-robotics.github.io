#!/usr/bin/env bash
# Rebuild the Project-1 visuals on projects/av_projects/: p1_paths.png, p1_exploration.png, p1_informed.mp4 and its poster.
#   AV_P1=<course project1 folder, with matlab/ and maps/> AV_P1_LOGS=<its logs/ folder> tools/av_p1/make.sh
set -euo pipefail
: "${AV_P1:?course project1 folder}" "${AV_P1_LOGS:?course project1 logs folder}"
cd "$(dirname "$0")/../.."
matlab -batch "addpath('tools/av_p1'); paths_figure; exploration_figure; informed_frames"
python3 - <<'PY'
from PIL import Image
for name in ("p1_paths", "p1_exploration"):
    im = Image.open(f"tools/av_p1/{name}_300dpi.png").convert("RGB")
    im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS).save(f"images/av_projects/{name}.png", optimize=True)
PY
python3 tools/av_p1/informed_clip.py
