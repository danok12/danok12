"""Сборка решения задания №1 (трёхшарнирная арка, вариант 19) в reshenie.html.

Все числа в тексте берутся из расчёта ниже — руками в шаблон ничего не вписано.
«Ручная» арифметика ведётся в Decimal с теми же округлениями, что написаны
в решении (sin, cos — 6 знаков, H — 4 знака, произведения — 3 знака),
и сверяется с точным расчётом (Fraction + math) до 0,005.
Чертежи — SVG в масштабе, координаты считаются по уравнению оси.
"""
import math
import sys
from decimal import Decimal as D, ROUND_HALF_UP
from fractions import Fraction as Fr
from pathlib import Path
from string import Template

HERE = Path(__file__).parent

# ============================ расчёт ============================
l, f, q, P = 44, 14, 10, 14
P2 = 2 * P
x1, x2 = l / 4, 3 * l / 4

# Ось — дуга окружности через A(0; 0), C(l/2; f), B(l; 0):
# R = (l²/4 + f²) / (2f), центр O(l/2; −(R − f)).
RAD = (Fr(l * l, 4) + f * f) / (2 * f)
assert RAD == Fr(170, 7)
Rf = float(RAD)


def y_of(x):
    return math.sqrt(Rf**2 - (x - l / 2) ** 2) - (Rf - f)


def tg_of(x):
    return (l / 2 - x) / math.sqrt(Rf**2 - (x - l / 2) ** 2)


def R(v, n=3):
    return D(v).quantize(D(1).scaleb(-n), rounding=ROUND_HALF_UP)


# точно
VA = Fr(P * 3 * l, 4 * l) + Fr(P2 * l, 4 * l) + Fr(q * (l // 2) * (l // 4), l)
VB = Fr(P * l, 4 * l) + Fr(P2 * 3 * l, 4 * l) + Fr(q * (l // 2) * (3 * l // 4), l)
H = (VA * l / 2 - P * Fr(l, 4)) / f
HB = (VB * l / 2 - q * Fr(l, 2) * Fr(l, 4) - P2 * Fr(l, 4)) / f
assert VA == Fr(145, 2) and VB == Fr(379, 2) and H == HB == Fr(1441, 14)
dx = Fr(l, 2) - Fr(l, 4)                       # l/2 − x для K1 (для K2 — то же по модулю)
sin_k = dx / RAD                               # sin φ = (l/2 − x)/R — точно
assert sin_k == Fr(77, 170)
R2m = RAD**2 - dx**2                           # R² − (l/2 − x)² = 22971/49
assert R2m == Fr(22971, 49)
root = math.sqrt(float(R2m))                   # √(R² − (l/2 − x)²)
yk = root - float(RAD - f)
assert abs(yk - y_of(x1)) < 1e-12 and abs(yk - y_of(x2)) < 1e-12
Hf = float(H)
Hy = Hf * yk
M1 = float(VA) * 11 - Hy
M2 = float(VB) * 11 - 605 - Hy
M0_2 = VA * Fr(3 * l, 4) - P * Fr(l, 2) - q * Fr(l, 4) * Fr(l, 8)
assert abs(float(M0_2) - Hy - M2) < 1e-9

s_ex = float(sin_k)
c_ex = root / Rf
assert abs(s_ex / c_ex - tg_of(x1)) < 1e-12
phi = math.degrees(math.asin(s_ex))
ex = {
    "Q1l": float(VA) * c_ex - Hf * s_ex, "N1l": -float(VA) * s_ex - Hf * c_ex,
    "Q1p": float(VA - P) * c_ex - Hf * s_ex, "N1p": -float(VA - P) * s_ex - Hf * c_ex,
    "Q2l": -float(VB - 110 - 28) * c_ex + Hf * s_ex, "N2l": -float(VB - 110 - 28) * s_ex - Hf * c_ex,
    "Q2p": -float(VB - 110) * c_ex + Hf * s_ex, "N2p": -float(VB - 110) * s_ex - Hf * c_ex,
}

# вручную — как записано в решении
S, C = R(repr(s_ex), 6), R(repr(c_ex), 6)
Hd = R(D(1441) / D(14), 4)
Hs, Hc = R(Hd * S), R(Hd * C)
VAd, VBd = D("72.5"), D("189.5")
Rd, RmF = R(D(170) / D(7), 4), R(D(72) / D(7), 4)          # R и R − f
sqd = R(D(22971).sqrt(), 5)                                 # √22971
rootd = R(sqd / 7, 5)                                       # √(R² − 11²) = √22971 / 7
Yd = R((sqd - 72) / 7, 5)                                   # y_K = (√22971 − 72) / 7
assert abs(float(Yd) - yk) < 1e-5 and abs(float(rootd) - root) < 1e-5, (Yd, yk)
assert R(sqd / 170, 6) == C and R(D(77) / D(170), 6) == S
tgd = R(S / C, 5)
h = {}
h["VAc"], h["VAs"] = R(VAd * C), R(VAd * S)
h["VAPc"], h["VAPs"] = R((VAd - P) * C), R((VAd - P) * S)
h["Q1l"], h["Q1p"] = h["VAc"] - Hs, h["VAPc"] - Hs
h["N1l"], h["N1p"] = -h["VAs"] - Hc, -h["VAPs"] - Hc
B1, B2 = VBd - 110, VBd - 110 - 28                     # 79,5 и 51,5
h["B1c"], h["B1s"], h["B2c"], h["B2s"] = R(B1 * C), R(B1 * S), R(B2 * C), R(B2 * S)
h["Q2p"], h["Q2l"] = -h["B1c"] + Hs, -h["B2c"] + Hs
h["N2p"], h["N2l"] = -h["B1s"] - Hc, -h["B2s"] - Hc
for k in ex:
    assert abs(float(h[k]) - ex[k]) < 0.005, (k, h[k], ex[k])
    assert R(h[k], 2) == R(repr(ex[k]), 2), (k, h[k], ex[k])
Hyd = R(D(1441) * Yd / 14)                                  # H·y_K с H = 1441/14
M1d = D("797.5") - Hyd
M2d = D("2084.5") - 605 - Hyd
M0_2d = D(M0_2.numerator) / D(M0_2.denominator)
assert R(M1d, 2) == R(repr(M1), 2) and R(M2d, 2) == R(repr(M2), 2), (M1d, M1, M2d, M2)
assert M0_2d - Hyd == M2d

# скачки и проверки равновесия (ручные значения)
h["Pc"], h["Ps"] = R(P * C), R(P * S)
h["P2c"], h["P2s"] = R(P2 * C), R(P2 * S)
h["jQ1"], h["jN1"] = h["Q1l"] - h["Q1p"], h["N1p"] - h["N1l"]
h["jQ2"], h["jN2"] = h["Q2l"] - h["Q2p"], h["N2l"] - h["N2p"]
h["x1a"], h["x1b"] = R(h["N1p"] * C), R(h["Q1p"] * S)
h["X1"] = h["x1a"] + h["x1b"] + Hd
h["y1a"], h["y1b"] = R(h["N1p"] * S), R(h["Q1p"] * C)
h["Y1"] = (VAd - P) + h["y1a"] - h["y1b"]
h["x2a"], h["x2b"] = R(-h["N2p"] * C), R(h["Q2p"] * S)
h["X2"] = h["x2a"] + h["x2b"] - Hd
h["y2a"], h["y2b"] = R(h["N2p"] * S), R(h["Q2p"] * C)
h["Y2"] = B1 + h["y2a"] + h["y2b"]
h["negy1b"] = -h["y1b"]
for k in ("X1", "Y1", "X2", "Y2"):
    assert abs(h[k]) <= D("0.002"), (k, h[k])
for a, b in (("jQ1", "Pc"), ("jN1", "Ps"), ("jQ2", "P2c"), ("jN2", "P2s")):
    assert abs(h[a] - h[b]) <= D("0.002"), (a, h[a], h[b])


def fmt(v, n=None):
    """Число по-русски: запятая, длинный минус."""
    if isinstance(v, Fr):
        v = D(v.numerator) / D(v.denominator)
    if n is not None:
        v = R(v, n)
    s = format(D(v), "f") if isinstance(v, D) else str(v)
    if "." in s:
        s = s.rstrip("0").rstrip(".") if n is None else s
    return s.replace("-", "−").replace(".", ",")


def sgn(v, n=3):
    """Для подстановки: отрицательное — в скобках."""
    s = fmt(v, n)
    return f"({s})" if s.startswith("−") else s


V = {k: fmt(v, 3) for k, v in h.items()}
V.update(
    S=fmt(S, 6), C=fmt(C, 6), H4=fmt(Hd, 4), H2=fmt(H, 2), Hs=fmt(Hs, 3), Hc=fmt(Hc, 3),
    phi=fmt(R(repr(phi), 3)), phi2=fmt(R(repr(phi), 2)),
    M1=fmt(M1d, 2), M2=fmt(M2d, 2), M0_2=fmt(M0_2, 1), M1_3=fmt(M1d, 3), M2_3=fmt(M2d, 3),
    Rr=fmt(Rd, 4), RmF=fmt(RmF, 4), sq=fmt(sqd, 5), root=fmt(rootd, 5),
    Y=fmt(Yd, 5), Y3=fmt(Yd, 3), Y2d=fmt(Yd, 2), Hy=fmt(Hyd, 3), tg=fmt(tgd, 5),
    Q1p_b=sgn(h["Q1p"]), N1p_b=sgn(h["N1p"]), Q2p_b=sgn(h["Q2p"]), N2p_b=sgn(h["N2p"]),
    N2p_neg=fmt(-h["N2p"], 3), X1=fmt(h["X1"], 4), X2=fmt(h["X2"], 4),
    Y1=fmt(abs(h["Y1"]), 3), Y2=fmt(abs(h["Y2"]), 3),
    **{k + "_op": ("− " if h[k] < 0 else "+ ") + fmt(abs(h[k]), 3) for k in ("x1b", "y1a", "negy1b", "x2b", "y2a", "y2b")},
    **{"n" + b: ("" if h[a] == h[b] else ' <span class="c">(разница ' + fmt(abs(h[a] - h[b]), 3) + ' — округление)</span>')
       for a, b in (("jQ1", "Pc"), ("jN1", "Ps"), ("jQ2", "P2c"), ("jN2", "P2s"))},
    **{k + "_2": fmt(h[k], 2) for k in ("Q1l", "Q1p", "N1l", "N1p", "Q2l", "Q2p", "N2l", "N2p")},
    **{k + "_ex": fmt(R(repr(v), 2)) for k, v in ex.items()},
)

# ============================ чертежи ============================
sys.path.insert(0, str(HERE.parent))
from chertezh import *  # noqa: E402,F403 — палитра, Svg, esc, rich

def arch_pts(tr, xa, xb, n=160):
    return [tr(xa + (xb - xa) * i / n, y_of(xa + (xb - xa) * i / n)) for i in range(n + 1)]


PHI = math.radians(phi)
SIN, COS = math.sin(PHI), math.cos(PHI)


def fig_scheme():
    """Рис. 1 — расчётная схема по заданию."""
    g = Svg("f1", 720, 390)
    s, ox, oy = 11.5, 110, 285
    T = lambda x, yy: (ox + s * x, oy - s * yy)
    A, B, Cc, K1, K2 = T(0, 0), T(l, 0), T(l / 2, f), T(x1, y_of(x1)), T(x2, y_of(x2))
    g.poly(arch_pts(T, 0, l), INK, 2.6)
    g.support(*A)
    g.support(*B)
    g.hinge(*Cc)
    g.dot(*K1)
    g.dot(*K2)
    # нагрузки
    g.arrow(K1[0], K1[1] - 72, K1[0], K1[1] - 4, "load", 2)
    g.text(K1[0], K1[1] - 80, "P = 14 кН", LOAD, 13.5, "middle", "600")
    yq1, yq2 = oy - s * 16.2, oy - s * 17.6
    g.qload(Cc[0], B[0], yq2, yq1, 12)
    g.text(B[0] + 8, yq1 - 2, "q = 10 кН/м", LOAD, 13.5, "start", "600")
    g.arrow(K2[0], 34, K2[0], K2[1] - 4, "load", 2)
    g.text(K2[0], 26, "2P = 28 кН", LOAD, 13.5, "middle", "600")
    # подписи точек
    g.text(A[0] - 14, A[1] - 4, "A", INK, 14, "end", "700")
    g.text(B[0] + 14, B[1] - 4, "B", INK, 14, "start", "700")
    g.text(Cc[0] - 9, Cc[1] - 9, "C", INK, 14, "end", "700")
    g.text(K1[0] + 9, K1[1] + 24, "K_{1}", INK, 14, "start", "700")
    g.text(K2[0] - 9, K2[1] + 24, "K_{2}", INK, 14, "end", "700")
    # оси
    g.arrow(A[0], A[1], A[0], A[1] - 52, "ink", 1.1)
    g.text(A[0] - 6, A[1] - 44, "y", INK, 13, "end", italic=True)
    g.arrow(A[0], A[1], A[0] + 54, A[1], "ink", 1.1)
    g.text(A[0] + 50, A[1] - 6, "x", INK, 13, "middle", italic=True)
    # размеры
    yd = oy + 58
    for xx in (0, l):
        g.line(T(xx, 0)[0], oy + 30, T(xx, 0)[0], oy + 94, DIM, 0.7)
    for xx, p in ((x1, K1), (l / 2, Cc), (x2, K2)):
        g.ext(p[0], p[1] + 5, p[0], yd + 6)
    for a, b in ((0, x1), (x1, l / 2), (l / 2, x2), (x2, l)):
        g.dim_h(T(a, 0)[0], T(b, 0)[0], yd, "l/4 = 11 м")
    g.dim_h(A[0], B[0], oy + 88, "l = 44 м")
    xf = B[0] + 58
    g.ext(Cc[0] + 6, Cc[1], xf + 6, Cc[1])
    g.line(B[0] + 26, oy, xf + 6, oy, DIM, 0.7)
    g.dim_v(xf, Cc[1], oy, "f = 14 м", side=+1)
    xy = A[0] - 62
    g.ext(K1[0] - 6, K1[1], xy - 6, K1[1])
    g.line(A[0] - 26, oy, xy - 6, oy, DIM, 0.7)
    g.dim_v(xy, K1[1], oy, f"y_{{K}} = {V['Y3']} м")
    return g.svg("Расчётная схема арки")


def fig_signs():
    """Рис. 2 — положительные направления M, Q, N и знак моментов в уравнениях."""
    g = Svg("f2", 720, 188)
    xl, xr, yc = 300, 420, 95
    g.add(f'<rect x="{xl}" y="{yc - 15}" width="{xr - xl}" height="30" fill="#e8f1f1" stroke="{INK}" stroke-width="1.4"/>')
    g.text((xl + xr) / 2, yc + 5, "элемент", GRAY, 12, "middle", halo=False)
    # правый торец (= сечение левой отсечённой части)
    g.arrow(xr, yc, xr + 42, yc, "int", 2)
    g.text(xr + 30, yc - 7, "N", INT, 14, "middle", "700")
    g.arrow(xr + 12, yc - 34, xr + 12, yc + 34, "int", 2)
    g.text(xr + 12, yc + 52, "Q", INT, 14, "middle", "700")
    g.arc(xr, yc, 62, -52, 52, "int", 1.8)
    g.text(xr + 52, yc - 58, "M", INT, 14, "start", "700")
    # левый торец (= сечение правой отсечённой части)
    g.arrow(xl, yc, xl - 42, yc, "int", 2)
    g.text(xl - 30, yc - 7, "N", INT, 14, "middle", "700")
    g.arrow(xl - 12, yc + 34, xl - 12, yc - 34, "int", 2)
    g.text(xl - 12, yc - 42, "Q", INT, 14, "middle", "700")
    g.arc(xl, yc, 62, 232, 128, "int", 1.8)
    g.text(xl - 52, yc + 68, "M", INT, 14, "end", "700")
    g.text(xr + 6, 180, "правый торец — как сечение K₁ левой части", GRAY, 11.5, "start")
    g.text(xl - 6, 180, "левый торец — как сечение K₂ правой части", GRAY, 11.5, "end")
    # знак моментов в уравнениях
    g.text(110, 34, "в уравнениях ΣM:", GRAY, 12, "middle")
    g.arc(52, 70, 15, 150, -120, "ink", 1.5)
    g.text(78, 75, "по часовой — «+»", INK, 13, "start")
    g.arc(52, 120, 15, 30, 300, "ink", 1.5)
    g.text(78, 125, "против часовой — «−»", INK, 13, "start")
    return g.svg("Правило знаков")


def fig_whole(values):
    """Рис. 3 / 7 — арка без опор, с реакциями."""
    g = Svg("f3" if not values else "f7", 720, 410)
    s, ox, oy = 11, 118, 280
    T = lambda x, yy: (ox + s * x, oy - s * yy)
    A, B, Cc, K1, K2 = T(0, 0), T(l, 0), T(l / 2, f), T(x1, y_of(x1)), T(x2, y_of(x2))
    g.poly(arch_pts(T, 0, l), INK, 2.6)
    g.hinge(*A)
    g.hinge(*B)
    g.hinge(*Cc)
    g.dot(*K1)
    g.dot(*K2)
    g.arrow(K1[0], K1[1] - 70, K1[0], K1[1] - 4, "load", 2)
    g.text(K1[0], K1[1] - 78, "P = 14 кН", LOAD, 13.5, "middle", "600")
    yq1, yq2 = oy - s * 16.2, oy - s * 17.6
    g.qload(Cc[0], B[0], yq2, yq1, 12)
    g.text(B[0] - 6, yq2 - 8, "q = 10 кН/м", LOAD, 13.5, "end", "600")
    g.arrow(K2[0], 30, K2[0], K2[1] - 4, "load", 2)
    g.text(K2[0] - 8, 30, "2P = 28 кН", LOAD, 13.5, "end", "600")
    g.text(A[0] + 12, A[1] + 18, "A", INK, 14, "start", "700")
    g.text(B[0] - 12, B[1] + 18, "B", INK, 14, "end", "700")
    g.text(Cc[0] - 9, Cc[1] - 9, "C", INK, 14, "end", "700")
    g.text(K1[0] + 9, K1[1] + 24, "K_{1}", INK, 14, "start", "700")
    g.text(K2[0] - 9, K2[1] + 24, "K_{2}", INK, 14, "end", "700")
    va = "V_{A} = 72,5 кН" if values else "V_{A}"
    vb = "V_{B} = 189,5 кН" if values else "V_{B}"
    ha = f"H_{{A}} = {V['H2']} кН" if values else "H_{A}"
    hb = f"H_{{B}} = {V['H2']} кН" if values else "H_{B}"
    g.arrow(A[0], A[1] + 62, A[0], A[1] + 6, "reac", 2.2)
    g.text(A[0] + 8, A[1] + 58, va, REAC, 13.5, "start", "700")
    g.arrow(A[0] - 66, A[1], A[0] - 6, A[1], "reac", 2.2)
    g.text(A[0] - 8, A[1] - 12, ha, REAC, 13.5, "end", "700")
    g.arrow(B[0], B[1] + 62, B[0], B[1] + 6, "reac", 2.2)
    g.text(B[0] - 8, B[1] + 58, vb, REAC, 13.5, "end", "700")
    g.arrow(B[0] + 66, B[1], B[0] + 6, B[1], "reac", 2.2)
    g.text(B[0] + 8, B[1] - 12, hb, REAC, 13.5, "start", "700")
    if not values:
        g.text(K2[0] + 10, yq1 + 20, "R_{q} = q·l/2 = 220 кН  (при x = 33 м)", GRAY, 12, "start")
    yd = oy + 92
    g.line(A[0], oy + 68, A[0], yd + 30, DIM, 0.7)
    g.line(B[0], oy + 68, B[0], yd + 30, DIM, 0.7)
    for p in (K1, Cc, K2):
        g.ext(p[0], p[1] + 5, p[0], yd + 6)
    for a, b in ((0, x1), (x1, l / 2), (l / 2, x2), (x2, l)):
        g.dim_h(T(a, 0)[0], T(b, 0)[0], yd, "l/4 = 11 м")
    g.dim_h(A[0], B[0], yd + 24, "l = 44 м")
    return g.svg("Арка с опорными реакциями")


def fig_halves():
    """Рис. 4 — полуарки для ΣM_C."""
    g = Svg("f4", 740, 385)
    s, oy = 11, 268
    oxl, oxr = 92, 176
    TL = lambda x, yy: (oxl + s * x, oy - s * yy)
    TR = lambda x, yy: (oxr + s * x, oy - s * yy)
    A, Cl, K1 = TL(0, 0), TL(l / 2, f), TL(x1, y_of(x1))
    Cr, K2, B = TR(l / 2, f), TR(x2, y_of(x2)), TR(l, 0)
    g.poly(arch_pts(TL, 0, l / 2), INK, 2.6)
    g.poly(arch_pts(TR, l / 2, l), INK, 2.6)
    for p in (A, Cl, Cr, B):
        g.hinge(*p)
    g.dot(*K1)
    g.dot(*K2)
    g.text(TL(11, 0)[0], 20, "левая полуарка AC", GRAY, 12.5, "middle")
    g.text(TR(38, 0)[0], 20, "правая полуарка CB", GRAY, 12.5, "middle")
    # левая
    g.arrow(K1[0], K1[1] - 66, K1[0], K1[1] - 4, "load", 2)
    g.text(K1[0], K1[1] - 74, "P = 14 кН", LOAD, 13.5, "middle", "600")
    g.arrow(A[0], A[1] + 58, A[0], A[1] + 6, "reac", 2.2)
    g.text(A[0] + 8, A[1] + 54, "V_{A} = 72,5 кН", REAC, 13, "start", "700")
    g.arrow(A[0] - 60, A[1], A[0] - 6, A[1], "reac", 2.2)
    g.text(A[0] - 62, A[1] - 10, "H_{A}", REAC, 14, "start", "700")
    g.arrow(Cl[0] + 5, Cl[1], Cl[0] + 34, Cl[1], "gray", 1.5, "4 3")
    g.text(Cl[0] + 14, Cl[1] - 8, "X_{C}", GRAY, 13, "start")
    g.arrow(Cl[0], Cl[1] - 5, Cl[0], Cl[1] - 36, "gray", 1.5, "4 3")
    g.text(Cl[0] - 6, Cl[1] - 26, "Y_{C}", GRAY, 13, "end")
    g.text(A[0] - 10, A[1] + 22, "A", INK, 14, "end", "700")
    g.text(Cl[0] + 9, Cl[1] + 22, "C", INK, 14, "start", "700")
    g.text(K1[0] + 9, K1[1] + 24, "K_{1}", INK, 14, "start", "700")
    # правая
    yq1, yq2 = oy - s * 15.8, oy - s * 17.2
    g.qload(Cr[0], B[0], yq2, yq1, 11)
    g.text(B[0] - 4, yq2 - 8, "q = 10 кН/м", LOAD, 13.5, "end", "600")
    g.arrow(K2[0], 34, K2[0], K2[1] - 4, "load", 2)
    g.text(K2[0] - 8, 44, "2P = 28 кН", LOAD, 13.5, "end", "600")
    g.arrow(B[0], B[1] + 58, B[0], B[1] + 6, "reac", 2.2)
    g.text(B[0] - 8, B[1] + 54, "V_{B} = 189,5 кН", REAC, 13, "end", "700")
    g.arrow(B[0] + 60, B[1], B[0] + 6, B[1], "reac", 2.2)
    g.text(B[0] + 62, B[1] - 10, "H_{B}", REAC, 14, "end", "700")
    g.arrow(Cr[0] - 5, Cr[1], Cr[0] - 34, Cr[1], "gray", 1.5, "4 3")
    g.text(Cr[0] - 14, Cr[1] + 20, "X_{C}", GRAY, 13, "end")
    g.arrow(Cr[0], Cr[1] + 5, Cr[0], Cr[1] + 36, "gray", 1.5, "4 3")
    g.text(Cr[0] + 6, Cr[1] + 34, "Y_{C}", GRAY, 13, "start")
    g.text(B[0] + 10, B[1] + 22, "B", INK, 14, "start", "700")
    g.text(Cr[0] + 8, Cr[1] - 8, "C", INK, 14, "start", "700")
    g.text(K2[0] - 9, K2[1] + 24, "K_{2}", INK, 14, "end", "700")
    # f и размеры
    g.ext(A[0] + 6, oy, Cl[0] + 6, oy)
    g.dim_v(Cl[0], Cl[1] + 5, oy, "f = 14 м")
    yd = oy + 82
    g.line(A[0], oy + 62, A[0], yd + 6, DIM, 0.7)
    g.line(B[0], oy + 62, B[0], yd + 6, DIM, 0.7)
    for p in (K1, K2):
        g.ext(p[0], p[1] + 5, p[0], yd + 6)
    g.ext(Cl[0], oy + 5, Cl[0], yd + 6)
    g.ext(Cr[0], Cr[1] + 42, Cr[0], yd + 6)
    g.dim_h(A[0], K1[0], yd, "l/4 = 11 м")
    g.dim_h(K1[0], Cl[0], yd, "l/4 = 11 м")
    g.dim_h(Cr[0], K2[0], yd, "l/4 = 11 м")
    g.dim_h(K2[0], B[0], yd, "l/4 = 11 м")
    return g.svg("Полуарки для уравнения моментов относительно шарнира C")


def unit(deg):
    """Единичный вектор на экране для угла deg (математического)."""
    return math.cos(math.radians(deg)), -math.sin(math.radians(deg))


def fig_left_K1():
    """Рис. 5 — левая часть A–K1."""
    g = Svg("f5", 720, 455)
    s, ox, oy = 20, 176, 338
    T = lambda x, yy: (ox + s * x, oy - s * yy)
    A, K = T(0, 0), T(x1, y_of(x1))
    g.poly(arch_pts(T, 0, x1), INK, 2.8)
    g.hinge(*A)
    ph = phi
    at = lambda deg, r: (K[0] + r * unit(deg)[0], K[1] + r * unit(deg)[1])
    # оси m (касательная) и n (нормаль)
    g.line(*K, *at(ph, 132), GRAY, 0.9, "5 4")
    g.text(*at(ph, 142), "m", GRAY, 14, "middle", italic=True)
    g.line(*at(90 + ph, 62), *at(ph - 90, 80), GRAY, 0.9, "5 4")
    g.text(*at(90 + ph, 72), "n", GRAY, 14, "middle", italic=True)
    # горизонталь и угол φ
    xdim = ox + 400
    g.ext(K[0] + 4, K[1], xdim + 6, K[1])
    g.arc(K[0], K[1], 54, 0, ph, "ink", 1.1, head=False)
    g.text(*at(ph / 2, 67), "φ", INK, 14, "middle", italic=True)
    g.arc(K[0], K[1], 30, 90, 90 + ph, "ink", 1.0, head=False)
    g.text(*at(90 + ph / 2, 42), "φ", INK, 13, "middle", italic=True)
    # усилия
    g.arrow(*K, *at(ph, 84), "int", 2.4)
    g.text(at(ph, 84)[0] - 6, at(ph, 84)[1] - 12, "N_{1}", INT, 15, "end", "700")
    g.arrow(*K, *at(ph - 90, 66), "int", 2.4)
    g.text(at(ph - 90, 66)[0] + 10, at(ph - 90, 66)[1] + 4, "Q_{1}", INT, 15, "start", "700")
    g.arc(K[0], K[1], 32, 140, 198, "int", 2)
    g.text(*at(170, 52), "M_{1}", INT, 15, "middle", "700")
    # нагрузки и реакции
    g.arrow(K[0], K[1] - 84, K[0], K[1] - 5, "load", 2.2)
    g.text(K[0] + 8, K[1] - 76, "P = 14 кН", LOAD, 13.5, "start", "600")
    g.arrow(A[0], A[1] + 62, A[0], A[1] + 6, "reac", 2.2)
    g.text(A[0] + 10, A[1] + 58, "V_{A} = 72,5 кН", REAC, 13.5, "start", "700")
    g.arrow(A[0] - 70, A[1], A[0] - 6, A[1], "reac", 2.2)
    g.text(A[0] - 10, A[1] - 12, f"H = {V['H2']} кН", REAC, 13.5, "end", "700")
    g.text(A[0] - 10, A[1] + 22, "A", INK, 14, "end", "700")
    g.dot(*K)
    g.text(K[0] - 8, K[1] + 36, "K_{1}", INK, 14, "end", "700")
    # размеры
    g.ext(A[0] + 6, oy, xdim + 6, oy)
    g.dim_v(xdim, K[1], oy, f"y_{{K1}} = {V['Y3']} м", side=+1)
    yd = oy + 96
    g.line(A[0], oy + 68, A[0], yd + 6, DIM, 0.7)
    g.ext(K[0], K[1] + 5, K[0], yd + 6)
    g.dim_h(A[0], K[0], yd, "l/4 = 11 м")
    return g.svg("Левая часть арки, отсечённая по сечению K1")


def fig_right_K2():
    """Рис. 6 — правая часть K2–B."""
    g = Svg("f6", 720, 520)
    s, ox, oy = 20, 330 - 20 * x2, 392
    T = lambda x, yy: (ox + s * x, oy - s * yy)
    K, B = T(x2, y_of(x2)), T(l, 0)
    g.poly(arch_pts(T, x2, l), INK, 2.8)
    g.hinge(*B)
    ph = phi
    at = lambda deg, r: (K[0] + r * unit(deg)[0], K[1] + r * unit(deg)[1])
    # нагрузка q, равнодействующая, 2P
    yq1, yq2 = oy - s * 14.3, oy - s * 15.5
    g.qload(K[0], B[0], yq2, yq1, 10)
    g.text(B[0] + 8, yq1 - 3, "q = 10 кН/м", LOAD, 13.5, "start", "600")
    xr = T(x2 + l / 8, 0)[0]
    g.arrow(xr, yq2 - 34, xr, yq2 - 3, "load", 1.6, "5 3")
    g.text(xr + 8, yq2 - 24, "R_{q} = q·l/4 = 110 кН", LOAD, 13, "start")
    g.arrow(K[0], 40, K[0], K[1] - 5, "load", 2.2)
    g.text(K[0], 32, "2P = 28 кН", LOAD, 13.5, "middle", "600")
    # оси
    g.line(*K, *at(180 - ph, 128), GRAY, 0.9, "5 4")
    g.text(*at(180 - ph, 139), "m", GRAY, 14, "middle", italic=True)
    g.line(*K, *at(90 - ph, 70), GRAY, 0.9, "5 4")
    g.line(*K, *at(270 - ph, 48), GRAY, 0.9, "5 4")
    g.text(*at(90 - ph, 80), "n", GRAY, 14, "middle", italic=True)
    # горизонталь и угол φ
    xdim = B[0] + 128
    g.ext(K[0] + 4, K[1], xdim + 6, K[1])
    g.arc(K[0], K[1], 54, 0, -ph, "ink", 1.1, head=False)
    g.text(*at(-ph / 2, 68), "φ", INK, 14, "middle", italic=True)
    g.arc(K[0], K[1], 28, 90, 90 - ph, "ink", 1.0, head=False)
    g.text(*at(90 - ph / 2, 40), "φ", INK, 13, "middle", italic=True)
    # усилия
    g.arrow(*K, *at(180 - ph, 84), "int", 2.4)
    g.text(at(180 - ph, 84)[0] - 2, at(180 - ph, 84)[1] + 22, "N_{2}", INT, 15, "end", "700")
    g.arrow(*K, *at(90 - ph, 56), "int", 2.4)
    g.text(at(90 - ph, 56)[0] + 12, at(90 - ph, 56)[1] + 14, "Q_{2}", INT, 15, "start", "700")
    g.arc(K[0], K[1], 32, 226, 160, "int", 2)
    g.text(*at(194, 52), "M_{2}", INT, 15, "middle", "700")
    # реакции
    g.arrow(B[0], B[1] + 62, B[0], B[1] + 6, "reac", 2.2)
    g.text(B[0] + 10, B[1] + 58, "V_{B} = 189,5 кН", REAC, 13.5, "start", "700")
    g.arrow(B[0] + 70, B[1], B[0] + 6, B[1], "reac", 2.2)
    g.text(B[0] + 10, B[1] - 12, f"H = {V['H2']} кН", REAC, 13.5, "start", "700")
    g.text(B[0] - 10, B[1] + 22, "B", INK, 14, "end", "700")
    g.dot(*K)
    g.text(K[0] + 10, K[1] + 36, "K_{2}", INK, 14, "start", "700")
    # размеры
    g.line(B[0] + 76, oy, xdim + 6, oy, DIM, 0.7)
    g.dim_v(xdim, K[1], oy, f"y_{{K2}} = {V['Y3']} м", side=+1)
    yd = oy + 92
    g.line(B[0], oy + 68, B[0], yd + 30, DIM, 0.7)
    g.ext(K[0], K[1] + 5, K[0], yd + 30)
    g.ext(xr, yq1 + 2, xr, yd + 6)
    g.dim_h(K[0], xr, yd, "l/8 = 5,5 м")
    g.dim_h(xr, B[0], yd, "l/8 = 5,5 м")
    g.dim_h(K[0], B[0], yd + 24, "l/4 = 11 м")
    return g.svg("Правая часть арки, отсечённая по сечению K2")


def fig_geom():
    """Рис. 5 — геометрия круговой оси: центр O, радиусы, угол φ."""
    g = Svg("fg", 720, 420)
    s, ox, oy = 10.5, 150, 236
    T = lambda x, yy: (ox + s * x, oy - s * yy)
    A, B, Cc = T(0, 0), T(l, 0), T(l / 2, f)
    O = T(l / 2, -(Rf - f))
    K1 = T(x1, y_of(x1))
    M = T(l / 2, 0)
    # полная окружность бледно, рабочая дуга — жирно
    g.add(f'<circle cx="{O[0]:.1f}" cy="{O[1]:.1f}" r="{s * Rf:.1f}" fill="none" stroke="{GRAY}" '
          f'stroke-width="0.8" stroke-dasharray="3 4"/>')
    g.poly(arch_pts(T, 0, l), INK, 2.6)
    g.line(*A, *B, DIM, 0.8, "5 4")
    for p_ in (A, B, Cc):
        g.hinge(*p_)
    g.dot(*K1)
    g.dot(*O, 3.4, INT)
    # радиусы
    g.line(*O, *Cc, INT, 1.4)
    g.line(*O, *K1, INT, 1.6)
    g.line(*O, *A, INT, 1.2, "6 4")
    g.text((O[0] + K1[0]) / 2 - 10, (O[1] + K1[1]) / 2, "R", INT, 15, "end", "700", italic=True)
    g.text((O[0] + A[0]) / 2 - 8, (O[1] + A[1]) / 2 + 16, "R", INT, 15, "end", "700", italic=True)
    # угол φ у центра — между OC (вертикаль) и OK1
    a_k = math.degrees(math.atan2(y_of(x1) + (Rf - f), x1 - l / 2))
    g.arc(O[0], O[1], 46, 90, a_k, "ink", 1.1, head=False)
    g.text(O[0] + 60 * math.cos(math.radians((90 + a_k) / 2)) - 2,
           O[1] - 60 * math.sin(math.radians((90 + a_k) / 2)) + 5, "φ", INK, 14, "middle", italic=True)
    # касательная в K1 и угол φ к горизонтали
    ux, uy = math.cos(PHI), -math.sin(PHI)
    g.line(K1[0] - 70 * ux, K1[1] - 70 * uy, K1[0] + 90 * ux, K1[1] + 90 * uy, GRAY, 1.0, "5 4")
    g.ext(K1[0] + 4, K1[1], K1[0] + 78, K1[1])
    g.arc(K1[0], K1[1], 58, 0, phi, "ink", 1.1, head=False)
    g.text(K1[0] + 72 * math.cos(PHI / 2), K1[1] - 72 * math.sin(PHI / 2) + 5, "φ", INK, 14, "middle", italic=True)
    # прямой угол между радиусом и касательной
    rx, ry = (O[0] - K1[0]), (O[1] - K1[1])
    rl = math.hypot(rx, ry)
    rx, ry = rx / rl * 11, ry / rl * 11
    tx, ty = ux * 11, uy * 11
    g.poly([(K1[0] + rx, K1[1] + ry), (K1[0] + rx + tx, K1[1] + ry + ty), (K1[0] + tx, K1[1] + ty)], INK, 1.0)
    g.text(K1[0] - 72 * ux - 4, K1[1] - 72 * uy + 16, "касательная", GRAY, 12, "end")
    # подписи
    g.text(A[0] - 10, A[1] + 20, "A", INK, 14, "end", "700")
    g.text(B[0] + 10, B[1] + 20, "B", INK, 14, "start", "700")
    g.text(Cc[0] + 9, Cc[1] - 9, "C", INK, 14, "start", "700")
    g.text(K1[0] - 12, K1[1] - 6, "K_{1}", INK, 14, "end", "700")
    g.text(O[0] + 10, O[1] + 18, "O — центр", INT, 13, "start", "700")
    g.text(M[0] + 6, M[1] + 16, "M", GRAY, 12, "start")
    # размеры
    yd = Cc[1] - 40
    g.ext(K1[0], K1[1] - 6, K1[0], yd - 6)
    g.ext(Cc[0], Cc[1] - 6, Cc[0], yd - 6)
    g.dim_h(K1[0], Cc[0], yd, "l/2 − x = 11 м")
    xv = B[0] + 60
    g.ext(Cc[0] + 8, Cc[1], xv + 6, Cc[1])
    g.ext(B[0] + 8, oy, xv + 6, oy)
    g.ext(O[0] + 8, O[1], xv + 6, O[1])
    g.dim_v(xv, Cc[1], oy, "f = 14 м", side=+1)
    g.dim_v(xv, oy, O[1], f"R − f = {V['RmF']} м", side=+1, size=11.5)
    xl = A[0] - 56
    g.ext(K1[0] - 8, K1[1], xl - 6, K1[1])
    g.ext(A[0] - 8, oy, xl - 6, oy)
    g.dim_v(xl, K1[1], oy, f"y_{{K1}} = {V['Y3']} м", size=11.5)
    xl2 = xl - 34
    g.ext(xl - 6, O[1], xl2 - 6, O[1])
    g.ext(O[0] - 8, O[1], xl - 6, O[1])
    g.dim_v(xl2, K1[1], O[1], f"√(R² − 11²) = {V['root']} м", size=11.5)
    return g.svg("Геометрия круговой оси арки")


FIGS = dict(FIGG=fig_geom(), FIG1=fig_scheme(), FIG2=fig_signs(), FIG3=fig_whole(False), FIG4=fig_halves(),
            FIG5=fig_left_K1(), FIG6=fig_right_K2(), FIG7=fig_whole(True))

html = Template((HERE / "shablon.html").read_text(encoding="utf-8")).substitute(**V, **FIGS)
(HERE / "reshenie.html").write_text(html, encoding="utf-8")
print("reshenie.html собран;", ", ".join(f"{k}={V[k]}" for k in ("Q1l", "Q1p", "N1l", "N1p", "Q2l", "Q2p", "N2l", "N2p")))
