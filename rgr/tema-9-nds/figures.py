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


def fig26_mohr():
    """Круг Мора с полной разметкой построения: видно, что из чего берётся."""
    K = 4.6
    w, h = 760, 640
    ox, oy = 622.0, 300.0
    sx_, sy_, t_ = -85.0, -30.0, -30.0
    c_pl, r_pl = -57.5, 40.6971
    s1, s2 = -16.8029, -98.1971
    s_nu, t_tnu = -66.3157, -39.7308
    s = HEAD.format(w=w, h=h, m=MID, alt="Круг Мора: построение и результаты")
    X = lambda v: ox + v * K
    Y = lambda v: oy - v * K

    # оси
    s += ar((X(-106), oy), (X(11), oy), "ax", small=True)
    s += txt(X(16), oy + 5, "σ, МПа", "ax-lbl", "start")
    s += ar((ox, Y(-52)), (ox, Y(52)), "ax", small=True)
    s += txt(ox + 14, Y(54), "τ, МПа", "ax-lbl", "start")
    s += f'<circle cx="{ox}" cy="{oy}" r="3" class="dot"/>\n'
    s += txt(ox + 9, oy + 21, "O", "lbl", "start")

    s += (f'<circle cx="{X(c_pl):.1f}" cy="{oy:.1f}" r="{r_pl * K:.1f}" '
          f'class="plane-edge" fill="none"/>\n')

    P = {"D": (sx_, 0.0), "B": (sy_, 0.0), "C": (c_pl, 0.0), "K": (sy_, t_),
         "X": (sx_, t_), "s1": (s1, 0.0), "s2": (s2, 0.0),
         "t1": (c_pl, r_pl), "t2": (c_pl, -r_pl), "P": (s_nu, t_tnu)}
    px = {k: (X(v[0]), Y(v[1])) for k, v in P.items()}

    # ---- построение: катеты CB и BK, гипотенуза CK = R
    s += ln(px["C"], px["K"], "dim")
    s += ln(px["B"], px["K"], "dim")
    s += ln(px["C"], px["X"], "dim")
    s += ln(px["C"], px["P"], "dim")
    s += ln(px["D"], px["X"], "leader")
    pr = 13                                     # значок прямого угла при B
    s += ('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in (
        (px["B"][0] - pr, px["B"][1]), (px["B"][0] - pr, px["B"][1] + pr),
        (px["B"][0], px["B"][1] + pr))) + '" class="right-angle"/>\n')

    # размерная цепочка DC = CB над осью
    yd = oy - 30
    for a, b in (("D", "C"), ("C", "B")):
        s += ln((px[a][0], oy - 6), (px[a][0], yd - 6), "ext")
        s += ln((px[b][0], oy - 6), (px[b][0], yd - 6), "ext")
        s += ar2((px[a][0], yd), (px[b][0], yd), "dim")
        s += txt((px[a][0] + px[b][0]) / 2, yd - 6, "27,5", "val")
    # размер BK справа от катета
    xb = px["B"][0] + 22
    s += ln((px["B"][0] + 6, px["B"][1]), (xb + 6, px["B"][1]), "ext")
    s += ln((px["K"][0] + 6, px["K"][1]), (xb + 6, px["K"][1]), "ext")
    s += ar2((xb, px["B"][1]), (xb, px["K"][1]), "dim")
    s += txt(xb + 10, (px["B"][1] + px["K"][1]) / 2 + 5,
             "BK = τxy = −30", "val", "start")
    # размер OC под кругом
    yo = oy + 232
    s += ln((ox, oy + 6), (ox, yo + 6), "ext")
    s += ln((px["C"][0], px["C"][1] + 6), (px["C"][0], yo + 6), "ext")
    s += ar2((px["C"][0], yo), (ox, yo), "dim")
    s += txt((px["C"][0] + ox) / 2, yo - 7,
             "OC = (σx + σy)/2 = −57,50", "val")

    # дуга 2α от радиуса CX до радиуса CP
    rr = 62
    a0 = math.degrees(math.atan2(-t_, -(sx_ - c_pl)))
    a1 = math.degrees(math.atan2(-t_tnu, -(s_nu - c_pl)))
    s += (f'<path d="M {X(c_pl) + rr * math.cos(math.radians(a0)):.1f} '
          f'{oy + rr * math.sin(math.radians(a0)):.1f} A {rr} {rr} 0 0 0 '
          f'{X(c_pl) + rr * math.cos(math.radians(a1)):.1f} '
          f'{oy + rr * math.sin(math.radians(a1)):.1f}" class="arc"/>\n')
    s += txt(X(c_pl) - 30, oy + 118, "2α = 30°", "ang")

    for k in px:
        s += f'<circle cx="{px[k][0]:.1f}" cy="{px[k][1]:.1f}" r="3.6" class="dot"/>\n'

    lb = [("D", 0, 22, "D:  σx = −85", "middle"),
          ("B", -14, 22, "B:  σy = −30", "end"),
          ("C", 0, -44, "C", "middle"),
          ("s2", -11, -10, "σ₂ = −98,20", "end"),
          ("s1", 10, -26, "σ₁ = −16,80", "start"),
          ("t1", 0, -14, "τ₁ = +40,70   (σ′ = OC = −57,50)", "middle"),
          ("t2", 26, -12, "τ₂ = −40,70", "start"),
          ("X", -12, 6, "X (σx; τxy) — площадка x", "end"),
          ("K", 14, 6, "K (σy; τxy)", "start"),
          ("P", -12, 22, "P (σν; τtν) при α = 15°", "end")]
    for k, dx, dy, text, anc in lb:
        s += txt(px[k][0] + dx, px[k][1] + dy, text, "val", anc)
    s += txt((px["C"][0] + px["K"][0]) / 2 + 12,
             (px["C"][1] + px["K"][1]) / 2 + 16, "R = 40,70", "val", "start")
    s += '</svg>\n'
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
