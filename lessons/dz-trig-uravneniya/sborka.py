"""ДЗ 10 класса (профиль): простейшие тригонометрические уравнения и арк-функции.

Один источник задач: печатный лист ученику, ответы с окружностями преподавателю,
ZADACHI.md и OTVETY.md собираются отсюда. Перед сборкой каждая задача проверяется:
  * условие разбирается из того же текста, что печатается, — опечатка в листе не пройдёт;
  * арк-выражения сверяются с ответом точно (sympy);
  * каждая точка ответа подставляется в уравнение точно, для тангенса — проверка cos x ≠ 0;
  * независимо от ответа корни ищутся численно на [0; 2π) — набор точек должен совпасть
    с ответом: ни лишнего, ни потерянного; «нет решений» тоже проверяется так.

  pip install sympy       # один раз
  python3 sborka.py       # проверить, собрать html/md и, если есть Chromium, оба PDF
"""
import math, pathlib, re, subprocess, sys
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication

HERE = pathlib.Path(__file__).parent
x = sp.Symbol('x', real=True)
pi, R, sqrt = sp.pi, sp.Rational, sp.sqrt

# ---------- константы-арки для нетабличных ответов ----------
CONST = {}
def K(name, value):
    s = sp.Symbol(name, real=True)
    CONST[s] = value
    return s

# ---------- мини-разметка: [a|b] — дробь, √n — корень с чертой ----------
def to_html(s):
    s = re.sub(r'√(\d+)', r'√<span class="rad">\1</span>', s)
    return re.sub(r'\[([^|\]]*)\|([^\]]*)\]', r'<span class="fr"><span>\1</span><span>\2</span></span>', s)

def to_text(s):
    return re.sub(r'\[([^|\]]*)\|([^\]]*)\]', r'\1/\2', s)

FUN = {'arcsin': 'asin', 'arccos': 'acos', 'arctg': 'atan', 'tg': 'tan'}
NS = {'x': x, 'pi': pi, 'sqrt': sqrt, 'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
      'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan}

def parse(s):
    """Тот же текст, что в листе ученика -> выражение sympy."""
    t = re.sub(r'\[([^|\]]*)\|([^\]]*)\]', r'((\1)/(\2))', s)
    t = re.sub(r'(sin|cos|tg)²x', r'(\1(x))**2', t)
    t = re.sub(r'(arcsin|arccos|arctg|sin|cos|tg) ([0-9x]+)', r'\1(\2)', t)
    t = re.sub(r'√(\d+)', r'sqrt(\1)', t)
    t = t.replace('π', 'pi').replace('−', '-').replace('·', '*').replace('²', '**2')
    t = re.sub(r'arcsin|arccos|arctg|tg', lambda m: FUN[m.group()], t)
    if '=' in t:
        l, r = t.split('=')
        return _p(l) - _p(r)
    return _p(t)

def _p(t):
    return parse_expr(t, local_dict=NS, transformations=standard_transformations + (implicit_multiplication,))

# ---------- печать ответов ----------
def coef(c, unit):
    """c·unit, c рациональное: 5/6, π -> 5π/6; −1, π -> −π."""
    c = R(c)
    sgn = '−' if c < 0 else ''
    p, q = abs(c.p), c.q
    return sgn + ('' if p == 1 else str(p)) + unit + ('' if q == 1 else f'/{q}')

def fmt_rest(e, al):
    """Часть без π: рациональные, корни, константы-арки."""
    if e == 0:
        return ''
    if isinstance(e, sp.Symbol):
        return al.get(e, e.name)
    if isinstance(e, sp.Rational):
        return ('−' if e < 0 else '') + str(abs(e.p)) + ('' if e.q == 1 else f'/{e.q}')
    if isinstance(e, sp.Pow) and e.exp == R(1, 2):
        return f'√{e.base}'
    if isinstance(e, sp.Mul):
        c, rest = e.as_coeff_Mul()
        if c != 1:
            body = fmt_rest(rest, al)
            if c == -1:
                return '−' + body
            return coef(c, body)
    if isinstance(e, sp.Add):
        return join([fmt_rest(t, al) for t in sorted(e.args, key=lambda t: -num(t))])
    raise ValueError(f'не умею печатать {e!r}')

def join(parts):
    parts = [p for p in parts if p]
    if not parts:
        return '0'
    s = parts[0]
    for p in parts[1:]:
        s += f' − {p[1:]}' if p.startswith('−') else f' + {p}'
    return s

def fmt(e, al=None):
    e = sp.expand(e)
    c2, c1 = e.coeff(pi, 2), e.coeff(pi, 1)
    rest = sp.expand(e - c2 * pi ** 2 - c1 * pi)
    parts = [coef(c2, 'π²') if c2 else '', coef(c1, 'π') if c1 else '']
    if rest != 0:
        parts.append(fmt_rest(rest, al or {}))
    return join(parts)

def fmt_series(b, T, pm, al=None):
    t = coef(T / pi, 'πk')
    if b == 0:
        return f'x = {t}'
    return f'x = {"±" if pm else ""}{fmt(b, al)} + {t}'

# ---------- задачи ----------
ARC = [  # условие, ответ
    ('arcsin([1|2]) + arccos([1|2])', pi / 2),
    ('arccos(−[√2|2]) − arcsin(−[√2|2])', pi),
    ('arctg(−√3) + arccos(−[1|2])', pi / 3),
    ('arcsin(−[√3|2]) + (arccos 0)²', pi ** 2 / 4 - pi / 3),
    ('6arcsin(−[1|2]) + 4arccos(−[√2|2])', 2 * pi),
    ('arccos(−1) · arcsin(−[√3|2])', -pi ** 2 / 3),
    ('sin(arccos(−[1|2]))', sqrt(3) / 2),
    ('arcsin(sin([5π|6]))', pi / 6),
]

S2, PI = 2 * pi, pi
A_cos = K('arccos(−2/5)', sp.acos(R(-2, 5)))
A_tg7 = K('arctg 7', sp.atan(7))
A_sin = K('arcsin(√3 − 1)', sp.asin(sqrt(3) - 1))
A_tg3 = K('arctg 3', sp.atan(3))

def eq(cond, series, excl=(), guides=(), note='', tag=''):
    return dict(cond=cond, series=series, excl=list(excl), guides=list(guides), note=note, tag=tag)

SECTIONS = [
 ('Решите уравнение.', [
    eq('2cos x + √3 = 0', [(5 * pi / 6, S2, True)], guides=[('cos', -sqrt(3) / 2)]),
    eq('2sin x + √2 = 0', [(-pi / 4, S2, False), (-3 * pi / 4, S2, False)], guides=[('sin', -sqrt(2) / 2)]),
    eq('√3 tg x − 1 = 0', [(pi / 6, PI, False)]),
    eq('5 + 5sin x = 0', [(-pi / 2, S2, False)], note='частный случай sin x = −1: одна точка, период 2π'),
    eq('3sin x + 4 = 0', [], guides=[('sin', R(-4, 3))], note='sin x = −4/3 < −1'),
    eq('5cos x + 2 = 0', [(A_cos, S2, True)], guides=[('cos', R(-2, 5))],
       note='нетабличное значение; годится и ±(π − arccos(2/5)) + 2πk'),
    eq('tg x + 7 = 0', [(-A_tg7, PI, False)], tag='есть',
       note='тангенс не ограничен — решения есть при любом числе'),
    eq('cos x = [π|3]', [], guides=[('cos', pi / 3)], note='π/3 ≈ 1,05 > 1'),
    eq('sin x = √3 − 1', [(A_sin, S2, False), (pi - A_sin, S2, False)], guides=[('sin', sqrt(3) - 1)], tag='есть',
       note='√3 − 1 ≈ 0,73 — в пределах [−1; 1], решения есть'),
    eq('4sin²x = 3', [(pi / 3, PI, True)], guides=[('sin', sqrt(3) / 2), ('sin', -sqrt(3) / 2)],
       note='sin x = ±√3/2 — обе ветки'),
    eq('2cos²x = 1', [(pi / 4, pi / 2, False)], guides=[('cos', sqrt(2) / 2), ('cos', -sqrt(2) / 2)],
       note='четыре точки через π/2'),
    eq('4cos²x = 5', [], guides=[('cos', sqrt(5) / 2), ('cos', -sqrt(5) / 2)], note='cos²x = 5/4 > 1'),
    eq('2sin x + cos x = 4', [], note='оценка: 2sin x ≤ 2, cos x ≤ 1, сумма ≤ 3 < 4'),
 ]),
 ('Решите уравнение (произведение равно нулю).', [
    eq('(2sin x − 1)(cos x + 1) = 0', [(pi / 6, S2, False), (5 * pi / 6, S2, False), (pi, S2, False)],
       guides=[('sin', R(1, 2))]),
    eq('sin x · (2cos x − √2) = 0', [(0, PI, False), (pi / 4, S2, True)], guides=[('cos', sqrt(2) / 2)]),
    eq('sin x · cos x = 0', [(0, pi / 2, False)], note='πk и π/2 + πk вместе — четыре точки, πk/2'),
    eq('(2cos x − 3)(2sin x + √3) = 0', [(-pi / 3, S2, False), (-2 * pi / 3, S2, False)],
       guides=[('cos', R(3, 2)), ('sin', -sqrt(3) / 2)], tag='часть', note='cos x = 3/2 корней не даёт'),
    eq('(tg x − 1)(2cos x + 1) = 0', [(pi / 4, PI, False), (2 * pi / 3, S2, True)], guides=[('cos', R(-1, 2))],
       tag='контраст', note='тангенс есть, но выкалывать нечего: в точках ±2π/3 cos x ≠ 0'),
    eq('cos x · (tg x + 1) = 0', [(-pi / 4, PI, False)], excl=[(pi / 2, PI, False)],
       note='cos x = 0 даёт π/2 + πk, но там tg x не определён'),
    eq('tg x · (sin x − 1) = 0', [(0, PI, False)], excl=[(pi / 2, S2, False)],
       note='sin x = 1 даёт π/2 + 2πk, но там tg x не определён'),
 ]),
 ('Решите уравнение заменой t = sin x, t = cos x или t = tg x.', [
    eq('2sin²x − sin x − 1 = 0', [(pi / 2, S2, False), (-pi / 6, S2, False), (-5 * pi / 6, S2, False)],
       guides=[('sin', R(-1, 2))], note='t = 1 или t = −1/2'),
    eq('2cos²x + 3cos x + 1 = 0', [(2 * pi / 3, S2, True), (pi, S2, False)], guides=[('cos', R(-1, 2))],
       note='t = −1/2 или t = −1'),
    eq('tg²x + 2tg x − 3 = 0', [(pi / 4, PI, False), (-A_tg3, PI, False)], note='t = 1 или t = −3'),
    eq('2sin²x + 5sin x − 3 = 0', [(pi / 6, S2, False), (5 * pi / 6, S2, False)], guides=[('sin', R(1, 2))], tag='часть',
       note='t = 1/2 или t = −3 — второй не подходит'),
    eq('2cos²x − 7cos x + 6 = 0', [], guides=[('cos', R(3, 2))], note='t = 2 или t = 3/2 — оба вне [−1; 1]'),
    eq('4cos²x − 4cos x + 1 = 0', [(pi / 3, S2, True)], guides=[('cos', R(1, 2))],
       note='(2cos x − 1)² = 0, t = 1/2'),
    eq('tg x · (2sin²x − sin x − 1) = 0', [(0, PI, False), (-pi / 6, S2, False), (-5 * pi / 6, S2, False)],
       excl=[(pi / 2, S2, False)], guides=[('sin', R(-1, 2))],
       note='та же скобка, что в № 29, но корень π/2 + 2πk выпадает: там tg x не определён'),
 ]),
]

# ---------- проверка ----------
TWO_PI = 2 * math.pi

def num(e):
    return float(sp.N(sp.sympify(e).subs(CONST), 30))

def norm(v):
    v %= TWO_PI
    return 0.0 if v > TWO_PI - 1e-7 else v

def points(series):
    """Точки серий: [(представитель в (−π; π] как выражение, значение в [0; 2π))]."""
    out = []
    for b, T, pm in series:
        for s in ((1, -1) if pm else (1,)):
            for k in range(-8, 9):
                p = sp.expand(s * b + T * k)
                v = num(p)
                if -math.pi + 1e-9 < v <= math.pi + 1e-9 and all(abs(norm(v) - w) > 1e-7 for _, w in out):
                    out.append((p, norm(v)))
    return sorted(out, key=lambda t: num(t[0]))

def numeric_roots(f):
    """Корни f на [0; 2π) без опоры на ответ: смена знака (не через полюс) и касание нуля."""
    N = 200_000
    a, h = -0.01, (TWO_PI + 0.02) / 200_000
    xs = [a + i * h for i in range(N + 1)]
    def F(t):
        try:
            return f(t)
        except (ZeroDivisionError, ValueError, OverflowError):
            return math.nan
    ys = [F(t) for t in xs]
    found = []
    def add(r):
        r = norm(r)
        if all(min(abs(r - w), TWO_PI - abs(r - w)) > 1e-6 for w in found):
            found.append(r)
    for i in range(1, N):
        y0, y1, y2 = ys[i - 1], ys[i], ys[i + 1]
        if math.isnan(y0) or math.isnan(y1) or math.isnan(y2):
            continue
        if y1 == 0:
            add(xs[i]); continue
        if y1 * y2 < 0 and abs(y1) < 1e-2 and abs(y2) < 1e-2:
            lo, hi = xs[i], xs[i + 1]
            for _ in range(80):
                mid = (lo + hi) / 2
                if F(lo) * F(mid) <= 0: hi = mid
                else: lo = mid
            if abs(F(lo)) < 1e-9:
                add(lo)
        if abs(y1) <= abs(y0) and abs(y1) <= abs(y2) and abs(y1) < 1e-3:
            lo, hi = xs[i - 1], xs[i + 1]
            g = (math.sqrt(5) - 1) / 2
            for _ in range(120):
                m1, m2 = hi - g * (hi - lo), lo + g * (hi - lo)
                if abs(F(m1)) < abs(F(m2)): hi = m2
                else: lo = m1
            r = (lo + hi) / 2
            if abs(F(r)) < 1e-10:
                add(r)
    return sorted(found)

def same_sets(a, b):
    a, b = sorted(a), sorted(b)
    return len(a) == len(b) and all(min(abs(p - q), TWO_PI - abs(p - q)) < 1e-6 for p, q in zip(a, b))

def check_arc(cond, ans):
    e = parse(cond)
    assert sp.simplify(e - ans) == 0, (cond, e, ans)
    assert abs(num(e) - num(ans)) < 1e-12, cond

def check_eq(n, d):
    e = parse(d['cond'])
    has_tg = e.has(sp.tan)
    f = sp.lambdify(x, e, 'math')
    pts = points(d['series'])
    for p, _ in pts:  # точная подстановка каждой точки ответа
        pe = p.subs(CONST)
        assert sp.simplify(e.subs(x, pe)) == 0, (n, p)
        if has_tg:
            assert sp.simplify(sp.cos(pe)) != 0, (n, p, 'tg не определён')
    ex = points(d['excl'])
    for p, _ in ex:  # выколотые: tg не определён, а «наивный» множитель обнуляется
        pe = p.subs(CONST)
        assert has_tg and sp.simplify(sp.cos(pe)) == 0, (n, p)
        assert any(not m.has(sp.tan) and sp.simplify(m.subs(x, pe)) == 0 for m in sp.Mul.make_args(e)), (n, p)
    roots = numeric_roots(f)
    if has_tg:
        roots = [r for r in roots if abs(math.cos(r)) > 1e-6]
    assert same_sets(roots, [v for _, v in pts]), (n, d['cond'], roots, [v for _, v in pts])
    d['pts'], d['ex'] = pts, ex
    d['al'] = {s: 'α' for s in CONST if any(s in sp.sympify(b).free_symbols for b, _, _ in d['series'])}

# ---------- окружность в SVG ----------
def circle_svg(d):
    W, H, cx, cy, r = 190, 168, 95, 84, 52
    g = ['<svg viewBox="0 0 190 168" xmlns="http://www.w3.org/2000/svg" font-family="Times New Roman,serif">',
         f'<line x1="{cx - r - 14}" y1="{cy}" x2="{cx + r + 14}" y2="{cy}" stroke="#999" stroke-width=".7"/>',
         f'<line x1="{cx}" y1="{cy - r - 14}" x2="{cx}" y2="{cy + r + 14}" stroke="#999" stroke-width=".7"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#000" stroke-width="1.1"/>']
    for kind, v in d['guides']:
        v = num(v)
        if abs(v) > 1.55:
            continue
        if kind == 'sin':
            y = cy - r * v
            g.append(f'<line x1="{cx - r - 12}" y1="{y:.1f}" x2="{cx + r + 12}" y2="{y:.1f}" stroke="#555" stroke-width=".8" stroke-dasharray="3 2"/>')
        else:
            X = cx + r * v
            g.append(f'<line x1="{X:.1f}" y1="{cy - r - 12}" x2="{X:.1f}" y2="{cy + r + 12}" stroke="#555" stroke-width=".8" stroke-dasharray="3 2"/>')
    def mark(p, hollow):
        t = num(p)
        px, py = cx + r * math.cos(t), cy - r * math.sin(t)
        lx, ly = cx + (r + 17) * math.cos(t), cy - (r + 15) * math.sin(t) + 4
        anchor = 'middle' if abs(math.cos(t)) < .35 else ('start' if math.cos(t) > 0 else 'end')
        lx += 0 if anchor == 'middle' else (-10 if anchor == 'start' else 10)
        fill = '#fff' if hollow else '#000'
        g.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.4" fill="{fill}" stroke="#000" stroke-width="1.1"/>')
        g.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" text-anchor="{anchor}">{fmt(p, d["al"])}</text>')
    for p, _ in d['pts']:
        mark(p, False)
    for p, _ in d['ex']:
        mark(p, True)
    g.append('</svg>')
    return ''.join(g)

# ---------- сборка ----------
STYLE_COMMON = '''
.fr{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;margin:0 2px;font-size:.92em}
.fr>span:first-child{border-bottom:1px solid #000;padding:0 3px} .fr>span:last-child{padding:0 3px}
.rad{border-top:1px solid #000;padding:0 1px}
'''

def answer_lines(d):
    if not d['series']:
        return ['нет решений']
    return [fmt_series(b, T, pm) for b, T, pm in d['series']]

def build():
    for cond, ans in ARC:
        check_arc(cond, ans)
    n = len(ARC)
    for _, items in SECTIONS:
        for d in items:
            n += 1
            d['n'] = n
            check_eq(n, d)
    eqs = [d for _, items in SECTIONS for d in items]

    # лист ученику
    head = ('<p class="rule">К каждому уравнению — рисунок тригонометрической окружности, на котором '
            'отмечены все корни. <b>Решение без рисунка не засчитывается.</b> '
            'Если корней нет — объясните почему. Ответ записывайте сериями: x = … + 2πk, k ∈ ℤ.</p>')
    body = [f'<h2>1. Вычислите.</h2><ol>' + ''.join(f'<li>{to_html(c)}</li>' for c, _ in ARC) + '</ol>']
    for i, (title, items) in enumerate(SECTIONS, 2):
        body.append(f'<h2>{i}. {title}</h2><ol start="{items[0]["n"]}">' +
                    ''.join(f'<li>{to_html(d["cond"])}</li>' for d in items) + '</ol>')
    page = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Домашнее задание</title>
<style>
@page{{margin:14mm 14mm}}
body{{font-family:"Times New Roman",serif;font-size:13.5pt;color:#000;background:#fff;margin:0}}
h1{{font-size:15pt;margin:0 0 4pt}} h2{{font-size:13.5pt;margin:12pt 0 6pt;break-after:avoid}}
.rule{{margin:0 0 8pt;font-size:12pt;line-height:1.35}}
ol{{columns:2;column-gap:10mm;margin:0;padding-left:8mm}}
li{{margin:0 0 9pt;break-inside:avoid;line-height:1.6}}
{STYLE_COMMON}</style></head><body>
<h1>Домашнее задание</h1>{head}{"".join(body)}
</body></html>'''
    (HERE / 'zadachi.html').write_text(page, encoding='utf-8')

    md = ['# Домашнее задание', '',
          'К каждому уравнению — рисунок тригонометрической окружности, на котором отмечены все корни. '
          '**Решение без рисунка не засчитывается.** Если корней нет — объясните почему. '
          'Ответ записывайте сериями: x = … + 2πk, k ∈ ℤ.', '',
          '## 1. Вычислите.', '']
    md += [f'{i}. {to_text(c)}' for i, (c, _) in enumerate(ARC, 1)]
    for i, (title, items) in enumerate(SECTIONS, 2):
        md += ['', f'## {i}. {title}', '']
        md += [f'{d["n"]}. {to_text(d["cond"])}' for d in items]
    (HERE / 'ZADACHI.md').write_text('\n'.join(md) + '\n', encoding='utf-8')

    # ответы преподавателю
    none_ = [d['n'] for d in eqs if not d['series']]
    part = [d['n'] for d in eqs if d['tag'] == 'часть']
    drop = [d['n'] for d in eqs if d['ex']]
    yes = [d['n'] for d in eqs if d['tag'] == 'есть']
    tgok = [d['n'] for d in eqs if d['tag'] == 'контраст']
    lst = lambda a: ', '.join(f'№ {k}' for k in a)
    traps = [f'нет решений — {lst(none_)};',
             f'часть корней вне [−1; 1] — {lst(part)};',
             f'корень выпадает из-за тангенса — {lst(drop)};',
             f'тангенс есть, но ничего не выпадает — {lst(tgok)};',
             f'похоже на ловушку, но решения есть — {lst(yes)}.']
    rules = [
        '<b>Без окружности с отмеченными корнями работу не принимать</b> — вернуть на доработку, даже если ответ верный.',
        'На рисунке должны быть все точки ответа: серия с периодом π — две противоположные точки, с периодом π/2 — четыре.',
        'Где корень выпадает из-за тангенса, хорошо, если точка π/2 показана выколотой: видно, что её нашли и отбросили сознательно.',
        'Где корней нет, отмечать нечего — но должна быть записана причина (|sin x| ≤ 1, оценка суммы); голое «нет решений» не засчитывать.',
        'Нетабличные точки (arccos(−2/5) и т. п.) — примерно в своей четверти, с подписью.',
        'Любая равносильная запись ответа засчитывается: сверять по точкам на окружности.',
    ]
    cards = []
    for d in eqs:
        al = ''.join(f'<div class="al">α = {s.name} ≈ {str(round(num(v), 2)).replace(".", ",")}</div>'
                     for s, v in CONST.items() if s in d['al'])
        ans = '<br>'.join(answer_lines(d)) + ('' if not d['series'] else ', k ∈ ℤ')
        ex = ''.join(f'<div class="ex">выколоть: {fmt_series(b, T, pm)}</div>' for b, T, pm in d['excl'])
        note = f'<div class="note">{to_html(d["note"])}</div>' if d['note'] else ''
        cards.append(f'<div class="card"><div class="q"><b>{d["n"]}.</b> {to_html(d["cond"])}</div>'
                     f'<div class="a">{ans}</div>{ex}{circle_svg(d)}{al}{note}</div>')
    arcs = ''.join(f'<li>{to_html(c)} = <b>{fmt(a)}</b></li>' for c, a in ARC)
    tpage = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Ответы к ДЗ</title>
<style>
@page{{margin:12mm 12mm}}
body{{font-family:"Times New Roman",serif;font-size:12pt;color:#000;background:#fff;margin:0}}
h1{{font-size:15pt;margin:0 0 6pt}} h2{{font-size:13pt;margin:10pt 0 5pt;break-after:avoid}}
ul{{margin:0 0 4pt;padding-left:6mm}} li{{margin:0 0 3pt}}
ol{{columns:2;column-gap:10mm;margin:0;padding-left:8mm}} ol li{{margin:0 0 6pt;line-height:1.6;break-inside:avoid}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm}}
.card{{border:1px solid #888;border-radius:2mm;padding:2mm 2.5mm;break-inside:avoid;font-size:11pt}}
.q{{line-height:1.5}} .a{{margin:1mm 0;line-height:1.35}} .ex{{font-size:10pt}}
.card svg{{display:block;width:100%;max-width:52mm;margin:1mm auto 0}}
.al{{font-size:10pt;text-align:center}} .note{{font-size:10pt;font-style:italic;color:#333;margin-top:1mm}}
{STYLE_COMMON}</style></head><body>
<h1>Ответы и проверка ДЗ по тригонометрии</h1>
<h2>Как принимать работу</h2><ul>{"".join(f"<li>{r}</li>" for r in rules)}</ul>
<h2>Ловушки</h2><ul>{"".join(f"<li>{t}</li>" for t in traps)}</ul>
<h2>1. Вычислите</h2><ol>{arcs}</ol>
<h2>2–4. Уравнения</h2>
<p style="margin:0 0 3mm;font-size:10.5pt">● — корень, ○ — выколотая точка, пунктир — прямая sin x = a или cos x = a.</p>
<div class="grid">{"".join(cards)}</div>
</body></html>'''
    (HERE / 'otvety.html').write_text(tpage, encoding='utf-8')

    ot = ['# Ответы и проверка (только для преподавателя)', '',
          'Собрано и проверено скриптом `sborka.py`. Печатная версия с окружностями — PDF «ответы».', '',
          '## Как принимать работу', '']
    ot += [f'- {re.sub(r"</?b>", "**", r)}' for r in rules]
    ot += ['', '## Ловушки', ''] + [f'- {t}' for t in traps]
    ot += ['', '## 1. Вычислите', '']
    ot += [f'{i}. {to_text(c)} = **{fmt(a)}**' for i, (c, a) in enumerate(ARC, 1)]
    for i, (title, items) in enumerate(SECTIONS, 2):
        ot += ['', f'## {i}. {title}', '']
        for d in items:
            line = f'{d["n"]}. {to_text(d["cond"])} → **' + '; '.join(answer_lines(d)) + '**'
            if d['series']:
                line += ', k ∈ ℤ'
                line += '  \n   на окружности: ' + ', '.join(fmt(p, d['al']) for p, _ in d['pts'])
            for s, v in CONST.items():
                if s in d['al']:
                    line += f' (α = {s.name})'
            if d['excl']:
                line += '  \n   выколоть: ' + '; '.join(fmt_series(b, T, pm) for b, T, pm in d['excl'])
            if d['note']:
                line += f'  \n   *{to_text(d["note"])}*'
            ot.append(line)
    (HERE / 'OTVETY.md').write_text('\n'.join(ot) + '\n', encoding='utf-8')
    print(f'ok: {len(ARC)} выражений, {len(eqs)} уравнений; нет решений: {none_}; выкол: {drop}')

PDF = {'zadachi.html': 'ДЗ — тригонометрические уравнения и арки.pdf',
       'otvety.html': 'ДЗ — тригонометрические уравнения и арки — ответы.pdf'}
CH = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

def pdfs():
    if not pathlib.Path(CH).exists():
        print('Chromium не найден — PDF не собраны'); return
    for src, out in PDF.items():
        subprocess.run([CH, '--headless', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer',
                        '--virtual-time-budget=8000', f'--print-to-pdf={HERE / out}', f'file://{HERE / src}'],
                       check=True, capture_output=True)
        print('pdf:', out)

if __name__ == '__main__':
    build()
    if '--no-pdf' not in sys.argv:
        pdfs()
