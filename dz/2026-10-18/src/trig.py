"""Проверка тригонометрических уравнений части 2: серии корней и отбор на отрезке."""
import math

import mpmath as mp
import sympy as sp

from common import x, tex_of

PI = sp.pi
mp.mp.dps = 40


def series_points(series, lo, hi):
    """series: [(смещение, период)] -> все точки в [lo, hi] (точно, sympy)."""
    pts = set()
    for off, per in series:
        n_lo = math.floor(float((lo - off) / per)) - 1
        n_hi = math.ceil(float((hi - off) / per)) + 1
        for n in range(n_lo, n_hi + 1):
            p = sp.nsimplify(off + n * per) if not off.has(sp.atan) else off + n * per
            if sp.N(p - lo, 50) >= -1e-40 and sp.N(hi - p, 50) >= -1e-40:
                pts.add(sp.simplify(p))
    return sorted(pts, key=lambda z: float(z))


def make_f(f_expr, conds):
    """Численная функция; None там, где уравнение не определено.
    conds — выражения, которые должны быть: ('ne0', e) — не ноль, ('ge0', e) — неотрицательны."""
    g = sp.lambdify(x, f_expr, 'mpmath')
    cfs = [(k, sp.lambdify(x, e, 'mpmath')) for k, e in conds]

    def F(z):
        for k, c in cfs:
            v = c(z)
            if k == 'ne0' and abs(v) < mp.mpf('1e-30'):
                return None
            if k == 'ge0' and v < -mp.mpf('1e-30'):
                return None
        try:
            v = g(z)
        except (ZeroDivisionError, ValueError):
            return None
        if isinstance(v, mp.mpc):
            if abs(v.imag) > mp.mpf('1e-15'):
                return None
            v = v.real
        return v
    return F


def verify(f_expr, series, conds=(), lo=-4 * PI, hi=4 * PI, n=60000):
    """1) каждая точка серий — корень (с учётом ОДЗ); 2) численный поиск минимумов |f|
    не находит корней вне серий."""
    F = make_f(f_expr, conds)
    pts = series_points(series, lo, hi)
    for p in pts:
        v = F(mp.mpf(sp.N(p, 45)))
        assert v is not None and abs(v) < mp.mpf('1e-18'), ('точка серии не корень', p, v)
    flo, fhi = float(lo), float(hi)
    step = (fhi - flo) / n
    vals = []
    for i in range(n + 1):
        z = flo + i * step
        v = F(mp.mpf(z))
        vals.append(math.inf if v is None else abs(float(v)))
    fp = [float(p) for p in pts]
    for i in range(1, n):
        if vals[i] < 0.05 and vals[i] <= vals[i - 1] and vals[i] <= vals[i + 1]:
            z = flo + i * step
            if z - flo < 0.01 or fhi - z < 0.01:
                continue
            assert any(abs(z - q) < 3e-3 for q in fp), ('корень вне серий?', z, vals[i])
    return pts


def on_segment(series, L, R):
    return series_points(series, L, R)


def pts_tex(pts):
    return ';\\ '.join(tex_of(p) for p in pts)
