"""Общий каркас: модель документа, проверка ответов, вёрстка HTML.

Условия пишутся в LaTeX. Где можно, ответ не набирается руками, а считается
из того же LaTeX через sympy (parse_latex) — так текст задачи и ответ не
разъедутся. Где ответ набран руками, он сверяется с вычисленным (check_*).
"""
import html
import re
from fractions import Fraction

import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.core.function import AppliedUndef

x = sp.Symbol('x', real=True)
a = sp.Symbol('a', real=True)
t = sp.Symbol('t', real=True)


# ---------------------------------------------------------------- LaTeX -> sympy

def to_sympy(tex):
    if '=' in tex:
        l, r = tex.split('=', 1)
        return sp.Eq(_to_sympy(l), _to_sympy(r), evaluate=False)
    return _to_sympy(tex)


def _to_sympy(tex):
    """LaTeX условия -> выражение sympy. Понимает наши макросы:
    \\mix{3}{1}{2} — смешанное число, 0{,}25 — десятичная запятая,
    \\dv — деление двоеточием, \\tg/\\ctg, 19^\\circ — градусы."""
    s = tex
    s = re.sub(r'\\mix\{(\d+)\}\{(\d+)\}\{(\d+)\}', r'(\1+\\frac{\2}{\3})', s)
    s = re.sub(r'(\d+)\{,\}(\d+)',
               lambda m: r'(\frac{%d}{%d})' % (int(m.group(1) + m.group(2)), 10 ** len(m.group(2))), s)
    s = re.sub(r'(-?\d+)\^(?:\{\\circ\}|\\circ)', r'(\\frac{\1\\pi}{180})', s)
    for old, new in [(r'\dv', r'\div'), (r'\tg', r'\tan'), (r'\ctg', r'\cot'),
                     (r'\dfrac', r'\frac'), (r'\tfrac', r'\frac'), (r'\cfrac', r'\frac'),
                     (r'\,', ' ')]:
        s = s.replace(old, new)
    s = s.replace(r'\pi(', r'\pi\cdot(')
    # \tan a \cdot \cot a parse_latex читает как tan(a·cot a): аргумент без скобок оборачиваем
    s = re.sub(r'\\(sin|cos|tan|cot)(\^\{?\d\}?)?\s*(\d*\s*[a-z])(?![a-z])', r'\\\1\2(\3)', s)
    # x(x+3) parse_latex читает как вызов функции x — ставим умножение явно
    s = re.sub(r'(?<![\\a-zA-Z])([a-z])\s*(\\left)?\(', lambda m: m.group(1) + r'\cdot ' + (m.group(2) or '') + '(', s)
    e = parse_latex(s)
    if e.atoms(AppliedUndef):
        raise ValueError('в выражении осталась неизвестная функция: %s' % e)
    subs = {sp.Symbol(n): sp.Symbol(n, real=True) for n in 'xyabcmnkt'}
    subs[sp.Symbol('pi')] = sp.pi
    return e.subs(subs)


def value(tex):
    """Точное значение числового выражения."""
    v = sp.nsimplify(sp.simplify(to_sympy(tex)))
    return v


def same(e1, e2):
    """Тождественное равенство (символьно + численно в случайных точках)."""
    d = sp.simplify(sp.together(e1 - e2))
    if d == 0:
        return True
    import random
    syms = sorted(d.free_symbols, key=str)
    ok = 0
    for _ in range(40):
        pt = {s: sp.Rational(random.randint(-40, 40), random.randint(1, 9)) + sp.Rational(1, 7) for s in syms}
        try:
            val = complex(d.subs(pt).evalf(30))
        except (TypeError, ZeroDivisionError):
            continue
        if abs(val) > 1e-12:
            return False
        ok += 1
    if ok < 10:
        raise ValueError('не удалось проверить тождество численно')
    return True


def roots_real(eq_tex, var=x, interval=None):
    """Действительные корни уравнения с проверкой подстановкой (ОДЗ: логарифмы,
    корни, знаменатели проверяются на исходном уравнении). Если solveset не
    справился, берём solve и страхуемся численным поиском корней на сетке."""
    eq = to_sympy(eq_tex) if isinstance(eq_tex, str) else eq_tex
    f = eq.lhs - eq.rhs
    dom = sp.S.Reals if interval is None else interval
    sol = sp.solveset(f, var, domain=dom)
    if isinstance(sol, sp.FiniteSet):
        cands = list(sol)
    elif sol.is_empty:
        cands = []
    else:
        cands = [r for r in sp.solve(f, var) if r.is_real]
        lo, hi = (-100, 100) if interval is None else (float(interval.start), float(interval.end))
        for z in numeric_roots(f, var, lo, hi):
            assert any(abs(float(c) - z) < 0.011 for c in cands), ('solve потерял корень', eq_tex, z, cands)
    good = []
    for r in cands:
        if is_root(eq, r, var):
            good.append(sp.nsimplify(r))
    return sorted(set(good), key=lambda z: float(z))


def numeric_roots(f, var, lo, hi, n=40000):
    """Грубый численный поиск: смена знака на сетке (только в точках, где f вещественна)."""
    import math
    g = sp.lambdify(var, f, 'math')
    out = []
    prev = None
    step = (hi - lo) / n
    for i in range(n + 1):
        z = lo + i * step
        try:
            v = g(z)
            if isinstance(v, complex) or math.isnan(v):
                v = None
        except (ValueError, ZeroDivisionError, OverflowError):
            v = None
        if v is not None and prev is not None and prev[1] * v < 0 and abs(prev[1]) + abs(v) < 1:
            out.append((prev[0] + z) / 2)
        if v is not None and v == 0:
            out.append(z)
        prev = (z, v) if v is not None else None
    return out


def is_root(eq, r, var=x):
    """Подстановка в исходное уравнение: обе части определены, вещественны и равны."""
    try:
        l = sp.N(eq.lhs.subs(var, r), 40)
        rr = sp.N(eq.rhs.subs(var, r), 40)
    except (ZeroDivisionError, ValueError):
        return False
    for v in (l, rr):
        if v.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or not v.is_real:
            return False
    # логарифм: основание > 0, != 1, аргумент > 0 — проверяем все log в выражении
    for side in (eq.lhs, eq.rhs):
        for lg in side.atoms(sp.log):
            arg = sp.N(lg.args[0].subs(var, r), 40)
            if not (arg.is_real and arg > 0):
                return False
        for p in side.atoms(sp.Pow):
            if p.exp.is_Rational and p.exp.q % 2 == 0:
                base = sp.N(p.base.subs(var, r), 40)
                if not (base.is_real and base >= 0):
                    return False
            if p.exp.is_negative or (p.exp.is_Rational and p.exp < 0):
                base = sp.N(p.base.subs(var, r), 40)
                if base == 0:
                    return False
    # основание логарифма: log(u, b) = log(u)/log(b), при b = 1 деление на 0 отсекло выше
    return abs(complex(l - rr)) < 1e-25


def fmt_num(v):
    """Число для ответа ЕГЭ: целое или конечная десятичная дробь с запятой."""
    v = sp.nsimplify(v)
    if not v.is_Rational:
        raise ValueError('ответ не рационален: %s' % v)
    f = Fraction(int(v.p), int(v.q))
    q = f.denominator
    while q % 2 == 0:
        q //= 2
    while q % 5 == 0:
        q //= 5
    if q != 1:
        raise ValueError('ответ не конечная десятичная дробь: %s' % v)
    if f.denominator == 1:
        return str(f.numerator).replace('-', '−')
    from decimal import Decimal, getcontext
    getcontext().prec = 40
    s = str(Decimal(f.numerator) / Decimal(f.denominator))   # точно: знаменатель вида 2^a·5^b
    return s.replace('.', ',').replace('-', '−')


def tex_of(v):
    """sympy -> LaTeX для листа ответов (запятая вместо точки, tg вместо tan)."""
    s = sp.latex(v)
    s = s.replace(r'\tan', r'\tg').replace(r'\cot', r'\ctg').replace(r'\operatorname{atan}', r'\arctg')
    s = re.sub(r'\\arctg\{\\left\((\d+) \\right\)\}', r'\\arctg \1', s)
    s = re.sub(r'\\(sin|cos|tg|ctg)\{\\left\((\\alpha|[a-z]) \\right\)\}', r'\\\1\2', s)
    return s


def num_or_tex(v):
    v = sp.nsimplify(v)
    if v.is_Rational:
        f = Fraction(int(v.p), int(v.q))
        q = f.denominator
        while q % 2 == 0:
            q //= 2
        while q % 5 == 0:
            q //= 5
        if q == 1:
            return '$' + fmt_num(v).replace(',', '{,}').replace('−', '-') + '$'
    return '$' + tex_of(v) + '$'


def roots_tex(rs):
    if not rs:
        return 'корней нет'
    return '; '.join(num_or_tex(r) for r in rs)


# ---------------------------------------------------------------- модель документа

class Task:
    def __init__(self, text, answer=None, note=None, wide=False):
        self.text = text          # HTML с $...$
        self.answer = answer      # HTML с $...$ (для листа ответов)
        self.note = note          # пояснение преподавателю в листе ответов
        self.wide = wide          # на всю ширину строки (длинная формула)


class Doc:
    def __init__(self, key, title, subtitle):
        self.key = key            # имя файла
        self.title = title
        self.subtitle = subtitle
        self.blocks = []
        self.n = 0

    def h(self, text, level=2):
        self.blocks.append(('h', level, text))

    def p(self, text):
        self.blocks.append(('p', text))

    def raw(self, text):
        self.blocks.append(('raw', text))

    def tasks(self, items, cols=1, answer_cols=None):
        """items: Task. Нумерация сквозная по документу."""
        numbered = []
        for it in items:
            self.n += 1
            numbered.append((self.n, it))
        self.blocks.append(('tasks', cols, numbered, answer_cols))

    def videos(self, items):
        """items: (тема, название ролика, url)."""
        self.blocks.append(('videos', items))

    def pagebreak(self):
        self.blocks.append(('br',))


# ---------------------------------------------------------------- HTML

KATEX_MACROS = {
    r'\dv': r'\mathbin{:}',
    r'\mix': r'#1\frac{#2}{#3}',
    r'\tg': r'\operatorname{tg}',
    r'\ctg': r'\operatorname{ctg}',
    r'\arctg': r'\operatorname{arctg}',
    r'\arcctg': r'\operatorname{arcctg}',
}

CSS = r"""
@page { size: A4; margin: 14mm 15mm 14mm 15mm; }
html { background: #fff; }
body { font-family: 'Liberation Serif', 'Times New Roman', serif; font-size: 12.5pt;
       line-height: 1.38; color: #000; background: #fff; margin: 0; }
h1 { font-size: 16pt; margin: 0 0 2pt 0; }
.sub { margin: 0 0 10pt 0; font-size: 11.5pt; }
h2 { font-size: 13.5pt; margin: 14pt 0 5pt 0; break-after: avoid; page-break-after: avoid; }
h3 { font-size: 12.5pt; margin: 10pt 0 4pt 0; break-after: avoid; page-break-after: avoid; }
p { margin: 3pt 0 5pt 0; }
.tasks { display: grid; column-gap: 18pt; row-gap: 6pt; margin: 4pt 0 6pt 0; }
.task { display: flex; gap: 6pt; break-inside: avoid; page-break-inside: avoid; }
.task .n { font-weight: bold; min-width: 2.1em; text-align: right; flex: none; }
.task .b { flex: 1; min-width: 0; }
.videos { margin: 4pt 0; padding-left: 0; list-style: none; }
.videos li { margin: 0 0 6pt 0; break-inside: avoid; }
.videos .url { font-family: 'Liberation Mono', monospace; font-size: 10pt; word-break: break-all; }
a { color: #000; }
.br { break-after: page; page-break-after: always; }
.box { border: 1px solid #000; padding: 6pt 9pt; margin: 6pt 0; break-inside: avoid; }
.formulas { columns: 2; column-gap: 18pt; }
.formulas p, .formulas .fg { break-inside: avoid; margin: 0 0 6pt 0; }
.formulas .f { margin: 1pt 0 3pt 0; }
table.t { border-collapse: collapse; margin: 4pt 0; }
table.t td, table.t th { border: 1px solid #000; padding: 2pt 6pt; text-align: center; }
figure { margin: 2pt 0; break-inside: avoid; }
.fig-row { display: flex; gap: 14pt; flex-wrap: wrap; align-items: flex-end; }
.ans .task .b { font-size: 11.5pt; }
.note { font-size: 10.5pt; }
.nw { white-space: nowrap; }
.katex { font-size: 1.04em; }
.katex-display { margin: 4pt 0; }
"""


def render(doc, answers=False):
    out = []
    for i, b in enumerate(doc.blocks):
        kind = b[0]
        if kind == 'h':
            if answers:
                nxt = next((c for c in doc.blocks[i + 1:] if c[0] in ('h', 'tasks')), None)
                if nxt is None or nxt[0] != 'tasks':
                    continue
            out.append('<h%d>%s</h%d>' % (b[1], b[2], b[1]))
        elif kind == 'p':
            if not answers:
                out.append('<p>%s</p>' % b[1])
        elif kind == 'raw':
            if not answers:
                out.append(b[1])
        elif kind == 'br':
            if not answers:
                out.append('<div class="br"></div>')
        elif kind == 'videos':
            if answers:
                continue
            out.append('<ul class="videos">')
            for theme, name, url in b[1]:
                out.append('<li><b>%s</b> — «%s»<br><a class="url" href="%s">%s</a></li>'
                           % (theme, html.escape(name), url, url))
            out.append('</ul>')
        elif kind == 'tasks':
            cols, numbered, acols = b[1], b[2], b[3]
            if answers:
                cols = acols or max(cols, 2)
            out.append('<div class="tasks" style="grid-template-columns: repeat(%d, minmax(0,1fr))">' % cols)
            for n, it in numbered:
                body = it.answer if answers else it.text
                if answers and it.answer is None:
                    body = '—'
                if answers and it.note:
                    body += ' <span class="note">(%s)</span>' % it.note
                wide = ' style="grid-column: 1 / -1"' if (it.wide and not answers) else ''
                out.append('<div class="task"%s><div class="n">%d.</div><div class="b">%s</div></div>' % (wide, n, body))
            out.append('</div>')
    return postprocess('\n'.join(out))


def postprocess(h):
    """Все формулы — в displaystyle (дроби читаемого размера); знак препинания после формулы
    не уезжает на новую строку. Разбор по парам $…$, без регулярок поперёк границ."""
    parts = h.split('$')
    assert len(parts) % 2 == 1, 'непарный $'
    out = []
    for i, seg in enumerate(parts):
        if i % 2 == 0:
            out.append(seg)
            continue
        if not seg.startswith('\\displaystyle'):
            seg = '\\displaystyle ' + seg
        seg = seg.replace('<', '&lt;').replace('>', '&gt;')   # $-4<a<4$: «<a» браузер принял бы за тег
        math = '$' + seg + '$'
        nxt = parts[i + 1]
        if nxt[:1] in ('.', ',', ';', ':', '?', '!', ')'):
            math = '<span class="nw">' + math + nxt[0] + '</span>'
            parts[i + 1] = nxt[1:]
        out.append(math)
    return ''.join(out)


def page(title, body, katex_dir):
    import json
    macros = json.dumps(KATEX_MACROS)
    return """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>%s</title>
<link rel="stylesheet" href="%s/katex.min.css">
<style>%s</style>
<script src="%s/katex.min.js"></script>
<script src="%s/auto-render.min.js"></script>
</head><body>
%s
<script>
renderMathInElement(document.body, {delimiters: [
  {left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}],
  macros: %s, throwOnError: true, strict: false});
document.body.setAttribute('data-ok', '1');
</script>
</body></html>""" % (html.escape(title), katex_dir, CSS, katex_dir, katex_dir, body, macros)


def header(doc):
    return '<h1>%s</h1><div class="sub">%s</div>' % (doc.title, doc.subtitle)


# ---------------------------------------------------------------- ЕГЭ, задание 7

RULE_TEXT = {
    'min': 'Если уравнение имеет более одного корня, в ответе запишите меньший из них.',
    'max': 'Если уравнение имеет более одного корня, в ответе запишите больший из них.',
    'maxneg': 'В ответе запишите наибольший отрицательный корень.',
    'minpos': 'В ответе запишите наименьший положительный корень.',
}


def ege_eq(tex, rule=None):
    """Корни уравнения (с проверкой ОДЗ) и ответ по правилу ЕГЭ. Ответ обязан быть
    целым числом или конечной десятичной дробью — иначе fmt_num упадёт."""
    trig = any(f in tex for f in (r'\sin', r'\cos', r'\tg', r'\ctg'))
    dom = sp.Interval(-60, 60) if trig else None
    rs = roots_real(tex, interval=dom)
    if not rs:
        raise ValueError('нет корней: ' + tex)
    if rule is None:
        assert len(rs) == 1, (tex, rs)
        r = rs[0]
    elif rule == 'min':
        r = rs[0]
    elif rule == 'max':
        r = rs[-1]
    elif rule == 'maxneg':
        r = max(v for v in rs if v < 0)
    elif rule == 'minpos':
        r = min(v for v in rs if v > 0)
    if rule in ('min', 'max'):
        assert len(rs) > 1, ('правило не нужно, корень один', tex, rs)
    return fmt_num(r), rs


RULE_SHORT = {
    'min': 'в ответ — меньший корень',
    'max': 'в ответ — больший корень',
    'maxneg': 'в ответ — наибольший отрицательный корень',
    'minpos': 'в ответ — наименьший положительный корень',
}


def ege_task(tex, rule=None, prefix='Найдите корень уравнения', short=False):
    ans, rs = ege_eq(tex, rule)
    text = ('%s $%s$.' % (prefix, tex)) if prefix else '$%s$' % tex
    if rule and short:
        text += ' <i>(%s)</i>' % RULE_SHORT[rule]
    elif rule:
        text += ' ' + RULE_TEXT[rule]
    trig = any(f in tex for f in (r'\sin', r'\cos', r'\tg', r'\ctg'))
    note = None
    if not trig and len(rs) > 1:
        note = 'корни: ' + '; '.join(fmt_num(r) if _finite(r) else '$%s$' % tex_of(r) for r in rs)
    return Task(text, ans, note)


def _finite(r):
    try:
        fmt_num(r)
        return True
    except ValueError:
        return False
