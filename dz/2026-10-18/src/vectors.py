"""Задание 2 ЕГЭ (векторы). Все ответы считаются из координат/длин."""
import sympy as sp

from common import Task, fmt_num

V = sp.Matrix


def length(v):
    return sp.sqrt(v.dot(v))


def deg(c):
    """Угол в градусах по косинусу."""
    return sp.nsimplify(sp.acos(c) * 180 / sp.pi)


def vt(v):
    return '(' + '; '.join(fmt_num(c) for c in v) + ')'


def vec_tasks_varvara():
    T = []
    A, B = V([2, -1]), V([-4, 7])
    T.append(Task('Даны точки $A%s$ и $B%s$. Найдите длину вектора $\\overrightarrow{AB}$.' % (vt(A), vt(B)),
                  fmt_num(length(B - A))))
    a, b = V([3, -2]), V([-1, 5])
    T.append(Task('Даны векторы $\\vec a%s$ и $\\vec b%s$. Найдите сумму координат вектора $2\\vec a-3\\vec b$.' % (vt(a), vt(b)),
                  fmt_num(sum(2 * a - 3 * b))))
    a, b = V([5, -3]), V([-2, 7])
    T.append(Task('Даны векторы $\\vec a%s$ и $\\vec b%s$. Найдите длину вектора $\\vec a+\\vec b$.' % (vt(a), vt(b)),
                  fmt_num(length(a + b))))
    A, B = V([-3, 5]), V([7, -1])
    M = (A + B) / 2
    T.append(Task('Точка $M$ — середина отрезка $AB$, где $A%s$, $B%s$, $O$ — начало координат. '
                  'Найдите сумму координат вектора $\\overrightarrow{OM}$.' % (vt(A), vt(B)), fmt_num(sum(M))))
    a, b = V([1, 4]), V([-2, 3])
    T.append(Task('Найдите скалярное произведение векторов $\\vec a%s$ и $\\vec b%s$.' % (vt(a), vt(b)),
                  fmt_num(a.dot(b))))
    a, b = V([3, 4]), V([4, 3])
    T.append(Task('Найдите косинус угла между векторами $\\vec a%s$ и $\\vec b%s$.' % (vt(a), vt(b)),
                  fmt_num(a.dot(b) / length(a) / length(b))))
    a, b = V([3, 0]), V([-2, 2])
    T.append(Task('Найдите угол между векторами $\\vec a%s$ и $\\vec b%s$. Ответ дайте в градусах.' % (vt(a), vt(b)),
                  fmt_num(deg(a.dot(b) / length(a) / length(b)))))
    m = sp.Symbol('m')
    sol = sp.solve(V([4, m]).dot(V([-3, 2])), m)
    T.append(Task('При каком значении $m$ векторы $\\vec a(4; m)$ и $\\vec b(-3; 2)$ перпендикулярны?', fmt_num(sol[0])))
    k = sp.Symbol('k')
    sol = sp.solve(2 * 10 - (-5) * k, k)          # 2·10 − (−5)·k = 0 — определитель
    T.append(Task('При каком значении $k$ векторы $\\vec a(2; -5)$ и $\\vec b(k; 10)$ коллинеарны?', fmt_num(sol[0])))
    xx, yy = sp.symbols('x y')
    s = sp.solve(list(xx * V([1, 1]) + yy * V([2, -1]) - V([7, 4])), [xx, yy])
    T.append(Task('Вектор $\\vec c(7; 4)$ разложили по векторам $\\vec a(1; 1)$ и $\\vec b(2; -1)$: '
                  '$\\vec c = x\\vec a + y\\vec b$. Найдите $x+y$.', fmt_num(s[xx] + s[yy])))
    T.append(Task('Длины векторов $\\vec a$ и $\\vec b$ равны 3 и 4, угол между ними $60^\\circ$. '
                  'Найдите $\\vec a\\cdot\\vec b$.', fmt_num(3 * 4 * sp.cos(sp.pi / 3))))
    T.append(Task('$|\\vec a| = 3$, $|\\vec b| = 5$, $\\vec a\\cdot\\vec b = 1$. Найдите $|\\vec a+\\vec b|$.',
                  fmt_num(sp.sqrt(9 + 25 + 2 * 1))))
    T.append(Task('$|\\vec a| = 7$, $|\\vec b| = 4$. Найдите скалярное произведение $(\\vec a+\\vec b)\\cdot(\\vec a-\\vec b)$.',
                  fmt_num(49 - 16)))
    # квадрат ABCD со стороной 6: A(0,0), B(6,0), C(6,6)
    A, B, C = V([0, 0]), V([6, 0]), V([6, 6])
    T.append(Task('Сторона квадрата $ABCD$ равна 6. Найдите скалярное произведение '
                  '$\\overrightarrow{AB}\\cdot\\overrightarrow{AC}$.', fmt_num((B - A).dot(C - A))))
    # ромб со стороной 5 и диагональю AC = 8: A(-4,0), C(4,0), B(0,-3), D(0,3)
    A, B, C, D = V([-4, 0]), V([0, -3]), V([4, 0]), V([0, 3])
    assert length(B - A) == 5 and length(C - A) == 8
    T.append(Task('Сторона ромба $ABCD$ равна 5, диагональ $AC = 8$. Найдите длину вектора '
                  '$\\overrightarrow{AB}-\\overrightarrow{AD}$.', fmt_num(length((B - A) - (D - A)))))
    # правильный треугольник со стороной 4
    A, B, C = V([0, 0]), V([4, 0]), V([2, 2 * sp.sqrt(3)])
    T.append(Task('Треугольник $ABC$ правильный, его сторона равна 4. Найдите '
                  '$\\overrightarrow{AB}\\cdot\\overrightarrow{AC}$.', fmt_num(sp.simplify((B - A).dot(C - A)))))
    a, b = V([1, -2, 2]), V([2, 1, -2])
    T.append(Task('Даны векторы $\\vec a%s$ и $\\vec b%s$ в пространстве. Найдите $|\\vec a|$ и $\\vec a\\cdot\\vec b$. '
                  'В ответ запишите их сумму.' % (vt(a), vt(b)), fmt_num(length(a) + a.dot(b))))
    sol = sp.solve(V([2, m, -1]).dot(V([3, 1, 4])), m)
    T.append(Task('При каком значении $m$ векторы $\\vec a(2; m; -1)$ и $\\vec b(3; 1; 4)$ перпендикулярны?',
                  fmt_num(sol[0])))
    return T


def vec_tasks_timofey():
    T = []
    m = sp.Symbol('m')
    a, b = V([4, 9]), V([2, -1])
    T.append(Task('Даны векторы $\\vec a%s$ и $\\vec b%s$. Найдите длину вектора $\\vec a+\\vec b$.' % (vt(a), vt(b)),
                  fmt_num(length(a + b))))
    a, b = V([3, -1]), V([-2, 4])
    T.append(Task('Даны векторы $\\vec a%s$ и $\\vec b%s$. Найдите абсциссу вектора $3\\vec a+2\\vec b$.' % (vt(a), vt(b)),
                  fmt_num((3 * a + 2 * b)[0])))
    a, b = V([-2, 5]), V([4, 3])
    T.append(Task('Найдите скалярное произведение векторов $\\vec a%s$ и $\\vec b%s$.' % (vt(a), vt(b)),
                  fmt_num(a.dot(b))))
    a, b = V([6, 8]), V([-3, 4])
    T.append(Task('Найдите косинус угла между векторами $\\vec a%s$ и $\\vec b%s$.' % (vt(a), vt(b)),
                  fmt_num(a.dot(b) / length(a) / length(b))))
    sol = sp.solve(V([m, 3]).dot(V([6, -4])), m)
    T.append(Task('При каком значении $m$ векторы $\\vec a(m; 3)$ и $\\vec b(6; -4)$ перпендикулярны?', fmt_num(sol[0])))
    T.append(Task('Длины векторов $\\vec a$ и $\\vec b$ равны 4 и 6, угол между ними $120^\\circ$. '
                  'Найдите $\\vec a\\cdot\\vec b$.', fmt_num(4 * 6 * sp.cos(2 * sp.pi / 3))))
    T.append(Task('$|\\vec a| = |\\vec b| = 5$, $\\vec a\\cdot\\vec b = 7$. Найдите $|\\vec a-\\vec b|$.',
                  fmt_num(sp.sqrt(25 + 25 - 2 * 7))))
    A, C, D = V([0, 0]), V([8, 6]), V([0, 6])
    T.append(Task('В прямоугольнике $ABCD$ стороны $AB = 8$, $AD = 6$. Найдите скалярное произведение '
                  '$\\overrightarrow{AC}\\cdot\\overrightarrow{AD}$.', fmt_num((C - A).dot(D - A))))
    # правильный шестиугольник со стороной 3, центр в начале координат
    P = [V([3 * sp.cos(sp.pi * k / 3), 3 * sp.sin(sp.pi * k / 3)]) for k in range(6)]
    A, B, F = P[0], P[1], P[5]
    T.append(Task('Сторона правильного шестиугольника $ABCDEF$ равна 3. Найдите длину вектора '
                  '$\\overrightarrow{AB}+\\overrightarrow{AF}$.', fmt_num(sp.simplify(length((B - A) + (F - A))))))
    a, b = V([1, 2, 4]), V([0, 1, 2])
    T.append(Task('Даны векторы $\\vec a%s$ и $\\vec b%s$. Найдите длину вектора $2\\vec a-\\vec b$.' % (vt(a), vt(b)),
                  fmt_num(length(2 * a - b))))
    return T
