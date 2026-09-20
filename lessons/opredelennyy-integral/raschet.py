# -*- coding: utf-8 -*-
"""Пересчёт всех ответов занятия по определённому интегралу.

На каждой задаче проверяются три вещи:
  1) sympy берёт интеграл символьно и точно — Rational и константы,
     никакого float;
  2) тот же интеграл считается независимо численной квадратурой mpmath
     с 30 знаками: это ловит ошибку самого символьного движка;
  3) ответ, выписанный в ZADACHI.md, OTVETY.md и на странице, сверяется
     с (1) — simplify разности обязан дать ноль.

Расходится хоть что-то — задача печатается как расхождение.
Запуск:  python3 raschet.py
"""
import mpmath as mp
import sympy as sp

x = sp.Symbol('x', real=True)
E, PI = sp.E, sp.pi
R = sp.Rational
ln = sp.log

# (номер, уровень, подынтегральная функция, нижний предел, верхний предел,
#  ответ — ровно тот, что выписан в материалах занятия)
ZADACHI = [
    # --- A. Формула Ньютона—Лейбница
    ("A1", 1, 4*x**3 - 6*x + 5, 1, 3, 66),
    ("A2", 1, 3*x**2 - 4*x + 1, 0, 2, 2),
    ("A3", 1, sp.sqrt(x) + 1/sp.sqrt(x), 1, 4, R(20, 3)),
    ("A4", 1, 3/x, 1, E, 3),
    ("A5", 1, 2*sp.sin(x) + sp.cos(x), 0, PI/3, 1 + sp.sqrt(3)/2),
    ("A6", 1, 1/sp.sin(x)**2, PI/6, PI/3, 2*sp.sqrt(3)/3),
    ("A7", 1, 1/(1 + x**2), 0, 1, PI/4),
    ("A8", 1, 1/sp.sqrt(1 - x**2), 0, R(1, 2), PI/6),
    ("A9", 1, x**2 - 3*x, -1, 2, R(-3, 2)),
    ("A10", 1, sp.exp(2*x), 0, ln(2), R(3, 2)),
    # --- B. Свойства
    ("B1", 2, x**5 - 3*x**3 + x, -2, 2, 0),
    ("B2", 2, x**4 + sp.Abs(x), -1, 1, R(7, 5)),
    ("B3", 2, sp.Abs(x - 2), 0, 3, R(5, 2)),
    ("B4", 3, sp.Abs(x**2 - x - 2), 0, 3, R(31, 6)),
    ("B6", 2, sp.Piecewise((3*x**2, x <= 1), (4 - x, True)), 0, 2, R(7, 2)),
    ("B8", 2, 1/(x + 2), 1, 4, ln(2)),
    # --- C. Замена переменной
    ("C1", 1, 1/(3*x + 1), 1, 2, ln(R(7, 4))/3),
    ("C2", 2, x*(x**2 + 3)**3, 0, 1, R(175, 8)),
    ("C3", 2, sp.sin(x)**3*sp.cos(x), 0, PI/2, R(1, 4)),
    ("C4", 2, sp.exp(x)/(1 + sp.exp(x)), 0, ln(3), ln(2)),
    ("C5", 3, x/sp.sqrt(x + 1), 0, 3, R(8, 3)),
    ("C6", 3, sp.sqrt(4 - x**2), 0, 2, PI),
    ("C7", 3, 1/(sp.sqrt(x)*(1 + sp.sqrt(x))), 1, 4, 2*ln(R(3, 2))),
    ("C8", 2, sp.tan(x), 0, PI/4, ln(2)/2),
    ("C9", 2, sp.cos(x)/(1 + sp.sin(x)**2), 0, PI/2, PI/4),
    # --- D. Интегрирование по частям
    ("D1", 2, x*sp.exp(2*x), 0, 1, (E**2 + 1)/4),
    ("D2", 2, x*sp.cos(x), 0, PI/2, PI/2 - 1),
    ("D3", 2, ln(x), 1, E, 1),
    ("D4", 2, x*ln(x), 1, 2, 2*ln(2) - R(3, 4)),
    ("D5", 3, sp.atan(x), 0, 1, PI/4 - ln(2)/2),
    ("D6", 3, sp.exp(x)*sp.sin(x), 0, PI, (E**PI + 1)/2),
    ("D7", 2, x**2*sp.exp(x), 0, 2, 2*E**2 - 2),
    ("D8", 3, ln(x)**2, 1, E, E - 2),
    # --- E. Повышенный уровень
    ("E1", 3, x**3*sp.exp(x**2), 0, 1, R(1, 2)),
    ("E2", 3, sp.cos(x)**2, 0, PI/2, PI/4),
    ("E3", 3, x**3*sp.cos(x) + sp.sin(x)**2, -PI/2, PI/2, PI/2),
    ("E4", 3, sp.sqrt(x)*ln(x), 1, 4, R(32, 3)*ln(2) - R(28, 9)),
    ("E5", 3, sp.sin(x)/(sp.sin(x) + sp.cos(x)), 0, PI/2, PI/4),
    ("E6", 3, sp.sqrt(sp.exp(x) - 1), 0, ln(2), 2 - PI/2),
    ("E7", 3, x*sp.atan(x), 0, 1, PI/4 - R(1, 2)),
    # --- F. Найди ошибку: проверяем ВЕРНЫЙ ответ, не тот, что в «решении»
    ("F1", 2, x*(x**2 + 1)**3, 0, 2, 78),
    ("F3", 2, 1/x, -2, -1, -ln(2)),
    ("F4", 1, sp.sin(x), 0, PI, 2),
    ("F5", 2, x*sp.sin(x), 0, PI, PI),
]


# точки излома: на них квадратуру надо разбивать, иначе модуль и
# кусочная функция интегрируются с ошибкой в третьем знаке
IZLOM = {"B2": [0], "B3": [2], "B4": [2], "B6": [1]}


def kvadratura(nom, f, a, b):
    """Независимая численная проверка — квадратура mpmath."""
    g = sp.lambdify(x, f, "mpmath")
    uzly = [a] + IZLOM.get(nom, []) + [b]
    return mp.quad(g, [mp.mpf(str(sp.N(u, 40))) for u in uzly])


def kachestvennye():
    """Задачи B5, B7, B8 — не на вычисление, но числа в них тоже сверяем."""
    print("\nкачественные задачи:")
    # B5: аддитивность по отрезку
    b5 = 2 - 7
    print(f"  B5: ∫(4..9) = ∫(1..9) − ∫(1..4) = 2 − 7 = {b5};"
          f"  ∫(9..4) = {-b5}")
    # B7: сравнение без вычисления
    i2 = sp.integrate(x**2, (x, 0, 1))
    i3 = sp.integrate(x**3, (x, 0, 1))
    print(f"  B7: ∫x² = {i2}, ∫x³ = {i3}, первый больше: {i2 > i3}")
    # B8: оценка m(b−a) ≤ I ≤ M(b−a) для убывающей 1/(x+2) на [1;4]
    f = 1/(x + 2)
    m, M = f.subs(x, 4), f.subs(x, 1)
    I = sp.integrate(f, (x, 1, 4))
    niz, verh = m*3, M*3
    print(f"  B8: {niz} ≤ {I} ≤ {verh} — "
          f"{'попало' if niz <= I <= verh else 'НЕ ПОПАЛО'}"
          f"  (численно {sp.N(niz, 6)} ≤ {sp.N(I, 6)} ≤ {sp.N(verh, 6)})")


def main():
    mp.mp.dps = 30
    print(f"{'№':4s} {'ур':>2s}  {'ответ в материалах':32s} "
          f"{'численно':>16s}  символьно  квадратура")
    bad = 0
    for nom, lvl, f, a, b, otv in ZADACHI:
        tochno = sp.integrate(f, (x, a, b))
        if tochno.has(sp.meijerg):
            # движок оставил G-функцию Мейера и свернуть её не может;
            # символьное сравнение зависло бы, сверяем 30 знаками
            simv = abs(sp.N(tochno, 30) - sp.N(otv, 30)) < sp.Float("1e-25")
        else:
            simv = sp.simplify(tochno - otv) == 0
        kv = abs(mp.mpf(str(sp.N(otv, 30)))
                 - kvadratura(nom, f, a, b)) < mp.mpf("1e-22")
        bad += not (simv and kv)
        print(f"{nom:4s} {lvl:2d}  {sp.sstr(otv):32s} {sp.N(otv, 12)!s:>16s}  "
              f"{'ок':^9s}  {'ок' if kv else 'РАСХОЖДЕНИЕ'}"
              if simv else
              f"{nom:4s} {lvl:2d}  {sp.sstr(otv):32s} {sp.N(otv, 12)!s:>16s}  "
              f"{'РАСХОЖДЕНИЕ':^9s}  {'ок' if kv else 'РАСХОЖДЕНИЕ'}")
    print(f"\nзадач с интегралом: {len(ZADACHI)}, расхождений: {bad}")
    kachestvennye()
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
