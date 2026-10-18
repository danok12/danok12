"""Антон и Стас, 8 класс: теплоёмкость + видео на следующие темы, дроби.
Стасу дополнительно — уравнения без квадратных."""
from fractions import Fraction as F

import sympy as sp

from common import Doc, Task, to_sympy, same, roots_tex, tex_of, num_or_tex, x


# ------------------------------------------------------------ физика

def kdj(q):
    """Дж -> строка ответа."""
    q = F(q)
    if q.denominator != 1:
        raise ValueError(q)
    q = q.numerator
    s = f'{q:,}'.replace(',', ' ')
    return s + ' Дж'


def physics():
    c_w, c_al, c_st = 4200, 920, 500
    t = []
    q1 = c_w * 3 * (70 - 20)
    t.append(Task('Сколько теплоты нужно, чтобы нагреть 3 кг воды от 20 °C до 70 °C? '
                  'Удельная теплоёмкость воды 4200 Дж/(кг·°C).',
                  f'{kdj(q1)} = {q1 // 1000} кДж'))
    q2 = F(c_al) * F(4, 10) * (220 - 20)
    t.append(Task('Алюминиевая деталь массой 400 г остыла от 220 °C до 20 °C. Какое количество теплоты '
                  'она отдала? Удельная теплоёмкость алюминия 920 Дж/(кг·°C).',
                  f'{kdj(q2)} = 73,6 кДж'))
    assert q2 == 73600
    c3 = F(40000, 2 * 50)
    t.append(Task('На нагревание куска металла массой 2 кг на 50 °C затратили 40 кДж теплоты. '
                  'Найдите удельную теплоёмкость металла. Что это может быть за металл '
                  '(посмотрите таблицу в учебнике)?',
                  f'{c3} Дж/(кг·°C): медь, латунь или цинк'))
    assert c3 == 400
    m4 = F(1260000, c_w * (65 - 15))
    t.append(Task('Какую массу воды можно нагреть от 15 °C до 65 °C, сообщив ей 1,26 МДж теплоты?',
                  f'{m4} кг'))
    assert m4 == 6
    dt5 = F(90000, c_st * 5)
    t.append(Task('Стальной брусок массой 5 кг получил 90 кДж теплоты. На сколько градусов он нагрелся? '
                  'Какой стала его температура, если сначала она была 12 °C? '
                  'Удельная теплоёмкость стали 500 Дж/(кг·°C).',
                  f'на {dt5} °C, до {12 + dt5} °C'))
    assert dt5 == 36
    q6a = F(c_al) * F(8, 10) * 80
    q6w = F(c_w) * F(25, 10) * 80
    t.append(Task('В алюминиевой кастрюле массой 800 г нагревают 2,5 л воды от 20 °C до кипения (100 °C). '
                  'Сколько теплоты нужно? Не забудьте, что нагревается и сама кастрюля. '
                  'Масса 1 л воды — 1 кг.',
                  f'{kdj(q6a)} + {kdj(q6w)} = {kdj(q6a + q6w)} ≈ 899 кДж'))
    assert q6a + q6w == 898880
    r7 = F(4200, 400)
    t.append(Task('Воде массой 1 кг и меди массой 1 кг сообщили одинаковое количество теплоты. '
                  'Что нагреется сильнее и во сколько раз? Удельная теплоёмкость меди 400 Дж/(кг·°C). '
                  'Почему у моря летом днём прохладнее, чем в степи?',
                  'медь, в 10,5 раза; у воды большая теплоёмкость — она медленно нагревается'))
    assert r7 == F(21, 2)
    return t


VIDEOS_PHYS = [
    ('1. Энергия топлива', '8 класс урок №8 Энергия топлива. Удельная теплота сгорания топлива',
     'https://www.youtube.com/watch?v=OfWBL9g2_bY'),
    ('2. Закон сохранения энергии в тепловых процессах',
     '8 класс урок №9 Закон сохранения и превращения энергии в тепловых процессах',
     'https://www.youtube.com/watch?v=h0teMzDxJh0'),
    ('3. Задачи на теплообмен (уравнение теплового баланса)',
     'Расчёт количества теплоты при теплообмене. Урок 8. Физика 8 класс',
     'https://www.youtube.com/watch?v=cj_EwfZlFn8'),
    ('4. Плавление и кристаллизация',
     '8 класс урок №12 Плавление и кристаллизация твёрдых тел. Удельная теплота плавления',
     'https://www.youtube.com/watch?v=r9u_QAZikhM'),
    ('5. Кипение и парообразование', '8 класс урок №15 Кипение, удельная теплота парообразования',
     'https://www.youtube.com/watch?v=4ZgFfSRHQFY'),
]


# ------------------------------------------------------------ дроби

NUMERIC = [
    (r'\left(\frac{5}{6}-\frac{3}{8}\right)\cdot\frac{24}{11}+\frac{7}{12}\cdot\frac{18}{35}', '13/10'),
    (r'\mix{2}{1}{3}\cdot\mix{1}{2}{7}-\mix{1}{5}{6}\cdot\frac{9}{11}', '3/2'),
    (r'\dfrac{\dfrac{3}{4}+\dfrac{5}{6}}{\dfrac{7}{8}-\dfrac{2}{3}}', '38/5'),
    (r'\frac{2}{3}\cdot\frac{9}{14}\dv\left(\frac{5}{7}-\frac{1}{2}\right)+\frac{1}{3}', '7/3'),
    (r'\left(\frac{1}{2}+\frac{1}{3}+\frac{1}{4}\right)\cdot\frac{12}{13}-\left(\frac{1}{5}-\frac{1}{6}\right)\cdot 30', '0'),
    (r'1+\cfrac{1}{2+\cfrac{1}{3+\cfrac{1}{4}}}', '43/30'),
]


def numeric_tasks():
    out = []
    for tex, ans in NUMERIC:
        v = sp.nsimplify(to_sympy(tex))
        assert v == sp.Rational(ans), (tex, v, ans)
        ans = '$' + tex_of(v) + '$'
        if v.q > 1 and num_or_tex(v) != ans:
            ans += ' = ' + num_or_tex(v)
        out.append(Task('$\\displaystyle ' + tex + '$', ans))
    # телескопическая сумма и произведение — считаем Fraction'ами
    s = sum(F(1, k * (k + 1)) for k in range(1, 10))
    assert s == F(9, 10)
    out.append(Task(r'$\displaystyle \frac{1}{1\cdot 2}+\frac{1}{2\cdot 3}+\frac{1}{3\cdot 4}+\ldots+\frac{1}{9\cdot 10}$'
                    r'<br>Подсказка: проверьте, что $\frac{1}{2\cdot 3}=\frac{1}{2}-\frac{1}{3}$.',
                    r'$\frac{9}{10}$', wide=True))
    p = F(1)
    for k in range(2, 11):
        p *= 1 - F(1, k * k)
    assert p == F(11, 20)
    out.append(Task(r'$\displaystyle \left(1-\frac{1}{4}\right)\left(1-\frac{1}{9}\right)\left(1-\frac{1}{16}\right)'
                    r'\cdot\ldots\cdot\left(1-\frac{1}{100}\right)$',
                    r'$\frac{11}{20}$', wide=True))
    return out


# (условие, ожидаемый ответ). Ответ сверяется с условием тождественно.
ALGEBRAIC = [
    (r'\frac{a}{a-3}-\frac{3}{a+3}', r'\frac{a^2+9}{a^2-9}'),
    (r'\frac{1}{a-b}-\frac{1}{a+b}-\frac{2b}{a^2-b^2}', r'0'),
    (r'\frac{5}{2x-6}-\frac{x+1}{x^2-3x}', r'\frac{3x-2}{2x(x-3)}'),
    (r'\frac{4b^3}{15a^2}\cdot\frac{25a^3}{8b^5}', r'\frac{5a}{6b^2}'),
    (r'\frac{a^2-9}{a^2+6a+9}\cdot\frac{2a+6}{a-3}', r'2'),
    (r'\frac{x^2-4x}{x^2-16}\cdot\frac{x^2+8x+16}{3x}', r'\frac{x+4}{3}'),
    (r'\left(\frac{a}{a-2}-\frac{a}{a+2}\right)\cdot\frac{a^2-4}{8a}', r'\frac{1}{2}'),
    (r'\left(\frac{x}{y}-\frac{y}{x}\right)\cdot\frac{xy}{x+y}', r'x-y'),
    (r'\left(\frac{1}{x-1}+\frac{2}{x^2-1}\right)\cdot\frac{x^2-1}{x+3}', r'1'),
    (r'\frac{a^2+ab}{a^2-b^2}\cdot\left(\frac{a}{b}-\frac{b}{a}\right)', r'\frac{a+b}{b}'),
    (r'\left(\frac{3}{a-3}-\frac{a+15}{a^2-9}+\frac{2}{a}\right)\cdot\frac{a^2+3a}{4}', r'\frac{2a+3}{2}'),
    (r'\frac{1}{x(x+1)}+\frac{1}{(x+1)(x+2)}+\frac{1}{(x+2)(x+3)}', r'\frac{3}{x(x+3)}'),
]


def algebraic_tasks():
    out = []
    for tex, ans in ALGEBRAIC:
        assert same(to_sympy(tex), to_sympy(ans)), (tex, ans)
        out.append(Task('$\\displaystyle ' + tex + '$', '$' + ans + '$', wide=len(tex) > 64))
    e = r'\frac{x+3}{x^2-3x}-\frac{x-3}{x^2+3x}-\frac{12}{x^2-9}'
    assert same(to_sympy(e), 0)
    out.append(Task('Докажите, что значение выражения не зависит от $x$:<br>$\\displaystyle ' + e + '$',
                    '$0$ при всех допустимых $x$', wide=True))
    e = r'\frac{x^2-9}{2x^2+x}\cdot\frac{4x^2+4x+1}{x^2+3x}'
    simp = r'\frac{(x-3)(2x+1)}{x^2}'
    assert same(to_sympy(e), to_sympy(simp))
    v = to_sympy(e).subs(x, sp.Rational(1, 2))
    assert v == -20
    out.append(Task('Упростите и найдите значение при $x=\\frac{1}{2}$:<br>$\\displaystyle ' + e + '$',
                    '$' + simp + '$; при $x=\\frac12$ получается $-20$', wide=True))
    return out


# ------------------------------------------------------------ уравнения (Стас)

EQS = [
    r'5(x-3)-2(x+4)=3(x-1)-2x',
    r'\frac{x}{3}+\frac{x}{4}=14',
    r'\frac{2x-1}{3}-\frac{x+2}{4}=\frac{x}{6}-\frac{1}{2}',
    r'\frac{3x-1}{5}-\frac{2-x}{2}=x-\frac{3}{10}',
    r'\frac{x-1}{2}+\frac{x-2}{3}+\frac{x-3}{4}=x-1',
    r'(x+3)^2-(x-2)^2=35',
    r'(2x-1)(x+3)-2(x-1)^2=22',
    r'(x-4)(x+4)-x(x-3)=2x-1',
    r'3(x-2)-(x+1)=2(x-4)+1',
    r'4(x+1)-3x=x+7',
    r'\frac{3}{x-2}=\frac{5}{x+2}',
    r'\frac{x+1}{x-3}=\frac{x-2}{x+4}',
    r'\frac{2x+1}{x-1}=\frac{2x-3}{x-2}',
    r'\frac{1}{x-1}+\frac{2}{x+1}=\frac{4}{x^2-1}',
    r'\frac{3}{x-2}-\frac{1}{x+2}=\frac{x+10}{x^2-4}',
    r'\frac{x+5}{x-1}+\frac{x-7}{x-1}=2',
    r'|2x-5|=7',
    r'|3x-1|=x+5',
    r'|x-3|=|x+5|',
    r'\big||x-2|-3\big|=1',
]


def excluded_points(expr):
    """Значения x, при которых обращается в 0 какой-нибудь знаменатель исходного выражения."""
    bad = set()
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Pow) and node.exp.is_negative and node.base.has(x):
            s = sp.solveset(node.base, x, sp.S.Reals)
            bad |= set(s) if not s.is_empty else set()
    return bad


def eq_answer(tex):
    """Решение линейного/дробного/модульного уравнения с полной проверкой.
    Тождество, «нет корней» и посторонние корни распознаются."""
    eq = to_sympy(tex.replace(r'\big', ''))
    diff = eq.lhs - eq.rhs
    excluded = excluded_points(diff)
    num = sp.expand(sp.fraction(sp.cancel(diff))[0])
    if not num.has(sp.Abs):
        # «без квадратных»: после приведения к общему знаменателю — линейное уравнение
        assert sp.degree(num, x) <= 1 or num == 0, (tex, num)
    if not num.has(sp.Abs) and sp.simplify(num) == 0:
        if not excluded:
            return 'любое число (тождество)'
        return 'любое $x$, кроме ' + ', '.join('$%s$' % tex_of(e) for e in sorted(excluded))
    sol = sp.solveset(diff, x, sp.S.Reals)
    sol = [] if sol.is_empty else sol
    assert sol == [] or isinstance(sol, sp.FiniteSet), (tex, sol)
    rs = sorted([r for r in sol if r not in excluded], key=float)
    for r in rs:                                   # подстановка в исходное уравнение
        assert abs(complex(sp.N(diff.subs(x, r)))) < 1e-20
    if rs:
        return roots_tex(rs)
    # корней нет: был ли посторонний корень (обнуляет знаменатель)?
    dens = [node.base ** (-node.exp) for node in sp.preorder_traversal(diff)
            if isinstance(node, sp.Pow) and node.exp.is_negative and node.base.has(x)]
    lcd = sp.lcm_list([sp.factor(d) for d in dens])
    raw = sp.cancel(sp.expand(diff * lcd))         # умножили на общий знаменатель
    cand = sp.solveset(raw, x, sp.S.Reals)
    dropped = sorted(set(cand) & excluded) if isinstance(cand, sp.FiniteSet) else []
    if dropped:
        return 'корней нет (получается $x=%s$, но при нём знаменатель равен 0)' % tex_of(dropped[0])
    return 'корней нет'


def equations_tasks():
    out = [Task('$' + e + '$', eq_answer(e)) for e in EQS]
    out.append(Task('При каком значении $a$ уравнение $(a-2)x=a+1$ не имеет корней? '
                    'При каком значении $a$ его корень равен 4?',
                    check_param_linear(), wide=True))
    return out


def check_param_linear():
    # (a-2)x = a+1: нет корней <=> a-2=0 и a+1!=0; корень 4 <=> 4(a-2)=a+1
    a = sp.Symbol('a')
    no_roots = [v for v in sp.solve(a - 2, a) if v + 1 != 0]
    four = sp.solve(4 * (a - 2) - (a + 1), a)
    assert no_roots == [2] and four == [3]
    return 'нет корней при $a=2$; корень 4 при $a=3$'


# ------------------------------------------------------------ документ

def build(name, with_equations):
    doc = Doc(name.lower(), f'{name}, 8 класс', 'Домашнее задание · физика и алгебра')
    doc.h('Физика. Количество теплоты: $Q = cm(t_2 - t_1)$')
    doc.p('Записывайте «Дано», переводите граммы в килограммы, а килоджоули в джоули. '
          'Ответ — с единицами измерения.')
    doc.tasks(physics())
    doc.h('Физика. Видео на следующие темы')
    doc.p('Это то, что будем проходить дальше. Посмотрите по порядку и выпишите в тетрадь '
          'новые формулы и что означает каждая буква.')
    doc.videos(VIDEOS_PHYS)
    doc.h('Алгебра. Дроби: действия с числами')
    doc.p('Сначала действия в скобках, потом умножение и деление слева направо, потом сложение и вычитание. '
          'Ответ — несократимая дробь или целое число.')
    doc.tasks(numeric_tasks(), cols=2, answer_cols=4)
    doc.h('Алгебра. Рациональные дроби')
    doc.p('Упростите выражение. Прежде чем приводить к общему знаменателю или умножать, '
          'разложите все числители и знаменатели на множители.')
    doc.tasks(algebraic_tasks(), cols=2, answer_cols=3)
    if with_equations:
        doc.h('Алгебра. Уравнения')
        doc.p('Решите уравнение. В уравнениях с дробями сначала выпишите, каким $x$ быть нельзя, '
              'и в конце проверьте корни. Бывает, что корней нет или их бесконечно много — '
              'это тоже ответ.')
        doc.tasks(equations_tasks(), cols=2, answer_cols=3)
    return doc


def build_anton():
    return build('Антон', False)


def build_stas():
    return build('Стас', True)
