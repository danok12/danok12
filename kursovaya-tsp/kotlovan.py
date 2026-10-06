"""Курсовая по ТСП, вариант 2: котлован - контуры, размеры, объёмы (п. 2.2.2 методички).

Габариты - Задание 4, вариант 2; грунт - супесь (как в планировке, по указанию
преподавателя). Здание - вариант размещения 8: центр здания в центре квадрата 8.
Точная арифметика - fractions.Fraction; корень в формуле объёма - через float.
"""
from fractions import Fraction as Fr
from math import sqrt
import raschet as R

# ---------- Задание 4, вариант 2 ----------
NK = Fr("2.4")       # глубина котлована по заданию Нк, м (от планировочной отметки)
H_FP = Fr("0.4")     # фундаментная плита Нф.п, м
H_BP = Fr("0.15")    # бетонная подготовка hб.п, м
H_PODS = Fr("0.1")   # подсыпка hподс (щебень), м
L_KAR = Fr("10")     # расстояние до карьера, отвала, км
RAZM = 8             # вариант размещения здания = номер квадрата

# Схема размещения фундамента в котловане (мм): стена 400 по оси;
# от наружной грани стены 500 (вылет плиты) + 200 (выход подготовки) + 500 (до откоса)
B_ST = Fr("0.4")
D_ST = B_ST / 2                  # ось -> наружная грань стены = 0,2
D_FP = D_ST + Fr("0.5")          # ось -> край фундаментной плиты = 0,7
D_BP = D_FP + Fr("0.2")          # ось -> край бетонной подготовки = 0,9
D_NIZ = D_BP + Fr("0.5")         # ось -> низ откоса (подошва котлована) = 1,4
C_RZ = D_NIZ - D_FP              # рабочая зона от плиты до откоса = 0,7 (не менее 0,6)

# Здание по осям: Г-образное 60 x 30 м с вырезом 42 x 12 справа снизу
BX, BY = 60, 30
CUT_X, CUT_Y = 42, 12
SQ = RAZM
_r, _c = divmod(SQ - 1, R.NX)
SQ_CENTER = (Fr(R.A * _c) + Fr(R.A, 2), Fr(R.A * (R.NY - 1 - _r)) + Fr(R.A, 2))
X0 = SQ_CENTER[0] - Fr(BX, 2)    # левая ось здания
Y0 = SQ_CENTER[1] - Fr(BY, 2)    # нижняя ось здания


def contour(d):
    """Контур, смещённый от осей здания наружу на d (координаты площадки, м)."""
    pts = [(-d, -d), (BX - CUT_X + d, -d), (BX - CUT_X + d, CUT_Y - d), (BX + d, CUT_Y - d),
           (BX + d, BY + d), (-d, BY + d)]
    return [(X0 + x, Y0 + y) for x, y in pts]


def area(poly):
    s = 0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        s += x1 * y2 - x2 * y1
    return abs(Fr(s)) / 2


def sides(poly):
    return [abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1])]


def h_work(x, y):
    """Рабочая отметка в точке площадки - билинейная интерполяция по квадрату."""
    i = min(int(x // R.A), R.NX - 1)
    jb = min(int(y // R.A), R.NY - 1)          # ряд снизу
    j = R.NY - 1 - jb                           # строка вершин сверху (верх квадрата)
    u, v = Fr(x) / R.A - i, Fr(y) / R.A - jb
    h00, h10 = R.h(i, j + 1), R.h(i + 1, j + 1)  # низ
    h01, h11 = R.h(i, j), R.h(i + 1, j)          # верх
    return h00 * (1 - u) * (1 - v) + h10 * u * (1 - v) + h01 * (1 - u) * v + h11 * u * v


# ---------- расположение котлована относительно ЛНР ----------
def slope_m(depth):
    """Супесь, прил. 3: до 1,5 м - 1:0,25; до 3 м - 1:0,67; до 5 м - 1:0,85."""
    return Fr("0.25") if depth <= Fr("1.5") else Fr("0.67") if depth <= 3 else Fr("0.85")


# предварительно - по глубине задания, затем по фактической
VERH0 = contour(D_NIZ + NK * slope_m(NK))
H_CORNERS = [h_work(*p) for p in VERH0]
H_MEAN = sum(H_CORNERS) / len(H_CORNERS)
CROSSED = min(H_CORNERS) < 0 < max(H_CORNERS)   # ЛНР пересекает котлован
IN_FILL = H_MEAN > 0
CENTER = SQ_CENTER
HR = h_work(*CENTER) if IN_FILL else Fr(0)      # hр в центре котлована (только для насыпи)
HK = NK - HR                                     # фактическая глубина от естественной поверхности
M = slope_m(HK)
L_OTK = HK * M                                   # заложение откоса l = hк*m

OSI = contour(Fr(0))
ST = contour(D_ST)
FP = contour(D_FP)
BP = contour(D_BP)
NIZ = contour(D_NIZ)
VERH = contour(D_NIZ + L_OTK)
H_CORNERS_F = [h_work(*p) for p in VERH]
assert (sum(H_CORNERS_F) > 0) == IN_FILL         # зона не меняется после уточнения глубины

F_OSI, F_ST, F_FP, F_BP = area(OSI), area(ST), area(FP), area(BP)
F_KN, F_KV = area(NIZ), area(VERH)

# ---------- пандус (принято: однополосный въезд автосамосвалов) ----------
B_PAN = Fr(3)        # ширина, м
I_PAN = Fr("0.1")    # уклон 0,10-0,15 при вывозе самосвалами
N_PAN = 1 / I_PAN
L_PAN = HK * N_PAN   # длина в плане от подошвы до бровки
V_PAN = N_PAN * (B_PAN * HK ** 2 / 2 + M * HK ** 3 / 3)
PAN_X = NIZ[3][0]                                # правая сторона котлована (ось 3 + 1,4)
PAN_Y = Y0 + Fr(BY + CUT_Y, 2) - B_PAN / 2       # по середине правой стороны


def ramp_geometry():
    """Линии пандуса в плане: подошва, бровки откосов, пересечения с откосом котлована."""
    xb, y1, y2 = PAN_X, PAN_Y, PAN_Y + B_PAN
    xe = xb + L_PAN
    xt = xb + L_OTK                                  # бровка котлована
    off = M * HK * (1 - L_OTK / L_PAN)               # бровка откоса пандуса у бровки котлована
    return {
        "toe": [((xb, y1), (xe, y1)), ((xb, y2), (xe, y2))],
        "brow": [((xt, y1 - off), (xe, y1)), ((xt, y2 + off), (xe, y2))],
        "edge": [((xb, y1), (xt, y1 - off)), ((xb, y2), (xt, y2 + off))],
        "end": ((xe, y1), (xe, y2)),
        "gap": (y1 - off, y2 + off),     # разрыв бровки котлована
    }


# ---------- объёмы ----------
V_OSN = float(HK) / 3 * (float(F_KN) + float(F_KV) + sqrt(float(F_KN * F_KV)))
V_K = V_OSN + float(V_PAN)
V_PODS = F_KN * H_PODS                    # подсыпка по всей подошве
V_BP = F_BP * H_BP
V_FP = F_FP * H_FP
H_STEN = HK - H_FP - H_BP - H_PODS        # стены подвала ниже естественной поверхности
V_KSP = F_ST * H_STEN
V_PCH = V_FP + V_KSP
V_GI = V_ST = Fr(0)                       # гидроизоляция (2 слоя рулонной) и стяжка - в задании без толщин
V_OZ = V_K - float(V_PCH + V_PODS + V_BP + V_GI + V_ST)

# ---------- сводный баланс (табл. 2), до корректировки отметок ----------
K_OR = Fr("1.04")
VV_PL = sum(g["V"] for g in R.FIGS if g["sign"] < 0)
VN_PL = sum(g["V"] for g in R.FIGS if g["sign"] > 0)
SUM_V = float(VV_PL) + V_K
SUM_N = float(VN_PL) + V_OZ
SUM_NK = float(VN_PL / K_OR) + V_OZ / float(K_OR)
BALANCE = SUM_V - SUM_NK
BAL_PCT = BALANCE / max(SUM_V, SUM_NK) * 100


def f(v, n=3):
    return f"{round(float(v), n):.{n}f}".rstrip("0").rstrip(".").replace(".", ",")


if __name__ == "__main__":
    print(f"Здание: квадрат {SQ}, центр ({f(CENTER[0])}; {f(CENTER[1])}), оси x {f(X0)}..{f(X0 + BX)},"
          f" y {f(Y0)}..{f(Y0 + BY)}")
    print("Рабочие отметки по углам котлована (бровка):", [f(h) for h in H_CORNERS_F],
          " среднее", f(sum(H_CORNERS_F) / 6, 4))
    print("ЛНР пересекает котлован:", CROSSED, "->", "зона насыпи" if IN_FILL else "зона выемки")
    print("hр в центре =", f(HR, 4), " hк = Нк - hр =", f(NK), "-", f(HR, 4), "=", f(HK, 4), "м")
    print("m =", f(M), " l = hк*m =", f(L_OTK, 5), "м")
    for name, p, F in (("Оси", OSI, F_OSI), ("Наружн. грань стен", ST, F_ST), ("Плита", FP, F_FP),
                       ("Подготовка", BP, F_BP), ("Низ котлована", NIZ, F_KN), ("Верх котлована", VERH, F_KV)):
        print(f"  {name}: стороны {[f(s, 4) for s in sides(p)]}  F = {f(F, 4)} м2")
    print("Габарит по низу:", f(BX + 2 * D_NIZ), "x", f(BY + 2 * D_NIZ),
          " по верху:", f(BX + 2 * (D_NIZ + L_OTK), 4), "x", f(BY + 2 * (D_NIZ + L_OTK), 4))
    print("Vосн =", f(V_OSN), " Vпан =", f(V_PAN), f"(L = {f(L_PAN, 3)} м)", " Vк =", f(V_K))
    print("Vподс =", f(V_PODS), " Vб.п =", f(V_BP), " Vф.п =", f(V_FP),
          " Vк.с.п =", f(V_KSP), f"(h = {f(H_STEN, 4)})", " Vп.ч =", f(V_PCH))
    print("Vо.з =", f(V_OZ))
    print(f"Баланс: Vв = {f(VV_PL)} + {f(V_K)} = {f(SUM_V)};  Vн = {f(VN_PL)} + {f(V_OZ)} = {f(SUM_N)};"
          f"  Vн/Kор = {f(SUM_NK)};  Vв - Vн/Kор = {f(BALANCE)} ({f(BAL_PCT, 2)} %)")
