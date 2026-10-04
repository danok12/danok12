"""Проверка числовых ответов по параллелограмму.
1) Отношения и периметры — точной арифметикой (Fraction).
2) Каждую конфигурацию строим в координатах при нескольких острых углах и
   находим точку пересечения биссектрисы со стороной честно, без леммы о
   равнобедренном треугольнике. Округление через round(v, 6)."""
from fractions import Fraction as F
import math

def sides_acute(k_obt, k_acute, P):
    """Биссектриса острого угла A делит BC: от вершины B (тупой) k_obt частей,
    от C k_acute частей. AB = BE. Возвращает (AB, BC)."""
    x = F(P, 2 * (k_obt + (k_obt + k_acute)))
    return k_obt * x, (k_obt + k_acute) * x

def build(AB, AD, alpha_deg):
    a = math.radians(alpha_deg)
    A = (0.0, 0.0); D = (AD, 0.0)
    B = (AB * math.cos(a), AB * math.sin(a)); C = (B[0] + AD, B[1])
    return A, B, C, D

def hit(P0, direction, Q1, Q2):
    """Пересечение луча P0+t*dir с отрезком Q1Q2: параметр s на отрезке."""
    dx, dy = direction; ex, ey = Q2[0]-Q1[0], Q2[1]-Q1[1]
    det = dx*(-ey) - dy*(-ex)
    t = ((Q1[0]-P0[0])*(-ey) - (Q1[1]-P0[1])*(-ex)) / det
    s = (dx*(Q1[1]-P0[1]) - dy*(Q1[0]-P0[0])) / det
    return t, s

def unit(v):
    n = math.hypot(*v); return (v[0]/n, v[1]/n)

def bis(V, U, W):
    u, w = unit((U[0]-V[0], U[1]-V[1])), unit((W[0]-V[0], W[1]-V[1]))
    return (u[0]+w[0], u[1]+w[1])

def dist(P, Q): return math.hypot(P[0]-Q[0], P[1]-Q[1])

ANGLES = (35, 50, 60, 72, 85)

# ДЗ: 3:5 от тупого, P = 66
AB, BC = sides_acute(3, 5, 66)
assert (AB, BC) == (9, 24), (AB, BC)
for al in ANGLES:
    A, B, C, D = build(float(AB), float(BC), al)
    t, s = hit(A, bis(A, B, D), B, C)
    BE, EC = s*dist(B, C), (1-s)*dist(B, C)
    assert round(BE/EC, 6) == round(3/5, 6)
print("ok  ДЗ №1: стороны 9 и 24, P =", 2*(AB+BC))

# Аналог 1: 2:7 от тупого, P = 88
AB, BC = sides_acute(2, 7, 88); assert (AB, BC) == (8, 36)
print("ok  Г1: 8 и 36")

# Аналог 2: биссектриса ТУПОГО угла B делит AD в отношении 4:3 от острой вершины A, P = 110
x = F(110, 2*(4+7)); AB, AD = 4*x, 7*x; assert (AB, AD) == (20, 35)
for al in ANGLES:
    A, B, C, D = build(float(AB), float(AD), al)
    t, s = hit(B, bis(B, A, C), A, D)
    assert round(s/(1-s), 6) == round(4/3, 6)
print("ok  Г2: 20 и 35")

# Аналог 3: биссектриса острого угла A делит BC в отношении 1:2, считая от C (острая вершина), P = 60
AB, BC = sides_acute(2, 1, 60); assert (AB, BC) == (12, 18)
for al in ANGLES:
    A, B, C, D = build(float(AB), float(BC), al)
    t, s = hit(A, bis(A, B, D), B, C)
    assert round((1-s)/s, 6) == round(1/2, 6)
print("ok  Г3: 12 и 18")

# Аналог 4: стороны 10 и 16 -> отрезки большей стороны
for al in ANGLES:
    A, B, C, D = build(10.0, 16.0, al)
    t, s = hit(A, bis(A, B, D), B, C)
    assert (round(s*16, 6), round((1-s)*16, 6)) == (10, 6)
print("ok  Г4: 10 и 6 (от тупой вершины)")

# Аналог 5: биссектрисы A и D делят BC на три равные части, P = 40: два ответа
answers = []
for AB in range(1, 20):
    for BC in range(1, 20):
        if 2*(AB+BC) != 40: continue
        good = True
        for al in ANGLES:
            A, B, C, D = build(float(AB), float(BC), al)
            _, sE = hit(A, bis(A, B, D), B, C)
            _, sF = hit(D, bis(D, A, C), B, C)
            if not (0 <= sE <= 1 and 0 <= sF <= 1): good = False; break
            cuts = sorted([0, sE, sF, 1])
            parts = [round((cuts[i+1]-cuts[i])*BC, 6) for i in range(3)]
            if len(set(parts)) != 1: good = False; break
        if good: answers.append((AB, BC))
assert answers == [(5, 15), (8, 12)], answers
print("ok  Г5: два ответа", answers)

# Доказательство Д4: AB = 6, BC = 10, угол A = 60°, биссектрисы B и D -> периметр BMDK
A, B, C, D = build(6.0, 10.0, 60)
_, sK = hit(B, bis(B, A, C), A, D); K = (A[0]+sK*10, 0.0)
_, sM = hit(D, bis(D, A, C), B, C); M = (B[0]+sM*10, B[1])
per = dist(B, M) + dist(M, D) + dist(D, K) + dist(K, B)
assert round(per, 6) == 20, per
assert round(dist(B, K), 6) == 6 and round(dist(K, D), 6) == 4
print("ok  Д4: BK = 6, KD = 4, периметр 20")

# «Найди ошибку»
print("Ош1: 16x = 66 -> x =", F(66, 16), "=", float(F(66, 16)), "стороны", 3*F(66,16), 5*F(66,16))
print("Ош2: 11x = 66 -> x = 6, стороны 18 и 48, периметр", 2*(18+48))
print("Ош3: AB = 5x, 26x = 66 -> x =", F(66, 26))
