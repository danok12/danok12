"""Клим, 7 класс: полные квадратные уравнения через дискриминант, потом задачи потяжелее."""
from math import gcd

import sympy as sp

from common import Doc, Task, to_sympy, tex_of, x

A_INT = [r'x^2-5x+6=0', r'x^2+7x+12=0', r'x^2-2x-15=0', r'x^2+x-20=0',
         r'x^2-10x+21=0', r'x^2+2x-48=0', r'x^2-12x+35=0', r'x^2+9x+14=0']
A_COEF = [r'2x^2-7x+3=0', r'3x^2+5x-2=0', r'5x^2-8x+3=0', r'2x^2+5x-12=0',
          r'4x^2-4x-3=0', r'6x^2-x-2=0', r'3x^2-10x+3=0', r'-x^2+3x+10=0']
A_SPECIAL = [r'x^2-6x+9=0', r'4x^2+12x+9=0', r'x^2+3x+5=0', r'2x^2-x+1=0']
A_IRR = [r'x^2-4x+1=0', r'x^2+2x-4=0', r'x^2-3x+1=0', r'2x^2-6x+1=0']
A_REARR = [r'x^2=3x+10', r'(x-2)(x+5)=8', r'(2x-1)^2=4x+9', r'x(x+4)=3(x+2)',
           r'(x+3)^2-2(x+3)=15', r'3x(x-2)-(x-4)(x+1)=13']
B_EQ = [r'\frac{x^2}{4}+\frac{x}{2}=2', r'\frac{x^2+x}{2}-\frac{x+3}{3}=3', r'x^2-2\sqrt{3}x+2=0']


def quad_coeffs(tex):
    eq = to_sympy(tex)
    p = sp.Poly(sp.expand(eq.lhs - eq.rhs), x)
    assert p.degree() == 2, tex
    return [int(c) if c.is_Integer else c for c in p.all_coeffs()]


def pm_form(a, b, c):
    """Корни с иррациональностью в виде (p ± q√m)/r, сокращённые."""
    D = b * b - 4 * a * c
    k, m = 1, D
    for f in range(2, int(D ** 0.5) + 1):
        while m % (f * f) == 0:
            m //= f * f
            k *= f
    p, r = -b, 2 * a
    g = gcd(gcd(abs(p), k), abs(r))
    p, k, r = p // g, k // g, r // g
    if r < 0:
        p, r = -p, -r
    sq = (str(k) if k != 1 else '') + r'\sqrt{%d}' % m
    top = (str(p) if p else '') + r'\pm ' + sq
    s = top if r == 1 else r'\frac{%s}{%d}' % (top, r)
    roots = [(sp.Integer(p) + s_ * k * sp.sqrt(m)) / r for s_ in (1, -1)]
    return s, roots


def answer(tex):
    eq = to_sympy(tex)
    f = eq.lhs - eq.rhs
    rs = sorted(sp.solveset(f, x, sp.S.Reals), key=float)
    for r in rs:
        assert sp.simplify(f.subs(x, r)) == 0
    if not rs:
        return 'корней нет ($D<0$)'
    if all(r.is_Rational for r in rs):
        if len(rs) == 1:
            return '$%s$ (один корень, $D=0$)' % tex_of(rs[0])
        return '; '.join('$%s$' % tex_of(r) for r in rs)
    coeffs = quad_coeffs(tex)
    if all(isinstance(c, int) for c in coeffs):
        s, roots = pm_form(*coeffs)
        assert sorted(roots, key=float) == sorted(rs, key=float) or \
            all(sp.simplify(u - v) == 0 for u, v in zip(sorted(roots, key=float), rs))
        return '$%s$' % s
    return '; '.join('$%s$' % tex_of(sp.radsimp(r)) for r in rs)


def eq_tasks(lst):
    return [Task('$%s$' % t, answer(t)) for t in lst]


def harder():
    T = eq_tasks(B_EQ)
    e = to_sympy(B_EQ[2])
    rs = sorted(sp.solveset(e.lhs - e.rhs, x, sp.S.Reals), key=float)
    assert rs == sorted([sp.sqrt(3) - 1, sp.sqrt(3) + 1], key=float)
    T[2].answer = '$\\sqrt{3}\\pm 1$'
    # биквадратные и замена
    for tex in [r'x^4-13x^2+36=0', r'x^4-3x^2-4=0', r'(x^2+2x)^2-2(x^2+2x)-3=0', r'x^2-5|x|+6=0']:
        e = to_sympy(tex)
        rs = sorted(sp.solveset(e.lhs - e.rhs, x, sp.S.Reals), key=float)
        hint = ''
        if 'x^4' in tex:
            hint = ' (замена $t=x^2$)'
        elif '(x^2+2x)^2' in tex:
            hint = ' (замена $t=x^2+2x$)'
        elif '|x|' in tex:
            hint = ' (замена $t=|x|$)'
        T.append(Task('$%s$%s' % (tex, hint), '; '.join('$%s$' % tex_of(r) for r in rs)))
    e = to_sympy(r'(x^2-9)^2+(x^2-2x-3)^2=0')
    rs = sorted(sp.solveset(e.lhs - e.rhs, x, sp.S.Reals), key=float)
    assert rs == [3]
    T.append(Task('$(x^2-9)^2+(x^2-2x-3)^2=0$ (когда сумма квадратов равна нулю?)', '$3$'))
    k = sp.Symbol('k')
    kv = sp.solve(9 + 3 * k - 12, k)[0]
    other = [r for r in sp.solve(x ** 2 + kv * x - 12, x) if r != 3][0]
    T.append(Task('Число 3 — корень уравнения $x^2+kx-12=0$. Найдите $k$ и второй корень.',
                  '$k=%s$, второй корень $%s$' % (kv, other)))
    b = sp.Symbol('b')
    bs = sorted(sp.solve(b ** 2 - 64, b))
    T.append(Task('При каких $b$ уравнение $x^2+bx+16=0$ имеет ровно один корень?', '$b=%s$; $b=%s$' % tuple(bs)))
    c = sp.Symbol('c')
    cond = sp.solve_univariate_inequality(16 - 8 * c < 0, c)
    T.append(Task('При каких $c$ уравнение $2x^2-4x+c=0$ не имеет корней?', '$c>2$'))
    assert cond == sp.Interval.open(2, sp.oo).as_relational(c) or str(cond) == '(2 < c) & (c < oo)'
    # текстовые задачи — решаем уравнением и выбираем по смыслу
    n = [r for r in sp.solve(x * (x + 1) - 156, x) if r > 0][0]
    T.append(Task('Произведение двух последовательных натуральных чисел равно 156. Найдите эти числа.',
                  '%s и %s' % (n, n + 1)))
    w = [r for r in sp.solve(x * (x + 7) - 60, x) if r > 0][0]
    T.append(Task('Площадь прямоугольника 60 см², одна сторона на 7 см длиннее другой. Найдите стороны.',
                  '%s см и %s см' % (w, w + 7)))
    n = [r for r in sp.solve(x ** 2 + (x + 1) ** 2 - 113, x) if r > 0][0]
    T.append(Task('Сумма квадратов двух последовательных натуральных чисел равна 113. Найдите эти числа.',
                  '%s и %s' % (n, n + 1)))
    n = [r for r in sp.solve(x * (x - 3) / 2 - 35, x) if r > 0][0]
    T.append(Task('У выпуклого многоугольника с $n$ сторонами $\\frac{n(n-3)}{2}$ диагоналей. '
                  'Сколько сторон у многоугольника, у которого 35 диагоналей?', str(n)))
    ts = sorted(sp.solve(20 * x - 5 * x ** 2 - 15, x))
    T.append(Task('Мяч подбросили вверх, его высота (в метрах) через $t$ секунд равна $h=20t-5t^2$. '
                  'Через сколько секунд мяч будет на высоте 15 м? Почему ответов два?',
                  'через %s с (вверх) и через %s с (вниз)' % tuple(ts)))
    return T


def build():
    doc = Doc('klim', 'Клим, 7 класс', 'Домашнее задание · квадратные уравнения')
    doc.h('Формулы')
    doc.p('Уравнение $ax^2+bx+c=0$, где $a\\ne0$. Дискриминант $D=b^2-4ac$.<br>'
          'Если $D>0$ — два корня $x_{1,2}=\\dfrac{-b\\pm\\sqrt{D}}{2a}$; если $D=0$ — один корень '
          '$x=-\\dfrac{b}{2a}$; если $D<0$ — корней нет.')
    doc.p('В каждом номере сначала выпишите $a$, $b$, $c$ (со знаками!), потом считайте $D$.')
    doc.h('1. Решите уравнение: старший коэффициент равен 1', 3)
    doc.tasks(eq_tasks(A_INT), cols=2, answer_cols=4)
    doc.h('2. Старший коэффициент не равен 1', 3)
    doc.tasks(eq_tasks(A_COEF), cols=2, answer_cols=4)
    doc.h('3. Один корень или ни одного', 3)
    doc.tasks(eq_tasks(A_SPECIAL), cols=2, answer_cols=4)
    doc.h('4. Корни с квадратным корнем', 3)
    doc.p('Ответ оставляйте в виде $\\frac{3\\pm\\sqrt5}{2}$. Если можно, сократите дробь.')
    doc.tasks(eq_tasks(A_IRR), cols=2, answer_cols=4)
    doc.h('5. Сначала приведите к виду $ax^2+bx+c=0$', 3)
    doc.tasks(eq_tasks(A_REARR), cols=2, answer_cols=3)
    doc.h('Задачи потяжелее')
    doc.p('Дроби в уравнении: умножьте обе части на общий знаменатель. Уравнения четвёртой степени '
          'решаются заменой — в скобках подсказано какой.')
    doc.tasks(harder(), cols=1, answer_cols=2)
    return doc
