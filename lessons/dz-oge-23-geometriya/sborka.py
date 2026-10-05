"""ДЗ 9 класса, ОГЭ-2027: задание 23 (геометрическая задача на вычисление) и задание 19
(верные утверждения) по темам: подобие треугольников, равнобедренный треугольник,
касательная к окружности, признак вписанного четырёхугольника. Плюс отдельный лист Тимофею.

Один источник: условия, ответы и решения лежат здесь. Каждый ответ перед сборкой находится
заново — конфигурация строится в координатах, неизвестное ищется численно (бисекцией),
без формулы из решения; сверка через round(v, 6). Утверждения № 19: для неверных строится
контрпример, верные проверяются на случайных фигурах.

  python3 sborka.py   # проверить и собрать ZADACHI.md, OTVETY.md, *.html и три PDF
"""
from fractions import Fraction as F
import math, random, re, subprocess, pathlib

HERE = pathlib.Path(__file__).parent
CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
random.seed(2027)

# ---------------- геометрия на плоскости ----------------
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def mul(k, a): return (k * a[0], k * a[1])
def mid(a, b): return mul(.5, add(a, b))
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def crs(a, b): return a[0] * b[1] - a[1] * b[0]
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def unit(a): n = math.hypot(*a); return (a[0] / n, a[1] / n)
def perp(a): return (-a[1], a[0])
def pol(r, deg): return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))

def ang(A, V, B):
    """Угол AVB в градусах."""
    u, w = sub(A, V), sub(B, V)
    return math.degrees(math.atan2(abs(crs(u, w)), dot(u, w)))

def inter(P, d, Q, e):
    """Пересечение прямых P + t·d и Q + s·e."""
    t = crs(sub(Q, P), e) / crs(d, e)
    return add(P, mul(t, d))

def foot(P, A, B):
    d = sub(B, A)
    return add(A, mul(dot(sub(P, A), d) / dot(d, d), d))

def tri(a, b, c):
    """Треугольник ABC со сторонами BC = a, CA = b, AB = c: B = (0, 0), C = (a, 0), A сверху."""
    assert a < b + c and b < a + c and c < a + b, ('нет треугольника', a, b, c)
    x = (c * c - b * b + a * a) / (2 * a)
    return (x, math.sqrt(c * c - x * x)), (0.0, 0.0), (float(a), 0.0)

def circum(A, B, C):
    O = inter(mid(A, B), perp(sub(B, A)), mid(A, C), perp(sub(C, A)))
    return O, dist(O, A)

def orto(A, B, C):
    return inter(A, perp(sub(C, B)), B, perp(sub(C, A)))

def second(P, Q, O, r, known):
    """Вторая (кроме known) точка пересечения прямой PQ с окружностью (O, r)."""
    d = sub(Q, P); f = sub(P, O)
    a, b, c = dot(d, d), 2 * dot(f, d), dot(f, f) - r * r
    D = b * b - 4 * a * c
    assert D > 0
    pts = [add(P, mul((-b + s * math.sqrt(D)) / (2 * a), d)) for s in (1, -1)]
    pts.sort(key=lambda X: -dist(X, known))
    assert dist(pts[1], known) < 1e-7, 'known не на окружности'
    return pts[0]

def on_seg(X, A, B):
    """X лежит на отрезке AB строго внутри."""
    return abs(crs(sub(X, A), sub(B, A))) < 1e-7 * dist(A, B) ** 2 and \
        1e-9 < dot(sub(X, A), sub(B, A)) / dot(sub(B, A), sub(B, A)) < 1 - 1e-9

def acute(A, B, C): return max(ang(B, A, C), ang(A, B, C), ang(A, C, B)) < 90 - 1e-9

def convex(*P):
    s = [crs(sub(P[(i + 1) % len(P)], P[i]), sub(P[(i + 2) % len(P)], P[(i + 1) % len(P)])) for i in range(len(P))]
    return all(x > 0 for x in s) or all(x < 0 for x in s)

def root(f, lo, hi):
    a, b = f(lo), f(hi)
    assert a * b < 0, ('нет смены знака', lo, hi, a, b)
    for _ in range(200):
        m = (lo + hi) / 2
        if f(m) * a > 0: lo = m
        else: hi = m
    return (lo + hi) / 2

def one(vals):
    """Все прогоны дали одно и то же число (ответ не зависит от свободных параметров)."""
    r = {round(v, 6) for v in vals}
    assert len(r) == 1, r
    return r.pop()

# ---------------- проверки задач № 23 ----------------
def ch_bn():                                   # MN ∥ AC, MN = 12, AC = 42, NC = 25 → BN
    out = []
    for AB in (30, 40, 55):
        def f(x):
            A, B, C = tri(x + 25, 42, AB)
            N = add(B, mul(x / (x + 25), sub(C, B)))
            M = inter(N, sub(C, A), B, sub(A, B))
            return dist(M, N) - 12
        x = root(f, 1, 40)
        A, B, C = tri(x + 25, 42, AB)
        N = add(B, mul(x / (x + 25), sub(C, B))); M = inter(N, sub(C, A), B, sub(A, B))
        assert on_seg(M, A, B) and on_seg(N, B, C)
        out.append(x)
    return one(out)

def ch_mc():                                   # AB ∥ CD, AC ∩ BD = M; AB = 18, CD = 27, AC = 35 → MC
    out = []
    for th in (50, 70, 110):
        def build(y):
            C = pol(y, -th); A = mul(-(35 - y) / y, C); D = add(C, (27.0, 0.0))
            B = inter(A, (1.0, 0.0), (0.0, 0.0), D)
            return A, B, C, D
        y = root(lambda y: dist(*build(y)[:2]) - 18, 1, 34)
        A, B, C, D = build(y)
        assert on_seg((0.0, 0.0), A, C) and on_seg((0.0, 0.0), B, D)
        out.append(y)
    return one(out)

def ch_ad_common():                            # ∠ABD = ∠ACB, AB = 12, AC = 18 → AD
    out = []
    for a in (10, 15, 25):
        A, B, C = tri(a, 18, 12)
        Dt = lambda t: add(A, mul(t, sub(C, A)))
        t = root(lambda t: ang(A, B, Dt(t)) - ang(A, C, B), 1e-6, 1 - 1e-6)
        out.append(dist(A, Dt(t)))
    return one(out)

def ch_ab_right():                             # ∠B = 90°, BH — высота, AH = 4, AC = 25 → AB
    def f(c):
        A, B, C = (c, 0.0), (0.0, 0.0), (0.0, math.sqrt(625 - c * c))
        return dist(A, foot(B, A, C)) - 4
    return one([root(f, 1, 24.9)])

def ch_ac_median():                            # AO ⊥ BM, O — середина BM, AB = 7 → AC
    out = []
    for phi in (40, 75, 110):
        A, B = (0.0, 0.0), pol(7, phi)
        def f(c):
            M = (c / 2, 0.0); O = mid(B, M)
            return dot(sub(O, A), sub(M, B))
        c = root(f, 0.1, 60)
        C, M = (c, 0.0), (c / 2, 0.0)
        D = inter(A, sub(mid(B, M), A), B, sub(C, B))
        assert on_seg(D, B, C)
        out.append(c)
    return one(out)

def ch_par_bis():                              # биссектрисы A и D пересекаются на BC, AB = 11 → P
    out = []
    for al in (50, 70, 110):
        A, B = (0.0, 0.0), pol(11, al)
        def pts(d):
            D = (d, 0.0); C = add(B, D)
            E1 = inter(A, add(unit(B), (1.0, 0.0)), B, (1.0, 0.0))
            E2 = inter(D, add(unit(sub(A, D)), unit(sub(C, D))), B, (1.0, 0.0))
            return C, E1, E2
        d = root(lambda d: pts(d)[1][0] - pts(d)[2][0], 1, 80)
        C, E1, _ = pts(d)
        assert on_seg(E1, B, C)
        out.append(2 * (11 + d))
    return one(out)

def ch_trap_area():                            # равнобедр. трапеция, AD = 22, BC = 10, AC — биссектриса ∠A → S
    A, D = (0.0, 0.0), (22.0, 0.0)
    BC = lambda h: ((6.0, h), (16.0, h))
    h = root(lambda h: ang(BC(h)[0], A, BC(h)[1]) - ang(BC(h)[1], A, D), 0.1, 50)
    return one([(22 + 10) / 2 * h])

def ch_angle_c():                              # медиана BM = AM, ∠A = 37° → ∠C
    A, M, C = (0.0, 0.0), (1.0, 0.0), (2.0, 0.0)
    t = root(lambda t: dist(pol(t, 37), M) - 1, 0.1, 3)
    return one([ang(pol(t, 37), C, A)])

def ch_ad_tangent():                           # AB = 24 касается в B, r = 7, D = AO ∩ окр. → AD
    O, B = (0.0, 0.0), (7.0, 0.0)
    A = (7.0, 24.0)                            # AB ⊥ OB: касательная
    assert abs(dot(sub(A, B), sub(B, O))) < 1e-12
    D = second(A, O, O, 7, (-7 * A[0] / dist(A, O), -7 * A[1] / dist(A, O)))  # ближняя к A точка
    assert on_seg(D, A, O)
    return one([dist(A, D)])

def ch_abo():                                  # касательные в A и B, ∠AMB = 64° → ∠ABO
    out = []
    for th in (0, 35, 200):
        O = (0.0, 0.0)
        def pts(beta):
            A, B = pol(1, th), pol(1, th + beta)
            return A, B, inter(A, perp(A), B, perp(B))
        beta = root(lambda b: ang(pts(b)[0], pts(b)[2], pts(b)[1]) - 64, 1, 179)
        A, B, M = pts(beta)
        out.append(ang(A, B, O))
    return one(out)

def tangent_len(AB, BC):                       # касательная и секущая: AB, BC → AK, по координатам
    out = []
    for R in (BC / 2 + 0.5, BC, 3 * BC):
        h = math.sqrt(R * R - (BC / 2) ** 2)
        B, C, A, O = (-BC / 2, h), (BC / 2, h), (-BC / 2 - AB, h), (0.0, 0.0)
        assert abs(dist(B, O) - R) < 1e-9 and abs(dist(C, O) - R) < 1e-9
        AK = math.sqrt(dist(A, O) ** 2 - R * R)            # OK ⊥ AK
        K = add(O, pol(R, math.degrees(math.atan2(A[1], A[0]) + math.acos(R / dist(A, O)))))
        assert abs(dist(A, K) - AK) < 1e-9 and abs(dot(sub(K, O), sub(A, K))) < 1e-9
        out.append(AK)
    return one(out)

def ch_diam():                                 # центр на AC, проходит через C, касается AB в B; AB = 12, AC = 18
    A, C = (0.0, 0.0), (18.0, 0.0)
    def B_of(r):                               # точка касания касательной из A
        O = (18 - r, 0.0)
        return add(O, pol(r, 180 - math.degrees(math.acos(r / dist(A, O))))), O
    r = root(lambda r: dist(A, B_of(r)[0]) - 12, 0.1, 8.9)
    B, O = B_of(r)
    assert abs(dot(sub(B, O), sub(A, B))) < 1e-9 and abs(B[1]) > 1
    return one([2 * r])

def ch_heights_c():                            # высоты AA₁, BB₁, ∠AHB = 124° → ∠C
    out = []
    for a, b in ((5, 6), (7, 6), (6, 6)):
        C = (0.0, 0.0)
        pts = lambda g: (pol(b, g), (float(a), 0.0))
        g = root(lambda g: ang(pts(g)[0], orto(*pts(g), C), pts(g)[1]) - 124, 45, 89)
        A, B = pts(g)
        assert acute(A, B, C)
        out.append(g)
    return one(out)

def secant_chord(a, b, c, AK):                 # окр. через B, C; K на AB (AK дано), P на AC → KP
    A, B, C = tri(a, b, c)
    K = add(A, mul(AK / c, sub(B, A)))
    O, r = circum(B, C, K)
    P = second(A, C, O, r, C)
    assert on_seg(K, A, B) and on_seg(P, A, C)
    return dist(K, P)

def ch_kp():
    return one([secant_chord(20, 15, c, 6) for c in (12, 18, 25, 30)])

def ch_ca1b1():                                # высоты AA₁, BB₁, ∠A = 64° → ∠CA₁B₁
    out = []
    for b, c in ((5, 6), (6, 5), (7, 6.5)):
        A, B, C = (0.0, 0.0), (float(c), 0.0), pol(b, 64)
        assert acute(A, B, C)
        A1, B1 = foot(A, B, C), foot(B, A, C)
        out.append(ang(C, A1, B1))
    return one(out)

def ch_abd():                                  # ∠ABC = 112°, ∠ADC = 68°, ∠CAD = 29° → ∠ABD
    A, C = (0.0, 0.0), (1.0, 0.0)
    D = inter(A, pol(1, -29), C, pol(1, 180 + 83))     # ∠ACD = 180 − 68 − 29
    assert abs(ang(A, D, C) - 68) < 1e-9
    out = []
    for phi in (10, 30, 50):
        t = root(lambda t: ang(A, pol(t, phi), C) - 112, 0.01, 0.99)
        B = pol(t, phi)
        assert convex(A, B, C, D)
        out.append(ang(A, B, D))
    return one(out)

def ch_bk():                                   # окр. через A, C; K на AB, M на BC; BM = 8, MC = 10, AB = 24 → BK
    out = []
    for b in (10, 20, 30, 40):
        A, B, C = tri(18, b, 24)
        M = (8.0, 0.0)
        O, r = circum(A, C, M)
        K = second(B, A, O, r, A)
        assert on_seg(K, B, A) and on_seg(M, B, C)
        out.append(dist(B, K))
    return one(out)

def ch_err_kp():
    right = one([secant_chord(12, 8, 10, 4)])
    assert right != round(12 * 4 / 10, 6)            # «решение ученика» действительно неверно
    return right

def ch_err_ak():
    right = tangent_len(4, 5)
    assert right != round(math.sqrt(4 * 5), 6)
    return right

# ---------------- проверки задач Тимофея ----------------
def ch_cd():                                   # AB = 8, AC = 32, O — центр опис. окр., BD ⊥ AO → CD
    out = []
    for a in (26, 30, 35, 39):                 # среди них и тупоугольные треугольники
        A, B, C = tri(a, 32, 8)
        O, _ = circum(A, B, C)
        D = inter(B, perp(sub(O, A)), A, sub(C, A))
        assert on_seg(D, A, C)
        out.append(dist(C, D))
    return one(out)

def ch_two_circles():                          # R = 9, r = 4, касаются внешне в K; общая касательная AB
    A = (0.0, 0.0); O1 = (0.0, 9.0)
    x = root(lambda x: dist(O1, (x, 4.0)) - 13, 0.1, 100)
    O2, B = (x, 4.0), (x, 0.0)
    K = add(O1, mul(9 / 13, sub(O2, O1)))
    assert abs(dist(K, O2) - 4) < 1e-9
    return one([dist(A, B)]), one([ang(A, K, B)])

def ch_proof():                                # ∠HA₁B₁ = ∠HCB₁ на случайных остроугольных
    n = 0
    while n < 200:
        A, B, C = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(3)]
        if not acute(A, B, C) or abs(crs(sub(B, A), sub(C, A))) < 1: continue
        H = orto(A, B, C); A1, B1 = foot(A, B, C), foot(B, A, C)
        assert abs(ang(H, A1, B1) - ang(H, C, B1)) < 1e-7
        n += 1
    return True

# ---------------- утверждения № 19: контрпример или проверка на случайных ----------------
def rnd_tri():
    while True:
        a, b, c = (random.uniform(1, 10) for _ in range(3))
        if a < b + c and b < a + c and c < a + b and min(a + b - c, a + c - b, b + c - a) > .3:
            return tri(a, b, c)

def angles(A, B, C): return ang(B, A, C), ang(A, B, C), ang(A, C, B)
def sides(A, B, C): return dist(B, C), dist(C, A), dist(A, B)
def similar(T1, T2):
    s1, s2 = sorted(sides(*T1)), sorted(sides(*T2))
    return len({round(x / y, 6) for x, y in zip(s1, s2)}) == 1
def cyclic(A, B, C, D):
    O, r = circum(A, B, C)
    return abs(dist(O, D) - r) < 1e-7
def many(test, n=200): return all(test() for _ in range(n))

def s_two_angles():                            # два угла равны → подобны
    def t():
        T = rnd_tri(); al, be, _ = angles(*T); k = random.uniform(.2, 5)
        A2, B2 = (0.0, 0.0), (k * dist(T[0], T[1]) * random.uniform(.5, 2), 0.0)
        C2 = inter(A2, pol(1, al), B2, pol(1, 180 - be))
        return similar(T, (A2, B2, C2))
    return many(t)

def s_any_right_similar():                     # любые два прямоугольных подобны — контрпример
    return similar(((0., 0.), (3., 0.), (0., 4.)), ((0., 0.), (1., 0.), (0., 1.)))

def s_tangent_perp():                          # касательная ⊥ радиусу: прямая через K ⊥ OK — одна общая точка
    def t():
        r = random.uniform(1, 5); K = pol(r, random.uniform(0, 360)); d = perp(K)
        X = add(K, mul(random.uniform(.01, 5) * random.choice((1, -1)), d))
        return dist(X, (0., 0.)) > r                     # любая другая точка прямой вне круга
    return many(t)

def s_rhombus_cyclic():                        # ромб с углом 60° не вписан
    A, B, D = (0., 0.), pol(1, 60), (1., 0.)
    return cyclic(A, B, add(B, D), D)

def s_isosceles_base():                        # углы при основании равны
    def t():
        a, h = random.uniform(1, 5), random.uniform(.5, 8)
        A, B, C = (-a, 0.), (0., h), (a, 0.)
        return abs(ang(B, A, C) - ang(A, C, B)) < 1e-9
    return many(t)

def s_area_ratio_k():                          # площади относятся как k? при k = 2 площади ×4
    S = lambda A, B, C: abs(crs(sub(B, A), sub(C, A))) / 2
    T = ((0., 0.), (4., 0.), (1., 3.)); T2 = tuple(mul(2, X) for X in T)
    return S(*T2) / S(*T) == 2

def s_dist_less_tangent():                     # d < r → касается? прямая y = d и окружность x² + y² = r²
    r, d = 5.0, 3.0
    common = {round(x, 9) for x in (math.sqrt(r * r - d * d), -math.sqrt(r * r - d * d))}
    return len(common) == 1                    # «касается» = ровно одна общая точка; здесь две

def s_opposite_180():                          # A + C = 180° → вписан
    def t():
        A, C = (-1., 0.), (1., 0.)
        B = pol(random.uniform(.3, 3), random.uniform(20, 160))
        b = ang(A, B, C)
        # D по другую сторону AC, ∠ADC = 180 − ∠ABC, ∠DAC произвольный допустимый
        da = random.uniform(1, 179 - (180 - b) - 1)
        D = inter(A, pol(1, -da), C, pol(1, 180 + (180 - (180 - b) - da)))
        assert abs(ang(A, D, C) + b - 180) < 1e-7
        return cyclic(A, B, C, D)
    return many(t)

def s_equilateral_similar():
    def t():
        k = random.uniform(.1, 10)
        return similar(((0., 0.), (1., 0.), pol(1, 60)), ((0., 0.), (k, 0.), pol(k, 60)))
    return many(t)

def s_median_to_leg_is_height():               # медиана к боковой стороне — высота? контрпример
    A, B, C = (-1., 0.), (0., 3.), (1., 0.)    # AB = BC, медиана из A к BC
    M = mid(B, C)
    return abs(dot(sub(M, A), sub(C, B))) < 1e-9

def s_tangent_segments():
    def t():
        r = random.uniform(1, 3); P = pol(random.uniform(r + .1, 10), random.uniform(0, 360))
        a = math.degrees(math.acos(r / dist(P, (0., 0.)))); base = math.degrees(math.atan2(P[1], P[0]))
        K1, K2 = pol(r, base + a), pol(r, base - a)
        assert abs(dot(K1, sub(P, K1))) < 1e-9 and abs(dot(K2, sub(P, K2))) < 1e-9
        return abs(dist(P, K1) - dist(P, K2)) < 1e-9
    return many(t)

def s_any_trapezoid_cyclic():                  # неравнобедренная трапеция не вписана
    return cyclic((0., 0.), (1., 2.), (4., 2.), (7., 0.))

def s_median_height_isosceles():               # медиана = высота → равнобедренный
    def t():
        A, C = (-random.uniform(.5, 5), 0.), (0., 0.)
        C = (-A[0], 0.)
        M = mid(A, C); B = add(M, (0., random.uniform(.5, 8)))   # высота из B через середину AC
        return abs(dist(B, A) - dist(B, C)) < 1e-9
    return many(t)

def s_equal_side_sums_cyclic():                # суммы противолежащих сторон равны → вписан? ромб — нет
    A, B, D = (0., 0.), pol(1, 60), (1., 0.); C = add(B, D)
    assert abs((dist(A, B) + dist(C, D)) - (dist(B, C) + dist(D, A))) < 1e-12
    return cyclic(A, B, C, D)

def s_inscribed_opposite_equal():              # во вписанном противолежащие углы равны? нет
    A, B, C, D = pol(1, 0), pol(1, 50), pol(1, 160), pol(1, 250)
    assert cyclic(A, B, C, D)
    return abs(ang(D, A, B) - ang(B, C, D)) < 1e-9

def s_two_tangents():                          # из внешней точки ровно две касательные
    def t():
        r = random.uniform(1, 3); d = random.uniform(r + .05, 10)
        # прямая через P = (d, 0) под углом φ касается, если расстояние от O до неё равно r: d·|sin φ| = r
        # на [0°, 180°) это ровно два значения φ
        n = sum(1 for k in range(180000) if (d * abs(math.sin(math.radians(k / 1000))) - r) *
                (d * abs(math.sin(math.radians((k + 1) / 1000))) - r) <= 0)
        return n == 2
    return many(t, 5)

def s_perimeter_ratio():
    def t():
        T = rnd_tri(); k = random.uniform(.2, 5); T2 = tuple(mul(k, X) for X in T)
        return abs(sum(sides(*T2)) / sum(sides(*T)) - k) < 1e-9
    return many(t)

def s_isosceles_acute():                       # любой равнобедренный остроугольный? 30–30–120 — нет
    return acute((-1., 0.), (0., math.tan(math.radians(30))), (1., 0.))

def s_touching_sum():                          # касание — всегда сумма радиусов? внутреннее касание: разность
    R, r = 5.0, 2.0
    O1, O2 = (0., 0.), (3., 0.)                # окружности касаются в точке (5, 0)
    assert abs(dist(O1, (5., 0.)) - R) < 1e-12 and abs(dist(O2, (5., 0.)) - r) < 1e-12
    return dist(O1, O2) == R + r

def s_two_sides_prop():                        # две стороны пропорциональны → подобны? нет
    return similar(tri(4, 3, 3), tri(5, 3, 3))  # стороны 3, 3 у обоих, третьи разные

def s_rectangle_cyclic():
    def t():
        a, b = random.uniform(.5, 5), random.uniform(.5, 5)
        return cyclic((0., 0.), (a, 0.), (a, b), (0., b))
    return many(t)

def s_median_half_right():
    def t():
        M = (0., 0.); m = random.uniform(.5, 5)
        A, C = (-m, 0.), (m, 0.); B = pol(m, random.uniform(1, 179))
        return abs(ang(A, B, C) - 90) < 1e-9
    return many(t)

def s_center_on_bisector():
    def t():
        al = random.uniform(10, 170); r = random.uniform(.5, 3); u = pol(1, al)
        # центр окружности радиуса r, касающейся сторон угла (лучи 0° и al°): на расстоянии r
        # от обеих прямых внутри угла — пересечение двух сдвинутых внутрь прямых
        n = (math.sin(math.radians(al)), -math.cos(math.radians(al)))   # внутренняя нормаль ко второй стороне
        O = inter((0., r), (1., 0.), mul(r, n), u)
        return abs(ang((1., 0.), (0., 0.), O) - al / 2) < 1e-7
    return many(t)

def s_altitude_right_similar():
    def t():
        A, B = (random.uniform(1, 5), 0.), (0., 0.); C = (0., random.uniform(1, 5))
        H = foot(B, A, C)
        return similar((A, B, C), (A, H, B)) and similar((A, B, C), (C, H, B))
    return many(t)

def s_bisector_base_median():                  # биссектриса угла при основании — медиана? нет
    A, B, C = (-1., 0.), (0., 3.), (1., 0.)
    d = add(unit(sub(B, A)), unit(sub(C, A)))
    L = inter(A, d, B, sub(C, B))
    return abs(dist(B, L) - dist(L, C)) < 1e-9

S19 = [
    ('Какие из следующих утверждений верны?', [
        ('Если два угла одного треугольника соответственно равны двум углам другого треугольника, '
         'то такие треугольники подобны.', s_two_angles),
        ('Любые два прямоугольных треугольника подобны.', s_any_right_similar),
        ('Касательная к окружности перпендикулярна радиусу, проведённому в точку касания.', s_tangent_perp)]),
    ('Какое из следующих утверждений верно?', [
        ('Около любого ромба можно описать окружность.', s_rhombus_cyclic),
        ('В равнобедренном треугольнике углы при основании равны.', s_isosceles_base),
        ('Отношение площадей подобных треугольников равно коэффициенту подобия.', s_area_ratio_k)]),
    ('Какие из следующих утверждений верны?', [
        ('Если расстояние от центра окружности до прямой меньше радиуса окружности, '
         'то прямая касается окружности.', s_dist_less_tangent),
        ('Если сумма двух противолежащих углов четырёхугольника равна 180°, '
         'то около него можно описать окружность.', s_opposite_180),
        ('Любые два равносторонних треугольника подобны.', s_equilateral_similar)]),
    ('Какие из следующих утверждений верны?', [
        ('Если медиана треугольника является его высотой, то этот треугольник равнобедренный.', s_median_height_isosceles),
        ('Отрезки касательных, проведённых к окружности из одной точки, равны.', s_tangent_segments),
        ('Около любой трапеции можно описать окружность.', s_any_trapezoid_cyclic)]),
    ('Какое из следующих утверждений верно?', [
        ('Если в четырёхугольнике суммы противолежащих сторон равны, '
         'то около него можно описать окружность.', s_equal_side_sums_cyclic),
        ('Во вписанном четырёхугольнике противолежащие углы равны.', s_inscribed_opposite_equal),
        ('Через точку, лежащую вне окружности, можно провести ровно две касательные к этой окружности.', s_two_tangents)]),
    ('Какие из следующих утверждений верны?', [
        ('Отношение периметров подобных треугольников равно коэффициенту подобия.', s_perimeter_ratio),
        ('Любой равнобедренный треугольник является остроугольным.', s_isosceles_acute),
        ('Если две окружности касаются, то расстояние между их центрами равно сумме их радиусов.', s_touching_sum)]),
    ('Какие из следующих утверждений верны?', [
        ('Если две стороны одного треугольника пропорциональны двум сторонам другого треугольника, '
         'то такие треугольники подобны.', s_two_sides_prop),
        ('Около любого прямоугольника можно описать окружность.', s_rectangle_cyclic),
        ('Если в треугольнике медиана равна половине стороны, к которой она проведена, '
         'то этот треугольник прямоугольный.', s_median_half_right)]),
    ('Какие из следующих утверждений верны?', [
        ('Центр окружности, вписанной в угол, лежит на биссектрисе этого угла.', s_center_on_bisector),
        ('Высота прямоугольного треугольника, проведённая из вершины прямого угла, '
         'делит его на два треугольника, подобных исходному.', s_altitude_right_similar),
        ('Биссектриса угла при основании равнобедренного треугольника является его медианой.', s_bisector_base_median)]),
]

# пояснения к утверждениям № 19 для учителя: почему неверно (по номеру задания и утверждения)
WHY19 = {
    (1, 2): 'углы прямоугольных треугольников 3–4–5 и 1–1–√2 разные',
    (2, 1): 'у ромба с углом 60° противолежащие углы 60° и 120°, сумма не 180°',
    (2, 3): 'площади относятся как k², а не как k',
    (3, 1): 'при d < r у прямой и окружности две общие точки — это секущая',
    (4, 3): 'описать окружность можно только около равнобедренной трапеции',
    (5, 1): 'это признак описанного четырёхугольника (в него можно вписать окружность), а не вписанного; ромб — контрпример',
    (5, 2): 'противолежащие углы в сумме дают 180°, равны они только у прямоугольника',
    (6, 2): 'равнобедренный треугольник с углами 30°, 30°, 120° тупоугольный',
    (6, 3): 'при внутреннем касании расстояние равно разности радиусов',
    (7, 1): 'нужно ещё равенство углов между этими сторонами; треугольники 3, 3, 4 и 3, 3, 5',
    (8, 3): 'биссектриса угла при основании совпадает с медианой только в равностороннем треугольнике',
}

# ---------------- условия, ответы, решения ----------------
SECTIONS = [
    ('Подобие треугольников', [
        dict(t='Прямая пересекает стороны AB и BC треугольника ABC в точках M и N соответственно и '
               'параллельна стороне AC. Найдите BN, если MN = 12, AC = 42, NC = 25.',
             a=10, u='', ch=ch_bn,
             s='△MBN ∼ △ABC: ∠B общий, ∠BMN = ∠BAC (соответственные при MN ∥ AC). '
               'k = MN : AC = 12 : 42 = 2 : 7, значит, BN : BC = 2 : 7. '
               'BC = BN + 25, поэтому 7·BN = 2·(BN + 25), BN = 10.'),
        dict(t='Отрезки AB и CD лежат на параллельных прямых, а отрезки AC и BD пересекаются в точке M. '
               'Найдите MC, если AB = 18, CD = 27, AC = 35.',
             a=21, u='', ch=ch_mc,
             s='△AMB ∼ △CMD: углы при M вертикальные, ∠BAM = ∠DCM (накрест лежащие при AB ∥ CD). '
               'AM : MC = AB : CD = 2 : 3, MC = 3/5 · 35 = 21.'),
        dict(t='На стороне AC треугольника ABC отмечена точка D так, что ∠ABD = ∠ACB. '
               'Найдите AD, если AB = 12, AC = 18.',
             a=8, u='', ch=ch_ad_common,
             s='△ABD ∼ △ACB: ∠A общий, ∠ABD = ∠ACB. Соответствие вершин A→A, B→C, D→B, '
               'поэтому AB : AC = AD : AB, AD = AB² : AC = 144 : 18 = 8.'),
        dict(t='В прямоугольном треугольнике ABC с прямым углом B проведена высота BH. '
               'Найдите катет AB, если AH = 4, AC = 25.',
             a=10, u='', ch=ch_ab_right,
             s='△AHB ∼ △ABC: ∠A общий, ∠AHB = ∠ABC = 90°. AH : AB = AB : AC, '
               'AB² = AH · AC = 4 · 25 = 100, AB = 10.'),
    ]),
    ('Равнобедренный треугольник', [
        dict(t='В треугольнике ABC проведена медиана BM. Прямая, проходящая через вершину A '
               'перпендикулярно BM, делит медиану BM пополам. Найдите AC, если AB = 7.',
             a=14, u='', ch=ch_ac_median,
             s='Пусть O — середина BM. В △ABM отрезок AO — и высота, и медиана, значит, △ABM '
               'равнобедренный: AM = AB = 7. M — середина AC, AC = 2 · 7 = 14.'),
        dict(t='Биссектрисы углов A и D параллелограмма ABCD пересекаются в точке K, лежащей на стороне BC. '
               'Найдите периметр параллелограмма, если AB = 11.',
             a=66, u='', ch=ch_par_bis,
             s='∠BKA = ∠KAD (накрест лежащие при BC ∥ AD) = ∠BAK, значит, △ABK равнобедренный, '
               'BK = AB = 11. Так же △DCK: CK = CD = 11. BC = 22, P = 2 · (11 + 22) = 66.'),
        dict(t='В равнобедренной трапеции ABCD с основаниями AD = 22 и BC = 10 диагональ AC является '
               'биссектрисой угла BAD. Найдите площадь трапеции.',
             a=128, u='', ch=ch_trap_area,
             s='∠BCA = ∠CAD (накрест лежащие) = ∠BAC, значит, △ABC равнобедренный: AB = BC = 10. '
               'Высота из B отсекает от AD отрезок (22 − 10) : 2 = 6, h = √(10² − 6²) = 8. '
               'S = (22 + 10) : 2 · 8 = 128.'),
        dict(t='В треугольнике ABC проведена медиана BM, причём BM = AM. '
               'Найдите угол C, если ∠A = 37°.',
             a=53, u='°', ch=ch_angle_c,
             s='AM = BM = MC, поэтому △ABM и △CBM равнобедренные: ∠ABM = ∠A, ∠CBM = ∠C. '
               'Значит, ∠B = ∠A + ∠C, а сумма углов 2∠B = 180°, ∠B = 90°, ∠C = 90° − 37° = 53°.'),
    ]),
    ('Касательная к окружности', [
        dict(t='Из точки A проведена касательная AB к окружности с центром O (B — точка касания). '
               'Радиус окружности равен 7, AB = 24. Отрезок AO пересекает окружность в точке D. Найдите AD.',
             a=18, u='', ch=ch_ad_tangent,
             s='OB ⊥ AB (радиус в точку касания). AO = √(24² + 7²) = 25. AD = AO − OD = 25 − 7 = 18.'),
        dict(t='Касательные к окружности с центром O, проведённые в точках A и B, пересекаются в точке M, '
               'причём ∠AMB = 64°. Найдите угол ABO.',
             a=32, u='°', ch=ch_abo,
             s='OA ⊥ MA, OB ⊥ MB, поэтому в четырёхугольнике OAMB ∠AOB = 360° − 90° − 90° − 64° = 116°. '
               '△AOB равнобедренный (OA = OB), ∠ABO = (180° − 116°) : 2 = 32°.'),
        dict(t='Через точку A, лежащую вне окружности, проведены касательная AK (K — точка касания) и прямая, '
               'пересекающая окружность в точках B и C, причём B лежит между A и C. '
               'Найдите AK, если AB = 5, BC = 15.',
             a=10, u='', ch=lambda: tangent_len(5, 15),
             s='AC = AB + BC = 20. По теореме о касательной и секущей AK² = AB · AC = 5 · 20 = 100, AK = 10. '
               '(Доказательство теоремы — подобие △AKB ∼ △ACK: ∠A общий, ∠AKB = ∠ACK.)'),
        dict(t='Окружность с центром на стороне AC треугольника ABC проходит через вершину C и касается '
               'прямой AB в точке B. Найдите диаметр окружности, если AB = 12, AC = 18.',
             a=10, u='', ch=ch_diam,
             s='Пусть r — радиус, O — центр. OC = r, AO = 18 − r, OB = r и OB ⊥ AB. '
               'По теореме Пифагора (18 − r)² = 12² + r², 324 − 36r = 144, r = 5, диаметр 10. '
               '(Или: AB² = AD · AC, где D — вторая точка на AC, AD = 8, CD = 10.)'),
    ]),
    ('Вписанный четырёхугольник', [
        dict(t='Высоты AA₁ и BB₁ остроугольного треугольника ABC пересекаются в точке H. '
               'Найдите угол ACB, если ∠AHB = 124°.',
             a=56, u='°', ch=ch_heights_c,
             s='∠A₁HB₁ = ∠AHB = 124° (вертикальные). В четырёхугольнике CA₁HB₁ углы при A₁ и B₁ прямые, '
               'их сумма 180°, значит, он вписанный и ∠C + ∠A₁HB₁ = 180°. ∠C = 56°. '
               '(Можно и через сумму углов четырёхугольника 360°.)'),
        dict(t='Окружность проходит через вершины B и C треугольника ABC и пересекает стороны AB и AC '
               'в точках K и P соответственно. Найдите KP, если AK = 6, AC = 15, BC = 20.',
             a=8, u='', ch=ch_kp,
             s='BKPC вписан, ∠BKP + ∠BCP = 180°, поэтому ∠AKP = 180° − ∠BKP = ∠ACB. '
               '△AKP ∼ △ACB (∠A общий): K→C, P→B. KP : CB = AK : AC, KP = 20 · 6 : 15 = 8.'),
        dict(t='В остроугольном треугольнике ABC проведены высоты AA₁ и BB₁. '
               'Найдите угол CA₁B₁, если ∠BAC = 64°.',
             a=64, u='°', ch=ch_ca1b1,
             s='∠AA₁B = ∠AB₁B = 90°: из A₁ и B₁ отрезок AB виден под прямым углом, точки A, B, A₁, B₁ '
               'лежат на окружности с диаметром AB. В вписанном ABA₁B₁ ∠BA₁B₁ + ∠BAB₁ = 180°, '
               'поэтому ∠CA₁B₁ = 180° − ∠BA₁B₁ = ∠BAC = 64°. '
               '(Другой путь: CA₁ = AC·cos C, CB₁ = BC·cos C, △CA₁B₁ ∼ △CAB.)'),
        dict(t='В выпуклом четырёхугольнике ABCD углы ABC и ADC равны 112° и 68° соответственно, а ∠CAD = 29°. '
               'Найдите угол ABD.',
             a=83, u='°', ch=ch_abd,
             s='112° + 68° = 180° — около ABCD можно описать окружность. ∠ABD и ∠ACD опираются на одну '
               'дугу AD: ∠ABD = ∠ACD = 180° − 68° − 29° = 83°. '
               '(Или ∠CBD = ∠CAD = 29°, ∠ABD = 112° − 29° = 83°.)'),
        dict(t='Окружность, проходящая через вершины A и C треугольника ABC, пересекает стороны AB и BC '
               'в точках K и M соответственно. Найдите BK, если BM = 8, MC = 10, AB = 24.',
             a=6, u='', ch=ch_bk,
             s='AKMC вписан, ∠BKM = 180° − ∠AKM = ∠ACM. △BKM ∼ △BCA (∠B общий): K→C, M→A. '
               'BK : BC = BM : BA, BC = 8 + 10 = 18, BK = 8 · 18 : 24 = 6.'),
    ]),
    ('Найдите ошибку', [
        dict(t='Задача: «Окружность проходит через вершины B и C треугольника ABC и пересекает стороны AB и AC '
               'в точках K и P. Найдите KP, если AK = 4, AB = 10, AC = 8, BC = 12».',
             wrong='Четырёхугольник BKPC вписан в окружность, значит, △AKP ∼ △ABC. '
                   'Тогда KP : BC = AK : AB, KP = 12 · 4 : 10 = 4,8. Ответ: 4,8.',
             a=6, u='', ch=ch_err_kp,
             s='Ошибка — соответствие вершин. Из вписанности ∠AKP = ∠ACB, то есть K соответствует C, а не B: '
               '△AKP ∼ △ACB, KP : CB = AK : AC = 4 : 8, KP = 6. '
               'Как поймать: при «△AKP ∼ △ABC» вышло бы KP ∥ BC, а трапеция BKPC вписана только если '
               'она равнобедренная, то есть AB = AC — здесь 10 ≠ 8.'),
        dict(t='Задача: «Из точки A проведены касательная AK и прямая, пересекающая окружность в точках B и C '
               '(B между A и C). Найдите AK, если AB = 4, BC = 5».',
             wrong='По теореме о касательной и секущей AK² = AB · BC = 4 · 5 = 20, AK = 2√5. Ответ: 2√5.',
             a=6, u='', ch=ch_err_ak,
             s='В теореме — вся секущая: AK² = AB · AC, AC = 4 + 5 = 9, AK² = 36, AK = 6. '
               'Подсказка-проверка: в № 23 ответ обычно «хороший», 2√5 — повод перепроверить.'),
    ]),
]

TIMOFEY = [
    dict(t='В треугольнике ABC стороны AB = 8 и AC = 32, точка O — центр окружности, описанной около него. '
           'Прямая, проходящая через вершину B перпендикулярно AO, пересекает сторону AC в точке D. Найдите CD.',
         a=30, u='', ch=ch_cd,
         s='Касательная к описанной окружности в точке A перпендикулярна AO, значит, BD ей параллельна. '
           'Угол между касательной и хордой AB равен вписанному ∠ACB, а он равен ∠ABD (накрест лежащие). '
           '△ABD ∼ △ACB (∠A общий): AB² = AD · AC, AD = 64 : 32 = 2, CD = 30. '
           'Без касательной: ∠OAB = 90° − ∠C (из равнобедренного △AOB и центрального угла 2∠C), '
           'тогда ∠ABD = 90° − ∠OAB = ∠C. Скрипт проверил и тупоугольные треугольники.'),
    dict(t='Окружности радиусов 9 и 4 касаются внешним образом в точке K. Прямая касается первой окружности '
           'в точке A, а второй — в точке B. Найдите AB и угол AKB.',
         a=12, a2=90, u='', ch=ch_two_circles,
         s='Через K проведём общую касательную, она пересечёт AB в точке M. Отрезки касательных из M равны: '
           'MA = MK = MB, поэтому в △AKB медиана KM равна половине AB, и ∠AKB = 90°. '
           'Длина: O₁A ⊥ AB, O₂B ⊥ AB, O₁O₂ = 9 + 4 = 13; опустим из O₂ перпендикуляр на O₁A: '
           'катеты 9 − 4 = 5 и AB, гипотенуза 13, AB = 12 (в общем виде AB = 2√(Rr)).'),
    dict(t='Высоты AA₁ и BB₁ остроугольного треугольника ABC пересекаются в точке H. '
           'Докажите, что ∠HA₁B₁\u00a0=\u00a0∠HCB₁.',
         a=None, u='', ch=ch_proof,
         s='∠HA₁C = ∠HB₁C = 90°, их сумма 180°, поэтому около четырёхугольника CA₁HB₁ можно описать '
           'окружность (на диаметре CH). Вписанные углы HA₁B₁ и HCB₁ опираются на одну дугу HB₁, '
           'значит, равны. Это формат № 24; та же вписанность нужна в задачах 13 и 15 общего ДЗ.'),
]

# ---------------- проверка ----------------
def fmt(v):
    v = F(v).limit_denominator(1000)
    return str(v.numerator) if v.denominator == 1 else str(round(float(v), 6)).replace('.', ',')

def check_all():
    n = 0
    for _, items in SECTIONS:
        for it in items:
            got = it['ch']()
            assert got == round(float(it['a']), 6), (it['t'][:50], got, it['a'])
            n += 1
    for it in TIMOFEY:
        got = it['ch']()
        if it['a'] is None:
            assert got is True
        elif 'a2' in it:
            assert got == (round(float(it['a']), 6), round(float(it['a2']), 6)), got
        else:
            assert got == round(float(it['a']), 6), (it['t'][:50], got)
    ans19 = []
    for q, sts in S19:
        truth = [f() for _, f in sts]
        a = ''.join(str(i) for i, ok in enumerate(truth, 1) if ok)
        assert a, q
        if q.startswith('Какое'):
            assert len(a) == 1, ('в «Какое … верно?» должно быть ровно одно верное', a)
        ans19.append(a)
    for (k, j) in WHY19:                       # пояснение есть ровно у неверных
        assert str(j) not in ans19[k - 1], (k, j)
    assert sum(len(a) for a in ans19) + len(WHY19) == 3 * len(S19)
    print(f'ok: № 23 — {n} задач, Тимофею — {len(TIMOFEY)}, № 19 — {len(S19)}: {", ".join(ans19)}')
    return ans19

# ---------------- сборка ----------------
def h(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return re.sub(r'([₀-₉]+)', lambda m: '<sub>' + m.group(1).translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')) + '</sub>', s)

def ans_str(it):
    if it['a'] is None: return 'доказательство'
    if 'a2' in it: return f'AB = {fmt(it["a"])}, ∠AKB = {fmt(it["a2"])}°'
    return fmt(it['a']) + it['u']

CSS = '''@page{margin:14mm 14mm}
body{font-family:"Times New Roman","Liberation Serif",serif;font-size:13pt;line-height:1.35;color:#000;background:#fff;margin:0}
h1{font-size:15pt;margin:0 0 2pt} .sub{margin:0 0 8pt;font-size:11.5pt}
h2{font-size:13pt;margin:12pt 0 5pt;break-after:avoid} h3{font-size:12.5pt;font-style:italic;font-weight:normal;margin:8pt 0 4pt;break-after:avoid}
.note{font-size:11.5pt;margin:0 0 6pt}
ol.t{margin:0;padding-left:8mm} ol.t>li{margin:0 0 7pt;break-inside:avoid}
ol.st{list-style:none;margin:2pt 0 0;padding-left:0} ol.st li{margin:0 0 1pt}
.wrong{border-left:2px solid #000;padding:1pt 0 1pt 6pt;margin:3pt 0 0;font-style:italic}
.ans{margin:3pt 0 0;font-size:11.5pt} .ans b{font-weight:bold}
sub{font-size:.7em}
table{border-collapse:collapse;font-size:11pt;margin:4pt 0} td,th{border:1px solid #000;padding:2pt 5pt;vertical-align:top;text-align:left}
tr{break-inside:avoid}'''

def page(title, sub, body):
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{CSS}</style></head><body><h1>{title}</h1><p class="sub">{sub}</p>{body}</body></html>')

def body_main(teacher, ans19):
    out, n = [], 0
    out.append('<h2>Часть 1. Задачи с полным решением (как № 23)</h2>'
               '<p class="note">Каждую задачу оформите полностью: рисунок, решение с обоснованием каждого шага, ответ.</p>')
    for title, items in SECTIONS:
        out.append(f'<h3>{title}</h3><ol class="t" start="{n + 1}">')
        for it in items:
            n += 1
            li = h(it['t'])
            if 'wrong' in it:
                li += f'<div class="wrong">Решение ученика: {h(it["wrong"])}</div>Найдите ошибку и решите задачу верно.'
            if teacher:
                li += f'<div class="ans"><b>Ответ: {h(ans_str(it))}.</b> {h(it["s"])}</div>'
            out.append(f'<li>{li}</li>')
        out.append('</ol>')
    out.append('<h2>Часть 2. Верные утверждения (как № 19)</h2>'
               '<p class="note">В ответ запишите номера верных утверждений без пробелов, запятых и других символов.</p>'
               f'<ol class="t" start="{n + 1}">')
    for k, (q, sts) in enumerate(S19, 1):
        n += 1
        li = h(q) + '<ol class="st">' + ''.join(f'<li>{i}) {h(s)}</li>' for i, (s, _) in enumerate(sts, 1)) + '</ol>'
        if teacher:
            why = '; '.join(f'{j}) {WHY19[(k, j)]}' for j in range(1, 4) if (k, j) in WHY19)
            li += f'<div class="ans"><b>Ответ: {ans19[k - 1]}.</b> Неверны: {h(why)}.</div>'
        out.append(f'<li>{li}</li>')
    out.append('</ol>')
    return ''.join(out)

def body_timofey(teacher):
    out = ['<ol class="t">']
    for it in TIMOFEY:
        li = h(it['t'])
        if teacher:
            li += f'<div class="ans"><b>Ответ: {h(ans_str(it))}.</b> {h(it["s"])}</div>'
        out.append(f'<li>{li}</li>')
    return ''.join(out) + '</ol>'

# заметки преподавателю: одни данные -> и HTML, и Markdown
NOTES = [
    ('h', 'Где эти темы в ОГЭ-2027'),
    ('p', 'Проект демоверсии 2027 года опубликован; по открытым источникам структура и содержание КИМ '
          'по сравнению с 2026 годом не менялись: 25 заданий, часть 1 — 19 с кратким ответом, часть 2 — 6 '
          'с развёрнутым. Сайт ФИПИ из среды подготовки недоступен — при случае сверьте с демоверсией.'),
    ('t', ['№', 'Формат', 'Что из ДЗ туда идёт'], [
        ['15', 'треугольники, краткий ответ', 'подобие, равнобедренный треугольник'],
        ['16', 'окружность, краткий ответ', 'касательная, вписанный четырёхугольник'],
        ['17', 'четырёхугольники, краткий ответ', 'параллелограмм и трапеция с биссектрисой (6, 7)'],
        ['19', 'верные утверждения, краткий ответ', 'часть 2 ДЗ'],
        ['23', 'вычисление, развёрнутый ответ, 2 балла', 'часть 1 ДЗ'],
        ['24', 'доказательство, 2 балла', 'вписанность через два прямых угла (13, 15), подобие; задача Тимофея 3'],
        ['25', 'сложная задача, 2 балла', 'задачи Тимофея 1 и 2']]),
    ('p', 'Оценивание № 23: 2 балла — ход решения верный, все шаги выполнены, ответ верный; '
          '1 балл — ход верный, но неполные объяснения или одна вычислительная ошибка; иначе 0. '
          'Значит, проверять в ДЗ не только число, но и обоснования: «почему подобны», «почему вписан».'),
    ('h', 'Типовые ошибки — на что смотреть при проверке'),
    ('t', ['Ошибка', 'Откуда', 'Как поймать', 'Где в ДЗ'], [
        ['перепутано соответствие вершин в подобии', 'пишут △AKP ∼ △ABC «по порядку букв»',
         'сначала выписать пары равных углов, потом отношение сторон, лежащих против них', '3, 14, 17, 18'],
        ['AK² = AB · BC вместо AB · AC', 'помнят «произведение отрезков», но не каких',
         'вывести через подобие △AKB ∼ △ACK; некруглый ответ — сигнал', '11, 19'],
        ['видят один равнобедренный треугольник из двух', 'в № 6 находят BK = 11, но забывают CK = CD и берут BC = 11',
         'отметить на рисунке все пары равных углов и для каждой найти стороны против них', '6, 7, 8'],
        ['BC = 10 вместо 18', 'в условии даны отрезки BM и MC, а нужна вся сторона',
         'подписать на рисунке все длины до вычислений', '17'],
        ['радиус вместо диаметра', 'нашли r и записали в ответ', 'перечитать вопрос перед записью ответа', '12'],
        ['в № 19 путают вписанный и описанный четырёхугольник', 'оба признака «про суммы»',
         'вписанный — углы (180°), описанный — стороны (равные суммы)', '24'],
        ['ответ № 19 через запятую или с пробелом', 'привычка', 'в бланке только цифры: 13, а не «1, 3»', '20–27']]),
    ('p', 'Все ответы пересчитаны скриптом sborka.py: каждая конфигурация построена в координатах при нескольких '
          'значениях свободных параметров, неизвестное найдено численно, без формулы из решения. '
          'Для неверных утверждений № 19 скрипт строит контрпример.'),
]

def notes_html():
    out = ['<h2>Заметки преподавателю</h2>']
    for kind, *x in NOTES:
        if kind == 'h': out.append(f'<h3>{h(x[0])}</h3>')
        elif kind == 'p': out.append(f'<p class="note">{h(x[0])}</p>')
        else:
            head, rows = x
            out.append('<table><tr>' + ''.join(f'<th>{h(c)}</th>' for c in head) + '</tr>' +
                       ''.join('<tr>' + ''.join(f'<td>{h(c)}</td>' for c in r) + '</tr>' for r in rows) + '</table>')
    return ''.join(out)

def notes_md():
    out = ['## Заметки преподавателю', '']
    for kind, *x in NOTES:
        if kind == 'h': out += [f'### {x[0]}', '']
        elif kind == 'p': out += [x[0], '']
        else:
            head, rows = x
            out += ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
            out += ['| ' + ' | '.join(r) + ' |' for r in rows] + ['']
    return '\n'.join(out)

def pdf(html_text, out):
    tmp = HERE / '_print.html'
    tmp.write_text(html_text, encoding='utf-8')
    subprocess.run([CH, '--headless', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer',
                    '--virtual-time-budget=8000', f'--print-to-pdf={out}', f'file://{tmp}'],
                   check=True, capture_output=True)
    tmp.unlink()

SUB = 'ОГЭ, задания 23 и 19: подобие треугольников, равнобедренный треугольник, касательная к окружности, вписанный четырёхугольник'
NAME = 'ДЗ — ОГЭ 23 и 19, геометрия'

def build():
    ans19 = check_all()
    student = page('Домашнее задание', SUB, body_main(False, ans19))
    teacher = page('Домашнее задание — ответы и решения', SUB,
                   body_main(True, ans19) + '<h2>Тимофею дополнительно</h2>' + body_timofey(True) + notes_html())
    tim = page('Тимофею — задачи на подумать', 'Дополнительно к общему ДЗ. Решение оформите полностью.', body_timofey(False))
    (HERE / 'zadachi.html').write_text(student, encoding='utf-8')
    (HERE / 'timofey.html').write_text(tim, encoding='utf-8')
    (HERE / 'otvety.html').write_text(teacher, encoding='utf-8')
    for text in (student, tim):                # в версиях ученика не должно остаться ответов
        assert 'Ответ:' not in text.replace('Ответ: 4,8', '').replace('Ответ: 2√5', '') and 'class="ans"' not in text
    pdf(student, HERE / f'{NAME}.pdf')
    pdf(tim, HERE / 'ДЗ — Тимофей, задачи на подумать.pdf')
    pdf(teacher, HERE / f'{NAME} — ответы и решения.pdf')

    md = ['# Домашнее задание', '', SUB, '', '## Часть 1. Задачи с полным решением (как № 23)', '',
          'Каждую задачу оформите полностью: рисунок, решение с обоснованием каждого шага, ответ.', '']
    ot = ['# Ответы и решения (только для преподавателя)', '', 'Собрано и проверено скриптом `sborka.py`.', '',
          '## Часть 1. Задачи с полным решением (как № 23)', '']
    n = 0
    for title, items in SECTIONS:
        md += [f'### {title}', '']; ot += [f'### {title}', '']
        for it in items:
            n += 1
            md.append(f'{n}. {it["t"]}')
            if 'wrong' in it:
                md += ['', f'   > Решение ученика: {it["wrong"]}', '', '   Найдите ошибку и решите задачу верно.']
            ot.append(f'{n}. **{ans_str(it)}.** {it["s"]}')
        md.append(''); ot.append('')
    md += ['## Часть 2. Верные утверждения (как № 19)', '',
           'В ответ запишите номера верных утверждений без пробелов, запятых и других символов.', '']
    ot += ['## Часть 2. Верные утверждения (как № 19)', '']
    for k, (q, sts) in enumerate(S19, 1):
        n += 1
        md.append(f'{n}. {q}')
        md += [f'   {i}) {s}' for i, (s, _) in enumerate(sts, 1)]
        md.append('')
        why = '; '.join(f'{j}) {WHY19[(k, j)]}' for j in range(1, 4) if (k, j) in WHY19)
        ot.append(f'{n}. **{ans19[k - 1]}.** Неверны: {why}.')
    md += ['', '## Тимофею дополнительно', '']
    ot += ['', '## Тимофею дополнительно', '']
    for i, it in enumerate(TIMOFEY, 1):
        md.append(f'{i}. {it["t"]}')
        ot.append(f'{i}. **{ans_str(it)}.** {it["s"]}')
    ot += ['', notes_md()]
    (HERE / 'ZADACHI.md').write_text('\n'.join(md).rstrip() + '\n', encoding='utf-8')
    (HERE / 'OTVETY.md').write_text('\n'.join(ot).rstrip() + '\n', encoding='utf-8')
    print('собрано: ZADACHI.md, OTVETY.md, zadachi.html, timofey.html, otvety.html и три PDF')

if __name__ == '__main__':
    build()
