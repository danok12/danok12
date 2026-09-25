"""Курсовая по ТСП, вариант 2: линия нулевых работ и объёмы планировочных работ.

Сетка 5x3 квадрата по a = 100 м. Вершины h1..h24 нумеруются построчно
слева направо, сверху вниз (как в приложении 1 методички).
Рабочая отметка h = Hкр - Hчёрн: минус - выемка (ПВ), плюс - насыпь (ПН).
Точная арифметика - fractions.Fraction.
"""
from fractions import Fraction as Fr

A = 100                      # сторона квадрата, м
NX, NY = 5, 3                # квадратов по горизонтали и вертикали
H = [-0.25, 0.15, 0.34, 0.47, 0.66, 0.85,
     -0.49, -0.31, 0.28, 0.52, 0.84, 0.47,
     -0.24, -0.43, -0.28, 0.14, 0.36, 0.76,
     -0.40, -0.65, -0.52, -0.28, -0.43, 0.14]
H = [Fr(str(v)) for v in H]
assert len(H) == (NX + 1) * (NY + 1)


def vnum(i, j):
    """Номер вершины (1..24): i - столбец 0..5, j - строка 0..3 сверху."""
    return j * (NX + 1) + i + 1


def h(i, j):
    return H[vnum(i, j) - 1]


def xy(i, j):
    """Координаты вершины, м: начало в левом нижнем углу, ось y вверх."""
    return (Fr(A * i), Fr(A * (NY - j)))


def zero_point(p1, p2):
    """Точка нуля на ребре p1-p2 (узлы (i,j)) или None.
    x = a*|h1|/(|h1|+|h2|) - расстояние от p1."""
    h1, h2 = h(*p1), h(*p2)
    if h1 == 0 or h2 == 0 or (h1 > 0) == (h2 > 0):
        return None
    x = A * abs(h1) / (abs(h1) + abs(h2))
    (x1, y1), (x2, y2) = xy(*p1), xy(*p2)
    t = x / A
    return {"p1": vnum(*p1), "p2": vnum(*p2), "x1": x, "x2": A - x,
            "pt": (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)}


def area(poly):
    s = 0
    for k in range(len(poly)):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def centroid(poly):
    s = cx = cy = 0
    for k in range(len(poly)):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
        c = x1 * y2 - x2 * y1
        s += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    return (cx / (3 * s), cy / (3 * s))


def split_square(n):
    """Квадрат n (1..15) -> список фигур: знак, вершины, отметки, площадь."""
    r, c = divmod(n - 1, NX)
    # обход против часовой: левый-нижний, правый-нижний, правый-верхний, левый-верхний
    nodes = [(c, r + 1), (c + 1, r + 1), (c + 1, r), (c, r)]
    ring = []                    # (координата, рабочая отметка, метка)
    for k in range(4):
        p1, p2 = nodes[k], nodes[(k + 1) % 4]
        ring.append((xy(*p1), h(*p1), ("v", vnum(*p1))))
        z = zero_point(p1, p2)
        if z:
            ring.append((z["pt"], Fr(0), ("z", tuple(sorted((z["p1"], z["p2"]))))))
    signs = {1 if hv > 0 else -1 for _, hv, _ in ring if hv != 0}
    zeros = [k for k, (_, hv, _) in enumerate(ring) if hv == 0]
    if len(signs) == 1:
        parts = [ring]
    else:
        assert len(zeros) == 2, f"седловой квадрат {n}: разобрать вручную"
        a, b = zeros
        parts = [ring[a:b + 1], ring[b:] + ring[:a + 1]]
    figs = []
    for part in parts:
        sgn = 1 if any(hv > 0 for _, hv, _ in part) else -1
        poly = [p for p, _, _ in part]
        marks = [abs(hv) for _, hv, _ in part]
        F = area(poly)
        hcp = sum(marks) / len(marks)
        figs.append({"sq": n, "sign": sgn, "poly": poly, "marks": marks,
                     "labels": [lb for _, _, lb in part],
                     "F": F, "hcp": hcp, "V": F * hcp, "c": centroid(poly)})
    # подпись: целый квадрат - "n"; разделённый - выемка "n", насыпь "n'"
    for f in figs:
        f["name"] = f"{n}" if len(figs) == 1 or f["sign"] < 0 else f"{n}'"
    return figs


def all_zero_points():
    pts = []
    for j in range(NY + 1):
        for i in range(NX):
            z = zero_point((i, j), (i + 1, j))
            if z: pts.append(z)
    for i in range(NX + 1):
        for j in range(NY):
            z = zero_point((i, j), (i, j + 1))
            if z: pts.append(z)
    return pts


FIGS = [f for n in range(1, NX * NY + 1) for f in split_square(n)]
ZP = all_zero_points()

if __name__ == "__main__":
    K_OR = Fr("1.04")
    print("Точки нулевых работ:")
    for z in ZP:
        print(f"  h{z['p1']}-h{z['p2']}: x1 = {float(z['x1']):.2f} м от h{z['p1']},"
              f" x2 = {float(z['x2']):.2f} м  pt=({float(z['pt'][0]):.2f}, {float(z['pt'][1]):.2f})")
    tot = {1: [0, 0], -1: [0, 0]}
    for sgn, title in ((-1, "ПВ"), (1, "ПН")):
        print(title)
        for f in FIGS:
            if f["sign"] != sgn: continue
            tot[sgn][0] += f["F"]; tot[sgn][1] += f["V"]
            print(f"  {f['name']:>4} F={round(float(f['F']), 6):>10} hcp={round(float(f['hcp']), 6):>9}"
                  f" ({'+'.join(str(float(m)) for m in f['marks'])})/{len(f['marks'])}"
                  f"  V={round(float(f['V']), 6)}")
        print(f"  ΣF={round(float(tot[sgn][0]), 6)} ΣV={round(float(tot[sgn][1]), 6)}")
    assert tot[1][0] + tot[-1][0] == A * A * NX * NY
    Vc, Vf = tot[-1][1], tot[1][1]
    print(f"ΣVпв={float(Vc):.2f}  ΣVпн={float(Vf):.2f}  ΣVпн/Kор={float(Vf / K_OR):.2f}"
          f"  разница={float(Vf / K_OR - Vc):.2f} ({float((Vf / K_OR - Vc) / Vc * 100):.2f} %)")
