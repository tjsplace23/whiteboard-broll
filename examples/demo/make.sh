#!/bin/bash
# End-to-end demo. Builds a stand-in A-roll, then runs the real pipeline on it.
set -e
cd "$(dirname "$0")"
S=../../scripts
[ -f a-roll.mp4 ] || ffmpeg -y -v error -f lavfi -i "testsrc2=size=1920x1080:rate=25:duration=46" \
  -f lavfi -i "sine=frequency=220:duration=46" -c:v libx264 -preset veryfast -crf 23 \
  -pix_fmt yuv420p -c:a aac -shortest a-roll.mp4

python3 $S/anchor.py --srt demo.srt --check-tail "I'll see you in the next one."
python3 $S/anchor.py --srt demo.srt --scenes ../../references/example_scenes.py --out timeline.json
python3 $S/render.py  --timeline timeline.json --scenes ../../references/example_scenes.py --out clips/ --pocket
python3 $S/composite.py --aroll a-roll.mp4 --timeline timeline.json --clips clips/ --out FINAL.mp4 --pocket
./composite.sh 600
