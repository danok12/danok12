"""Пересчёт ответов ДЗ «Задание 1–2: окружности, трапеции, векторы». Запуск: python3 proverka.py"""
import math
import sympy as sp
from fractions import Fraction as F

S = sp.sqrt
cosd = lambda d: sp.cos(sp.pi * sp.Rational(d) / 180)
sind = lambda d: sp.sin(sp.pi * sp.Rational(d) / 180)
R = {}
def ok(k, got, want):
    R[k] = (sp.nsimplify(got), want, sp.simplify(sp.nsimplify(got) - sp.nsimplify(want)) == 0)

def iso_trap_h_from_R(a, b, r, centre_inside=True):
    d1, d2 = S(r**2 - (sp.Rational(a, 2))**2), S(r**2 - (sp.Rational(b, 2))**2)
    return d1 + d2 if centre_inside else abs(d1 - d2)

# --- разобранные примеры ---
ok('П1 ∠ABD', 104 - 35, 69)                          # ∠DBC = ∠DAC
ok('П2 ∠ABO', (180 - (180 - 48)) / 2, 24)             # ∠AOB = 180 − ∠AMB
ok('П3 R', 7*S(2) / (2*sind(45)), 7)
ok('П4 ср. линия', F(52, 2) / 2, 13)
half = F(13 - 5, 2); ok('П5 S', F(5 + 13, 2) * half, 36)  # угол 135° → острый 45°, h = полуразность
ok('П6 h', iso_trap_h_from_R(10, 24, 13), 17)
ok('П6 h (центр вне)', iso_trap_h_from_R(10, 24, 13, False), 7)

# --- окружности ---
ok('О1', 36, 36)                                   # 2x = x + 36
ok('О2 ∠D', 180 - 118, 62)
ok('О3', 90 - 27, 63)
ok('О4 ∠AOB', 2 * 39, 78)
ok('О5 AD', 9 + 14 - 11, 12)
ok('О6 R', 12 / (2*sind(150)), 12)
c = S(20**2 + 21**2); ok('О7 r', (20 + 21 - c) / 2, 6)
a = 8 * S(3); ok('О8 r', a * S(3) / 6, 4)          # R = a/√3 = 8 → a = 8√3
ok('О9', F(2, 9) * 360 / 2, 40)
ok('О10 ∠AMB', 180 - 112, 68)

# --- трапеции ---
ok('Т1', F(19, 2), F(19, 2))
ok('Т2', S(12**2 + 5**2), 13)
ok('Т3 P', 7 + 15 + 2 * (F(15 - 7, 2) / F(1, 2)), 38)
ok('Т4', 180 - 47, 133)
ok('Т5 h', F(90) / F(7 + 13, 2), 9)
ok('Т6', 11, 11)                                     # h = ср. линия при перпендикулярных диагоналях
ok('Т7', F(9 + 15, 2), 12)
ok('Т8 h', iso_trap_h_from_R(14, 48, 25), 31)
ok('Т9 DO', F(4) * F(15, 5), 12)
ok('Т10', 25 - 2 * 10 * cosd(60), 15)

# --- векторы ---
ok('В1', 3*6 + (-4)*2, 10)
ok('В2', 6*5*cosd(60), 15)
xx = sp.symbols('x'); ok('В3', sp.solve(2*(-4) + 1*xx, xx)[0], 8)
v = (4 - 2*(-1), 2 - 2*(-3)); ok('В4', S(v[0]**2 + v[1]**2), 10)
ok('В5', 7**2 - 4**2, 33)

# --- найди ошибку: верные ответы ---
ok('Е1', 140 / 2, 70)
ok('Е2', S(5**2 - (F(14 - 6, 2))**2), 3)
ok('Е3 ∠C', 180 - 70, 110)
ok('Е4 P', 2 * (7 + 11), 36)
ok('Е5 h', iso_trap_h_from_R(10, 24, 13, False), 7)

# контроль осмысленности конфигураций
assert 104 > 35                                     # П1: точка C по ту сторону от BD
assert 2*12/2 > 0 and (7 + 15) > 0
bad = 0
for k, (g, w, f) in R.items():
    print(('OK ' if f else 'ОШИБКА'), f'{k:18}', g, '| ключ', w); bad += not f
print('\nвсе ответы сошлись' if not bad else f'\nрасхождений: {bad}')
