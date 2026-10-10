"""Пересчёт всех ответов двух вариантов (ЕГЭ-2027, профиль: № 1–13, 14, 16).
Точная арифметика: Fraction и sympy. Запуск: python3 proverka.py"""
from fractions import Fraction as F
import sympy as sp

x, t = sp.symbols('x t', real=True)
res = {}

def ok(key, got, want):
    if isinstance(got, str):
        res[key] = (got, want, got == want); return
    got_s = sp.nsimplify(got) if not isinstance(got, (F, int, str)) else got
    flag = sp.simplify(sp.sympify(str(got_s)) - sp.sympify(str(want))) == 0
    res[key] = (got_s, want, flag)

def roots_on(expr, lo, hi):
    """корни тригонометрического уравнения на отрезке: решаем на большом интервале и отбираем"""
    sols = sp.solveset(sp.Eq(expr, 0), x, sp.Interval(lo, hi))
    return sorted(sols, key=lambda r: float(r))

# ---------------- ВАРИАНТ 1 ----------------
# 1. ABCD вписан, ∠ABD=38, ∠CAD=54 → ∠ABC = ∠ABD + ∠DBC, ∠DBC=∠DAC
ok('В1-1', 38 + 54, 92)
# 2. a(2;-3), b(-1;4): (a+2b)·b
a = (2, -3); b = (-1, 4)
s = (a[0] + 2*b[0], a[1] + 2*b[1]); ok('В1-2', s[0]*b[0] + s[1]*b[1], 20)
# 3. вода 2000 см³ на высоте 12, поднялась на 9 → V детали
ok('В1-3', F(2000, 12) * 9, 1500)
# 4. 40 билетов, 6 с вопросом про грибы → P(нет вопроса)
ok('В1-4', F(34, 40), F(85, 100))
# 5. p=0,8; попал, попал, промах
ok('В1-5', F(8, 10)**2 * F(2, 10), F(128, 1000))
# 6. X: -2,0,1,4; p: 0,1 0,3 p 0,2 → p=0,4; EX
p = 1 - F(1, 10) - F(3, 10) - F(2, 10)
ok('В1-6', -2*F(1, 10) + 0 + 1*p + 4*F(2, 10), 1)
# 7. 2^(3-2x) = 0,125·4^x
sol = sp.solve(sp.Eq(2**(3 - 2*x), sp.Rational(1, 8) * 4**x), x); ok('В1-7', sol[0], sp.Rational(3, 2))
# 8. cos α = -√10/10, α∈(π; 3π/2) → tg α
c = -sp.sqrt(10)/10; s_ = -sp.sqrt(1 - c**2); ok('В1-8', sp.simplify(s_/c), 3)
# 9. касательная через (-4;-1) и (4;5) → f'(x0)
ok('В1-9', F(5 - (-1), 4 - (-4)), F(3, 4))
# 10. h = 1,2 + 9t - 5t², h ≥ 4,8 — сколько секунд
r = sp.solve(sp.Eq(sp.Rational(12, 10) + 9*t - 5*t**2, sp.Rational(48, 10)), t)
ok('В1-10', max(r) - min(r), sp.Rational(6, 10))
# 11. 80 км, автомобилист на 30 км/ч быстрее, на 6 ч раньше → v велосипедиста
v = sp.symbols('v', positive=True)
ok('В1-11', sp.solve(sp.Eq(80/v - 80/(v + 30), 6), v)[0], 10)
# 12. f = -0,5(x+1)²+4 по точкам (-1;4),(1;2),(-3;2),(3;-4); f(7)
A, B, C = sp.symbols('A B C')
fx = A*x**2 + B*x + C
cf = sp.solve([fx.subs(x, -1) - 4, fx.subs(x, 1) - 2, fx.subs(x, 3) + 4], [A, B, C])
assert fx.subs(cf).subs(x, -3) == 2 and fx.subs(cf).subs(x, -5) == -4
ok('В1-12', fx.subs(cf).subs(x, 7), -28)
# 13. кредит 1 260 000, 2 года, +10% в январе, два равных платежа
S, X = 1260000, sp.symbols('X')
ok('В1-13', sp.solve(sp.Eq((S*sp.Rational(11, 10) - X)*sp.Rational(11, 10) - X, 0), X)[0], 726000)
# 14. cos2x + 3√2·sin(π − x) − 3 = 0;  б) [2π; 7π/2]
e14 = sp.cos(2*x) + 3*sp.sqrt(2)*sp.sin(sp.pi - x) - 3
r14 = roots_on(e14, 2*sp.pi, sp.Rational(7, 2)*sp.pi)
ok('В1-14б', str(r14), str([sp.Rational(9, 4)*sp.pi, sp.Rational(11, 4)*sp.pi]))
# общий вид а): проверяем, что π/4 и 3π/4 — корни, а на [0;2π) других нет
ok('В1-14а', str(roots_on(e14, 0, 2*sp.pi - sp.Rational(1, 10**6))), str([sp.pi/4, 3*sp.pi/4]))
# 16. (4^x − 2^{x+2} − 4)/(2^x − 5) + (4^x − 2^{x+3} + 9)/(2^x − 7) ≤ 2^{x+1} − 1
T = sp.symbols('T', positive=True)
lhs = (T**2 - 4*T - 4)/(T - 5) + (T**2 - 8*T + 9)/(T - 7) - (2*T - 1)
solT = sp.solve_univariate_inequality(lhs <= 0, T, relational=False)
ok('В1-16 (по t=2^x)', str(solT), str(sp.Union(sp.Interval.Ropen(3, 5), sp.Interval.Ropen(6, 7))))

# ---------------- ВАРИАНТ 2 ----------------
# 1. равнобедр. трапеция: основания 9 и 21, S=120 → периметр
h = F(120) / F(9 + 21, 2); half = F(21 - 9, 2); lat = sp.sqrt(h**2 + half**2)
ok('В2-1', 9 + 21 + 2*lat, 50)
# 2. |a|=5, |b|=8, угол 120° → |a+b|
ok('В2-2', sp.sqrt(25 + 64 + 2*5*8*sp.cos(sp.Rational(2, 3)*sp.pi)), 7)
# 3. прав. 4-уг. пирамида: сторона 6, боковое ребро √34 → V
hh = sp.sqrt(34 - (3*sp.sqrt(2))**2); ok('В2-3', sp.Rational(1, 3)*36*hh, 48)
# 4. 5 + 7 + 8 докладчиков, девятым — из России
ok('В2-4', F(7, 20), F(35, 100))
# 5. дефект 6%, выявляется с p=0,9; исправная бракуется с p=0,05 → P(брак)
ok('В2-5', F(6, 100)*F(9, 10) + F(94, 100)*F(5, 100), F(101, 1000))
# 6. X: 1,2,3; p: 0,2 0,5 0,3 → DX
P = [F(2, 10), F(5, 10), F(3, 10)]; Xs = [1, 2, 3]
EX = sum(xi*pi for xi, pi in zip(Xs, P)); EX2 = sum(xi*xi*pi for xi, pi in zip(Xs, P))
ok('В2-6', EX2 - EX**2, F(49, 100))
# 7. log₇(x²+2x) = log₇(x²−12)
sol = [r for r in sp.solve(sp.Eq(x**2 + 2*x, x**2 - 12), x) if (r**2 + 2*r) > 0 and (r**2 - 12) > 0]
ok('В2-7', sol[0], -6)
# 8. log₃64 / log₃4 + 7^(log₄₉ 25)
ok('В2-8', sp.nsimplify(sp.log(64, 3)/sp.log(4, 3) + 7**(sp.log(25, 49))), 8)
# 9. f'(x) = (x+5)(x+2)(x−1)(x−4)/25 на (−5,5; 4,5); точка наибольшего значения f на [−1; 3]
fp = (x + 5)*(x + 2)*(x - 1)*(x - 4)/25
Fx = sp.integrate(fp, x)
cand = [-1, 3] + [r for r in sp.solve(fp, x) if -1 <= r <= 3]
ok('В2-9', max(cand, key=lambda q: Fx.subs(x, q)), 1)
# 10. S = 58t + 4t² ≤ 30 → наибольшее t, в минутах
r = sp.solve(sp.Eq(58*t + 4*t**2, 30), t); ok('В2-10', max(r)*60, 30)
# 11. 30% и 60% растворы + 10 кг воды → 36%; + 10 кг 50% → 41%
p1, p2 = sp.symbols('p1 p2')
sol = sp.solve([sp.Rational(3, 10)*p1 + sp.Rational(6, 10)*p2 - sp.Rational(36, 100)*(p1 + p2 + 10),
                sp.Rational(3, 10)*p1 + sp.Rational(6, 10)*p2 + 5 - sp.Rational(41, 100)*(p1 + p2 + 10)], [p1, p2])
ok('В2-11', sol[p1], 60)
# 12. прямые y=2/3x+3 и y=1/2x+1 → абсцисса пересечения
ok('В2-12', sp.solve(sp.Eq(sp.Rational(2, 3)*x + 3, sp.Rational(1, 2)*x + 1), x)[0], -12)
# 13. дифференцированный кредит, 10 мес, 2%, выплаты 1 110 000 → сумма кредита
Ssym = sp.symbols('S'); n = 10; r_ = sp.Rational(2, 100)
debts = [Ssym*(n - k)/n for k in range(n + 1)]
total = sum(debts[k]*(1 + r_) - debts[k + 1] for k in range(n))
ok('В2-13', sp.solve(sp.Eq(total, 1110000), Ssym)[0], 1000000)
# 14. sin2x + √2·cos(3π/2 + x) = 2cos x + √2;  б) [−3π; −3π/2]
e14 = sp.sin(2*x) + sp.sqrt(2)*sp.cos(sp.Rational(3, 2)*sp.pi + x) - 2*sp.cos(x) - sp.sqrt(2)
ok('В2-14б', str(roots_on(e14, -3*sp.pi, -sp.Rational(3, 2)*sp.pi)),
   str([-sp.Rational(11, 4)*sp.pi, -sp.Rational(3, 2)*sp.pi]))
ok('В2-14а', str(roots_on(e14, 0, 2*sp.pi - sp.Rational(1, 10**6))),
   str([sp.pi/2, sp.Rational(3, 4)*sp.pi, sp.Rational(5, 4)*sp.pi]))
# 16. log₃(x²−4x+3) − log₃((x−3)/(x+1)) ≤ 1
dom = sp.solve_univariate_inequality(x**2 - 4*x + 3 > 0, x, relational=False) & \
      sp.solve_univariate_inequality((x - 3)/(x + 1) > 0, x, relational=False)
ineq = sp.solve_univariate_inequality((x**2 - 4*x + 3) - 3*(x - 3)/(x + 1) <= 0, x, relational=False)
ok('В2-16', str(dom & ineq), str(sp.Interval.Ropen(-2, -1)))

bad = 0
for k, (g, w, f) in res.items():
    print(f"{'OK ' if f else 'ОШИБКА'} {k:16} получено {g}   в ключе {w}")
    bad += not f
print('\nвсе ответы сошлись' if not bad else f'\nрасхождений: {bad}')
