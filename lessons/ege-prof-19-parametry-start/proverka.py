"""Проверка всех ответов по параметрам перебором значения параметра.
Для каждого a (сетка с шагом 1/8 на [-12; 16] + граничные точки ± 1/1000) уравнение решается
точно (sympy, рациональное a), считается число различных корней и сравнивается с ответом.
Запуск: python3 proverka.py  (≈ 1–2 минуты)"""
import sympy as sp
from sympy import Rational as Q, sqrt, Abs, log, S, oo

x, y = sp.symbols('x y', real=True)

def nroots(expr, dom=S.Reals, denom=None):
    sol = sp.solveset(sp.Eq(expr, 0), x, dom)
    if isinstance(sol, sp.ConditionSet):
        raise RuntimeError(f'не решилось: {expr}')
    if denom is not None:
        sol = sol - sp.solveset(sp.Eq(denom, 0), x, S.Reals)
    if sol.is_FiniteSet:
        return len(sol)
    return oo   # интервал/бесконечное множество

def nsys(eqs):
    sols = sp.solve(eqs, [x, y], dict=True)
    real = {(sp.nsimplify(s[x]), sp.nsimplify(s[y])) for s in sols if s[x].is_real and s[y].is_real}
    return len(real)

def grid(bounds):
    pts = {Q(k, 8) for k in range(-96, 129)}
    for b in bounds:
        pts |= {b, b - Q(1, 1000), b + Q(1, 1000)}
    return sorted(pts, key=float)

def check(name, count, claim, bounds):
    """claim(a) -> True/False: входит ли a в ответ; count(a) -> число корней; вопрос задан через want(n)"""
    bad = []
    for a in grid(bounds):
        try:
            got = claim[0](count(a))
        except RuntimeError as e:
            bad.append((a, str(e))); continue
        if got != claim[1](a):
            bad.append((a, count(a)))
    print(('OK ' if not bad else 'ОШИБКА'), name, '' if not bad else bad[:6])
    return not bad


allok = True
def C(*args):
    global allok
    allok &= check(*args)

two = lambda n: n == 2; one = lambda n: n == 1; three = lambda n: n == 3; four = lambda n: n == 4
zero = lambda n: n == 0; inf = lambda n: n == oo

# ===== РАЗБОР =====
# П1. (a²−4)x = a²+a−2
f = lambda a: nroots((a**2 - 4)*x - (a**2 + a - 2))
C('П1 а) нет корней', f, (zero, lambda a: a == 2), [2, -2])
C('П1 б) бесконечно', f, (inf, lambda a: a == -2), [2, -2])
C('П1 в) единственный', f, (one, lambda a: a not in (2, -2)), [2, -2])
# П2. (a−1)x² − 2(a+1)x + a + 4 = 0 — ровно один корень
C('П2', lambda a: nroots((a - 1)*x**2 - 2*(a + 1)*x + a + 4), (one, lambda a: a in (1, 5)), [1, 5])
# П3. (x²−6x+5)√(x−a) = 0 — ровно два корня
C('П3', lambda a: nroots((x**2 - 6*x + 5)*sqrt(x - a), sp.Interval(a, oo)), (two, lambda a: 1 <= a < 5), [1, 5])
# П4. (x−a)(x−3)/(x−2) = 0 — ровно один корень
C('П4', lambda a: nroots((x - a)*(x - 3), denom=x - 2), (one, lambda a: a in (2, 3)), [2, 3])
# П5. |x²−4x+3| = a — три / четыре корня
f = lambda a: nroots(Abs(x**2 - 4*x + 3) - a)
C('П5 три', f, (three, lambda a: a == 1), [0, 1])
C('П5 четыре', f, (four, lambda a: 0 < a < 1), [0, 1])
# П6. |x−2| = ax + 1 — ровно два корня
C('П6', lambda a: nroots(Abs(x - 2) - a*x - 1), (two, lambda a: Q(-1, 2) < a < 1), [Q(-1, 2), 1, -1])
# П7. x²+y²=8, y=x+a
f = lambda a: nsys([x**2 + y**2 - 8, y - x - a])
C('П7 одно', f, (one, lambda a: a in (4, -4)), [4, -4])
C('П7 два', f, (two, lambda a: -4 < a < 4), [4, -4])
# П8. (x²−2x−a)√(x+1) = 0 — ровно два корня
C('П8', lambda a: nroots((x**2 - 2*x - a)*sqrt(x + 1), sp.Interval(-1, oo)), (two, lambda a: a == -1 or a >= 3), [-1, 3])

# ===== ЗАДАЧИ =====
f = lambda a: nroots((a**2 - 9)*x - (a + 3))
C('1.1 а) нет', f, (zero, lambda a: a == 3), [3, -3])
C('1.1 б) беск.', f, (inf, lambda a: a == -3), [3, -3])
C('1.1 в) один', f, (one, lambda a: a not in (3, -3)), [3, -3])
f = lambda a: nroots(a*(a - 1)*x - (a**2 - 1))
C('1.2 a=0 нет', f, (zero, lambda a: a == 0), [0, 1])
C('1.2 a=1 беск.', f, (inf, lambda a: a == 1), [0, 1])
# 1.2: при a≠0;1 корень x=(a+1)/a
for a in [Q(5, 2), sp.Integer(-3), Q(-1, 3)]:
    assert sp.solve(a*(a - 1)*x - (a**2 - 1), x) == [(a + 1)/a]
# 1.3 (a+1)x = 2a−1 — единственный положительный корень
def f13(a):
    s = sp.solveset(sp.Eq((a + 1)*x, 2*a - 1), x, S.Reals)
    return 1 if (s.is_FiniteSet and len(s) == 1 and list(s)[0] > 0) else 0
C('1.3', f13, (one, lambda a: a < -1 or a > Q(1, 2)), [-1, Q(1, 2)])
C('2.1', lambda a: nroots((a + 2)*x**2 + 6*x - 3), (one, lambda a: a in (-5, -2)), [-5, -2])
C('2.2', lambda a: nroots(x**2 - 2*a*x + a + 6), (two, lambda a: a < -2 or a > 3), [-2, 3])
C('2.3', lambda a: nroots((a - 3)*x**2 - 2*a*x + a + 1), (zero, lambda a: a < Q(-3, 2)), [Q(-3, 2), 3])
C('3.1', lambda a: nroots((x**2 - 7*x + 6)*sqrt(x - a), sp.Interval(a, oo)), (two, lambda a: 1 <= a < 6), [1, 6])
C('3.2', lambda a: nroots((x - a)*(x + 4), denom=x - 1), (one, lambda a: a in (-4, 1)), [-4, 1])
C('3.3', lambda a: nroots((x**2 - 9)*sqrt(a - x), sp.Interval(-oo, a)), (two, lambda a: -3 < a <= 3), [-3, 3])
C('4.1', lambda a: nroots(Abs(x**2 - 2*x - 3) - a), (four, lambda a: 0 < a < 4), [0, 4])
f = lambda a: nroots(x**2 - 4*Abs(x) + 3 - a)
C('4.2 три', f, (three, lambda a: a == 3), [-1, 3])
C('4.2 четыре', f, (four, lambda a: -1 < a < 3), [-1, 3])
f = lambda a: nroots(Abs(x + 1) + Abs(x - 3) - a)
C('4.3 два', f, (two, lambda a: a > 4), [4])
C('4.3 беск.', f, (inf, lambda a: a == 4), [4])
C('5.1', lambda a: nroots(Abs(x) - a*x - 2), (two, lambda a: -1 < a < 1), [-1, 1])
C('5.2', lambda a: nroots(Abs(x - 1) - a*(x + 1)), (two, lambda a: 0 < a < 1), [0, 1, -1])
k1, k2 = -4 - 2*sqrt(5), -4 + 2*sqrt(5)
# 5.3: иррациональные границы проверяем отдельно точно, сетку — как обычно
C('5.3', lambda a: nroots(x**2 - 4*x + 5 - a*x), (one, lambda a: False), [])
assert nroots(x**2 - 4*x + 5 - k1*x) == 1 and nroots(x**2 - 4*x + 5 - k2*x) == 1
f = lambda a: nsys([x**2 + y**2 - 18, y - x - a])
C('6.1 два', f, (two, lambda a: -6 < a < 6), [6, -6])
C('6.2 одно', lambda a: nsys([(x - 2)**2 + y**2 - 5, y - 2*x - a]), (one, lambda a: a in (1, -9)), [1, -9])
C('6.3 нет', lambda a: nsys([x**2 + y**2 - a, x + y - 2]), (zero, lambda a: a < 2), [0, 2])
C('7.1', lambda a: nroots((x**2 - 4*x - a)*sqrt(x + 2), sp.Interval(-2, oo)), (two, lambda a: a == -4 or a >= 12), [-4, 12])
def f72(a):
    sols = set(sp.solveset(sp.Eq(x**2 - 5*x + 6, 0), x, sp.Interval.open(a, oo))) | {a + 1}
    # проверка, что a+1 действительно корень log: ln(1) = 0
    return len(sols)
C('7.2', f72, (two, lambda a: a == 1 or 2 < a < 3), [1, 2, 3])
# найди ошибку — верные ответы
C('Н1', lambda a: nroots((a - 1)*x**2 + 2*x + 1), (one, lambda a: a in (1, 2)), [1, 2])
C('Н2', lambda a: nroots((x**2 - 4)*sqrt(x - a), sp.Interval(a, oo)), (two, lambda a: -2 <= a < 2), [-2, 2])
s8 = 2*sqrt(2)
C('Н3', lambda a: nsys([x**2 + y**2 - 4, y - x - a]), (two, lambda a: -s8 < a < s8), [])
print('\nвсе ответы сошлись' if allok else '\nЕСТЬ РАСХОЖДЕНИЯ')
