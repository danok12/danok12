"""Общие средства для SVG-чертежей в решениях по статике.

Палитра, стрелки-маркеры, подписи с индексами (X_{A}, x^{2}), опоры, размеры.
Экранные координаты: x вправо, y вниз; углы в arc() — математические
(против часовой — плюс).
"""
import math
import re

INK, LOAD, REAC, INT, DIM, GRAY = "#1d2b30", "#b3402d", "#0f6b73", "#6a3d9a", "#6f7f86", "#8a979c"
FONT = "'Source Sans 3','Liberation Sans','DejaVu Sans',sans-serif"
MARK = {"load": (LOAD, 12, 8), "loadS": (LOAD, 8, 5.5), "reac": (REAC, 12, 8),
        "int": (INT, 12, 8), "dim": (DIM, 9, 6), "gray": (GRAY, 10, 7), "ink": (INK, 10, 7)}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rich(s, size):
    """Разметка подписей: X_{A} — индекс, x^{2} — степень."""
    out, shift = [], 0.0
    for p in re.split(r"([_^]\{[^}]*\})", s):
        if not p:
            continue
        if p[0] in "_^" and len(p) > 2 and p[1] == "{":
            d = size * 0.3 if p[0] == "_" else -size * 0.4
            out.append(f'<tspan dy="{d - shift:.1f}" font-size="{size * 0.72:.1f}">{esc(p[2:-1])}</tspan>')
            shift = d
        else:
            out.append(f'<tspan dy="{-shift:.1f}">{esc(p)}</tspan>' if shift else esc(p))
            shift = 0.0
    return "".join(out)


class Svg:
    def __init__(self, sid, w, h):
        self.sid, self.w, self.h, self.items = sid, w, h, []

    def add(self, s):
        self.items.append(s)

    def line(self, x1, y1, x2, y2, col=INK, w=1.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{col}" stroke-width="{w}"{d} stroke-linecap="round"/>')

    def poly(self, pts, col=INK, w=2.0, fill="none", close=False, dash=None):
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + (" Z" if close else "")
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="{fill}"{da} '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')

    def arrow(self, x1, y1, x2, y2, kind="load", w=1.8, dash=None):
        col, L, _ = MARK[kind]
        ln = math.hypot(x2 - x1, y2 - y1)
        sh = L * 0.6
        ux, uy = (x2 - x1) / ln, (y2 - y1) / ln
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - ux * sh:.1f}" y2="{y2 - uy * sh:.1f}" '
                 f'stroke="{col}" stroke-width="{w}"{d} marker-end="url(#{self.sid}-{kind})"/>')

    def arc(self, cx, cy, r, a1, a2, kind="int", w=1.6, head=True):
        """Дуга от угла a1 к a2 (градусы, против часовой — плюс, как в математике)."""
        col = MARK[kind][0]
        p1 = (cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1)))
        p2 = (cx + r * math.cos(math.radians(a2)), cy - r * math.sin(math.radians(a2)))
        large = 1 if abs(a2 - a1) > 180 else 0
        sweep = 0 if a2 > a1 else 1
        m = f' marker-end="url(#{self.sid}-{kind})"' if head else ""
        self.add(f'<path d="M{p1[0]:.1f},{p1[1]:.1f} A{r},{r} 0 {large},{sweep} {p2[0]:.1f},{p2[1]:.1f}" '
                 f'fill="none" stroke="{col}" stroke-width="{w}"{m}/>')

    def text(self, x, y, s, col=INK, size=13, anchor="start", weight="normal", rot=None, halo=True, italic=False):
        tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
        ha = ' paint-order="stroke" stroke="#fff" stroke-width="3.5" stroke-linejoin="round"' if halo else ""
        it = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{col}" text-anchor="{anchor}" '
                 f'font-weight="{weight}"{it}{tr}{ha}>{rich(s, size)}</text>')

    def hinge(self, x, y, r=4.6):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="1.6"/>')

    def dot(self, x, y, r=3.2, col=INK):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"/>')

    def support(self, x, y):
        """Шарнирно-неподвижная опора."""
        self.poly([(x, y), (x - 13, y + 20), (x + 13, y + 20)], INK, 1.3, fill="#fff", close=True)
        self.line(x - 22, y + 20, x + 22, y + 20, INK, 1.4)
        for i in range(-20, 23, 6):
            self.line(x + i, y + 20, x + i - 6, y + 27, INK, 0.9)
        self.hinge(x, y)

    def qload(self, xa, xb, ytop, ybot, n):
        self.line(xa, ytop, xb, ytop, LOAD, 1.5)
        for i in range(n + 1):
            x = xa + (xb - xa) * i / n
            self.arrow(x, ytop, x, ybot, "loadS", 1.1)

    def tick(self, x, y):
        self.line(x - 4, y + 4, x + 4, y - 4, DIM, 1.5)

    def dim_h(self, xa, xb, y, label, size=12.5):
        self.line(xa - 5, y, xb + 5, y, DIM, 0.9)
        self.tick(xa, y)
        self.tick(xb, y)
        self.text((xa + xb) / 2, y - 5, label, DIM, size, "middle")

    def dim_v(self, x, ya, yb, label, side=-1, size=12.5):
        self.line(x, ya - 5, x, yb + 5, DIM, 0.9)
        self.tick(x, ya)
        self.tick(x, yb)
        tx = x + (-6 if side < 0 else 15)
        self.text(tx, (ya + yb) / 2, label, DIM, size, "middle", rot=-90)

    def ext(self, x1, y1, x2, y2):
        self.line(x1, y1, x2, y2, DIM, 0.7, "3 3")

    def svg(self, label):
        defs = "".join(
            f'<marker id="{self.sid}-{k}" viewBox="0 0 {L} {W}" refX="{L - L * 0.6:.1f}" refY="{W / 2}" '
            f'markerWidth="{L}" markerHeight="{W}" markerUnits="userSpaceOnUse" orient="auto">'
            f'<path d="M0,0 L{L},{W / 2} L0,{W} Z" fill="{c}"/></marker>'
            for k, (c, L, W) in MARK.items())
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{esc(label)}" '
                f'font-family="{FONT}" xmlns="http://www.w3.org/2000/svg"><defs>{defs}</defs>'
                + "".join(self.items) + "</svg>")
