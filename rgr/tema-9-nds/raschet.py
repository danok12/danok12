# -*- coding: utf-8 -*-
"""РГР 9, задача 2. Проверочный расчёт пунктов 1-9.

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
# нумерация как на занятии: σ1 и σ2 — оба корня в плоскости пластины
# (σ1 больший), σ3 = 0 — по площадке, совпадающей с плоскостью пластины.
# Это НЕ порядок по убыванию: здесь σ3 больше обоих остальных.
roots = [sA, sB, Decimal(0)]
print(f"\nНумерация по разбору с занятия (σ1, σ2 — в плоскости; σ3 = 0):")
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
for name, val in (("σ1", sA), ("σ2", sB)):
    den = Decimal(float(sy2)) - val
    tg = Decimal(float(txy2)) / den
    a = math.degrees(math.atan(float(tg)))
    angles[name] = a
    print(f"  {name} = {val:.4f}:  tg α = {float(txy2)} / ({float(sy2)} - ({val:.4f})) "
          f"= {float(txy2)} / {den:.4f} = {tg:.5f}  ->  α = {a:.2f}°")
s = abs(angles["σ1"]) + abs(angles["σ2"])
print(f"\nПроверка: |α(σ1)| + |α(σ2)| = {abs(angles['σ1']):.2f}° + "
      f"{abs(angles['σ2']):.2f}° = {s:.2f}°  (должно быть 90°)")

print("\nПодстановка направляющих косинусов в систему (l = cos α, m = -sin α):")
for name, val in (("σ1", sA), ("σ2", sB)):
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


# ======================================================================
# ЗАДАЧА 2. Пункты 4-9
# ======================================================================
print()
print("=" * 72)
print("ЗАДАЧА 2, п. 4-9")
print("=" * 72)

s1_2, s2_2, s3_2 = roots            # 0 >= sigma2 >= sigma3, упорядочены выше

# --- п. 4. Экстремальные касательные напряжения -----------------------
print("\nп. 4. ЭКСТРЕМАЛЬНЫЕ КАСАТЕЛЬНЫЕ НАПРЯЖЕНИЯ (площадки под ±45° к главным)")
par = (("τ12", s1_2, s2_2), ("τ23", s2_2, s3_2), ("τ31", s3_2, s1_2))
for nm, a, b in par:
    print(f"  {nm} = ±(({a:.4f}) - ({b:.4f}))/2 = ±{(a - b) / 2:.4f} МПа;"
          f"   σ' = {(a + b) / 2:.4f} МПа")
tmax2 = max(abs((a - b) / 2) for _, a, b in par)
print(f"  наибольшее из трёх: τmax = {tmax2:.4f} МПа (пара σ2, σ3)")
print(f"  контроль: τ12 = радиус круга Мора в плоскости = {root2:.4f} МПа")

# --- п. 5. Площадки под углом alpha к осям Ox и Oy --------------------
AL = 15                                    # градусов, как в разобранном примере
print(f"\nп. 5. НАПРЯЖЕНИЯ НА ПЛОЩАДКАХ ПОД УГЛОМ α = {AL}° К ОСЯМ Ox И Oy")
a_r = math.radians(AL)
c2, s2_, s2a, c2a = (math.cos(a_r)**2, math.sin(a_r)**2,
                     math.sin(2 * a_r), math.cos(2 * a_r))
sx_, sy_, t_ = float(sx2), float(sy2), float(txy2)
s_nu = sx_ * c2 + sy_ * s2_ - t_ * s2a
t_tnu = (sx_ - sy_) / 2 * s2a + t_ * c2a
s_t = sx_ + sy_ - s_nu
s_t_pr = sx_ * s2_ + sy_ * c2 + t_ * s2a
print(f"  σν  = σx·cos²α + σy·sin²α - τxy·sin2α = {s_nu:.4f} МПа")
print(f"  τtν = (σx-σy)/2·sin2α + τxy·cos2α     = {t_tnu:.4f} МПа")
print(f"  σt  = σx + σy - σν                    = {s_t:.4f} МПа")
print(f"  контроль σt по прямой формуле         = {s_t_pr:.4f} МПа  "
      f"(Δ = {abs(s_t - s_t_pr):.2e})")
print(f"  инвариант I1: σν + σt = {s_nu + s_t:.6f} МПа  (I1н = {float(J1)})")
print(f"  инвариант I2: σν·σt - τtν² = {s_nu * s_t - t_tnu**2:.6f} МПа²  "
      f"(I2н = {float(J2)})")

# --- п. 6. Деформации -------------------------------------------------
print("\nп. 6. ОТНОСИТЕЛЬНЫЕ ЛИНЕЙНЫЕ И УГЛОВЫЕ ДЕФОРМАЦИИ")
ex2 = (sx2 - nu * sy2) / E
ey2 = (sy2 - nu * sx2) / E
ez2 = (-nu * (sx2 + sy2)) / E
th2 = ex2 + ey2 + ez2
for nm, v, sl in (("εx", ex2, "укорочение dx"), ("εy", ey2, "укорочение dy"),
                  ("εz", ez2, "удлинение dz")):
    print(f"  {nm} = {float(v) * 1e5:+.4f}·10⁻⁵   ({sl if v < 0 or nm == 'εz' else ''})")
print(f"  θ = Σεi = {float(th2) * 1e5:+.4f}·10⁻⁵")
print(f"  контроль θ = (1-2ν)/E·I1н = {float((1 - 2 * nu) / E * J1) * 1e5:+.4f}·10⁻⁵")
g_xy2 = txy2 / G_zad
print(f"  γxy = τxy/G = {txy2}/{float(G_zad):.0f} = {float(g_xy2) * 1e5:+.4f}·10⁻⁵")
print(f"  γyz = γzx = 0, так как τyz = τzx = 0")
print(f"  при точном G = E/(2(1+ν)) = {float(G_tochn):.1f} МПа: "
      f"γxy = {float(txy2 / G_tochn) * 1e5:+.4f}·10⁻⁵")

# --- п. 7. Удельная потенциальная энергия -----------------------------
print("\nп. 7. УДЕЛЬНАЯ ПОТЕНЦИАЛЬНАЯ ЭНЕРГИЯ УПРУГОЙ ДЕФОРМАЦИИ")
sq2 = J1**2 - 2 * J2                    # σ1²+σ2²+σ3²
U0_2 = (sq2 - 2 * nu * J2) / (2 * E)
Uf_2 = (1 + nu) / (6 * E) * 2 * (J1**2 - 3 * J2)
Uo_2 = (1 - 2 * nu) / (6 * E) * J1**2
print(f"  σ1²+σ2²+σ3² = I1² - 2·I2 = {sq2} МПа²;  σ1σ2+σ2σ3+σ3σ1 = I2 = {J2} МПа²")
print(f"  U₀   = (1/2E)[Σσi² - 2ν·ΣσiσJ] = {float(U0_2):.6f} МПа")
print(f"  U₀^ф = ((1+ν)/6E)·2(I1²-3I2)   = {float(Uf_2):.6f} МПа  "
      f"({float(Uf_2 / U0_2) * 100:.2f} %)")
print(f"  U₀^об= ((1-2ν)/6E)·I1²        = {float(Uo_2):.6f} МПа  "
      f"({float(Uo_2 / U0_2) * 100:.2f} %)")
print(f"  контроль U₀^ф + U₀^об = {float(Uf_2 + Uo_2):.6f} МПа  "
      f"(Δ = {float(abs(U0_2 - Uf_2 - Uo_2)):.2e})")

# --- п. 8. Проверка прочности по IV теории ----------------------------
print("\nп. 8. ПРОВЕРКА ПРОЧНОСТИ ПО ЭНЕРГЕТИЧЕСКОЙ (IV) ТЕОРИИ")
pod2 = J1**2 - 3 * J2                   # σ_экв² — точно
sekv2 = sqrt_hp(pod2)
print(f"  σ_экв^IV = √(I1² - 3I2) = √{pod2} = {sekv2:.4f} МПа")
print(f"  R·γc = {R}·{float(gamma_c)} = {float(R * gamma_c)} МПа")
zap = Decimal(float(R * gamma_c)) / sekv2
print(f"  {sekv2:.2f} ≤ {float(R * gamma_c)}  ->  прочность обеспечена, "
      f"использовано {100 / zap:.1f} % несущей способности, запас {zap:.3f}")
print(f"  связь с энергией: U₀^ф = ((1+ν)/(3E))·σ_экв² = "
      f"{float((1 + nu) / (3 * E) * pod2):.6f} МПа  (выше: {float(Uf_2):.6f})")

# --- п. 9. Данные для круга Мора --------------------------------------
print("\nп. 9. КРУГ МОРА (данные построения)")
print(f"  OD = σx = {sx2};  OB = σy = {sy2};  BK = τxy = {txy2}")
print(f"  OC = (σx+σy)/2 = {float(half)} МПа;  R = CK = {root2:.4f} МПа")
print(f"  σ(в плоскости): OC + R = {sA:.4f};  OC - R = {sB:.4f} МПа")
print("  три круга (по паре главных на каждый):")
for nm, a, b in par:
    print(f"    {nm}: центр {(a + b) / 2:8.3f} МПа,  радиус {abs((a - b) / 2):7.3f} МПа")
