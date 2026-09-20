# -*- coding: utf-8 -*-
"""Описание пяти расчётных схем варианта 2 (строка 2 таблицы 1).

l = 6 м; h = 4 м; q = 1 кН/м; F = 20 кН; m = 10 кН·м.

Оси: x вправо, y вверх. Момент против часовой стрелки — положительный.
Направления нагрузок взяты по оригиналу методички с правками,
внесёнными вручную: схема 1 — m против часовой; схема 2 — m по часовой;
схема 3 — m по часовой; схема 4 — m против часовой и сила F направлена
влево; схема 5 — m по часовой.
"""
from rama import Sistema, F

l, h = 6, 4
q, P, m = 1, 20, 10


def shema1():
    s = Sistema("Схема 1")
    s.node('A', 0, 0).node('B', l, 0).node('C', l, -h) \
     .node('K', l, -2 * h).node('D', 2 * l, -h)
    s.member('AB', 'A', 'B').member('BC', 'B', 'C') \
     .member('CK', 'C', 'K').member('CD', 'C', 'D')
    s.dist('BC', -q, 0, label='q')            # горизонтальная, справа налево
    s.force('D', 0, P, 'F')                   # вверх
    s.moment('K', m, 'm')                     # против часовой
    s.support('A', 1, 0, 'R_Ax').support('A', 0, 1, 'R_Ay').support_m('A', 'M_A')
    s.W = "Д=1, Ш=0, С₀=3:  W = 3·1 − 0 − 3 = 0"
    return s


def shema2():
    s = Sistema("Схема 2")
    s.node('L', 0, 0).node('M', l, 0).node('S', l + l // 2, 0).node('E', 2 * l, 0) \
     .node('P', 0, -h // 2).node('LB', 0, -h).node('MB', l, -h)
    s.member('LM', 'L', 'M').member('MS', 'M', 'S').member('SE', 'S', 'E') \
     .member('LP', 'L', 'P').member('PB', 'P', 'LB').member('MMB', 'M', 'MB')
    s.dist('LM', 0, -q, label='q')            # вертикальная, вниз
    s.force('P', P, 0, 'F')                   # вправо
    s.moment('S', -m, 'm')                    # по часовой
    s.support('LB', 0, 1, 'R_1')              # вертикальный стержень
    s.support('MB', 1, 0, 'R_2')              # горизонтальный стержень
    s.support('E', 1, 0, 'R_3')               # горизонтальный стержень
    s.W = "Д=1, Ш=0, С₀=3:  W = 3·1 − 0 − 3 = 0"
    return s


def shema3():
    s = Sistema("Схема 3")
    s.node('K', 0, h).node('J', 0, 0).node('LB', 0, -h) \
     .node('R', l, 0).node('RB', l, -h)
    s.member('KJ', 'K', 'J').member('JLB', 'J', 'LB') \
     .member('JR', 'J', 'R').member('RRB', 'R', 'RB')
    s.force('K', P, 0, 'F')                   # вправо
    s.dist('JR', 0, -q, label='q')            # вниз по всему ригелю
    s.moment('R', -m, 'm')                    # по часовой
    s.support('LB', 0, 1, 'R_1v').support('LB', 1, 0, 'R_1h')
    s.support('RB', 0, 1, 'R_2v').support('RB', 1, 0, 'R_2h')
    s.hinge('J', ['KJ', 'JLB'])               # шарнир между стойкой и ригелем
    s.W = "Д=2, Ш=1, С₀=4:  W = 3·2 − 2·1 − 4 = 0"
    return s


def shema4():
    s = Sistema("Схема 4")
    s.node('S', 0, 0).node('K', l // 2, 0).node('C', l, 0) \
     .node('H', l, h).node('R', 2 * l, h).node('RB', 2 * l, 0)
    s.member('SK', 'S', 'K').member('KC', 'K', 'C').member('CH', 'C', 'H') \
     .member('HR', 'H', 'R').member('RRB', 'R', 'RB')
    s.force('C', -P, 0, 'F')                  # ВЛЕВО (правка)
    s.dist('RRB', -q, 0, label='q')           # горизонтальная, справа налево
    s.moment('R', m, 'm')                     # против часовой (правка)
    s.support('S', 0, 1, 'R_S')
    s.support('RB', 1, 0, 'R_Bx').support('RB', 0, 1, 'R_By').support_m('RB', 'M_B')
    s.hinge('H', ['SK', 'KC', 'CH'])
    s.W = "Д=2, Ш=1, С₀=4:  W = 3·2 − 2·1 − 4 = 0"
    return s


def shema5():
    s = Sistema("Схема 5")
    hl = l // 2
    xs = {'A': 0, 'H1': l, 'H2': 2 * l, 'B': 2 * l + hl,
          'P': 2 * l + 2 * hl, 'C': 2 * l + 3 * hl, 'E': 2 * l + 5 * hl}
    for n, x in xs.items():
        s.node(n, x, 0)
    s.member('AH1', 'A', 'H1').member('H1H2', 'H1', 'H2') \
     .member('H2B', 'H2', 'B').member('BP', 'B', 'P') \
     .member('PC', 'P', 'C').member('CE', 'C', 'E')
    s.dist('AH1', 0, -q, label='q')
    s.dist('H1H2', 0, -q, label='q')
    s.force('P', 0, -P, 'F')                  # вниз
    s.moment('E', -m, 'm')                    # по часовой
    s.support('A', 1, 0, 'R_Ax').support('A', 0, 1, 'R_Ay').support_m('A', 'M_A')
    s.support('B', 0, 1, 'R_B')
    s.support('C', 0, 1, 'R_C')
    s.hinge('H1', ['AH1'])
    s.hinge('H2', ['AH1', 'H1H2'])
    s.W = "Д=3, Ш=2, С₀=5:  W = 3·3 − 2·2 − 5 = 0"
    return s


ALL = [shema1, shema2, shema3, shema4, shema5]
