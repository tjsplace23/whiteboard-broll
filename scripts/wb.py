"""ASC whiteboard renderer — evidence rendered legible, never decoration.
Cream #F5F3EE / ink #0E0E0E / orange #FF4D00. 1920x1080 @ 25fps."""
import os, math, random
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 25

# Presenter pocket. When enabled, this rectangle is left pure black on every card
# and the compositor drops the A-roll into it, so the presenter is never fully off
# screen during a long hold. Keep body text clear of it.
POCKET = (1340, 729, 1880, 1033)          # x0, y0, x1, y1  -> 540x304, 16:9
CREAM = (245, 243, 238, 255)
INK   = (14, 14, 14, 255)
ORANGE= (255, 77, 0, 255)
GREY  = (120, 118, 112, 255)
FD = os.environ.get('WB_FONTS') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts')

_fc = {}
def F(name, size):
    k = (name, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(FD, name + '.ttf'), size)
    return _fc[k]

def ease(p):                      # smooth but with a little snap, like a pen
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 2.2

def _jit(seed, amp=2.0):
    r = random.Random(seed)
    return lambda: r.uniform(-amp, amp)


# ---------------------------------------------------------------- elements
class El:
    def __init__(self, t0, dur):
        self.t0, self.dur = t0, dur
    def prog(self, t):
        if self.dur <= 0: return 1.0 if t >= self.t0 else 0.0
        return ease((t - self.t0) / self.dur)


class Text(El):
    """Writes on left-to-right, line by line, like a marker."""
    def __init__(self, x, y, lines, font='caveat', size=64, color=INK,
                 t0=0.0, dur=1.0, spacing=1.25, align='left', seed=0):
        super().__init__(t0, dur)
        self.x, self.y = x, y
        self.lines = lines if isinstance(lines, list) else [lines]
        self.f = F(font, size); self.color = color
        self.lh = int(size * spacing); self.align = align; self.seed = seed

    def bbox(self):
        w = max(self.f.getbbox(l)[2] for l in self.lines) if self.lines else 0
        return (self.x, self.y, self.x + w, self.y + self.lh * len(self.lines))

    def draw(self, img, t):
        p = self.prog(t)
        if p <= 0: return
        n = len(self.lines)
        j = _jit(self.seed, 1.4)
        for i, ln in enumerate(self.lines):
            lo, hi = i / n, (i + 1) / n
            lp = 0.0 if p <= lo else (1.0 if p >= hi else (p - lo) / (hi - lo))
            if lp <= 0: continue
            w = self.f.getbbox(ln)[2] or 1
            layer = Image.new('RGBA', (w + 30, self.lh + 24), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            d.text((0, 0), ln, font=self.f, fill=self.color)
            if lp < 1.0:
                m = Image.new('L', layer.size, 0)
                ImageDraw.Draw(m).rectangle([0, 0, int(w * lp), layer.size[1]], fill=255)
                layer.putalpha(Image.composite(layer.split()[3], Image.new('L', layer.size, 0), m))
            ox = self.x
            if self.align == 'center': ox = self.x - w // 2
            elif self.align == 'right': ox = self.x - w
            img.alpha_composite(layer, (int(ox + j()), int(self.y + i * self.lh + j())))


class Line(El):
    def __init__(self, p1, p2, color=INK, wd=6, t0=0.0, dur=0.5, seed=0):
        super().__init__(t0, dur)
        self.p1, self.p2, self.color, self.wd, self.seed = p1, p2, color, wd, seed
    def draw(self, img, t):
        p = self.prog(t)
        if p <= 0: return
        j = _jit(self.seed, 2.2)
        x1, y1 = self.p1; x2, y2 = self.p2
        x2 = x1 + (x2 - x1) * p; y2 = y1 + (y2 - y1) * p
        ImageDraw.Draw(img).line([x1 + j(), y1 + j(), x2 + j(), y2 + j()],
                                 fill=self.color, width=self.wd)


class Box(El):
    def __init__(self, xy, color=INK, wd=5, t0=0.0, dur=0.6, seed=0):
        super().__init__(t0, dur)
        self.xy, self.color, self.wd, self.seed = xy, color, wd, seed
    def draw(self, img, t):
        p = self.prog(t)
        if p <= 0: return
        x0, y0, x1, y1 = self.xy
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        segs = [(pts[i], pts[i + 1]) for i in range(4)]
        tot = sum(math.dist(a, b) for a, b in segs); run = tot * p
        d = ImageDraw.Draw(img); j = _jit(self.seed, 1.6)
        for a, b in segs:
            L = math.dist(a, b)
            if run <= 0: break
            f = min(1.0, run / L); run -= L
            bx = a[0] + (b[0] - a[0]) * f; by = a[1] + (b[1] - a[1]) * f
            d.line([a[0] + j(), a[1] + j(), bx + j(), by + j()], fill=self.color, width=self.wd)


class Circle(El):
    def __init__(self, xy, color=ORANGE, wd=6, t0=0.0, dur=0.6, seed=0):
        super().__init__(t0, dur)
        self.xy, self.color, self.wd, self.seed = xy, color, wd, seed
    def draw(self, img, t):
        p = self.prog(t)
        if p <= 0: return
        x0, y0, x1, y1 = self.xy
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
        d = ImageDraw.Draw(img); r = random.Random(self.seed)
        steps = max(2, int(150 * p)); prev = None
        for i in range(steps + 1):
            a = -0.4 + (2 * math.pi + 0.5) * (i / 150)
            x = cx + rx * math.cos(a) + r.uniform(-2, 2)
            y = cy + ry * math.sin(a) + r.uniform(-2, 2)
            if prev: d.line([prev[0], prev[1], x, y], fill=self.color, width=self.wd)
            prev = (x, y)


class Arrow(El):
    def __init__(self, p1, p2, color=ORANGE, wd=6, t0=0.0, dur=0.5, seed=0):
        super().__init__(t0, dur)
        self.p1, self.p2, self.color, self.wd, self.seed = p1, p2, color, wd, seed
    def draw(self, img, t):
        p = self.prog(t)
        if p <= 0: return
        x1, y1 = self.p1; x2, y2 = self.p2
        ex = x1 + (x2 - x1) * p; ey = y1 + (y2 - y1) * p
        d = ImageDraw.Draw(img)
        d.line([x1, y1, ex, ey], fill=self.color, width=self.wd)
        if p > 0.75:
            ang = math.atan2(y2 - y1, x2 - x1); hl = 26
            for s in (2.6, -2.6):
                d.line([ex, ey, ex + hl * math.cos(ang + s), ey + hl * math.sin(ang + s)],
                       fill=self.color, width=self.wd)


class Shade(El):
    """Diagonal hatch — used to shade out the truncated remainder."""
    def __init__(self, xy, color=GREY, wd=3, t0=0.0, dur=0.6, gap=22):
        super().__init__(t0, dur)
        self.xy, self.color, self.wd, self.gap = xy, color, wd, gap
    def draw(self, img, t):
        p = self.prog(t)
        if p <= 0: return
        x0, y0, x1, y1 = self.xy
        d = ImageDraw.Draw(img)
        xs = list(range(int(x0), int(x1 + (y1 - y0)), self.gap))
        for k, sx in enumerate(xs):
            if k / max(1, len(xs)) > p: break
            ax, ay = sx, y0; bx, by = sx - (y1 - y0), y1
            ax, bx = max(x0, min(x1, ax)), max(x0, min(x1, bx))
            d.line([ax, ay, bx, by], fill=self.color, width=self.wd)


# ---------------------------------------------------------------- scene
def render_scene(scene_id, elements, dur, outdir, hold_tail=0.5, preview=None,
                 pocket=False):
    """Render a scene to PNG frames. pocket=True reserves the presenter pocket."""
    os.makedirs(outdir, exist_ok=True)
    n = int(round(dur * FPS))
    frames = [preview] if preview is not None else range(n)
    for i in frames:
        t = i / FPS
        img = Image.new('RGBA', (W, H), CREAM)
        for el in elements:
            el.draw(img, t)
        if pocket:
            d = ImageDraw.Draw(img)
            x0, y0, x1, y1 = POCKET
            r = random.Random(99)
            for k in range(3):                      # hand-drawn pocket frame
                d.rectangle([x0 - 5 + r.uniform(-2, 2), y0 - 5 + r.uniform(-2, 2),
                             x1 + 5 + r.uniform(-2, 2), y1 + 5 + r.uniform(-2, 2)],
                            outline=GREY, width=2)
            d.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 255))
        img.convert('RGB').save(os.path.join(outdir, f'{i:05d}.png'),
                                'PNG', compress_level=1)
    return n
