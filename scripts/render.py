#!/usr/bin/env python3
"""Render each scene in a timeline to its own MP4 clip.

  python3 render.py --timeline timeline.json --scenes my_scenes.py --out clips/
"""
import argparse, importlib.util, json, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wb import render_scene, FPS


def load(path):
    spec = importlib.util.spec_from_file_location('user_scenes', path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--timeline', required=True)
    ap.add_argument('--scenes', required=True)
    ap.add_argument('--out', default='clips')
    ap.add_argument('--crf', default='20')
    ap.add_argument('--pocket', action='store_true',
                    help='reserve the presenter pocket; pair with composite.py --pocket')
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    items = json.load(open(a.timeline))
    mod = load(a.scenes)
    t0 = time.time()

    for k, it in enumerate(items, 1):
        dst = os.path.join(a.out, f"{it['id']}.mp4")
        if os.path.exists(dst):
            print(f"[{k}/{len(items)}] {it['id']} cached", flush=True)
            continue
        tmp = os.path.join(a.out, f'_fr_{it["id"]}')
        shutil.rmtree(tmp, ignore_errors=True)
        n = render_scene(it['id'], mod.BUILDERS[it['id']](it['dur']), it['dur'], tmp,
                         pocket=a.pocket)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', str(FPS),
                        '-i', f'{tmp}/%05d.png', '-c:v', 'libx264', '-preset', 'slow',
                        '-crf', a.crf, '-pix_fmt', 'yuv420p', '-r', str(FPS),
                        dst + '.tmp.mp4'], check=True)
        os.replace(dst + '.tmp.mp4', dst)      # never leave a half-written clip
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[{k}/{len(items)}] {it['id']:>4} {n:>4}f "
              f"{os.path.getsize(dst)/1e6:.2f}MB ({time.time()-t0:.0f}s)", flush=True)

    tot = sum(os.path.getsize(os.path.join(a.out, f"{i['id']}.mp4")) for i in items)
    print(f"\n{len(items)} clips, {tot/1e6:.1f} MB, {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
