# -*- coding: utf-8 -*-
"""Построение эпюр M, Q, N по результатам расчёта.

Эпюра строится выборкой: усилие считается в 41 точке каждого стержня,
поэтому парабола под распределённой нагрузкой получается сама собой,
без отдельной формулы для стрелки.

Правила откладывания:
  M — со стороны растянутого волокна, без знака;
  Q и N — со знаком, ординаты по нормали к стержню.
"""
import math
from fractions import Fraction as F
from sistemy import ALL
from ordinaty import fmt

NS = 40                      # число выборок на стержень
HATCH = 2                    # штрих через каждые HATCH выборок
OFF = 5                      # отступ подписи от кончика ординаты


def num(v):
    return fmt(v)


class Panel:
    def __init__(self, ox, oy, sg):
        self.ox, self.oy, self.sg = ox, oy, sg

    def P(self, pt):
        return (self.ox + float(pt[0]) * self.sg,
                self.oy - float(pt[1]) * self.sg)


def ln(p1, p2, cls):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" '
            f'y2="{p2[1]:.1f}" class="{cls}"/>\n')


def txt(x, y, s, cls="ep-lbl", anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}">{s}</text>\n')


def skeleton(s, pan):
    out = ""
    for mem, a, b in s.members:
        out += ln(pan.P(s.nodes[a]), pan.P(s.nodes[b]), "ep-axis")
    return out


def diagram(s, pan, kind, sc):
    """kind: 0 — N, 1 — Q, 2 — M.

    Эпюра штрихуется по нормали к стержню — как чертят от руки; сплошная
    заливка съедает ординаты и ось, поэтому здесь только штрихи и контур.
    """
    out = ""
    for mem, a, b in s.members:
        e = s.axis(mem)
        n = (-float(e[1]), float(e[0]))          # нормаль
        sign = -1.0 if kind == 2 else 1.0        # M — на растянутом волокне
        pts, base_pts, vals = [], [], []
        for i in range(NS + 1):
            t = F(i, NS)
            v = float(s.internal(mem, t)[kind])
            base = pan.P(s.point_on(mem, t))
            base_pts.append(base)
            pts.append((base[0] + sign * n[0] * v * sc,
                        base[1] - sign * n[1] * v * sc))
            vals.append(v)
        if max(abs(v) for v in vals) < 1e-12:
            continue
        for i in range(0, NS + 1, HATCH):        # штриховка
            if abs(vals[i]) > 1e-9:
                out += ln(base_pts[i], pts[i], "ep-hatch")
        out += ('<polyline points="' +
                ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) +
                '" class="ep-line"/>\n')
        p0 = pan.P(s.nodes[a]); p1 = pan.P(s.nodes[b])
        out += ln(p0, pts[0], "ep-line") + ln(p1, pts[-1], "ep-line")
    return out


def rect(x0, y0, x1, y1):
    return (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" '
            f'height="{y1 - y0:.1f}" class="ep-bg"/>\n')


def box(lx, ly, s, anchor):
    """Габарит подписи — оценка по числу знаков, шрифт моноширинных цифр."""
    w, h = 7.6 * len(s) + 5, 15.0
    x0 = lx - 2 if anchor == "start" else (
        lx - w + 2 if anchor == "end" else lx - w / 2)
    return (x0, ly - 12, x0 + w, ly + 3)


def hit(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def labels(s, pan, kind, sc):
    """Подписи характерных ординат.

    Подпись ставится за кончиком ординаты, по направлению от оси стержня
    наружу — так она не ложится на штриховку. Если она всё же налезает на
    соседнюю, её отодвигают дальше по тому же направлению. Под подписью —
    белая подложка, чтобы линии эпюры не перечёркивали цифры.

    Рядом стоящие одинаковые подписи (конец одного стержня и начало
    другого в том же узле) печатаются один раз.
    """
    out = ""
    placed, boxes = [], []
    for mem, a, b in s.members:
        e = s.axis(mem)
        n = (-float(e[1]), float(e[0]))
        sign = -1.0 if kind == 2 else 1.0
        marks = [F(0), F(1)]
        d = next((x for x in s.dists if x[0] == mem), None)
        if d is not None and kind == 2:
            # под распределённой нагрузкой эпюра M — парабола; её середину
            # подписываем всегда. Стрелка бывает меньше толщины линии
            # (на схеме 1 это 2 кН·м при наибольшей ординате 242), и тогда
            # кривизну видно только по числу.
            marks.append(F(1, 2))
        if d is not None:
            q0 = float(s.internal(mem, F(0))[1])
            q1 = float(s.internal(mem, F(1))[1])
            if q0 * q1 < 0:
                marks.append(F(q0).limit_denominator(10**6) /
                             (F(q0).limit_denominator(10**6) -
                              F(q1).limit_denominator(10**6)))
        for t in marks:
            v = float(s.internal(mem, t)[kind])
            if abs(v) < 1e-9:
                continue
            base = pan.P(s.point_on(mem, t))
            x = base[0] + sign * n[0] * v * sc
            y = base[1] - sign * n[1] * v * sc
            if any(abs(px - x) < 15 and abs(py - y) < 15 and abs(pv - v) < 1e-6
                   for px, py, pv in placed):
                continue
            placed.append((x, y, v))
            # единичный вектор от оси к кончику ординаты, в экранных осях
            dx, dy = x - base[0], y - base[1]
            h = math.hypot(dx, dy) or 1.0
            ux, uy = dx / h, dy / h
            if ux > .3:
                anchor = "start"
            elif ux < -.3:
                anchor = "end"
            else:
                anchor = "middle"
            nudge = 12 if uy > .3 else (-2 if uy < -.3 else 5)
            # на эпюре M знак не ставится — она и так со стороны
            # растянутого волокна; на Q и N знак нужен
            cap = num(abs(v) if kind == 2 else v).replace('-', '\u2212')
            for k in range(6):                      # развести столкновения
                off = OFF + 17 * k
                lx, ly = x + ux * off, y + uy * off + nudge
                bx = box(lx, ly, cap, anchor)
                if not any(hit(bx, o) for o in boxes):
                    break
            boxes.append(bx)
            out += rect(*bx) + txt(lx, ly, cap, "ep-lbl", anchor)
    return out
