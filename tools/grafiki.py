"""Общие функции для SVG-чертежей в материалах: клетчатая плоскость, графики, точки.
Чертёж задаётся в математических координатах, перевод в пиксели — здесь."""
import math

class Plane:
    def __init__(self, xmin, xmax, ymin, ymax, cell=26, grid=True, ink='#000', gridc='#bbb',
                 labels=True, unit_labels=True, xlabel='x', ylabel='y', paper='#fff'):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.c = cell; self.ink = ink; self.parts = []; self.paper = paper
        self.W = (xmax - xmin) * cell; self.H = (ymax - ymin) * cell
        if grid:
            for i in range(math.ceil(xmin), math.floor(xmax) + 1):
                X = self.px(i, 0)[0]
                self.parts.append(f'<line x1="{X:.1f}" y1="0" x2="{X:.1f}" y2="{self.H:.1f}" stroke="{gridc}" stroke-width="0.6"/>')
            for j in range(math.ceil(ymin), math.floor(ymax) + 1):
                Y = self.px(0, j)[1]
                self.parts.append(f'<line x1="0" y1="{Y:.1f}" x2="{self.W:.1f}" y2="{Y:.1f}" stroke="{gridc}" stroke-width="0.6"/>')
        # оси
        if xmin < 0 < xmax or ymin < 0 < ymax:
            ox, oy = self.px(0, 0)
            self.parts.append(f'<line x1="0" y1="{oy:.1f}" x2="{self.W - 2:.1f}" y2="{oy:.1f}" stroke="{ink}" stroke-width="1.3"/>')
            self.parts.append(f'<path d="M{self.W:.1f},{oy:.1f} l-9,-3.5 v7 z" fill="{ink}"/>')
            self.parts.append(f'<line x1="{ox:.1f}" y1="{self.H:.1f}" x2="{ox:.1f}" y2="2" stroke="{ink}" stroke-width="1.3"/>')
            self.parts.append(f'<path d="M{ox:.1f},0 l-3.5,9 h7 z" fill="{ink}"/>')
            if labels:
                self.text(self.xmax - 0.35, -0.45, xlabel, italic=True)
                self.text(0.3, self.ymax - 0.45, ylabel, italic=True, anchor='start')
                self.text(-0.3, -0.5, '0', anchor='end')
            if unit_labels:
                self.text(1, -0.55, '1')
                self.text(-0.3, 0.85, '1', anchor='end')

    def px(self, x, y):
        return ((x - self.xmin) * self.c, (self.ymax - y) * self.c)

    def text(self, x, y, s, size=14, italic=False, anchor='middle', color=None, bold=False):
        X, Y = self.px(x, y)
        st = ' font-style="italic"' if italic else ''
        bw = ' font-weight="700"' if bold else ''
        self.parts.append(f'<text x="{X:.1f}" y="{Y + size*0.35:.1f}" font-size="{size}" text-anchor="{anchor}"{st}{bw} '
                          f'fill="{color or self.ink}" font-family="inherit">{s}</text>')

    def curve(self, f, a, b, n=400, color=None, width=2, dash=None, clip=True):
        pts, segs = [], []
        for k in range(n + 1):
            x = a + (b - a) * k / n
            try:
                y = f(x)
            except (ValueError, ZeroDivisionError):
                y = None
            if y is None or (clip and not (self.ymin - 0.2 <= y <= self.ymax + 0.2)):
                if len(pts) > 1: segs.append(pts)
                pts = []; continue
            pts.append(self.px(x, y))
        if len(pts) > 1: segs.append(pts)
        d = ' '.join('M' + ' L'.join(f'{X:.1f},{Y:.1f}' for X, Y in s) for s in segs)
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color or self.ink}" stroke-width="{width}"{da} stroke-linejoin="round"/>')

    def line_through(self, p, q, color=None, width=2, dash=None):
        (x1, y1), (x2, y2) = p, q
        if x1 == x2:
            self.seg((x1, self.ymin), (x1, self.ymax), color, width, dash); return
        k = (y2 - y1) / (x2 - x1)
        self.curve(lambda x: y1 + k * (x - x1), self.xmin, self.xmax, n=2, color=color, width=width, dash=dash, clip=False)

    def seg(self, p, q, color=None, width=2, dash=None):
        (X1, Y1), (X2, Y2) = self.px(*p), self.px(*q)
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<line x1="{X1:.1f}" y1="{Y1:.1f}" x2="{X2:.1f}" y2="{Y2:.1f}" stroke="{color or self.ink}" stroke-width="{width}"{da}/>')

    def circle(self, cx, cy, r, color=None, width=2, dash=None, fill='none'):
        X, Y = self.px(cx, cy)
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r*self.c:.1f}" fill="{fill}" stroke="{color or self.ink}" stroke-width="{width}"{da}/>')

    def dot(self, x, y, color=None, hollow=False, r=3.6):
        X, Y = self.px(x, y)
        fill = self.paper if hollow else (color or self.ink)
        self.parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r}" fill="{fill}" stroke="{color or self.ink}" stroke-width="1.6"/>')

    def svg(self, extra_class='fig'):
        pad = 6
        return (f'<svg class="{extra_class}" viewBox="{-pad} {-pad} {self.W + 2*pad:.1f} {self.H + 2*pad:.1f}" '
                f'width="{self.W + 2*pad:.0f}" height="{self.H + 2*pad:.0f}" xmlns="http://www.w3.org/2000/svg">'
                + ''.join(self.parts) + '</svg>')


class Sketch:
    """Геометрический чертёж без сетки: точки в условных координатах, y вверх."""
    def __init__(self, xmin, xmax, ymin, ymax, scale=40, ink='#000', accent=None):
        self.xmin, self.ymax, self.s = xmin, ymax, scale
        self.W = (xmax - xmin) * scale; self.H = (ymax - ymin) * scale
        self.ink = ink; self.acc = accent or ink; self.parts = []

    def px(self, p):
        return ((p[0] - self.xmin) * self.s, (self.ymax - p[1]) * self.s)

    def poly(self, pts, close=True, color=None, width=1.8, fill='none', dash=None):
        d = ' '.join(f'{X:.1f},{Y:.1f}' for X, Y in map(self.px, pts))
        tag = 'polygon' if close else 'polyline'
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<{tag} points="{d}" fill="{fill}" stroke="{color or self.ink}" stroke-width="{width}"{da} stroke-linejoin="round"/>')

    def seg(self, p, q, color=None, width=1.8, dash=None):
        self.poly([p, q], close=False, color=color, width=width, dash=dash)

    def circle(self, c, r, color=None, width=1.8, dash=None):
        X, Y = self.px(c)
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r*self.s:.1f}" fill="none" stroke="{color or self.ink}" stroke-width="{width}"{da}/>')

    def dot(self, p, color=None, r=3):
        X, Y = self.px(p)
        self.parts.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r}" fill="{color or self.ink}"/>')

    def label(self, p, s, dx=0, dy=0, size=15, italic=True, color=None):
        X, Y = self.px(p)
        st = ' font-style="italic"' if italic else ''
        self.parts.append(f'<text x="{X + dx:.1f}" y="{Y + dy + size*0.35:.1f}" font-size="{size}" text-anchor="middle"{st} '
                          f'fill="{color or self.ink}" font-family="inherit">{s}</text>')

    def arc_angle(self, v, p, q, r=0.45, color=None, width=1.4, n=1):
        """дуга угла с вершиной v между лучами vp и vq"""
        a1 = math.atan2(p[1] - v[1], p[0] - v[0]); a2 = math.atan2(q[1] - v[1], q[0] - v[0])
        d = (a2 - a1) % (2 * math.pi)
        if d > math.pi: a1, a2, d = a2, a1, 2 * math.pi - d
        for k in range(n):
            rr = r + 0.08 * k
            pts = [(v[0] + rr * math.cos(a1 + d * i / 24), v[1] + rr * math.sin(a1 + d * i / 24)) for i in range(25)]
            self.poly(pts, close=False, color=color or self.acc, width=width)

    def right_angle(self, v, p, q, s=0.28, color=None):
        def u(a):
            L = math.hypot(a[0] - v[0], a[1] - v[1]); return ((a[0] - v[0]) / L, (a[1] - v[1]) / L)
        e1, e2 = u(p), u(q)
        A = (v[0] + s * e1[0], v[1] + s * e1[1]); B = (A[0] + s * e2[0], A[1] + s * e2[1]); C = (v[0] + s * e2[0], v[1] + s * e2[1])
        self.poly([A, B, C], close=False, color=color or self.ink, width=1.3)

    def text(self, p, s, size=14, color=None, anchor='middle', italic=False):
        X, Y = self.px(p)
        st = ' font-style="italic"' if italic else ''
        self.parts.append(f'<text x="{X:.1f}" y="{Y + size*0.35:.1f}" font-size="{size}" text-anchor="{anchor}"{st} '
                          f'fill="{color or self.ink}" font-family="inherit">{s}</text>')

    def svg(self, cls='fig'):
        pad = 14
        return (f'<svg class="{cls}" viewBox="{-pad} {-pad} {self.W + 2*pad:.1f} {self.H + 2*pad:.1f}" '
                f'width="{self.W + 2*pad:.0f}" height="{self.H + 2*pad:.0f}" xmlns="http://www.w3.org/2000/svg">'
                + ''.join(self.parts) + '</svg>')


def on_circle(c, r, deg):
    return (c[0] + r * math.cos(math.radians(deg)), c[1] + r * math.sin(math.radians(deg)))
