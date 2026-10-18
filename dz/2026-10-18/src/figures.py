"""Чертежи многогранников (SVG, косоугольная проекция) и расчёт сечений.

Невидимые рёбра определяются по нормалям граней, а не вручную. Сечение считается
как пересечение плоскости с рёбрами выпуклого многогранника — по нему пишется
ответ (вид многоугольника, на каких рёбрах вершины, в каком отношении делят ребро).
"""
import math

import sympy as sp

R = sp.Rational
K, PHI = 0.5, math.radians(40)          # сокращение и угол оси глубины
DVIEW = (-K * math.cos(PHI), 1.0, -K * math.sin(PHI))   # направление «в экран»


class Solid:
    def __init__(self, verts, faces):
        self.v = {k: tuple(sp.nsimplify(c) for c in p) for k, p in verts.items()}
        self.faces = faces
        edges = set()
        for f in faces:
            for i in range(len(f)):
                e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
                edges.add(e)
        self.edges = sorted(edges)

    def centroid(self):
        n = len(self.v)
        return tuple(sum(p[i] for p in self.v.values()) / n for i in range(3))

    def visible_faces(self):
        c = [float(t) for t in self.centroid()]
        vis = []
        for f in self.faces:
            p0, p1, p2 = [[float(t) for t in self.v[k]] for k in f[:3]]
            u = [p1[i] - p0[i] for i in range(3)]
            w = [p2[i] - p0[i] for i in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            fc = [sum(float(self.v[k][i]) for k in f) / len(f) for i in range(3)]
            if sum(n[i] * (fc[i] - c[i]) for i in range(3)) < 0:
                n = [-t for t in n]
            vis.append(sum(n[i] * DVIEW[i] for i in range(3)) < -1e-9)
        return vis

    def hidden_edges(self):
        vis = self.visible_faces()
        hid = set()
        for e in self.edges:
            adj = [vis[i] for i, f in enumerate(self.faces) if e[0] in f and e[1] in f and
                   abs(f.index(e[0]) - f.index(e[1])) in (1, len(f) - 1)]
            if not any(adj):
                hid.add(e)
        return hid


def proj(p):
    x, y, z = [float(t) for t in p]
    return (x + K * y * math.cos(PHI), z + K * y * math.sin(PHI))


def point_on(solid, a, b, t):
    pa, pb = solid.v[a], solid.v[b]
    t = sp.nsimplify(t)
    return tuple(pa[i] + t * (pb[i] - pa[i]) for i in range(3))


def label_svg(name, x, y):
    """A1 -> A с индексом 1."""
    base, sub = name[0], name[1:]
    s = '<text x="%.1f" y="%.1f" font-family="Liberation Serif" font-style="italic" font-size="15" ' \
        'text-anchor="middle" dominant-baseline="middle">%s' % (x, y, base)
    if sub:
        s += '<tspan font-size="10" dy="4">%s</tspan>' % sub
    return s + '</text>'


def svg(solid, points=None, width=210, labels=True, extra=()):
    """points: {имя: (x,y,z)} — отмеченные точки. extra: [(p, q, 'dash'|'solid')]."""
    points = points or {}
    P = {k: proj(p) for k, p in solid.v.items()}
    Q = {k: proj(p) for k, p in points.items()}
    xs = [p[0] for p in list(P.values()) + list(Q.values())]
    ys = [p[1] for p in list(P.values()) + list(Q.values())]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    pad = 22
    scale = (width - 2 * pad) / (maxx - minx)
    height = (maxy - miny) * scale + 2 * pad

    def T(p):
        return (pad + (p[0] - minx) * scale, height - pad - (p[1] - miny) * scale)

    cx = sum(T(p)[0] for p in P.values()) / len(P)
    cy = sum(T(p)[1] for p in P.values()) / len(P)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
           % (width, height, width, height)]
    hid = solid.hidden_edges()
    for e in solid.edges:
        (x1, y1), (x2, y2) = T(P[e[0]]), T(P[e[1]])
        dash = ' stroke-dasharray="5,4"' if e in hid else ''
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#000" stroke-width="1.3"%s/>'
                   % (x1, y1, x2, y2, dash))
    for p, q, style in extra:
        (x1, y1), (x2, y2) = T(proj(p)), T(proj(q))
        dash = ' stroke-dasharray="5,4"' if style == 'dash' else ''
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#000" stroke-width="1"%s/>'
                   % (x1, y1, x2, y2, dash))
    if labels:
        for k, p in P.items():
            x, y = T(p)
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy) or 1
            out.append(label_svg(k, x + 13 * dx / d, y + 13 * dy / d))
    for k, p in Q.items():
        x, y = T(p)
        out.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="#000"/>' % (x, y))
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        out.append(label_svg(k, x + 12 * dx / d, y + 12 * dy / d))
    out.append('</svg>')
    return ''.join(out)


# ------------------------------------------------------------ тела

def cube(a=1):
    a = sp.nsimplify(a)
    v = {'A': (0, 0, 0), 'B': (a, 0, 0), 'C': (a, a, 0), 'D': (0, a, 0)}
    v.update({k + '1': (p[0], p[1], a) for k, p in list(v.items())})
    faces = [['A', 'B', 'C', 'D'], ['A1', 'B1', 'C1', 'D1'], ['A', 'B', 'B1', 'A1'],
             ['B', 'C', 'C1', 'B1'], ['C', 'D', 'D1', 'C1'], ['D', 'A', 'A1', 'D1']]
    return Solid(v, faces)


def box(a, b, c):
    a, b, c = map(sp.nsimplify, (a, b, c))
    v = {'A': (0, 0, 0), 'B': (a, 0, 0), 'C': (a, b, 0), 'D': (0, b, 0)}
    v.update({k + '1': (p[0], p[1], c) for k, p in list(v.items())})
    s = cube()
    return Solid(v, s.faces)


def tetra():
    v = {'A': (0, R(7, 10), 0), 'B': (R(6, 10), 0, 0), 'C': (R(14, 10), R(9, 10), 0), 'D': (R(6, 10), R(5, 10), R(12, 10))}
    return Solid(v, [['A', 'B', 'C'], ['A', 'B', 'D'], ['B', 'C', 'D'], ['C', 'A', 'D']])


def regular_tetra(a):
    a = sp.nsimplify(a)
    v = {'A': (0, 0, 0), 'B': (a, 0, 0), 'C': (a / 2, a * sp.sqrt(3) / 2, 0),
         'D': (a / 2, a * sp.sqrt(3) / 6, a * sp.sqrt(R(2, 3)))}
    return Solid(v, [['A', 'B', 'C'], ['A', 'B', 'D'], ['B', 'C', 'D'], ['C', 'A', 'D']])


def pyramid4():
    v = {'A': (0, 0, 0), 'B': (1, 0, 0), 'C': (1, 1, 0), 'D': (0, 1, 0), 'S': (R(1, 2), R(1, 2), R(13, 10))}
    return Solid(v, [['A', 'B', 'C', 'D'], ['A', 'B', 'S'], ['B', 'C', 'S'], ['C', 'D', 'S'], ['D', 'A', 'S']])


def prism3():
    base = {'A': (0, R(9, 10), 0), 'B': (R(7, 10), 0, 0), 'C': (R(16, 10), R(9, 10), 0)}
    v = dict(base)
    v.update({k + '1': (p[0], p[1], R(11, 10)) for k, p in base.items()})
    return Solid(v, [['A', 'B', 'C'], ['A1', 'B1', 'C1'], ['A', 'B', 'B1', 'A1'], ['B', 'C', 'C1', 'B1'],
                     ['C', 'A', 'A1', 'C1']])


# ------------------------------------------------------------ сечения

def plane(p, q, r):
    u = [q[i] - p[i] for i in range(3)]
    w = [r[i] - p[i] for i in range(3)]
    n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    d = -sum(n[i] * p[i] for i in range(3))
    return n, d


def section(solid, p, q, r):
    """Многоугольник сечения: список (точка, описание)."""
    n, d = plane(p, q, r)
    f = lambda P: sp.simplify(sum(n[i] * P[i] for i in range(3)) + d)
    pts = []
    for a, b in solid.edges:
        A, B = solid.v[a], solid.v[b]
        fa, fb = f(A), f(B)
        if fa == 0:
            pts.append((A, a))
        if fb == 0:
            pts.append((B, b))
        if fa * fb < 0:
            t = fa / (fa - fb)
            P = tuple(sp.simplify(A[i] + t * (B[i] - A[i])) for i in range(3))
            pts.append((P, (a, b, t)))
    uniq = []
    for P, desc in pts:
        if not any(all(sp.simplify(P[i] - U[i]) == 0 for i in range(3)) for U, _ in uniq):
            uniq.append((P, desc))
    # упорядочить по углу в плоскости сечения
    c = [sum(float(P[i]) for P, _ in uniq) / len(uniq) for i in range(3)]
    nf = [float(t) for t in n]
    e1 = [float(uniq[0][0][i]) - c[i] for i in range(3)]
    e2 = [nf[1] * e1[2] - nf[2] * e1[1], nf[2] * e1[0] - nf[0] * e1[2], nf[0] * e1[1] - nf[1] * e1[0]]

    def ang(P):
        v = [float(P[i]) - c[i] for i in range(3)]
        return math.atan2(sum(v[i] * e2[i] for i in range(3)), sum(v[i] * e1[i] for i in range(3)))
    uniq.sort(key=lambda u: ang(u[0]))
    return uniq


def dist(P, Q):
    return sp.sqrt(sp.simplify(sum((P[i] - Q[i]) ** 2 for i in range(3))))


def perimeter(poly):
    return sp.nsimplify(sp.simplify(sum(dist(poly[i][0], poly[(i + 1) % len(poly)][0]) for i in range(len(poly)))))


def area(poly):
    o = poly[0][0]
    s = [0, 0, 0]
    for i in range(1, len(poly) - 1):
        u = [poly[i][0][k] - o[k] for k in range(3)]
        w = [poly[i + 1][0][k] - o[k] for k in range(3)]
        cr = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        s = [s[k] + cr[k] for k in range(3)]
    return sp.nsimplify(sp.simplify(sp.sqrt(sum(t ** 2 for t in s)) / 2))


SUB = str.maketrans('1', '₁')
NAMES = {3: 'треугольник', 4: 'четырёхугольник', 5: 'пятиугольник', 6: 'шестиугольник'}


def describe(poly, known=None):
    """Текст для листа ответов: вид сечения и где лежат вершины.
    known: {имя: точка} — отмеченные в условии точки подписываются своими именами,
    новые получают буквы P, Q, R, T, E, F."""
    known = known or {}
    free = iter('PQRTEF')
    parts = []
    for P, desc in poly:
        name = next((k for k, q in known.items() if all(sp.simplify(P[i] - q[i]) == 0 for i in range(3))), None)
        if isinstance(desc, str):
            parts.append(desc.translate(SUB))
        elif name:
            parts.append(name)
        else:
            a, b, t = desc
            t = sp.nsimplify(t)
            ratio = sp.nsimplify(t / (1 - t))
            X = next(free)
            A, B = a.translate(SUB), b.translate(SUB)
            parts.append('%s на %s%s (%s)' % (X, A, B, 'середина' if t == R(1, 2) else
                                               '%s%s : %s%s = %s : %s' % (A, X, X, B, ratio.p, ratio.q)))
    return '%s %s' % (NAMES[len(poly)], ', '.join(parts))
