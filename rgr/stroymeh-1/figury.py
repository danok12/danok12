# -*- coding: utf-8 -*-
"""Сборка рисунков с эпюрами: отдельный рисунок на каждую эпюру.

Раньше M, Q и N стояли тремя панелями в ряд — на листе A4 каждая выходила
шириной в палец, и ординаты было не прочитать. Теперь каждая эпюра —
самостоятельный рисунок во всю ширину полосы.
"""
from fractions import Fraction as F
from sistemy import ALL
from epury import Panel, skeleton, diagram, labels, txt

HEAD = ('<svg viewBox="0 0 {w} {h}" role="img" aria-label="{alt}" '
        'xmlns="http://www.w3.org/2000/svg">\n')
W = 760                        # ширина рисунка, единицы viewBox
AMP = 62                       # наибольшая ордината, единицы viewBox
KINDS = [("m", 2, "M, кН·м"), ("q", 1, "Q, кН"), ("n", 0, "N, кН")]


def extent(s):
    xs = [float(p[0]) for p in s.nodes.values()]
    ys = [float(p[1]) for p in s.nodes.values()]
    return min(xs), max(xs), min(ys), max(ys)


def razmah(s, kind):
    """Наибольшая по модулю ордината эпюры — 0, если эпюра нулевая."""
    best = 0.0
    for mem, _, _ in s.members:
        for i in range(21):
            best = max(best, abs(float(s.internal(mem, F(i, 20))[kind])))
    return best


def risunok(s, kind, name):
    """Один рисунок: скелет системы и эпюра на нём."""
    x0, x1, y0, y1 = extent(s)
    wm, hm = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    pad = AMP + 34                       # поле под ординаты и подписи
    sg = min((W - 2 * pad) / wm, 46)     # масштаб, пикселей на метр
    H = hm * sg + 2 * pad
    ox = W / 2 - wm * sg / 2 - x0 * sg
    oy = pad + hm * sg + y0 * sg
    pan = Panel(ox, oy, sg)
    sc = AMP / razmah(s, kind)
    out = HEAD.format(w=round(W), h=round(H), alt=f"{s.name}: эпюра {kind}")
    out += diagram(s, pan, kind, sc)
    out += skeleton(s, pan)
    out += labels(s, pan, kind, sc)
    out += '</svg>\n'
    open(name, "w", encoding="utf-8").write(out)
    return name


def nulevaya(s, kind):
    """Эпюра тождественно нулевая — рисовать нечего."""
    return razmah(s, kind) <= 1e-12


if __name__ == "__main__":
    for i, f in enumerate(ALL, 1):
        s = f(); s.solve()
        for suff, kind, title in KINDS:
            if nulevaya(s, kind):
                print(f"схема {i}: эпюра {title} нулевая — рисунок не нужен")
                continue
            print("записано", risunok(s, kind, f"epury-{i}-{suff}.svg"))
