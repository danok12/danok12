# -*- coding: utf-8 -*-
"""Сверка с присланным решением: пересчёт ВСЕХ чисел пп. 1-6 задачи 1
и пп. 1-3 задачи 2, сравнение с тем, что написано в исходном документе.

Печатает таблицу «наше значение / в документе / расхождение».
"""
from fractions import Fraction as F
from decimal import Decimal, getcontext
import math

getcontext().prec = 50
OK, BAD = "совпало", "РАСХОЖДЕНИЕ"
problems = []


def cmp(name, ours, doc, tol=0.006, unit=""):
    """tol — допустимое относительное расхождение (округления в документе)."""
    o, d = float(ours), float(doc)
    if abs(d) > 1e-12:
        rel = abs(o - d) / abs(d)
    else:
        rel = abs(o - d)
    ok = rel <= tol
    if not ok:
        problems.append((name, o, d, rel))
    print(f"  {name:<34} {o:>14.5f} {d:>14.5f} {unit:<8} "
          f"{'' if ok else '<-- ' + BAD}")
    return ok


E = F(21, 10) * 10**5
nu = F(3, 10)
G = F(8, 10) * 10**5
R, gc = 210, F(9, 10)

print("=" * 86)
print("ЗАДАЧА 1. СВЕРКА С ПРИСЛАННЫМ РЕШЕНИЕМ")
print("=" * 86)
print(f"  {'величина':<34} {'пересчёт':>14} {'в документе':>14}")

sx, sy, sz = F(-80), F(60), F(-60)
txy, tyz, tzx = F(90), F(50), F(-65)

# --- п. 1-2. Инварианты ------------------------------------------------
print("\n-- п. 2. Инварианты ---------------------------------------------")
I1 = sx + sy + sz
I2 = sx*sy + sy*sz + sz*sx - txy**2 - tyz**2 - tzx**2
I3 = sx*sy*sz + 2*txy*tyz*tzx - sx*tyz**2 - sy*tzx**2 - sz*txy**2
cmp("I1н, МПа", I1, -80)
cmp("I2н, МПа²", I2, -18425)
cmp("I3н, МПа³", I3, 135500)

# таблица подбора корня
print("\n-- п. 2. Таблица 2 (подбор корня) -------------------------------")
f = lambda s: s**3 + 80*s**2 - 18425*s - 135500
for s_, doc in ((0, -135500), (50, -731750), (100, -178000),
                (105, -30500), (106, 1346), (110, 136750)):
    cmp(f"f({s_})", f(F(s_)), doc, tol=1e-9)

# --- корни -------------------------------------------------------------
def newton(s0):
    s = Decimal(s0)
    for _ in range(200):
        d = 3*s**2 - 2*Decimal(int(I1))*s + Decimal(int(I2))
        sn = s - (s**3 - Decimal(int(I1))*s**2 + Decimal(int(I2))*s
                  - Decimal(int(I3))) / d
        if abs(sn - s) < Decimal("1e-40"):
            return sn
        s = sn
    return s

s1, s2, s3 = newton("106"), newton("-7"), newton("-179")
print("\n-- п. 2. Главные напряжения -------------------------------------")
cmp("σ1, МПа", s1, 105.96)
cmp("σ2, МПа", s2, -7.15)
cmp("σ3, МПа", s3, -178.81)
print(f"  {'проверка Виета: Σσi':<34} {float(s1+s2+s3):>14.5f} "
      f"{float(I1):>14.5f}")
print(f"  {'проверка Виета: Πσi':<34} {float(s1*s2*s3):>14.5f} "
      f"{float(I3):>14.5f}")

# --- п. 3. Направляющие косинусы --------------------------------------
print("\n-- п. 3. Направляющие косинусы и углы ---------------------------")
doc_cos = {1: (0.3990, 0.9094, 0.1177), 2: (0.5582, -0.1390, -0.8180),
           3: (0.7275, -0.3921, 0.5630)}
doc_ang = {1: (66.49, 24.58, 83.24), 2: (56.07, 97.99, 144.89),
           3: (43.32, 113.08, 55.73)}
cosines = {}
fx, fy, fz = float(sx), float(sy), float(txy)
for i, si in ((1, s1), (2, s2), (3, s3)):
    s_ = float(si)
    D  = (fx - s_) * (fy - s_) - float(txy)**2
    D1 = -(fy - s_) * float(tzx) + float(txy) * float(tyz)
    D2 = -(fx - s_) * float(tyz) + float(txy) * float(tzx)
    Di = math.sqrt(D1*D1 + D2*D2 + D*D)
    l, m, n = D1/Di, D2/Di, D/Di
    cosines[i] = (l, m, n)
    for lbl, v, d in (("l", l, doc_cos[i][0]), ("m", m, doc_cos[i][1]),
                      ("n", n, doc_cos[i][2])):
        cmp(f"{lbl}{i}", v, d, tol=0.004)
    for lbl, v, d in (("(ν,x)", math.degrees(math.acos(l)), doc_ang[i][0]),
                      ("(ν,y)", math.degrees(math.acos(m)), doc_ang[i][1]),
                      ("(ν,z)", math.degrees(math.acos(n)), doc_ang[i][2])):
        cmp(f"∠{lbl} для ν{i}, град", v, d, tol=0.004)

print("\n-- п. 3. Ортогональность нормалей -------------------------------")
for a, b in ((1, 2), (2, 3), (3, 1)):
    d = sum(cosines[a][k] * cosines[b][k] for k in range(3))
    print(f"  ν{a}·ν{b} = {d:+.8f}   (должно быть 0)")
    if abs(d) > 1e-6:
        problems.append((f"ортогональность ν{a}·ν{b}", d, 0.0, abs(d)))
for i in (1, 2, 3):
    nrm = sum(c*c for c in cosines[i])
    print(f"  |ν{i}|² = {nrm:.8f}   (должно быть 1)")

# --- п. 5. Экстремальные касательные ----------------------------------
print("\n-- п. 5. Экстремальные касательные и нормальные -----------------")
t12 = -(s1 - s2) / 2
t23 = -(s2 - s3) / 2
t31 = -(s3 - s1) / 2
cmp("τ12, МПа", t12, -56.56)
cmp("τ23, МПа", t23, -85.83)
cmp("τ31, МПа", t31, 142.38)
cmp("σ12, МПа", (s1 + s2) / 2, 49.40)
cmp("σ23, МПа", (s2 + s3) / 2, -92.98)
cmp("σ31, МПа", (s1 + s3) / 2, -36.42)

# --- п. 6. Деформации --------------------------------------------------
print("\n-- п. 6а. Линейные деформации (×10⁻⁵) ---------------------------")
ex = (sx - nu * (sy + sz)) / E
ey = (sy - nu * (sz + sx)) / E
ez = (sz - nu * (sx + sy)) / E
cmp("εx ×10⁻⁵", ex * 10**5, -38.10)
cmp("εy ×10⁻⁵", ey * 10**5, 48.57)
cmp("εz ×10⁻⁵", ez * 10**5, -25.71)
theta = ex + ey + ez
cmp("θ ×10⁻⁵", theta * 10**5, -15.24)
print(f"  контроль θ = (1-2ν)/E·I1н = {float((1-2*nu)/E*I1*10**5):.5f} ×10⁻⁵")

print("\n-- п. 6б. Угловые деформации (×10⁻⁵) ----------------------------")
gxy, gyz, gzx = txy / G, tyz / G, tzx / G
cmp("γxy ×10⁻⁵", gxy * 10**5, 112.50)
cmp("γyz ×10⁻⁵", gyz * 10**5, 62.50)
cmp("γzx ×10⁻⁵", gzx * 10**5, -81.25)
print("  знак «+» — прямой угол уменьшился, «−» — увеличился:")
for nm, g in (("γxy", gxy), ("γyz", gyz), ("γzx", gzx)):
    print(f"    {nm} = {float(g)*10**5:+.2f}·10⁻⁵ -> угол "
          f"{'уменьшился' if g > 0 else 'увеличился'} "
          f"на {abs(math.degrees(float(g)))*3600:.1f}″")

# --- п. 7-8 ------------------------------------------------------------
print("\n-- п. 7. Удельная энергия ---------------------------------------")
U0 = (I1**2 - 2*I2 - 2*nu*I2) / (2*E)
S = 2 * (I1**2 - 3*I2)
U0f = (1 + nu) / (6*E) * S
U0v = (1 - 2*nu) / (6*E) * I1**2
u_lin = (sx**2+sy**2+sz**2 - 2*nu*(sx*sy+sy*sz+sz*sx)) / (2*E)
u_sh = (txy**2+tyz**2+tzx**2) / (2*G)
print(f"  через главные напряжения (формула тетради): U0  = {float(U0):.5f} МПа")
print(f"  через σx..τzx при G = 0,8·10⁵ (как в документе): {float(u_lin+u_sh):.5f} МПа"
      f"   <- в документе 0,13018")
cmp("  слагаемое 1/(2E)[...]", u_lin, 0.03752, tol=0.002)
cmp("  слагаемое 1/(2G)(...)", u_sh, 0.09266, tol=0.002)
Gt = E / (2 * (1 + nu))
print(f"  через σx..τzx при G = E/[2(1+ν)] = {float(Gt):.1f}: "
      f"{float(u_lin + (txy**2+tyz**2+tzx**2)/(2*Gt)):.5f} МПа  "
      f"-> совпадает с формулой тетради")
print(f"  U0ф по формуле тетради            = {float(U0f):.5f} МПа")
print(f"  U0ф вычитанием, как в документе   = {float(u_lin+u_sh-U0v):.5f} МПа"
      f"   <- в документе 0,12815")
print(f"  U0об                               = {float(U0v):.5f} МПа"
      f"   <- в документе 0,00203")

print("\n-- п. 8. Прочность ----------------------------------------------")
sekv = (Decimal(int(I1**2 - 3*I2))).sqrt()
cmp("σэкв, МПа", sekv, 248.34)
cmp("γc·R, МПа", gc * R, 189.0)
print(f"  превышение: {(float(sekv)/float(gc*R) - 1)*100:.1f} %  <- в документе 31,4 %")

# ======================================================================
print()
print("=" * 86)
print("ЗАДАЧА 2. СВЕРКА")
print("=" * 86)
sx2, sy2, txy2 = F(-85), F(-30), F(-30)
J1, J2 = sx2 + sy2, sx2*sy2 - txy2**2
cmp("I1н, МПа", J1, -115)
cmp("I2н, МПа²", J2, 1650)
half = float(J1) / 2
rad = math.sqrt(float(((sx2-sy2)/2)**2 + txy2**2))
cmp("(σx+σy)/2, МПа", half, -57.5)
cmp("√[((σx-σy)/2)²+τ²], МПа", rad, 40.70)
cmp("σmax(в плоскости), МПа", half + rad, -16.80)
cmp("σmin, МПа", half - rad, -98.20)
cmp("τmax(в плоскости) = (σ2-σ3)/2", rad, 40.70)
cmp("τmax(пространств.) = (σ1-σ3)/2", (0 - (half - rad)) / 2, 49.10)
a2 = math.degrees(math.atan(float(txy2) / (float(sy2) - (half + rad))))
a3 = math.degrees(math.atan(float(txy2) / (float(sy2) - (half - rad))))
cmp("α2 (ось y вниз), град", a2, 66.26)
cmp("α3 (ось y вниз), град", a3, -23.74)
cmp("|α2|+|α3|, град", abs(a2) + abs(a3), 90.0)
a0 = math.degrees(math.atan(2*float(txy2) / float(sx2 - sy2))) / 2
cmp("α0 (ось y вверх), град", a0, 23.74)

print()
print("=" * 86)
if problems:
    print("НАЙДЕНЫ РАСХОЖДЕНИЯ:")
    for n, o, d, r in problems:
        print(f"  {n}: пересчёт {o:.5f}, в документе {d:.5f}, "
              f"относительно {r*100:.2f} %")
else:
    print("ВСЕ ЧИСЛА СОШЛИСЬ с присланным решением (в пределах округления).")
print("=" * 86)
