"""Задачи с параметром (Яна, Матвей). Аналитический способ.

Проверка: заявленный ответ — предикат от a. Для каждого a из сетки
(включая граничные точки и их окрестности) независимо считаем число корней
(или проверяем условие) прямым решением и сравниваем с предикатом.
"""
import math
from fractions import Fraction as Fr

import sympy as sp

from common import Task

X, Y = sp.symbols('x y', real=True)
R = sp.Rational


def grid(critical=()):
    pts = {R(k, 4) for k in range(-48, 49)}
    for c in critical:
        c = sp.nsimplify(c)
        pts.add(c)
        for d in (R(1, 1000), R(1, 100)):
            pts.add(c + d)
            pts.add(c - d)
    return sorted(pts, key=float)


def check(name, fact, claim, critical=()):
    """fact(a) — вычисленное свойство, claim(a) — заявленный ответ. Должны совпасть везде."""
    for av in grid(critical):
        f, c = fact(av), claim(av)
        assert f == c, (name, av, f, c)


def real_roots(expr, var=X):
    """Различные действительные корни многочлена."""
    p = sp.Poly(sp.expand(expr), var)
    if p.degree() <= 0:
        return None if p.is_zero else []
    return sorted(set(r for r in sp.real_roots(p)), key=float)


def trig_count(poly_u, fn, interval):
    """Число корней уравнения P(fn(x)) = 0 на отрезке: решаем P(u)=0, затем fn(x)=u
    (solveset на исходном уравнении теряет корни вида arccos — проверено)."""
    U = sp.Symbol('u', real=True)
    xs = set()
    for u in real_roots(poly_u(U), U):
        s = sp.solveset(fn(X) - u, X, interval)
        assert isinstance(s, sp.FiniteSet) or s.is_empty, s
        xs |= set(s)
    return len(xs)


def count_set(sol):
    if sol.is_empty:
        return 0
    if isinstance(sol, sp.FiniteSet):
        return len(sol)
    return math.inf


# ===================================================================== Яна

def yana():
    T = []

    # 1. (a^2-4)x = a+2
    def fact(av):
        s = sp.solveset((av ** 2 - 4) * X - (av + 2), X, sp.S.Reals)
        return {0: 'none', 1: 'one'}.get(count_set(s), 'inf') if count_set(s) != math.inf else 'inf'
    check('я1', fact, lambda av: 'none' if av == 2 else ('inf' if av == -2 else 'one'), [2, -2])
    T.append(Task('Решите уравнение при каждом значении параметра $a$: $(a^2-4)x = a+2$.',
                  'при $a=2$ корней нет; при $a=-2$ $x$ — любое; иначе $x=\\frac{1}{a-2}$'))

    # 2. ax^2 - 6x + 9 = 0 ровно один корень
    check('я2', lambda av: len(real_roots(av * X ** 2 - 6 * X + 9)) == 1, lambda av: av in (0, 1), [0, 1])
    T.append(Task('Найдите все значения $a$, при которых уравнение $ax^2-6x+9=0$ имеет ровно один корень.',
                  '$a=0$; $a=1$', 'не забыть случай $a=0$'))

    # 3. два различных корня
    check('я3', lambda av: len(real_roots(X ** 2 - 2 * (av - 1) * X + av + 5)) == 2,
          lambda av: av < -1 or av > 4, [-1, 4])
    T.append(Task('Найдите все $a$, при которых уравнение $x^2-2(a-1)x+a+5=0$ имеет два различных корня.',
                  '$a<-1$ или $a>4$'))

    # 4. (a+2)x^2 - 4x + a - 1 > 0 при всех x
    def fact4(av):
        L = av + 2
        if L == 0:
            return False                     # линейная функция принимает и отрицательные значения
        if L < 0:
            return False
        xv = R(2) / L
        return (L * xv ** 2 - 4 * xv + av - 1) > 0   # минимум в вершине
    check('я4', fact4, lambda av: av > 2, [2, -2, -3])
    T.append(Task('Найдите все $a$, при которых неравенство $(a+2)x^2-4x+a-1>0$ выполняется при всех $x$.',
                  '$a>2$', 'при $a=-2$ неравенство линейное — не подходит'))

    # 5. два различных положительных корня
    def fact5(av):
        rs = real_roots(X ** 2 - 2 * av * X + av + 6)
        return len(rs) == 2 and all(r > 0 for r in rs)
    check('я5', fact5, lambda av: av > 3, [3, -2, -6, 0])
    T.append(Task('Найдите все $a$, при которых уравнение $x^2-2ax+a+6=0$ имеет два различных положительных корня.',
                  '$a>3$'))

    # 6. корни a и a+1 на [-1; 3]
    def fact6(av):
        rs = real_roots(X ** 2 - (2 * av + 1) * X + av ** 2 + av)
        return all(-1 <= r <= 3 for r in rs)
    check('я6', fact6, lambda av: -1 <= av <= 2, [-1, 2])
    T.append(Task('Найдите все $a$, при которых все корни уравнения $x^2-(2a+1)x+a^2+a=0$ принадлежат отрезку $[-1;\\,3]$.',
                  '$a\\in[-1;\\,2]$', 'корни $a$ и $a+1$'))

    # 7. log3(x+a) = log3(2x-1) имеет корень
    def fact7(av):
        xs = sp.solve(X + av - (2 * X - 1), X)    # равенство аргументов
        return any((xv + av) > 0 and (2 * xv - 1) > 0 for xv in xs)
    check('я7', fact7, lambda av: av > R(-1, 2), [R(-1, 2)])
    T.append(Task('При каких $a$ уравнение $\\log_3(x+a)=\\log_3(2x-1)$ имеет корень?',
                  '$a>-\\frac12$'))

    # 8. дробь ровно один корень
    def fact8(av):
        rs = [r for r in real_roots(X ** 2 - (av + 3) * X + 3 * av) if r != 5]
        return len(rs) == 1
    check('я8', fact8, lambda av: av in (3, 5), [3, 5])
    T.append(Task('Найдите все $a$, при которых уравнение $\\dfrac{x^2-(a+3)x+3a}{x-5}=0$ имеет ровно один корень.',
                  '$a=3$; $a=5$'))

    # 9. система
    def fact9(av):
        s = sp.linsolve([av * X + 4 * Y - 2, X + av * Y - 1], [X, Y])
        if s.is_empty:
            return 'none'
        (sx, sy), = s
        return 'inf' if (sx.free_symbols or sy.free_symbols) else 'one'
    check('я9', fact9, lambda av: 'none' if av == -2 else ('inf' if av == 2 else 'one'), [2, -2])
    T.append(Task('При каких $a$ система $\\begin{cases} ax+4y=2,\\\\ x+ay=1 \\end{cases}$ а) не имеет решений; '
                  'б) имеет бесконечно много решений?', 'а) $a=-2$; б) $a=2$'))

    # 10. |x-2| + |x+1| = a
    def fact10(av):
        return count_set(sp.solveset(sp.Abs(X - 2) + sp.Abs(X + 1) - av, X, sp.S.Reals))
    check('я10', fact10, lambda av: 2 if av > 3 else (math.inf if av == 3 else 0), [3])
    T.append(Task('Сколько корней имеет уравнение $|x-2|+|x+1|=a$ в зависимости от $a$?',
                  'при $a<3$ — нет; при $a=3$ — бесконечно много ($x\\in[-1;\\,2]$); при $a>3$ — два'))

    # 11. 4^x - (a+3)2^x + 3a = 0
    def fact11(av):
        ts = [r for r in real_roots(X ** 2 - (av + 3) * X + 3 * av) if r > 0]
        return len(ts)                         # каждому t>0 — ровно один x
    check('я11', fact11, lambda av: 1 if (av <= 0 or av == 3) else 2, [0, 3])
    T.append(Task('Найдите все $a$, при которых уравнение $4^x-(a+3)\\cdot 2^x+3a=0$ имеет ровно один корень. '
                  'При каких $a$ корней два?',
                  'один корень: $a\\le 0$ или $a=3$; два корня: $a>0$, $a\\ne 3$'))

    # 12. (x^2-5x+4)sqrt(x-a) = 0 ровно два корня
    def fact12(av):
        cands = {av} | {r for r in (1, 4) if r >= av}
        return len(cands) == 2
    check('я12', fact12, lambda av: 1 <= av < 4, [1, 4])
    T.append(Task('Найдите все $a$, при которых уравнение $(x^2-5x+4)\\sqrt{x-a}=0$ имеет ровно два различных корня.',
                  '$a\\in[1;\\,4)$'))

    # 13. x^2 - 6|x| + a = 0
    def fact13(av):
        return count_set(sp.solveset(X ** 2 - 6 * sp.Abs(X) + av, X, sp.S.Reals))
    check('я13а', lambda av: fact13(av) == 3, lambda av: av == 0, [0, 9])
    check('я13б', lambda av: fact13(av) == 4, lambda av: 0 < av < 9, [0, 9])
    T.append(Task('При каких $a$ уравнение $x^2-6|x|+a=0$ имеет а) ровно три корня; б) ровно четыре корня?',
                  'а) $a=0$; б) $0<a<9$', 'функция чётная: корни парами $\\pm x$'))

    # 14. x^2 - ax + 9 >= 0 на [1;4]
    def fact14(av):
        pts = [R(1), R(4)] + ([R(av, 2)] if 1 <= R(av, 2) <= 4 else [])
        return min(p ** 2 - av * p + 9 for p in pts) >= 0
    check('я14', fact14, lambda av: av <= 6, [6])
    T.append(Task('Найдите все $a$, при которых неравенство $x^2-ax+9\\ge 0$ выполняется при всех $x\\in[1;\\,4]$.',
                  '$a\\le 6$', '$a\\le x+\\frac9x$, минимум 6 при $x=3$'))

    # 15. sqrt(x+3) = x + a ровно два корня
    def fact15(av):
        cands = real_roots((X + av) ** 2 - (X + 3))
        good = [c for c in cands if c + 3 >= 0 and c + av >= 0]
        return len(good) == 2
    check('я15', fact15, lambda av: 3 <= av < R(13, 4), [3, R(13, 4)])
    T.append(Task('Найдите все $a$, при которых уравнение $\\sqrt{x+3}=x+a$ имеет ровно два различных корня.',
                  '$a\\in\\left[3;\\,\\frac{13}{4}\\right)$', 'замена $t=\\sqrt{x+3}\\ge 0$: $t^2-t+a-3=0$, два неотрицательных корня'))

    # 16. 2sin^2x - (2a+1)sinx + a = 0 на [0; pi]
    def fact16(av):
        return trig_count(lambda u: 2 * u ** 2 - (2 * av + 1) * u + av, sp.sin, sp.Interval(0, sp.pi))
    check('я16а', lambda av: fact16(av) == 3, lambda av: av == 1, [0, R(1, 2), 1])
    check('я16б', lambda av: fact16(av) == 4, lambda av: 0 <= av < 1 and av != R(1, 2), [0, R(1, 2), 1])
    T.append(Task('При каких $a$ уравнение $2\\sin^2x-(2a+1)\\sin x+a=0$ имеет на отрезке $[0;\\,\\pi]$ '
                  'а) ровно три корня; б) ровно четыре корня?',
                  'а) $a=1$; б) $a\\in\\left[0;\\,\\frac12\\right)\\cup\\left(\\frac12;\\,1\\right)$',
                  '$(2\\sin x-1)(\\sin x-a)=0$'))

    # 17. два различных корня, каждый больше 1
    def fact17(av):
        rs = real_roots(X ** 2 - 2 * (av + 1) * X + av ** 2 + 3)
        return len(rs) == 2 and all(r > 1 for r in rs)
    check('я17', fact17, lambda av: av > 1, [0, 1])
    T.append(Task('Найдите все $a$, при которых уравнение $x^2-2(a+1)x+a^2+3=0$ имеет два различных корня, '
                  'каждый из которых больше 1.', '$a>1$'))

    # 18. окружность и прямая
    def fact18(av):
        return len(real_roots(X ** 2 + (X + av) ** 2 - 8))
    check('я18а', lambda av: fact18(av) == 1, lambda av: av in (4, -4), [4, -4])
    check('я18б', lambda av: fact18(av) == 2, lambda av: -4 < av < 4, [4, -4])
    T.append(Task('При каких $a$ система $\\begin{cases} x^2+y^2=8,\\\\ y=x+a \\end{cases}$ имеет а) ровно одно решение; '
                  'б) ровно два решения? Решите подстановкой, без рисунка.', 'а) $a=\\pm 4$; б) $-4<a<4$'))
    return T


# ===================================================================== Матвей

def matvey():
    T = []

    def fact1(av):
        s = sp.solveset((av - 3) * X - (av ** 2 - 9), X, sp.S.Reals)
        n = count_set(s)
        return 'inf' if n == math.inf else ('one' if n == 1 else 'none')
    check('м1', fact1, lambda av: 'inf' if av == 3 else 'one', [3])
    T.append(Task('Решите уравнение при каждом значении $a$: $(a-3)x=a^2-9$.',
                  'при $a=3$ $x$ — любое; при $a\\ne3$ $x=a+3$'))

    def fact2(av):
        s = sp.solveset(av * (av - 2) * X - av, X, sp.S.Reals)
        n = count_set(s)
        return 'inf' if n == math.inf else ('one' if n == 1 else 'none')
    check('м2', fact2, lambda av: 'inf' if av == 0 else ('none' if av == 2 else 'one'), [0, 2])
    T.append(Task('Решите уравнение при каждом значении $a$: $a(a-2)x=a$.',
                  'при $a=0$ $x$ — любое; при $a=2$ корней нет; иначе $x=\\frac{1}{a-2}$'))

    check('м3', lambda av: len(real_roots(X ** 2 + 4 * X + av)) == 2, lambda av: av < 4, [4])
    T.append(Task('При каких $a$ уравнение $x^2+4x+a=0$ имеет два различных корня?', '$a<4$'))

    check('м4', lambda av: len(real_roots((av - 1) * X ** 2 + 2 * X + 1)) == 1, lambda av: av in (1, 2), [1, 2])
    T.append(Task('При каких $a$ уравнение $(a-1)x^2+2x+1=0$ имеет ровно один корень?', '$a=1$; $a=2$'))

    check('м5', lambda av: (av ** 2 - 16) < 0, lambda av: -4 < av < 4, [4, -4])
    # независимая проверка: минимум x^2+ax+4 в вершине положителен
    check('м5б', lambda av: (R(av, 2) ** 2 - av * R(av, 2) + 4) > 0, lambda av: -4 < av < 4, [4, -4])
    T.append(Task('При каких $a$ неравенство $x^2+ax+4>0$ верно при всех $x$?', '$-4<a<4$'))

    def fact6(av):
        rs = real_roots(X ** 2 - 2 * av * X + av ** 2 - 4)
        return all(r > 0 for r in rs) and len(rs) == 2
    check('м6', fact6, lambda av: av > 2, [2])
    T.append(Task('При каких $a$ оба корня уравнения $x^2-2ax+a^2-4=0$ положительны?', '$a>2$', 'корни $a\\pm2$'))

    def fact7(av):
        rs = [r for r in real_roots(X ** 2 - (av + 4) * X + 4 * av) if r != 1]
        return len(rs) == 1
    check('м7', fact7, lambda av: av in (1, 4), [1, 4])
    T.append(Task('При каких $a$ уравнение $\\dfrac{x^2-(a+4)x+4a}{x-1}=0$ имеет ровно один корень?', '$a=1$; $a=4$'))

    def fact8(av):
        s = sp.linsolve([2 * X + av * Y - 3, av * X + 8 * Y - 6], [X, Y])
        if s.is_empty:
            return 'none'
        (sx, sy), = s
        return 'inf' if (sx.free_symbols or sy.free_symbols) else 'one'
    check('м8', fact8, lambda av: 'inf' if av == 4 else ('none' if av == -4 else 'one'), [4, -4])
    T.append(Task('При каких $a$ система $\\begin{cases} 2x+ay=3,\\\\ ax+8y=6 \\end{cases}$ а) не имеет решений; '
                  'б) имеет бесконечно много решений?', 'а) $a=-4$; б) $a=4$'))

    def fact9(av):
        return count_set(sp.solveset(X ** 4 - 4 * X ** 2 + av, X, sp.S.Reals))
    check('м9а', lambda av: fact9(av) == 2, lambda av: av < 0 or av == 4, [0, 4])
    check('м9б', lambda av: fact9(av) == 4, lambda av: 0 < av < 4, [0, 4])
    T.append(Task('При каких $a$ уравнение $x^4-4x^2+a=0$ имеет а) ровно два корня; б) ровно четыре корня?',
                  'а) $a<0$ или $a=4$; б) $0<a<4$', 'замена $t=x^2\\ge0$'))

    def fact10(av):
        return len([r for r in real_roots(X ** 2 - (av + 1) * X + av) if r > 0])
    check('м10', lambda av: fact10(av) == 1, lambda av: av <= 0 or av == 1, [0, 1])
    T.append(Task('При каких $a$ уравнение $9^x-(a+1)\\cdot3^x+a=0$ имеет ровно один корень?', '$a\\le0$ или $a=1$'))

    def fact11(av):
        s = sp.solveset((X - av) * sp.sqrt(X - 2), X, sp.S.Reals)
        return len([r for r in s if r - 2 >= 0])          # корень вне ОДЗ sympy не отсекает
    check('м11', lambda av: fact11(av) == 2, lambda av: av > 2, [2])
    T.append(Task('При каких $a$ уравнение $(x-a)\\sqrt{x-2}=0$ имеет ровно два корня? Ровно один?',
                  'два: $a>2$; один: $a\\le 2$'))

    def fact12(av):
        rs = real_roots(X ** 2 - 6 * X + av)
        return len(rs) == 2 and all(r > 1 for r in rs)
    check('м12', fact12, lambda av: 5 < av < 9, [5, 9])
    T.append(Task('При каких $a$ оба корня уравнения $x^2-6x+a=0$ различны и больше 1?', '$5<a<9$'))

    def fact13(av):
        return trig_count(lambda u: u ** 2 - (av + 1) * u + av, sp.cos, sp.Interval(0, sp.pi))
    check('м13', lambda av: fact13(av) == 2, lambda av: -1 <= av < 1, [-1, 1])
    T.append(Task('При каких $a$ уравнение $\\cos^2x-(a+1)\\cos x+a=0$ имеет на отрезке $[0;\\,\\pi]$ ровно два корня?',
                  '$a\\in[-1;\\,1)$', '$(\\cos x-1)(\\cos x-a)=0$'))
    return T
