"""Проверка расчётной среды: каждая библиотека решает задачу с известным ответом.

Запуск: python3 tools/proverka_sredy.py
"""
import math

import numpy as np
import sympy as sp


def balka_anastruct():
    # Шарнирная балка l = 6 м, q = 10 кН/м: Mmax = ql²/8 = 45, f = 5ql⁴/(384EI)
    from anastruct import SystemElements

    q, l, EI = 10, 6, 1e4
    s = SystemElements(EI=EI, mesh=200)
    s.add_element([[0, 0], [l / 2, 0]])
    s.add_element([[l / 2, 0], [l, 0]])
    s.add_support_hinged(1)
    s.add_support_roll(3)
    s.q_load(q=-q, element_id=[1, 2])
    s.solve()
    m = max(abs(v) for v in s.get_element_result_range("moment"))
    f = abs(s.get_node_displacements(2)["uy"])
    return [("anastruct: Mmax балки", m, q * l**2 / 8),
            ("anastruct: прогиб в середине", f, 5 * q * l**4 / (384 * EI))]


def balka_pynite():
    # Консоль l = 2 м, сила P = 5 кН на конце: прогиб Pl³/(3EI)
    from Pynite import FEModel3D

    P, l, E, Iz = 5.0, 2.0, 2e8, 1e-5
    m = FEModel3D()
    m.add_material("st", E=E, G=8e7, nu=0.3, rho=0)
    m.add_section("sec", A=1e-3, Iy=1e-5, Iz=Iz, J=2e-5)
    m.add_node("A", 0, 0, 0)
    m.add_node("B", l, 0, 0)
    m.add_member("AB", "A", "B", "st", "sec")
    m.def_support("A", True, True, True, True, True, True)
    m.add_node_load("B", "FY", -P)
    m.analyze(check_statics=False)
    return [("PyNite: прогиб консоли", abs(m.nodes["B"].DY["Combo 1"]),
             P * l**3 / (3 * E * Iz))]


def sechenie():
    # Прямоугольник 100×200 мм: Ix = bh³/12
    from sectionproperties.analysis import Section
    from sectionproperties.pre.library import rectangular_section

    b, h = 100, 200
    geom = rectangular_section(d=h, b=b)
    geom.create_mesh(mesh_sizes=[500])
    sec = Section(geometry=geom)
    sec.calculate_geometric_properties()
    ixx = sec.get_ic()[0]
    return [("sectionproperties: Ix прямоугольника", ixx, b * h**3 / 12)]


def glavnye_napryazheniya():
    # Плоское напряжённое состояние σx = 80, σy = −20, τ = 30 МПа
    sx, sy, t = 80, -20, 30
    s1 = (sx + sy) / 2 + math.hypot((sx - sy) / 2, t)
    s3 = (sx + sy) / 2 - math.hypot((sx - sy) / 2, t)
    lam = np.linalg.eigvalsh(np.array([[sx, t], [t, sy]]))
    return [("numpy: σ1", lam.max(), s1), ("numpy: σ3", lam.min(), s3)]


def izognutaya_os():
    # EI·v'' = −M(x), ось v вниз, для той же балки: прогиб в середине 5ql⁴/(384EI)
    x, q, l, EI = sp.symbols("x q l EI", positive=True)
    C1, C2 = sp.symbols("C1 C2")
    M = q * l * x / 2 - q * x**2 / 2
    v = sp.integrate(sp.integrate(-M, x) + C1, x) + C2
    sol = sp.solve([v.subs(x, 0), v.subs(x, l)], [C1, C2])
    f = sp.simplify(v.subs(sol).subs(x, l / 2) / EI)
    return [("sympy: прогиб в общем виде", float(f.subs({q: 10, l: 6, EI: 1e4})),
             5 * 10 * 6**4 / (384 * 1e4))]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import pandas, openpyxl, scipy  # noqa: F401  проверка импорта

    rows = []
    for check in (balka_anastruct, balka_pynite, sechenie, glavnye_napryazheniya, izognutaya_os):
        rows += check()

    bad = 0
    for name, got, want in rows:
        ok = math.isclose(got, want, rel_tol=1e-3)
        bad += not ok
        print(f"{'OK ' if ok else 'ОШИБКА'} {name}: {round(got, 6)} (ожидается {round(want, 6)})")
    print("Среда готова." if not bad else f"Расхождений: {bad}")
    raise SystemExit(bad)


if __name__ == "__main__":
    main()
