"""Стереометрия, 10 класс, вариант I: теория и решения трёх задач с доски.

    python3 build.py          проверить ответы, собрать print.html и PDF
    python3 build.py --check  только проверка

Проверка идёт точной арифметикой (Fraction) на явных координатах:
задача 1 — какие точки в каких плоскостях и по каким прямым плоскости пересекаются,
задача 2 — что AC действительно пересекает α и где, задача 3 — ответ AC = 15
и то, что запись с доски «ΔC₁DA₁ ∼ ΔC₁BA₁» в общем случае неверна.
Чертежи к задачам 2 и 3 строятся по тем же координатам; тетраэдр задачи 1 нарисован плоско, как на доске.
"""
import math
import pathlib
import re
import subprocess
import sys
from fractions import Fraction as F
from itertools import combinations

HERE = pathlib.Path(__file__).resolve().parent
PDF_NAME = "Стереометрия, вариант I — теория и решения.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FONT_CSS = ("https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,600;1,400"
            "&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap")


# ───────────────────────── точная арифметика в пространстве ─────────────────────────

def vsub(p, q): return tuple(a - b for a, b in zip(p, q))
def vadd(p, q, k=1): return tuple(a + k * b for a, b in zip(p, q))
def cross(u, v): return (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
def dot(u, v): return sum(a * b for a, b in zip(u, v))
def on_line(t, p, q): return vadd(p, vsub(q, p), F(t))


def coplanar(a, b, c, d):
    return dot(cross(vsub(b, a), vsub(c, a)), vsub(d, a)) == 0


def collinear(a, b, c):
    return cross(vsub(b, a), vsub(c, a)) == (0, 0, 0)


def check_1():
    """Тетраэдр DABC общего положения; E ∈ AB, P ∈ DE, M ∈ DB, K ∈ DC."""
    T = {"A": (F(0), F(0), F(0)), "B": (F(5), F(-3), F(0)), "C": (F(9), F(2), F(0)), "D": (F(4), F(1), F(6))}
    T["E"] = on_line(F(2, 5), T["A"], T["B"])
    T["P"] = on_line(F(3, 5), T["D"], T["E"])
    T["M"] = on_line(F(1, 2), T["D"], T["B"])
    T["K"] = on_line(F(2, 5), T["D"], T["C"])

    def in_plane(x, pl):
        return coplanar(*(T[c] for c in pl), T[x])

    def points_of(pl):
        return "".join(sorted(x for x in T if in_plane(x, pl)))

    def lines_in(pl):
        """Прямые через две подписанные точки, лежащие в плоскости (обе точки в ней)."""
        return {a + b for a, b in combinations(sorted(T), 2) if in_plane(a, pl) and in_plane(b, pl)}

    def meet(p1, p2):
        """Общие подписанные точки двух плоскостей — все они на линии пересечения."""
        return "".join(sorted(x for x in T if in_plane(x, p1) and in_plane(x, p2)))

    assert not coplanar(T["A"], T["B"], T["C"], T["D"])
    # а) в каких плоскостях лежат прямые
    faces = ["ABC", "ADB", "DBC", "CDA"]
    res_a = {ln: [f for f in faces if ln in lines_in(f) or ln[::-1] in lines_in(f)] for ln in ["EP", "KM", "BD", "AB"]}
    assert res_a == {"EP": ["ADB"], "KM": ["DBC"], "BD": ["ADB", "DBC"], "AB": ["ABC", "ADB"]}, res_a
    assert coplanar(T["D"], T["E"], T["C"], T["P"])          # PE лежит ещё и в (DEC)
    # б) точки плоскостей
    assert points_of("ADB") == "ABDEMP" and points_of("DBC") == "BCDKM"
    assert meet("ADB", "DBC") == "BDM" and collinear(T["B"], T["D"], T["M"])
    # в) линии пересечения: общие точки (их ≥ 2, все на одной прямой)
    assert meet("ABC", "DCB") == "BC"
    assert meet("ABD", "CDA") == "AD"
    assert all(in_plane(x, "PDB") == in_plane(x, "ADB") for x in T)   # (PDB) = (ADB)
    assert meet("PDB", "ABC") == "ABE" and collinear(T["A"], T["B"], T["E"])
    return "задача 1: а) PE⊂(ADB), MK⊂(DBC), DB⊂(ADB),(DBC), AB⊂(ABC),(ADB); " \
           "б) (ADB): A,B,D,E,M,P; (DBC): B,C,D,K,M; в) BC, AD, AB"


P2 = {"A": (F(-3, 2), F(3, 10), F(-1)), "B": (F(4, 5), F(6, 5), F(4)), "C": (F(18, 5), F(9, 5), F(-4))}


def plane_hit(p, q):
    """Параметр t точки p + t(q − p) на плоскости α: z = 0 (None — параллельна)."""
    dz = q[2] - p[2]
    return None if dz == 0 else -p[2] / dz


def check_2():
    A, B, C = P2["A"], P2["B"], P2["C"]
    M, N = on_line(F(1, 2), A, B), on_line(F(1, 2), B, C)
    assert N[2] == 0 and M[2] != 0                       # MN ∩ α = N, MN ⊄ α
    assert cross(vsub(N, M), vsub(C, A)) == (0, 0, 0)    # MN ∥ AC
    t = plane_hit(A, C)
    assert t is not None                                  # AC пересекает α
    X = on_line(t, A, C)
    assert not (0 <= t <= 1)                              # но не отрезок: X на продолжении за A
    K = on_line(plane_hit(A, B), A, B)
    assert collinear(K, N, X)                             # α ∩ (ABC) = KN, X на ней
    P2.update(M=M, N=N, K=K, X=X)
    return f"задача 2: AC ∩ α = X, t = {t} (продолжение за A)"


P3 = {"A": (F(0), F(0), F(0)), "B": (F(7), F(6), F(0)), "C": (F(15), F(0), F(0)), "D": (F(8), F(-6), F(0))}


def check_3():
    # параллелограмм с BC = 10, AC = 15; A₁ ∈ AD, DA₁ = 4; α ∥ AC через A₁ — вертикальная плоскость через A₁C₁
    A, B, C, D = P3["A"], P3["B"], P3["C"], P3["D"]
    assert vadd(A, vsub(C, B)) == D                        # ABCD — параллелограмм
    dist2 = lambda p, q: dot(vsub(p, q), vsub(p, q))
    assert dist2(B, C) == 100 and dist2(A, C) == 225
    A1 = on_line(F(6, 10), A, D)
    assert dist2(D, A1) == 16
    # плоскость α: через A₁, содержит направление AC и вертикаль; ищем C₁ = α ∩ CD
    n = cross(vsub(C, A), (0, 0, 1))                       # нормаль α
    assert dot(n, vsub(C, A)) == 0                          # AC ∥ α (AC не в α: A ∉ α)
    assert dot(n, vsub(A, A1)) != 0
    s = dot(n, vsub(A1, C)) / dot(n, vsub(D, C))
    C1 = on_line(s, C, D)
    assert cross(vsub(C1, A1), vsub(C, A)) == (0, 0, 0)    # A₁C₁ ∥ AC
    assert dist2(A1, C1) == 36                              # A₁C₁ = 6
    P3.update(A1=A1, C1=C1)
    k = F(4, 10)
    assert k * k * dist2(A, C) == dist2(A1, C1)             # AC = A₁C₁ / k = 15
    # общий случай: AC = A₁C₁ · BC / DA₁ для «косого» параллелограмма
    A_, B_, D_ = (F(0), F(0), F(0)), (F(3), F(7), F(0)), (F(11), F(-2), F(0))
    C_ = vadd(B_, vsub(D_, A_))
    for r in (F(1, 3), F(2, 5), F(5, 7)):
        A1_ = on_line(1 - r, A_, D_)                        # DA₁ = r · DA
        C1_ = on_line(1 - r, C_, D_)                        # прямая через A₁ ∥ AC
        assert cross(vsub(C1_, A1_), vsub(C_, A_)) == (0, 0, 0)
        assert dist2(A1_, C1_) == r * r * dist2(A_, C_)
    # «ΔC₁DA₁ ∼ ΔC₁BA₁» в квадрате со стороной 10: у первого прямой угол, у второго нет
    Aq, Bq, Cq, Dq = (0, 0), (0, 10), (10, 10), (10, 0)
    A1q, C1q = (6, 0), (10, 4)
    d2 = lambda p, q: (p[0]-q[0])**2 + (p[1]-q[1])**2
    tri1 = sorted([d2(C1q, Dq), d2(Dq, A1q), d2(A1q, C1q)])
    tri2 = sorted([d2(C1q, Bq), d2(Bq, A1q), d2(A1q, C1q)])
    assert tri1[0] + tri1[1] == tri1[2] and tri2[0] + tri2[1] != tri2[2]
    ratios = {F(x, y) for x, y in zip(tri2, tri1)}
    assert len(ratios) > 1                                  # стороны не пропорциональны
    return "задача 3: A₁C₁ ∥ AC, k = 2/5, AC = 15; ΔC₁BA₁ не подобен ΔC₁DA₁ (квадрат)"


def check():
    out = [check_1(), check_2(), check_3()]
    for s in out:
        print("✓", s)


# ───────────────────────────────── чертежи ─────────────────────────────────

class Fig:
    """SVG по точным координатам. 3D-точки проецируются косоугольно (фронтальная диметрия)."""

    def __init__(self, s=40.0, kx=0.5, ky=0.35):
        self.s, self.kx, self.ky = s, kx, ky
        self.items, self.box = [], []

    def p(self, q):
        q = [float(c) for c in q]
        if len(q) == 2:
            return (q[0], q[1])
        x, y, z = q
        return (self.s * (x + self.kx * y), -self.s * (z + self.ky * y))

    def _keep(self, *pts):
        self.box.extend(pts)

    def poly(self, pts, cls):
        P = [self.p(q) for q in pts]
        self._keep(*P)
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in P)
        self.items.append(f'<polygon class="{cls}" points="{d}"/>')

    def seg(self, a, b, cls="e"):
        (x1, y1), (x2, y2) = self.p(a), self.p(b)
        self._keep((x1, y1), (x2, y2))
        self.items.append(f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')

    def seg_vis(self, a, b, hidden, cls="e", hcls="h", n=240):
        """Отрезок, разбитый на видимые и невидимые куски по предикату hidden(3D-точка)."""
        pts = [vadd(a, vsub(b, a), F(i, n)) for i in range(n + 1)]
        runs, cur, start = [], None, 0
        for i, q in enumerate(pts):
            h = hidden(q)
            if cur is None:
                cur = h
            elif h != cur:
                runs.append((start, i, cur)); start, cur = i, h
        runs.append((start, n, cur))
        for i, j, h in runs:
            self.seg(pts[i], pts[j], hcls if h else cls)

    def dot(self, q, r=2.6):
        x, y = self.p(q)
        self._keep((x, y))
        self.items.append(f'<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>')

    def name(self, q, text, dx=0, dy=0, cls="lb"):
        x, y = self.p(q)
        x, y = x + dx, y + dy
        self._keep((x - 8, y - 14), (x + 14, y + 6))
        t = re.sub(r"(\w)1", r'\1<tspan class="sub" dy="4">1</tspan>', text)
        self.items.append(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">{t}</text>')

    def svg(self, width, pad=10, label=""):
        xs = [x for x, _ in self.box]; ys = [y for _, y in self.box]
        x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
        w, h = x1 - x0, y1 - y0
        return (f'<svg class="fig-svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" width="{width}" '
                f'height="{width * h / w:.0f}" role="img" aria-label="{label}">' + "".join(self.items) + "</svg>")


def inside(pt, poly):
    x, y = pt
    res = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            res = not res
    return res


# тетраэдр задачи 1 — плоский рисунок, как на доске
T2 = {"D": (170, 18), "A": (28, 214), "B": (150, 290), "C": (306, 206)}


def lerp2(t, p, q): return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))


T2["E"] = lerp2(0.4, T2["A"], T2["B"])
T2["P"] = lerp2(0.55, T2["D"], T2["E"])
T2["M"] = lerp2(0.52, T2["D"], T2["B"])
T2["K"] = lerp2(0.42, T2["D"], T2["C"])
NAME1 = {"D": (6, -6), "A": (-12, 6), "B": (2, 20), "C": (13, 6), "E": (-9, 18),
         "P": (-12, 2), "M": (13, 10), "K": (12, -4)}


def fig_tetra(mode="base", width=330):
    f, T = Fig(), T2
    if mode == "planes":       # (ADB) и (DBC) — по ребру DB
        f.poly([T["A"], T["D"], T["B"]], "fa"); f.poly([T["D"], T["B"], T["C"]], "fb")
    if mode == "pdb":          # (PDB) = (ADB) и основание (ABC) — по AB
        f.poly([T["A"], T["B"], T["C"]], "fb"); f.poly([T["A"], T["D"], T["B"]], "fa")
    for a, b in ["DA", "DC", "AB", "BC"]:
        f.seg(T[a], T[b], "e")
    f.seg(T["D"], T["B"], "hl" if mode == "planes" else "e")
    f.seg(T["A"], T["C"], "h")
    if mode == "base":
        f.seg(T["E"], T["C"], "h")
    if mode == "pdb":
        f.seg(T["A"], T["B"], "hl")
        f.seg(T["P"], T["B"], "aux")
    f.seg(T["D"], T["E"], "e" if mode != "pdb" else "aux")
    if mode != "pdb":
        f.seg(T["M"], T["K"], "e")
    shown = {"base": "DABCEPMK", "planes": "DABCEPMK", "pdb": "DABCEP"}[mode]
    for x in shown:
        if x in "EPMK":
            f.dot(T[x])
        f.name(T[x], x, *NAME1[x])
    return f.svg(width, label="тетраэдр DABC")


def fig_2(width=420):
    A, B, C = P2["A"], P2["B"], P2["C"]
    M, N, K, X = P2["M"], P2["N"], P2["K"], P2["X"]
    f = Fig(s=46)
    plane = [(F(-23, 5), F(-8, 5), 0), (F(26, 5), F(-8, 5), 0), (F(26, 5), F(21, 5), 0), (F(-23, 5), F(21, 5), 0)]
    f.poly(plane, "pl")
    poly2 = [f.p(q) for q in plane]
    hid = lambda q: q[2] < 0 and inside(f.p(q), poly2)
    # линия пересечения α и (ABC): через X, K, N и чуть дальше
    f.seg(vadd(X, vsub(N, X), F(-1, 8)), vadd(X, vsub(N, X), F(9, 8)), "lnr")
    f.seg_vis(A, X, hid, "ext", "exth")
    f.seg_vis(A, B, hid); f.seg_vis(B, C, hid); f.seg_vis(A, C, hid)
    f.seg(M, N, "mid")
    for q in (M, N, K, X):
        f.dot(q)
    for q, t, dx, dy in [(A, "A", -12, 8), (B, "B", 0, -9), (C, "C", 12, 10), (M, "M", -13, -2),
                         (N, "N", 13, -5), (K, "K", -12, -6), (X, "X", -6, -9)]:
        f.name(q, t, dx, dy)
    f.name(plane[0], "α", 22, -10, "lb al")
    return f.svg(width, label="плоскость α и треугольник ABC")


def fig_3(width=430):
    A, B, C, D, A1, C1 = (P3[k] for k in ("A", "B", "C", "D", "A1", "C1"))
    d = vsub(C1, A1)
    Q1, Q2 = vadd(A1, d, F(-2, 5)), vadd(C1, d, F(2, 5))
    up = (0, 0, F(18, 5))
    f = Fig(s=22, kx=0.4, ky=0.45)
    wall = [Q1, Q2, vadd(Q2, up), vadd(Q1, up)]
    f.poly([C, D, A], "fb")
    f.poly([C1, D, A1], "fa")
    f.poly(wall, "pl")
    w2 = [f.p(q) for q in wall]
    behind = lambda q: q[1] > A1[1] and inside(f.p(q), w2)   # за стеной α (смотрим спереди)
    for a, b in [(A, B), (B, C), (C, D), (D, A)]:
        f.seg_vis(a, b, behind, "e", "eb")
    f.seg_vis(A, C, behind, "mid", "midb")
    f.seg(Q1, Q2, "lnr"); f.seg(A1, C1, "hl")
    f.dot(A1); f.dot(C1)
    for q, t, dx, dy in [(A, "A", -12, 5), (B, "B", 0, -8), (C, "C", 12, 5), (D, "D", 0, 18),
                         (A1, "A1", -12, 16), (C1, "C1", 13, 16)]:
        f.name(q, t, dx, dy)
    f.name(vadd(Q1, up), "α", 12, 20, "lb al")
    f.name(vadd(A1, vsub(D, A1), F(1, 2)), "4", -10, 8, "lb num")
    f.name(vadd(A1, d, F(1, 2)), "6", 0, -6, "lb num")
    f.name(vadd(B, vsub(C, B), F(1, 2)), "10", 12, -2, "lb num")
    return f.svg(width, label="параллелограмм ABCD и плоскость α")


# ───────────────────────────────── страница ─────────────────────────────────

def m(s):
    """Формула моноширинным, A1 → A₁ (удобно писать в исходнике)."""
    return f'<span class="m">{subs(s)}</span>'


CSS = r"""
:root{
  --ground:#FFFFFF; --surface:#FFFFFF; --surface-2:#EAF0F2;
  --ink:#111D22; --ink-soft:#40565E; --muted:#6E858D;
  --rule:#D3DFE3; --rule-soft:#E3EBEE;
  --primary:#0F5A6E; --primary-soft:#DCEEF2;
  --coral:#B4423A; --coral-soft:#FAE7E4;
  --moss:#33734A; --moss-soft:#E1F0E5;
  --amber:#8F5D09; --amber-soft:#FBEED6;
  --display:"Spectral",Georgia,"DejaVu Serif",serif;
  --body:"Source Sans 3","Liberation Sans","DejaVu Sans",sans-serif;
  --mono:"JetBrains Mono","DejaVu Sans Mono",monospace;
}
@page{size:A4;margin:14mm 13mm 14mm}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:var(--ground);color:var(--ink);font-family:var(--body);font-size:13.6px;line-height:1.5;margin:0}
.wrap{max-width:760px;margin:0 auto}
p{margin:0 0 .6em}
strong{font-weight:600}
.m{font-family:var(--mono);font-size:.9em;white-space:nowrap}
sub{font-size:.72em;vertical-align:-.28em;line-height:0}

.masthead{border-bottom:2px solid var(--ink);padding:4px 0 12px;margin-bottom:16px}
.eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary);margin:0 0 8px}
h1{font-family:var(--display);font-weight:600;font-size:30px;line-height:1.1;letter-spacing:-.01em;margin:0 0 8px}
.standfirst{font-family:var(--display);font-style:italic;font-size:15.5px;color:var(--ink-soft);margin:0 0 10px}
.facts{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:0;padding:0}
.facts li{font-family:var(--mono);font-size:10.5px;border:1px solid var(--rule);color:var(--ink-soft);border-radius:2px;padding:2px 7px}

.legend{display:grid;grid-template-columns:repeat(2,1fr);gap:2px 22px;font-size:12.6px;border:1px solid var(--rule);border-radius:2px;padding:8px 12px;margin:0 0 18px;background:var(--surface-2);break-inside:avoid}
.legend b{font-family:var(--mono);font-weight:600;color:var(--primary);display:inline-block;min-width:74px}

section.task{margin:0 0 22px}
.head{display:flex;align-items:baseline;gap:12px;border-top:2px solid var(--ink);padding-top:8px;margin-bottom:10px;break-after:avoid}
.badge{font-family:var(--mono);font-size:11px;color:#fff;background:var(--primary);border-radius:2px;padding:2px 7px}
h2{font-family:var(--display);font-weight:600;font-size:23px;line-height:1.15;margin:0}
h3{font-family:var(--display);font-weight:600;font-size:17px;margin:14px 0 6px;break-after:avoid}
h4{font-size:13px;font-weight:600;letter-spacing:.02em;color:var(--ink-soft);margin:10px 0 4px;break-after:avoid}
ul,ol{padding-left:1.3em;margin:0 0 .6em}
li{margin-bottom:.22em}

.cond{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;border:1px solid var(--rule);border-left:3px solid var(--ink);border-radius:2px;padding:10px 12px;margin-bottom:6px;break-inside:avoid}
.cond.solo{grid-template-columns:1fr}
.cond p:last-child,.cond ul:last-child{margin-bottom:0}
.board{font-size:11.5px;color:var(--muted);margin:0 0 10px}

.theory{display:grid;gap:7px}
.card{border:1px solid var(--rule);border-left:3px solid var(--primary);background:var(--primary-soft);border-radius:2px;padding:7px 11px;break-inside:avoid}
.card p:last-child,.card ol:last-child,.card ul:last-child{margin-bottom:0}
.card .t{font-weight:600;color:var(--primary)}
.proof{font-size:12.8px;color:var(--ink-soft);border-top:1px dashed var(--rule);margin-top:5px;padding-top:5px}

.steps{counter-reset:st;list-style:none;padding:0}
.steps>li{position:relative;padding-left:26px;margin-bottom:6px;break-inside:avoid}
.steps>li::before{counter-increment:st;content:counter(st);position:absolute;left:0;top:1px;font-family:var(--mono);font-size:10.5px;color:#fff;background:var(--ink);border-radius:2px;width:18px;text-align:center}

table{border-collapse:collapse;width:100%;font-size:13px;margin:0 0 10px}
th,td{border-bottom:1px solid var(--rule);padding:4px 8px;text-align:left;vertical-align:top}
th{font-size:11.5px;font-weight:600;color:var(--ink-soft);border-bottom:1.5px solid var(--ink)}
tr{break-inside:avoid}
td:first-child,td:nth-child(2){font-family:var(--mono);white-space:nowrap}

.answer{border:1px solid var(--moss);background:var(--moss-soft);border-radius:2px;padding:8px 12px;margin:10px 0;break-inside:avoid}
.answer .t{font-weight:600;color:var(--moss)}
.answer p:last-child{margin-bottom:0}
.warn{border:1px solid var(--rule);border-left:3px solid var(--amber);background:var(--amber-soft);border-radius:2px;padding:7px 12px;margin:10px 0;break-inside:avoid;font-size:12.8px}
.warn .t{font-weight:600;color:var(--amber)}
.warn ul{margin:0}
.note{border:1px solid var(--rule);border-left:3px solid var(--coral);background:var(--coral-soft);border-radius:2px;padding:7px 12px;margin:0 0 10px;break-inside:avoid;font-size:12.8px}
.note .t{font-weight:600;color:var(--coral)}

figure{margin:0;break-inside:avoid}
figure.wide{display:flex;justify-content:center;gap:26px;margin:6px 0 10px}
figure.wide>div{text-align:center}
figcaption{font-size:11.5px;color:var(--muted);text-align:center;margin-top:2px}
.fig-svg{display:block;margin:0 auto;overflow:visible}

/* чертежи */
.fig-svg line{stroke-linecap:round}
.e{stroke:var(--ink);stroke-width:1.6}
.h{stroke:var(--ink);stroke-width:1.2;stroke-dasharray:5 4}
.hl{stroke:var(--coral);stroke-width:3}
.mid{stroke:var(--primary);stroke-width:2.6}
.aux{stroke:var(--primary);stroke-width:1.6;stroke-dasharray:6 3}
.ext{stroke:var(--coral);stroke-width:1.6;stroke-dasharray:6 4}
.exth{stroke:var(--coral);stroke-width:1.3;stroke-dasharray:3 4}
.lnr{stroke:var(--coral);stroke-width:1.1}
.pl{fill:var(--primary-soft);fill-opacity:.75;stroke:var(--primary);stroke-width:1.2}
.eb{stroke:var(--ink);stroke-opacity:.4;stroke-width:1.2;stroke-dasharray:5 4}
.midb{stroke:var(--primary);stroke-opacity:.55;stroke-width:2;stroke-dasharray:6 4}
.base{fill:none}
.fa{fill:var(--primary-soft);fill-opacity:.9;stroke:none}
.fb{fill:var(--amber-soft);fill-opacity:.9;stroke:none}
.pt{fill:var(--ink)}
.lb{font-family:var(--body);font-size:15px;font-style:italic;fill:var(--ink)}
.lb .sub{font-size:10px;font-style:normal}
.al{fill:var(--primary);font-size:17px}
.num{font-family:var(--mono);font-style:normal;font-size:12px;fill:var(--coral)}
"""


def html(fonts_css=""):
    t1, t1a, t1b = fig_tetra("base", 250), fig_tetra("planes", 230), fig_tetra("pdb", 230)
    f2, f3 = fig_2(400), fig_3(410)
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Стереометрия, вариант I</title>
<style>{fonts_css}{CSS}</style></head>
<body><div class="wrap">

<header class="masthead">
  <p class="eyebrow">Геометрия · 10 класс · Вариант I</p>
  <h1>Аксиомы стереометрии и параллельность: теория и решения</h1>
  <p class="standfirst">Три задачи с доски. К каждой — нужная теория, рисунок и решение, в котором обоснован каждый шаг.</p>
  <ul class="facts"><li>3 задачи</li><li>аксиомы и следствия</li><li>параллельные прямые</li><li>прямая, параллельная плоскости</li></ul>
</header>

<div class="legend">
  <div><b>(ABC)</b> плоскость через точки A, B, C</div>
  <div><b>α, β</b> плоскости</div>
  <div><b>A ∈ a</b> точка A лежит на прямой a</div>
  <div><b>a ⊂ α</b> прямая a лежит в плоскости α</div>
  <div><b>α ∩ β = a</b> плоскости пересекаются по прямой a</div>
  <div><b>a ∥ b, a ∥ α</b> параллельны</div>
</div>

<section class="task">
  <div class="head"><span class="badge">№ 1</span><h2>Плоскости, точки и линии пересечения</h2></div>
  <div class="cond">
    <div>
      <p><strong>По рисунку назовите:</strong></p>
      <ul>
        <li>плоскости, в которых лежат прямые {m("PE")}, {m("MK")}, {m("DB")}, {m("AB")};</li>
        <li>точки, лежащие в плоскостях {m("(ADB)")} и {m("(DBC)")};</li>
        <li>прямые, по которым пересекаются плоскости {m("(ABC)")} и {m("(DCB)")}; {m("(ABD)")} и {m("(CDA)")}; {m("(PDB)")} и {m("(ABC)")}.</li>
      </ul>
      <p>На рисунке: {m("E ∈ AB")}, {m("P ∈ DE")}, {m("M ∈ DB")}, {m("K ∈ DC")}.</p>
    </div>
    <figure>{t1}<figcaption>Рис. 1. Тетраэдр DABC</figcaption></figure>
  </div>

  <h3>Теория</h3>
  <div class="theory">
    <div class="card">
      <p><span class="t">Аксиома 1.</span> Через любые три точки, не лежащие на одной прямой, проходит плоскость, и притом только одна. Поэтому плоскость называют тремя её точками: {m("(ABC)")}.</p>
      <p><span class="t">Аксиома 2.</span> Если две точки прямой лежат в плоскости, то все точки прямой лежат в этой плоскости.</p>
      <p><span class="t">Аксиома 3.</span> Если две различные плоскости имеют общую точку, то они имеют общую прямую, на которой лежат все общие точки этих плоскостей. Иначе говоря, плоскости пересекаются по прямой.</p>
    </div>
    <div class="card">
      <p><span class="t">Три приёма для таких задач</span></p>
      <ol>
        <li><em>Лежит ли прямая в плоскости?</em> Найдите на прямой две точки этой плоскости — по аксиоме 2 в ней лежит вся прямая.</li>
        <li><em>По какой прямой пересекаются плоскости?</em> Найдите две общие точки — по аксиомам 3 и 2 это прямая через них.</li>
        <li><em>Одна плоскость — разные имена.</em> Если три точки, не лежащие на одной прямой, лежат в плоскости, то они задают именно её (аксиома 1, «только одна»). Например, {m("(PDB) = (ADB)")}, потому что {m("P ∈ (ADB)")}.</li>
      </ol>
    </div>
  </div>

  <h3>Решение</h3>
  <h4>а) В каких плоскостях лежат прямые</h4>
  <table>
    <tr><th>Прямая</th><th>Плоскость</th><th>Почему</th></tr>
    <tr><td>PE</td><td>(ADB)</td><td>{m("D ∈ (ADB)")}, {m("E ∈ AB ⊂ (ADB)")} ⇒ {m("DE ⊂ (ADB)")} (аксиома 2). Точка P лежит на DE, поэтому прямая PE — это прямая DE.</td></tr>
    <tr><td>MK</td><td>(DBC)</td><td>{m("M ∈ DB")}, {m("K ∈ DC")}, обе прямые лежат в {m("(DBC)")} ⇒ M и K в ней ⇒ {m("MK ⊂ (DBC)")}.</td></tr>
    <tr><td>DB</td><td>(ADB), (DBC)</td><td>Общее ребро двух боковых граней.</td></tr>
    <tr><td>AB</td><td>(ABC), (ADB)</td><td>Общее ребро основания и боковой грани.</td></tr>
  </table>
  <p>Через любую прямую проходит бесконечно много плоскостей; называют те, что заданы точками рисунка. Например, PE лежит ещё и в {m("(DEC)")}.</p>

  <h4>б) Точки в плоскостях (ADB) и (DBC)</h4>
  <p><strong>{m("(ADB)")}:</strong> A, D, B, а также E (на AB), P (на DE), M (на DB).<br>
     <strong>{m("(DBC)")}:</strong> D, B, C, а также M (на DB), K (на DC).<br>
     <strong>В обеих сразу:</strong> D, B, M — они лежат на прямой DB, по которой эти плоскости пересекаются.</p>
  <p>Почему остальные точки не годятся: если бы {m("K ∈ (ADB)")}, то D и K лежали бы в {m("(ADB)")}, а с ними вся прямая DC и точка C — тетраэдр стал бы плоским. E не лежит в {m("(DBC)")}: иначе там были бы B и E, а с ними прямая AB и точка A. P тоже нет: иначе в {m("(DBC)")} попала бы прямая DP, то есть DE, и точка E.</p>

  <figure class="wide">
    <div>{t1a}<figcaption>Рис. 2. {m("(ADB) ∩ (DBC) = DB")}</figcaption></div>
    <div>{t1b}<figcaption>Рис. 3. {m("(PDB) = (ADB)")}, {m("(ADB) ∩ (ABC) = AB")}</figcaption></div>
  </figure>

  <h4>в) Прямые, по которым пересекаются плоскости</h4>
  <ol class="steps">
    <li>{m("(ABC)")} и {m("(DCB)")}: общие точки B и C ⇒ плоскости пересекаются по прямой <strong>BC</strong>.</li>
    <li>{m("(ABD)")} и {m("(CDA)")}: общие точки A и D ⇒ по прямой <strong>AD</strong>.</li>
    <li>{m("(PDB)")} и {m("(ABC)")}: точка P лежит на DE, а {m("DE ⊂ (ADB)")}. Значит, P, D, B лежат в {m("(ADB)")} и не лежат на одной прямой, поэтому {m("(PDB) = (ADB)")} (аксиома 1). Общие точки {m("(ADB)")} и {m("(ABC)")} — A и B ⇒ прямая <strong>AB</strong>.</li>
  </ol>

  <div class="answer"><p class="t">Ответ</p>
    <p>а) {m("PE ⊂ (ADB)")}; {m("MK ⊂ (DBC)")}; {m("DB ⊂ (ADB), (DBC)")}; {m("AB ⊂ (ABC), (ADB)")}.<br>
    б) {m("(ADB)")}: A, B, D, E, P, M; {m("(DBC)")}: B, C, D, M, K; в обеих — B, D, M.<br>
    в) {m("(ABC) ∩ (DCB) = BC")}; {m("(ABD) ∩ (CDA) = AD")}; {m("(PDB) ∩ (ABC) = AB")}.</p>
  </div>
  <div class="warn"><p class="t">Типичные ошибки</p><ul>
    <li>Для DB и AB названа одна плоскость, а их две: каждая прямая — ребро двух граней.</li>
    <li>«Плоскости пересекаются в точке B». Две различные плоскости с общей точкой пересекаются по прямой (аксиома 3), а не в точке.</li>
    <li>{m("(PDB) ∩ (ABC) = PB")} или {m("= DB")}. Ни P, ни D не лежат в основании {m("(ABC)")}, такая прямая не может быть общей.</li>
  </ul></div>
</section>

<section class="task">
  <div class="head"><span class="badge">№ 2</span><h2>Средняя линия и плоскость</h2></div>
  <div class="cond">
    <div>
      <p>{m("MN")} — средняя линия треугольника {m("ABC")} ({m("M ∈ AB")}, {m("N ∈ BC")}). Прямая MN пересекает плоскость α в точке N: {m("MN ∩ α = N")}.</p>
      <p><strong>Докажите,</strong> что прямая AC пересекает плоскость α.</p>
    </div>
    <figure>{f2}<figcaption>Рис. 4. Отрезки под плоскостью — пунктиром</figcaption></figure>
  </div>

  <h3>Теория</h3>
  <div class="theory">
    <div class="card"><p><span class="t">Параллельные прямые в пространстве</span> — прямые, которые <em>лежат в одной плоскости</em> и не пересекаются. Две прямые без общих точек, не лежащие в одной плоскости, называют скрещивающимися — они не параллельны.</p></div>
    <div class="card"><p><span class="t">Средняя линия треугольника</span> параллельна третьей стороне и равна её половине: {m("MN ∥ AC")}, {m("MN = AC/2")}.</p></div>
    <div class="card"><p><span class="t">Из планиметрии.</span> Если прямая на плоскости пересекает одну из двух параллельных прямых, то она пересекает и другую.</p></div>
    <div class="card">
      <p><span class="t">Лемма.</span> Если одна из двух параллельных прямых пересекает плоскость, то и другая прямая пересекает эту плоскость.</p>
      <div class="proof">
        <p><em>Доказательство.</em> Пусть {m("a ∥ b")} и a пересекает α в точке Y.</p>
        <ol>
          <li>Параллельные a и b лежат в одной плоскости β. Она отлична от α: a лежит в β, но не в α.</li>
          <li>У α и β общая точка Y ⇒ по аксиоме 3 они пересекаются по прямой c, {m("Y ∈ c")}.</li>
          <li>В плоскости β прямая c пересекает a (в точке Y), значит, пересекает и параллельную ей b — в некоторой точке Z. Так как {m("Z ∈ c ⊂ α")}, Z — общая точка b и α.</li>
          <li>b не лежит в α: иначе b лежала бы и в α, и в β, то есть совпала бы с c. Но c пересекает a, а {m("b ∥ a")}. Значит, Z — единственная общая точка: b пересекает α. ∎</li>
        </ol>
      </div>
    </div>
  </div>

  <h3>Решение</h3>
  <ol class="steps">
    <li>MN — средняя линия треугольника ABC, поэтому {m("MN ∥ AC")}.</li>
    <li>{m("MN ∩ α = N")}: у прямой MN с плоскостью α ровно одна общая точка, то есть MN пересекает α. (Если бы MN лежала в α, общих точек было бы бесконечно много.)</li>
    <li>Прямые MN и AC параллельны, и одна из них, MN, пересекает α. По лемме и AC пересекает плоскость α. ∎</li>
  </ol>

  <div class="note"><p class="t">Пересекает прямая, а не обязательно отрезок</p>
    <p>На рис. 4 точки A и C лежат по одну сторону от α, поэтому отрезок AC плоскость не пересекает. Прямая AC пересекает α в точке X на продолжении за точку A. Найти X можно так: плоскости α и {m("(ABC)")} пересекаются по прямой KN, где {m("K = AB ∩ α")}; тогда {m("X = KN ∩ AC")}. Прямая KN не параллельна AC: единственная прямая через N, параллельная AC в плоскости {m("(ABC)")}, — это MN, а MN в α не лежит.</p>
  </div>

  <div class="answer"><p class="t">Вывод</p><p>{m("MN ∥ AC")} и MN пересекает α ⇒ прямая AC пересекает α (лемма о двух параллельных прямых).</p></div>
  <div class="warn"><p class="t">Типичные ошибки</p><ul>
    <li>«AC пересекает α в точке N». Точка N лежит на BC, а не на AC; у AC своя точка пересечения.</li>
    <li>«Отрезок AC пересекает α». Утверждается только про прямую — см. рис. 4.</li>
    <li>Ссылка на лемму без двух условий: что MN и AC параллельны (средняя линия) и что MN именно пересекает α, а не лежит в ней.</li>
  </ul></div>
</section>

<section class="task">
  <div class="head"><span class="badge">№ 3</span><h2>Плоскость, параллельная диагонали</h2></div>
  <div class="cond">
    <div>
      <p><strong>Дано:</strong> {m("ABCD")} — параллелограмм, {m("AC")} — диагональ; {m("A1 ∈ AD")}, {m("DA1 = 4")}; плоскость {m("α ∥ AC")}, {m("A1 ∈ α")}, {m("α ∩ CD = C1")}.</p>
      <p><strong>Доказать:</strong> {m("ΔC1DA1 ∼ ΔCDA")}.</p>
      <p><strong>Найти:</strong> {m("AC")}, если {m("BC = 10")}, {m("A1C1 = 6")}.</p>
    </div>
    <figure>{f3}<figcaption>Рис. 5. Плоскость α пересекает плоскость параллелограмма по прямой A<sub>1</sub>C<sub>1</sub></figcaption></figure>
  </div>
  <div class="note"><p class="t">О записи на доске</p>
    <p>На доске записано {m("ΔC1DA1 ∼ ΔC1BA1")}. Скорее всего, это описка: треугольник {m("C1BA1")} в общем случае не подобен {m("C1DA1")}. Проверка на квадрате со стороной 10: у {m("C1DA1")} прямой угол при D, а у {m("C1BA1")} прямого угла нет. Доказываем подобие с {m("ΔCDA")}. Так как {m("ΔCDA = ΔABC")}, верно и {m("ΔC1DA1 ∼ ΔABC")} с соответствием {m("C1↔A, D↔B, A1↔C")}.</p>
  </div>

  <h3>Теория</h3>
  <div class="theory">
    <div class="card"><p><span class="t">Прямая и плоскость параллельны,</span> если у них нет общих точек: {m("a ∥ α")}.</p></div>
    <div class="card">
      <p><span class="t">Утверждение.</span> Если плоскость β проходит через прямую a, параллельную плоскости α, и пересекает α по прямой b, то {m("b ∥ a")}.</p>
      <div class="proof"><p><em>Доказательство.</em> Прямые a и b лежат в одной плоскости β. Общих точек у них нет: b лежит в α, а у a с плоскостью α общих точек нет. Две прямые одной плоскости без общих точек параллельны. ∎</p></div>
    </div>
    <div class="card"><p><span class="t">Параллелограмм:</span> противоположные стороны равны ({m("AD = BC")}); диагональ AC делит его на два равных треугольника, {m("ΔABC = ΔCDA")}.</p></div>
    <div class="card"><p><span class="t">Подобие.</span> Признак: если два угла одного треугольника равны двум углам другого, треугольники подобны. Отношение сходственных сторон равно коэффициенту подобия k. Соответственные углы при параллельных прямых и секущей равны.</p></div>
  </div>

  <h3>Решение</h3>
  <ol class="steps">
    <li><strong>Линия пересечения.</strong> {m("A1 ∈ α")} и {m("A1 ∈ AD ⊂ (ABC)")}; {m("C1 ∈ α")} и {m("C1 ∈ CD ⊂ (ABC)")}. Плоскости α и {m("(ABC)")} различны: AC лежит в {m("(ABC)")}, а с α у AC нет общих точек. Две общие точки ⇒ {m("α ∩ (ABC) = A1C1")} (аксиомы 3 и 2).</li>
    <li><strong>{m("A1C1 ∥ AC")}.</strong> Плоскость {m("(ABC)")} проходит через прямую AC, параллельную α, и пересекает α по {m("A1C1")}. По утверждению {m("A1C1 ∥ AC")}.</li>
    <li><strong>Подобие.</strong> В треугольниках {m("C1DA1")} и {m("CDA")}: угол D общий; {m("∠DA1C1 = ∠DAC")} как соответственные при {m("A1C1 ∥ AC")} и секущей AD. По двум углам {m("ΔC1DA1 ∼ ΔCDA")}, соответствие {m("C1↔C, D↔D, A1↔A")}. ∎</li>
    <li><strong>Вычисление.</strong> {m("AD = BC = 10")} (противоположные стороны параллелограмма). Коэффициент подобия {m("k = DA1 / DA = 4/10 = 2/5")}. Сходственные стороны: {m("A1C1 / AC = k")}, откуда {m("AC = A1C1 / k = 6 · 10/4 = 15")}.</li>
  </ol>

  <div class="answer"><p class="t">Ответ</p><p>{m("ΔC1DA1 ∼ ΔCDA")} (по двум углам, так как {m("A1C1 ∥ AC")}); {m("AC = 15")}.</p></div>
  <div class="warn"><p class="t">Типичные ошибки</p><ul>
    <li>Не доказано, что {m("A1C1 ∥ AC")}, а это главный шаг задачи: параллельность следует из {m("AC ∥ α")} по утверждению, а не «видно по рисунку».</li>
    <li>Взято отношение {m("DA1 : A1A = 4 : 6")} вместо {m("DA1 : DA = 4 : 10")} — получается {m("AC = 9")}. Сходственные стороны берутся целиком, от вершины D.</li>
    <li>BC подставлено как сторона треугольника {m("CDA")}. В нём сторона DA, а {m("DA = BC")} — по свойству параллелограмма, это нужно сказать.</li>
  </ul></div>
</section>

</div></body></html>
"""


def subs(text):
    """A1 → A<sub>1</sub> в формулах (только заглавная буква + 1)."""
    return re.sub(r"(?<=[A-Z])1", "<sub>1</sub>", text)


def page(fonts_css=""):
    return html(fonts_css)


def fonts():
    """Шрифты серии кладём рядом (каталог .fonts в .gitignore); без сети — системные фолбэки."""
    d = HERE / ".fonts"
    css = d / "fonts.css"
    if not css.exists():
        d.mkdir(exist_ok=True)
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
        r = subprocess.run(["curl", "-sS", "-m", "20", "-A", ua, FONT_CSS], capture_output=True, text=True)
        if r.returncode != 0 or "@font-face" not in r.stdout:
            print("! шрифты не скачались, печать системными")
            return ""
        text = r.stdout
        for i, url in enumerate(sorted(set(re.findall(r"url\((https://[^)]+\.woff2)\)", text)))):
            name = f"f{i}.woff2"
            subprocess.run(["curl", "-sS", "-m", "20", "-o", str(d / name), url], check=True)
            text = text.replace(url, name)
        css.write_text(text)
    return re.sub(r"url\((f\d+\.woff2)\)", lambda mm: f"url(.fonts/{mm.group(1)})", css.read_text())


def build():
    check()
    (HERE / "print.html").write_text(page(fonts()))
    out = HERE / PDF_NAME
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    "--virtual-time-budget=8000", f"--print-to-pdf={out}", f"file://{HERE / 'print.html'}"],
                   check=True, capture_output=True)
    print("→", out.name)


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        build()
