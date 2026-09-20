# -*- coding: utf-8 -*-
"""Характерные ординаты эпюр N, Q, M для всех пяти схем."""
import sys
from fractions import Fraction as F
from sistemy import ALL


def fmt(v, n=2):
    x = float(v)
    if abs(x - round(x)) < 1e-9:
        return f"{round(x):d}"
    return f"{x:.{n}f}".replace('.', ',')


def uchastok(s, mem):
    """Ординаты на стержне: N, Q по концам, M по концам и в середине,
    плюс экстремум M там, где Q меняет знак."""
    L = s.length(mem)
    N0, Q0, M0 = s.internal(mem, F(0))
    N1, Q1, M1 = s.internal(mem, F(1))
    _, _, Mm = s.internal(mem, F(1, 2))
    has_q = any(d[0] == mem for d in s.dists)
    ext = None
    if has_q and Q0 * Q1 < 0:
        # Q линейна: находим t, где Q = 0
        t = Q0 / (Q0 - Q1)
        _, Qe, Me = s.internal(mem, t)
        assert Qe == 0
        ext = (t * L, Me)
    return dict(L=L, N=(N0, N1), Q=(Q0, Q1), M=(M0, Mm, M1),
                q=has_q, ext=ext)


def report(out=sys.stdout):
    for f in ALL:
        s = f(); s.solve()
        print('=' * 74, file=out)
        print(s.name, file=out)
        print('=' * 74, file=out)
        print('Кинематический анализ: ' + s.W, file=out)
        print('Реакции:', file=out)
        for k, v in s.R.items():
            print(f'   {k:6s} = {fmt(v)}'
                  f'{" кН·м" if k.startswith("M") else " кН"}', file=out)
        print(f'\n{"стержень":10s}{"L":>5s}{"N нач":>9s}{"N кон":>9s}'
              f'{"Q нач":>9s}{"Q кон":>9s}{"M нач":>10s}{"M сер":>10s}'
              f'{"M кон":>10s}', file=out)
        for mem, a, b in s.members:
            d = uchastok(s, mem)
            print(f'{mem+" ("+a+"-"+b+")":10s}{fmt(d["L"]):>5s}'
                  f'{fmt(d["N"][0]):>9s}{fmt(d["N"][1]):>9s}'
                  f'{fmt(d["Q"][0]):>9s}{fmt(d["Q"][1]):>9s}'
                  f'{fmt(d["M"][0]):>10s}{fmt(d["M"][1]):>10s}'
                  f'{fmt(d["M"][2]):>10s}', file=out)
            if d['ext']:
                x, Me = d['ext']
                print(f'{"":10s}экстремум M: x = {fmt(x)} м от начала, '
                      f'M = {fmt(Me)} кН·м  (Q = 0)', file=out)
        print(file=out)


if __name__ == "__main__":
    report()
