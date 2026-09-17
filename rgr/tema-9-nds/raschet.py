# -*- coding: utf-8 -*-
"""РГР 9. Проверочный расчёт: задача 1 (пп. 7-8) и задача 2 (пп. 1-3).

Точная арифметика через Fraction везде, где это возможно.
Инварианты и подкоренные выражения считаются как рациональные числа,
корни извлекаются только на последнем шаге.
"""
from fractions import Fraction as F
from decimal import Decimal, getcontext
import math

getcontext().prec = 50


def r(x, n=4):
    """Округление до n знаков (round, а не усечение)."""
    return round(float(x), n)


def sqrt_hp(x):
    """Корень с запасом точности (Decimal, 50 знаков)."""
    return Decimal(F(x).numerator).sqrt() / Decimal(F(x).denominator).sqrt()


print("=" * 72)
print("ИСХОДНЫЕ ДАННЫЕ, общие для обеих задач")
print("=" * 72)
E = F(21, 10) * 10**5          # МПа
nu = F(3, 10)
G_zad = F(8, 10) * 10**5       # МПа, из задания (округлено)
G_tochn = E / (2 * (1 + nu))   # МПа, согласованное с E и nu
R = 210                        # МПа
gamma_c = F(9, 10)
print(f"E = {float(E):.6g} МПа;  nu = {float(nu)};  R = {R} МПа;  gamma_c = {float(gamma_c)}")
print(f"G (задание)  = {float(G_zad):.6g} МПа")
print(f"G = E/[2(1+nu)] = {float(G_tochn):.6f} МПа   -> расхождение "
      f"{float((G_tochn - G_zad) / G_zad * 100):.2f} %")

# ======================================================================
# ЗАДАЧА 1. Трёхосное напряжённое состояние
# ======================================================================
print()
print("=" * 72)
print("ЗАДАЧА 1. Строка 14: sx, sy, txy;  строка 11: sz, tyz, tzx")
print("=" * 72)
sx, sy, sz = F(-80), F(60), F(-60)
txy, tyz, tzx = F(90), F(50), F(-65)

I1 = sx + sy + sz
I2 = sx * sy + sy * sz + sz * sx - txy**2 - tyz**2 - tzx**2
I3 = (sx * sy * sz + 2 * txy * tyz * tzx
      - sx * tyz**2 - sy * tzx**2 - sz * txy**2)
print(f"I1н = {I1} МПа;  I2н = {I2} МПа²;  I3н = {I3} МПа³")
assert (I1, I2, I3) == (-80, -18425, 135500), "инварианты разошлись с текстом РГР"

# --- главные напряжения: корни sigma^3 - I1 s^2 + I2 s - I3 = 0 -------
def f_cubic(s):
    s = Decimal(s)
    return s**3 - Decimal(int(I1)) * s**2 + Decimal(int(I2)) * s - Decimal(int(I3))

def newton(s0):
    s = Decimal(s0)
    for _ in range(200):
        fs = f_cubic(s)
        d = 3 * s**2 - 2 * Decimal(int(I1)) * s + Decimal(int(I2))
        s_new = s - fs / d
        if abs(s_new - s) < Decimal("1e-40"):
            return s_new
        s = s_new
    return s

s1 = newton("106")
s2 = newton("-7")
s3 = newton("-179")
print(f"sigma1 = {s1:.6f} МПа")
print(f"sigma2 = {s2:.6f} МПа")
print(f"sigma3 = {s3:.6f} МПа")
print(f"проверка сумм:      {s1 + s2 + s3:.9f}  (I1н = {I1})")
print(f"проверка произвед.: {s1 * s2 * s3:.6f}  (I3н = {I3})")

# --- п. 7. Удельная потенциальная энергия деформации ------------------
print()
print("-" * 72)
print("п. 7. УДЕЛЬНАЯ ПОТЕНЦИАЛЬНАЯ ЭНЕРГИЯ УПРУГОЙ ДЕФОРМАЦИИ")
print("-" * 72)
# Через главные напряжения (формула тетради), но без потери точности:
#   s1^2+s2^2+s3^2          = I1^2 - 2*I2
#   s1*s2 + s2*s3 + s3*s1   = I2
sum_sq = I1**2 - 2 * I2
sum_pair = I2
print(f"sigma1²+sigma2²+sigma3² = I1н² - 2·I2н = {I1}² - 2·({I2}) = {sum_sq} МПа²")
print(f"sigma1σ2+σ2σ3+σ3σ1      = I2н                = {sum_pair} МПа²")

U0 = (sum_sq - 2 * nu * sum_pair) / (2 * E)          # полная, точно
print(f"U0 (полная)  = [{sum_sq} - 2·{float(nu)}·({sum_pair})] / (2·{float(E):.6g}) "
      f"= {sum_sq - 2 * nu * sum_pair} / {float(2 * E):.6g}")
print(f"U0 = {U0} = {r(U0, 5)} МДж/м³")

# Разности главных напряжений -> тоже точно через инварианты:
#   (s1-s2)² + (s2-s3)² + (s3-s1)² = 2*(I1² - 3*I2)
S = 2 * (I1**2 - 3 * I2)
print(f"\n(σ1-σ2)²+(σ2-σ3)²+(σ3-σ1)² = 2(I1н² - 3·I2н) = 2·{I1**2 - 3*I2} = {S} МПа²")
# контроль по численным корням
S_num = (s1 - s2)**2 + (s2 - s3)**2 + (s3 - s1)**2
print(f"   контроль по корням: {S_num:.4f}  (разности: "
      f"{s1-s2:.4f}; {s2-s3:.4f}; {s3-s1:.4f})")

U0f = (1 + nu) / (6 * E) * S                         # энергия формоизменения
U0v = U0 - U0f                                       # энергия изменения объёма
U0v_check = (1 - 2 * nu) / (6 * E) * I1**2
print(f"U0ф = (1+ν)/(6E)·{S} = {r(U0f, 5)} МДж/м³")
print(f"U0об = U0 - U0ф       = {r(U0v, 5)} МДж/м³")
print(f"U0об = (1-2ν)/(6E)·I1н² = {r(U0v_check, 5)} МДж/м³  -> совпадает: "
      f"{U0v == U0v_check}")
print(f"доля формоизменения: {r(U0f / U0 * 100, 2)} %")
print(f"U0 > U0ф : {U0 > U0f}")

# Сопоставление с формой записи через sx..tzx (зависит от G)
u_lin = (sx**2 + sy**2 + sz**2 - 2 * nu * (sx*sy + sy*sz + sz*sx)) / (2 * E)
u_sh_zad = (txy**2 + tyz**2 + tzx**2) / (2 * G_zad)
u_sh_t = (txy**2 + tyz**2 + tzx**2) / (2 * G_tochn)
print(f"\nТа же энергия через σx..τzx:")
print(f"  при G = 0,8·10⁵ (задание): {r(u_lin, 5)} + {r(u_sh_zad, 5)} = {r(u_lin + u_sh_zad, 5)} МДж/м³")
print(f"  при G = E/[2(1+ν)]:        {r(u_lin, 5)} + {r(u_sh_t, 5)} = {r(u_lin + u_sh_t, 5)} МДж/м³")
print(f"  совпадение со значением по главным напряжениям: {u_lin + u_sh_t == U0}")
print(f"  расхождение из-за округления G: {r((u_lin + u_sh_zad - U0) / U0 * 100, 2)} %")

# --- п. 8. Проверка прочности по IV теории ----------------------------
print()
print("-" * 72)
print("п. 8. ПРОВЕРКА ПРОЧНОСТИ ПО IV (ЭНЕРГЕТИЧЕСКОЙ) ТЕОРИИ")
print("-" * 72)
# s_экв = (1/sqrt2)*sqrt(S) = sqrt(S/2) = sqrt(I1^2 - 3*I2) -- точно под корнем
rad = I1**2 - 3 * I2
s_ekv = sqrt_hp(rad)
print(f"σэкв = √(½·{S}) = √{rad} = {s_ekv:.4f} МПа")
pred = gamma_c * R
print(f"γc·R = {float(gamma_c)}·{R} = {float(pred)} МПа")
ratio = float(s_ekv) / float(pred)
print(f"σэкв / (γc·R) = {r(ratio, 4)}  ->  превышение {r((ratio - 1) * 100, 1)} %")
print("Условие прочности НЕ выполняется" if float(s_ekv) > float(pred)
      else "Условие прочности выполняется")
# связь с энергией формоизменения
print(f"контроль: U0ф = σэкв²/(6G) = {r(float(s_ekv)**2 / (6 * float(G_tochn)), 5)} МДж/м³ "
      f"(при точном G) vs U0ф = {r(U0f, 5)}")

# ======================================================================
# ЗАДАЧА 2. Двухосное (плоское) напряжённое состояние
# ======================================================================
print()
print("=" * 72)
print("ЗАДАЧА 2. σx — строка 29, σy — строка 8, τxy — строка 25")
print("=" * 72)
sx2, sy2, txy2 = F(-85), F(-30), F(-30)
print(f"σx = {sx2} МПа;  σy = {sy2} МПа;  τxy = τyx = {txy2} МПа;  σz = τyz = τzx = 0")

# --- п. 2. Главные напряжения ----------------------------------------
J1 = sx2 + sy2
J2 = sx2 * sy2 - txy2**2
J3 = F(0)
print(f"\nI1н = σx+σy           = {J1} МПа")
print(f"I2н = σx·σy - τxy²    = {sx2*sy2} - {txy2**2} = {J2} МПа²")
print(f"I3н = 0 (двухосное состояние)")
print(f"Кубическое: σ³ - ({J1})σ² + ({J2})σ = 0  ->  σ(σ² + {-J1}σ + {J2}) = 0")

half = J1 / 2
rad2 = ((sx2 - sy2) / 2)**2 + txy2**2
assert rad2 == (J1 / 2)**2 - J2
root2 = sqrt_hp(rad2)
print(f"(σx+σy)/2 = {float(half)} МПа;  (σx-σy)/2 = {float((sx2-sy2)/2)} МПа")
print(f"√[((σx-σy)/2)² + τxy²] = √({float(((sx2-sy2)/2)**2)} + {float(txy2**2)}) "
      f"= √{float(rad2)} = {root2:.4f} МПа")
sA = Decimal(float(half)) + root2   # больший из плоских
sB = Decimal(float(half)) - root2   # меньший из плоских
print(f"σmax(в плоскости) = {sA:.4f} МПа;  σmin = {sB:.4f} МПа")
roots = sorted([Decimal(0), sA, sB], reverse=True)
print(f"\nУпорядочение σ1 ≥ σ2 ≥ σ3:")
for i, v in enumerate(roots, 1):
    print(f"  σ{i} = {v:.4f} МПа")
print("Напряжённое состояние: двухосное сжатие (оба ненулевых главных < 0)")

print("\nПроверка по инвариантам:")
print(f"  σ1+σ2+σ3        = {sum(roots):.6f} МПа   |  I1н = {J1} МПа")
p2 = roots[0]*roots[1] + roots[1]*roots[2] + roots[2]*roots[0]
print(f"  σ1σ2+σ2σ3+σ3σ1  = {p2:.6f} МПа²  |  I2н = {J2} МПа²")
print(f"  σ1·σ2·σ3        = {roots[0]*roots[1]*roots[2]:.6f} МПа³  |  I3н = {J3} МПа³")

# --- п. 3. Углы наклона главных площадок -----------------------------
print()
print("-" * 72)
print("п. 3. УГЛЫ НАКЛОНА ГЛАВНЫХ ПЛОЩАДОК К ОСИ X")
print("tg αi = τyx / (σy - σi)   (обозначения и ориентация осей — как в тетради)")
print("-" * 72)
angles = {}
for name, val in (("σ2", sA), ("σ3", sB)):
    den = Decimal(float(sy2)) - val
    tg = Decimal(float(txy2)) / den
    a = math.degrees(math.atan(float(tg)))
    angles[name] = a
    print(f"  {name} = {val:.4f}:  tg α = {float(txy2)} / ({float(sy2)} - ({val:.4f})) "
          f"= {float(txy2)} / {den:.4f} = {tg:.5f}  ->  α = {a:.2f}°")
s = abs(angles["σ2"]) + abs(angles["σ3"])
print(f"\nПроверка: |α(σ2)| + |α(σ3)| = {abs(angles['σ2']):.2f}° + "
      f"{abs(angles['σ3']):.2f}° = {s:.2f}°  (должно быть 90°)")

print("\nПодстановка направляющих косинусов в систему (l = cos α, m = -sin α):")
for name, val in (("σ2", sA), ("σ3", sB)):
    a = math.radians(angles[name])
    l, m = math.cos(a), -math.sin(a)
    e1 = (float(sx2) - float(val)) * l + float(txy2) * m
    e2 = float(txy2) * l + (float(sy2) - float(val)) * m
    print(f"  {name}: l = {l:.5f}; m = {m:.5f};  l²+m² = {l*l+m*m:.6f};  "
          f"ур.(a) = {e1:.6f};  ур.(b) = {e2:.6f}")

print("\nСопоставление с формулой tg 2α0 = 2τxy/(σx-σy) "
      "(ось y вверх, угол против часовой стрелки):")
tg2 = 2 * float(txy2) / float(sx2 - sy2)
a0 = math.degrees(math.atan(tg2)) / 2
print(f"  tg 2α0 = {2*float(txy2)}/{float(sx2-sy2)} = {tg2:.5f};  2α0 = {2*a0:.2f}°;  α0 = {a0:.2f}°")
sa = (float(J1)/2 + float((sx2-sy2)/2)*math.cos(math.radians(2*a0))
      + float(txy2)*math.sin(math.radians(2*a0)))
print(f"  σ(α0) = {sa:.4f} МПа  -> это σ3 (σmin); вторая площадка под α0+90° = {a0+90:.2f}°")
