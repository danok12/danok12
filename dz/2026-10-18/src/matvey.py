"""Матвей, 11 класс: вся тригонометрия (справочник, формулы приведения, часть 1 и часть 2),
разбор прототипа задания 14 с образцовым оформлением, параметры от начальных к средним."""
import random

import sympy as sp

from common import Doc, Task, to_sympy, same, value, fmt_num, ege_task, tex_of, x
from params import matvey as matvey_params
from trig import verify, on_segment, pts_tex, PI

al, be = sp.symbols('alpha beta', real=True)


# ------------------------------------------------------------ справочник

FORMULAS = [
    ('Основные тождества', [
        r'\sin^2\alpha+\cos^2\alpha=1',
        r'\tg\alpha=\frac{\sin\alpha}{\cos\alpha}',
        r'\ctg\alpha=\frac{\cos\alpha}{\sin\alpha}',
        r'\tg\alpha\cdot\ctg\alpha=1',
        r'1+\tg^2\alpha=\frac{1}{\cos^2\alpha}',
        r'1+\ctg^2\alpha=\frac{1}{\sin^2\alpha}',
    ]),
    ('Чётность', [
        r'\sin(-\alpha)=-\sin\alpha',
        r'\cos(-\alpha)=\cos\alpha',
        r'\tg(-\alpha)=-\tg\alpha',
    ]),
    ('Сложение', [
        r'\sin(\alpha\pm\beta)=\sin\alpha\cos\beta\pm\cos\alpha\sin\beta',
        r'\cos(\alpha\pm\beta)=\cos\alpha\cos\beta\mp\sin\alpha\sin\beta',
        r'\tg(\alpha\pm\beta)=\frac{\tg\alpha\pm\tg\beta}{1\mp\tg\alpha\tg\beta}',
    ]),
    ('Двойной и тройной угол', [
        r'\sin2\alpha=2\sin\alpha\cos\alpha',
        r'\cos2\alpha=\cos^2\alpha-\sin^2\alpha',
        r'\cos2\alpha=2\cos^2\alpha-1',
        r'\cos2\alpha=1-2\sin^2\alpha',
        r'\tg2\alpha=\frac{2\tg\alpha}{1-\tg^2\alpha}',
        r'\sin3\alpha=3\sin\alpha-4\sin^3\alpha',
        r'\cos3\alpha=4\cos^3\alpha-3\cos\alpha',
    ]),
    ('Понижение степени', [
        r'\sin^2\alpha=\frac{1-\cos2\alpha}{2}',
        r'\cos^2\alpha=\frac{1+\cos2\alpha}{2}',
    ]),
    ('Сумма и разность в произведение', [
        r'\sin\alpha+\sin\beta=2\sin\frac{\alpha+\beta}{2}\cos\frac{\alpha-\beta}{2}',
        r'\sin\alpha-\sin\beta=2\sin\frac{\alpha-\beta}{2}\cos\frac{\alpha+\beta}{2}',
        r'\cos\alpha+\cos\beta=2\cos\frac{\alpha+\beta}{2}\cos\frac{\alpha-\beta}{2}',
        r'\cos\alpha-\cos\beta=-2\sin\frac{\alpha+\beta}{2}\sin\frac{\alpha-\beta}{2}',
    ]),
    ('Произведение в сумму', [
        r'\sin\alpha\sin\beta=\frac{1}{2}\left(\cos(\alpha-\beta)-\cos(\alpha+\beta)\right)',
        r'\cos\alpha\cos\beta=\frac{1}{2}\left(\cos(\alpha-\beta)+\cos(\alpha+\beta)\right)',
        r'\sin\alpha\cos\beta=\frac{1}{2}\left(\sin(\alpha+\beta)+\sin(\alpha-\beta)\right)',
    ]),
    ('Через тангенс половинного угла', [
        r'\sin\alpha=\frac{2\tg\frac{\alpha}{2}}{1+\tg^2\frac{\alpha}{2}}',
        r'\cos\alpha=\frac{1-\tg^2\frac{\alpha}{2}}{1+\tg^2\frac{\alpha}{2}}',
    ]),
]


def check_formulas():
    """Каждую формулу проверяем численно в случайных точках (± разворачиваем в два случая)."""
    for _, fs in FORMULAS:
        for f in fs:
            variants = [f]
            if r'\pm' in f:
                variants = [f.replace(r'\pm', '+').replace(r'\mp', '-'),
                            f.replace(r'\pm', '-').replace(r'\mp', '+')]
            for v in variants:
                e = to_sympy(v.replace(r'\alpha', ' a ').replace(r'\beta', ' b '))
                d = e.lhs - e.rhs
                for _ in range(8):
                    pt = {s: random.uniform(-3, 3) for s in d.free_symbols}
                    assert abs(complex(d.subs(pt).evalf())) < 1e-9, (v, pt)


ANGLES = [0, PI / 6, PI / 4, PI / 3, PI / 2, PI, 3 * PI / 2]


def values_table():
    def cell(v):
        if v is sp.zoo or v.has(sp.zoo):
            return '—'
        return '$' + tex_of(sp.nsimplify(v)) + '$'
    rows = ['<tr><th>$\\alpha$</th>' + ''.join('<th>$%s$</th>' % tex_of(a) for a in ANGLES) + '</tr>']
    for name, fn in [('\\sin', sp.sin), ('\\cos', sp.cos), ('\\tg', sp.tan), ('\\ctg', sp.cot)]:
        rows.append('<tr><td>$%s\\alpha$</td>' % name + ''.join('<td>%s</td>' % cell(fn(a)) for a in ANGLES) + '</tr>')
    return '<table class="t">' + ''.join(rows) + '</table>'


RED_ARGS = [PI / 2 - al, PI / 2 + al, PI - al, PI + al, 3 * PI / 2 - al, 3 * PI / 2 + al, 2 * PI - al]
RED_ARGS_TEX = [r'\frac{\pi}{2}-\alpha', r'\frac{\pi}{2}+\alpha', r'\pi-\alpha', r'\pi+\alpha',
                r'\frac{3\pi}{2}-\alpha', r'\frac{3\pi}{2}+\alpha', r'2\pi-\alpha']


def reduction_table():
    rows = ['<tr><th></th>' + ''.join('<th>$%s$</th>' % t for t in RED_ARGS_TEX) + '</tr>']
    for name, fn in [('\\sin', sp.sin), ('\\cos', sp.cos), ('\\tg', sp.tan), ('\\ctg', sp.cot)]:
        cells = []
        for arg in RED_ARGS:
            v = fn(arg)                               # sympy сам применяет формулы приведения
            cells.append('<td>$%s$</td>' % tex_of(v).replace(r'\alpha', r'\alpha'))
        rows.append('<tr><td>$%s$</td>' % name + ''.join(cells) + '</tr>')
    return '<table class="t">' + ''.join(rows) + '</table>'


def reference(doc):
    doc.h('Справочник: все формулы')
    doc.p('Не заучивайте подряд: прочитайте, закройте и восстановите каждую группу на черновике. '
          'Какие формулы не вспомнились — выпишите на отдельную карточку.')
    parts = []
    for title, fs in FORMULAS:
        parts.append('<div class="fg"><b>%s.</b>%s</div>' % (title, ''.join('<div class="f">$%s$</div>' % f for f in fs)))
    parts.append('<p class="fg"><b>Период.</b> У $\\sin$ и $\\cos$ период $2\\pi$, у $\\tg$ и $\\ctg$ — $\\pi$.</p>')
    parts.append('<p class="fg"><b>Вспомогательный угол.</b><br>$a\\sin x+b\\cos x=\\sqrt{a^2+b^2}\\,\\sin(x+\\varphi)$, '
                 'где $\\cos\\varphi=\\frac{a}{\\sqrt{a^2+b^2}}$, $\\sin\\varphi=\\frac{b}{\\sqrt{a^2+b^2}}$.</p>')
    doc.raw('<div class="formulas">' + ''.join(parts) + '</div>')
    doc.h('Значения', 3)
    doc.raw(values_table())
    doc.h('Формулы приведения', 3)
    doc.p('Правило: 1) если в аргументе $\\frac{\\pi}{2}$ или $\\frac{3\\pi}{2}$, функция меняется на «кофункцию» '
          '($\\sin\\leftrightarrow\\cos$, $\\tg\\leftrightarrow\\ctg$), если $\\pi$ или $2\\pi$ — не меняется; '
          '2) знак ставим тот, который имеет <i>исходная</i> функция в этой четверти, считая $\\alpha$ острым углом.')
    doc.raw(reduction_table())
    doc.h('Простейшие уравнения ($n\\in\\mathbb{Z}$)', 3)
    doc.raw('<div class="formulas">'
            '<p>$\\sin x=a,\\ |a|\\le1$: $x=\\arcsin a+2\\pi n$ или $x=\\pi-\\arcsin a+2\\pi n$</p>'
            '<p>$\\cos x=a,\\ |a|\\le1$: $x=\\pm\\arccos a+2\\pi n$</p>'
            '<p>$\\tg x=a$: $x=\\arctg a+\\pi n$</p>'
            '<p>$\\sin x=0$: $x=\\pi n$; $\\sin x=\\pm1$: $x=\\pm\\frac{\\pi}{2}+2\\pi n$</p>'
            '<p>$\\cos x=0$: $x=\\frac{\\pi}{2}+\\pi n$; $\\cos x=1$: $x=2\\pi n$; $\\cos x=-1$: $x=\\pi+2\\pi n$</p>'
            '<p>$\\arcsin(-a)=-\\arcsin a$, $\\arccos(-a)=\\pi-\\arccos a$, $\\arctg(-a)=-\\arctg a$</p>'
            '</div>')
    check_formulas()
    # таблица значений арк-функций проверяется sympy автоматически при сборке справочника


# ------------------------------------------------------------ формулы приведения

REDUCTION = [
    (r'\sin(\pi+\alpha)', r'-\sin\alpha'),
    (r'\cos\left(\frac{\pi}{2}+\alpha\right)', r'-\sin\alpha'),
    (r'\tg\left(\frac{3\pi}{2}-\alpha\right)', r'\ctg\alpha'),
    (r'\cos(2\pi-\alpha)', r'\cos\alpha'),
    (r'\sin\left(\frac{3\pi}{2}+\alpha\right)', r'-\cos\alpha'),
    (r'\ctg(\pi-\alpha)', r'-\ctg\alpha'),
    (r'\sin(\alpha-\pi)', r'-\sin\alpha'),
    (r'\cos\left(\alpha-\frac{3\pi}{2}\right)', r'-\sin\alpha'),
    (r'\tg\left(\frac{5\pi}{2}+\alpha\right)', r'-\ctg\alpha'),
    (r'\sin\left(\frac{7\pi}{2}-\alpha\right)', r'-\cos\alpha'),
    (r'\cos 300^\circ', None),
    (r'\sin 210^\circ', None),
    (r'\tg 135^\circ', None),
    (r'\cos(-240^\circ)', None),
    (r'\sin 750^\circ', None),
    (r'\ctg\frac{5\pi}{3}', None),
]


def reduction_tasks():
    out = []
    for tex, ans in REDUCTION:
        e = to_sympy(tex.replace(r'\alpha', ' a '))
        if ans is None:
            v = sp.nsimplify(sp.simplify(e))
            out.append(Task('$' + tex + '$', '$' + tex_of(v) + '$'))
        else:
            assert same(e, to_sympy(ans.replace(r'\alpha', ' a '))), (tex, ans)
            out.append(Task('$' + tex + '$', '$' + ans + '$'))
    return out


# ------------------------------------------------------------ часть 1: вычисления

# (выражение, ответ, посчитанный вручную) — сверяются друг с другом
CALC = [
    (r'\frac{12\sin 11^\circ}{\sin 349^\circ}', -12),
    (r'\frac{5\cos 29^\circ}{\sin 61^\circ}', 5),
    (r'\frac{24(\sin^2 17^\circ-\cos^2 17^\circ)}{\cos 34^\circ}', -24),
    (r'\frac{10\sin 6^\circ\cos 6^\circ}{\sin 12^\circ}', 5),
    (r'-18\sqrt{2}\sin(-135^\circ)', 18),
    (r'4\sqrt{3}\cos^2\frac{13\pi}{12}-2\sqrt{3}', 3),
    (r'\sqrt{48}-\sqrt{192}\sin^2\frac{19\pi}{12}', -6),
]


def angle_in(cos_val=None, sin_val=None, lo=None, hi=None):
    """Угол из интервала (lo, hi) с данным косинусом (или синусом)."""
    if cos_val is not None:
        cands = sp.solveset(sp.cos(x) - cos_val, x, sp.Interval.open(lo, hi))
    else:
        cands = sp.solveset(sp.sin(x) - sin_val, x, sp.Interval.open(lo, hi))
    (r,) = list(cands)
    return r


def calc_tasks():
    out = []
    for tex, hand in CALC:
        v = sp.nsimplify(sp.simplify(to_sympy(tex)))
        num = float(to_sympy(tex).evalf())
        assert abs(num - float(v)) < 1e-12 and v == hand, (tex, v, hand)
        out.append(Task('$\\displaystyle ' + tex + '$', fmt_num(v)))
    A = angle_in(cos_val=sp.Rational(-4, 5), lo=PI, hi=3 * PI / 2)
    out.append(Task('Найдите $\\tg\\alpha$, если $\\cos\\alpha=-0{,}8$ и $\\alpha\\in\\left(\\pi;\\,\\frac{3\\pi}{2}\\right)$.',
                    fmt_num(sp.nsimplify(sp.tan(A)))))
    A = angle_in(cos_val=2 * sp.sqrt(6) / 5, lo=3 * PI / 2, hi=2 * PI)
    out.append(Task('Найдите $5\\sin\\alpha$, если $\\cos\\alpha=\\frac{2\\sqrt6}{5}$ и $\\alpha\\in\\left(\\frac{3\\pi}{2};\\,2\\pi\\right)$.',
                    fmt_num(sp.nsimplify(5 * sp.sin(A)))))
    A = angle_in(cos_val=sp.Rational(12, 13), lo=3 * PI / 2, hi=2 * PI)
    out.append(Task('Найдите $26\\cos\\left(\\frac{3\\pi}{2}+\\alpha\\right)$, если $\\cos\\alpha=\\frac{12}{13}$ и '
                    '$\\alpha\\in\\left(\\frac{3\\pi}{2};\\,2\\pi\\right)$.',
                    fmt_num(sp.nsimplify(26 * sp.cos(3 * PI / 2 + A)))))
    A = sp.atan(3)                                   # tg = 3; выражение от четверти не зависит
    e = (3 * sp.cos(A) - 4 * sp.sin(A)) / (2 * sp.sin(A) - 5 * sp.cos(A))
    out.append(Task('Найдите $\\dfrac{3\\cos\\alpha-4\\sin\\alpha}{2\\sin\\alpha-5\\cos\\alpha}$, если $\\tg\\alpha=3$.',
                    fmt_num(sp.nsimplify(sp.simplify(e)))))
    e = to_sympy(r'\frac{2\sin(a-7\pi)+\cos(\frac{3\pi}{2}+a)}{\sin(a+\pi)}')
    out.append(Task('Найдите значение выражения $\\dfrac{2\\sin(\\alpha-7\\pi)+\\cos\\left(\\frac{3\\pi}{2}+\\alpha\\right)}'
                    '{\\sin(\\alpha+\\pi)}$.', fmt_num(sp.simplify(e))))
    # sin a + cos a = 1,2 -> sin 2a = 1,2^2 - 1
    s = sp.Rational(6, 5)
    sols = sp.solve([sp.Symbol('s') + sp.Symbol('c') - s, sp.Symbol('s') ** 2 + sp.Symbol('c') ** 2 - 1],
                    [sp.Symbol('s'), sp.Symbol('c')])
    vals = {sp.nsimplify(2 * a * b) for a, b in sols}
    assert len(vals) == 1
    out.append(Task('Найдите $\\sin2\\alpha$, если $\\sin\\alpha+\\cos\\alpha=1{,}2$.', fmt_num(vals.pop())))
    return out


TRIG7 = [
    (r'\sin\frac{\pi(x+2)}{3}=\frac{\sqrt{3}}{2}', 'minpos'),
    (r'\tg\frac{\pi(x-3)}{6}=\sqrt{3}', 'maxneg'),
    (r'\cos\frac{\pi x}{6}=-\frac{1}{2}', 'minpos'),
    (r'\sin\frac{\pi(4x-1)}{4}=-1', 'maxneg'),
]


# ------------------------------------------------------------ часть 2: задание 14

S, C = sp.sin(x), sp.cos(x)
r3, r2 = sp.sqrt(3), sp.sqrt(2)

# (условие а), выражение f, серии [(смещение, период)], ответ а) LaTeX, отрезок б) (L, R, LaTeX), ОДЗ)
PART2 = [
    (r'2\sin^2x+3\cos x-3=0', 2 * S ** 2 + 3 * C - 3,
     [(0, 2 * PI), (PI / 3, 2 * PI), (-PI / 3, 2 * PI)],
     r'2\pi n;\ \pm\frac{\pi}{3}+2\pi k,\ n,k\in\mathbb{Z}',
     (-3 * PI, -3 * PI / 2, r'\left[-3\pi;\,-\frac{3\pi}{2}\right]'), ()),
    (r'\cos2x+3\sin x=2', sp.cos(2 * x) + 3 * S - 2,
     [(PI / 2, 2 * PI), (PI / 6, 2 * PI), (5 * PI / 6, 2 * PI)],
     r'\frac{\pi}{2}+2\pi n;\ \frac{\pi}{6}+2\pi k;\ \frac{5\pi}{6}+2\pi k,\ n,k\in\mathbb{Z}',
     (2 * PI, 7 * PI / 2, r'\left[2\pi;\,\frac{7\pi}{2}\right]'), ()),
    (r'2\sin^2x=\sqrt{3}\sin2x', 2 * S ** 2 - r3 * sp.sin(2 * x),
     [(0, PI), (PI / 3, PI)],
     r'\pi n;\ \frac{\pi}{3}+\pi k,\ n,k\in\mathbb{Z}',
     (3 * PI / 2, 3 * PI, r'\left[\frac{3\pi}{2};\,3\pi\right]'), ()),
    (r'\sin^2x-4\sin x\cos x+3\cos^2x=0', S ** 2 - 4 * S * C + 3 * C ** 2,
     [(PI / 4, PI), (sp.atan(3), PI)],
     r'\frac{\pi}{4}+\pi n;\ \arctg3+\pi k,\ n,k\in\mathbb{Z}',
     (PI, 2 * PI, r'\left[\pi;\,2\pi\right]'), ()),
    (r'\cos\left(\frac{\pi}{2}+2x\right)=\sqrt{2}\sin x', sp.cos(PI / 2 + 2 * x) - r2 * S,
     [(0, PI), (3 * PI / 4, 2 * PI), (-3 * PI / 4, 2 * PI)],
     r'\pi n;\ \pm\frac{3\pi}{4}+2\pi k,\ n,k\in\mathbb{Z}',
     (-5 * PI / 2, -PI, r'\left[-\frac{5\pi}{2};\,-\pi\right]'), ()),
    (r'9^{\cos x}-4\cdot3^{\cos x}+3=0', 9 ** C - 4 * 3 ** C + 3,
     [(PI / 2, PI), (0, 2 * PI)],
     r'\frac{\pi}{2}+\pi n;\ 2\pi k,\ n,k\in\mathbb{Z}',
     (-7 * PI / 2, -2 * PI, r'\left[-\frac{7\pi}{2};\,-2\pi\right]'), ()),
    (r'\dfrac{2\sin^2x-\sin x}{2\cos x-\sqrt{3}}=0', (2 * S ** 2 - S) / (2 * C - r3),
     [(0, PI), (5 * PI / 6, 2 * PI)],
     r'\pi n;\ \frac{5\pi}{6}+2\pi k,\ n,k\in\mathbb{Z}',
     (-3 * PI / 2, PI / 2, r'\left[-\frac{3\pi}{2};\,\frac{\pi}{2}\right]'), [('ne0', 2 * C - r3)]),
    (r'(2\sin x+1)\sqrt{-\cos x}=0', (2 * S + 1) * sp.sqrt(-C),
     [(PI / 2, PI), (7 * PI / 6, 2 * PI)],
     r'\frac{\pi}{2}+\pi n;\ \frac{7\pi}{6}+2\pi k,\ n,k\in\mathbb{Z}',
     (PI, 5 * PI / 2, r'\left[\pi;\,\frac{5\pi}{2}\right]'), [('ge0', -C)]),
]


def part2_tasks():
    out = []
    for cond, f, series, ans_a, (L, R, seg), conds in PART2:
        series = [(sp.sympify(o), sp.sympify(p)) for o, p in series]
        verify(f, series, conds)
        pts = on_segment(series, L, R)
        assert 2 <= len(pts) <= 4, (cond, pts)
        out.append(Task('а) Решите уравнение $%s$.<br>б) Найдите все корни этого уравнения, принадлежащие отрезку $%s$.'
                        % (cond, seg),
                        'а) $%s$; б) $%s$' % (ans_a, pts_tex(pts))))
    return out


# ------------------------------------------------------------ разбор прототипа

def prototype(doc):
    f = sp.cos(2 * x) + sp.sin(PI / 2 + x) + 1
    series = [(PI / 2, PI), (2 * PI / 3, 2 * PI), (-2 * PI / 3, 2 * PI)]
    verify(f, series)
    pts = on_segment(series, -3 * PI, -3 * PI / 2)
    assert pts == [-8 * PI / 3, -5 * PI / 2, -3 * PI / 2], pts
    # двойные неравенства из разбора
    n = [k for k in range(-10, 10) if -3 <= sp.Rational(1, 2) + k <= sp.Rational(-3, 2)]
    k1 = [k for k in range(-10, 10) if -3 <= sp.Rational(2, 3) + 2 * k <= sp.Rational(-3, 2)]
    k2 = [k for k in range(-10, 10) if -3 <= sp.Rational(-2, 3) + 2 * k <= sp.Rational(-3, 2)]
    assert n == [-3, -2] and k1 == [] and k2 == [-1]
    doc.h('Разбор прототипа задания 14 — образец оформления')
    doc.p('Так должно выглядеть решение на чистовике. Прочитайте, закройте, решите сами и сравните.')
    doc.raw(r'''<div class="box">
<p><b>Задача.</b> а) Решите уравнение $\cos2x+\sin\left(\frac{\pi}{2}+x\right)+1=0$.<br>
б) Найдите все корни этого уравнения, принадлежащие отрезку $\left[-3\pi;\,-\frac{3\pi}{2}\right]$.</p>
<p><b>Решение.</b> а) По формуле приведения $\sin\left(\frac{\pi}{2}+x\right)=\cos x$,
по формуле косинуса двойного угла $\cos2x=2\cos^2x-1$. Уравнение принимает вид</p>
<p style="text-align:center">$2\cos^2x-1+\cos x+1=0;\qquad 2\cos^2x+\cos x=0;\qquad \cos x\,(2\cos x+1)=0.$</p>
<p>Произведение равно нулю, когда хотя бы один из множителей равен нулю (оба множителя определены при всех $x$):</p>
<p>1) $\cos x=0$, откуда $x=\frac{\pi}{2}+\pi n,\ n\in\mathbb{Z}$;</p>
<p>2) $\cos x=-\frac{1}{2}$, откуда $x=\pm\frac{2\pi}{3}+2\pi k,\ k\in\mathbb{Z}$.</p>
<p>б) Отберём корни, принадлежащие отрезку $\left[-3\pi;\,-\frac{3\pi}{2}\right]$, с помощью двойных неравенств.</p>
<p>1) $-3\pi\le\frac{\pi}{2}+\pi n\le-\frac{3\pi}{2}\ \Leftrightarrow\ -3\le\frac12+n\le-\frac32\ \Leftrightarrow\
-\frac72\le n\le-2$. Так как $n\in\mathbb{Z}$, то $n=-3$ или $n=-2$, откуда $x=-\frac{5\pi}{2}$ и $x=-\frac{3\pi}{2}$.</p>
<p>2) $-3\pi\le\frac{2\pi}{3}+2\pi k\le-\frac{3\pi}{2}\ \Leftrightarrow\ -\frac{11}{3}\le2k\le-\frac{13}{6}\ \Leftrightarrow\
-\frac{11}{6}\le k\le-\frac{13}{12}$. Целых $k$ на этом промежутке нет.</p>
<p>3) $-3\pi\le-\frac{2\pi}{3}+2\pi k\le-\frac{3\pi}{2}\ \Leftrightarrow\ -\frac{7}{3}\le2k\le-\frac{5}{6}\ \Leftrightarrow\
-\frac{7}{6}\le k\le-\frac{5}{12}$, откуда $k=-1$ и $x=-\frac{2\pi}{3}-2\pi=-\frac{8\pi}{3}$.</p>
<p><b>Ответ:</b> а) $\frac{\pi}{2}+\pi n,\ \pm\frac{2\pi}{3}+2\pi k,\ n,k\in\mathbb{Z}$;
б) $-\frac{8\pi}{3};\ -\frac{5\pi}{2};\ -\frac{3\pi}{2}$.</p>
</div>''')
    doc.p('<b>На что смотрит эксперт.</b> 1) Каждое преобразование названо: «по формуле приведения», '
          '«по формуле двойного угла». 2) У каждой серии указано $n\\in\\mathbb{Z}$, у разных серий — разные буквы. '
          '3) В пункте б) виден способ отбора: двойные неравенства или единичная окружность с отмеченной дугой. '
          'Голый список корней без отбора не засчитают. 4) Ответ записан полностью, по обоим пунктам.')


# ------------------------------------------------------------ документ

def build():
    doc = Doc('matvey', 'Матвей, 11 класс', 'Домашнее задание · тригонометрия и параметры')
    reference(doc)
    doc.pagebreak()
    doc.h('Формулы приведения')
    doc.p('Упростите выражение или найдите значение. Сначала по правилу, без таблицы. Таблицей проверяйте себя.')
    doc.tasks(reduction_tasks(), cols=3, answer_cols=4)
    doc.h('Часть 1. Задание 8: вычисления')
    doc.p('Найдите значение выражения. Ответ — целое число или конечная десятичная дробь.')
    doc.tasks(calc_tasks(), cols=2, answer_cols=6)
    doc.h('Часть 1. Задание 7: простейшие тригонометрические уравнения')
    doc.tasks([ege_task(t, r) for t, r in TRIG7], cols=1, answer_cols=4)
    prototype(doc)
    doc.h('Часть 2. Задание 14 (в сборниках прошлых лет — №13)')
    doc.p('Оформляйте как в разборе выше: преобразования с названиями формул, серии с $n\\in\\mathbb{Z}$, '
          'отбор корней с обоснованием.')
    doc.tasks(part2_tasks(), cols=1, answer_cols=1)
    doc.h('Параметры. Задание 19: от простого к среднему')
    doc.p('Только аналитически: разбор случаев, дискриминант, теорема Виета, замена переменной, ОДЗ. '
          'Если старший коэффициент зависит от $a$, сначала отдельно разберите случай, когда он равен нулю.')
    doc.tasks(matvey_params(), cols=1, answer_cols=1)
    return doc
