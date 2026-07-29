# Scene authoring

A scenes file exports two things:

```python
from wb import *

CA, PH, MO = 'caveat', 'patrick-hand', 'roboto-mono'   # marker, print, code

def S1(d):                      # d = the scene's duration, usually ignored
    return [ ... elements ... ]

BUILDERS = {'1': S1, '2': S2}
CUES     = [('1', 'paste your script into the box'),    # anchor phrase from the SRT
            ('2', 'twelve thousand four hundred')]
```

`CUES` is an ordered list of `(scene_id, cue_phrase)`. The phrase is matched case- and
punctuation-insensitively against the captions, searching forward from the previous
scene, so the same words appearing twice won't misfire.

## Elements

Every element takes `t0` (seconds into the scene when it starts drawing) and `dur`
(how long the stroke takes). Give each a distinct `seed` so the hand-jitter differs.

| Element | Signature |
|---|---|
| `Text` | `Text(x, y, lines, font, size, color, t0, dur, spacing=1.25, align='left', seed=0)` |
| `Line` | `Line((x1,y1), (x2,y2), color, width, t0, dur, seed=0)` |
| `Box` | `Box((x0,y0,x1,y1), color, width, t0, dur, seed=0)` |
| `Circle` | `Circle((x0,y0,x1,y1), color, width, t0, dur, seed=0)` |
| `Arrow` | `Arrow((x1,y1), (x2,y2), color, width, t0, dur, seed=0)` |
| `Shade` | `Shade((x0,y0,x1,y1), color, width, t0, dur, gap=22)` |
| `Card` | `Card(title, lines, source, t0, dur, hi=())` — see below |

`lines` on `Text` is a list; each line writes on in turn across the total `dur`.
`align` accepts `'left'`, `'center'`, `'right'` — right-align is how you keep a long
label from running off frame.

Colors: `INK`, `ORANGE`, `GREY`, `CREAM`, or any RGBA tuple.

## Patterns that work

**Strike something through.** Write it, then draw an accent line across it.
```python
Text(300, 330, ['Paste your script into the box.'], CA, 130, INK, 0.2, 1.6, seed=11),
Line((280, 430), (1430, 452), ORANGE, 12, 2.1, 0.6, seed=12),
```

**Show a proportion honestly.** Draw the whole, cut it, shade the loss.
```python
Box((220, 470, 1720, 600), INK, 5, 0.6, 0.7),
Line((1622, 415), (1622, 660), ORANGE, 11, 1.5, 0.4),      # the cut, to scale
Shade((1628, 475, 1715, 595), GREY, 3, 2.3, 0.8),          # what was lost
```

**Circle the word that matters** — after it has written on, not before.
```python
Text(260, 500, ['2.  wrong engine   ->  SILENT'], MO, 46, INK, 2.3, 1.1),
Circle((962, 484, 1160, 566), ORANGE, 6, 3.5, 0.6),
```
Measure where the word actually falls instead of guessing:
```python
from wb import F
x0 = 260 + F('roboto-mono', 46).getbbox('2.  wrong engine   ->  ')[2]
```

**A pipeline.** Boxes and arrows, each appearing in order, accent on the parts that matter.

## Evidence cards

For real quoted material — an API response, a policy page, a document:

```python
Card("HeyGen account - live response", [
    '{',
    '  "plan": "creator",',
    '  "remaining": 168,',
    '}',
], "source: HeyGen API - get_current_user - pulled 2026-07-27",
   t0=0.15, dur=2.6, hi=(1, 2))
```

`hi` is the set of line indices to accent. The source stamp is not optional — it is
what separates a rebuilt-for-legibility quote from an invented one.

**Redact before rendering.** Emails, API keys, account IDs, customer names. Write
`"[ redacted ]"` in place of the value; don't rely on blurring later.

Cards auto-size: 11 lines or fewer render at full size, more shrink to fit. Keep them
under about 13 lines or the point is lost anyway.

## Timing

- A scene holds for `content_end + ~3s` so the finished board can be read.
- 5–10 seconds each is the useful range. Under 4s nobody reads it; over 12s it's a still.
- Aim for 12–25 scenes in a 15–20 minute video.

## Layout

1920×1080. Keep text within x: 150–1780, y: 150–950.

**If you use `--pocket`, the presenter pocket owns `x ≥ 1340, y ≥ 729`.** Anything drawn
there is covered by the A-roll inset and nobody will ever read it. Either keep body
content left of x=1300, or above y=700 if it needs the full width. `examples/demo`
shows the safe geometry. Check legibility at phone size —
if a line is unreadable at 400px wide, it's decoration with extra steps.
