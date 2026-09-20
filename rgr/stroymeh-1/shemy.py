# -*- coding: utf-8 -*-
"""Расчётные схемы задания 1 по строительной механике, вариант 2.

Схемы перечерчены со скана методички (МГСУ, «Расчёт статически определимых
стержневых систем», 2015, с. 6). Геометрия снята с оригинала по пикселям,
размеры подписаны так же, как в методичке (l, h, l/2, h/2).

Чертёж чёрно-белый, стили берутся из CSS страницы.
"""
import math

W = 2.6          # толщина стержня
R_H = 5.2        # радиус шарнира


def ln(p1, p2, cls="bar"):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}"/>\n')


def ar(p1, p2, cls="load", marker="ah"):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}" marker-end="url(#{marker})"/>\n')


def txt(x, y, s, cls="lbl", anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}">{s}</text>\n')


def sub(sym, idx):
    return f"{sym}<tspan class='sub'>{idx}</tspan>"


def hinge(p):
    return f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{R_H}" class="hinge"/>\n'


def cross(p, label=None, dx=0, dy=18):
    d = 5.5
    s = ln((p[0]-d, p[1]-d), (p[0]+d, p[1]+d), "mark")
    s += ln((p[0]-d, p[1]+d), (p[0]+d, p[1]-d), "mark")
    if label:
        s += txt(p[0] + dx, p[1] + dy, label, "lbl")
    return s


def hatch(p, length, angle=0, n=7, side=1):
    """Штриховка основания: линия + косые штрихи.

    angle = 0 — горизонтальная опорная поверхность (штрихи снизу),
    angle = 90 — вертикальная стенка (штрихи слева/справа по side).
    """
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)          # вдоль линии
    nx, ny = -uy * side, ux * side             # наружу (в материал)
    x0, y0 = p[0] - ux * length / 2, p[1] - uy * length / 2
    s = ln((x0, y0), (x0 + ux * length, y0 + uy * length), "hatch-line")
    for i in range(n):
        t = (i + 0.5) * length / n
        bx, by = x0 + ux * t, y0 + uy * t
        s += ln((bx, by), (bx + (nx - ux) * 7, by + (ny - uy) * 7), "hatch")
    return s


def link(p, dx, dy, ground_angle=None):
    """Опорный стержень: шарнир у конструкции, стержень, шарнир на основании."""
    q = (p[0] + dx, p[1] + dy)
    s = hinge(p) + ln(p, q, "bar-thin") + hinge(q)
    ang = ground_angle if ground_angle is not None else (0 if abs(dy) > abs(dx) else 90)
    side = 1 if (dy > 0 or dx > 0) else -1
    off = (0, R_H + 1) if ang == 0 else (R_H + 1, 0)
    s += hatch((q[0] + off[0] * (1 if dx >= 0 else -1) * (0 if ang == 0 else side),
                q[1] + (off[1] * side if ang == 0 else 0)), 30, ang,
               6, side)
    return s


def link_v(p, L=26):
    """Вертикальный опорный стержень (вниз)."""
    q = (p[0], p[1] + L)
    s = hinge(p) + ln(p, q, "bar-thin") + hinge(q)
    s += hatch((q[0], q[1] + R_H + 1), 34, 0, 7, 1)
    return s


def link_h(p, L=26, d=1):
    """Горизонтальный опорный стержень (d = +1 вправо, −1 влево)."""
    q = (p[0] + d * L, p[1])
    s = hinge(p) + ln(p, q, "bar-thin") + hinge(q)
    s += hatch((q[0] + d * (R_H + 1), q[1]), 34, 90, 7, d)
    return s


def pin2(p, L=24, d=1):
    """Неподвижная опора двумя стержнями: вертикальный + горизонтальный."""
    return link_v(p, L) + link_h(p, L, d)


def fixed(p, angle=0, length=44, side=1):
    """Заделка: штриховка прямо по торцу стержня."""
    return hatch(p, length, angle, 9, side)


def qload(p1, p2, offset, n=6, label="q", lab_off=(0, -14)):
    """Распределённая нагрузка: внешняя линия и стрелки к стержню.

    offset — вектор от стержня к внешней линии (куда «отложена» нагрузка).
    """
    ox, oy = offset
    a = (p1[0] + ox, p1[1] + oy)
    b = (p2[0] + ox, p2[1] + oy)
    s = ln(a, b, "q-line")
    for i in range(n + 1):
        t = i / n
        s0 = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        s1 = (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)
        s += ar(s0, s1, "q-arrow", "ahs")
    mx, my = (a[0] + b[0]) / 2 + lab_off[0], (a[1] + b[1]) / 2 + lab_off[1]
    s += txt(mx, my, label, "lbl")
    return s


def force(tip, dx, dy, label="F", lab=(0, 0), length=46):
    """Сосредоточенная сила: жирная стрелка остриём в точку приложения."""
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    start = (tip[0] - ux * length, tip[1] - uy * length)
    s = ar(start, tip, "force")
    s += txt(start[0] - ux * 12 + lab[0], start[1] - uy * 12 + lab[1] + 5,
             label, "lbl")
    return s


def moment(p, label="m", r=16, ccw=True, gap=90, lab=(0, 0), span=285):
    """Сосредоточенный момент — дуга со стрелкой.

    ccw=True  — против часовой стрелки на листе;
    ccw=False — по часовой.
    gap — куда смотрит разрыв дуги, в экранных градусах
          (0 вправо, 90 вниз, 180 влево, 270 вверх).

    В экранных координатах ось y направлена вниз, поэтому рост угла —
    это движение по часовой стрелке, а флаг sweep=1 в SVG означает
    «в сторону роста угла». Отсюда: по часовой — sweep=1, против — 0.
    """
    half = (360 - span) / 2
    if ccw:
        a0, a1, sweep = gap - half, gap - half - span, 0
    else:
        a0, a1, sweep = gap + half, gap + half + span, 1
    x0 = p[0] + r * math.cos(math.radians(a0))
    y0 = p[1] + r * math.sin(math.radians(a0))
    x1 = p[0] + r * math.cos(math.radians(a1))
    y1 = p[1] + r * math.sin(math.radians(a1))
    large = 1 if span > 180 else 0
    s = (f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} {sweep} '
         f'{x1:.1f} {y1:.1f}" class="moment" marker-end="url(#ah)"/>\n')
    if label:
        s += txt(p[0] + lab[0], p[1] + lab[1], label, "lbl")
    return s


def dim(p1, p2, label, off=0, vertical=False):
    """Размерная линия с засечками."""
    if vertical:
        x = p1[0] + off
        s = ""
        s += (f'<line x1="{x:.1f}" y1="{p1[1]:.1f}" x2="{x:.1f}" '
              f'y2="{p2[1]:.1f}" class="dim" marker-start="url(#ahs)" '
              f'marker-end="url(#ahs)"/>\n')
        for yy in (p1[1], p2[1]):
            s += ln((x - 5, yy), (x + 5, yy), "dim")
        s += txt(x + 13, (p1[1] + p2[1]) / 2 + 5, label, "dim-lbl", "start")
    else:
        y = p1[1] + off
        s = ln((p1[0], p1[1] + 6), (p1[0], y + 7), "ext")
        s += ln((p2[0], p2[1] + 6), (p2[0], y + 7), "ext")
        s += (f'<line x1="{p1[0]:.1f}" y1="{y:.1f}" x2="{p2[0]:.1f}" '
              f'y2="{y:.1f}" class="dim" marker-start="url(#ahs)" '
              f'marker-end="url(#ahs)"/>\n')
        s += txt((p1[0] + p2[0]) / 2, y - 7, label, "dim-lbl")
    return s


HEAD = ('<svg viewBox="0 0 {w} {h}" role="img" aria-label="{alt}" '
        'xmlns="http://www.w3.org/2000/svg">\n<defs>\n'
        '<marker id="ah" viewBox="0 0 10 10" refX="9.4" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0.5 L10 5 L0 9.5 z" fill="context-stroke"/></marker>\n'
        '<marker id="ahs" viewBox="0 0 10 10" refX="9.4" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        '<path d="M0 1 L10 5 L0 9 z" fill="context-stroke"/></marker>\n'
        '</defs>\n')


# ===================================================== схема 1
def shema1():
    w, h = 600, 470
    L, H = 118, 104
    x0, xa = 96, 214            # стена и ось стойки
    yt = 74                     # верх стойки
    yb, yk = yt + H, yt + 2 * H
    s = HEAD.format(w=w, h=h, alt="Схема 1: рама, защемлённая в стене")
    # стержни
    s += ln((x0, yt), (xa, yt)) + ln((xa, yt), (xa, yk))
    s += ln((xa, yb), (xa + L, yb))
    s += fixed((x0, yt), 90, 52, -1)
    # нагрузки
    s += qload((xa, yt), (xa, yb), (46, 0), 5, "q", (16, 4))
    s += force((xa + L, yb), 0, -1, "F", (14, 0))
    s += moment((xa, yk), "m", 16, True, 270, (28, 22))
    s += cross((xa, yk))
    s += txt(xa - 14, yk - 6, "K", "lbl", "end")
    # размеры
    s += dim((x0, yk), (xa, yk), "l", 78)
    s += dim((xa, yk), (xa + L, yk), "l", 78)
    s += dim((xa, yt), (xa, yb), "h", 226, True)
    s += dim((xa, yb), (xa, yk), "h", 226, True)
    s += txt(112, 250, "Δ<tspan class='sub'>kp</tspan> — ?", "lbl", "start")
    s += '</svg>\n'
    return s


# ===================================================== схема 2
def shema2():
    w, h = 620, 330
    xl, xm, xr = 96, 268, 440
    yt, yb = 86, 86 + 140
    s = HEAD.format(w=w, h=h, alt="Схема 2: рама на трёх опорных стержнях")
    s += ln((xl, yt), (xr, yt))
    s += ln((xl, yt), (xl, yb)) + ln((xm, yt), (xm, yb))
    s += qload((xl, yt), (xm, yt), (0, -34), 5, "q", (0, -8))
    s += force((xl, yt + 70), 1, 0, "F", (0, -6))
    s += moment((xm + (xr - xm) / 2, yt), "m", 16, False, 90, (0, -30))
    s += link_v((xl, yb))
    s += link_h((xm, yb), 26, 1)
    s += link_h((xr, yt), 26, 1)
    s += dim((xl, yt), (xl, yt + 70), "h/2", 402, True)
    s += dim((xl, yt + 70), (xl, yb), "h/2", 402, True)
    s += dim((xl, yb), (xm, yb), "l", 62)
    s += dim((xm, yb), (xr, yt), "l", 62)
    s += '</svg>\n'
    return s


# ===================================================== схема 3
def shema3():
    w, h = 560, 500
    xl, xr = 128, 330
    yk, ym, yb = 72, 72 + 148, 72 + 296
    s = HEAD.format(w=w, h=h, alt="Схема 3: рама с шарниром в узле ригеля")
    s += ln((xl, yk), (xl, yb)) + ln((xl, ym), (xr, ym)) + ln((xr, ym), (xr, yb))
    s += qload((xl, ym), (xr, ym), (0, -34), 6, "q", (0, -8))
    s += force((xl, yk), 1, 0, "F", (0, -6))
    s += moment((xr, ym), "m", 16, False, 200, (26, -4))
    s += cross((xl, yk))
    s += txt(xl + 14, yk - 8, "K", "lbl", "start")
    s += pin2((xl, yb), 24, -1)
    s += pin2((xr, yb), 24, 1)
    s += dim((xr, yk), (xr, ym), "h", 118, True)
    s += dim((xr, ym), (xr, yb), "h", 118, True)
    s += dim((xl, yb), (xr, yb), "l", 76)
    s += txt(176, 116, "φ<tspan class='sub'>kp</tspan> — ?", "lbl", "start")
    s += '</svg>\n'
    return s


# ===================================================== схема 4
def shema4():
    w, h = 640, 420
    xs, xc, xr = 100, 268, 436
    yt, yb = 150, 150 + 140
    s = HEAD.format(w=w, h=h, alt="Схема 4: рама с шарниром и защемлённой стойкой")
    s += ln((xs, yb), (xc, yb)) + ln((xc, yb), (xc, yt))
    s += ln((xc, yt), (xr, yt)) + ln((xr, yt), (xr, yb))
    s += hinge((xc, yt))
    s += qload((xr, yt), (xr, yb), (42, 0), 5, "q", (16, 4))
    s += force((xc, yb), -1, 0, "F", (0, -14), 44)
    s += moment((xr, yt), "m", 16, True, 200, (26, -6))
    s += cross(((xs + xc) / 2, yb))
    s += txt((xs + xc) / 2, yb + 24, "K", "lbl")
    s += link_v((xs, yb))
    s += fixed((xr, yb), 0, 46, 1)
    s += dim((xs, yb), (xc, yb), "l", 66)
    s += dim((xc, yb), (xr, yb), "l", 66)
    s += dim((xr, yt), (xr, yb), "h", 104, True)
    s += txt(300, 200, "Δ<tspan class='sup'>верт</tspan>"
                       "<tspan class='sub'>K</tspan> — ?", "lbl", "start")
    s += '</svg>\n'
    return s


# ===================================================== схема 5
def shema5():
    w, h = 900, 250
    x0, u = 70, 116                      # начало и длина l
    y = 104
    xs = [x0, x0 + u, x0 + 2 * u]        # заделка, шарнир 1, шарнир 2
    half = u / 2
    xs += [xs[2] + half * k for k in (1, 2, 3, 4, 5)]
    s = HEAD.format(w=w, h=h, alt="Схема 5: многопролётная балка")
    s += ln((x0, y), (xs[-1], y))
    s += fixed((x0, y), 90, 46, -1)
    s += hinge((xs[1], y)) + hinge((xs[2], y))
    s += qload((x0, y), (xs[2], y), (0, -30), 8, "q", (0, -8))
    s += link_v((xs[3], y), 24)
    s += link_v((xs[5], y), 24)
    s += force((xs[4], y), 0, 1, "F", (12, 0), 48)
    s += moment((xs[-1], y), "m", 16, False, 180, (26, -14))
    s += dim((x0, y), (xs[1], y), "l", 96)
    s += dim((xs[1], y), (xs[2], y), "l", 96)
    for i in (2, 3, 4, 5, 6):
        s += dim((xs[i], y), (xs[i + 1], y), "l/2", 96)
    s += '</svg>\n'
    return s


# ===================================================== схема 1 с реакциями
def shema1_reakcii():
    """Та же схема 1, но с найденными опорными реакциями в заделке."""
    w, h = 660, 470
    L, H = 118, 104
    x0, xa = 150, 268
    yt = 74
    yb, yk = yt + H, yt + 2 * H
    s = HEAD.format(w=w, h=h, alt="Схема 1: опорные реакции в заделке")
    s += ln((x0, yt), (xa, yt)) + ln((xa, yt), (xa, yk))
    s += ln((xa, yb), (xa + L, yb))
    s += fixed((x0, yt), 90, 52, -1)
    s += qload((xa, yt), (xa, yb), (46, 0), 5, "q = 1 кН/м", (54, 4))
    s += force((xa + L, yb), 0, -1, "F = 20 кН", (44, 0))
    s += moment((xa, yk), "m = 10 кН·м", 16, True, 270, (74, 24))
    s += cross((xa, yk))
    s += txt(xa - 14, yk - 6, "K", "lbl", "end")
    # реакции
    s += force((x0 + 26, yt), 1, 0, "", (0, 0), 40)
    s += txt(x0 + 34, yt - 10, "R<tspan class='sub'>Ax</tspan> = 4 кН", "lbl", "start")
    s += force((x0 + 12, yt + 54), 0, 1, "", (0, 0), 44)
    s += txt(x0 + 20, yt + 52, "R<tspan class='sub'>Ay</tspan> = 20 кН", "lbl", "start")
    s += moment((x0 - 30, yt + 72), "", 19, False, 90)
    s += txt(x0 - 30, yt + 112, "M<tspan class='sub'>A</tspan> = 242 кН·м", "lbl")
    s += txt(x0 - 16, yt - 14, "A", "lbl", "end")
    s += dim((x0, yk), (xa, yk), "l = 6 м", 78)
    s += dim((xa, yk), (xa + L, yk), "l = 6 м", 78)
    s += dim((xa, yt), (xa, yb), "h = 4 м", 226, True)
    s += dim((xa, yb), (xa, yk), "h = 4 м", 226, True)
    s += '</svg>\n'
    return s


if __name__ == "__main__":
    for name, fn in (("shema-1", shema1), ("shema-2", shema2),
                     ("shema-3", shema3), ("shema-4", shema4),
                     ("shema-5", shema5),
                     ("shema-1-reakcii", shema1_reakcii)):
        open(name + ".svg", "w", encoding="utf-8").write(fn())
        print("записано", name + ".svg")
