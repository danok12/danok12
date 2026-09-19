# -*- coding: utf-8 -*-
"""Независимая перепроверка решения.

Каждая величина проверяется способом, отличным от того, каким она
получена в тексте:
  - корни — подстановкой в det(Tн − σE) = 0, а не в кубическое уравнение;
  - направляющие косинусы — из условия Tн·ν = σ·ν, а не по формулам Крамера;
  - удельная энергия — свёрткой ½·σij·εij, а не по формуле с инвариантами;
  - σэкв — через девиатор: √(3/2 · sij·sij);
  - τmax — как (σ1 − σ3)/2.
"""
from fractions import Fraction as F
from decimal import Decimal, getcontext
import math

getcontext().prec = 60
bad = []


def check(name, a, b, nd=2, unit=""):
    """nd — до скольких знаков округлено значение в тексте решения.

    Допуск — половина единицы последнего разряда: расхождение больше него
    означает настоящую ошибку, а не округление.
    """
    atol = 0.5 * 10 ** (-nd) + 1e-9
    ok = abs(float(a) - float(b)) <= atol
    print(f"  {name:<46} {float(a):>16.8f}  {float(b):>16.8f} {unit} "
          f"{'' if ok else '<-- РАСХОЖДЕНИЕ'}")
    if not ok:
        bad.append(name)


E = F(21, 10) * 10**5
nu = F(3, 10)
G = F(8, 10) * 10**5
Gt = E / (2 * (1 + nu))
R, gc = 210, F(9, 10)


def det3(M):
    return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
            - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))


def matvec(M, v):
    return [sum(M[i][j] * v[j] for j in range(3)) for i in range(3)]


print("=" * 92)
print("ЗАДАЧА 1")
print("=" * 92)
sx, sy, sz = -80.0, 60.0, -60.0
txy, tyz, tzx = 90.0, 50.0, -65.0
T = [[sx, txy, tzx], [txy, sy, tyz], [tzx, tyz, sz]]
print("  Tн симметричен (закон парности):",
      all(abs(T[i][j] - T[j][i]) < 1e-12 for i in range(3) for j in range(3)))

# --- 1. Корни: ищем как нули det(T - sE) ------------------------------
def fdet(s):
    return det3([[T[i][j] - (s if i == j else 0) for j in range(3)] for i in range(3)])

def bisect(a, b, n=300):
    fa = fdet(a)
    for _ in range(n):
        m = (a + b) / 2
        fm = fdet(m)
        if fa * fm <= 0:
            b = m
        else:
            a, fa = m, fm
    return (a + b) / 2

s1 = bisect(100.0, 120.0)
s2 = bisect(-20.0, 0.0)
s3 = bisect(-200.0, -150.0)
print("\n-- главные напряжения как нули det(Tн − σE) --------------------")
print(f"  {'величина':<46} {'проверка':>16}  {'в решении':>16}")
check("σ1, МПа", s1, 105.9582, 4)
check("σ2, МПа", s2, -7.1519, 4)
check("σ3, МПа", s3, -178.8063, 4)
print(f"  det(Tн − σ1·E) = {fdet(s1):.6e}   (должно быть 0)")
print(f"  det(Tн − σ2·E) = {fdet(s2):.6e}")
print(f"  det(Tн − σ3·E) = {fdet(s3):.6e}")
check("сумма корней = I1н", s1 + s2 + s3, -80, 6)
check("произведение корней = I3н", s1 * s2 * s3, 135500, 2)
check("след Tн", T[0][0] + T[1][1] + T[2][2], -80, 6)
check("det Tн", det3(T), 135500, 4)

# --- 2. Косинусы: из Tн·ν = σ·ν ---------------------------------------
print("\n-- направляющие косинусы из условия Tн·ν = σ·ν -----------------")
doc = {1: (0.3990, 0.9094, 0.1177), 2: (0.5582, -0.1390, -0.8180),
       3: (0.7275, -0.3921, 0.5630)}
vecs = {}
for i, s in ((1, s1), (2, s2), (3, s3)):
    # собственный вектор как векторное произведение двух строк (T − sE)
    A = [[T[r][c] - (s if r == c else 0) for c in range(3)] for r in range(3)]
    best, bn = None, 0.0
    for r1, r2 in ((0, 1), (1, 2), (2, 0)):
        u, v = A[r1], A[r2]
        w = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]]
        n = math.sqrt(sum(q*q for q in w))
        if n > bn:
            best, bn = w, n
    w = [q / bn for q in best]
    if sum(a*b for a, b in zip(w, doc[i])) < 0:      # знак — как в решении
        w = [-q for q in w]
    vecs[i] = w
    res = matvec(T, w)
    err = max(abs(res[k] - s * w[k]) for k in range(3))
    print(f"  ν{i}: невязка |Tн·ν − σ·ν| = {err:.2e}")
    for k, nm in enumerate(("l", "m", "n")):
        check(f"  {nm}{i}", w[k], doc[i][k], 4)
print("\n-- ортогональность и нормировка --------------------------------")
for a, b in ((1, 2), (2, 3), (3, 1)):
    print(f"  ν{a}·ν{b} = {sum(x*y for x, y in zip(vecs[a], vecs[b])):+.2e}")
for i in (1, 2, 3):
    print(f"  |ν{i}|  = {math.sqrt(sum(x*x for x in vecs[i])):.10f}")
print("\n-- углы наклона (таблица 3) ------------------------------------")
ang_doc = {1: (66.49, 24.58, 83.24), 2: (56.07, 97.99, 144.89),
           3: (43.32, 113.08, 55.73)}
for i in (1, 2, 3):
    for k, nm in enumerate(("x", "y", "z")):
        check(f"  ∠(ν{i},{nm}), град", math.degrees(math.acos(vecs[i][k])),
              ang_doc[i][k], 2)

# --- 3. Экстремальные касательные -------------------------------------
print("\n-- экстремальные касательные и нормальные ----------------------")
check("τ31 = (σ1 − σ3)/2, МПа", (s1 - s3) / 2, 142.38)
check("τ12 = (σ1 − σ2)/2, МПа", (s1 - s2) / 2, 56.56)
check("τ23 = (σ2 − σ3)/2, МПа", (s2 - s3) / 2, 85.83)
check("σ12, МПа", (s1 + s2) / 2, 49.40)
check("σ23, МПа", (s2 + s3) / 2, -92.98)
check("σ31, МПа", (s1 + s3) / 2, -36.42)

# --- 4. Деформации и энергия ------------------------------------------
print("\n-- деформации ---------------------------------------------------")
fE, fnu, fG = float(E), float(nu), float(G)
ex = (sx - fnu * (sy + sz)) / fE
ey = (sy - fnu * (sz + sx)) / fE
ez = (sz - fnu * (sx + sy)) / fE
gxy, gyz, gzx = txy / fG, tyz / fG, tzx / fG
check("εx ×10⁻⁵", ex * 1e5, -38.10)
check("εy ×10⁻⁵", ey * 1e5, 48.57)
check("εz ×10⁻⁵", ez * 1e5, -25.71)
check("θ ×10⁻⁵", (ex + ey + ez) * 1e5, -15.24)
check("γxy ×10⁻⁵", gxy * 1e5, 112.50)
check("γyz ×10⁻⁵", gyz * 1e5, 62.50)
check("γzx ×10⁻⁵", gzx * 1e5, -81.25)

print("\n-- удельная энергия свёрткой ½·σij·εij --------------------------")
# тензор деформаций: сдвиговые компоненты εij = γij/2, G берём согласованный
fGt = float(Gt)
eps = [[ex, txy / (2 * fGt), tzx / (2 * fGt)],
       [txy / (2 * fGt), ey, tyz / (2 * fGt)],
       [tzx / (2 * fGt), tyz / (2 * fGt), ez]]
u_conv = 0.5 * sum(T[i][j] * eps[i][j] for i in range(3) for j in range(3))
check("U0 свёрткой, МПа", u_conv, 0.12930, 5)
check("U0об = (1−2ν)/(6E)·I1н², МПа",
      (1 - fnu * 2) / (6 * fE) * 6400, 0.00203, 5)
check("U0ф = U0 − U0об, МПа", u_conv - (1 - 2 * fnu) / (6 * fE) * 6400,
      0.12727, 5)

print("\n-- σэкв через девиатор √(3/2·sij·sij) ---------------------------")
sm = (sx + sy + sz) / 3
dev = [[T[i][j] - (sm if i == j else 0) for j in range(3)] for i in range(3)]
s_ekv = math.sqrt(1.5 * sum(dev[i][j] ** 2 for i in range(3) for j in range(3)))
check("σэкв, МПа", s_ekv, 248.3445, 4)
check("σэкв по главным напряжениям, МПа",
      math.sqrt(((s1-s2)**2 + (s2-s3)**2 + (s3-s1)**2) / 2), 248.3445, 4)
check("R·γc, МПа", float(gc) * R, 189.0, 4)
print(f"  σэкв / (R·γc) = {s_ekv / 189.0:.4f}  -> превышение "
      f"{(s_ekv / 189.0 - 1) * 100:.1f} %   (в решении 31,4 %)")
check("U0ф = σэкв²/(6G), МПа", s_ekv**2 / (6 * fGt), 0.12727, 5)

# ======================================================================
print()
print("=" * 92)
print("ЗАДАЧА 2")
print("=" * 92)
ax, ay, axy = -85.0, -30.0, -30.0
T2 = [[ax, axy, 0.0], [axy, ay, 0.0], [0.0, 0.0, 0.0]]
r = math.sqrt(((ax - ay) / 2) ** 2 + axy ** 2)
p2, p3 = (ax + ay) / 2 + r, (ax + ay) / 2 - r
check("след Tн", ax + ay, -115, 6)
check("det 2×2 = I2н", ax * ay - axy ** 2, 1650, 6)
check("det Tн (3×3) = I3н", det3(T2), 0, 6)
check("σ2, МПа", p2, -16.8029, 4)
check("σ3, МПа", p3, -98.1971, 4)
print(f"  det(Tн − σ2·E) = "
      f"{det3([[T2[i][j] - (p2 if i == j else 0) for j in range(3)] for i in range(3)]):.3e}")
print(f"  det(Tн − σ3·E) = "
      f"{det3([[T2[i][j] - (p3 if i == j else 0) for j in range(3)] for i in range(3)]):.3e}")
check("τmax в плоскости = (σ2−σ3)/2", (p2 - p3) / 2, 40.6971, 4)
check("τmax в пространстве = (σ1−σ3)/2", (0 - p3) / 2, 49.0985, 4)

print("\n-- углы: собственные векторы против формулы tg αi = τyx/(σy − σi) --")
for nm, s in (("σ2", p2), ("σ3", p3)):
    a_formula = math.degrees(math.atan(axy / (ay - s)))
    # собственный вектор в плоскости (ось y вниз -> m = −sin α)
    l, m = math.cos(math.radians(a_formula)), -math.sin(math.radians(a_formula))
    e1 = (ax - s) * l + axy * m
    e2 = axy * l + (ay - s) * m
    print(f"  {nm}: α = {a_formula:+7.3f}°;  ур.(a) = {e1:+.2e};  "
          f"ур.(b) = {e2:+.2e};  l²+m² = {l*l+m*m:.10f}")
check("α2, град", math.degrees(math.atan(axy / (ay - p2))), 66.26)
check("α3, град", math.degrees(math.atan(axy / (ay - p3))), -23.74)
check("|α2|+|α3|, град",
      abs(math.degrees(math.atan(axy / (ay - p2))))
      + abs(math.degrees(math.atan(axy / (ay - p3)))), 90.0, 4)

print()
print("=" * 92)
print("ЕСТЬ РАСХОЖДЕНИЯ: " + ", ".join(bad) if bad
      else "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ — решение сходится независимыми способами.")
print("=" * 92)
