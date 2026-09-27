"""Чертежи для решения по трёхшарнирной раме-ферме (все в масштабе сетки d = l/6)."""
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from chertezh import *  # noqa: E402,F403
from rama import NODES, MEMBERS  # noqa: E402

TENS, COMP = "#b3402d", "#1f5fa8"

LEFT_NODES = {"1", "2", "3", "4", "1′", "2′", "3′", "4′", "D", "E", "A", "C"}
RIGHT_NODES = {"C", "6", "7", "8", "9", "6′", "7′", "8′", "9′", "F", "G", "B"}


def draw_frame(g, T, members=MEMBERS, col=INK, w=1.9, nodes=None, dots=True):
    for a, b in members:
        g.line(*T(*NODES[a]), *T(*NODES[b]), col, w)
    if dots:
        for n in (nodes or NODES):
            if n not in ("A", "B", "C"):
                g.dot(*T(*NODES[n]), 2.4)


def loads_on(g, T, which=("2", "1′", "4′", "7", "9′", "F"), k_label="3P", values=False):
    lab = {"2": "P", "1′": "P", "4′": k_label, "7": "2P", "9′": "P", "F": "P/2"}
    val = {"2": "P = 14 кН", "1′": "P = 14 кН", "4′": f"{k_label} = 42 кН", "7": "2P = 28 кН",
           "9′": "P = 14 кН", "F": "P/2 = 7 кН"}
    for n in which:
        x, y = T(*NODES[n])
        t = val[n] if values else lab[n]
        if n in ("2", "7"):
            g.arrow(x, y - 60, x, y - 5, "load", 2)
            g.text(x + 7, y - 46, t, LOAD, 13.5, "start", "700")
        elif n in ("1′", "4′"):
            g.arrow(x, y + 4, x, y + 62, "load", 2)
            g.text(x + (-8 if n == "1′" else 8), y + 50, t, LOAD, 13.5, "end" if n == "1′" else "start", "700")
        else:
            g.arrow(x + 4, y, x + 60, y, "load", 2)
            g.text(x + 34, y - 8, t, LOAD, 13.5, "middle", "700")


def fig_scheme(k_label="3P", sid="r1"):
    """Рис. 1 — расчётная схема по карточке."""
    g = Svg(sid, 780, 430)
    s, ox, oy = 66, 140, 318
    T = lambda x, y: (ox + s * float(x), oy - s * float(y))
    draw_frame(g, T)
    g.support(*T(0, 0))
    g.support(*T(6, 0))
    g.hinge(*T(3, 3), 5.2)
    loads_on(g, T, k_label=k_label)
    xa, ya = T(0, 0)
    xb, yb = T(6, 0)
    g.text(xa - 26, ya + 14, "A", INK, 14, "end", "700")
    g.text(xb + 26, yb + 14, "B", INK, 14, "start", "700")
    g.text(T(3, 3)[0], T(3, 3)[1] - 11, "C", INK, 14, "middle", "700")
    yd = oy + 50
    for i in range(-1, 8):
        y0 = T(i, 2)[1] + 70 if i == -1 else (T(i, 2)[1] + 8 if i == 7 else oy + 30)
        g.line(T(i, 0)[0], y0, T(i, 0)[0], yd + 6, DIM, 0.7, "3 3" if i in (-1, 7) else None)
    for i in range(-1, 7):
        g.dim_h(T(i, 0)[0], T(i + 1, 0)[0], yd, "d", 12)
    g.line(xa, yd + 6, xa, yd + 30, DIM, 0.7)
    g.line(xb, yd + 6, xb, yd + 30, DIM, 0.7)
    g.dim_h(xa, xb, yd + 24, "l = 6d = 44 м")
    xv = T(7, 0)[0] + 92
    for j in range(3):
        g.dim_v(xv, T(0, j + 1)[1], T(0, j)[1], "d", side=+1, size=12)
    g.ext(T(7, 3)[0] + 6, T(0, 3)[1], xv + 40, T(0, 3)[1])
    g.ext(xb + 26, oy, xv + 40, oy)
    for j in (1, 2):
        g.ext(xv - 6, T(0, j)[1], xv + 6, T(0, j)[1])
    g.dim_v(xv + 34, T(0, 3)[1], oy, "3d = l/2 = 22 м", side=+1, size=12)
    return g.svg("Расчётная схема трёхшарнирной рамы-фермы")


LABEL_OFF = {   # смещение подписи узла (dx, dy, anchor)
    "1": (0, -10, "middle"), "2": (0, -10, "middle"), "3": (0, -10, "middle"), "4": (0, -10, "middle"),
    "6": (0, -10, "middle"), "7": (0, -10, "middle"), "8": (0, -10, "middle"), "9": (0, -10, "middle"),
    "1′": (-7, 17, "end"), "2′": (-7, 17, "end"), "3′": (7, 17, "start"), "4′": (0, 19, "middle"),
    "6′": (0, 19, "middle"), "7′": (-7, 17, "end"), "8′": (7, 17, "start"), "9′": (7, 17, "start"),
    "D": (-8, 5, "end"), "E": (9, 5, "start"), "F": (8, 5, "start"), "G": (-9, 5, "end"),
}


def fig_numbering(sid="r2"):
    """Рис. 2 — нумерация узлов."""
    g = Svg(sid, 780, 330)
    s, ox, oy = 72, 160, 270
    T = lambda x, y: (ox + s * float(x), oy - s * float(y))
    draw_frame(g, T, w=1.6)
    g.support(*T(0, 0))
    g.support(*T(6, 0))
    g.hinge(*T(3, 3), 5.2)
    for n, (dx, dy, anc) in LABEL_OFF.items():
        x, y = T(*NODES[n])
        g.text(x + dx, y + dy, n, INT, 14, anc, "700")
    g.text(T(3, 3)[0], T(3, 3)[1] - 11, "C", INT, 14, "middle", "700")
    g.text(T(0, 0)[0] - 26, T(0, 0)[1] + 14, "A", INT, 14, "end", "700")
    g.text(T(6, 0)[0] + 26, T(6, 0)[1] + 14, "B", INT, 14, "start", "700")
    # угол α у наклонного стержня левой ноги
    x0, y0 = T(0, 0)
    g.arc(x0, y0, 34, 0, math.degrees(math.atan(2)), "ink", 1.0, head=False)
    g.ext(x0 + 4, y0, x0 + 46, y0)
    g.text(x0 + 40, y0 - 16, "α", INK, 13, "start", italic=True)
    return g.svg("Нумерация узлов")


def fig_whole(values, sid):
    """Рис. 3 / итог — рама без опор, с реакциями."""
    g = Svg(sid, 780, 440)
    s, ox, oy = 64, 150, 318
    T = lambda x, y: (ox + s * float(x), oy - s * float(y))
    draw_frame(g, T)
    for n in ("A", "B", "C"):
        g.hinge(*T(*NODES[n]), 5)
    loads_on(g, T, values=values)
    xa, ya = T(0, 0)
    xb, yb = T(6, 0)
    va = "V_{A} = 57,17 кН" if values else "V_{A}"
    ha = "H_{A} = 10,5 кН" if values else "H_{A}"
    vb = "V_{B} = 40,83 кН" if values else "V_{B}"
    hb = "H_{B} = 31,5 кН" if values else "H_{B}"
    g.arrow(xa, ya + 62, xa, ya + 6, "reac", 2.2)
    g.text(xa + 8, ya + 58, va, REAC, 13.5, "start", "700")
    g.arrow(xa - 66, ya, xa - 6, ya, "reac", 2.2)
    g.text(xa - 10, ya - 10, ha, REAC, 13.5, "end", "700")
    g.arrow(xb, yb + 62, xb, yb + 6, "reac", 2.2)
    g.text(xb - 8, yb + 58, vb, REAC, 13.5, "end", "700")
    g.arrow(xb + 66, yb, xb + 6, yb, "reac", 2.2)
    g.text(xb + 10, yb + 18, hb, REAC, 13.5, "start", "700")
    g.text(xa - 10, ya + 18, "A", INK, 14, "end", "700")
    g.text(xb + 10, yb - 8, "B", INK, 14, "start", "700")
    g.text(T(3, 3)[0], T(3, 3)[1] - 11, "C", INK, 14, "middle", "700")
    yd = oy + 88
    for i in range(-1, 8):
        y0 = T(i, 2)[1] + 70 if i == -1 else (T(i, 2)[1] + 8 if i == 7 else (oy + 66 if i in (0, 6) else oy + 8))
        g.line(T(i, 0)[0], y0, T(i, 0)[0], yd + 6, DIM, 0.7, None if i in (0, 6) else "3 3")
    for i in range(-1, 7):
        g.dim_h(T(i, 0)[0], T(i + 1, 0)[0], yd, "d", 12)
    xv = T(7, 0)[0] + 96
    for j in range(3):
        g.dim_v(xv, T(0, j + 1)[1], T(0, j)[1], "d", side=+1, size=12)
    g.ext(T(7, 3)[0] + 6, T(0, 3)[1], xv + 6, T(0, 3)[1])
    g.ext(T(7, 2)[0] + 66, T(0, 2)[1], xv + 6, T(0, 2)[1])
    g.ext(xb + 70, oy, xv + 6, oy)
    g.ext(T(6, 1)[0] + 66, T(0, 1)[1], xv + 6, T(0, 1)[1])
    return g.svg("Рама с опорными реакциями")


def fig_halves(sid="r4"):
    """Рис. 4 — полурамы для ΣM_C."""
    g = Svg(sid, 800, 400)
    s, oy = 56, 300
    oxl, oxr = 120, 190
    TL = lambda x, y: (oxl + s * float(x), oy - s * float(y))
    TR = lambda x, y: (oxr + s * float(x), oy - s * float(y))
    lm = [m for m in MEMBERS if m[0] in LEFT_NODES and m[1] in LEFT_NODES]
    rm = [m for m in MEMBERS if m[0] in RIGHT_NODES and m[1] in RIGHT_NODES]
    draw_frame(g, TL, lm, nodes=LEFT_NODES)
    draw_frame(g, TR, rm, nodes=RIGHT_NODES)
    for p in (TL(0, 0), TL(3, 3), TR(3, 3), TR(6, 0)):
        g.hinge(*p, 5)
    loads_on(g, TL, ("2", "1′", "4′"))
    loads_on(g, TR, ("7", "9′", "F"))
    xa, ya = TL(0, 0)
    xb, yb = TR(6, 0)
    g.arrow(xa, ya + 56, xa, ya + 6, "reac", 2.2)
    g.text(xa + 8, ya + 52, "V_{A}", REAC, 14, "start", "700")
    g.arrow(xa - 56, ya, xa - 6, ya, "reac", 2.2)
    g.text(xa - 10, ya - 10, "H_{A}", REAC, 14, "end", "700")
    g.arrow(xb, yb + 56, xb, yb + 6, "reac", 2.2)
    g.text(xb - 8, yb + 52, "V_{B}", REAC, 14, "end", "700")
    g.arrow(xb + 56, yb, xb + 6, yb, "reac", 2.2)
    g.text(xb + 10, yb - 10, "H_{B}", REAC, 14, "start", "700")
    cl, cr = TL(3, 3), TR(3, 3)
    g.arrow(cl[0] + 5, cl[1], cl[0] + 30, cl[1], "gray", 1.5, "4 3")
    g.text(cl[0] + 12, cl[1] + 18, "X_{C}", GRAY, 13, "start")
    g.arrow(cl[0], cl[1] - 5, cl[0], cl[1] - 32, "gray", 1.5, "4 3")
    g.text(cl[0] + 6, cl[1] - 24, "Y_{C}", GRAY, 13, "start")
    g.arrow(cr[0] - 5, cr[1], cr[0] - 30, cr[1], "gray", 1.5, "4 3")
    g.text(cr[0] - 10, cr[1] + 18, "X_{C}", GRAY, 13, "end")
    g.arrow(cr[0], cr[1] + 5, cr[0], cr[1] + 32, "gray", 1.5, "4 3")
    g.text(cr[0] - 6, cr[1] + 36, "Y_{C}", GRAY, 13, "end")
    g.text(cl[0] - 10, cl[1] - 8, "C", INK, 14, "end", "700")
    g.text(cr[0] + 8, cr[1] - 8, "C", INK, 14, "start", "700")
    g.text(xa - 10, ya + 18, "A", INK, 14, "end", "700")
    g.text(xb + 10, yb + 18, "B", INK, 14, "start", "700")
    # размеры: плечи относительно C
    yd = oy + 76
    for i in (-1, 0, 2, 3):
        y0 = TL(i, 2)[1] + 70 if i == -1 else (oy + 62 if i == 0 else TL(i, 2)[1] + (70 if i == 2 else 6))
        g.line(TL(i, 0)[0], y0, TL(i, 0)[0], yd + 6, DIM, 0.7, None if i == 0 else "3 3")
    g.dim_h(TL(-1, 0)[0], TL(0, 0)[0], yd, "d", 12)
    g.dim_h(TL(0, 0)[0], TL(2, 0)[0], yd, "2d", 12)
    g.dim_h(TL(2, 0)[0], TL(3, 0)[0], yd, "d", 12)
    for i in (3, 5, 6):
        y0 = TR(i, 2)[1] + 6 if i == 3 else (TR(i, 3)[1] + 6 if i == 5 else oy + 62)
        g.line(TR(i, 0)[0], y0, TR(i, 0)[0], yd + 6, DIM, 0.7, None if i == 6 else "3 3")
    g.dim_h(TR(3, 0)[0], TR(5, 0)[0], yd, "2d", 12)
    g.dim_h(TR(5, 0)[0], TR(6, 0)[0], yd, "d", 12)
    xv = TR(7, 0)[0] + 84
    g.ext(TR(3, 3)[0] + 8, TR(0, 3)[1], xv + 6, TR(0, 3)[1])
    g.ext(TR(7, 2)[0] + 64, TR(0, 2)[1], xv + 6, TR(0, 2)[1])
    g.ext(TR(6, 1)[0] + 64, TR(0, 1)[1], xv + 6, TR(0, 1)[1])
    g.ext(xb + 60, oy, xv + 6, oy)
    for j in range(3):
        g.dim_v(xv, TR(0, j + 1)[1], TR(0, j)[1], "d", side=+1, size=12)
    xl = TL(-1, 0)[0] - 36
    g.ext(TL(-1, 3)[0] - 6, TL(0, 3)[1], xl - 6, TL(0, 3)[1])
    g.ext(xa - 62, oy, xl - 6, oy)
    g.dim_v(xl, TL(0, 3)[1], oy, "3d", size=12)
    g.text(TL(1, 0)[0], 18, "левая полурама A…C", GRAY, 12.5, "middle")
    g.text(TR(5, 0)[0], 18, "правая полурама C…B", GRAY, 12.5, "middle")
    return g.svg("Полурамы для уравнений моментов относительно шарнира C")


def fig_node(n, unknown, ext, sid):
    """Мини-схема узла: все стержни — растяжение (от узла), неизвестные выделены."""
    g = Svg(sid, 240, 200)
    cx, cy, L = 120, 100, 50
    for m in MEMBERS:
        if n not in m:
            continue
        o = m[1] if m[0] == n else m[0]
        dx = float(NODES[o][0] - NODES[n][0])
        dy = float(NODES[o][1] - NODES[n][1])
        r = math.hypot(dx, dy)
        ux, uy = dx / r, -dy / r
        g.line(cx + ux * 5, cy + uy * 5, cx + ux * (L - 2), cy + uy * (L - 2), "#d6e2e4", 6)
        kind = "int" if m in unknown else "gray"
        g.arrow(cx + ux * 5, cy + uy * 5, cx + ux * L, cy + uy * L, kind, 2.2 if m in unknown else 1.6)
        tx, ty = cx + ux * (L + 12), cy + uy * (L + 12) + 5
        anc = "start" if ux > 0.3 else ("end" if ux < -0.3 else "middle")
        if anc == "middle":
            ty += 8 if uy > 0 else -6
        col = INT if m in unknown else GRAY
        g.text(tx, ty, f"N_{{{m[0]}–{m[1]}}}", col, 13, anc, "700" if m in unknown else "normal")
    for sym, ax, sg, lab in ext:
        if ax == 1 and sg < 0 and n in ("2", "7"):
            g.arrow(cx, cy - 58, cx, cy - 6, "load", 2)
            g.text(cx + 7, cy - 44, lab, LOAD, 13, "start", "700")
        elif ax == 1 and sg < 0:
            g.arrow(cx, cy + 6, cx, cy + 58, "load", 2)
            g.text(cx + 7, cy + 52, lab, LOAD, 13, "start", "700")
        elif ax == 0 and sg > 0 and sym.startswith("H"):
            g.arrow(cx - 58, cy, cx - 6, cy, "reac", 2)
            g.text(cx - 58, cy - 8, lab, REAC, 13, "start", "700")
        elif ax == 0 and sg < 0:
            g.arrow(cx + 58, cy, cx + 6, cy, "reac", 2)
            g.text(cx + 58, cy - 8, lab, REAC, 13, "end", "700")
        elif ax == 1 and sg > 0:
            g.arrow(cx, cy + 58, cx, cy + 6, "reac", 2)
            g.text(cx + 7, cy + 52, lab, REAC, 13, "start", "700")
        else:
            g.arrow(cx + 6, cy, cx + 58, cy, "load", 2)
            g.text(cx + 34, cy - 8, lab, LOAD, 13, "middle", "700")
    g.add(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{INK}"/>')
    g.text(14, 20, f"узел {n}", INK, 14, "start", "700")
    return g.svg(f"Узел {n}")


def fig_ritter(sid="r5"):
    """Рис. 5 — сечение через панель 3–4, левая часть."""
    g = Svg(sid, 740, 480)
    s, ox, oy = 88, 200, 360
    T = lambda x, y: (ox + s * float(x), oy - s * float(y))
    part = {"1", "2", "3", "1′", "2′", "3′", "D", "E", "A"}
    ms = [m for m in MEMBERS if m[0] in part and m[1] in part]
    draw_frame(g, T, ms, nodes=part)
    g.hinge(*T(0, 0), 5)
    xs = T(1.72, 0)[0]
    g.line(xs, T(0, 3.3)[1], xs, T(0, 1.5)[1], GRAY, 1.2, "7 4")
    g.text(xs, T(0, 1.5)[1] + 16, "сечение", GRAY, 12, "middle")
    x3, y3 = T(1, 3)
    x3p, y3p = T(1, 2)
    x4p, y4p = T(2, 2)
    # усилия в разрезанных стержнях (растяжение — от левой части)
    g.arrow(x3 + 5, y3, x3 + 58, y3, "int", 2.4)
    g.text(x3 + 62, y3 + 5, "N_{3–4}", INT, 14, "start", "700")
    k = 0.7071
    g.arrow(x3 + 5 * k, y3 + 5 * k, x3 + 50 * k, y3 + 50 * k, "int", 2.4)
    g.text(x3 + 50 * k + 8, y3 + 50 * k + 4, "N_{3–4′}", INT, 14, "start", "700")
    g.arrow(x3p + 5, y3p, x3p + 50, y3p, "int", 2.4)
    g.text(x3p + 6, y3p - 9, "N_{3′–4′}", INT, 14, "start", "700")
    # моментные точки
    g.add(f'<circle cx="{x3:.1f}" cy="{y3:.1f}" r="8" fill="none" stroke="{LOAD}" stroke-width="1.6"/>')
    g.add(f'<circle cx="{x4p:.1f}" cy="{y4p:.1f}" r="8" fill="none" stroke="{LOAD}" stroke-width="1.6"/>')
    g.dot(x4p, y4p, 2.6, LOAD)
    g.text(x3 + 14, y3 - 16, "моментная точка для N_{3′–4′}", LOAD, 12, "start")
    g.text(x4p + 14, y4p + 4, "4′ — моментная точка для N_{3–4}", LOAD, 12, "start")
    loads_on(g, T, ("2", "1′"))
    xa, ya = T(0, 0)
    g.arrow(xa, ya + 58, xa, ya + 6, "reac", 2.2)
    g.text(xa + 8, ya + 52, "V_{A} = 57,167 кН", REAC, 13.5, "start", "700")
    g.arrow(xa - 62, ya, xa - 6, ya, "reac", 2.2)
    g.text(xa - 10, ya - 10, "H_{A} = 10,5 кН", REAC, 13.5, "end", "700")
    for n in ("1", "2", "3", "1′", "2′", "3′", "D", "E"):
        dx, dy, anc = LABEL_OFF[n]
        if n in ("2", "3"):
            dx, dy, anc = (-8, -8, "end")
        x, y = T(*NODES[n])
        g.text(x + dx, y + dy, n, INK, 12.5, anc, "700")
    g.text(xa - 10, ya + 18, "A", INK, 13, "end", "700")
    # размеры
    xv = T(-1, 0)[0] - 44
    for j in range(3):
        g.dim_v(xv, T(0, j + 1)[1], T(0, j)[1], "d", size=12)
    g.ext(xv - 6, T(0, 3)[1], T(-1, 3)[0] - 6, T(0, 3)[1])
    g.ext(xv - 6, T(0, 2)[1], T(-1, 2)[0] - 6, T(0, 2)[1])
    g.ext(xv - 6, T(0, 1)[1], T(0, 1)[0] - 8, T(0, 1)[1])
    g.ext(xv - 6, oy, xa - 70, oy)
    yd = oy + 84
    for xx in (-1, 0, 1, 2):
        y0 = T(xx, 2)[1] + (70 if xx == -1 else 12) if xx != 0 else oy + 64
        g.line(T(xx, 0)[0], y0, T(xx, 0)[0], yd + 6, DIM, 0.7, None if xx == 0 else "3 3")
    for xx in (-1, 0, 1):
        g.dim_h(T(xx, 0)[0], T(xx + 1, 0)[0], yd, "d", 12)
    return g.svg("Сечение через панель 3–4")


def fig_forces(N, sid="r6"):
    """Итоговая схема усилий: растяжение — красный, сжатие — синий, ноль — пунктир."""
    g = Svg(sid, 800, 360)
    s, ox, oy = 86, 118, 300
    T = lambda x, y: (ox + s * float(x), oy - s * float(y))
    for m in MEMBERS:
        v = N[m]
        a, b = T(*NODES[m[0]]), T(*NODES[m[1]])
        if abs(v) < 5e-4:
            g.line(*a, *b, GRAY, 1.2, "4 3")
        else:
            g.line(*a, *b, TENS if v > 0 else COMP, 2.6)
    for n in ("A", "B", "C"):
        g.hinge(*T(*NODES[n]), 5)

    def lab(m, x, y, anc="middle", rot=None):
        v = N[m]
        t = "0" if abs(v) < 5e-4 else f"{v:+.2f}".replace("-", "−").replace(".", ",")
        col = GRAY if abs(v) < 5e-4 else (TENS if v > 0 else COMP)
        g.text(x, y, t, col, 11.5, anc, "700", rot=rot)

    for m in MEMBERS:
        (x1, y1), (x2, y2) = NODES[m[0]], NODES[m[1]]
        mx, my = T((x1 + x2) / 2, (y1 + y2) / 2)
        if y1 == y2 == 3:
            lab(m, mx, my - 6)
        elif y1 == y2 == 2:
            lab(m, mx, my - 5)
        elif x1 == x2 and min(y1, y2) >= 2:
            lab(m, mx - 5, my, "middle", -90)
        elif min(y1, y2) >= 2:
            lab(m, mx, my + 4)
        elif x1 == x2:                      # стойки ног
            side = -1 if x1 == 0 else 1
            lab(m, mx + side * 8, my + 4, "end" if side < 0 else "start")
        elif y1 == y2:                      # распорки
            lab(m, mx, my + 15)
        else:                               # наклонные и раскосы ног
            (xa, ya), (xb, yb) = (x1, y1), (x2, y2)
            left = (xa + xb) / 2 < 3
            steep = abs(float(xb - xa)) == 0.5 and abs(float(yb - ya)) == 1
            if m in (("2′", "E"), ("8′", "G")):
                lab(m, mx + (6 if left else -6), my - 8, "start" if left else "end")
            elif steep:
                lab(m, mx + (10 if left else -10), my + 8, "start" if left else "end")
            else:
                lab(m, mx, my + 4)
    g.text(T(0, 0)[0] - 10, T(0, 0)[1] + 18, "A", INK, 13, "end", "700")
    g.text(T(6, 0)[0] + 10, T(6, 0)[1] + 18, "B", INK, 13, "start", "700")
    g.text(T(3, 3)[0], T(3, 3)[1] - 11, "C", INK, 13, "middle", "700")
    # легенда
    lx, ly = 250, 336
    for i, (c, t, dash) in enumerate(((TENS, "растяжение (+)", None), (COMP, "сжатие (−)", None), (GRAY, "нулевой стержень", "4 3"))):
        x = lx + i * 170
        g.line(x, ly, x + 34, ly, c, 2.6 if dash is None else 1.2, dash)
        g.text(x + 42, ly + 4, t, INK, 12.5, "start")
    return g.svg("Усилия во всех стержнях")
