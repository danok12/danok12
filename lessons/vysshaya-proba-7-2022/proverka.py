"""Проверка перебором ответов отборочного этапа «Высшей пробы» 2022, 7 класс, день 1."""
from fractions import Fraction as F
from math import factorial
from itertools import product, combinations

res = {}

# 1. Квадрат со стороной a режут на 3 прямоугольника; сумма периметров = 4a + 2·(длина разрезов).
#    Разрезы: две полные параллельные (длина 2a) или полная + неполная (длина 2a − x, 0<x<a).
#    Перебираем a и x с шагом 1/100: наименьшее a, при котором сумма может быть 40.
best = None
for a100 in range(1, 3000):
    a = F(a100, 100)
    sums = {8 * a} | ({8 * a - 2 * F(x, 100) for x in range(1, a100)})
    if 40 in sums:
        best = a; break
res[1] = best

# 2. Круг из 70; left(i)=i−1, right(i)=i+1. П: левый — Л, правый — Х. Л: левый не Л, правый не Х.
#    Max Л — динамикой по кругу (фиксируем первых двоих).
T = 'ПЛХ'
def ok(l, me, r):
    if me == 'П': return l == 'Л' and r == 'Х'
    if me == 'Л': return l != 'Л' and r != 'Х'
    return True
n = 70; best = -1
for a0, a1 in product(T, T):
    dp = {(a0, a1): (a0 == 'Л') + (a1 == 'Л')}
    for i in range(2, n):
        nd = {}
        for (p, q), v in dp.items():
            for c in T:
                if i >= 2 and (i - 1 >= 1) and not ok(p, q, c): continue
                k = (q, c); nd[k] = max(nd.get(k, -1), v + (c == 'Л'))
        dp = nd
    for (p, q), v in dp.items():  # замыкание: проверяем a[n−1] и a[0]
        if ok(p, q, a0) and ok(q, a0, a1): best = max(best, v)
res[2] = best

# 3. Углы MNK = 90° − (угол ABC)/2 ⇒ угол ABC = 180 − 2·(угол MNK).
angles = sorted(180 - 2 * t for t in (44, 55, 81)); assert sum(angles) == 180
res[3] = angles[0]

# 4.
f60 = factorial(60)
res[4] = sum(1 for d in range(10, 100) if f60 % d)

# 5. Клетчатый 3×31, у каждой клетки ≤ 1 красной стороны. Динамика по столбцам.
R, C = 3, 31
def col_options(c, used_in):
    """Все способы покрасить отрезки столбца c: верх/низ границы, горизонтальные внутри столбца,
    левая граница (c=0), правая граница (c=C−1) или правые внутренние отрезки (в следующий столбец)."""
    segs = [('top', (0,)), ('bot', (R - 1,))] + [('h', (r, r + 1)) for r in range(R - 1)]
    if c == 0: segs += [('L', (r,)) for r in range(R)]
    if c == C - 1: segs += [('Rb', (r,)) for r in range(R)]
    else: segs += [('Ri', (r,)) for r in range(R)]  # занимает клетку r здесь и в следующем столбце
    for mask in range(1 << len(segs)):
        used = list(used_in); good = True; nxt = [0] * R; cnt = 0
        for j, (kind, cells) in enumerate(segs):
            if mask >> j & 1:
                cnt += 1
                for r in cells:
                    if used[r]: good = False; break
                    used[r] = 1
                if not good: break
                if kind == 'Ri': nxt[cells[0]] = 1
        if good: yield tuple(nxt), cnt
dp = {(0,) * R: 0}
for c in range(C):
    nd = {}
    for st, v in dp.items():
        for nx, cnt in col_options(c, st):
            nd[nx] = max(nd.get(nx, -1), v + cnt)
    dp = nd
res[5] = max(dp.values())

# 6. Наименьшее n, при котором гири 1..n (все) уравновешивают 57; затем max число гирь у камня.
n = 1
while True:
    s = n * (n + 1) // 2
    if s >= 57 and (s - 57) % 2 == 0: break
    n += 1
need = (s - 57) // 2  # сумма гирь на чаше с камнем
mx = 0
for k in range(1, n + 1):
    for comb in combinations(range(1, n + 1), k):
        if sum(comb) == need: mx = max(mx, k)
res[6] = (n, need, mx)

# 7. Король a1 → c8 за 7 ходов (по всем 8 направлениям, внутри доски).
ways = {(0, 0): 1}
for _ in range(7):
    nw = {}
    for (x, y), v in ways.items():
        for dx, dy in product((-1, 0, 1), repeat=2):
            if dx == dy == 0: continue
            X, Y = x + dx, y + dy
            if 0 <= X < 8 and 0 <= Y < 8: nw[(X, Y)] = nw.get((X, Y), 0) + v
    ways = nw
res[7] = ways.get((2, 7), 0)

# 8. Пары различных 1/a, 1/b (a,b ≥ 2), сумма = 1/c > 1/6.
pairs = []
for a in range(2, 200):
    for b in range(a + 1, 400):
        s = F(1, a) + F(1, b)
        if s.numerator == 1 and s > F(1, 6) and s < 1: pairs.append((a, b, s))
res[8] = (len(pairs), pairs)

# 9. 12 девушек, 4 юноши, разбить на 8 пар без пары юноша–юноша. Перебор всех разбиений.
people = ['g'] * 12 + ['b'] * 4
def count(rest):
    if not rest: return 1
    first, others = rest[0], rest[1:]
    tot = 0
    for i, p in enumerate(others):
        if people[first] == 'b' and people[p] == 'b': continue
        tot += count(others[:i] + others[i + 1:])
    return tot
res[9] = count(tuple(range(16)))

# 10. Наибольшее хроматическое число графа с 500 рёбрами: k(k−1)/2 ≤ 500.
k = 1
while (k + 1) * k // 2 <= 500: k += 1
res[10] = k

for i in range(1, 11): print(i, res[i])
