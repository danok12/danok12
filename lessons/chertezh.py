"""Чертежи для листов: точные координаты → SVG в стиле серии (цвета берутся из токенов CSS).

    f = Fig()
    f.poly("ABCD", P)            многоугольник по именам точек
    f.seg(P["A"], P["E"], "r")   отрезок; классы: s — основной, b — петроль, r — коралл, d — пунктир
    f.circle(O, R)
    f.angle(V, A, B, n=1)        дуга угла AVB (n дуг — равные углы)
    f.right(V, A, B)             знак прямого угла
    f.name(P, "A", away=O)       подпись точки, отодвинутая от центра
    f.text(P, "7")               подпись величины
    svg = f.svg(width=360)
"""
import math

ARC_CLS = {"r": "arc", "b": "arcb"}


def pt(x, y):
    return (float(x), float(y))


def polar(r, deg, c=(0, 0)):
    a = math.radians(deg)
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def add(p, q, k=1):
    return (p[0] + k * q[0], p[1] + k * q[1])


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def mid(p, q):
    return ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)


def line_circle(p, d, c, r):
    """Точки пересечения прямой p + t·d с окружностью (c, r), по возрастанию t."""
    dx, dy = d
    fx, fy = p[0] - c[0], p[1] - c[1]
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    cc = fx * fx + fy * fy - r * r
    disc = math.sqrt(b * b - 4 * a * cc)
    ts = sorted([(-b - disc) / (2 * a), (-b + disc) / (2 * a)])
    return [add(p, d, t) for t in ts]


class Fig:
    def __init__(self):
        self.items = []          # (вид, данные)
        self.pts = []            # все точки — для рамки

    def _reg(self, *ps):
        self.pts.extend(ps)

    def seg(self, p, q, cls="s"):
        self._reg(p, q)
        self.items.append(("seg", p, q, cls))

    def poly(self, names, P, cls="s", fill=None):
        ps = [P[n] for n in names]
        self._reg(*ps)
        self.items.append(("poly", ps, cls, fill))

    def circle(self, c, r, cls="s"):
        self._reg((c[0] - r, c[1] - r), (c[0] + r, c[1] + r))
        self.items.append(("circle", c, r, cls))

    def dot(self, p):
        self._reg(p)
        self.items.append(("dot", p))

    def angle(self, v, a, b, r=0.9, n=1, cls="r"):
        self.items.append(("angle", v, a, b, r, n, cls))

    def right(self, v, a, b, s=0.55):
        self.items.append(("right", v, a, b, s))

    def name(self, p, text, away=None, d=0.75, ang=None):
        if ang is not None:
            off = polar(d, ang)
        else:
            off = unit(sub(p, away)) if away else (0, 1)
            off = (off[0] * d, off[1] * d)
        q = add(p, off)
        self._reg(q)
        self.items.append(("name", q, text))

    def text(self, p, text, cls="v"):
        self._reg(p)
        self.items.append(("text", p, text, cls))

    def svg(self, width=360, pad=0.9, label=""):
        xs = [p[0] for p in self.pts]
        ys = [p[1] for p in self.pts]
        x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
        k = width / (x1 - x0)
        h = (y1 - y0) * k
        X = lambda p: (p[0] - x0) * k
        Y = lambda p: (y1 - p[1]) * k
        f = lambda v: f"{v:.1f}"
        out = [f'<svg viewBox="0 0 {f(width)} {f(h)}" role="img" aria-label="{label}">']
        for it in self.items:
            kind = it[0]
            if kind == "seg":
                _, p, q, cls = it
                out.append(f'<line class="{cls}" x1="{f(X(p))}" y1="{f(Y(p))}" x2="{f(X(q))}" y2="{f(Y(q))}"/>')
            elif kind == "poly":
                _, ps, cls, fill = it
                pts = " ".join(f"{f(X(p))},{f(Y(p))}" for p in ps)
                if fill:
                    out.append(f'<polygon class="{fill}" points="{pts}"/>')
                out.append(f'<polygon class="{cls}" points="{pts}"/>')
            elif kind == "circle":
                _, c, r, cls = it
                out.append(f'<circle class="{cls}" cx="{f(X(c))}" cy="{f(Y(c))}" r="{f(r * k)}"/>')
            elif kind == "dot":
                out.append(f'<circle class="pt" cx="{f(X(it[1]))}" cy="{f(Y(it[1]))}" r="3"/>')
            elif kind == "angle":
                _, v, a, b, r, n, cls = it
                a1 = math.atan2(a[1] - v[1], a[0] - v[0])
                a2 = math.atan2(b[1] - v[1], b[0] - v[0])
                dlt = (a2 - a1) % (2 * math.pi)
                if dlt > math.pi:              # рисуем меньший угол
                    a1, a2, dlt = a2, a1, 2 * math.pi - dlt
                for i in range(n):
                    rr = (r + 0.22 * i) * k
                    p1 = (X(v) + rr * math.cos(a1), Y(v) - rr * math.sin(a1))
                    p2 = (X(v) + rr * math.cos(a1 + dlt), Y(v) - rr * math.sin(a1 + dlt))
                    out.append(f'<path class="{ARC_CLS.get(cls, "arc")}" d="M{f(p1[0])},{f(p1[1])} '
                               f'A{f(rr)},{f(rr)} 0 0 0 {f(p2[0])},{f(p2[1])}"/>')
            elif kind == "right":
                _, v, a, b, s = it
                ua, ub = unit(sub(a, v)), unit(sub(b, v))
                p1, p3 = add(v, ua, s), add(v, ub, s)
                p2 = add(p1, ub, s)
                out.append(f'<polyline class="mk" points="{f(X(p1))},{f(Y(p1))} {f(X(p2))},{f(Y(p2))} '
                           f'{f(X(p3))},{f(Y(p3))}"/>')
            elif kind == "name":
                _, q, t = it
                out.append(f'<text class="nm" x="{f(X(q))}" y="{f(Y(q) + 6)}" text-anchor="middle">{t}</text>')
            elif kind == "text":
                _, q, t, cls = it
                out.append(f'<text class="{cls}" x="{f(X(q))}" y="{f(Y(q) + 5)}" text-anchor="middle">{t}</text>')
        out.append("</svg>")
        return "\n".join(out)


def grid(vectors, w=10, h=7, cell=34, label=""):
    """Клетчатая бумага w×h клеток и векторы [(начало, конец, подпись, класс, *точки)] в координатах клеток.
    Класс s — простой отрезок без стрелки; точка — ((x, y), имя, (сдвиг x, сдвиг y))."""
    W, H = w * cell + 2, h * cell + 2
    X = lambda x: 1 + x * cell
    Y = lambda y: 1 + (h - y) * cell
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}">',
           '<defs><marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path class="ahb" d="M0,0 L10,5 L0,10 z"/></marker>'
           '<marker id="ahr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path class="ahr" d="M0,0 L10,5 L0,10 z"/></marker></defs>']
    for i in range(w + 1):
        out.append(f'<line class="gr" x1="{X(i)}" y1="{Y(0)}" x2="{X(i)}" y2="{Y(h)}"/>')
    for j in range(h + 1):
        out.append(f'<line class="gr" x1="{X(0)}" y1="{Y(j)}" x2="{X(w)}" y2="{Y(j)}"/>')
    for v in vectors:
        a, b, name, cls = v[:4]
        mk = "" if cls == "s" else f' marker-end="url(#{"ahb" if cls == "b" else "ahr"})"'
        out.append(f'<line class="{cls}" x1="{X(a[0])}" y1="{Y(a[1])}" x2="{X(b[0])}" y2="{Y(b[1])}"{mk}/>')
        if name:
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy)
            off = (-dy / n * 0.45, dx / n * 0.45)       # слева по ходу вектора
            out.append(f'<text class="vn {cls}t" x="{X(m[0] + off[0]):.1f}" y="{Y(m[1] + off[1]) + 6:.1f}" '
                       f'text-anchor="middle">{name}</text>')
    for p in [q for v in vectors for q in v[4:]]:
        (x, y), t, (ox, oy) = p
        out.append(f'<circle class="pt" cx="{X(x)}" cy="{Y(y)}" r="3"/>')
        out.append(f'<text class="nm" x="{X(x + ox):.1f}" y="{Y(y + oy) + 6:.1f}" text-anchor="middle">{t}</text>')
    out.append("</svg>")
    return "\n".join(out)
