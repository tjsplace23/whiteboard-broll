#!/usr/bin/env python3
"""Generate a chunked, resumable ffmpeg compositor that lays the clips over the A-roll.

  python3 composite.py --aroll a-roll.mp4 --timeline timeline.json --clips clips/ --out FINAL.mp4
  ./composite.sh          # re-run until it prints FINAL

Why chunked: a full-length filter graph with 20+ inputs buffers badly, and any
environment with a command timeout will kill a long single-pass render. Each chunk
finishes independently and is cached, so a killed job resumes instead of restarting.

Boundaries are only ever placed in gaps between cutaways, so no clip is ever split.
"""
import argparse, json, os, subprocess, sys

ENC = ('-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r {fps} '
       '-video_track_timescale 12800 -c:a aac -b:a 192k -ar 48000 -ac 2')


def probe(path, entries, video_only=False):
    """One value from ffprobe. video_only pins it to stream v:0 - without that a
    stream=... query also returns the audio stream's value and you get two lines."""
    cmd = ['ffprobe', '-v', 'error']
    if video_only:
        cmd += ['-select_streams', 'v:0']
    cmd += ['-show_entries', entries, '-of', 'csv=p=0', path]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip().splitlines()[0] if out.stdout.strip() else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--aroll', required=True)
    ap.add_argument('--timeline', required=True)
    ap.add_argument('--clips', default='clips')
    ap.add_argument('--out', default='FINAL.mp4')
    ap.add_argument('--script', default='composite.sh')
    ap.add_argument('--chunk', type=float, default=72.0,
                    help='seconds of video per chunk; lower it if your shell times out')
    ap.add_argument('--pocket', action='store_true',
                    help='composite the A-roll into the presenter pocket on every cutaway')
    a = ap.parse_args()

    runtime = float(probe(a.aroll, 'format=duration'))
    rate = probe(a.aroll, 'stream=r_frame_rate', video_only=True)
    if '/' in rate:
        num, den = rate.split('/')
        fps = round(float(num) / float(den)) if float(den) else 25
    else:
        fps = int(float(rate or 25))
    items = json.load(open(a.timeline))
    print(f"a-roll {runtime:.2f}s @ {fps}fps, {len(items)} cutaways")

    def inside(t):
        for o in items:
            if o['start'] - 0.3 <= t <= o['end'] + 0.3:
                return o
        return None

    bounds = [0.0]
    while runtime - bounds[-1] > a.chunk * 1.35:
        t = bounds[-1] + a.chunk
        o = inside(t)
        if o:
            t = round(o['end'] + 0.35, 3)
        if t <= bounds[-1] + 5 or t >= runtime:
            break
        bounds.append(round(t, 3))
    bounds.append(runtime)

    chunks, body, idx = [], [], []
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        ov = [o for o in items if o['start'] >= s - 1e-6 and o['end'] <= e + 1e-6]
        straddle = [o for o in items if not (o['end'] <= s or o['start'] >= e)]
        if len(ov) != len(straddle):
            sys.exit(f"chunk {i} would split a cutaway; lower --chunk or adjust the timeline")
        chunks.append((i, s, e - s, ov))
        idx.append(str(i))
        ins = ' '.join(f'-i "$C/{o["id"]}.mp4"' for o in ov)
        fg = []
        for k, o in enumerate(ov, 1):
            off, rs, re_ = o['start'] - s, o['start'] - s, o['end'] - s
            fg.append(f"[{k}:v]setpts=PTS-STARTPTS+{off:.3f}/TB[o{k}];")
            prev = '[0:v]' if k == 1 else f'[v{k-1}]'
            fg.append(f"{prev}[o{k}]overlay=0:0:eof_action=pass:repeatlast=0:"
                      f"enable='between(t,{rs:.3f},{re_:.3f})'[v{k}];")
        if ov and a.pocket:
            # split the a-roll: one copy is the base, one is scaled into the pocket
            head = "[0:v]split=2[m][pp];[pp]scale=540:304:flags=lanczos[pip];"
            fg2 = []
            for k, o in enumerate(ov, 1):
                off, rs, re_ = o['start'] - s, o['start'] - s, o['end'] - s
                fg2.append(f"[{k}:v]setpts=PTS-STARTPTS+{off:.3f}/TB[o{k}];")
                prev = '[m]' if k == 1 else f'[v{k-1}]'
                fg2.append(f"{prev}[o{k}]overlay=0:0:eof_action=pass:repeatlast=0:"
                           f"enable='between(t,{rs:.3f},{re_:.3f})'[v{k}];")
            gate = "+".join(f"between(t,{o['start']-s:.3f},{o['end']-s:.3f})" for o in ov)
            fg2.append(f"[v{len(ov)}][pip]overlay=1340:729:enable='{gate}'[vout]")
            filt = f'-filter_complex "{head}{"".join(fg2)}"'
            vmap = '-map "[vout]"'
        else:
            vmap = f'-map "[v{len(ov)}]"' if ov else '-map 0:v'
            filt = f'-filter_complex "{"".join(fg).rstrip(";")}"' if ov else ''
        body.append(f'''
run_{i}() {{
  ffmpeg -y -v error -ss {s:.3f} -t {e-s:.3f} -i "$A" {ins} \\
   {filt} {vmap} -map 0:a? {ENC.format(fps=fps)} "$P/.t{i:02d}.mp4" \\
   && mv "$P/.t{i:02d}.mp4" "$P/part{i:02d}.mp4"
}}''')

    exp = ' '.join(f'{c[2]:.2f}' for c in chunks)
    sh = f'''#!/bin/bash
# Resumable composite. Re-run until it prints FINAL. Finished chunks are skipped.
D="$(cd "$(dirname "$0")" && pwd)"; C="{os.path.abspath(a.clips)}"; P="$D/parts"; mkdir -p "$P"
A="{os.path.abspath(a.aroll)}"
N={len(chunks)}; EXP=({exp})
{''.join(body)}
T0=$(date +%s); DONE=0; MADE=""
for i in {' '.join(idx)}; do
  f=$(printf "$P/part%02d.mp4" $i)
  # a non-empty file is NOT a finished file - probe it
  if [ -s "$f" ] && d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null) \\
     && [ -n "$d" ] && awk "BEGIN{{exit !(($d-${{EXP[$i]}})<0.4 && ($d-${{EXP[$i]}})>-0.4)}}"; then
    DONE=$((DONE+1)); continue
  fi
  if [ $(( $(date +%s) - T0 )) -ge ${{1:-26}} ]; then break; fi
  run_$i || {{ echo "CHUNK $i FAILED"; exit 1; }}
  DONE=$((DONE+1)); MADE="$MADE $i"
done
echo "parts: $DONE/$N (made:${{MADE:- none}}) ${{SECONDS}}s"
if [ $DONE -eq $N ]; then
  L="$P/list.txt"; printf '' > "$L"
  for i in {' '.join(idx)}; do printf "file 'part%02d.mp4'\\n" $i >> "$L"; done
  ffmpeg -y -v error -f concat -safe 0 -i "$L" -c copy -movflags +faststart "{os.path.abspath(a.out)}" \\
   && echo "FINAL $(ffprobe -v error -show_entries format=duration -of csv=p=0 "{os.path.abspath(a.out)}")s"
fi
'''
    open(a.script, 'w').write(sh)
    os.chmod(a.script, 0o755)
    print(f"{len(chunks)} chunks, max {max(c[2] for c in chunks):.1f}s -> ./{a.script}")
    print("run it repeatedly until it prints FINAL")


if __name__ == '__main__':
    main()
