# -*- coding: utf-8 -*-
"""Независимая перепроверка решения — другими способами, чем в raschet.py.

Ничего не берётся из raschet.py: тензор строится заново, главные напряжения
считаются как собственные числа, напряжения на наклонных площадках — прямым
преобразованием T·ν, энергия — свёрткой ½·σij·εij, эквивалентное напряжение —
через девиатор. Отдельно проверяется геометрия рисунков 4 и 7 (круг Мора — по координатам
точек, снятым с чертежа в его масштабе).
"""
import math
import re

SX, SY, TXY = -85.0, -30.0, -30.0
E, NU = 2.1e5, 0.3
G_ZAD = 0.8e5
G_TOCH = E / (2 * (1 + NU))
R_RASCH, GAMMA_C = 210.0, 0.9

T = [[SX, TXY, 0.0], [TXY, SY, 0.0], [0.0, 0.0, 0.0]]
ok_all = True


def check(name, a, b, tol=5e-4, unit=""):
    global ok_all
    good = abs(a - b) <= tol
    ok_all &= good
    print(f"  {'ок ' if good else 'НЕТ'} {name:52s} {a:12.6f} | {b:12.6f} {unit}")
    return good


def mv(M, v):
    return [sum(M[i][j] * v[j] for j in range(3)) for i in range(3)]


def dot(a, b):
    return sum(p * q for p, q in zip(a, b))


print("=" * 84)
print("НЕЗАВИСИМАЯ ПЕРЕПРОВЕРКА РЕШЕНИЯ")
print("=" * 84)

# --- главные напряжения как собственные числа (характеристический многочлен) ---
I1 = SX + SY
I2 = SX * SY - TXY**2
r = math.sqrt(((SX - SY) / 2)**2 + TXY**2)
pl_max, pl_min = (SX + SY) / 2 + r, (SX + SY) / 2 - r
# нумерация конспекта: σ1, σ2 — в плоскости пластины, σ3 = 0
s1, s2, s3 = pl_max, pl_min, 0.0
print("\nглавные напряжения (через собственные числа тензора):")
for nm, v in (("σ1", s1), ("σ2", s2), ("σ3", s3)):
    print(f"    {nm} = {v:.4f} МПа")
print("  контроль: каждое обращает det(T − σE) в нуль")
for nm, v in (("σ1", s1), ("σ2", s2), ("σ3", s3)):
    d = (-v)**3 - I1 * (-v)**2 * 0 + 0   # считаем det напрямую ниже
    det = ((SX - v) * (SY - v) - TXY**2) * (0.0 - v)
    check(f"det(T − {nm}·E)", det, 0.0, 1e-6)

# --- п. 4 ---------------------------------------------------------------
print("\nп. 4. экстремальные касательные напряжения")
check("τ12 = (σ1−σ2)/2", (s1 - s2) / 2, 40.6971, 1e-3, "МПа")
check("τ23 = (σ2−σ3)/2 = τmax", abs((s2 - s3) / 2), 49.0985, 1e-3, "МПа")
check("τ31 = (σ3−σ1)/2", abs((s3 - s1) / 2), 8.4015, 1e-3, "МПа")
check("σ' на площадках 1-2", (s1 + s2) / 2, -57.5, 1e-3, "МПа")
check("τ12 = радиус круга Мора", (s1 - s2) / 2, r, 1e-9, "МПа")

# --- п. 5: напряжения на наклонной площадке прямым преобразованием -------
print("\nп. 5. площадки под α = 15°: прямое преобразование T·ν")
al = math.radians(15)
nu_ = [math.cos(al), -math.sin(al), 0.0]      # ось y на чертеже вниз
t_ = [math.sin(al), math.cos(al), 0.0]
p_nu = mv(T, nu_)
check("σν = ν·T·ν", dot(nu_, p_nu), -66.3157, 1e-3, "МПа")
check("τtν = t·T·ν", dot(t_, p_nu), -39.7308, 1e-3, "МПа")
check("σt = t·T·t", dot(t_, mv(T, t_)), -48.6843, 1e-3, "МПа")
check("ν·t = 0 (площадки перпендикулярны)", dot(nu_, t_), 0.0, 1e-12)
check("инвариант σν + σt", dot(nu_, p_nu) + dot(t_, mv(T, t_)), I1, 1e-6, "МПа")
check("инвариант σν·σt − τtν²",
      dot(nu_, p_nu) * dot(t_, mv(T, t_)) - dot(t_, p_nu)**2, I2, 1e-6, "МПа²")

# --- п. 6: деформации ----------------------------------------------------
print("\nп. 6. деформации")
ex = (SX - NU * SY) / E
ey = (SY - NU * SX) / E
ez = -NU * (SX + SY) / E
check("εx·10⁵", ex * 1e5, -36.1905, 1e-3)
check("εy·10⁵", ey * 1e5, -2.1429, 1e-3)
check("εz·10⁵", ez * 1e5, 16.4286, 1e-3)
check("θ·10⁵ = εx+εy+εz", (ex + ey + ez) * 1e5, -21.9048, 1e-3)
check("θ·10⁵ = (1−2ν)/E·I1", (1 - 2 * NU) / E * I1 * 1e5, -21.9048, 1e-3)
check("γxy·10⁵ при G = 0,8·10⁵", TXY / G_ZAD * 1e5, -37.5, 1e-3)

# --- п. 7: энергия свёрткой ½σij·εij -------------------------------------
print("\nп. 7. энергия")
U0_f = (1 / (2 * E)) * (s1**2 + s2**2 + s3**2
                        - 2 * NU * (s1 * s2 + s2 * s3 + s3 * s1))
g_xy = TXY / G_TOCH                      # для свёртки нужен согласованный G
U0_conv = 0.5 * (SX * ex + SY * ey + 0.0 * ez + TXY * g_xy)
check("U₀ по формуле через σi", U0_f, 0.021274, 1e-5, "МПа")
check("U₀ свёрткой ½σij·εij", U0_conv, U0_f, 1e-9, "МПа")
Uf = (1 + NU) / (6 * E) * ((s1 - s2)**2 + (s2 - s3)**2 + (s3 - s1)**2)
Uo = (1 - 2 * NU) / (6 * E) * I1**2
check("U₀^ф", Uf, 0.017075, 1e-5, "МПа")
check("U₀^об", Uo, 0.004198, 1e-5, "МПа")
check("U₀^ф + U₀^об = U₀", Uf + Uo, U0_f, 1e-12, "МПа")
check("доля формоизменения, %", Uf / U0_f * 100, 80.26, 1e-2)

# --- п. 8: σ_экв через девиатор ------------------------------------------
print("\nп. 8. эквивалентное напряжение")
sm = I1 / 3
dev = [[T[i][j] - (sm if i == j else 0.0) for j in range(3)] for i in range(3)]
J2d = 0.5 * sum(dev[i][j]**2 for i in range(3) for j in range(3))
check("σ_экв = √(3·J2 девиатора)", math.sqrt(3 * J2d), 90.9670, 1e-3, "МПа")
check("σ_экв = √(I1² − 3I2)", math.sqrt(I1**2 - 3 * I2), 90.9670, 1e-3, "МПа")
check("U₀^ф = ((1+ν)/3E)·σ_экв²", (1 + NU) / (3 * E) * (I1**2 - 3 * I2),
      Uf, 1e-12, "МПа")
pred = R_RASCH * GAMMA_C
print(f"  условие: 90,97 ≤ {pred:.1f} МПа — "
      f"{'выполняется' if math.sqrt(I1**2 - 3*I2) <= pred else 'НЕ ВЫПОЛНЯЕТСЯ'};"
      f" запас {pred / math.sqrt(I1**2 - 3*I2):.3f}")

# --- п. 9: круг Мора -----------------------------------------------------
print("\nп. 9. круг Мора: все точки обязаны лежать на окружности")
OC = (SX + SY) / 2
for nm, (sv, tv) in (("D(σx; −τxy)", (SX, -TXY)), ("K(σy; τxy)", (SY, TXY)),
                     ("площадка α=15° (σν; τtν)", (-66.3157, -39.7308)),
                     ("σ1", (s1, 0.0)), ("σ2", (s2, 0.0))):
    check(f"{nm}: (σ−OC)² + τ²  = R²", (sv - OC)**2 + tv**2, r**2, 5e-2, "МПа²")
check("OC + R = σ1", OC + r, s1, 1e-6, "МПа")
check("OC − R = σ2", OC - r, s2, 1e-6, "МПа")

# --- правило полюса (как в конспекте) ---
# Полюс K(σy; τxy). Для площадки с нормалью под α к оси x точка круга —
# (σα; τα) из прямого преобразования T·ν; проверяем, что отрезок K→точка
# наклонён к оси σ ровно под α (по модулю 180°).
print("\nправило полюса: прямая из K(σy; τxy) на точку площадки наклонена под α")
KP = (SY, TXY)


def tochka_ploshchadki(al_deg):
    a = math.radians(al_deg)
    nu_ = [math.cos(a), -math.sin(a), 0.0]           # ось y вниз, как в тетради
    t_ = [math.sin(a), math.cos(a), 0.0]
    pp = mv(T, nu_)
    return dot(nu_, pp), dot(t_, pp)


for al_deg, nm in ((15.0, "P, α = 15°"), (66.255224, "σ1, α1"),
                   (-23.744776, "σ2, α2"), (105.0, "P′, α = 105°")):
    sg_, tg_ = tochka_ploshchadki(al_deg)
    naklon = math.degrees(math.atan2(tg_ - KP[1], sg_ - KP[0]))
    d = (naklon - al_deg) % 180
    d = d - 180 if d > 90 else d
    check(f"{nm}: наклон K→({sg_:.2f}; {tg_:.2f}) − α", d, 0.0, 1e-6, "°")
check("α=15°: σ точки = σν из п. 5", tochka_ploshchadki(15)[0], -66.3157, 1e-4, "МПа")
check("α=15°: τ точки = τtν из п. 5", tochka_ploshchadki(15)[1], -39.7308, 1e-4, "МПа")
check("α=105°: σ точки = σt из п. 5", tochka_ploshchadki(105)[0], -48.6843, 1e-4, "МПа")
check("K на круге: (σy−OC)² + τxy² = R²", (SY - OC)**2 + TXY**2, r**2, 1e-9, "МПа²")

# --- геометрия рисунков ---------------------------------------------------
print("\nгеометрия рисунков")
a_tau = 66.26 - 45
alr = math.radians(a_tau)
n_t = [math.cos(alr), -math.sin(alr), 0.0]
t_t = [math.sin(alr), math.cos(alr), 0.0]
p = mv(T, n_t)
check("рис. 4: σ на грани элемента (α=21,26°)", dot(n_t, p), -57.5, 2e-2, "МПа")
check("рис. 4: |τ| на грани элемента", abs(dot(t_t, p)), 40.6971, 2e-2, "МПа")

# рис. 7 — круг Мора: координаты точек снимаются с чертежа по его масштабу
svg = open("fig-7.svg", encoding="utf-8").read()
mm_na_ed = 0.187
for m in re.finditer(r'<g data-panel="(.)" data-ox="([-\d.]+)" data-oy="([-\d.]+)" '
                     r'data-k="([\d.]+)">(.*?)</g>', svg, re.S):
    bukva, ox7, oy7, k7, body = m.group(1), *map(float, m.group(2, 3, 4)), m.group(5)
    check("рис. 7: масштаб, мм на 1 МПа (1 см = 10 МПа)", k7 * mm_na_ed, 1.0, 1e-4, "мм")
    rr = [float(c) for c in re.findall(r'class="plane-edge"', body) and
          re.findall(r'<circle cx="[-\d.]+" cy="[-\d.]+" r="([\d.]+)" class="plane-edge"', body)]
    check(f"рис. 7: радиус круга -> МПа", rr[0] / k7, r, 2e-3, "МПа")
    pts = {nm: ((float(x) - ox7) / k7, (oy7 - float(y)) / k7) for nm, x, y in
           re.findall(r'data-pt="([^"]+)" cx="([-\d.]+)" cy="([-\d.]+)"', body)}
    want = {"O": (0, 0), "D": (SX, 0), "B": (SY, 0), "C": (OC, 0), "K": KP,
            "σ1": (s1, 0), "σ2": (s2, 0), "T1": (OC, r), "T2": (OC, -r),
            "X": (SX, TXY), "P": tochka_ploshchadki(15), "P'": tochka_ploshchadki(105)}
    for nm, (ws, wt) in want.items():
        if nm in pts:
            check(f"рис. 7: точка {nm}, σ", pts[nm][0], ws, 1e-2, "МПа")
            check(f"рис. 7: точка {nm}, τ", pts[nm][1], wt, 1e-2, "МПа")


print("\n" + "=" * 84)
print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if ok_all else "ЕСТЬ РАСХОЖДЕНИЯ — см. строки «НЕТ»")
print("=" * 84)
