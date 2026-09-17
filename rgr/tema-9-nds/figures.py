# -*- coding: utf-8 -*-
"""Генерация схем к задаче 2 (рис. 2.1 и 2.2).

Ориентация осей — как в тетради: x вправо, y вниз, угол α отсчитывается
от оси x против часовой стрелки (вверх на листе).
Цвета берутся из CSS-переменных страницы, поэтому SVG вставляется в HTML
инлайном и работает в обеих темах.
"""
import math

SX, SY, TXY = -85.0, -30.0, -30.0
S2, A2 = -16.8029, 66.26      # МПа, град
S3, A3 = -98.1971, -23.74

HEAD = ('<svg viewBox="0 0 {w} {h}" role="img" aria-label="{alt}" '
        'xmlns="http://www.w3.org/2000/svg">\n'
        '<defs>\n'
        '<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        '<path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/></marker>\n'
        '</defs>\n')


def arrow(x1, y1, x2, y2, cls, mid):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'class="{cls}" marker-end="url(#{mid})"/>\n')


def txt(x, y, s, cls="lbl", anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}">{s}</text>\n')


# ----------------------------------------------------------------- рис. 2.1
def fig21():
    w, h, mid = 460, 360, "ah1"
    cx, cy, a = 235, 190, 66
    s = HEAD.format(w=w, h=h, mid=mid,
                    alt="Напряжения на гранях элемента: sigma x, sigma y, tau xy")
    # оси
    s += arrow(46, 44, 126, 44, "ax", mid) + txt(133, 48, "x", "ax-lbl")
    s += arrow(46, 44, 46, 124, "ax", mid) + txt(46, 140, "y", "ax-lbl")
    s += f'<circle cx="46" cy="44" r="2.5" class="dot"/>\n'
    # элемент
    s += (f'<rect x="{cx-a}" y="{cy-a}" width="{2*a}" height="{2*a}" '
          f'class="elem"/>\n')
    # sigma_x < 0 -> стрелки внутрь, к граням
    s += arrow(cx + a + 58, cy, cx + a + 6, cy, "sig", mid)
    s += arrow(cx - a - 58, cy, cx - a - 6, cy, "sig", mid)
    s += txt(cx + a + 66, cy - 9, "σ", "lbl", "start") + \
         txt(cx + a + 75, cy - 5, "x", "sub", "start") + \
         txt(cx + a + 66, cy + 12, "−85", "val", "start")
    # sigma_y < 0 -> стрелки внутрь
    s += arrow(cx, cy - a - 52, cx, cy - a - 6, "sig", mid)
    s += arrow(cx, cy + a + 52, cx, cy + a + 6, "sig", mid)
    s += txt(cx + 8, cy - a - 58, "σ", "lbl", "start") + \
         txt(cx + 17, cy - a - 54, "y", "sub", "start") + \
         txt(cx + 46, cy - a - 58, "−30", "val", "start")
    # tau_xy < 0: на грани +x стрелка вверх, на грани −x вниз,
    #             на грани +y (нижней) влево, на грани −y (верхней) вправо
    s += arrow(cx + a + 14, cy + 44, cx + a + 14, cy - 44, "tau", mid)
    s += arrow(cx - a - 14, cy - 44, cx - a - 14, cy + 44, "tau", mid)
    s += arrow(cx + 44, cy + a + 14, cx - 44, cy + a + 14, "tau", mid)
    s += arrow(cx - 44, cy - a - 14, cx + 44, cy - a - 14, "tau", mid)
    s += txt(cx + a + 20, cy - 52, "τ", "tau-lbl", "start") + \
         txt(cx + a + 28, cy - 48, "xy", "tau-sub", "start") + \
         txt(cx + a + 20, cy - 33, "−30", "tau-val", "start")
    s += txt(cx - a - 20, cy + a + 34, "τ", "tau-lbl", "end") + \
         txt(cx - a - 12, cy + a + 38, "yx", "tau-sub", "end")
    s += '</svg>\n'
    return s


# ----------------------------------------------------------------- рис. 2.2
def fig22():
    """Главный элемент — построение как «Рисунок 2» в тетради:
    ось x через центр, две главные нормали, дуги отсчитываемых от x углов."""
    w, h, mid = 520, 400, "ah2"
    cx, cy, a = 250, 200, 60
    s = HEAD.format(w=w, h=h, mid=mid,
                    alt="Главные площадки и главные напряжения sigma 2 и sigma 3")

    def uv(deg):
        r = math.radians(deg)
        return math.cos(r), -math.sin(r)
    n2, n3 = uv(A2), uv(A3)

    # оси через центр элемента
    s += arrow(cx - 160, cy, cx + 162, cy, "ax", mid) + txt(cx + 172, cy + 5, "x", "ax-lbl")
    s += arrow(cx, cy, cx, cy + 146, "ax", mid) + txt(cx - 14, cy + 150, "y", "ax-lbl")

    # главный элемент
    pts = []
    for s2, s3 in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        pts.append((cx + a * (s2 * n2[0] + s3 * n3[0]),
                    cy + a * (s2 * n2[1] + s3 * n3[1])))
    s += ('<polygon points="' +
          ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + '" class="elem"/>\n')

    # нормали (штриховые линии на всю ширину элемента) и напряжения
    for n, val, name in ((n2, S2, "σ₂"), (n3, S3, "σ₃")):
        s += (f'<line x1="{cx - 118 * n[0]:.1f}" y1="{cy - 118 * n[1]:.1f}" '
              f'x2="{cx + 118 * n[0]:.1f}" y2="{cy + 118 * n[1]:.1f}" class="norm"/>\n')
        for sgn in (1, -1):
            fx, fy = cx + sgn * a * n[0], cy + sgn * a * n[1]
            s += arrow(fx + sgn * 52 * n[0], fy + sgn * 52 * n[1],
                       fx + sgn * 7 * n[0], fy + sgn * 7 * n[1], "sig", mid)
        lx, ly = cx + 152 * n[0], cy + 152 * n[1]
        s += txt(lx, ly, name, "lbl")
        s += txt(lx, ly + 18, f"{val:.2f}".replace(".", ",").replace("-", "−") + " МПа", "val")

    # дуги углов от оси x
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


open("fig-2-1.svg", "w", encoding="utf-8").write(fig21())
open("fig-2-2.svg", "w", encoding="utf-8").write(fig22())
print("готово:", len(fig21()), len(fig22()))
