"""Example scenes file. Copy this, replace with the real things YOUR video shows.

Every element here depicts something specific and checkable. That is the whole rule:
if you can't point at the real thing a drawing represents, it's decoration - cut it.

Render a preview of any scene without building the whole video:

    python3 -c "
    import sys; sys.path[:0]=['scripts','.']
    from wb import render_scene
    from example_scenes import BUILDERS
    render_scene('1', BUILDERS['1'](8), 8, 'preview', preview=100)"
"""
from wb import *

CA, PH, MO = 'caveat', 'patrick-hand', 'roboto-mono'


def S1(d):
    """A claim, struck through. Use for 'everyone tells you X - that's wrong'."""
    return [
        Text(300, 330, ['Paste your script', 'into the box.'], CA, 130, INK, 0.2, 1.6, seed=11),
        Line((280, 430), (1430, 452), ORANGE, 12, 2.1, 0.6, seed=12),
        Line((280, 620), (1180, 640), ORANGE, 12, 2.5, 0.5, seed=13),
        Text(300, 760, ['- every tutorial on YouTube'], PH, 52, GREY, 3.1, 1.0, seed=14),
    ]


def S2(d):
    """A real proportion, drawn to scale. Here: a 13,295-char script cut at 12,431.

    Note the geometry: the bar stops at x=1300 and every label sits left of it.
    The presenter pocket owns x>=1340, y>=729 - anything drawn there is hidden."""
    x0, x1, y = 220, 1300, 470
    cut = x0 + int((12431 / 13295) * (x1 - x0))
    return [
        Text(220, 250, ['13,295 characters'], PH, 62, INK, 0.1, 0.9, seed=21),
        Box((x0, y, x1, y + 130), INK, 5, 0.6, 0.7, seed=22),
        Line((cut, y - 55), (cut, y + 190), ORANGE, 11, 1.5, 0.4, seed=23),
        Text(cut - 10, y - 130, ['12,431'], CA, 96, ORANGE, 1.8, 0.7, align='right', seed=24),
        Shade((cut + 6, y + 5, x1 - 5, y + 125), GREY, 3, 2.3, 0.8),
        Text(x1, y + 200, ['what got cut'], PH, 42, GREY, 3.2, 1.0, align='right', seed=25),
        Text(220, y + 200, ['rendered'], PH, 42, INK, 2.8, 0.5, seed=26),
    ]


def S3(d):
    """A pipeline. Accent the step that carries the argument."""
    labels, els = ['INPUT', 'STEP', 'OUTPUT'], []
    x, y, bw, gap = 300, 440, 380, 90
    for i, lab in enumerate(labels):
        col = ORANGE if i == 1 else INK
        t = 0.1 + i * 0.7
        els.append(Box((x, y, x + bw, y + 180), col, 6, t, 0.45, seed=31 + i))
        els.append(Text(x + bw // 2, y + 55, [lab], PH, 64, col, t + 0.3, 0.35,
                        align='center', seed=41 + i))
        if i < len(labels) - 1:
            els.append(Arrow((x + bw + 6, y + 90), (x + bw + gap - 6, y + 90),
                             GREY, 6, t + 0.5, 0.25))
        x += bw + gap
    return els


def S4(d):
    """A numbered list with the payoff line accented and underlined."""
    return [
        Text(240, 200, ['DO THIS FIRST'], PH, 62, ORANGE, 0.1, 0.8, seed=51),
        Text(240, 360, ['1.  Connect it once'], PH, 68, INK, 0.9, 1.1, seed=52),
        Text(240, 500, ['2.  Ask what it can see'], PH, 68, INK, 2.1, 1.2, seed=53),
        Text(240, 640, ['3.  Write down the ID'], PH, 68, ORANGE, 3.4, 1.2, seed=54),
        Line((235, 745), (900, 757), ORANGE, 8, 4.7, 0.4, seed=55),
    ]


def S5(d):
    """A real subtraction. Two timestamps, a rule, the answer."""
    return [
        Text(700, 250, ['01:38:12'], MO, 96, INK, 0.1, 0.9, seed=61),
        Text(700, 400, ['01:32:31'], MO, 96, INK, 1.1, 0.9, seed=62),
        Text(600, 400, ['-'], MO, 96, INK, 2.0, 0.2, seed=63),
        Line((590, 540), (1200, 552), INK, 7, 2.3, 0.5, seed=64),
        Text(600, 600, ['6 min 41 sec'], CA, 150, ORANGE, 2.9, 1.2, seed=65),
    ]


BUILDERS = {'1': S1, '2': S2, '3': S3, '4': S4, '5': S5}

# (scene_id, cue phrase found in the .srt). Order matters - matching walks forward.
CUES = [
    ('1', 'paste your script into the box'),
    ('2', 'twelve thousand four hundred and thirty-one'),
    ('3', 'here is the whole pipeline'),
    ('4', 'do this before you do anything else'),
    ('5', 'six minutes and forty-one seconds'),
]
