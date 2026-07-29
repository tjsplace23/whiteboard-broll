---
name: whiteboard-broll
description: Build a hand-drawn whiteboard B-roll layer for a talking-head video and composite it onto the A-roll, with every cut locked to the video's own caption file. Use when someone wants B-roll, cutaways, or motion graphics for a video and has an MP4 plus an SRT. Trigger on "make b-roll for this video", "add cutaways", "whiteboard animation", "build a b-roll layer", "I have a script and an srt", or "my AI video needs visuals". Renders in pure Python — no browser, no Remotion, no AI generation credits.
---

# Whiteboard B-roll

Turns a talking-head video into an edited one. You bring an `a-roll.mp4` and its `.srt`; this builds animated hand-drawn whiteboard scenes and source-stamped evidence cards, anchors each to the exact second the matching sentence is spoken, and composites the whole thing to a publish-ready MP4.

**Everything renders with Pillow and ffmpeg.** No headless browser, no Remotion, no generation credits. A 23-cutaway layer for a 17-minute video comes out to about 1.8 MB and a few minutes of CPU.

## The one rule that makes this look good

**Every drawn element must depict something real and specific** — an actual filename, an actual number, an actual step, an actual quoted line. A whiteboard drawing of a real retention curve is evidence rendered legible. A glowing ring is decoration, and decoration is why AI videos look cheap.

Test before adding any scene: **point at the specific real thing it depicts.** If you can't name it, cut it.

This matters beyond taste. YouTube's monetization policy names content that "stitches together unrelated or inconsistent AI clips" as violative. Cutaways that don't connect to the sentence under them are a risk, not just weak craft.

## Workflow

### 1. Read the transcript and pick the moments

Parse the `.srt` first. Find the 12–25 places where a *specific, showable thing* is said — a number, a filename, a comparison, a list, a failure. Those are your scenes. Ignore the rest.

Write each one down as: **cue phrase → what the board shows.**

### 2. Verify the SRT actually matches the script

Before anything else, run the marker check **both directions**: pick 3–4 phrases unique to the final script and confirm they're in the SRT, and 3–4 from any superseded draft and confirm they are *not*. Then confirm the last spoken sentence is present — if it isn't, the render truncated and everything downstream is built on a broken file.

```bash
python3 scripts/anchor.py --srt caption.srt --check-tail "your last sentence here"
```

### 3. Author the scenes

Define scenes in a Python file using the element API (see `references/scene-authoring.md`). Start from `references/example_scenes.py`.

```python
def S1(d):
    return [
        Text(300, 330, ['Paste your script', 'into the box.'], CA, 130, INK, 0.2, 1.6),
        Line((280, 430), (1430, 452), ORANGE, 12, 2.1, 0.6),      # strike it through
    ]
```

Every element takes `t0` (when it starts drawing) and `dur` (how long the stroke takes). Text writes on left-to-right like a marker. Lines, boxes, arrows and circles draw progressively. A seeded jitter keeps it hand-drawn instead of vector-perfect.

### 4. Anchor to the caption file

```bash
python3 scripts/anchor.py --srt caption.srt --scenes my_scenes.py --out timeline.json
```

Each scene names a **cue phrase**. The anchor finds the caption block containing it and pins the scene there. Re-record with different pacing and everything re-snaps — you never touch a timeline.

It also **validates**: no overlapping cutaways, nothing out of bounds, no scene cut off mid-draw. Fix what it reports before rendering; the check is in the tool so it can't be skipped in review.

### 5. Render and composite

Run the bundled demo first if you have never used this — `./examples/demo/make.sh`
builds a stand-in A-roll and takes it all the way to a finished MP4, so you can see
the shape of the output before authoring anything.

```bash
python3 scripts/render.py --timeline timeline.json --scenes my_scenes.py --out clips/ --pocket
python3 scripts/composite.py --aroll a-roll.mp4 --timeline timeline.json --clips clips/ --out FINAL.mp4 --pocket
```

`--pocket` keeps the presenter on screen in a bottom-right inset during every cutaway,
so a long hold never fully loses the face. Pass it to **both** commands or neither.
With it on, the pocket owns `x >= 1340, y >= 729` — keep body content clear of it.

`composite.py` writes a chunked, resumable shell script. Each chunk finishes independently, so a killed job resumes instead of restarting.

## Hard-won gotchas

- **A non-empty output file is not a finished file.** A render killed mid-write leaves a plausible-looking MP4 with no moov atom, and a size check will happily call it done. Validate every part with `ffprobe` against its expected duration. `composite.py` does this; don't bypass it.
- **Aim for 35%+ coverage.** Below that the talking head dominates and average view duration drops. Never hold the avatar longer than ~12 seconds without a cut. If your plan is under 35%, the tool says so — believe it rather than shipping and hoping.
- **Never reuse the same graphic twice in one video.** Repetition is what drags retention. Specific evidence never repeats, which is the practical reason the "must depict something real" rule works.
- **Delivery is ~175 words per minute**, not the 130 most estimators assume. Check runtime against the SRT, not the script.

## Evidence cards

For quoting a real API response, a policy page, or a document, use `Card` instead of a whiteboard scene: real text, rebuilt clean for legibility, **with its source stamped on screen**. Rebuilt for readability, never invented. Redact anything private before it renders — emails, keys, account IDs, customer data.

## Layout

- 1920×1080 at 25 fps by default (match your A-roll's frame rate — check with `ffprobe`).
- Palette lives at the top of `scripts/wb.py`. Default is cream `#F5F3EE`, ink `#0E0E0E`, accent `#FF4D00`. Change those three constants to rebrand everything.
- Keep text inside x: 150–1780. Check legibility at phone size before committing.

## Fonts

Bundled in `assets/fonts/`: Caveat (marker), Patrick Hand (print), Roboto Mono (code and IDs). All SIL Open Font License — see `assets/fonts/OFL.txt`. Swap in any TTF by dropping it in and using its filename stem.
