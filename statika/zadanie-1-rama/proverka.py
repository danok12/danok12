"""Независимая проверка расчёта рамы-фермы (вариант 19, нижняя схема).

Отдельный путь вычислений: координаты в метрах, единичные векторы через sqrt,
Гаусс на float с выбором главного элемента. Реакции — неизвестные наравне
с усилиями (46 уравнений узлов). Затем:
  * сравнение с точным решением rama.py (дроби) и методом трёх шарниров;
  * невязки равновесия во всех узлах;
  * равновесие каждой полурамы как целого (ΣX, ΣY, ΣM_C) — это и есть
    условие шарнира C;
  * несколько усилий способом сечений (Риттер).
Запуск: python3 proverka.py  (ничего не падает = всё сошлось).
"""
import math

import rama

d = 44 / 6
P = 14.0
XY = {n: (float(x) * d, float(y) * d) for n, (x, y) in rama.NODES.items()}
LOADS = {n: (float(fx), float(fy)) for n, (fx, fy) in rama.LOADS.items()}
names = list(XY)
m = len(rama.MEMBERS)


def unit(a, b):
    dx, dy = XY[b][0] - XY[a][0], XY[b][1] - XY[a][1]
    L = math.hypot(dx, dy)
    return dx / L, dy / L


A = []
b = []
for n in names:
    for c in (0, 1):
        row = [0.0] * (m + 4)
        for j, (p, q) in enumerate(rama.MEMBERS):
            if n == p:
                row[j] = unit(p, q)[c]
            elif n == q:
                row[j] = unit(q, p)[c]
        if n == "A":
            row[m + (0 if c == 1 else 1)] = 1.0          # V_A вверх, H_A вправо
        if n == "B":
            row[m + (2 if c == 1 else 3)] = 1.0 if c == 1 else -1.0   # V_B вверх, H_B влево
        A.append(row)
        b.append(-LOADS.get(n, (0.0, 0.0))[c])

# Гаусс с выбором главного элемента
nn = len(A)
M = [A[i][:] + [b[i]] for i in range(nn)]
for col in range(nn):
    piv = max(range(col, nn), key=lambda r: abs(M[r][col]))
    assert abs(M[piv][col]) > 1e-9, "система вырождена — схема изменяема"
    M[col], M[piv] = M[piv], M[col]
    for r in range(nn):
        if r != col and M[r][col] != 0:
            f = M[r][col] / M[col][col]
            M[r] = [x - f * y for x, y in zip(M[r], M[col])]
sol = [M[i][nn] / M[i][i] for i in range(nn)]
N = dict(zip(rama.MEMBERS, sol[:m]))
VA, HA, VB, HB = sol[m:]

# 1) сравнение с точным решением и методом трёх шарниров
ex_N, _, R_ex = rama.forces()
R3 = rama.reactions()
for got, e1, e2 in zip((VA, HA, VB, HB), R_ex, R3):
    assert abs(got - float(e1)) < 1e-9 and abs(got - float(e2)) < 1e-9
for mm in rama.MEMBERS:
    assert abs(N[mm] - ex_N[mm]) < 1e-9, mm

# 2) невязки во всех узлах
worst = 0.0
for n in names:
    fx, fy = LOADS.get(n, (0.0, 0.0))
    if n == "A":
        fx, fy = fx + HA, fy + VA
    if n == "B":
        fx, fy = fx - HB, fy + VB
    for (p, q), v in N.items():
        if n in (p, q):
            ux, uy = unit(n, q if n == p else p)
            fx += v * ux
            fy += v * uy
    worst = max(worst, abs(fx), abs(fy))
assert worst < 1e-9

# 3) полурамы как целое: внешние силы + реакции + сила в шарнире C
LEFT = {"1", "2", "3", "4", "1′", "2′", "3′", "4′", "D", "E", "A"}
xc, yc = XY["C"]
for side, nodes, sup in (("лев", LEFT, "A"), ("прав", set(names) - LEFT - {"C"}, "B")):
    Fx = sum(LOADS.get(n, (0, 0))[0] for n in nodes)
    Fy = sum(LOADS.get(n, (0, 0))[1] for n in nodes)
    Mc = sum(-((XY[n][0] - xc) * LOADS[n][1] - (XY[n][1] - yc) * LOADS[n][0]) for n in nodes if n in LOADS)
    if sup == "A":
        Fx, Fy = Fx + HA, Fy + VA
        Mc += -((0 - xc) * VA - (0 - yc) * HA)
    else:
        Fx, Fy = Fx - HB, Fy + VB
        Mc += -((XY["B"][0] - xc) * VB - (0 - yc) * (-HB))
    assert abs(Mc) < 1e-9, (side, Mc)          # шарнир C не передаёт момент
    print(f"полурама {side}: ΣM_C = {Mc:+.2e}; сила от шарнира C: X = {-Fx:+.3f}, Y = {-Fy:+.3f} кН")

# 4) способ сечений: панель 3–4 (левая часть с опорой A) и панель 7–8 (правая часть с опорой B)
n34 = -2 * VA + 2 * HA + 5 * P
n3p4p = VA - 3 * HA - 3 * P
n34p = (VA - 2 * P) / math.sin(math.pi / 4)
assert abs(n34 - N[("3", "4")]) < 1e-9 and abs(n3p4p - N[("3′", "4′")]) < 1e-9 and abs(n34p - N[("3", "4′")]) < 1e-9
# правая часть справа от сечения через панель 7–8: стержни 7–8, 7–8′, 7′–8′ и 7′–G;
# моменты относительно узла 8′ (через него проходят 7–8′, 7′–8′ и 8′-линии) не годятся из-за 7′–G,
# поэтому проверяем ΣM относительно узла 8 для правой части узлов {8, 9, 8′, 9′, F, G, B}:
cut = [("7", "8"), ("7", "8′"), ("7′", "8′"), ("7′", "G")]
right = {"8", "9", "8′", "9′", "F", "G", "B"}
x8, y8 = XY["8"]
Mt = 0.0
for n in right:
    if n in LOADS:
        Mt += (XY[n][0] - x8) * LOADS[n][1] - (XY[n][1] - y8) * LOADS[n][0]
Mt += (XY["B"][0] - x8) * VB - (XY["B"][1] - y8) * (-HB)
for p, q in cut:
    inner = p if p in right else q
    outer = q if inner == p else p
    ux, uy = unit(inner, outer)
    v = N[(p, q)]
    Mt += (XY[inner][0] - x8) * v * uy - (XY[inner][1] - y8) * v * ux
assert abs(Mt) < 1e-9, Mt

print(f"реакции: V_A = {VA:.4f}, H_A = {HA:.4f}, V_B = {VB:.4f}, H_B = {HB:.4f} кН")
print(f"макс. невязка в узлах: {worst:.1e}")
print("сечение 3–4:", round(n34, 4), round(n3p4p, 4), round(n34p, 4))
print("Всё сошлось: float-решение = точное решение = метод трёх шарниров; полурамы и сечения в равновесии.")
