"""Курсовая по ТСП, вариант 2: контуры, размеры и геометрический объём котлована.

Исходные данные - Задание 4 (вариант 2), грунт - супесь (как в планировке).
Методичка: «Технологическая карта на земляные работы», МГСУ 2018, п. 2.2.2.
Точная арифметика - fractions.Fraction; корень в формуле объёма - через float.
"""
from fractions import Fraction as Fr
from math import sqrt

# --- Задание 4, вариант 2 ---
HK = Fr("2.4")       # глубина котлована Нк, м
H_FP = Fr("0.4")     # фундаментная плита, м
H_BP = Fr("0.15")    # бетонная подготовка, м
H_PODS = Fr("0.1")   # подсыпка (щебень), м
L_KAR = Fr("10")     # расстояние до карьера, отвала, км
RAZM = 8             # вариант размещения здания

# Схема размещения фундамента (размеры от оси стены, мм): 500 + 200 + 500
A_FP = Fr("0.5")     # ось -> край фундаментной плиты
D_BP = Fr("0.2")     # выход бетонной подготовки за плиту
C_RZ = Fr("0.5")     # рабочая зона: край подготовки -> подошва откоса
OTS_NIZ = A_FP + D_BP + C_RZ   # ось -> низ котлована = 1,2 м

# Супесь, глубина до 3 м: крутизна 1:0,67 (прил. 3)
M = Fr("0.67")
L_OTK = HK * M       # заложение откоса l = Нк*m

# Пандус: принято (уточнить у преподавателя) - однополосный въезд автосамосвалов
B_PAN = Fr(3)        # ширина пандуса, м
I_PAN = Fr("0.1")    # уклон въезда, 0,10-0,15
N_PAN = 1 / I_PAN    # n = 1/i


def contour(d):
    """Г-образный контур по осям здания, смещённый наружу на d.
    Оси: 60 x 30 м с вырезом 42 x 12 в правом нижнем углу (начало - левый нижний угол)."""
    return [(-d, -d), (18 + d, -d), (18 + d, 12 - d), (60 + d, 12 - d),
            (60 + d, 30 + d), (-d, 30 + d)]


def area(poly):
    s = 0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        s += x1 * y2 - x2 * y1
    return abs(Fr(s)) / 2


def sides(poly):
    out = []
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        out.append(abs(x2 - x1) + abs(y2 - y1))
    return out


OSI = contour(Fr(0))
FP = contour(A_FP)
BP = contour(A_FP + D_BP)
NIZ = contour(OTS_NIZ)
VERH = contour(OTS_NIZ + L_OTK)

F_OSI, F_FP, F_BP = area(OSI), area(FP), area(BP)
F_KN, F_KV = area(NIZ), area(VERH)

V_PAN = N_PAN * (B_PAN * HK ** 2 / 2 + M * HK ** 3 / 3)
L_PAN = HK * N_PAN   # длина пандуса в плане
V_OSN = float(HK) / 3 * (float(F_KN) + float(F_KV) + sqrt(float(F_KN * F_KV)))
V_K = V_OSN + float(V_PAN)

V_FP = F_FP * H_FP
V_BP = F_BP * H_BP
V_PODS = F_KN * H_PODS


def f(v, n=3):
    return f"{round(float(v), n):.{n}f}".rstrip("0").rstrip(".").replace(".", ",")


if __name__ == "__main__":
    print("Здание по осям: стороны", [f(s) for s in sides(OSI)], " F =", f(F_OSI), "м2")
    print("Фундаментная плита (оси + 0,5):", [f(s) for s in sides(FP)], " F =", f(F_FP))
    print("Бетонная подготовка (оси + 0,7):", [f(s) for s in sides(BP)], " F =", f(F_BP))
    print("Отступ низа котлована от осей:", f(OTS_NIZ), "м")
    print("Заложение откоса l = 2,4*0,67 =", f(L_OTK), "м")
    print("Низ котлована:", [f(s) for s in sides(NIZ)], " Fк.н =", f(F_KN), "м2")
    print("Верх котлована:", [f(s) for s in sides(VERH)], " Fк.в =", f(F_KV), "м2")
    print("Габарит по низу:", f(60 + 2 * OTS_NIZ), "x", f(30 + 2 * OTS_NIZ))
    print("Габарит по верху:", f(60 + 2 * (OTS_NIZ + L_OTK)), "x", f(30 + 2 * (OTS_NIZ + L_OTK)))
    print("Объём без пандуса:", f(V_OSN), "м3")
    print("Пандус: b =", f(B_PAN), "i =", f(I_PAN), "n =", f(N_PAN),
          "длина =", f(L_PAN), " Vпан =", f(V_PAN), "м3")
    print("Vк =", f(V_K), "м3")
    print("Vф.п =", f(V_FP), " Vб.п =", f(V_BP), " Vподс =", f(V_PODS), "м3")
