# -*- coding: utf-8 -*-
"""Схемы к РГР по теме 9.

Плоские схемы задачи 2 (рис. 2.1, 2.2) — оси как в тетради: x вправо, y вниз,
угол α отсчитывается от оси x вверх.
Пространственные схемы задачи 1 (рис. 1.1-1.5) — аксонометрия: z вверх,
x вправо, y на зрителя (влево-вниз), как на схеме элемента в тетради.

Цвета берутся из CSS-переменных страницы: SVG вставляется в HTML инлайном
и поэтому работает и в светлой, и в тёмной теме.
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
        '<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        '<path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker>\n'
        '<marker id="axm" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        '<path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker>\n</defs>\n')


def ln(p1, p2, cls):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}"/>\n')


def ar(p1, p2, cls, mid):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}" marker-end="url(#{mid})"/>\n')


def poly(pts, cls):
    return ('<polygon points="' +
            ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + f'" class="{cls}"/>\n')


def txt(x, y, s, cls="lbl", anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}">{s}</text>\n')


def num(v, n=2):
    return f"{v:.{n}f}".replace(".", ",").replace("-", "−")


# ------------------------------------------------- аксонометрия (3D → 2D)
KY, KYV = -0.62, 0.44          # орт оси y на экране
VIEW = (0.62, 1.0, 0.44)       # направление на зрителя


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


UNIT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
# грани куба: внешняя нормаль и четыре вершины в координатах (±1)
FACES = []
for ax in range(3):
    for sgn in (1, -1):
        n = [0, 0, 0]; n[ax] = sgn
        o1, o2 = [k for k in range(3) if k != ax]
        pts = []
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            v = [0, 0, 0]; v[ax] = sgn; v[o1] = a; v[o2] = b
            pts.append(tuple(v))
        FACES.append((tuple(n), pts))


def draw_box(iso, M, cls_vis, cls_hid=None, half=1.0):
    """Параллелепипед, заданный матрицей рёбер M (столбцы — направления)."""
    def P(v):
        return iso.p(mul(mv(M, v), half))
    s = ""
    if cls_hid:
        for n, pts in FACES:
            if not visible(mv(M, n)):
                for i in range(4):
                    s += ln(P(pts[i]), P(pts[(i + 1) % 4]), cls_hid)
    for n, pts in FACES:
        if visible(mv(M, n)):
            s += poly([P(q) for q in pts], cls_vis)
    return s


IDENT = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def face_center(M, n, half=1.0):
    return mul(mv(M, n), half)



def stress_arrow(iso, c, n, val, mid, cls="sig", near=0.10, far=1.20):
    """Стрелка нормального напряжения на грани.

    Растяжение (val > 0) — от грани наружу; сжатие (val < 0) — снаружи к грани.
    """
    p_near = iso.p(add(c, mul(n, near)))
    p_far = iso.p(add(c, mul(n, far)))
    return ar(p_near, p_far, cls, mid) if val > 0 else ar(p_far, p_near, cls, mid)



def lab(iso, c, n, dist):
    """Точка для подписи: от центра грани по экранному направлению нормали.

    Смещение считается в пикселях, а не в единицах модели: в аксонометрии
    нормаль, направленная на зрителя, проецируется коротко, и подпись
    иначе попадает на сам элемент.
    """
    p0, p1 = iso.p(c), iso.p(add(c, n))
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    return (p0[0] + dx / L * dist, p0[1] + dy / L * dist)


def axes2d(x0, y0, s, names=("x", "y", "z")):
    """Тройка осей в аксонометрии от фиксированной точки на листе."""
    out = ""
    for d, nm in zip(UNIT, names):
        p1 = (x0 + s * (d[0] + KY * d[1]), y0 + s * (KYV * d[1] - d[2]))
        out += ar((x0, y0), p1, "ax", "axm")
        p2 = (x0 + s * 1.28 * (d[0] + KY * d[1]), y0 + s * 1.28 * (KYV * d[1] - d[2]))
        out += txt(p2[0], p2[1] + 4, nm, "ax-lbl")
    return out


# ------------------------------------------------------------- рис. 1.1
def fig11():
    w, h, mid = 640, 470, "a11"
    iso = Iso(320, 222, 58)
    s = HEAD.format(w=w, h=h, mid=mid,
                    alt="Напряжения на гранях элементарного параллелепипеда")
    s += axes2d(74, 404, 38)
    s += draw_box(iso, IDENT, "elem", "hid")

    data = [((1, 0, 0), SX, "x", 88, [((0, 1, 0), TXY, "xy"), ((0, 0, 1), TZX, "xz")]),
            ((0, 1, 0), SY, "y", 112, [((1, 0, 0), TXY, "yx"), ((0, 0, 1), TYZ, "yz")]),
            ((0, 0, 1), SZ, "z", 80, [((1, 0, 0), TZX, "zx"), ((0, 1, 0), TYZ, "zy")])]
    for n, sv, sub, dlab, shears in data:
        c = face_center(IDENT, n)
        s += stress_arrow(iso, c, n, sv, mid)
        q = lab(iso, c, n, dlab)
        s += txt(q[0], q[1], f"σ<tspan class='sub'>{sub}</tspan>", "lbl")
        s += txt(q[0], q[1] + 16, num(sv, 0), "val")
        for d, tv, tsub in shears:
            dd = mul(d, 1 if tv > 0 else -1)
            s += ar(iso.p(add(c, mul(dd, -0.58))),
                    iso.p(add(c, mul(dd, 0.58))), "tau", mid)
            q = lab(iso, add(c, mul(dd, 0.58)), add(mul(dd, 0.5), n), 30)
            s += txt(q[0], q[1] + 4,
                     f"τ<tspan class='tau-sub'>{tsub}</tspan>", "tau-lbl")
    s += '</svg>\n'
    return s


# ------------------------------------------------------------- рис. 1.2
def fig12():
    w, h, mid = 640, 470, "a12"
    iso = Iso(320, 225, 58)
    s = HEAD.format(w=w, h=h, mid=mid, alt="Главный элемент и главные напряжения")
    s += axes2d(74, 404, 38)
    M = [[NU[1][0], NU[2][0], NU[3][0]],
         [NU[1][1], NU[2][1], NU[3][1]],
         [NU[1][2], NU[2][2], NU[3][2]]]
    s += draw_box(iso, M, "elem", "hid", half=0.95)
    for i, val in ((1, S1), (2, S2), (3, S3)):
        n = NU[i]
        c = mul(n, 0.95)
        s += stress_arrow(iso, c, n, val, mid, near=0.10, far=1.15)
        s += ln(iso.p(mul(n, -0.9)), iso.p(mul(n, 0.9)), "norm")
        q = lab(iso, c, n, 108)
        s += txt(q[0], q[1], f"σ<tspan class='sub'>{i}</tspan> "
                             f"(ν<tspan class='sub'>{i}</tspan>)", "lbl")
        s += txt(q[0], q[1] + 16, num(val) + " МПа", "val")
    s += '</svg>\n'
    return s


# ------------------------------------------------------------- рис. 1.3
def fig13():
    w, h, mid = 640, 470, "a13"
    iso = Iso(310, 215, 62)
    s = HEAD.format(w=w, h=h, mid=mid,
                    alt="Диагональная площадка с наибольшим касательным напряжением")
    s += axes2d(74, 404, 38, ("1", "2", "3"))
    s += draw_box(iso, IDENT, "elem-lite", "hid")
    # площадка, равнонаклонённая к направлениям 1 и 3: содержит ось 2
    quad = [(1, -1, -1), (1, 1, -1), (-1, 1, 1), (-1, -1, 1)]
    s += poly([iso.p(q) for q in quad], "plane")
    r2 = 1 / math.sqrt(2)
    nrm, tng = (r2, 0.0, r2), (r2, 0.0, -r2)
    for sgn in (1, -1):
        s += stress_arrow(iso, (0.0, 0.0, 0.0), mul(nrm, sgn), S31, mid,
                          near=0.35, far=1.75)
    for sgn in (1, -1):
        base = mul((0, 1, 0), sgn * 0.75)
        s += ar(iso.p(add(base, mul(tng, -sgn * 0.72))),
                iso.p(add(base, mul(tng, sgn * 0.72))), "tau", mid)
    # подписи — на фиксированных местах, с выносками
    pn = iso.p(mul(nrm, 1.75))
    s += ln((pn[0] + 10, pn[1] - 10), (470, 92), "leader")
    s += txt(474, 78, "σ<tspan class='sub'>31</tspan>", "lbl", "start")
    s += txt(474, 96, num(S31) + " МПа", "val", "start")
    pt = iso.p(add(mul((0, 1, 0), 0.75), mul(tng, 0.72)))
    s += ln((pt[0], pt[1] + 8), (206, 376), "leader")
    s += txt(202, 366, "τ<tspan class='tau-sub'>31</tspan>", "tau-lbl", "end")
    s += txt(202, 384, num(T31) + " МПа", "tau-val", "end")
    s += txt(310, 446, "площадка равнонаклонена к направлениям 1 и 3 "
                       "(под 45° к каждому)", "cap")
    s += '</svg>\n'
    return s


# ------------------------------------------------------------- рис. 1.4
def fig14():
    w, h, mid = 640, 470, "a14"
    iso = Iso(320, 210, 58)
    K = 420.0                      # условное увеличение деформаций
    s = HEAD.format(w=w, h=h, mid=mid, alt="Относительные линейные деформации")
    s += axes2d(74, 396, 38)
    s += draw_box(iso, IDENT, "elem-lite", "hid")
    D = [[1 + K * EX, 0, 0], [0, 1 + K * EY, 0], [0, 0, 1 + K * EZ]]
    s += draw_box(iso, D, "deformed")
    for n, val, sub, what, dlab in (((1, 0, 0), EX, "x", "укорочение", 86),
                                    ((0, 1, 0), EY, "y", "удлинение", 112),
                                    ((0, 0, 1), EZ, "z", "укорочение", 78)):
        c = face_center(IDENT, n)
        q = lab(iso, c, n, dlab)
        s += txt(q[0], q[1], f"ε<tspan class='sub'>{sub}</tspan>", "lbl")
        s += txt(q[0], q[1] + 16, num(val * 1e5) + "·10⁻⁵", "val")
        s += txt(q[0], q[1] + 31, what, "cap")
    s += txt(320, 446, "сплошной контур — до деформации, штриховой — после "
                       "(масштаб условный)", "cap")
    s += '</svg>\n'
    return s


# ------------------------------------------------------------- рис. 1.5
def fig15():
    """Угловые деформации: три куба, на каждом — сдвиг в своей плоскости.

    Сдвиг простой: рёбра одного направления наклоняются, второе остаётся
    на месте — как на плоских схемах. Выделенная грань каждого куба лежит
    в своей координатной плоскости:
      куб 1 — верхняя грань, плоскость xOy, угол между x и y -> γxy,
      куб 2 — правая грань,  плоскость yOz, угол между y и z -> γyz,
      куб 3 — передняя грань, плоскость zOx, угол между z и x -> γzx.
    """
    w, h, mid = 1020, 424, "a15"
    K = 240.0                      # условное увеличение углов
    s = HEAD.format(w=w, h=h, mid=mid,
                    alt="Угловые деформации: три куба со сдвигом в плоскостях "
                        "xOy, yOz и zOx")

    # (плоскость, γ, индекс, позиция сдвига в матрице, выделенная грань,
    #  вершина угла, направления рёбер угла)
    # плоскость, γ, индекс, недиагональный член сдвига, выделенная грань,
    # две оси этой грани
    panels = [
        ("xOy", GXY, "xy", (0, 1), (0, 0, 1), 0, 1, "x", "y"),
        ("yOz", GYZ, "yz", (1, 2), (1, 0, 0), 1, 2, "y", "z"),
        ("zOx", GZX, "zx", (2, 0), (0, 1, 0), 2, 0, "z", "x"),
    ]

    for p, (plane, g, sub, cell, fn, i1, i2, n1, n2) in enumerate(panels):
        # вершина угла — ближайший к зрителю угол выделенной грани,
        # стороны угла идут от неё внутрь грани
        def side(idx):
            sg = 1 if VIEW[idx] > 0 else -1
            v = [0, 0, 0]; v[idx] = sg
            return tuple(v)
        a1, a2 = side(i1), side(i2)
        corner = add(fn, a1, a2)
        e1, e2 = mul(a1, -1), mul(a2, -1)
        x0 = 14 + p * 334
        cx, cy = x0 + 176, 238
        iso = Iso(cx, cy, 57)
        if p:
            s += ln((x0 - 6, 22), (x0 - 6, 392), "sep")
        # заголовок панели
        s += txt(x0 + 168, 34, f"плоскость {plane}", "cap")
        s += txt(x0 + 168, 56,
                 f"γ<tspan class='sub'>{sub}</tspan> = "
                 f"{'+' if g > 0 else '−'}{num(abs(g) * 1e5)}·10⁻⁵", "lbl")
        s += txt(x0 + 168, 74,
                 "прямой угол " + ("уменьшился" if g > 0 else "увеличился"), "cap")
        # оси
        s += axes2d(x0 + 46, 368, 30)
        # недеформированный куб
        s += draw_box(iso, IDENT, "elem-lite", "hid")
        # простой сдвиг: один недиагональный член
        Fm = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        Fm[cell[0]][cell[1]] = K * g
        s += draw_box(iso, Fm, "deformed")
        # выделенная грань деформированного куба
        for n, pts in FACES:
            if n == fn:
                s += poly([iso.p(mv(Fm, q)) for q in pts], "face-hi")
        # исходный прямой угол — уголок на недеформированном кубе
        d = 0.30
        s += ('<polyline points="' + ' '.join(
            f'{q[0]:.1f},{q[1]:.1f}' for q in (
                iso.p(add(corner, mul(e1, d))),
                iso.p(add(corner, mul(e1, d), mul(e2, d))),
                iso.p(add(corner, mul(e2, d))))) +
            '" class="right-angle"/>\n')
        # изменившийся угол — дуга на деформированном кубе
        pc = iso.p(mv(Fm, corner))
        q1 = iso.p(mv(Fm, add(corner, mul(e1, 0.58))))
        q2 = iso.p(mv(Fm, add(corner, mul(e2, 0.58))))
        s += (f'<path d="M {q1[0]:.1f} {q1[1]:.1f} Q {pc[0]:.1f} {pc[1]:.1f} '
              f'{q2[0]:.1f} {q2[1]:.1f}" class="arc-def"/>\n')
        s += f'<circle cx="{pc[0]:.1f}" cy="{pc[1]:.1f}" r="3" class="vertex"/>\n'

    s += txt(510, 412, "сплошной контур — до деформации, штриховой — после; "
                       "закрашена грань, лежащая в рассматриваемой плоскости; "
                       "углы увеличены примерно в 240 раз", "cap")
    s += '</svg>\n'
    return s


# ------------------------------------------------------------- рис. 2.1
def fig21():
    w, h, mid = 460, 360, "a21"
    cx, cy, a = 235, 190, 66
    s = HEAD.format(w=w, h=h, mid=mid,
                    alt="Напряжения на гранях элемента при плоском состоянии")
    s += ar((46, 44), (126, 44), "ax", mid) + txt(133, 48, "x", "ax-lbl")
    s += ar((46, 44), (46, 124), "ax", mid) + txt(46, 140, "y", "ax-lbl")
    s += f'<circle cx="46" cy="44" r="2.5" class="dot"/>\n'
    s += (f'<rect x="{cx-a}" y="{cy-a}" width="{2*a}" height="{2*a}" class="elem"/>\n')
    s += ar((cx + a + 58, cy), (cx + a + 6, cy), "sig", mid)
    s += ar((cx - a - 58, cy), (cx - a - 6, cy), "sig", mid)
    s += txt(cx + a + 66, cy - 9, "σ<tspan class='sub'>x</tspan>", "lbl", "start")
    s += txt(cx + a + 66, cy + 12, "−85", "val", "start")
    s += ar((cx, cy - a - 52), (cx, cy - a - 6), "sig", mid)
    s += ar((cx, cy + a + 52), (cx, cy + a + 6), "sig", mid)
    s += txt(cx + 8, cy - a - 58, "σ<tspan class='sub'>y</tspan>", "lbl", "start")
    s += txt(cx + 42, cy - a - 58, "−30", "val", "start")
    s += ar((cx + a + 14, cy + 44), (cx + a + 14, cy - 44), "tau", mid)
    s += ar((cx - a - 14, cy - 44), (cx - a - 14, cy + 44), "tau", mid)
    s += ar((cx + 44, cy + a + 14), (cx - 44, cy + a + 14), "tau", mid)
    s += ar((cx - 44, cy - a - 14), (cx + 44, cy - a - 14), "tau", mid)
    s += txt(cx + a + 20, cy - 52, "τ<tspan class='tau-sub'>xy</tspan>", "tau-lbl", "start")
    s += txt(cx + a + 20, cy - 33, "−30", "tau-val", "start")
    s += txt(cx - a - 20, cy + a + 34, "τ<tspan class='tau-sub'>yx</tspan>", "tau-lbl", "end")
    s += '</svg>\n'
    return s


# ------------------------------------------------------------- рис. 2.2
def fig22():
    w, h, mid = 520, 400, "a22"
    cx, cy, a = 250, 200, 60
    s = HEAD.format(w=w, h=h, mid=mid, alt="Главные площадки и главные напряжения")

    def uv(deg):
        r = math.radians(deg)
        return math.cos(r), -math.sin(r)
    n2, n3 = uv(A2), uv(A3)
    s += ar((cx - 160, cy), (cx + 162, cy), "ax", mid) + txt(cx + 172, cy + 5, "x", "ax-lbl")
    s += ar((cx, cy), (cx, cy + 146), "ax", mid) + txt(cx - 14, cy + 150, "y", "ax-lbl")
    pts = []
    for q2, q3 in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        pts.append((cx + a * (q2 * n2[0] + q3 * n3[0]),
                    cy + a * (q2 * n2[1] + q3 * n3[1])))
    s += poly(pts, "elem")
    for n, val, name in ((n2, P2, "σ₂"), (n3, P3, "σ₃")):
        s += ln((cx - 118 * n[0], cy - 118 * n[1]),
                (cx + 118 * n[0], cy + 118 * n[1]), "norm")
        for sgn in (1, -1):
            fx, fy = cx + sgn * a * n[0], cy + sgn * a * n[1]
            s += ar((fx + sgn * 52 * n[0], fy + sgn * 52 * n[1]),
                    (fx + sgn * 7 * n[0], fy + sgn * 7 * n[1]), "sig", mid)
        lx, ly = cx + 152 * n[0], cy + 152 * n[1]
        s += txt(lx, ly, name, "lbl")
        s += txt(lx, ly + 18, num(val) + " МПа", "val")
    for deg, name, r, rl in ((A2, "α₂ = 66,26°", 96, 104),
                             (A3, "α₃ = −23,74°", 62, 120)):
        ex = cx + r * math.cos(math.radians(deg))
        ey = cy - r * math.sin(math.radians(deg))
        sweep = 1 if deg < 0 else 0
        s += (f'<path d="M {cx + r} {cy} A {r} {r} 0 0 {sweep} {ex:.1f} {ey:.1f}" '
              f'class="arc"/>\n')
        md = math.radians(deg / 2)
        s += txt(cx + rl * math.cos(md) + 6, cy - rl * math.sin(md) + 4,
                 name, "ang", "start")
    s += '</svg>\n'
    return s


if __name__ == "__main__":
    # контроль: что именно показывает рис. 1.5
    K = 240.0
    for nm, cell, i, j, g in (("xOy (γxy)", (0, 1), 0, 1, GXY),
                              ("yOz (γyz)", (1, 2), 1, 2, GYZ),
                              ("zOx (γzx)", (2, 0), 2, 0, GZX)):
        Fm = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
        Fm[cell[0]][cell[1]] = K * g
        a = mv(Fm, UNIT[i]); b = mv(Fm, UNIT[j])
        cosang = (sum(p * q for p, q in zip(a, b))
                  / math.sqrt(sum(p * p for p in a))
                  / math.sqrt(sum(q * q for q in b)))
        ang = math.degrees(math.acos(cosang))
        print(f"  {nm}: на рисунке угол {ang:6.2f}° "
              f"({'уменьшился' if ang < 90 else 'увеличился'} на {abs(ang-90):.2f}°), "
              f"γ = {g*1e5:+.2f}·10⁻⁵ -> "
              f"{'уменьшился' if g > 0 else 'увеличился'}  "
              f"{'ok' if (ang < 90) == (g > 0) else 'ЗНАК НЕ СОШЁЛСЯ'}")
    for name, fn in (("fig-1-1", fig11), ("fig-1-2", fig12), ("fig-1-3", fig13),
                     ("fig-1-4", fig14), ("fig-1-5", fig15),
                     ("fig-2-1", fig21), ("fig-2-2", fig22)):
        open(name + ".svg", "w", encoding="utf-8").write(fn())
    print("схемы собраны")
