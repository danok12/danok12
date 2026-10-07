"""Курсовая по ТСП, вариант 2: котлован - контуры, размеры, объёмы (п. 2.2.2 методички).

Габариты - Задание 4, вариант 2; грунт - супесь (как в планировке, по указанию
преподавателя). Здание - вариант размещения 8: центр здания в центре квадрата 8.
Глубина - по формуле методички (с. 11): hк = Нк - hр.сл - hр (hр - только в насыпи).
Всё считается функцией pit() от состояния планировки (черновик или после Δh).
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
H_RSL = Fr("0.2")    # растительный слой hр.сл, м (методичка, с. 11: 200 мм)
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
CENTER = SQ_CENTER

# пандус (принято: однополосный въезд автосамосвалов)
B_PAN = Fr(3)        # ширина, м (методичка: 3 м - односторонний проезд)
I_PAN = Fr("0.1")    # уклон 0,10-0,15 при вывозе самосвалами
N_PAN = 1 / I_PAN


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


def h_work(hf, x, y):
    """Рабочая отметка в точке площадки - билинейная интерполяция по квадрату;
    hf(i, j) - рабочая отметка вершины."""
    i = min(int(x // R.A), R.NX - 1)
    jb = min(int(y // R.A), R.NY - 1)          # ряд снизу
    j = R.NY - 1 - jb                           # строка вершин сверху (верх квадрата)
    u, v = Fr(x) / R.A - i, Fr(y) / R.A - jb
    h00, h10 = hf(i, j + 1), hf(i + 1, j + 1)  # низ
    h01, h11 = hf(i, j), hf(i + 1, j)          # верх
    return h00 * (1 - u) * (1 - v) + h10 * u * (1 - v) + h01 * (1 - u) * v + h11 * u * v


def slope_m(depth):
    """Супесь, прил. 3: до 1,5 м - 1:0,25; до 3 м - 1:0,67; до 5 м - 1:0,85."""
    return Fr("0.25") if depth <= Fr("1.5") else Fr("0.67") if depth <= 3 else Fr("0.85")


def pit(P):
    """Котлован для состояния планировки P (результат raschet.compute)."""
    hf = P["h"]
    k = {}
    # расположение относительно ЛНР: предварительно - по глубине задания
    k["VERH0"] = contour(D_NIZ + NK * slope_m(NK))
    k["H_CORNERS"] = [h_work(hf, *p) for p in k["VERH0"]]
    k["H_MEAN"] = sum(k["H_CORNERS"]) / len(k["H_CORNERS"])
    k["CROSSED"] = min(k["H_CORNERS"]) < 0 < max(k["H_CORNERS"])     # ЛНР пересекает котлован
    k["IN_FILL"] = k["H_MEAN"] > 0
    k["HR"] = h_work(hf, *CENTER) if k["IN_FILL"] else Fr(0)          # hр в центре (только насыпь)
    k["HK"] = HK = NK - H_RSL - k["HR"]                                # hк = Нк - hр.сл - hр
    k["M"] = M = slope_m(HK)
    k["L_OTK"] = L_OTK = HK * M                                         # заложение откоса l = hк·m
    k["OSI"], k["ST"], k["FP"], k["BP"] = contour(Fr(0)), contour(D_ST), contour(D_FP), contour(D_BP)
    k["NIZ"], k["VERH"] = contour(D_NIZ), contour(D_NIZ + L_OTK)
    k["H_CORNERS_F"] = [h_work(hf, *p) for p in k["VERH"]]
    assert (sum(k["H_CORNERS_F"]) > 0) == k["IN_FILL"]                  # зона не меняется после уточнения
    for key, poly in (("F_OSI", "OSI"), ("F_ST", "ST"), ("F_FP", "FP"), ("F_BP", "BP"),
                      ("F_KN", "NIZ"), ("F_KV", "VERH")):
        k[key] = area(k[poly])
    # пандус
    k["L_PAN"] = HK * N_PAN                                             # длина в плане
    k["V_PAN"] = N_PAN * (B_PAN * HK ** 2 / 2 + M * HK ** 3 / 3)       # методичка, с. 14
    k["PAN_X"] = k["NIZ"][3][0]                                         # правая сторона (ось 3 + 1,4)
    k["PAN_Y"] = Y0 + Fr(BY + CUT_Y, 2) - B_PAN / 2                     # середина правой стороны
    # объёмы (с. 13-14)
    k["V_OSN"] = float(HK) / 3 * (float(k["F_KN"]) + float(k["F_KV"]) + sqrt(float(k["F_KN"] * k["F_KV"])))
    k["V_K"] = k["V_OSN"] + float(k["V_PAN"])
    k["V_PODS"] = k["F_KN"] * H_PODS
    k["V_BP"] = k["F_BP"] * H_BP
    k["V_FP"] = k["F_FP"] * H_FP
    k["H_STEN"] = HK - H_FP - H_BP - H_PODS     # = Нп − |hгр| − hр.сл − hр (стены ниже поверхности)
    k["V_KSP"] = k["F_ST"] * k["H_STEN"]
    k["V_PCH"] = k["V_FP"] + k["V_KSP"]
    k["V_GI"] = k["V_ST"] = Fr(0)               # гидроизоляция (2 слоя рулонной) и стяжка - в задании без толщин
    k["V_OZ"] = k["V_K"] - float(k["V_PCH"] + k["V_PODS"] + k["V_BP"] + k["V_GI"] + k["V_ST"])
    return k


def ramp_geometry(k):
    """Линии пандуса в плане: подошва, бровки откосов, пересечения с откосом котлована."""
    HK, M, L_OTK = k["HK"], k["M"], k["L_OTK"]
    xb, y1, y2 = k["PAN_X"], k["PAN_Y"], k["PAN_Y"] + B_PAN
    xe = xb + k["L_PAN"]
    xt = xb + L_OTK                                  # бровка котлована
    off = M * HK * (1 - L_OTK / k["L_PAN"])          # бровка откоса пандуса у бровки котлована
    return {
        "toe": [((xb, y1), (xe, y1)), ((xb, y2), (xe, y2))],
        "brow": [((xt, y1 - off), (xe, y1)), ((xt, y2 + off), (xe, y2))],
        "edge": [((xb, y1), (xt, y1 - off)), ((xb, y2), (xt, y2 + off))],
        "end": ((xe, y1), (xe, y2)),
        "gap": (y1 - off, y2 + off),     # разрыв бровки котлована
    }


K0 = pit(R.P0)                      # котлован по черновику
globals().update(K0)                # совместимость: kotlovan.HK, kotlovan.V_K, ... - по черновику


def f(v, n=3):
    return f"{round(float(v), n):.{n}f}".rstrip("0").rstrip(".").replace(".", ",")


def report(k, title):
    print(title)
    print(f"  Рабочие отметки по углам котлована (бровка): {[f(h) for h in k['H_CORNERS_F']]}"
          f"  среднее {f(sum(k['H_CORNERS_F']) / 6, 4)}")
    print("  ЛНР пересекает котлован:", k["CROSSED"], "->", "зона насыпи" if k["IN_FILL"] else "зона выемки")
    print(f"  hр в центре = {f(k['HR'], 4)};  hк = Нк - hр.сл - hр = {f(NK)} - {f(H_RSL)} - {f(k['HR'], 4)}"
          f" = {f(k['HK'], 4)} м;  m = {f(k['M'])};  l = {f(k['L_OTK'], 5)} м")
    for name, p, F in (("Низ котлована", k["NIZ"], k["F_KN"]), ("Верх котлована", k["VERH"], k["F_KV"])):
        print(f"  {name}: стороны {[f(s, 4) for s in sides(p)]}  F = {f(F, 4)} м2")
    print(f"  Vосн = {f(k['V_OSN'])}  Vпан = {f(k['V_PAN'])} (L = {f(k['L_PAN'])} м)  Vк = {f(k['V_K'])}")
    print(f"  Vподс = {f(k['V_PODS'])}  Vб.п = {f(k['V_BP'])}  Vф.п = {f(k['V_FP'])}"
          f"  Vк.с.п = {f(k['V_KSP'])} (h = {f(k['H_STEN'], 4)})  Vп.ч = {f(k['V_PCH'])}  Vо.з = {f(k['V_OZ'])}")


if __name__ == "__main__":
    print(f"Здание: квадрат {SQ}, центр ({f(CENTER[0])}; {f(CENTER[1])}), оси x {f(X0)}..{f(X0 + BX)},"
          f" y {f(Y0)}..{f(Y0 + BY)}")
    report(K0, "Котлован по черновику")
