"""Проверка решения: задание №1, трёхшарнирная арка, вариант 19.

Данные: l = 44 м, f = 14 м, q = 10 кН/м, P = 14 кН.
Схема: ось — квадратная парабола, опоры A и B шарнирно-неподвижные на одном
уровне, шарнир C в ключе. P в K1 (x = l/4), 2P в K2 (x = 3l/4),
q на правой половине пролёта (от C до B).

Два независимых способа:
  1) формулы конспекта (ΣM, Σn, Σm для отсечённой части) — точная арифметика
     Fraction там, где нет корней; sin/cos — через sqrt, плюс «ручные» значения
     с округлением sin, cos до 5 знаков (H — до 4), как они записаны в решении;
  2) линейная система равновесия двух полуарок + векторная сумма сил,
     действующих на отсечённую часть, с проекцией на касательную и нормаль.
Запуск: python3 proverka.py  (ничего не падает = всё сошлось).
"""
from fractions import Fraction as Fr
import math

l, f, q, P = Fr(44), Fr(14), Fr(10), Fr(14)
P2 = 2 * P
x1, x2 = l / 4, 3 * l / 4                     # K1, K2
qa, qb = l / 2, l                             # участок q

y = lambda x: 4 * f / l**2 * (l * x - x**2)
tg = lambda x: 4 * f / l**2 * (l - 2 * x)

def r3(v):
    return round(float(v), 3)

# ---------------- способ 1: как в конспекте ----------------
# ΣM_B = V_A·l − P·3l/4 − 2P·l/4 − q·(l/2)·(l/4) = 0
VA = (P * 3 * l / 4 + P2 * l / 4 + q * (l / 2) * (l / 4)) / l
# ΣM_A = −V_B·l + P·l/4 + 2P·3l/4 + q·(l/2)·(3l/4) = 0
VB = (P * l / 4 + P2 * 3 * l / 4 + q * (l / 2) * (3 * l / 4)) / l
assert VA + VB - P - P2 - q * l / 2 == 0
# ΣM_C(лев) = −H_A·f + V_A·l/2 − P·l/4 = 0
HA = (VA * l / 2 - P * l / 4) / f
# ΣM_C(прав) = H_B·f − V_B·l/2 + q·(l/2)²/2 + 2P·l/4 = 0
HB = (VB * l / 2 - q * (l / 2) ** 2 / 2 - P2 * l / 4) / f
assert HA == HB
H = HA

yk1, yk2 = y(x1), y(x2)
t1, t2 = tg(x1), tg(x2)
assert yk1 == yk2 == 3 * f / 4 and t1 == -t2 == 2 * f / l

phi = math.degrees(math.atan(float(t1)))
s = float(t1) / math.sqrt(1 + float(t1) ** 2)
c = 1 / math.sqrt(1 + float(t1) ** 2)
sr, cr, Hr = round(s, 5), round(c, 5), round(float(H), 4)   # как записано в решении

# K1 — левая часть
M1 = VA * l / 4 - H * yk1
# K2 — правая часть: ΣM_K2 = M2 − V_B·l/4 + q·(l/4)·(l/8) + H·y_k = 0
M2 = VB * l / 4 - q * (l / 4) * (l / 8) - H * yk2

def left_QN(Qb, s, c, H):          # левая часть, φ > 0
    return Qb * c - H * s, -Qb * s - H * c

def right_QN(Vb, s, c, H):         # правая часть, φ по модулю
    return -Vb * c + H * s, -Vb * s - H * c

res = {}
for name, sin_, cos_, H_ in (("точно", s, c, float(H)), ("ручн", sr, cr, Hr)):
    Q1l, N1l = left_QN(float(VA), sin_, cos_, H_)
    Q1p, N1p = left_QN(float(VA - P), sin_, cos_, H_)
    Q2l, N2l = right_QN(float(VB - q * l / 4 - P2), sin_, cos_, H_)
    Q2p, N2p = right_QN(float(VB - q * l / 4), sin_, cos_, H_)
    res[name] = dict(Q1l=Q1l, Q1p=Q1p, N1l=N1l, N1p=N1p, Q2l=Q2l, Q2p=Q2p, N2l=N2l, N2p=N2p)

# ---------------- способ 2: независимая проверка ----------------
# неизвестные: A=(Ax,Ay), B=(Bx,By), C=(Cx,Cy) — сила от правой полуарки на левую
# левая:  22·Cy − 14·Cx − P·11 = 0 (ΣM_A) ; правая: ΣM_B
# решаем 2×2 для Cx, Cy точно
a11, a12, b1 = -f, l / 2, P * l / 4                      # ΣM_A левой: (l/2)·Cy − f·Cx = P·l/4
a21, a22 = f, l / 2                                      # ΣM_B правой: (l/2)·Cy + f·Cx = −(2P·l/4 + q·(l/2)·(l/4))
b2 = -(P2 * l / 4 + q * (l / 2) * (l / 4))
det = a11 * a22 - a12 * a21
Cx = (b1 * a22 - a12 * b2) / det
Cy = (a11 * b2 - b1 * a21) / det
Ax, Ay = -Cx, P - Cy
Bx, By = Cx, Cy + P2 + q * (l / 2)
assert (Ax, Ay, -Bx, By) == (H, VA, H, VB), (Ax, Ay, Bx, By)

def section(xk, side):
    """Усилия в сечении xk ('л' — левее силы, 'п' — правее) по левой части."""
    X = float(Ax)
    Y = float(Ay)
    # момент сил относительно K (против часовой +):
    # у силы F=(Fx,Fy) в точке (px,py) он равен (px−xK)·Fy − (py−yK)·Fx
    xK, yK = float(xk), float(y(xk))
    Mz = (0 - xK) * float(Ay) - (0 - yK) * float(Ax)
    for F, xf in ((P, x1), (P2, x2)):
        if xf < xk or (xf == xk and side == "п"):
            Y -= float(F)
            Mz += (float(xf) - xK) * (-float(F))
    if qa < xk:
        b = min(qb, xk)
        R = float(q * (b - qa))
        Y -= R
        Mz += (float((qa + b) / 2) - xK) * (-R)
    Fint = (-X, -Y)                       # сила от правой части на левую
    Mint = -Mz                            # момент от правой части (против часовой +)
    tx, ty = 1 / math.sqrt(1 + float(tg(xk)) ** 2), float(tg(xk)) / math.sqrt(1 + float(tg(xk)) ** 2)
    N = Fint[0] * tx + Fint[1] * ty       # вдоль касательной, от сечения
    Q = Fint[0] * ty - Fint[1] * tx       # положительная Q на правом торце левой части — вдоль (ty, −tx)
    M = Mint                              # положительный M на правом торце левой части — против часовой
    return M, Q, N


chk = {
    "M1": section(x1, "л")[0], "Q1l": section(x1, "л")[1], "N1l": section(x1, "л")[2],
    "Q1p": section(x1, "п")[1], "N1p": section(x1, "п")[2],
    "M2": section(x2, "л")[0], "Q2l": section(x2, "л")[1], "N2l": section(x2, "л")[2],
    "Q2p": section(x2, "п")[1], "N2p": section(x2, "п")[2],
}
for k in ("Q1l", "Q1p", "N1l", "N1p", "Q2l", "Q2p", "N2l", "N2p"):
    assert abs(chk[k] - res["точно"][k]) < 1e-9, (k, chk[k], res["точно"][k])
assert abs(chk["M1"] - float(M1)) < 1e-9 and abs(chk["M2"] - float(M2)) < 1e-9

# ---------------- вывод ----------------
print(f"V_A = {VA} кН, V_B = {VB} кН, ΣY = {VA + VB - P - P2 - q * l / 2}")
print(f"H_A = H_B = {H} = {float(H):.6f} кН  (H·y_k = {H * yk1})")
print(f"y_K1 = y_K2 = {yk1} м, tgφ = {t1} = {float(t1):.6f}, φ = {phi:.4f}°, sinφ = {s:.6f}, cosφ = {c:.6f}")
print(f"M1 = {M1} = {float(M1)} кН·м;  M2 = {M2} = {float(M2)} кН·м")
print(f"{'':6}{'точно':>12}{'ручн (sin,cos 5 зн.)':>24}")
for k in ("Q1l", "Q1p", "N1l", "N1p", "Q2l", "Q2p", "N2l", "N2p"):
    print(f"{k:6}{res['точно'][k]:12.4f}{res['ручн'][k]:24.4f}")

# проверки из конспекта на «ручных» значениях
h = res["ручн"]
print("\nПроверки (ручные значения):")
print(" Q1л − Q1п =", r3(h["Q1l"] - h["Q1p"]), " P·cosφ =", r3(float(P) * cr))
print(" N1п − N1л =", r3(h["N1p"] - h["N1l"]), " P·sinφ =", r3(float(P) * sr))
print(" Q2л − Q2п =", r3(h["Q2l"] - h["Q2p"]), " 2P·cosφ =", r3(float(P2) * cr))
print(" N2л − N2п =", r3(h["N2l"] - h["N2p"]), " 2P·sinφ =", r3(float(P2) * sr))
print(" K1, левая часть:  ΣX = N1п·cosφ + Q1п·sinφ + H =",
      r3(h["N1p"] * cr + h["Q1p"] * sr + Hr),
      "; ΣY = V_A − P + N1п·sinφ − Q1п·cosφ =", r3(float(VA - P) + h["N1p"] * sr - h["Q1p"] * cr))
print(" K2, правая часть: ΣX = −N2п·cosφ + Q2п·sinφ − H =",
      r3(-h["N2p"] * cr + h["Q2p"] * sr - Hr),
      "; ΣY = V_B − q·l/4 + N2п·sinφ + Q2п·cosφ =", r3(float(VB - q * l / 4) + h["N2p"] * sr + h["Q2p"] * cr))
# балочные формулы как контроль M2 с другой стороны
M0_2 = VA * x2 - P * (x2 - x1) - q * (x2 - qa) * (x2 - qa) / 2
print(f" M2 через левую часть: M⁰ − H·y = {M0_2} − {H * yk2} = {M0_2 - H * yk2}")
assert M0_2 - H * yk2 == M2
print("\nВсё сошлось: способ 1 (формулы конспекта) = способ 2 (система равновесия + векторы).")
