# -*- coding: utf-8 -*-
"""Схемы к РГР по теме 9.

Аксонометрия: z вверх, x вправо, y на зрителя (влево-вниз) — как на схеме
элемента в тетради. Плоские схемы задачи 2 — оси x вправо, y вниз, угол α
отсчитывается от оси x вверх.

Правила черчения, принятые во всех схемах:
  * нормальные напряжения — стрелка по нормали к грани: растяжение от грани,
    сжатие к грани;
  * касательные — стрелка в плоскости грани, сдвинутая к её краю, чтобы
    не пересекаться со второй касательной и с нормальной;
  * невидимые рёбра — тонкий штрих; исходный контур — сплошной, деформи-
    рованный — штриховой полужирный;
  * подписи печатаются с белым ореолом (paint-order), поэтому читаются
    поверх линий.

Цвета не задаются: классы берут их из CSS страницы (документ чёрно-белый).
"""
import math

# ---------------------------------------------------------------- данные
SX, SY, SZ = -80.0, 60.0, -60.0
TXY, TYZ, TZX = 90.0, 50.0, -65.0
S1, S2, S3 = 105.9582, -7.1519, -178.8063
NU = {1: (0.39897, 0.90938, 0.11771),
      2: (0.55816, -0.13900, -0.81801),
      3: (0.72752, -0.39207, 0.56303)}
EX, EY, EZ = -38.095e-5, 48.571e-5, -25.714e-5
GXY, GYZ, GZX = 112.50e-5, 62.50e-5, -81.25e-5
T31, S31 = 142.38, -36.42

SX2, SY2, TXY2 = -85.0, -30.0, -30.0
P2, A2 = -16.8029, 66.26
P3, A3 = -98.1971, -23.74

# ------------------------------------------------------------ примитивы
HEAD = ('<svg viewBox="0 0 {w} {h}" role="img" aria-label="{alt}" '
        'xmlns="http://www.w3.org/2000/svg">\n<defs>\n'
        '<marker id="{m}" viewBox="0 0 10 10" refX="9.2" refY="5" '
        'markerWidth="6.4" markerHeight="6.4" orient="auto-start-reverse">'
        '<path d="M0 0.6 L10 5 L0 9.4 z" fill="context-stroke"/></marker>\n'
        '<marker id="{m}s" viewBox="0 0 10 10" refX="9.2" refY="5" '
        'markerWidth="5.2" markerHeight="5.2" orient="auto-start-reverse">'
        '<path d="M0 0.8 L10 5 L0 9.2 z" fill="context-stroke"/></marker>\n'
        '</defs>\n')

MID = "m"          # маркер обычной стрелки; MID + "s" — уменьшенной


def ln(p1, p2, cls):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}"/>\n')


def ar(p1, p2, cls, small=False):
    m = MID + ("s" if small else "")
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}" marker-end="url(#{m})"/>\n')


def ar2(p1, p2, cls):
    """Размерная линия со стрелками на обоих концах."""
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}" marker-start="url(#{MID}s)" '
            f'marker-end="url(#{MID}s)"/>\n')


def poly(pts, cls):
    return ('<polygon points="' +
            ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + f'" class="{cls}"/>\n')


def txt(x, y, s, cls="lbl", anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}">{s}</text>\n')


def sg(v, n=2):
    """Число со знаком в русской записи."""
    return f"{v:.{n}f}".replace(".", ",").replace("-", "−")


def sub(sym, idx):
    return f"{sym}<tspan class='sub'>{idx}</tspan>"


# ------------------------------------------------- аксонометрия (3D → 2D)
KY, KYV = -0.58, 0.40
VIEW = (0.58, 1.0, 0.40)
UNIT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


class Iso:
    def __init__(self, cx, cy, s):
        self.cx, self.cy, self.s = cx, cy, s

    def p(self, v):
        x, y, z = v
        return (self.cx + self.s * (x + KY * y),
                self.cy + self.s * (KYV * y - z))


def mv(M, v):
    return tuple(sum(M[i][j] * v[j] for j in range(3)) for i in range(3))


def add(*vs):
    return tuple(sum(v[i] for v in vs) for i in range(3))


def mul(v, k):
    return (v[0] * k, v[1] * k, v[2] * k)


def visible(n):
    return sum(a * b for a, b in zip(n, VIEW)) > 1e-9


FACES = []
for _ax in range(3):
    for _s in (1, -1):
        _n = [0, 0, 0]; _n[_ax] = _s
        _o1, _o2 = [k for k in range(3) if k != _ax]
        _pts = []
        for _a, _b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            _v = [0, 0, 0]; _v[_ax] = _s; _v[_o1] = _a; _v[_o2] = _b
            _pts.append(tuple(_v))
        FACES.append((tuple(_n), tuple(_pts), (_o1, _o2)))

IDENT = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def inplane(n):
    """Два орта, лежащие в грани с нормалью n."""
    ax = [i for i in range(3) if n[i]][0]
    return [UNIT[i] for i in range(3) if i != ax]


def draw_box(iso, M=IDENT, half=1.0, face="elem", hidden="hid"):
    def P(v):
        return iso.p(mul(mv(M, v), half))
    s = ""
    if hidden:
        for n, pts, _ in FACES:
            if not visible(mv(M, n)):
                for i in range(4):
                    s += ln(P(pts[i]), P(pts[(i + 1) % 4]), hidden)
    for n, pts, _ in FACES:
        if visible(mv(M, n)):
            s += poly([P(q) for q in pts], face)
    return s


def lab(iso, base, direction, dist):
    """Точка подписи: от base по экранному направлению, отступ в пикселях."""
    p0, p1 = iso.p(base), iso.p(add(base, direction))
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    return (p0[0] + dx / L * dist, p0[1] + dy / L * dist)


def stress_arrow(iso, c, n, val, near=0.12, far=1.22, cls="sig"):
    """Растяжение — от грани наружу, сжатие — снаружи к грани."""
    a, b = iso.p(add(c, mul(n, near))), iso.p(add(c, mul(n, far)))
    return ar(a, b, cls) if val > 0 else ar(b, a, cls)


def shear_arrow(iso, c, d, off, val, arm=0.46, cls="tau"):
    """Касательное напряжение: стрелка в плоскости грани, сдвинутая к краю."""
    dd = mul(d, 1.0 if val > 0 else -1.0)
    base = add(c, off)
    p1, p2 = iso.p(add(base, mul(dd, -arm))), iso.p(add(base, mul(dd, arm)))
    return ar(p1, p2, cls, small=True), p1, p2



def tip_label(p_tail, p_tip, away, along=11.0, side=15.0):
    """Точка подписи у острия стрелки: чуть дальше по стрелке и в сторону
    от центра элемента, чтобы подписи соседних стрелок не сливались."""
    ux, uy = p_tip[0] - p_tail[0], p_tip[1] - p_tail[1]
    L = math.hypot(ux, uy) or 1.0
    ux, uy = ux / L, uy / L
    vx, vy = -uy, ux
    if vx * (p_tip[0] - away[0]) + vy * (p_tip[1] - away[1]) < 0:
        vx, vy = -vx, -vy
    return (p_tip[0] + ux * along + vx * side,
            p_tip[1] + uy * along + vy * side)


def axes2d(x0, y0, s, names=("x", "y", "z")):
    out = ""
    for d, nm in zip(UNIT, names):
        p1 = (x0 + s * (d[0] + KY * d[1]), y0 + s * (KYV * d[1] - d[2]))
        out += ar((x0, y0), p1, "ax", small=True)
        p2 = (x0 + s * 1.3 * (d[0] + KY * d[1]), y0 + s * 1.3 * (KYV * d[1] - d[2]))
        out += txt(p2[0], p2[1] + 4, nm, "ax-lbl")
    return out


def legend(x, y, items, gap=150):
    """Пояснение к линиям: короткий образец + подпись."""
    out = ""
    for i, (cls, text) in enumerate(items):
        x0 = x + i * gap
        out += ln((x0, y - 4), (x0 + 26, y - 4), cls)
        out += txt(x0 + 32, y, text, "cap", "start")
    return out



# ================================================================ рис. 6
EX2, EY2, GXY2 = -36.1905e-5, -2.1429e-5, -37.50e-5
KDEF = 300                      # во столько раз увеличены деформации


EX2, EY2, EZ2 = -36.1905e-5, -2.1429e-5, 16.4286e-5
GXY2 = -37.50e-5
KLIN, KUGL = 500.0, 600.0       # во столько раз увеличены деформации


def fig_deform():
    """Деформации элемента в аксонометрии: линейные и угловая."""
    w, h = 540, 1010
    s = HEAD.format(w=w, h=h, m=MID, alt="Деформации элемента задачи 2")

    # ---------- а) линейные деформации
    iso = Iso(262, 252, 68)
    s += txt(262, 34, "а) линейные деформации: рёбра меняют длину", "cap")
    s += draw_box(iso, face="elem-lite")
    D = [[1 + KLIN * EX2, 0, 0], [0, 1 + KLIN * EY2, 0], [0, 0, 1 + KLIN * EZ2]]
    s += draw_box(iso, D, face="deformed", hidden=None)
    for n, val, name, what, dl in (((1, 0, 0), EX2, "x", "укорочение dx", 112),
                                   ((0, 1, 0), EY2, "y", "укорочение dy", 158),
                                   ((0, 0, 1), EZ2, "z", "удлинение dz", 124)):
        c = mul(n, 1.0)
        q = lab(iso, c, n, dl)
        s += txt(q[0], q[1] - 7, sub("ε", name), "lbl")
        v = sg(val * 1e5)
        s += txt(q[0], q[1] + 12,
                 ("" if v.startswith("−") else "+") + v + "·10⁻⁵", "val")
        s += txt(q[0], q[1] + 28, what, "cap")
    s += axes2d(462, 386, 36)
    s += txt(240, 438, "объёмная деформация θ = Σε\u1d62 = −21,90·10⁻⁵ "
                       "— объём уменьшился", "cap")
    s += txt(240, 458, f"деформации увеличены в {KLIN:.0f} раз", "cap")
    s += ln((30, 484), (510, 484), "sep")

    # ---------- б) угловая деформация
    s += '<g transform="translate(0,506)">\n'
    iso = Iso(262, 252, 64)
    s += txt(262, 34, "б) угловая деформация: прямые углы меняют величину", "cap")
    s += txt(262, 58, sub("γ", "xy") + " = −37,50·10⁻⁵ — угол между x и y "
                      "увеличился", "lbl")
    s += txt(262, 78, sub("γ", "yz") + " = " + sub("γ", "zx")
             + " = 0 — в этих плоскостях сдвига нет", "cap")
    s += draw_box(iso, face="elem-lite")
    Fm = [[1.0, KUGL * GXY2, 0], [0, 1.0, 0], [0, 0, 1.0]]
    s += draw_box(iso, Fm, face="deformed", hidden=None)
    for n, pts, _ in FACES:                      # грань в плоскости xOy
        if n == (0, 0, 1):
            s += poly([iso.p(mv(Fm, q)) for q in pts], "face-hi")

    def side(idx):
        k = 1 if VIEW[idx] > 0 else -1
        v = [0, 0, 0]
        v[idx] = k
        return tuple(v)
    a1, a2 = side(0), side(1)
    corner = add((0, 0, 1), a1, a2)
    e1, e2 = mul(a1, -1), mul(a2, -1)
    d = 0.42
    s += ('<polyline points="' + " ".join(
        f"{q[0]:.1f},{q[1]:.1f}" for q in (
            iso.p(add(corner, mul(e1, d))),
            iso.p(add(corner, mul(e1, d), mul(e2, d))),
            iso.p(add(corner, mul(e2, d))))) + '" class="right-angle"/>\n')
    pc = iso.p(mv(Fm, corner))
    q1 = iso.p(mv(Fm, add(corner, mul(e1, 0.72))))
    q2 = iso.p(mv(Fm, add(corner, mul(e2, 0.72))))
    s += (f'<path d="M {q1[0]:.1f} {q1[1]:.1f} Q {pc[0]:.1f} {pc[1]:.1f} '
          f'{q2[0]:.1f} {q2[1]:.1f}" class="arc-def"/>\n')
    s += f'<circle cx="{pc[0]:.1f}" cy="{pc[1]:.1f}" r="3" class="vertex"/>\n'
    s += axes2d(462, 386, 36)
    s += txt(240, 438, f"углы увеличены примерно в {KUGL:.0f} раз", "cap")
    s += "</g>\n"

    s += legend(116, 992, [("elem-lite", "до деформации"),
                           ("deformed", "после деформации"),
                           ("face-hi", "грань в плоскости xOy")], gap=152)
    s += '</svg>\n'
    return s


# ================================================================ рис. 1

def fig21_plate():
    """Тонкая пластина, нагруженная по контуру, и вырезанный элемент."""
    # Панели идут одна под другой, а не в ряд: в ряд схема получалась
    # шириной во всю полосу, упиралась в неё и печаталась мельче остальных.
    w, h = 520, 830
    s = HEAD.format(w=w, h=h, m=MID,
                    alt="Тонкая пластина и выделенный из неё объёмный элемент")
    s += ln((30, 412), (490, 412), "sep")

    # ---------- а) пластина -------------------------------------------
    iso = Iso(240, 196, 78)
    s += txt(240, 42, "а) тонкая пластина, нагруженная по контуру", "cap")
    A, B, H = 1.5, 1.0, 0.11
    s += draw_box(iso, [[A, 0, 0], [0, B, 0], [0, 0, H]])

    # нагрузка по контуру: оба напряжения сжимающие -> стрелки к кромкам
    for n, half in (((1, 0, 0), A), ((0, 1, 0), B)):
        other = (0, 1, 0) if n[0] else (1, 0, 0)
        oh = B if n[0] else A
        for k in (1, -1):
            for t in (-0.6, 0.0, 0.6):
                base = add(mul(n, k * half), mul(other, t * oh))
                d = mul(n, k)
                s += ar(iso.p(add(base, mul(d, 0.62))),
                        iso.p(add(base, mul(d, 0.10))), "sig")
    q = lab(iso, mul((1, 0, 0), A), (1, 0, 0), 84)
    s += txt(q[0], q[1] + 5, sub("q", "x"), "lbl")
    q = lab(iso, mul((0, 1, 0), B), (0, 1, 0), 124)
    s += txt(q[0], q[1] + 5, sub("q", "y"), "lbl")

    # место, откуда вырезан элемент
    e = 0.19
    s += poly([iso.p(p) for p in (( e,  e, H), (-e,  e, H),
                                  (-e, -e, H), ( e, -e, H))], "elem")
    p0 = iso.p((0, 0, H))
    s += ln((p0[0] + 8, p0[1] - 8), (316, 84), "leader")
    s += txt(322, 80, "выделенный элемент", "cap", "start")

    # размеры b, a, h
    pb1, pb2 = iso.p((-A, B, -H)), iso.p((A, B, -H))
    s += ln(pb1, (pb1[0], pb1[1] + 40), "ext")
    s += ln(pb2, (pb2[0], pb2[1] + 40), "ext")
    s += ar2((pb1[0], pb1[1] + 32), (pb2[0], pb2[1] + 32), "dim")
    s += txt((pb1[0] + pb2[0]) / 2, pb1[1] + 27, "b", "ax-lbl")

    pa1, pa2 = iso.p((-A, -B, H)), iso.p((-A, B, H))
    ux, uy = pa2[0] - pa1[0], pa2[1] - pa1[1]
    L = math.hypot(ux, uy)
    vx, vy = -uy / L, ux / L                      # наружу от пластины
    if vx > 0:
        vx, vy = -vx, -vy
    o = 46
    s += ln(pa1, (pa1[0] + vx * (o + 8), pa1[1] + vy * (o + 8)), "ext")
    s += ln(pa2, (pa2[0] + vx * (o + 8), pa2[1] + vy * (o + 8)), "ext")
    s += ar2((pa1[0] + vx * o, pa1[1] + vy * o),
             (pa2[0] + vx * o, pa2[1] + vy * o), "dim")
    s += txt((pa1[0] + pa2[0]) / 2 + vx * (o + 14),
             (pa1[1] + pa2[1]) / 2 + vy * (o + 14) + 4, "a", "ax-lbl")

    ph1, ph2 = iso.p((-A, B, H)), iso.p((-A, B, -H))
    s += ln(ph1, (ph1[0] - 34, ph1[1]), "ext")
    s += ln(ph2, (ph2[0] - 34, ph2[1]), "ext")
    s += ar2((ph1[0] - 26, ph1[1]), (ph2[0] - 26, ph2[1]), "dim")
    s += txt(ph1[0] - 34, (ph1[1] + ph2[1]) / 2 + 5, "h", "ax-lbl", "end")

    s += txt(240, 388, "h ≪ a, b — напряжения по толщине не меняются", "cap")
    s += axes2d(70, 330, 36)

    # ---------- б) объёмный элемент ------------------------------------
    # панель рисуется в своих прежних координатах и сдвигается целиком
    s += '<g transform="translate(-462,432)">\n'
    iso = Iso(722, 222, 70)
    s += txt(722, 42, "б) объёмный элемент в окрестности точки", "cap")
    s += draw_box(iso)
    mid0 = iso.p((0, 0, 0))
    for n, sv, name, dl, (d, tv, tname, off) in (
            ((1, 0, 0), SX2, "x", 96, ((0, 1, 0), TXY2, "xy", (0, 0, 0.62))),
            ((0, 1, 0), SY2, "y", 134, ((1, 0, 0), TXY2, "yx", (0, 0, -0.62)))):
        c = mul(n, 1.0)
        s += stress_arrow(iso, c, n, sv)
        q = lab(iso, c, n, dl)
        s += txt(q[0], q[1] - 7, sub("σ", name), "lbl")
        s += txt(q[0], q[1] + 12, sg(sv, 0) + " МПа", "val")
        arrow, p1, p2 = shear_arrow(iso, c, d, off, tv)
        s += arrow
        q = tip_label(p1, p2, mid0)
        s += txt(q[0], q[1] + 4, sub("τ", tname), "tau-lbl")
    # грани с нормалью z свободны — подпись внизу панели, с выноской к грани
    ptop = iso.p((0.3, -0.3, 1.0))
    s += ln((ptop[0], ptop[1]), (836, 104), "leader")
    s += txt(842, 94, "грань свободна:", "cap", "start")
    s += txt(842, 114, f"{sub('σ', 'z')} = 0", "lbl-s", "start")
    s += txt(842, 134, f"{sub('τ', 'zx')} = {sub('τ', 'zy')} = 0",
             "lbl-s", "start")
    s += axes2d(900, 326, 36)
    s += "</g>\n"
    s += '</svg>\n'
    return s


# ================================================================ рис. 2.2
def fig22_flat():
    """Плоский элемент: нормальные — по серединам граней, касательные
    сдвинуты к краям, поэтому стрелки нигде не пересекаются."""
    w, h = 600, 412
    cx, cy, a = 296, 214, 96
    s = HEAD.format(w=w, h=h, m=MID,
                    alt="Напряжения на гранях элемента при плоском состоянии")
    s += ar((50, 46), (128, 46), "ax", small=True) + txt(137, 51, "x", "ax-lbl")
    s += ar((50, 46), (50, 124), "ax", small=True) + txt(50, 141, "y", "ax-lbl")
    s += f'<circle cx="50" cy="46" r="2.8" class="dot"/>\n'
    s += (f'<rect x="{cx-a}" y="{cy-a}" width="{2*a}" height="{2*a}" '
          f'class="elem"/>\n')

    # нормальные: оба сжимающие -> стрелки снаружи к серединам граней
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        fx, fy = cx + dx * a, cy + dy * a
        s += ar((fx + dx * 68, fy + dy * 68), (fx + dx * 9, fy + dy * 9), "sig")
    s += txt(cx + a + 78, cy - 9, sub("σ", "x"), "lbl", "start")
    s += txt(cx + a + 78, cy + 13, sg(SX2, 0) + " МПа", "val", "start")
    s += txt(cx, cy - a - 86, sub("σ", "y"), "lbl")
    s += txt(cx, cy - a - 66, sg(SY2, 0) + " МПа", "val")

    # касательные: τxy < 0 -> на грани +x вверх, +y влево; сдвинуты к краям
    off, g = 15, 0.5 * a
    arms = 40
    pairs = [((cx + a + off, cy - g + arms), (cx + a + off, cy - g - arms),
              "xy", (cx + a + off + 10, cy - g - arms - 8), "start"),
             ((cx - a - off, cy + g - arms), (cx - a - off, cy + g + arms),
              "xy", (cx - a - off - 10, cy + g + arms + 16), "end"),
             ((cx + g + arms, cy + a + off), (cx + g - arms, cy + a + off),
              "yx", (cx + g + arms + 10, cy + a + off + 16), "start"),
             ((cx - g - arms, cy - a - off), (cx - g + arms, cy - a - off),
              "yx", (cx - g - arms - 10, cy - a - off - 8), "end")]
    for p1, p2, name, lp, anch in pairs:
        s += ar(p1, p2, "tau")
        if name:
            s += txt(lp[0], lp[1], sub("τ", name), "tau-lbl", anch)
            if lp[1] < cy:                    # значение пишем один раз на пару
                s += txt(lp[0], lp[1] + 19, sg(TXY2, 0) + " МПа",
                         "tau-val", anch)
    s += '</svg>\n'
    return s


# ================================================================ рис. 2.3
def fig23_main():
    w, h = 620, 432
    cx, cy, a = 292, 216, 78
    s = HEAD.format(w=w, h=h, m=MID,
                    alt="Главные площадки и главные напряжения задачи 2")

    def uv(deg):
        r = math.radians(deg)
        return math.cos(r), -math.sin(r)
    n2, n3 = uv(A2), uv(A3)

    s += ar((cx - 188, cy), (cx + 196, cy), "ax", small=True)
    s += txt(cx + 206, cy + 5, "x", "ax-lbl")
    s += ar((cx, cy), (cx, cy + 176), "ax", small=True)
    s += txt(cx - 15, cy + 182, "y", "ax-lbl")

    pts = [(cx + a * (q2 * n2[0] + q3 * n3[0]),
            cy + a * (q2 * n2[1] + q3 * n3[1]))
           for q2, q3 in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
    s += poly(pts, "elem")

    for n, val, name in ((n2, P2, "1"), (n3, P3, "2")):
        s += ln((cx - 152 * n[0], cy - 152 * n[1]),
                (cx + 152 * n[0], cy + 152 * n[1]), "norm")
        for k in (1, -1):
            fx, fy = cx + k * a * n[0], cy + k * a * n[1]
            s += ar((fx + k * 62 * n[0], fy + k * 62 * n[1]),
                    (fx + k * 9 * n[0], fy + k * 9 * n[1]), "sig")
        lx, ly = cx + 182 * n[0], cy + 182 * n[1]
        s += txt(lx, ly - 7, sub("σ", name), "lbl")
        s += txt(lx, ly + 13, sg(val) + " МПа", "val")

    # дуги углов: разные радиусы, каждая упирается в свою нормаль
    for deg, name, r in ((A2, "α₁ = 66,26°", 96), (A3, "α₂ = −23,74°", 132)):
        ex = cx + r * math.cos(math.radians(deg))
        ey = cy - r * math.sin(math.radians(deg))
        sweep = 1 if deg < 0 else 0
        s += (f'<path d="M {cx + r} {cy} A {r} {r} 0 0 {sweep} {ex:.1f} '
              f'{ey:.1f}" class="arc"/>\n')
        md = math.radians(deg / 2)
        s += txt(cx + (r + 16) * math.cos(md) + 6,
                 cy - (r + 16) * math.sin(md) + 5, name, "ang", "start")
    s += '</svg>\n'
    return s


# ---------------------------------------------------------------- п. 4
A_TAU = A2 - 45          # нормаль к площадке наибольшего τ в плоскости
S_SR = -57.5             # σ\' = (σ2+σ3)/2
T_23 = 40.6971           # τ23 = радиус круга Мора в плоскости
AL5 = 15
S_NU, S_T, T_TNU = -66.3157, -48.6843, -39.7308


def uv(deg):
    """Единичный вектор под углом deg к оси x; ось y на листе — вниз."""
    r = math.radians(deg)
    return math.cos(r), -math.sin(r)


def povernutyy(cx, cy, a, ang, sig_u, sig_v, tau_znak):
    """Квадратный элемент, повёрнутый на ang: нормальные и касательные.

    sig_u, sig_v — напряжения на гранях с нормалями u и v (оба сжатия,
    поэтому стрелки направлены внутрь). tau_znak задаёт сторону обхода
    касательных: пара образует уравновешенный момент.
    """
    u, v = uv(ang), uv(ang + 90)
    pts = [(cx + a * (p * u[0] + q * v[0]), cy + a * (p * u[1] + q * v[1]))
           for p, q in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
    s = poly(pts, "elem")
    for w in (u, v):
        for k in (1, -1):
            fx, fy = cx + k * a * w[0], cy + k * a * w[1]
            s += ar((fx + k * 58 * w[0], fy + k * 58 * w[1]),
                    (fx + k * 10 * w[0], fy + k * 10 * w[1]), "sig")
    for w, z, sgn in ((u, v, tau_znak), (v, u, -tau_znak)):
        for k in (1, -1):
            fx, fy = cx + k * a * w[0], cy + k * a * w[1]
            s += ar((fx - sgn * k * 40 * z[0], fy - sgn * k * 40 * z[1]),
                    (fx + sgn * k * 40 * z[0], fy + sgn * k * 40 * z[1]), "tau")
    return s, u, v


def vynos(cx, cy, a, u, v, sdvig, text, anchor="middle", dal=100):
    """Подпись за стрелками: вдоль нормали u на dal и вбок на sdvig по v."""
    x = cx + u[0] * (a + dal) + v[0] * sdvig
    y = cy + u[1] * (a + dal) + v[1] * sdvig
    return txt(x, y, text, "val", anchor)


def fig24_tau():
    """Площадки экстремальных касательных напряжений в плоскости пластины."""
    w, h = 700, 500
    cx, cy, a = 330, 252, 68
    s = HEAD.format(w=w, h=h, m=MID,
                    alt="Площадки экстремальных касательных напряжений задачи 2")
    s += ar((cx - 208, cy), (cx + 216, cy), "ax", small=True)
    s += txt(cx + 226, cy + 5, "x", "ax-lbl")
    s += ar((cx, cy), (cx, cy + 190), "ax", small=True)
    s += txt(cx - 16, cy + 202, "y", "ax-lbl")

    for d, nm in ((A2, "σ₁"), (A3, "σ₂")):      # главные направления — пунктир
        n = uv(d)
        s += ln((cx - 168 * n[0], cy - 168 * n[1]),
                (cx + 168 * n[0], cy + 168 * n[1]), "hid")
        s += txt(cx + 186 * n[0], cy + 186 * n[1] + 5, nm, "ang")

    body, u, v = povernutyy(cx, cy, a, A_TAU, S_SR, S_SR, 1)
    s += body
    s += vynos(cx, cy, a, u, v, -34, "σ\u2032 = " + sg(S_SR) + " МПа", "start")
    s += vynos(cx, cy, a, v, u, 30, "τ₁₂ = ±" + sg(T_23) + " МПа")
    r0 = 116
    ex, ey = cx + r0 * math.cos(math.radians(A_TAU)), cy - r0 * math.sin(math.radians(A_TAU))
    s += f'<path d="M {cx + r0} {cy} A {r0} {r0} 0 0 0 {ex:.1f} {ey:.1f}" class="arc"/>\n'
    s += txt(cx + r0 + 24, cy + 26, "α = 21,26°", "ang", "start")
    s += '</svg>\n'
    return s


def fig25_alpha():
    """Площадки, повёрнутые на α = 15° к осям Ox и Oy."""
    w, h = 700, 480
    cx, cy, a = 330, 236, 68
    s = HEAD.format(w=w, h=h, m=MID,
                    alt="Напряжения на площадках под углом 15° к осям")
    s += ar((cx - 208, cy), (cx + 212, cy), "ax", small=True)
    s += txt(cx + 222, cy + 5, "x", "ax-lbl")
    s += ar((cx, cy), (cx, cy + 184), "ax", small=True)
    s += txt(cx - 16, cy + 196, "y", "ax-lbl")

    body, u, v = povernutyy(cx, cy, a, AL5, S_NU, S_T, -1)
    for w_, nm in ((u, "ν"), (v, "t")):         # нормали к площадкам
        s += ln((cx, cy), (cx + 196 * w_[0], cy + 196 * w_[1]), "norm")
        s += txt(cx + 210 * w_[0], cy + 210 * w_[1] + 5, nm, "ax-lbl")
    s += body
    s += vynos(cx, cy, a, u, v, -26, "σ\u03bd = " + sg(S_NU) + " МПа",
               "start", dal=74)
    s += vynos(cx, cy, a, v, u, 62, "σ\u209c = " + sg(S_T) + " МПа",
               "start", dal=76)
    s += vynos(cx, cy, a, (-u[0], -u[1]), v, 6,
               "τ\u209c\u03bd = " + sg(T_TNU) + " МПа", "end", dal=52)
    r0 = 128
    ex, ey = cx + r0 * math.cos(math.radians(AL5)), cy - r0 * math.sin(math.radians(AL5))
    s += f'<path d="M {cx + r0} {cy} A {r0} {r0} 0 0 0 {ex:.1f} {ey:.1f}" class="arc"/>\n'
    s += txt(cx + r0 + 18, cy + 30, "α = 15°", "ang", "start")
    s += '</svg>\n'
    return s


MPA = 1 / 0.187     # единиц viewBox на 1 МПа: при MM_NA_ED = 0,187 это 1 мм


def txt_r(x, y, s, ang, cls="val halo", anchor="middle"):
    """Подпись, повёрнутая на угол ang (градусы, по часовой стрелке)."""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" '
            f'transform="rotate({ang:.2f} {x:.1f} {y:.1f})">{s}</text>\n')


def dug(cx, cy, r, a0, a1):
    """Дуга угла от a0 до a1 (градусы, против часовой в осях σ-τ)."""
    p0 = (cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0)))
    p1 = (cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1)))
    sweep = 0 if a1 > a0 else 1
    return (f'<path d="M {p0[0]:.1f} {p0[1]:.1f} A {r:.1f} {r:.1f} 0 0 {sweep} '
            f'{p1[0]:.1f} {p1[1]:.1f}" class="arc"/>\n')


def fig26_mohr():
    """Круг Мора в масштабе тетради: 1 см = 10 МПа (1 МПа = 1 мм на листе).

    Всё на одной окружности, как в конспекте: построение (D, B, C, K,
    радиус CK, размеры) и то, что с круга снимается (σ₁, σ₂, углы через
    полюс K, экстремальные касательные T₁, T₂, площадки под α = 15° — P, P′).
    Числа у точек T, P, P′ не пишутся — они в подписи к рисунку, чтобы
    не загромождать чертёж; у точек только буквы.

    Полюс K(σy; τxy): прямая из K под углом α к оси σ пересекает круг
    в точке (σα; τα) площадки с нормалью под α к оси x — так в конспекте
    найдены углы главных площадок (лучи K–σ₁ и K–σ₂).
    """
    k = MPA
    sx_, sy_, t_ = SX2, SY2, TXY2
    c_ = (sx_ + sy_) / 2
    r_ = math.hypot((sx_ - sy_) / 2, t_)
    s1, s2 = c_ + r_, c_ - r_

    def na_kruge(al):
        """Вторая точка пересечения прямой из полюса K под углом al с кругом."""
        ca, sa = math.cos(math.radians(al)), math.sin(math.radians(al))
        d = -2 * ((sy_ - c_) * ca + t_ * sa)
        return (sy_ + d * ca, t_ + d * sa)

    a1 = math.degrees(math.atan2(0 - t_, s1 - sy_))          # луч K–σ₁
    a2 = math.degrees(math.atan2(0 - t_, s2 - sy_)) - 180    # луч K–σ₂
    AL = 15.0
    Pn, Pt = na_kruge(AL), na_kruge(AL + 90)

    ox = 122 * k                   # σ = 0 на расстоянии 122 мм от левого края
    w = ox + 30 * k
    oy0 = 62 * k                  # ось τ = 0
    h = oy0 + 70 * k
    s = HEAD.format(w=f"{w:.0f}", h=f"{h:.0f}", m=MID,
                    alt="Круг Мора: построение и что с него снимается")

    def osnova(oy, bukva):
        X = lambda v: ox + v * k
        Y = lambda v: oy - v * k
        g = (f'<g data-panel="{bukva}" data-ox="{ox:.3f}" data-oy="{oy:.3f}" '
             f'data-k="{k:.5f}">\n')
        for v in range(-110, 11, 10):                          # сетка 10 МПа
            g += ln((X(v), Y(40)), (X(v), Y(-40)), "grid")
        for v in range(-40, 41, 10):
            g += ln((X(-110), Y(v)), (X(10), Y(v)), "grid")
        g += ar((X(-114), Y(0)), (X(17), Y(0)), "ax", small=True)
        g += txt(X(18), Y(0) + 5, "σ, МПа", "ax-lbl", "start")
        g += ar((X(0), Y(-44)), (X(0), Y(53)), "ax", small=True)
        g += txt(X(0) + 9, Y(53) + 9, "τ, МПа", "ax-lbl", "start")
        g += txt(X(1.2), Y(0) + 17, "O", "lbl halo", "start")
        g += (f'<circle cx="{X(c_):.2f}" cy="{Y(0):.2f}" r="{r_ * k:.2f}" '
              f'class="plane-edge"/>\n')
        return g, X, Y

    def tochka(X, Y, nm, v):
        return (f'<circle data-pt="{nm}" cx="{X(v[0]):.2f}" cy="{Y(v[1]):.2f}" '
                f'r="3.6" class="dot"/>\n')

    def razmer(X, Y, a, b, tau, text, ot=0.0):
        """Горизонтальный размер от σ=a до σ=b на уровне tau."""
        g = ln((X(a), Y(ot) + (5 if tau < ot else -5)),
               (X(a), Y(tau) + (6 if tau < ot else -6)), "ext")
        g += ln((X(b), Y(ot) + (5 if tau < ot else -5)),
                (X(b), Y(tau) + (6 if tau < ot else -6)), "ext")
        g += ar2((X(a), Y(tau)), (X(b), Y(tau)), "dim")
        g += txt((X(a) + X(b)) / 2, Y(tau) - 5, text, "val halo")
        return g

    sxs, sys_ = sub("σ", "x"), sub("σ", "y")
    tau_xy = sub("τ", "xy")

    g, X, Y = osnova(oy0, "1")
    D, B, C, Kp = (sx_, 0.0), (sy_, 0.0), (c_, 0.0), (sy_, t_)
    T1, T2 = (c_, r_), (c_, -r_)
    Xp = (sx_, t_)                                 # площадка x, α = 0

    # ---- построение: катеты CB и BK, гипотенуза CK = R
    g += ln((X(C[0]), Y(0)), (X(Kp[0]), Y(Kp[1])), "tri")        # CK = R
    g += ln((X(B[0]), Y(0)), (X(Kp[0]), Y(Kp[1])), "tri")        # BK = τxy
    pr = 9
    g += ('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in (
        (X(B[0]) - pr, Y(0)), (X(B[0]) - pr, Y(0) + pr), (X(B[0]), Y(0) + pr)))
        + '" class="right-angle"/>\n')
    g += txt_r(X(B[0]) + 11, Y(-11), f"{tau_xy} = {sg(t_, 0)}", -90)
    ug = math.degrees(math.atan2(Y(Kp[1]) - Y(0), X(Kp[0]) - X(C[0])))
    mx, my = (X(C[0]) + X(Kp[0])) / 2, (Y(0) + Y(Kp[1])) / 2
    nx, ny = math.sin(math.radians(ug)), -math.cos(math.radians(ug))
    g += txt_r(mx - 12 * nx - 14, my - 12 * ny - 6, f"R = {sg(r_)}", ug)
    # размерная цепочка DC = CB над кругом, размеры от O — под кругом
    # DC = CB — короткой цепочкой прямо над осью
    for a, b in ((D[0], C[0]), (C[0], B[0])):
        for v in (a, b):
            g += ln((X(v), Y(1)), (X(v), Y(7.5)), "ext")
        g += ar2((X(a), Y(5.5)), (X(b), Y(5.5)), "dim")
    g += txt((X(D[0]) + X(C[0])) / 2, Y(5.5) - 5, f"DC = CB = {sg((sy_ - sx_) / 2, 1)}", "val halo")
    # на CB только число: правее его пересекают прямые x₁ и t
    g += txt(X(C[0] + 6.5), Y(5.5) - 5, sg((sy_ - sx_) / 2, 1), "val halo")
    g += razmer(X, Y, 0.0, B[0], -46, f"OB = {sys_} = {sg(sy_, 0)}")
    g += razmer(X, Y, 0.0, C[0], -51.5,
                f"OC = ({sxs} + {sys_})/2 = {sub('σ', 'x1')} = {sub('σ', 'y1')} = {sg(c_)}")
    g += razmer(X, Y, 0.0, Pn[0], -57, f"{sub('σ', 'ν')} = {sg(Pn[0])}", ot=Pn[1])
    g += razmer(X, Y, 0.0, D[0], -62.5, f"OD = {sxs} = {sg(sx_, 0)}")
    # над кругом — абсцисса точки P′
    g += razmer(X, Y, 0.0, Pt[0], 46, f"{sub('σ', 't')} = {sg(Pt[0])}", ot=Pt[1])

    def razmer_v(tochka_, x_dim, text, sleva):
        """Вертикальный размер: ордината точки, от оси σ до уровня точки."""
        sx9, st9 = tochka_
        z = 1 if x_dim > sx9 else -1
        out = ln((X(sx9) + 5 * z, Y(st9)), (X(x_dim) + 6 * z, Y(st9)), "ext")
        out += ar2((X(x_dim), Y(0)), (X(x_dim), Y(st9)), "dim")
        xt = X(x_dim) - 5 if sleva else X(x_dim) + 16
        out += txt_r(xt, (Y(0) + Y(st9)) / 2, text, -90)
        return out

    # ординаты точек P и P′ — у полей чертежа, чтобы не пересекать лучи
    g += razmer_v(Pn, -106, f"{sub('τ', 'tν')} = {sg(Pn[1])}", True)
    g += razmer_v(Pt, 6, f"τ = +{sg(Pt[1])} = −{sub('τ', 'tν')}", False)

    def luch(p_from, p_to, za, cls, metka=None, m_off=(0, 0), os_=None):
        """Прямая через p_from и p_to, продлённая за p_to на za МПа (со стрелкой)."""
        dx, dy = p_to[0] - p_from[0], p_to[1] - p_from[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        a = (p_from[0] - 5 * ux, p_from[1] - 5 * uy)
        b = (p_to[0] + za * ux, p_to[1] + za * uy)
        out = ar((X(a[0]), Y(a[1])), (X(b[0]), Y(b[1])), cls)
        if os_:
            out = out.replace("<line ", f'<line data-os="{os_}" ', 1)
        if metka:
            out += txt(X(b[0]) + m_off[0], Y(b[1]) + m_off[1], metka, "lbl halo")
        return out

    # ---- что снимается: лучи из полюса K
    g += ln((X(Xp[0]), Y(t_)), (X(sy_ + 21), Y(t_)), "norm")   # горизонталь K–X
    g += luch((sy_, t_), (s1, 0.0), 24, "ray", "1", (8, 4), "1")
    g += luch((s2, 0.0), (sy_, t_), 16, "ray", "2", (6, 16), "2")
    g += luch(Pn, (sy_, t_), 20, "ray2", "ν", (10, 3), "ν")
    g += luch(Pt, (sy_, t_), 11, "ray2", "t", (11, 6), "t")
    # оси x₁, y₁ элемента с экстремальными касательными (рисунок 3 конспекта):
    # x₁ = ось 1 + 45° — через T₁, y₁ = ось 1 − 45° — через T₂
    g += luch((sy_, t_), T1, 8, "ray3", "x₁", (-9, -4), "x1")
    g += luch(T2, (sy_, t_), 27, "ray3", "y₁", (11, 2), "y1")
    # углы
    g += dug(X(s1), Y(0), 11 * k, 0, a1)
    g += txt(X(s1) + 12.5 * k, Y(0) - 5.5 * k, "α₁", "ang halo", "start")
    g += txt(X(sy_ + 51 * math.cos(math.radians(a1)) - 2.5),
             Y(t_ + 51 * math.sin(math.radians(a1))) + 5,
             f"α₁ = {sg(a1)}°", "val halo", "end")
    g += dug(X(s2), Y(0), 15 * k, a2, 0)
    g += txt(X(s2) + 17 * k, Y(0) + 4.2 * k, f"α₂ = {sg(a2)}°", "val halo", "start")
    g += dug(X(sy_), Y(t_), 13 * k, 0, AL)
    g += txt(X(sy_) + 14.5 * k, Y(t_) - 0.6 * k, f"α = {AL:.0f}°", "val halo", "start")

    for nm, v in (("O", (0.0, 0.0)), ("D", D), ("C", C), ("B", B), ("K", Kp),
                  ("σ1", (s1, 0.0)), ("σ2", (s2, 0.0)), ("T1", T1), ("T2", T2),
                  ("X", Xp), ("P", Pn), ("P'", Pt)):
        g += tochka(X, Y, nm, v)
    g += txt(X(D[0]) - 5, Y(0) - 7, "D", "lbl halo", "end")
    g += txt(X(C[0]) - 5, Y(0) + 18, "C", "lbl halo", "end")
    g += txt(X(B[0]) + 5, Y(0) - 7, "B", "lbl halo", "start")
    g += txt(X(sy_) + 16, Y(t_) + 30, "K", "lbl halo", "start")
    g += txt(X(s1) + 4, Y(0) + 18, f"σ₁ = {sg(s1)}", "val halo", "start")
    g += txt(X(s2) - 6, Y(0) - 7, f"σ₂ = {sg(s2)}", "val halo", "end")
    g += txt(X(Xp[0]) - 7, Y(Xp[1]) + 6, "X", "lbl halo", "end")
    g += txt(X(T1[0]) - 7, Y(T1[1]) - 6, "T₁", "lbl halo", "end")
    g += txt(X(T2[0]) + 5, Y(T2[1]) + 21, "T₂", "lbl halo", "start")
    g += txt(X(Pn[0]) - 7, Y(Pn[1]) + 19, "P", "lbl halo", "end")
    g += txt(X(Pt[0]) + 8, Y(Pt[1]) - 5, "P′", "lbl halo", "start")
    s += g + "</g>\n"
    s += "</svg>\n"
    return s


if __name__ == "__main__":
    # контроль знака угловой деформации на рис. 6: при γxy < 0 прямой угол
    # между осями x и y должен увеличиться
    ug = math.degrees(math.atan(abs(GXY2 * KUGL)))
    print(f"рис. 6: прямой угол изменился на {ug:.2f}° "
          f"({'увеличился' if GXY2 < 0 else 'уменьшился'}) — "
          f"{'ok' if GXY2 < 0 else 'проверить знак'}")
    # порядок — как в документе: схема N появляется в тексте N-й по счёту
    for name, fn in (("fig-1", fig21_plate), ("fig-2", fig22_flat),
                     ("fig-3", fig23_main), ("fig-4", fig24_tau),
                     ("fig-5", fig25_alpha), ("fig-6", fig_deform),
                     ("fig-7", fig26_mohr)):
        open(name + ".svg", "w", encoding="utf-8").write(fn())
    print("схемы собраны: 7")
