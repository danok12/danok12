#!/usr/bin/env python3
"""ДЗ от 15.10.2026: тригонометрические уравнения (10 класс, профиль) и дроби (6 класс).

Все условия и ответы записаны здесь один раз; из них же собираются PDF и md.

    python3 zadachi.py check     проверить все ответы
    python3 zadachi.py build     проверить, собрать PDF, ZADACHI.md и OTVETY.md

Как проверяется тригонометрия. Уравнение разбирается прямо из той строки,
что печатается в листе, ответ — из строки ответа. На [−6π; 6π] уравнение
решается численно: сетка с шагом 1e−4, смена знака и локальные минимумы |F|
(чтобы не терять корни вроде sin x = 1, где знак не меняется), уточнение,
отсев по ОДЗ (знаменатели, tg, ctg, корни). Затем в обе стороны:
каждая точка каждой серии ответа — корень с точностью 1e−15 (40 знаков)
и лежит в ОДЗ; каждый найденный численно корень попадает в серию ответа.
Дроби 6 класса считаются через Fraction, ответы печатаются из результата.
"""
import html
import math
import pathlib
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from fractions import Fraction as Fr

import mpmath
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (implicit_application, implicit_multiplication,
                                        parse_expr, standard_transformations)

HERE = pathlib.Path(__file__).resolve().parent
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
mpmath.mp.dps = 40

# ───────────────────────── разбор формул ─────────────────────────
# Разметка в условиях: {A // B} — дробь, √{A} — корень с чертой, ^{A} и ^2 — степень.

X = sp.Symbol('x', real=True)
A = sp.Symbol('a', real=True)
N = sp.Symbol('n', integer=True)
M = sp.Symbol('m', integer=True)


def arcctg(y):
    return sp.pi / 2 - sp.atan(y)


LOCAL = dict(x=X, a=A, n=N, m=M, pi=sp.pi, sin=sp.sin, cos=sp.cos, tan=sp.tan, cot=sp.cot,
             sqrt=sp.sqrt, Abs=sp.Abs, asin=sp.asin, acos=sp.acos, atan=sp.atan, arcctg=arcctg)
TR = standard_transformations + (implicit_multiplication, implicit_application)
FN = r'(sin|cos|tg|ctg)'
ARG = r'(\((?:[^()]|\([^()]*\))*\)|[\d.]+| pi )'


def to_py(s):
    s = s.replace('−', '-').replace('·', '*').replace('π', ' pi ')
    s = re.sub(r'(\d),(\d)', r'\1.\2', s)
    for ru, py in (('arcctg', 'arcctg'), ('arctg', 'atan'), ('arcsin', 'asin'), ('arccos', 'acos')):
        s = re.sub(ru + r'\s*' + ARG, py + r'(\1)', s)
    s = re.sub(FN + r'\^(\d+)\s*(\d*x)', r'(\1(\3))**\2', s)
    s = re.sub(FN + r'\s*(\d*x)', r'\1(\2)', s)
    s = re.sub(r'\|([^|]+)\|', r'Abs(\1)', s)
    s = re.sub(r'√(\d+)', r'sqrt(\1)', s)
    s = s.replace('√{', 'sqrt{').replace('^{', '**{')
    s = re.sub(r'\^(\w)', r'**\1', s)
    s = s.replace('//', ')/(').replace('{', '((').replace('}', '))')
    s = re.sub(r'(?<![A-Za-z])ctg(?![A-Za-z])', 'cot', s)     # \b не годится: «3tg» — без границы
    s = re.sub(r'(?<![A-Za-z])tg(?![A-Za-z])', 'tan', s)
    return s


def parse(s):
    return parse_expr(to_py(s), local_dict=LOCAL, transformations=TR)


def equation(s):
    lhs, rhs = s.split('=')
    return parse(lhs) - parse(rhs)


# ───────────────────────── вёрстка формул ─────────────────────────

def tree(s):
    def seq(i, stops):
        out, buf = [], []

        def flush():
            if buf:
                out.append(('t', ''.join(buf)))
                buf.clear()

        while i < len(s):
            if any(s.startswith(st, i) for st in stops):
                break
            if s.startswith('√{', i):
                flush()
                inner, i = seq(i + 2, ('}',))
                out.append(('sq', inner))
                i += 1
            elif s.startswith('^{', i):
                flush()
                inner, i = seq(i + 2, ('}',))
                out.append(('sup', inner))
                i += 1
            elif s[i] == '^':
                flush()
                out.append(('sup', [('t', s[i + 1])]))
                i += 2
            elif s[i] == '{':
                flush()
                num, i = seq(i + 1, ('//',))
                den, i = seq(i + 2, ('}',))
                out.append(('fr', num, den))
                i += 1
            else:
                buf.append(s[i])
                i += 1
        flush()
        return out, i

    nodes, i = seq(0, ())
    assert i == len(s), s
    return nodes


ITAL = re.compile(r'(?<![A-Za-z])([xantm])(?![A-Za-z])')


def H(s):
    def h(nodes):
        out = []
        for nd in nodes:
            if nd[0] == 't':
                out.append(ITAL.sub(r'<i>\1</i>', html.escape(nd[1], quote=False)))
            elif nd[0] == 'fr':
                out.append(f'<span class="fr"><span>{h(nd[1]).strip()}</span><span>{h(nd[2]).strip()}</span></span>')
            elif nd[0] == 'sq':
                out.append(f'√<span class="sq">{h(nd[1])}</span>')
            else:
                out.append(f'<sup>{h(nd[1])}</sup>')
        return ''.join(out)
    return h(tree(s))


SUPCH = '0123456789n+−()'
SUPMAP = str.maketrans(SUPCH, '⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ⁺⁻⁽⁾')


def T(s):
    def wrap(v):
        return v if re.fullmatch(r'[\w√π.,]+', v) else f'({v})'

    def t(nodes):
        out = []
        for nd in nodes:
            if nd[0] == 't':
                out.append(nd[1])
            elif nd[0] == 'fr':
                out.append(wrap(t(nd[1]).strip()) + '/' + wrap(t(nd[2]).strip()))
            elif nd[0] == 'sq':
                out.append('√' + wrap(t(nd[1])))
            else:
                v = t(nd[1])
                out.append(v.translate(SUPMAP) if all(c in SUPCH for c in v) else f'^({v})')
        return ''.join(out)
    return t(tree(s))


# ───────────────────────── численная проверка ─────────────────────────

def plain(F):
    """tg и ctg через sin/cos: так ОДЗ видна как знаменатели."""
    return F.replace(sp.tan, lambda u: sp.sin(u) / sp.cos(u)).replace(sp.cot, lambda u: sp.cos(u) / sp.sin(u))


def conditions(F):
    ne, ge = [], []
    for sub in sp.preorder_traversal(F):
        if isinstance(sub, sp.Pow) and sub.base.has(X) and sub.exp.is_number:
            if sub.exp.is_negative:
                ne.append(sub.base)
            if sub.exp.is_Rational and sub.exp.q == 2:
                ge.append(sub.base)
    return ne, ge


class Eq_:
    def __init__(self, F):
        self.F = plain(F)
        self.f = sp.lambdify(X, self.F, 'numpy')
        self.fm = sp.lambdify(X, self.F, 'mpmath')
        ne, ge = conditions(self.F)
        self.ne = [sp.lambdify(X, g, 'mpmath') for g in ne]
        self.ge_sym = ge
        self.ge = [sp.lambdify(X, g, 'mpmath') for g in ge]

    def ok(self, r, tol):
        """r — корень и лежит в ОДЗ."""
        try:
            if any(abs(g(r)) < 1e-20 for g in self.ne):
                return False
            if any(mpmath.re(g(r)) < -1e-30 for g in self.ge):
                return False
            v = self.fm(r)
        except (ZeroDivisionError, ValueError):
            return False
        return mpmath.isfinite(v) and abs(v) < tol

    def in_domain(self, r):
        try:
            return (all(abs(g(r)) > 1e-20 for g in self.ne)
                    and all(mpmath.re(g(r)) > -1e-30 for g in self.ge))
        except (ZeroDivisionError, ValueError):
            return False


def refine_mp(fm, a, b):
    a, b = mpmath.mpf(a), mpmath.mpf(b)
    fa = mpmath.re(fm(a))
    for _ in range(140):
        c = (a + b) / 2
        fc = mpmath.re(fm(c))
        if fc == 0:
            return c
        if (fc > 0) == (fa > 0):
            a, fa = c, fc
        else:
            b = c
    return (a + b) / 2


def raw_candidates(f, fm, lo, hi, h=1e-4):
    xs = np.linspace(lo, hi, int((hi - lo) / h) + 1)
    with np.errstate(all='ignore'):
        ys = np.asarray(f(xs), dtype=float) * np.ones_like(xs)
    fin = np.isfinite(ys)
    out = []
    sg = np.sign(ys)
    for i in np.where(fin[:-1] & fin[1:] & (sg[:-1] * sg[1:] < 0))[0]:
        a, b = xs[i], xs[i + 1]
        with np.errstate(all='ignore'):
            for _ in range(60):
                c = (a + b) / 2
                if np.sign(f(c)) == sg[i]:
                    a = c
                else:
                    b = c
            if abs(f((a + b) / 2)) > 1e-3:      # полюс, а не корень
                continue
        # уточняем в mpmath от исходной ячейки сетки: у кратного корня float-шум
        # сбивает знак в окрестности 1e−5, а на концах ячейки знак ещё надёжен
        out.append(refine_mp(fm, xs[i], xs[i + 1]))
    ay = np.where(fin, np.abs(ys), np.inf)
    mins = (ay[1:-1] <= ay[:-2]) & (ay[1:-1] <= ay[2:]) & (ay[1:-1] < 1e-3)
    gr = (math.sqrt(5) - 1) / 2
    for i in np.where(mins)[0] + 1:
        a, b = xs[i - 1], xs[i + 1]
        with np.errstate(all='ignore'):
            for _ in range(90):
                c, d = b - gr * (b - a), a + gr * (b - a)
                if abs(f(c)) < abs(f(d)):
                    b = d
                else:
                    a = c
        out.append(mpmath.mpf((a + b) / 2))
    return out


def roots(F, lo, hi):
    """Все корни F на [lo; hi] с учётом ОДЗ."""
    e = Eq_(F)
    cand = raw_candidates(e.f, e.fm, lo, hi)
    for g in e.ge_sym:                      # корни на границе ОДЗ: √(−cos x) = 0
        gf, gm = sp.lambdify(X, g, 'numpy'), sp.lambdify(X, g, 'mpmath')
        cand += raw_candidates(gf, gm, lo, hi)
    # У кратного корня (tg x + tg 3x − tg 4x ≈ c·t³ около πn) |F| мал на целой окрестности,
    # кандидатов там несколько. Берём в каждой окрестности 1e−3 самый точный.
    good = []
    for r in sorted((r for r in cand if e.ok(r, 1e-9)), key=lambda r: abs(e.fm(r))):
        if not any(abs(r - q) < 1e-3 for q in good):
            good.append(r)
    return sorted(float(r) for r in good)


@dataclass
class Series:
    a0: object
    d: object
    excl: tuple = None      # исключить n = c0 + c1·m


def series_of(s):
    excl = None
    if ', n ≠ ' in s:
        s, cond = s.split(', n ≠ ')
        e = parse(cond)
        excl = (int(e.subs(M, 0)), int(e.subs(M, 1) - e.subs(M, 0)))
    out = []
    for v in ([s.replace('±', '+', 1), s.replace('±', '−', 1)] if '±' in s else [s]):
        e = parse(v)
        if '(−1)^' in v:
            assert excl is None
            pieces = [e.subs(N, 2 * M), e.subs(N, 2 * M + 1)]
            var = M
        else:
            pieces, var = [e], N
        for p in pieces:
            a0 = p.subs(var, 0)
            d = sp.nsimplify(p.subs(var, 1) - a0)
            for k in (-1, 2, 3):
                assert abs(float(p.subs(var, k) - a0 - k * d)) < 1e-12, f'не линейно: {s}'
            out.append(Series(a0, d, excl))
    return out


def points(series, lo, hi):
    pts = []
    for s in series:
        a0, d = float(s.a0), float(s.d)
        k1, k2 = sorted(((lo - a0) / d, (hi - a0) / d))
        for k in range(math.ceil(k1), math.floor(k2) + 1):
            if s.excl and (k - s.excl[0]) % s.excl[1] == 0:
                continue
            pts.append(mpmath.mpf(str(sp.N(s.a0 + s.d * k, 50))))
    return pts


def mpval(s):
    return mpmath.mpf(str(sp.N(parse(s), 50)))


LO, HI = -6 * math.pi, 6 * math.pi


def check_series(eq, ans, where):
    F = equation(eq)
    e = Eq_(F)
    if isinstance(ans, tuple) and ans[0] == 'кроме':      # тождество: искать корни бессмысленно
        bad = [s.a0 + s.d * k for s in series_of(ans[1]) for k in range(-6, 7)]
        for b in bad:
            assert not e.in_domain(mpmath.mpf(str(sp.N(b, 50)))), f'{where}: {b} в ОДЗ'
        rnd = random.Random(1)
        for _ in range(300):
            r = mpmath.mpf(rnd.uniform(LO, HI))
            if min(abs(r - float(b)) for b in bad) > 1e-3:
                assert e.ok(r, 1e-15), f'{where}: в точке {r} не тождество'
        return
    found = [r for r in roots(F, LO, HI) if LO + 0.05 < r < HI - 0.05]
    if ans == 'нет':
        assert not found, f'{where}: ответ «нет корней», а найдено {found[:3]}'
        return
    claimed = [p for p in points([s for a in ans for s in series_of(a)], LO + 0.05, HI - 0.05)]
    for p in claimed:
        assert e.ok(p, 1e-15), f'{where}: x = {float(p):.6f} из ответа — не корень или вне ОДЗ'
    for r in found:
        assert any(abs(r - p) < 1e-6 for p in claimed), f'{where}: корень {r:.6f} не попал в ответ'
    for p in claimed:
        assert any(abs(r - p) < 1e-6 for r in found), f'{where}: численно не найден корень {float(p):.6f}'


def segment(seg):
    left, right = seg[0], seg[-1]
    lo, hi = seg[1:-1].split(';')
    return float(mpval(lo)), float(mpval(hi)), left == '[', right == ']'


def roots_on(eq, seg, F=None):
    lo, hi, cl, cr = segment(seg)
    rs = roots(equation(eq) if F is None else F, lo - 0.1, hi + 0.1)
    return [r for r in rs
            if (r > lo - 1e-6 if cl else r > lo + 1e-6) and (r < hi + 1e-6 if cr else r < hi - 1e-6)]


def check_values(found, claimed, where):
    want = sorted(float(mpval(c)) for c in claimed)
    assert len(found) == len(want) and all(abs(a - b) < 1e-6 for a, b in zip(found, want)), \
        f'{where}: найдено {found}, в ответе {want}'


# ───────────────────────── данные: тригонометрия ─────────────────────────

@dataclass
class Task:
    kind: str                 # solve | ab | seg | minpos | maxneg | sum | param
    eq: str
    ans: object = None        # серии | 'нет' | ('кроме', серия) | значения
    seg: str = None
    b: list = None            # ответ к пункту б
    note: str = None          # только для преподавателя
    text: str = None          # готовая формулировка (param)


def S(eq, ans, note=None):
    return Task('solve', eq, ans if ans == 'нет' or isinstance(ans, tuple) else list(ans), note=note)


def AB(eq, seg, ans, b, note=None):
    return Task('ab', eq, list(ans), seg=seg, b=list(b), note=note)


@dataclass
class Block:
    head: str
    cols: int
    tasks: list


@dataclass
class Sheet:
    file: str
    title: str
    who: str
    blocks: list
    ans_cols: int = 1


ZERO = 'Решите уравнения.'

SHEET1 = Sheet('1 Элементарные тригонометрические уравнения',
               'Элементарные тригонометрические уравнения', 'Настя, Кирилл, Лиза', [
    Block(ZERO, 4, [
        S('sin x = {1//2}', ['(−1)^n·π/6 + πn']),
        S('cos x = {√2//2}', ['±π/4 + 2πn']),
        S('tg x = √3', ['π/3 + πn']),
        S('ctg x = 1', ['π/4 + πn']),
        S('sin x = −{√3//2}', ['(−1)^{n+1}·π/3 + πn']),
        S('cos x = −{1//2}', ['±2π/3 + 2πn']),
        S('tg x = −1', ['−π/4 + πn']),
        S('ctg x = −√3', ['5π/6 + πn']),
        S('tg x = −{√3//3}', ['−π/6 + πn']),
        S('ctg x = {√3//3}', ['π/3 + πn']),
        S('sin x = 0', ['πn']),
        S('cos x = 0', ['π/2 + πn']),
        S('sin x = 1', ['π/2 + 2πn']),
        S('cos x = −1', ['π + 2πn']),
        S('sin x = −1', ['−π/2 + 2πn']),
        S('ctg x = 0', ['π/2 + πn']),
    ]),
    Block(None, 4, [
        S('sin x = {1//3}', ['(−1)^n·arcsin(1/3) + πn']),
        S('cos x = {π//3}', 'нет', 'π/3 ≈ 1,05 > 1'),
        S('cos x = −{2//5}', ['±(π − arccos(2/5)) + 2πn'], 'или ±arccos(−2/5) + 2πn'),
        S('tg x = 4', ['arctg 4 + πn']),
        S('cos x = −{√5//2}', 'нет', '√5/2 ≈ 1,12 > 1'),
        S('sin x = {π//4}', ['(−1)^n·arcsin(π/4) + πn'], 'π/4 ≈ 0,79 < 1 — корни есть'),
        S('ctg x = −3', ['π − arcctg 3 + πn'], 'arcctg(−3) = π − arcctg 3'),
    ]),
    Block(None, 2, [
        S('sin 2x = {√3//2}', ['(−1)^n·π/6 + πn/2']),
        S('cos{x//3} = −{√2//2}', ['±9π/4 + 6πn']),
        S('tg 3x = {√3//3}', ['π/18 + πn/3']),
        S('cos(x − {π//6}) = {1//2}', ['π/2 + 2πn', '−π/6 + 2πn'], 'или π/6 ± π/3 + 2πn'),
        S('sin(2x + {π//4}) = −1', ['−3π/8 + πn']),
        S('tg({x//2} + {π//3}) = −√3', ['2π/3 + 2πn'], 'или −4π/3 + 2πn'),
        S('2cos(3x − {π//4}) + √2 = 0', ['π/3 + 2πn/3', '−π/6 + 2πn/3']),
        S('ctg({π//4} − x) = 1', ['πn']),
        S('sin({π//3} − 2x) = {1//2}', ['π/12 + πn', '3π/4 + πn'], 'знак перед 2x'),
        S('cos 4x = 0', ['π/8 + πn/4']),
        S('√2·sin{x//2} − 1 = 0', ['(−1)^n·π/2 + 2πn']),
    ]),
    Block(None, 2, [
        S('2sin x + √3 = 0', ['(−1)^{n+1}·π/3 + πn']),
        S('3tg x − √3 = 0', ['π/6 + πn']),
        S('4cos^2x = 3', ['±π/6 + πn']),
        S('2sin^2x = 1', ['π/4 + πn/2']),
        S('tg^2x = 3', ['±π/3 + πn']),
        S('sin x·cos x = 0', ['πn/2']),
        S('(2cos x − 1)(tg x + 1) = 0', ['±π/3 + 2πn', '−π/4 + πn']),
        S('sin x·(2cos x + √2) = 0', ['πn', '±3π/4 + 2πn']),
        S('tg x·(sin x − 1) = 0', ['πn'], 'ловушка: при sin x = 1 cos x = 0, tg x не определён'),
    ]),
    Block(None, 1, [
        Task('seg', 'cos x = {√3//2}', ['−11π/6', '−π/6', 'π/6', '11π/6'], seg='[−2π; 2π]'),
        Task('minpos', 'sin 2x = −{√2//2}', ['5π/8']),
        Task('seg', 'tg x = −√3', ['−π/3', '2π/3'], seg='(−π; 3π/2)',
             note='концы не входят; 5π/3 > 3π/2'),
        Task('maxneg', 'cos(x + {π//3}) = {1//2}', ['−2π/3']),
    ]),
], ans_cols=2)

SHEET2 = Sheet('2 Уравнения, сводящиеся к элементарным',
               'Тригонометрические уравнения, сводящиеся к элементарным',
               'Настя, Кирилл, Алёна, Эмир, Тимур, Гоша', [
    Block(ZERO, 2, [
        S('2sin^2x − sin x − 1 = 0', ['π/2 + 2πn', '(−1)^{n+1}·π/6 + πn']),
        S('2cos^2x + 3cos x − 2 = 0', ['±π/3 + 2πn'], 'cos x = −2 — посторонний'),
        S('tg^2x − (1 + √3)tg x + √3 = 0', ['π/4 + πn', 'π/3 + πn']),
        S('6cos^2x − 5cos x + 1 = 0', ['±π/3 + 2πn', '±arccos(1/3) + 2πn']),
        S('ctg^2x + 2ctg x − 3 = 0', ['π/4 + πn', 'π − arcctg 3 + πn']),
        S('2sin^2 2x + sin 2x − 1 = 0', ['(−1)^n·π/12 + πn/2', '−π/4 + πn']),
        S('{1//sin^2x} + {1//sin x} − 2 = 0', ['π/2 + 2πn', '(−1)^{n+1}·π/6 + πn'],
          'замена t = 1/sin x'),
    ]),
    Block(None, 2, [
        S('2cos^2x + 5sin x − 4 = 0', ['(−1)^n·π/6 + πn'], 'sin x = 2 — посторонний'),
        S('2sin^2x + 3cos x = 0', ['±2π/3 + 2πn']),
        S('2sin^2x = 5 − 5cos x', ['2πn'], 'cos x = 3/2 — посторонний'),
        S('3sin^2x + 7cos x − 3 = 0', ['π/2 + πn'], 'неполное квадратное: cos x(7 − 3cos x) = 0'),
        S('{1//cos^2x} − 3tg x + 1 = 0', ['π/4 + πn', 'arctg 2 + πn'], '1/cos²x = 1 + tg²x'),
        S('{1//sin^2x} + ctg x − 3 = 0', ['π/4 + πn', 'π − arcctg 2 + πn'], '1/sin²x = 1 + ctg²x'),
        S('cos 2x + 3sin x = 2', ['π/2 + 2πn', '(−1)^n·π/6 + πn']),
        S('cos 2x + sin^2x = cos x', ['π/2 + πn', '2πn']),
    ]),
    Block(None, 2, [
        S('sin x − √3cos x = 0', ['π/3 + πn']),
        S('2sin x + cos x = 0', ['−arctg(1/2) + πn']),
        S('sin 2x = cos 2x', ['π/8 + πn/2']),
        S('√3·sin{x//2} + cos{x//2} = 0', ['−π/3 + 2πn']),
        S('3sin x − 4cos x = 0', ['arctg(4/3) + πn']),
    ]),
    Block(None, 2, [
        S('sin^2x − 4sin x cos x + 3cos^2x = 0', ['π/4 + πn', 'arctg 3 + πn']),
        S('√3·sin^2x − 4sin x cos x + √3·cos^2x = 0', ['π/3 + πn', 'π/6 + πn']),
        S('3sin^2x + sin x cos x − 2cos^2x = 0', ['arctg(2/3) + πn', '−π/4 + πn']),
        S('√3·sin x cos x + cos^2x = 0', ['π/2 + πn', '−π/6 + πn'],
          'ловушка: делить на cos²x нельзя — теряется cos x = 0; выносить cos x'),
        S('2sin^2x − 3sin x cos x + 4cos^2x = 4', ['πn', '−arctg(3/2) + πn'], '4 = 4sin²x + 4cos²x'),
        S('5sin^2x + 3sin 2x − 3cos^2x = 1', ['arctg(1/2) + πn', '−arctg 2 + πn'],
          'sin 2x = 2sin x cos x, 1 = sin²x + cos²x → 2tg²x + 3tg x − 2 = 0'),
    ]),
    Block(None, 2, [
        S('tg x + ctg x = 2', ['π/4 + πn']),
        S('3tg x − ctg x = 2', ['π/4 + πn', '−arctg(1/3) + πn']),
        S('2tg x − 2ctg x = 3', ['arctg 2 + πn', '−arctg(1/2) + πn']),
        S('tg^2x + ctg^2x = 2', ['π/4 + πn/2']),
        S('tg x + ctg x = 1', 'нет', 't² − t + 1 = 0, D < 0'),
    ]),
    Block(None, 2, [
        S('sin 2x = sin x', ['πn', '±π/3 + 2πn']),
        S('2cos^3x = cos x', ['π/2 + πn', 'π/4 + πn/2'], 'ловушка: деление на cos x теряет серию'),
        S('2sin x cos x − 2sin x + cos x − 1 = 0', ['2πn', '(−1)^{n+1}·π/6 + πn'],
          '(cos x − 1)(2sin x + 1) = 0'),
        S('2sin x cos x + √3·sin x − 2cos x − √3 = 0', ['π/2 + 2πn', '±5π/6 + 2πn'],
          '(sin x − 1)(2cos x + √3) = 0'),
        S('tg x·sin x + 1 = sin x + tg x', ['π/4 + πn'],
          '(tg x − 1)(sin x − 1) = 0; sin x = 1 вне ОДЗ'),
    ]),
    Block(None, 1, [
        AB('2cos^2x − 3sin x − 3 = 0', '[π; 5π/2]', ['−π/2 + 2πn', '(−1)^{n+1}·π/6 + πn'],
           ['7π/6', '3π/2', '11π/6']),
        AB('2sin^2x − √3·sin 2x = 0', '[−3π; −3π/2]', ['πn', 'π/3 + πn'],
           ['−3π', '−8π/3', '−2π', '−5π/3']),
        AB('sin 2x + 2sin x = √3·cos x + √3', '[−2π; −π/2]', ['π + 2πn', '(−1)^n·π/3 + πn'],
           ['−5π/3', '−4π/3', '−π'], '(cos x + 1)(2sin x − √3) = 0'),
        AB('tg x − 2ctg x + 1 = 0', '[π; 5π/2]', ['π/4 + πn', '−arctg 2 + πn'],
           ['5π/4', '2π − arctg 2', '9π/4']),
    ]),
])

PARAM_EQ = 'cos^2x − (a + 2)cos x + 2a = 0'
SHEET3 = Sheet('3 Тригонометрические уравнения, повышенный уровень (Алёна)',
               'Тригонометрические уравнения: повышенный уровень', 'Алёна (индивидуально)', [
    Block(None, 1, [
        AB('{2sin^2x − sin x // 2cos x − √3} = 0', '[−5π/2; −π]', ['πn', '5π/6 + 2πn'],
           ['−2π', '−7π/6', '−π'], 'sin x = 1/2 даёт π/6 (знаменатель 0) и 5π/6'),
        AB('(2sin^2x − 3sin x + 1)·√{−cos x} = 0', '[3π/2; 3π]', ['π/2 + πn', '5π/6 + 2πn'],
           ['3π/2', '5π/2', '17π/6'], 'нужно cos x ≤ 0: π/6 отпадает, π/2 + 2πn входит в π/2 + πn'),
        AB('√{1 + cos x} = √2·sin x', '[3π; 9π/2]', ['π/3 + 2πn', 'π + 2πn'], ['3π', '13π/3'],
           'условие sin x ≥ 0; cos x = −1 подходит (обе части 0)'),
        AB('9^{sin x} + 9^{−sin x} = {10//3}', '[2π; 7π/2]', ['±π/6 + πn'],
           ['13π/6', '17π/6', '19π/6'], 't = 9^{sin x}: t + 1/t = 10/3, sin x = ±1/2'),
        AB('sin 2x + 2sin x − 2cos x + 2 = 0', '[−7π/2; −2π]', ['2πn', '−π/2 + 2πn'],
           ['−5π/2', '−2π'], 't = sin x − cos x, sin 2x = 1 − t²; t = −1'),
        AB('|cos x| = cos x + 2sin x', '[−2π; π]', ['2πn', '3π/4 + 2πn'],
           ['−2π', '−5π/4', '0', '3π/4'], 'cos x ≥ 0 → sin x = 0; cos x < 0 → tg x = −1'),
    ]),
    Block(ZERO, 2, [
        S('√3·sin x + cos x = √2', ['π/12 + 2πn', '7π/12 + 2πn'], '2sin(x + π/6) = √2'),
        S('sin x + cos x + 2sin x cos x = 1', ['2πn', 'π/2 + 2πn'],
          't = sin x + cos x, t² + t − 2 = 0, t = −2 не годится'),
        S('ctg x − tg x = 2√3', ['π/12 + πn/2'], 'ctg x − tg x = 2ctg 2x'),
        S('sin x + sin 2x + sin 3x + sin 4x = 0', ['2πn/5', 'π/2 + πn', 'π + 2πn'],
          '4sin(5x/2)·cos x·cos(x/2) = 0'),
        S('sin x·sin 3x = {1//2}', ['π/4 + πn/2', '±π/6 + πn'], 'cos 2x(2cos 2x − 1) = 0'),
        S('sin^2 2x + sin^2 3x + sin^2 4x = {3//2}', ['π/12 + πn/6', '±π/3 + πn'],
          'понижение степени → cos 6x(2cos 2x + 1) = 0'),
        S('sin^8x + cos^8x = {41//128}', ['±π/6 + πn/2'], 'u = sin²2x: u²/8 − u + 87/128 = 0, u = 3/4'),
        S('tg x + tg 3x = tg 4x', ['πn/3', 'π/4 + πn/2'],
          'sin 4x/(cos x cos 3x) = sin 4x/cos 4x; ОДЗ режет π/2 + πn'),
        S('{sin 3x // sin x} − {cos 3x // cos x} = 2', ('кроме', 'πn/2'),
          'левая часть ≡ sin 2x/(sin x cos x) = 2 — тождество на ОДЗ'),
        S('cos x·cos 2x·cos 4x = {1//8}', ['2πn/7, n ≠ 7m', 'π/9 + 2πn/9, n ≠ 9m + 4'],
          'умножить на 8sin x: sin 8x = sin x, но sin x ≠ 0'),
        S('sin x·cos 4x = 1', ['π/2 + 2πn'], 'оценка: sin x = ±1 и cos 4x = ±1 одного знака'),
        S('sin^7x + cos^7x = 1', ['2πn', 'π/2 + 2πn'], 'sin⁷x ≤ sin²x, cos⁷x ≤ cos²x'),
    ]),
    Block(None, 1, [
        Task('sum', 'sin 5x = cos 3x', ['2π'], seg='[0; π]',
             note='корни π/16, 5π/16, 9π/16, 13π/16 и π/4'),
        Task('param', PARAM_EQ, 'a ∈ [0; 1)',
             text='Найдите все значения a, при каждом из которых уравнение '
                  + PARAM_EQ + ' имеет на отрезке [0; 5π/2] ровно три корня.',
             note='(cos x − 2)(cos x − a) = 0'),
    ]),
])

TRIG = [SHEET1, SHEET2, SHEET3]


def check_trig(sheet):
    k = 0
    for bl in sheet.blocks:
        for t in bl.tasks:
            k += 1
            where = f'{sheet.file}, №{k}'
            if t.kind in ('solve', 'ab'):
                check_series(t.eq, t.ans, where)
            if t.kind == 'ab':
                check_values(roots_on(t.eq, t.seg), t.b, where + ' б)')
                assert all(any(abs(float(mpval(v)) - float(p)) < 1e-9
                               for p in points([s for a in t.ans for s in series_of(a)], -40, 40))
                           for v in t.b), where + ': б) не из серий а)'
            elif t.kind == 'seg':
                check_values(roots_on(t.eq, t.seg), t.ans, where)
            elif t.kind in ('minpos', 'maxneg'):
                rs = roots(equation(t.eq), -4 * math.pi, 4 * math.pi)
                v = min(r for r in rs if r > 1e-9) if t.kind == 'minpos' else max(r for r in rs if r < -1e-9)
                check_values([v], t.ans, where)
            elif t.kind == 'sum':
                rs = roots_on(t.eq, t.seg)
                assert abs(sum(rs) - float(mpval(t.ans[0]))) < 1e-6, f'{where}: сумма {sum(rs)}'
            elif t.kind == 'param':
                for av in [-1.5, -1.01, -1, -0.99, -0.5, -1e-3, 0, 1e-3, 0.3, 0.5, 0.71,
                           0.999, 1, 1.001, 1.5, 2, 2.5]:
                    F = equation(t.eq).subs(A, sp.nsimplify(av))
                    cnt = len(roots_on(None, '[0; 5π/2]', F))
                    assert (cnt == 3) == (0 <= av < 1), f'{where}: a = {av}, корней {cnt}'
    return k


# ───────────────────────── данные: 6 класс ─────────────────────────

def factor(n):
    out, p = [], 2
    while n > 1:
        e = 0
        while n % p == 0:
            n //= p
            e += 1
        if e:
            out.append(f'{p}^{e}' if e > 1 else str(p))
        p += 1
    return '·'.join(out)


def frac(q):
    """Fraction → разметка: целое, дробь или смешанное число."""
    q = Fr(q)
    sign = '−' if q < 0 else ''
    q = abs(q)
    w, r = divmod(q.numerator, q.denominator)
    if r == 0:
        return sign + str(w)
    f = '{' + f'{r}//{q.denominator}' + '}'
    return sign + (f'{w}{f}' if w else f)


def fr_eval(s):
    p = re.sub(r'(\d+)\{(\d+)//(\d+)\}', r'(Fr(\1)+Fr(\2,\3))', s)
    p = re.sub(r'\{(\d+)//(\d+)\}', r'Fr(\1,\2)', p).replace('−', '-')
    return p


# eval только над строками из этого файла (разметка дробей → Fraction), чужого ввода нет
def fr_value(s):
    return eval(fr_eval(s), {'Fr': Fr})


def fr_solve(s):
    lhs, rhs = s.split('=')
    f = lambda xv: eval(fr_eval(lhs).replace('x', 'X') + '-(' + fr_eval(rhs) + ')', {'Fr': Fr, 'X': xv})
    f0, f1 = f(Fr(0)), f(Fr(1))
    xv = -f0 / (f1 - f0)
    assert f(xv) == 0
    return xv


@dataclass
class Q:
    text: str
    ans: str
    note: str = None


def sixth():
    b = []
    b.append(Block('Разложите на простые множители.', 3,
                   [Q(str(n), f'{n} = {factor(n)}') for n in (84, 180, 1001)]))
    b.append(Block('Найдите наибольший общий делитель.', 3,
                   [Q(f'НОД({", ".join(map(str, ns))})', str(math.gcd(*ns)))
                    for ns in ((42, 56), (75, 105), (84, 126), (35, 64), (36, 60, 84))]))
    b.append(Block('Найдите наименьшее общее кратное.', 3,
                   [Q(f'НОК({", ".join(map(str, ns))})', str(math.lcm(*ns)))
                    for ns in ((6, 8), (12, 18), (14, 21), (9, 16), (4, 6, 10))]))
    pairs = ((25, 36), (21, 49), (32, 45), (51, 68))
    b.append(Block(None, 1, [Q('Какие из пар чисел взаимно простые: '
                               + '; '.join(f'{p} и {q}' for p, q in pairs) + '?',
                               '; '.join(f'{p} и {q} — ' + ('да' if math.gcd(p, q) == 1
                                                           else f'нет (общий делитель {math.gcd(p, q)})')
                                         for p, q in pairs))]))
    b.append(Block('Сократите дроби.', 4,
                   [Q('{' + f'{p}//{q}' + '}', frac(Fr(p, q))) for p, q in ((24, 36), (45, 60), (56, 98), (75, 120))]))
    sums = ['{1//4} + {1//6}', '{2//9} + {5//12}', '{7//15} − {3//10}', '{5//8} + {7//12}',
            '{11//18} − {5//12}', '{3//14} + {5//21}', '{7//20} + {4//15}', '{9//16} − {5//24}',
            '{1//2} + {1//3} + {1//4}', '{5//6} − {1//4} + {2//9}']
    b.append(Block('Вычислите.', 4, [Q(s, frac(fr_value(s))) for s in sums]))
    mixed = ['2{1//3} + 1{3//4}', '5{1//6} − 2{3//4}', '3{5//12} + 2{7//18}', '4{7//10} − 1{13//15}',
             '1{5//8} + 2{3//10} + {3//40}']
    b.append(Block(None, 3, [Q(s, frac(fr_value(s))) for s in mixed]))
    eqs = ['x + {3//8} = {5//6}', '{9//10} − x = {2//15}']
    b.append(Block('Решите уравнения.', 2, [Q(s, 'x = ' + frac(fr_solve(s))) for s in eqs]))

    sh, md = 48, 36
    g1 = math.gcd(sh, md)
    t1, t2 = 12, 18
    l2 = math.lcm(t1, t2)
    d1, d2 = Fr(3, 8), Fr(5, 12)
    c1, c2 = 60, 84
    g4 = math.gcd(c1, c2)
    b.append(Block(None, 1, [
        Q(f'Для подарков купили {sh} шоколадок и {md} мандаринов. Какое наибольшее число одинаковых '
          'подарков можно составить, чтобы использовать всё? Сколько шоколадок и сколько мандаринов '
          'будет в каждом подарке?',
          f'{g1} подарков; в каждом {sh // g1} шоколадки и {md // g1} мандарина'),
        Q(f'С остановки автобус № 1 отправляется каждые {t1} минут, а автобус № 5 — каждые {t2} минут. '
          'В 8:00 они отправились одновременно. В какое время они в следующий раз отправятся одновременно?',
          f'через НОК({t1}, {t2}) = {l2} мин, в 8:{l2:02d}'),
        Q(f'Турист в первый день прошёл {frac(d1)} маршрута, а во второй — {frac(d2)} маршрута. '
          'Какую часть маршрута он прошёл за два дня? Какая часть маршрута осталась?',
          f'{frac(d1 + d2)}; осталось {frac(1 - d1 - d2)}'),
        Q(f'Из двух кусков ткани длиной {c1} м и {c2} м нужно нарезать без остатка одинаковые отрезы '
          'наибольшей возможной длины. Какой длины будут отрезы и сколько их получится?',
          f'по {g4} м; {c1 // g4 + c2 // g4} отрезов ({c1 // g4} + {c2 // g4})'),
    ]))
    return Sheet('4 НОД, НОК, сложение и вычитание дробей (Александр)',
                 'НОД, НОК, сложение и вычитание дробей', 'Александр, 6 класс', b, ans_cols=2)


SHEET4 = sixth()
SHEETS = [SHEET1, SHEET2, SHEET3, SHEET4]


# ───────────────────────── тексты условий и ответов ─────────────────────────

def seg_word(seg):
    return 'отрезку' if seg[0] == '[' and seg[-1] == ']' else 'промежутку'


def task_text(t, fmt):
    """Условие в виде строк разметки (несколько строк — для а) и б))."""
    if isinstance(t, Q):
        return [t.text]
    if t.kind == 'solve':
        return [t.eq]
    if t.kind == 'ab':
        return [f'а) Решите уравнение {t.eq}.',
                f'б) Найдите все корни этого уравнения, принадлежащие {seg_word(t.seg)} {t.seg}.']
    if t.kind == 'seg':
        return [f'Найдите все корни уравнения {t.eq}, принадлежащие {seg_word(t.seg)} {t.seg}.']
    if t.kind == 'minpos':
        return [f'Найдите наименьший положительный корень уравнения {t.eq}.']
    if t.kind == 'maxneg':
        return [f'Найдите наибольший отрицательный корень уравнения {t.eq}.']
    if t.kind == 'sum':
        return [f'Найдите сумму корней уравнения {t.eq}, принадлежащих {seg_word(t.seg)} {t.seg}.']
    return [t.text]


def series_text(ans):
    if ans == 'нет':
        return 'корней нет'
    if isinstance(ans, tuple):
        return f'любое x, кроме x = {ans[1]}, n ∈ ℤ'
    tail = '; n, m ∈ ℤ' if any('≠' in a for a in ans) else ', n ∈ ℤ'
    return 'x = ' + '; x = '.join(ans) + tail


def answer_text(t):
    if isinstance(t, Q):
        return t.ans
    if t.kind == 'solve':
        return series_text(t.ans)
    if t.kind == 'ab':
        return f'а) {series_text(t.ans)}; б) ' + '; '.join(t.b)
    if t.kind == 'param':
        return t.ans
    return '; '.join(t.ans)


# ───────────────────────── HTML и PDF ─────────────────────────

CSS = """
@page { size: A4; margin: 12mm 13mm 12mm 15mm; }
* { box-sizing: border-box; }
html, body { background: #fff; color: #000; }
body { margin: 0; font-family: "Liberation Serif", "Times New Roman", "DejaVu Serif", serif;
       font-size: 12pt; line-height: 1.4; }
h1 { font-size: 14pt; margin: 0 0 4pt; }
h2 { font-size: 13pt; margin: 16pt 0 6pt; break-after: avoid; }
.who { margin: 0 0 6pt; }
.head { margin: 10pt 0 4pt; break-after: avoid; }
.gap { height: 8pt; }
.g { display: grid; grid-template-columns: repeat(var(--c), minmax(0, 1fr));
     align-items: baseline; column-gap: 16pt; row-gap: 5pt; }
.t { display: flex; align-items: baseline; gap: 5pt; break-inside: avoid; }
.t > .n { flex: none; min-width: 24pt; }
.nw .t > span:last-child { white-space: nowrap; }
.fr { display: inline-flex; flex-direction: column; vertical-align: middle; text-align: center;
      line-height: 1.12; margin: 0 2pt; }
.fr > span:first-child { border-bottom: 0.7pt solid #000; padding: 0 2pt 1pt; }
.fr > span:last-child { padding: 1pt 2pt 0; }
.sq { border-top: 0.7pt solid #000; padding-top: 1pt; }
sup { font-size: 0.72em; line-height: 0; }
.note { font-style: italic; font-size: 11pt; }
"""


def page(title, body):
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def sheet_html(sh):
    out = [f'<h1>{html.escape(sh.title)}</h1>']
    k = 0
    for bl in sh.blocks:
        out.append(f'<div class="head">{H(bl.head)}</div>' if bl.head else '<div class="gap"></div>')
        out.append(f'<div class="g{" nw" if bl.cols > 1 else ""}" style="--c:{bl.cols}">')
        for t in bl.tasks:
            k += 1
            body = '<br>'.join(H(line) for line in task_text(t, 'html'))
            out.append(f'<div class="t"><span class="n">{k}.</span><span>{body}</span></div>')
        out.append('</div>')
    return page(sh.title, ''.join(out))


def answers_html():
    out = ['<h1>Ответы (для преподавателя)</h1><div class="who">ДЗ от 15.10.2026. '
           'Курсивом — на что смотреть при проверке.</div>']
    for i, sh in enumerate(SHEETS, 1):
        out.append(f'<h2>Лист {i}. {html.escape(sh.title)} — {html.escape(sh.who)}</h2>')
        out.append(f'<div class="g" style="--c:{sh.ans_cols}">')
        k = 0
        for bl in sh.blocks:
            for t in bl.tasks:
                k += 1
                note = f' <span class="note">— {H(t.note)}</span>' if t.note else ''
                out.append(f'<div class="t"><span class="n">{k}.</span><span>{H(answer_text(t))}{note}</span></div>')
        out.append('</div>')
    return page('Ответы', ''.join(out))


def md_tasks():
    out = ['# ДЗ от 15.10.2026 — условия', '',
           'Сгенерировано `zadachi.py` из тех же данных, что и PDF. Ответы — в `OTVETY.md`.', '']
    for i, sh in enumerate(SHEETS, 1):
        out += [f'## Лист {i}. {sh.title}', '', f'Кому: {sh.who}.', '']
        k = 0
        for bl in sh.blocks:
            if bl.head:
                out += [f'**{T(bl.head)}**', '']
            for t in bl.tasks:
                k += 1
                lines = task_text(t, 'md')
                out.append(f'{k}. ' + T(lines[0]) + ''.join(f'<br>{T(l)}' for l in lines[1:]))
            out.append('')
    return '\n'.join(out)


def md_answers():
    out = ['# ДЗ от 15.10.2026 — ответы', '',
           'Только для преподавателя. Все ответы проверены `python3 zadachi.py check`.', '']
    for i, sh in enumerate(SHEETS, 1):
        out += [f'## Лист {i}. {sh.title} — {sh.who}', '']
        k = 0
        for bl in sh.blocks:
            for t in bl.tasks:
                k += 1
                note = f' — *{T(t.note)}*' if t.note else ''
                out.append(f'{k}. {T(answer_text(t))}{note}')
        out.append('')
    return '\n'.join(out)


def pdf(html_path, pdf_path):
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer',
                    '--virtual-time-budget=8000', f'--print-to-pdf={pdf_path}', html_path.as_uri()],
                   check=True, capture_output=True)


def check():
    for sh in TRIG:
        k = check_trig(sh)
        print(f'  {sh.file}: {k} задач — ответы сходятся')
    k = sum(len(bl.tasks) for bl in SHEET4.blocks)
    print(f'  {SHEET4.file}: {k} задач — посчитано через Fraction')


def build():
    check()
    tmp = HERE / 'build'
    tmp.mkdir(exist_ok=True)
    for sh in SHEETS:
        p = tmp / (sh.file + '.html')
        p.write_text(sheet_html(sh), encoding='utf-8')
        pdf(p, HERE / (sh.file + '.pdf'))
    p = tmp / 'otvety.html'
    p.write_text(answers_html(), encoding='utf-8')
    pdf(p, HERE / 'Ответы ко всем листам (преподавателю).pdf')
    (HERE / 'ZADACHI.md').write_text(md_tasks(), encoding='utf-8')
    (HERE / 'OTVETY.md').write_text(md_answers(), encoding='utf-8')
    print('  PDF и md собраны')


if __name__ == '__main__':
    {'check': check, 'build': build}[sys.argv[1] if len(sys.argv) > 1 else 'check']()
