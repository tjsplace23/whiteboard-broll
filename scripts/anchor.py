#!/usr/bin/env python3
"""Anchor whiteboard scenes to the spoken cues in an SRT, and validate the plan.

  python3 anchor.py --srt caption.srt --check-tail "I'll see you in the next one."
  python3 anchor.py --srt caption.srt --scenes my_scenes.py --out timeline.json
"""
import argparse, importlib.util, json, os, re, sys


def parse_srt(path):
    raw = open(path, encoding='utf-8-sig').read()
    out = []
    for b in re.split(r'\n\s*\n', raw.strip()):
        L = b.strip().split('\n')
        if len(L) < 2 or '-->' not in L[1]:
            continue
        st, en = [x.strip() for x in L[1].split('-->')]

        def sec(t):
            h, m, rest = t.split(':')
            s, ms = rest.replace('.', ',').split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        out.append({'i': len(out) + 1, 's': sec(st), 'e': sec(en),
                    't': ' '.join(L[2:]).strip()})
    return out


def norm(s):
    return re.sub(r'[^a-z0-9 ]', '', re.sub(r'\s+', ' ', s.lower()))


def find(blocks, phrase, after=0.0):
    """Find the caption block containing `phrase`, searching from `after` onward.
    Falls back to a two-block sliding window for phrases split across captions."""
    p = norm(phrase)
    for b in blocks:
        if b['s'] >= after and p in norm(b['t']):
            return b
    for i in range(len(blocks) - 1):
        if blocks[i]['s'] >= after and p in norm(blocks[i]['t'] + ' ' + blocks[i + 1]['t']):
            return blocks[i]
    return None


def load_scenes(path):
    spec = importlib.util.spec_from_file_location('user_scenes', path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(mod)
    return mod


def build(blocks, mod, runtime, mingap=0.8, maxdur=12.0, hold=3.2):
    items, cursor = [], 0.0
    for sid, cue in mod.CUES:
        b = find(blocks, cue, cursor)
        if not b:
            print(f"  !! CUE NOT FOUND for scene {sid}: {cue!r}")
            continue
        els = mod.BUILDERS[sid](maxdur)
        items.append({'id': sid, 'start': round(b['s'], 3), 'cue': b['t'],
                      'contentEnd': round(max(e.t0 + e.dur for e in els), 2)})
        cursor = b['s'] + 0.01
    items.sort(key=lambda x: x['start'])
    for i, it in enumerate(items):
        nxt = items[i + 1]['start'] if i + 1 < len(items) else runtime
        room = nxt - it['start'] - mingap
        it['dur'] = round(max(3.5, min(it['contentEnd'] + hold, room, maxdur)), 2)
        it['end'] = round(it['start'] + it['dur'], 2)
    return items


def validate(items, runtime):
    errs = []
    for i in range(len(items) - 1):
        a, b = items[i], items[i + 1]
        if a['end'] > b['start'] - 0.05:
            errs.append(f"OVERLAP {a['id']} ends {a['end']:.2f} but {b['id']} starts {b['start']:.2f}")
    for it in items:
        if it['start'] < 0 or it['end'] > runtime:
            errs.append(f"OUT OF BOUNDS {it['id']} {it['start']:.2f}-{it['end']:.2f} (runtime {runtime:.2f})")
        if it['dur'] < it['contentEnd'] + 0.2:
            errs.append(f"CUT MID-DRAW {it['id']} dur {it['dur']:.2f} but needs {it['contentEnd']:.2f}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--srt', required=True)
    ap.add_argument('--scenes')
    ap.add_argument('--out', default='timeline.json')
    ap.add_argument('--check-tail', help='last spoken sentence; proves the render did not truncate')
    ap.add_argument('--must-contain', nargs='*', default=[])
    ap.add_argument('--must-not-contain', nargs='*', default=[])
    a = ap.parse_args()

    blocks = parse_srt(a.srt)
    if not blocks:
        sys.exit(f"no caption blocks parsed from {a.srt}")
    runtime = blocks[-1]['e']
    print(f"{len(blocks)} caption blocks, runtime {int(runtime)//60:02d}:{runtime%60:06.3f}")

    full = norm(' '.join(b['t'] for b in blocks))
    bad = 0
    if a.check_tail:
        ok = norm(a.check_tail) in full
        print(f"  {'OK  ' if ok else 'MISS'} tail present: {a.check_tail!r}")
        bad += not ok
    for m in a.must_contain:
        ok = norm(m) in full
        print(f"  {'OK  ' if ok else 'MISS'} must contain: {m!r}")
        bad += not ok
    for m in a.must_not_contain:
        ok = norm(m) not in full
        print(f"  {'OK  ' if ok else 'FOUND'} must NOT contain: {m!r}")
        bad += not ok
    if bad:
        sys.exit(f"\n{bad} SRT check(s) failed. The a-roll does not match the final script. Stop here.")

    if not a.scenes:
        print("\nSRT checks passed. Pass --scenes to build a timeline.")
        return

    mod = load_scenes(a.scenes)
    items = build(blocks, mod, runtime)
    errs = validate(items, runtime)
    print(f"\n{'id':>5} {'start':>9} {'end':>9} {'dur':>6}")
    for it in items:
        print(f"{it['id']:>5} {it['start']:>9.3f} {it['end']:>9.3f} {it['dur']:>6.2f}   {it['cue'][:52]}")
    cov = sum(i['dur'] for i in items)
    pct = cov / runtime * 100
    print(f"\ncoverage {cov:.1f}s / {runtime:.1f}s = {pct:.1f}%")
    if pct < 35:
        print(f"!! BELOW THE 35% FLOOR. You need about {(0.35*runtime - cov):.0f}s more cutaway.")
    print("VALIDATOR:", "PASS" if not errs else "FAIL")
    for e in errs:
        print("  !", e)
    if errs:
        sys.exit(1)
    json.dump(items, open(a.out, 'w'), indent=1)
    print(f"wrote {a.out}")


if __name__ == '__main__':
    main()
