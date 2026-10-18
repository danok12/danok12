# -*- coding: utf-8 -*-
"""Рисунок «перемножение эпюр по участкам» для схемы 1 (Δ_K горизонтальное).

Каждый участок развёрнут горизонтально: слева грузовая эпюра M_P, справа
единичная M₁, между ними «×», в конце — результат. По Верещагину отмечены
центр тяжести площади M₁ и ордината y_c эпюры M_P под ним; по Симпсону —
ординаты по концам и посередине. Отдельной строкой — как получена ордината
параболы посередине: хорда + ql²/8 (как на паре).
"""
from fractions import Fraction as F

HEAD = ('<svg viewBox="0 0 {w} {h}" role="img" aria-label="{alt}" '
        'xmlns="http://www.w3.org/2000/svg">\n')
LW, AMPL = 220, 46          # длина развёрнутого участка и наибольшая ордината, единиц


def num(v):
    v = F(v).limit_denominator(1000)
    if v.denominator == 1:
        return str(v.numerator)
    return f"{float(v):.2f}".replace(".", ",")


def ln(a, b, cls):
    return f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" class="{cls}"/>\n'


def tx(x, y, s, cls="ep-lbl", anchor="middle"):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}">{s}</text>\n'


def epura(x0, y0, f, vmax, ends, mids=()):
    """Эпюра на развёрнутом участке: f(t) — ордината (t = 0..1), вверх."""
    k = AMPL / vmax
    out, pts = "", []
    for i in range(0, 41):
        t = F(i, 40)
        v = float(f(t))
        x = x0 + LW * float(t)
        pts.append((x, y0 - v * k))
        if i % 2 == 0 and abs(v) > 1e-9:
            out += ln((x, y0), (x, y0 - v * k), "ep-hatch")
    out += '<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '" class="ep-line"/>\n'
    out += ln((x0, y0), (x0 + LW, y0), "ep-axis")
    out += tx(x0 - 4, y0 + 18, ends[0], "ep-kl", "start") + tx(x0 + LW + 4, y0 + 18, ends[1], "ep-kl", "end")
    for t, lab in mids:
        x = x0 + LW * float(t)
        out += tx(x, y0 - float(f(t)) * k - 6, lab, "ep-lbl")
    return out, k


def ryad(y0, title, P, U, ends, sposob, itog):
    """P, U — (функция, наибольшая по модулю ордината) для M_P и M₁."""
    xa, xb = 70, 400
    out = tx(10, y0 - 100, title, "lbl-b", "start")
    (fp, mp), (fu, mu) = P, U
    if sposob[0] == "в":                       # Верещагин: площадь M₁ × y_c(M_P)
        tc, Om = sposob[1], sposob[2]
        a, kp = epura(xa, y0, fp, mp, ends, [(0, num(fp(0))), (1, num(fp(1)))])
        b, ku = epura(xb, y0, fu, mu, ends, [(0, num(fu(0))), (1, num(fu(1)))])
        out += a + b
        xc_u, xc_p = xb + LW * float(tc), xa + LW * float(tc)
        yc_u = y0 - float(fu(tc)) * ku / 2.6
        out += f'<circle cx="{xc_u:.1f}" cy="{yc_u:.1f}" r="3.6" fill="#000"/>\n'
        out += tx(xc_u, y0 + 34, f"Ω₁ = {Om}", "val") + tx(xc_u, y0 + 52, "ц. т.", "note")
        out += ln((xc_p, y0), (xc_p, y0 - float(fp(tc)) * kp), "pair")
        out += tx(xc_p, y0 + 34, f"y<tspan class='sub'>c</tspan> = {num(fp(tc))}", "val")
    else:                                       # Симпсон: концы и середина
        a, _ = epura(xa, y0, fp, mp, ends, [(0, "a = " + num(fp(0))), (F(1, 2), "m = " + num(fp(F(1, 2)))),
                                            (1, "b = " + num(fp(1)))])
        b, _ = epura(xb, y0, fu, mu, ends, [(0, "c = " + num(fu(0))), (F(1, 2), "n = " + num(fu(F(1, 2)))),
                                            (1, "d = " + num(fu(1)))])
        out += a + b
        for x0 in (xa, xb):
            out += ln((x0 + LW / 2, y0), (x0 + LW / 2, y0 - 8), "ep-axis")
    out += tx(xa + LW / 2, y0 - AMPL - 26, "M<tspan class='sub'>P</tspan>", "ep-kl")
    out += tx(xb + LW / 2, y0 - AMPL - 26, "M₁", "ep-kl")
    out += tx((xa + LW + xb) / 2, y0 - 16, "×", "lbl-b")
    out += tx(xb + LW + 24, y0 - 16, "= " + itog, "lbl-b", "start")
    return out


def figura():
    w, h = 760, 720
    s = HEAD.format(w=w, h=h, alt="Схема 1: перемножение эпюр по участкам")
    # A–B: M_P 242 → 122 (линейно), M₁ = 8; Верещагин, ц. т. прямоугольника посередине
    s += ryad(150, "A–B (l = 6):  M₁ — прямоугольник, M<tspan class='sub'>P</tspan> — трапеция; по Верещагину",
              (lambda t: 242 - 120 * t, 242), (lambda t: F(8), 8), ("A", "B"),
              ("в", F(1, 2), "8·6 = 48"), "48·182 = 8736")
    # B–C: M_P парабола 122 → 130, посередине 128; M₁ 8 → 4; Симпсон
    s += ryad(355, "B–C (l = 4):  M<tspan class='sub'>P</tspan> — парабола от q; по Симпсону",
              (lambda t: 122 + 8 * t + 8 * t * (1 - t), 130), (lambda t: 8 - 4 * t, 8), ("B", "C"),
              ("с",), "3045,33")
    # C–K: M_P = 10, M₁ 4 → 0 (треугольник, ц. т. в 1/3 от C)
    s += ryad(560, "C–K (l = 4):  M₁ — треугольник, M<tspan class='sub'>P</tspan> = const; по Верещагину",
              (lambda t: F(10), 10), (lambda t: 4 - 4 * t, 4), ("C", "K"),
              ("в", F(1, 3), "½·4·4 = 8"), "8·10 = 80")
    s += tx(10, 680, "Все ординаты обеих эпюр на этих участках — с одной стороны стержня: "
                     "произведения со знаком «+».", "note", "start")
    s += '</svg>\n'
    return s


def parabola():
    """B–C: M_P = трапеция (хорда) + парабола со стрелкой ql²/8."""
    w, h = 760, 210
    s = HEAD.format(w=w, h=h, alt="Схема 1: эпюра M_P на B–C — хорда плюс парабола")
    y0 = 140
    a, _ = epura(20, y0, lambda t: 122 + 8 * t + 8 * t * (1 - t), 130, ("B", "C"),
                 [(0, "122"), (F(1, 2), "128"), (1, "130")])
    b, _ = epura(280, y0, lambda t: 122 + 8 * t, 130, ("B", "C"),
                 [(0, "122"), (F(1, 2), "126"), (1, "130")])
    s += a + b
    k = 7.0                                      # парабола отдельно, увеличена
    pts = [(540 + LW * i / 40, y0 - k * 8 * (i / 40) * (1 - i / 40)) for i in range(41)]
    s += '<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '" class="ep-line"/>\n'
    s += ln((540, y0), (540 + LW, y0), "ep-axis") + tx(540 + LW / 2, y0 - 2 * k - 8, "ql²/8 = 2", "ep-lbl")
    s += tx(250, y0 - 30, "=", "lbl-b") + tx(510, y0 - 30, "+", "lbl-b")
    s += tx(130, 26, "M<tspan class='sub'>P</tspan> на B–C", "ep-kl")
    s += tx(390, 26, "хорда (трапеция)", "ep-kl") + tx(650, 26, "парабола от q", "ep-kl")
    s += tx(10, 196, "посередине:  (122 + 130)/2 + q·h²/8 = 126 + 1·4²/8 = 126 + 2 = 128", "val", "start")
    s += '</svg>\n'
    return s


if __name__ == "__main__":
    # проверка: подписи на рисунке совпадают с расчётом
    from sistemy import shema1
    from peremeshcheniya import s1p, g1
    for mem, t, v in (('AB', F(1, 2), 182), ('BC', F(1, 2), 128), ('BC', 0, 122), ('BC', 1, 130),
                      ('CK', 0, 10)):
        assert s1p.internal(mem, F(t))[2] == v, (mem, t)
    for mem, t, v in (('AB', 0, 8), ('BC', 0, 8), ('BC', 1, 4), ('CK', 0, 4), ('CK', 1, 0)):
        assert g1.internal(mem, F(t))[2] == v, (mem, t)
    assert F(4, 6) * (122 * 8 + 4 * 128 * 6 + 130 * 4) == F(9136, 3)
    open("ed-1-pere.svg", "w", encoding="utf-8").write(figura())
    open("ed-1-parab.svg", "w", encoding="utf-8").write(parabola())
    print("записано: ed-1-pere.svg, ed-1-parab.svg")


# ===================== участки в настоящем положении — видно, с какой стороны эпюры
def panel(p0, ds, Lpx, f, vmax, amp, kon, podpisi=(), metka=None, pometka=None):
    """Участок стержня с эпюрой на его настоящей стороне.

    p0 — начало (экран), ds — орт направления (экран), f(t) — ордината со знаком
    решателя: «+» — волокно справа от направления стержня. Справа от направления
    в экранных осях — вектор (−ds_y, ds_x).
    """
    nx, ny = -ds[1], ds[0]
    k = amp / vmax
    P = lambda t, v=0.0: (p0[0] + ds[0] * Lpx * t + nx * v * k, p0[1] + ds[1] * Lpx * t + ny * v * k)
    out, pts = "", []
    for i in range(41):
        t = i / 40
        v = float(f(F(i, 40)))
        pts.append(P(t, v))
        if i % 2 == 0 and abs(v) > 1e-9:
            out += ln(P(t), P(t, v), "ep-hatch")
    out += '<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '" class="ep-line"/>\n'
    out += ln(P(0), P(1), "ep-axis")
    # буквы концов — с той стороны стержня, где эпюры нет
    glav = max((float(f(F(i, 8))) for i in range(9)), key=abs)
    zn = 1 if glav >= 0 else -1
    for t, nm in ((0, kon[0]), (1, kon[1])):
        x, y = P(t)
        out += tx(x - zn * nx * 14 + ds[0] * (8 if t == 0 else -8),
                  y - zn * ny * 14 + ds[1] * (12 if t == 0 else -4) + 5, nm, "ep-kl")
    for t, lab in podpisi:
        v = float(f(F(t)))
        x, y = P(float(t), v)
        sgn = 1 if v >= 0 else -1
        out += tx(x + nx * 8 * sgn + (6 if nx * sgn > 0 else (-6 if nx * sgn < 0 else 0)),
                  y + ny * 8 * sgn + (12 if ny * sgn > 0 else (-4 if ny * sgn < 0 else 4)), lab,
                  "ep-lbl", "start" if nx * sgn > .5 else ("end" if nx * sgn < -.5 else "middle"))
    if metka is not None:                      # центр тяжести площади
        t, _ = metka
        v = float(f(F(t)))
        x, y = P(float(t), v / 2.6)
        out += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#000"/>\n'
    if pometka is not None:                    # ордината y_c под центром тяжести
        t = pometka
        out += ln(P(float(t)), P(float(t), float(f(F(t)))), "pair")
    return out


def stroka(x, y, s, cls="val"):
    return tx(x, y, s, cls, "start")


def figura_storony():
    """Горизонтальное перемещение K: три участка, у каждого M_P и M₁."""
    w, h = 760, 820
    s = HEAD.format(w=w, h=h, alt="Схема 1: перемножение эпюр по участкам, стороны эпюр")
    # ---- A–B: горизонтально, обе эпюры снизу
    s += tx(10, 26, "A–B (l = 6):  обе эпюры снизу — растянуто нижнее волокно  →  знак «+»", "lbl-b", "start")
    s += tx(150, 56, "M<tspan class='sub'>P</tspan>", "ep-kl") + tx(530, 56, "M₁", "ep-kl")
    s += panel((40, 70), (1, 0), 220, lambda t: 242 - 120 * t, 242, 70, ("A", "B"),
               [(0, "242"), (1, "122"), (F(1, 2), "y<tspan class='sub'>c</tspan> = 182")], pometka=F(1, 2))
    s += panel((420, 70), (1, 0), 220, lambda t: F(8), 8, 50, ("A", "B"),
               [(0, "8"), (1, "8")], metka=(F(1, 2), ""))
    s += tx(310, 110, "×", "lbl-b")
    s += stroka(420, 165, "ц. т. прямоугольника — посередине, 3 м от A;  Ω₁ = 8·6 = 48")
    s += stroka(40, 190, "y<tspan class='sub'>c</tspan> = 242 − (242 − 122)·3/6 = 182")
    s += tx(10, 222, "48 · 182 = +8736", "lbl-b", "start")
    # ---- B–C и C–K: вертикально (сверху вниз), обе эпюры слева
    s += tx(10, 268, "B–C (l = 4) и C–K (l = 4):  обе эпюры слева от стойки — растянуто левое волокно  →  «+»",
            "lbl-b", "start")
    top, Lv = 320, 170
    s += tx(125, 300, "M<tspan class='sub'>P</tspan> на B–C", "ep-kl") + tx(330, 300, "M₁ на B–C", "ep-kl")
    s += panel((170, top), (0, 1), Lv, lambda t: 122 + 8 * t + 8 * t * (1 - t), 130, 80, ("B", "C"),
               [(0, "a = 122"), (F(1, 2), "m = 128"), (1, "b = 130")])
    s += panel((370, top), (0, 1), Lv, lambda t: 8 - 4 * t, 8, 70, ("B", "C"),
               [(0, "c = 8"), (F(1, 2), "n = 6"), (1, "d = 4")])
    s += tx(240, top + Lv / 2, "×", "lbl-b")
    s += tx(505, 300, "M<tspan class='sub'>P</tspan> на C–K", "ep-kl") + tx(665, 300, "M₁ на C–K", "ep-kl")
    s += panel((560, top), (0, 1), Lv, lambda t: F(10), 10, 40, ("C", "K"),
               [(0, "10"), (1, "10"), (F(1, 3), "y<tspan class='sub'>c</tspan> = 10")], pometka=F(1, 3))
    s += panel((730, top), (0, 1), Lv, lambda t: 4 - 4 * t, 4, 70, ("C", "K"),
               [(0, "4"), (1, "0")], metka=(F(1, 3), ""))
    s += tx(645, top + Lv / 2, "×", "lbl-b")
    y = top + Lv + 50
    s += stroka(20, y, "B–C: M<tspan class='sub'>P</tspan> — парабола, поэтому Симпсон:")
    s += stroka(20, y + 22, "l/6·(a·c + 4·m·n + b·d) = 4/6·(122·8 + 4·128·6 + 130·4)")
    s += stroka(20, y + 44, "= 4/6·(976 + 3072 + 520) = 4/6·4568")
    s += tx(20, y + 72, "= +3045,33", "lbl-b", "start")
    s += stroka(430, y, "C–K: M₁ — треугольник, Ω₁ = ½·4·4 = 8,")
    s += stroka(430, y + 22, "ц. т. — 1/3 длины от большей ординаты (от C);")
    s += stroka(430, y + 44, "M<tspan class='sub'>P</tspan> постоянна: y<tspan class='sub'>c</tspan> = 10")
    s += tx(430, y + 72, "8 · 10 = +80", "lbl-b", "start")
    s += tx(10, y + 118, "C–D: M₁ = 0 — произведение 0.     Δ_гор·EJ = 8736 + 3045,33 + 80 = 11 861,33",
            "lbl-b", "start")
    s += '</svg>\n'
    return s.replace("Δ_гор", "Δ<tspan class='sup'>гор</tspan><tspan class='sub'>K</tspan>")


def figura_raznye():
    """Для сравнения: вертикальное перемещение K — на A–B эпюры по разные стороны."""
    w, h = 760, 320
    s = HEAD.format(w=w, h=h, alt="Схема 1: эпюры по разные стороны — произведение со знаком минус")
    s += tx(10, 26, "Для сравнения — P = 1 вниз в K, участок A–B:  M<tspan class='sub'>P</tspan> снизу, "
                    "M₁ сверху  →  знак «−»", "lbl-b", "start")
    s += tx(150, 60, "M<tspan class='sub'>P</tspan>", "ep-kl") + tx(530, 60, "M₁", "ep-kl")
    s += panel((40, 140), (1, 0), 220, lambda t: 242 - 120 * t, 242, 70, ("A", "B"),
               [(0, "242"), (1, "122"), (F(1, 3), "y<tspan class='sub'>c</tspan> = 202")], pometka=F(1, 3))
    s += panel((420, 140), (1, 0), 220, lambda t: -6 + 6 * t, 6, 60, ("A", "B"),
               [(0, "6")], metka=(F(1, 3), ""))
    s += tx(310, 140, "×", "lbl-b")
    s += stroka(40, 262, "Ω₁ = ½·6·6 = 18;  ц. т. треугольника — 1/3 длины от A (2 м);"
                         "  y<tspan class='sub'>c</tspan> = 242 − 120·2/6 = 202")
    s += tx(40, 294, "−18 · 202 = −3636  (точка K поднимается)", "lbl-b", "start")
    s += '</svg>\n'
    return s


if __name__ == "__main__":
    open("ed-1-pere.svg", "w", encoding="utf-8").write(figura_storony())
    open("ed-1-pere-v.svg", "w", encoding="utf-8").write(figura_raznye())
    print("записано: ed-1-pere.svg (по сторонам), ed-1-pere-v.svg")
