"""Трёхшарнирная рама-ферма (задание №1, вариант 19, нижняя схема) — геометрия и точный расчёт.

Прочтение схемы с карточки (чертёж на карточке в масштабе; размеры панелей
не проставлены, поэтому сетка снята с чертежа):
  * шаг сетки d = l/6 по горизонтали и по вертикали, l = 44 м;
  * опоры A (x = 0) и B (x = l = 6d) шарнирно-неподвижные, на уровне y = 0;
  * верхний пояс на y = 3d = l/2, нижний на y = 2d, от x = −d до x = 7d;
  * ключевой шарнир C — узел верхнего пояса при x = 3d = l/2;
  * «ноги»: стойка над опорой и наклонный стержень к соседнему узлу нижнего
    пояса, распорка на высоте d и раскос от верха стойки к распорке.

Нумерация узлов: верхний пояс 1, 2, 3, 4, C, 6, 7, 8, 9 (x = −d … 7d),
нижний пояс 1′ … 9′ (под одноимёнными узлами, 5′ нет), ноги D, E (левая) и F, G (правая).
Правило знаков: N > 0 — растяжение. Реакции: V вверх, H_A вправо, H_B влево.
"""
from fractions import Fraction as Fr
import math

l = Fr(44)
d = l / 6
P = Fr(14)
K = 3                      # множитель силы в узле 4′ (на карточке «3P»)

_n = {
    "A": (0, 0), "B": (6, 0),
    "D": (0, 1), "E": (Fr(1, 2), 1), "F": (6, 1), "G": (Fr(11, 2), 1),
    "C": (3, 3),
}
for i in (1, 2, 3, 4, 6, 7, 8, 9):
    _n[str(i)] = (i - 2, 3)
    _n[f"{i}′"] = (i - 2, 2)
NODES = {k: (Fr(x), Fr(y)) for k, (x, y) in _n.items()}   # в долях d

MEMBERS = [
    # левый пояс: верхний, нижний, стойки, раскосы
    ("1", "2"), ("2", "3"), ("3", "4"), ("4", "C"),
    ("1′", "2′"), ("2′", "3′"), ("3′", "4′"),
    ("1", "1′"), ("2", "2′"), ("3", "3′"), ("4", "4′"),
    ("1", "2′"), ("2′", "3"), ("3", "4′"), ("4′", "C"),
    # правый пояс
    ("C", "6"), ("6", "7"), ("7", "8"), ("8", "9"),
    ("6′", "7′"), ("7′", "8′"), ("8′", "9′"),
    ("6", "6′"), ("7", "7′"), ("8", "8′"), ("9", "9′"),
    ("C", "6′"), ("6′", "7"), ("7", "8′"), ("8′", "9"),
    # левая нога: стойка, наклонный стержень, распорка, раскос
    ("2′", "D"), ("D", "A"), ("3′", "E"), ("E", "A"), ("D", "E"), ("2′", "E"),
    # правая нога
    ("8′", "F"), ("F", "B"), ("7′", "G"), ("G", "B"), ("F", "G"), ("8′", "G"),
]
assert len(MEMBERS) == 42 and len(NODES) == 23          # 42 + 4 = 2·23 — статически определима


def mname(a, b):
    return f"{a}–{b}"


LOADS = {                  # узловые нагрузки (Fx, Fy), кН
    "2": (Fr(0), -P),          # P вниз — верхний узел над опорой A
    "1′": (Fr(0), -P),         # P вниз — конец левой консоли
    "4′": (Fr(0), -K * P),     # 3P вниз — нижний узел x = 2d
    "7": (Fr(0), -2 * P),      # 2P вниз — верхний узел x = 5d
    "9′": (P, Fr(0)),          # P вправо — конец правой консоли
    "F": (P / 2, Fr(0)),       # P/2 вправо — узел распорки правой ноги
}


def xy(n):
    x, y = NODES[n]
    return x * d, y * d


def cw(n, x0, y0, F=LOADS):
    """Момент силы в узле n относительно (x0, y0): по часовой — плюс."""
    x, y = xy(n)
    fx, fy = F[n]
    return -((x - x0) * fy - (y - y0) * fx)


def reactions():
    """Метод трёхшарнирных систем: ΣM_A, ΣM_B, ΣM_C(лев), ΣM_C(прав)."""
    VB = sum(cw(n, 0, 0) for n in LOADS) / l
    VA = -sum(cw(n, l, 0) for n in LOADS) / l
    xc, yc = xy("C")
    left = [n for n in LOADS if xy(n)[0] < xc]
    right = [n for n in LOADS if xy(n)[0] > xc]
    HA = (VA * (l / 2) + sum(cw(n, xc, yc) for n in left)) / yc
    HB = (VB * (l / 2) - sum(cw(n, xc, yc) for n in right)) / yc
    return VA, HA, VB, HB


def solve(A, b):
    """Гаусс в дробях; A — квадратная."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = next(r for r in range(c, n) if M[r][c] != 0)
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        M[c] = [v / pv for v in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)]


def forces():
    """Все усилия вырезанием всех узлов сразу (46 уравнений: 42 стержня + 4 реакции).

    Неизвестные — «удельные» усилия u = N/|Δ| (|Δ| — длина в долях d), тогда
    коэффициенты рациональные. Возвращает N (float), u (Fraction), реакции (Fraction).
    """
    names = list(NODES)
    m = len(MEMBERS)
    rows, rhs = [], []
    for n in names:
        for c in (0, 1):
            row = [Fr(0)] * (m + 4)
            for j, (a, b) in enumerate(MEMBERS):
                if n in (a, b):
                    o = b if n == a else a
                    row[j] = NODES[o][c] - NODES[n][c]
            if n == "A":
                row[m + 0] = Fr(1) if c == 1 else Fr(0)        # V_A
                row[m + 1] = Fr(1) if c == 0 else Fr(0)        # H_A (вправо)
            if n == "B":
                row[m + 2] = Fr(1) if c == 1 else Fr(0)        # V_B
                row[m + 3] = Fr(-1) if c == 0 else Fr(0)       # H_B (влево)
            rows.append(row)
            rhs.append(-LOADS.get(n, (0, 0))[c])
    # 46 уравнений, 46 неизвестных — но система вырождена без условия шарнира C?
    # Нет: шарнир C — узел, в котором пояса не связаны на момент, это уже учтено
    # тем, что C — обычный узел фермы. Решаем как есть.
    sol = solve(rows, rhs)
    u = sol[:m]
    VA, HA, VB, HB = sol[m:]
    N = {}
    for j, (a, b) in enumerate(MEMBERS):
        dx = NODES[b][0] - NODES[a][0]
        dy = NODES[b][1] - NODES[a][1]
        N[(a, b)] = float(u[j]) * math.sqrt(float(dx * dx + dy * dy))
    return N, dict(zip(MEMBERS, u)), (VA, HA, VB, HB)


if __name__ == "__main__":
    VA, HA, VB, HB = reactions()
    print(f"Реакции (3 шарнира): V_A={VA}={float(VA):.4f}  H_A={HA}={float(HA):.4f}  "
          f"V_B={VB}={float(VB):.4f}  H_B={HB}={float(HB):.4f}")
    N, u, R = forces()
    print("Реакции (все узлы):", [str(r) for r in R])
    assert R == (VA, HA, VB, HB)
    for (a, b), v in N.items():
        print(f"{mname(a, b):7} {v:10.4f}   u={u[(a, b)]}")
