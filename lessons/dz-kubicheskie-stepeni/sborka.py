"""ДЗ: кубические уравнения (ОГЭ №20, группировка) + степени и корни (уровень 1-й части ЕГЭ).

Один источник задач: печатный HTML (ученику), ZADACHI.md и OTVETY.md собираются отсюда,
каждый ответ перед сборкой проверяется.
  python3 sborka.py        # проверить и собрать zadachi.html, ZADACHI.md, OTVETY.md
"""
from fractions import Fraction as F
from math import sqrt
import html, pathlib

HERE = pathlib.Path(__file__).parent

# ---------- мини-разметка формул: одна строка -> и HTML, и текст ----------
SUP = str.maketrans('0123456789−-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁻')
def sup_txt(e):
    return e.translate(SUP) if all(c in '0123456789−-' for c in e) else f'^({e})' if len(e) > 1 else f'^{e}'
def detag(h):
    import re
    return re.sub(r'<sup>(.*?)</sup>', lambda m: sup_txt(m.group(1)), h)
def atom(t):
    import re
    one = r'([\d,]+|[a-z]|[⁰¹²³⁴⁵⁶⁷⁸⁹]*[√∛∜](\([^()]*\)|\S+))(\^\([^()]*\)|\^\S+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]*)'
    return t if re.fullmatch(one, t) else f'({t})'

def p(h, t=None): return (h, detag(h) if t is None else t)
def fr(a, b):   return (f'<span class="fr"><span>{a[0]}</span><span>{b[0]}</span></span>', f'{atom(a[1])}/{atom(b[1])}')
def rt(x, n=''):
    t = {'': '√', '3': '∛', '4': '∜'}.get(n) or n.translate(SUP) + '√'
    return (f'<span class="rt"><sup>{n}</sup>√<span class="rad">{x[0]}</span></span>',
            f'{t}{x[1]}' if len(x[1]) == 1 or x[1].isdigit() else f'{t}({x[1]})')
def cat(*parts): return (''.join(x[0] for x in parts), ''.join(x[1] for x in parts))
def sup(base, e): return (f'{base[0]}<sup>{e}</sup>', f'{base[1]}{sup_txt(e)}')

# ---------- часть 1: уравнения ----------
# (условие, множество корней в виде (Fraction или ('±√', n)), многочлен P(x) коэффициенты от старшего)
def poly_mul(a, b):
    r = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    return r
def ev(c, x):
    v = 0
    for k in c: v = v * x + k
    return v

X = 'x'
EQ = [
 # условие (html)                                   P(x)=0 (левая минус правая, от старшей)        корни
 ('x<sup>3</sup> + 5x<sup>2</sup> − 4x − 20 = 0',          [1, 5, -4, -20],        [-5, -2, 2]),
 ('x<sup>3</sup> − 3x<sup>2</sup> − 16x + 48 = 0',         [1, -3, -16, 48],       [3, -4, 4]),
 ('x<sup>3</sup> + 2x<sup>2</sup> − 9x − 18 = 0',          [1, 2, -9, -18],        [-2, -3, 3]),
 ('x<sup>3</sup> − 7x<sup>2</sup> − x + 7 = 0',            [1, -7, -1, 7],         [7, -1, 1]),
 ('x<sup>3</sup> + 4x<sup>2</sup> = 25x + 100',            [1, 4, -25, -100],      [-4, -5, 5]),
 ('x<sup>3</sup> − 6x<sup>2</sup> = 4x − 24',              [1, -6, -4, 24],        [6, -2, 2]),
 ('x<sup>3</sup> + 3x<sup>2</sup> − 2x − 6 = 0',           [1, 3, -2, -6],         [-3, ('√', 2)]),
 ('x<sup>3</sup> − 5x<sup>2</sup> + x − 5 = 0',            [1, -5, 1, -5],         [5]),
 ('2x<sup>3</sup> − x<sup>2</sup> − 18x + 9 = 0',          [2, -1, -18, 9],        [F(1, 2), -3, 3]),
 ('3x<sup>3</sup> + 2x<sup>2</sup> − 12x − 8 = 0',         [3, 2, -12, -8],        [F(-2, 3), -2, 2]),
 ('4x<sup>3</sup> − 12x<sup>2</sup> − x + 3 = 0',          [4, -12, -1, 3],        [3, F(-1, 2), F(1, 2)]),
 ('9x<sup>3</sup> + 18x<sup>2</sup> − x − 2 = 0',          [9, 18, -1, -2],        [-2, F(-1, 3), F(1, 3)]),
 ('5x<sup>3</sup> + 4x<sup>2</sup> − 20x − 16 = 0',        [5, 4, -20, -16],       [F(-4, 5), -2, 2]),
 ('x<sup>3</sup> + 3x<sup>2</sup> − 9x − 27 = 0',          [1, 3, -9, -27],        [-3, 3]),
 ('x<sup>3</sup> − 12 = 4x − 3x<sup>2</sup>',              [1, 3, -4, -12],        [-3, -2, 2]),
 ('x<sup>3</sup> − 5x + 2x<sup>2</sup> − 10 = 0',          [1, 2, -5, -10],        [-2, ('√', 5)]),
 ('x(x<sup>2</sup> + 6x + 9) = 4(x + 3)',                   [1, 6, 5, -12],         [-3, 1, -4]),
 ('(x − 2)(x<sup>2</sup> + 5x + 4) = 10(x − 2)',            [1, 3, -16, 12],        [2, 1, -6]),
 ('x<sup>3</sup> + 8 = 2x(x + 2)',                          [1, -2, -4, 8],         [-2, 2]),
 ('x<sup>3</sup> − 27 = 13x(x − 3)',                        [1, -13, 39, -27],      [3, 1, 9]),
 ('x<sup>4</sup> + 3x<sup>3</sup> − 8x − 24 = 0',          [1, 3, 0, -8, -24],     [-3, 2]),
 ('x<sup>4</sup> − 2x<sup>3</sup> + x − 2 = 0',            [1, -2, 0, 1, -2],      [2, -1]),
]

def lhs_minus_rhs(cond):
    """Разобрать условие как функцию x (для сверки P(x) с текстом)."""
    s = (cond.replace('<sup>', '**').replace('</sup>', '').replace('−', '-')
             .replace('x(', 'x*(').replace(')(', ')*(').replace(' ', ''))
    import re
    s = re.sub(r'(\d)x', r'\1*x', s)
    s = re.sub(r'(\d)\(', r'\1*(', s)
    l, r = s.split('=')
    return lambda x: eval(l, {'x': x}) - eval(r, {'x': x})

def check_eq():
    out = []
    for i, (cond, P, roots) in enumerate(EQ, 1):
        f = lhs_minus_rhs(cond)
        # текст условия = P(x) на 7 точках (степень ≤ 4 -> совпадение многочленов)
        for t in range(-3, 4):
            assert f(F(t)) == ev([F(c) for c in P], F(t)), (i, t)
        # все корни: рациональные — точная подстановка, ±√n — через деление на x²−n
        rat = [F(r) for r in roots if not isinstance(r, tuple)]
        irr = [r[1] for r in roots if isinstance(r, tuple)]
        for r in rat: assert ev([F(c) for c in P], r) == 0, (i, r)
        # проверка, что корней ровно столько: P = lead·Π(x−r)^k · Q, Q без действительных корней
        Q = [F(c) for c in P]
        def divide(Q, d):
            q, rem = [], F(0)
            for c in Q:
                rem = rem * d + c; q.append(rem)
            assert q[-1] == 0; return q[:-1]
        for r in rat:
            while len(Q) > 1 and ev(Q, r) == 0: Q = divide(Q, r)
        for n in irr:  # деление на x² − n
            Q2 = Q[:]
            quo = []
            while len(Q2) >= 3:
                c = Q2[0]; quo.append(c)
                Q2 = [Q2[1], Q2[2] + c * n] + Q2[3:]
            assert all(v == 0 for v in Q2), (i, n)
            Q = quo
        # остаток: константа или квадратный трёхчлен с D<0
        if len(Q) == 3:
            a, b, c = Q; assert b * b - 4 * a * c < 0, (i, Q)
        else:
            assert len(Q) == 1, (i, Q)
        txt = []
        for r in rat: txt.append(str(r).replace('/', '/') if r.denominator != 1 else str(r))
        for n in irr: txt.append(f'±√{n}')
        out.append('; '.join(txt))
    return out

# ---------- часть 2: выражения ----------
N = p
EX = []  # (html, text, значение, ответ)
def add(expr, val, ans):
    v = round(float(val), 9)
    assert abs(v - float(ans)) < 1e-9, (expr[1], v, ans)
    EX.append((expr[0], expr[1], ans))

add(cat(sup(N('5'), '0,36'), N(' · '), sup(N('25'), '0,32')),                 5 ** 0.36 * 25 ** 0.32, 5)
add(fr(sup(N('12'), '3,4'), cat(sup(N('3'), '1,4'), N(' · '), sup(N('4'), '2,4'))), 12 ** 3.4 / (3 ** 1.4 * 4 ** 2.4), 36)
add(fr(sup(N('10'), '4,7'), cat(sup(N('2'), '2,7'), N(' · '), sup(N('5'), '3,7'))), 10 ** 4.7 / (2 ** 2.7 * 5 ** 3.7), 20)
add(fr(cat(sup(N('2'), '3,5'), N(' · '), sup(N('3'), '5,5')), sup(N('6'), '4,5')),  2 ** 3.5 * 3 ** 5.5 / 6 ** 4.5, 1.5)
add(fr(cat(sup(N('(2<sup>−3</sup>)'), '2'), N(' · '), sup(N('16'), '2')), sup(N('8'), '−1')), F(1, 2**6) * 256 / F(1, 8), 32)
add(fr(cat(sup(N('3'), '−5'), N(' · '), sup(N('9'), '4')), N('3')),             F(1, 3**5) * 9**4 / 3, 9)
add(cat(sup(N('(1¼)'), '−2'), N(' · '), sup(N('0,8'), '−3')),                   F(5, 4) ** -2 * F(4, 5) ** -3, 1.25)
add(cat(N('(4,5 · 10<sup>−3</sup>) · (2 · 10<sup>5</sup>)')),                     F(45, 10000) * 200000, 900)
add(fr(sup(N('(7<sup>1/3</sup> · 7<sup>1/4</sup>)'), '12'), sup(N('7'), '6')),   (7 ** (1/3) * 7 ** 0.25) ** 12 / 7 ** 6, 7)
add(cat(sup(N('1,5'), '1/4'), N(' · '), sup(N('2'), '1/2'), N(' · '), sup(N('6'), '3/4')), 1.5 ** 0.25 * 2 ** 0.5 * 6 ** 0.75, 6)
add(cat(rt(N('25'), '3'), N(' · '), rt(N('25'), '6')),                           25 ** (1/3) * 25 ** (1/6), 5)
add(cat(rt(N('12'), '3'), N(' · '), rt(N('18'), '3')),                           (12 * 18) ** (1/3), 6)
add(fr(rt(N('48'), '4'), rt(N('3'), '4')),                                       (48 / 3) ** 0.25, 2)
add(fr(cat(rt(N('2,8')), N(' · '), rt(N('4,2'))), rt(N('0,24'))),                sqrt(2.8) * sqrt(4.2) / sqrt(0.24), 7)
add(fr(sup(N('(' + rt(N('3'), '3')[0] + ' · ' + rt(N('3'))[0] + ')', '(∛3 · √3)'), '6'), sup(N('3'), '4')), (3 ** (1/3) * 3 ** 0.5) ** 6 / 81, 3)
add(cat(rt(N('65<sup>2</sup> − 56<sup>2</sup>', '65² − 56²'))),                    sqrt(65**2 - 56**2), 33)
add(cat(rt(N('3' + fr(N('6'), N('25'))[0], '3 6/25')), N(' − '), rt(N('1' + fr(N('11'), N('25'))[0], '1 11/25'))),
    sqrt(3 + 6/25) - sqrt(1 + 11/25), 0.6)
add(N('(' + rt(N('13'))[0] + ' − ' + rt(N('5'))[0] + ')(' + rt(N('13'))[0] + ' + ' + rt(N('5'))[0] + ')', '(√13 − √5)(√13 + √5)'), (sqrt(13) - sqrt(5)) * (sqrt(13) + sqrt(5)), 8)
add(sup(N('(' + rt(N('18'))[0] + ' − ' + rt(N('8'))[0] + ')', '(√18 − √8)'), '2'),        (sqrt(18) - sqrt(8)) ** 2, 2)
add(fr(N(rt(N('75'))[0] + ' − ' + rt(N('12'))[0], '√75 − √12'), rt(N('3'))),              (sqrt(75) - sqrt(12)) / sqrt(3), 3)
add(cat(sup(N('(' + rt(N('11'))[0] + ' − 3)', '(√11 − 3)'), '2'), N(' + 6'), rt(N('11'))), (sqrt(11) - 3) ** 2 + 6 * sqrt(11), 20)
add(cat(fr(N('4'), N(rt(N('5'))[0] + ' − 1', '√5 − 1')), N(' − '), rt(N('5'))),          4 / (sqrt(5) - 1) - sqrt(5), 1)
add(fr(sup(N('(' + rt(N('7'))[0] + ' + ' + rt(N('3'))[0] + ')', '(√7 + √3)'), '2'), N('5 + ' + rt(N('21'))[0], '5 + √21')), (sqrt(7) + sqrt(3)) ** 2 / (5 + sqrt(21)), 2)
add(cat(rt(N('(2 − ' + rt(N('7'))[0] + ')<sup>2</sup>', '(2 − √7)²')), N(' + '), rt(N('(3 − ' + rt(N('7'))[0] + ')<sup>2</sup>', '(3 − √7)²'))),
    abs(2 - sqrt(7)) + abs(3 - sqrt(7)), 1)
add(cat(rt(N('7 − 4' + rt(N('3'))[0], '7 − 4√3')), N(' + '), rt(N('3'))),               sqrt(7 - 4 * sqrt(3)) + sqrt(3), 2)
add(cat(rt(N('11 + 6' + rt(N('2'))[0], '11 + 6√2')), N(' − '), rt(N('2'))),              sqrt(11 + 6 * sqrt(2)) - sqrt(2), 3)
add(cat(rt(N('−0,125'), '3'), N(' + '), rt(N('0,0016'), '4')),                           -0.5 + 0.0016 ** 0.25, -0.3)
add(cat(fr(sup(N('5'), '2√3 + 1'), sup(N('25'), '√3'))),                                  5 ** (2 * sqrt(3) + 1) / 25 ** sqrt(3), 5)

# с переменной
EXV = []
def addv(expr, cond, f, ans, tests):
    for t in tests:
        v = round(float(f(*t)), 9)
        assert abs(v - float(ans)) < 1e-9, (expr[1], t, v, ans)
    EXV.append((expr[0] + ' ' + cond, expr[1] + ' ' + cond, ans))

addv(fr(sup(N('a'), '3,33'), cat(sup(N('a'), '2,11'), N(' · '), sup(N('a'), '0,22'))), 'при a = 7',
     lambda a: a ** 3.33 / (a ** 2.11 * a ** 0.22), 7, [(7,)])
addv(fr(sup(N('(b<sup>√7</sup>)', '(b^√7)'), '√7'), sup(N('b'), '5')), 'при b = 3',
     lambda b: (b ** sqrt(7)) ** sqrt(7) / b ** 5, 9, [(3,)])
addv(fr(cat(sup(N('x'), '−4'), N(' · '), sup(N('(x<sup>3</sup>)', '(x³)'), '3')), sup(N('x'), '6')), 'при x = −2',
     lambda x: F(x) ** -4 * (F(x) ** 3) ** 3 / F(x) ** 6, -0.5, [(-2,)])
addv(fr(cat(sup(N('(3a<sup>2</sup>)', '(3a²)'), '3'), N(' · '), sup(N('a'), '−4')), N('9a<sup>2</sup>', '9a²')), 'при a = 0,37',
     lambda a: (3 * a * a) ** 3 * a ** -4 / (9 * a * a), 3, [(0.37,), (-1.7,)])
addv(fr(cat(rt(N('a'), '9'), N(' · '), rt(N('a'), '18')), cat(N('a · '), rt(N('a'), '6'))), 'при a = 0,25',
     lambda a: a ** (1/9) * a ** (1/18) / (a * a ** (1/6)), 4, [(0.25,)])
addv(fr(rt(N('m')), cat(rt(N('m'), '6'), N(' · '), rt(N('m'), '3'))), 'при m > 0',
     lambda m: sqrt(m) / (m ** (1/6) * m ** (1/3)), 1, [(2.5,), (40,)])
addv(fr(cat(rt(N('x<sup>2</sup>', 'x²'), '3'), N(' · '), rt(N('x'), '6')), rt(N('x'))), 'при x = 125',
     lambda x: x ** (2/3) * x ** (1/6) / sqrt(x), 5, [(125,)])
addv(fr(sup(N('(' + rt(N('a'), '5')[0] + ' · ' + rt(N('b'), '3')[0] + ')', '(⁵√a · ∛b)'), '15'), N('a<sup>2</sup>b<sup>4</sup>', 'a²b⁴')), 'при a = 2, b = 3',
     lambda a, b: (a ** 0.2 * b ** (1/3)) ** 15 / (a ** 2 * b ** 4), 6, [(2, 3)])
addv(fr(rt(N('16a<sup>8</sup>b<sup>4</sup>', '16a⁸b⁴'), '4'), N('a<sup>2</sup>b', 'a²b')), 'при b > 0',
     lambda a, b: (16 * a ** 8 * b ** 4) ** 0.25 / (a ** 2 * b), 2, [(1.3, 2.1), (-0.7, 5)])

# ---------- сборка ----------
def build():
    ans_eq = check_eq()
    n_eq = len(EQ)
    items_eq = ''.join(f'<li>{c}</li>' for c, _, _ in EQ)
    all_ex = EX + EXV
    items_ex = ''.join(f'<li>{h}</li>' for h, _, _ in all_ex)
    page = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Домашнее задание</title>
<style>
@page{{margin:14mm 14mm}}
body{{font-family:"Times New Roman",serif;font-size:13.5pt;color:#000;background:#fff;margin:0}}
h1{{font-size:15pt;margin:0 0 6pt}} h2{{font-size:13.5pt;margin:12pt 0 6pt;break-after:avoid}}
ol{{columns:2;column-gap:10mm;margin:0;padding-left:8mm}}
li{{margin:0 0 11pt;break-inside:avoid;line-height:1.6}}
.fr{{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;margin:0 2px}}
.fr>span:first-child{{border-bottom:1px solid #000;padding:0 3px}} .fr>span:last-child{{padding:0 3px}}
.rt{{white-space:nowrap}} .rt>sup{{font-size:.65em;margin-right:-.25em}}
.rad{{border-top:1px solid #000;padding:0 1px}}
sup{{font-size:.7em}}
</style></head><body>
<h1>Домашнее задание</h1>
<h2>1. Решите уравнение.</h2>
<ol>{items_eq}</ol>
<h2>2. Найдите значение выражения.</h2>
<ol start="{n_eq + 1}">{items_ex}</ol>
</body></html>'''
    (HERE / 'zadachi.html').write_text(page, encoding='utf-8')

    def md_eq(c): return detag(c)
    md = ['# Домашнее задание', '', '## 1. Решите уравнение.', '']
    md += [f'{i}. {md_eq(c)}' for i, (c, _, _) in enumerate(EQ, 1)]
    md += ['', '## 2. Найдите значение выражения.', '']
    md += [f'{i}. {t}' for i, (_, t, _) in enumerate(all_ex, n_eq + 1)]
    (HERE / 'ZADACHI.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    ot = ['# Ответы (только для преподавателя)', '', 'Собрано и проверено скриптом `sborka.py`.', '',
          '## 1. Уравнения', '']
    ot += [f'{i}. {a}' for i, a in enumerate(ans_eq, 1)]
    ot += ['', '## 2. Выражения', '']
    ot += [f'{i}. {str(a).replace(".", ",")}' for i, (_, _, a) in enumerate(all_ex, n_eq + 1)]
    (HERE / 'OTVETY.md').write_text('\n'.join(ot) + '\n', encoding='utf-8')
    print(f'ok: {n_eq} уравнений, {len(all_ex)} выражений')

if __name__ == '__main__':
    build()
