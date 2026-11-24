#!/bin/bash
# Renders the four images into ../images/ (with wordmark) and ../images/plain/ (without).
# Needs Python with bpy (pip install bpy) and Pillow. About 2 minutes per image on 2 CPU cores.
set -e
cd "$(dirname "$0")"
python3 screens.py screens
mkdir -p raw ../images/plain
for spec in "tablet:On the wall" "phone:By the bed" "laptop:In the kitchen" "pi:On the desk"; do
  shot=${spec%%:*}; sub=${spec#*:}
  python3 scene.py "$shot" "raw/$shot.png" "${SAMPLES:-64}"
  cp "raw/$shot.png" "../images/plain/$shot.png"
  python3 overlay.py "raw/$shot.png" "../images/$shot.png" "$sub"
done
