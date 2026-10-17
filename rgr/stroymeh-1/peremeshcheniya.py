# -*- coding: utf-8 -*-
"""Перемещения точки K в схемах 1, 3, 4 — так, как делали на паре.

  схема 1 — от нагрузки:      Δ_KP = Σ ∫ M_P·M_1 / EJ dx  (Верещагин / Симпсон)
  схема 3 — от температуры:   φ_Kt = Σ α·t_ср·Ω_N1 + Σ α·t'/h·Ω_M1
  схема 4 — от осадки опор:   Δ_Kc = −Σ R_i1·c_i

Единичное состояние: та же система без нагрузки, в точке K — единичная сила
(или момент) по направлению искомого перемещения. Все числа — дроби.

Знак M у решателя: «+» — растянуто волокно справа от направления стержня
(от первого узла ко второму). Оба состояния считаются на тех же стержнях
с тем же направлением, поэтому знак произведения M_P·M_1 получается сам:
«+», если обе ординаты с одной стороны стержня.
"""
from fractions import Fraction as F
import math
from rama import Sistema
from sistemy import shema1, shema3, shema4

ok = True


def edinichnoe(src, name, force=None, moment=None):
    """Копия системы src без нагрузки, с единичным воздействием в точке."""
    s = Sistema(name)
    s.nodes = dict(src.nodes)
    s.members = list(src.members)
    s.supports = list(src.supports)
    s.hinges = list(src.hinges)
    if force:
        s.force(*force)
    if moment:
        s.moment(*moment)
    s.solve()
    return s


def simpson(sp, s1, mem):
    """∫ M_P·M_1 dx на стержне по формуле Симпсона: l/6·(ac + 4·mn + bd).
    Точна, пока произведение — многочлен не выше 3-й степени (прямая × парабола)."""
    L = sp.length(mem)
    a, m, b = (sp.internal(mem, F(t, 2))[2] for t in range(3))
    c, n, d = (s1.internal(mem, F(t, 2))[2] for t in range(3))
    return L, (a, m, b), (c, n, d), L / 6 * (a * c + 4 * m * n + b * d)


def chislenno(sp, s1, mem, n=4000):
    """Контроль: тот же интеграл прямым суммированием (средние точки)."""
    L = float(sp.length(mem))
    acc = 0.0
    for i in range(n):
        t = F(2 * i + 1, 2 * n)
        acc += float(sp.internal(mem, t)[2]) * float(s1.internal(mem, t)[2])
    return acc * L / n


def mora(sp, s1, title):
    global ok
    print(f"\n{title}")
    tot = F(0)
    for mem, a, b in sp.members:
        L, P, U, v = simpson(sp, s1, mem)
        num = chislenno(sp, s1, mem)
        good = abs(float(v) - num) < 1e-3 * max(1.0, abs(num))
        ok &= good
        print(f"  {mem:5s} l={L}:  M_P = {[str(x) for x in P]};  M_1 = {[str(x) for x in U]}"
              f"  ->  {str(v):>8s} = {float(v):9.4f}  (численно {num:9.4f}) {'ок' if good else 'НЕТ'}")
        tot += v
    print(f"  ИТОГО EJ·Δ = {tot} = {float(tot):.4f}")
    return tot


# ================================================================ схема 1
s1p = shema1(); s1p.solve()
print("=" * 80)
print("СХЕМА 1 — перемещение точки K от нагрузки")
v1 = edinichnoe(s1p, "Схема 1, P=1 вниз в K", force=('K', 0, -1, '1'))
g1 = edinichnoe(s1p, "Схема 1, P=1 вправо в K", force=('K', 1, 0, '1'))
for s in (v1, g1):
    print(s.name, {k: str(v) for k, v in s.R.items()})
Dv = mora(s1p, v1, "вертикальное (P = 1 вниз):")
Dg = mora(s1p, g1, "горизонтальное (P = 1 вправо):")
print(f"полное: EJ·Δ = √(Δв² + Δг²) = {math.hypot(float(Dv), float(Dg)):.4f}")

# ================================================================ схема 3
s3p = shema3(); s3p.solve()
print("\n" + "=" * 80)
print("СХЕМА 3 — угол поворота сечения K от температуры")
u3 = edinichnoe(s3p, "Схема 3, M=1 по часовой в K", moment=('K', -1, '1'))
print(u3.name, {k: str(v) for k, v in u3.R.items()})
# внутренняя сторона контура рамы J–R–RB–LB: s_in = +1, если она справа
# от направления стержня (там, где у решателя M > 0); у KJ внутренней стороны нет
S_IN = {'KJ': None, 'JLB': -1, 'JR': +1, 'RRB': +1}
for mem, a, b in u3.members:
    L = u3.length(mem)
    N = u3.internal(mem, F(1, 2))[0]
    Ma, Mb = u3.internal(mem, F(0))[2], u3.internal(mem, F(1))[2]
    Om = L * (Ma + Mb) / 2
    print(f"  {mem:4s} l={L}: N1 = {str(N):>6s}, Ω_N = {str(N * L):>6s};  M1: {Ma} → {Mb}, "
          f"Ω_M = {str(Om):>6s}, со стороны внутр.: {'—' if S_IN[mem] is None else str(Om * S_IN[mem])}")


def temperatura(t_nar, t_vn, h):
    """φ_Kt / α. У стержней контура t_ср = (t_нар + t_вн)/2, t' = |t_вн − t_нар|;
    у консоли K–J обе грани снаружи: t_ср = t_нар, t' = 0."""
    res_N, res_M = F(0), F(0)
    for mem, a, b in u3.members:
        L = u3.length(mem)
        N = u3.internal(mem, F(1, 2))[0]
        Ma, Mb = u3.internal(mem, F(0))[2], u3.internal(mem, F(1))[2]
        Om = L * (Ma + Mb) / 2
        if S_IN[mem] is None:
            tsr, dt = F(t_nar), F(0)
        else:
            tsr, dt = F(t_nar + t_vn, 2), F(t_vn - t_nar)
        res_N += tsr * N * L
        if dt:
            res_M += dt / F(h) * Om * S_IN[mem]   # «+» — эпюра со стороны тёплого волокна
    return res_N, res_M


rN, rM = temperatura(-8, 20, F(1, 2))
print(f"  пример (данные с пары: t_нар = −8, t_вн = +20, h = 0,5 м):")
print(f"     от N: {rN}·α;  от M: {rM}·α;  φ_Kt = {rN + rM}·α = {float(rN + rM):.4f}·α")

# ================================================================ схема 4
s4p = shema4(); s4p.solve()
print("\n" + "=" * 80)
print("СХЕМА 4 — вертикальное перемещение точки K от осадки опор")
u4 = edinichnoe(s4p, "Схема 4, P=1 вниз в K", force=('K', 0, -1, '1'))
print(u4.name, {k: str(v) for k, v in u4.R.items()})
print("  Δ_Kc = −Σ R_i1·c_i;  R_S ↑ = %s, R_Bx = %s, R_By ↑ = %s, M_B = %s (− — по часовой)"
      % tuple(str(u4.R[k]) for k in ('R_S', 'R_Bx', 'R_By', 'M_B')))

print("\n" + ("ВСЁ СОШЛОСЬ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ"))


# ======================================= независимая проверка — кинематикой
# Схема 3: деформации от температуры «собираются» по стержням от опор:
#   на прямом участке длины L (орт t, нормаль n = z×t) с удлинением ε и
#   кривизной κ (κ > 0, если удлиняется волокно справа от направления):
#   φ(L) = φ0 + κL;  u(L) = u0 + εL·t + (φ0·L + κL²/2)·n.
# Неизвестны повороты дисков у опор θ1, θ2 — из совпадения перемещений J.
def put(u0, phi0, t, L, eps, kap):
    n = (-t[1], t[0])
    c = phi0 * L + kap * L * L / 2
    return ((u0[0] + eps * L * t[0] + c * n[0], u0[1] + eps * L * t[1] + c * n[1]),
            phi0 + kap * L)


def phi_K_kinematika(t_nar, t_vn, h, alpha=F(1)):
    tsr, dt = F(t_nar + t_vn, 2), F(t_vn - t_nar)
    eps, kap = alpha * tsr, alpha * dt / F(h)          # тёплая сторона — внутри
    # u_J и φ как линейные функции θ: храним коэффициенты (свободный, при θ)
    def lin_put(start_theta_coef, segs):
        u0 = ((F(0), F(0)), (F(0), F(0)))              # (своб. часть, коэф. при θ)
        ph = (F(0), F(1))
        for t, L, e, k in segs:
            a, ph_a = put(u0[0], ph[0], t, L, e, k)
            b, ph_b = put(u0[1], ph[1], t, L, 0, 0)
            u0, ph = (a, b), (ph_a, ph_b)
        return u0, ph
    # диск I: опора 1 (0;−4) → J (0;0): вверх, внутренняя (тёплая) сторона справа
    uI, phI = lin_put(1, [((0, 1), 4, eps, +kap)])
    # диск II: опора 2 (6;−4) → R (6;0) вверх, тёплая сторона слева; R → J влево,
    # тёплая сторона (снизу) — слева от направления
    uII, phII = lin_put(1, [((0, 1), 4, eps, -kap), ((-1, 0), 6, eps, -kap)])
    # uI0 + θ1·uI1 = uII0 + θ2·uII1  (две проекции)
    a11, a12, b1 = uI[1][0], -uII[1][0], uII[0][0] - uI[0][0]
    a21, a22, b2 = uI[1][1], -uII[1][1], uII[0][1] - uI[0][1]
    det = a11 * a22 - a12 * a21
    th1 = (b1 * a22 - a12 * b2) / det
    return phI[0] + th1 * phI[1]          # K–J без кривизны (обе грани снаружи)


fk = phi_K_kinematika(-8, 20, F(1, 2))
good = (fk == -(rN + rM))                 # у Мора — по часовой, здесь — против
ok &= good
print(f"\nпроверка схемы 3 кинематикой: поворот K против часовой = {fk}·α "
      f"(по Мору по часовой {rN + rM}·α) — {'ок' if good else 'НЕТ'}")


# Схема 4: смещения опор — жёсткие перемещения дисков (деформаций нет)
def K_vniz_kinematika(cS=F(0), cBx=F(0), cBy=F(0), phB=F(0)):
    """cS, cBy — вверх «+», cBx — вправо «+», phB — по часовой «+».
    Возвращает перемещение K вниз."""
    B, H, S, K = (F(12), F(0)), (F(6), F(4)), (F(0), F(0)), (F(3), F(0))
    th = -phB                                         # против часовой «+»
    uH = (cBx - th * (H[1] - B[1]), cBy + th * (H[0] - B[0]))
    # диск I: u(P) = uH + θ1×(P − H); вертикаль в S задана: uS_y = cS
    th1 = (cS - uH[1]) / (S[0] - H[0])
    uK_y = uH[1] + th1 * (K[0] - H[0])
    return -uK_y


R = u4.R
for nm, kw in (("S вверх", dict(cS=F(1))), ("B вправо", dict(cBx=F(1))),
               ("B вверх", dict(cBy=F(1))), ("B по часовой", dict(phB=F(1)))):
    kin = K_vniz_kinematika(**kw)
    mor = -(R['R_S'] * kw.get('cS', 0) + R['R_Bx'] * kw.get('cBx', 0)
            + R['R_By'] * kw.get('cBy', 0) + (-R['M_B']) * kw.get('phB', 0))
    good = kin == mor
    ok &= good
    print(f"проверка схемы 4, смещение «{nm}» = 1:  кинематика {kin},  −ΣR·c = {mor}  "
          f"{'ок' if good else 'НЕТ'}")
print("\n" + ("ВСЁ СОШЛОСЬ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ"))


# ================================================================ рисунки
if __name__ == "__main__":
    import epury
    import figury

    def drob(v):
        """Ординаты единичных эпюр — простыми дробями, как на паре."""
        x = F(v).limit_denominator(48)
        if x.denominator == 1:
            return f"{x.numerator}"
        return f"{x.numerator}/{x.denominator}"

    def edinica(pt, dx, dy, lab):
        """Единичная сила на рисунке эпюры: стрелка остриём в точку."""
        def risuj(pan):
            x, y = pan.P(pt)
            L = 46
            sx, sy = x - dx * L, y + dy * L
            hx, hy = dx, -dy                    # к острию, в экранных осях
            nx, ny = -hy, hx
            a1 = (x - hx * 11 + nx * 5, y - hy * 11 + ny * 5)
            a2 = (x - hx * 11 - nx * 5, y - hy * 11 - ny * 5)
            out = epury.ln((sx, sy), (x - hx * 9, y - hy * 9), "ep-ed")
            out += (f'<polygon points="{x:.1f},{y:.1f} {a1[0]:.1f},{a1[1]:.1f} '
                    f'{a2[0]:.1f},{a2[1]:.1f}" fill="#000"/>\n')
            return out + epury.txt(sx + 8 * (1 if dx == 0 else 0), sy + (-6 if dy == 0 else 0),
                                   lab, "ep-kl", "start")
        return risuj

    epury.num = drob
    K1 = s1p.nodes['K']
    figury.risunok(v1, 2, "ed-1-v-m.svg", edinica(K1, 0, -1, "P = 1"))
    figury.risunok(g1, 2, "ed-1-g-m.svg", edinica(K1, 1, 0, "P = 1"))
    figury.risunok(u3, 2, "ed-3-m.svg")
    figury.risunok(u3, 0, "ed-3-n.svg")
    print("рисунки единичных эпюр записаны")
