"""Расчёт внутреннего водопровода В1 и канализации К1, вариант 3.

Запуск: python raschet_v3.py  ->  ../RASCHET_V3.md (таблицы для записки) и rezultaty_v3.json (данные для Revit).
Все допущения собраны в блоке ДОПУЩЕНИЯ; поменять там -> перезапустить.
"""
import json
import math
import os

from normy import A1, A2_ZHILYE, K_STOYAKI, T51, T51_L, T121, alpha_b2
from pavlovsky import flow

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- ИСХОДНЫЕ ДАННЫЕ (задание, вариант 3) ----------------
N_SEK, N_ET, H_ET = 2, 11, 3.2
U0 = 3.8                      # чел./кв.
H_PODVAL, T_PEREKR = 3.0, 0.3
DH_POL = 0.3                  # пол 1-го этажа над планировкой
H_PROMERZ = 1.7
H_GAR = 14.0
D_GOR_V, D_GOR_K = 250, 400

# ---------------- ДОПУЩЕНИЯ ----------------
N_KV = 3                      # квартир на этаже в секции (по плану: 3 санузла)
PRIBORY = ["мойка со смесителем", "умывальник со смесителем", "ванна со смесителем", "унитаз со смывным бачком"]
NORMA = A2_ZHILYE["ванны от 1500 мм с душами"]   # ЦГВ, ванны 1500-1700 мм
ALPHA_MODE = "floor"          # как в примерах методички
K_MS = 0.3                    # хоз-питьевой водопровод жилого здания
H_SV = 20.0                   # п. 8.21
Z0_ABS = 101.00               # абс. отметка 0,000 (как в образце)
# Трасса — из модели (revit/geometriya_v3.py пишет calc/trassa_v3.json): у каждой квартиры свои стояки В1 и К1
# (СП 30, п. 18.6; как в образце), секция 2 — зеркальная копия секции 1 относительно оси 11.
TRASSA = json.load(open(os.path.join(HERE, "trassa_v3.json"), encoding="utf-8"))
L_SEK = 22.5
X_NASOS = TRASSA["x_troynik"]  # тройник магистрали у насосной (подвал секции 1)
Y_MAG = TRASSA["y_mag"]        # магистраль В1 под потолком подвала вдоль оси В
Z_MAG = TRASSA["z_mag"]        # ось магистрали В1 (низ перекрытия -0,30)
Z_POD = 0.3                    # ось поквартирной разводки над полом
Z_UZEL = 1.0                   # тройник квартирного ответвления на стояке (узел учёта)
L_NAP = TRASSA["l_nap"]        # напорная линия: коллектор установки -> тройник магистрали, м (из модели)
# Стояки К1 в секции (локальные x от оси 1, y от оси А) — как в модели; секция 2 зеркальна
ST_K = {"A": (0.365, 6.22), "B": (15.325, 7.42), "C": (16.075, 7.43)}
# Кандидаты в диктующие приборы верхнего этажа: высота над полом и участки разводки (N, L) от прибора к стояку.
# Душ над ванной на 1,95 м — как в примерах ПЗ кафедры; мойка — самый удалённый от стояка прибор.
DIKT_VARIANTY = {
    "мойка": dict(z=1.0, L_KV=[(1, 1.6), (2, 0.6), (3, 0.95), (4, 1.2)]),
    "душевая сетка над ванной": dict(z=1.95, L_KV=[(1, 1.65), (3, 0.95), (4, 1.2)]),
}
L_VVOD = 25.0                 # ввод: 23 м от ГВК до стены + 2 м до насосной
Z_ZEML_VVOD = -0.50           # земля у ГВК, отн. (100,50)

# Сталь ВГП оцинкованная ГОСТ 3262-75 (обыкновенная): DN -> внутренний диаметр, мм
VGP = {15: 15.7, 20: 21.2, 25: 27.1, 32: 35.9, 40: 41.0, 50: 53.0, 65: 67.5, 80: 80.5, 100: 105.0}
D_ZAPAS = 1.0                 # расчётный диаметр Шевелёва: d_вн - 1 мм  (СВЕРИТЬ по программе)
# ПЭ100 SDR17 для ввода: наружный -> внутренний, мм
PE = {63: 55.4, 75: 66.0, 90: 79.2, 110: 96.8, 125: 110.2}
V_MAX = {"подводка": 1.5, "стояк": 1.2, "магистраль": 1.2}   # экономичные скорости; предел по методичке 1,5
I_MIN_K1 = {100: 0.02, 150: 0.008}   # внутри здания 0,02 (как в образце); дворовая d150 — 0,008 (СП 32)
Z_GKK_GOR = 97.80             # лоток городского коллектора Ø400 в ГКК — «по месту», принят


def r(v, n=3):
    return round(v + 0.0, n)


def shevelev_steel(q_ls, dn):
    """Потери i (м/м) и скорость по формулам Шевелёва для неновых стальных труб."""
    d = (VGP[dn] - D_ZAPAS) / 1000
    v = q_ls / 1000 / (math.pi * d * d / 4)
    if v < 1.2:
        i = 0.000912 * v * v / d ** 1.3 * (1 + 0.867 / v) ** 0.3
    else:
        i = 0.00107 * v * v / d ** 1.3
    return v, i


def colebrook_pe(q_ls, dn):
    d = PE[dn] / 1000
    v = q_ls / 1000 / (math.pi * d * d / 4)
    re = v * d / 1.31e-6
    lam = 0.02
    for _ in range(50):
        lam = (-2 * math.log10(0.01e-3 / (3.7 * d) + 2.51 / (re * math.sqrt(lam)))) ** -2
    return v, lam / d * v * v / (2 * 9.81)


def podbor(q_ls, fun, ryad, dmin=None, vmax=1.5):
    for dn in sorted(ryad):
        if dmin and dn < dmin:
            continue
        v, i = fun(q_ls, dn)
        if v <= vmax:
            return dn, v, i
    raise ValueError(q_ls)


# ---------------- 1. РАСХОДЫ ----------------
n_kv_vsego = N_KV * N_ET * N_SEK
U = math.ceil(U0 * n_kv_vsego - 1e-9)
N_PR = len(PRIBORY)
N = N_PR * n_kv_vsego
q_hr_c = NORMA["q_hr_tot"] - NORMA["q_hr_h"]
q_u_c = NORMA["q_u_tot"] - NORMA["q_u_h"]
P_tot = NORMA["q_hr_tot"] * U / (3600 * N * NORMA["q0_tot"])
P_c = q_hr_c * U / (3600 * N * NORMA["q0_c"])
P_hr_tot = P_tot * 3600 * NORMA["q0_tot"] / NORMA["q0hr_tot"]
P_hr_c = P_c * 3600 * NORMA["q0_c"] / NORMA["q0hr_c"]


def q_sec(n, p, q0):
    a = alpha_b2(n * p, ALPHA_MODE)
    return a, 5 * a * q0


rasx = {}
rasx["Q_sut_tot"] = NORMA["q_u_tot"] * U / 1000
rasx["Q_sut_c"] = q_u_c * U / 1000
rasx["q_T_tot"] = rasx["Q_sut_tot"] / NORMA["T"]
rasx["q_T_c"] = rasx["Q_sut_c"] / NORMA["T"]
rasx["a_tot"], rasx["q_tot"] = q_sec(N, P_tot, NORMA["q0_tot"])
rasx["a_c"], rasx["q_c"] = q_sec(N, P_c, NORMA["q0_c"])
rasx["a_hr_tot"] = alpha_b2(N * P_hr_tot, ALPHA_MODE)
rasx["q_hr_tot"] = 0.005 * rasx["a_hr_tot"] * NORMA["q0hr_tot"]
rasx["a_hr_c"] = alpha_b2(N * P_hr_c, ALPHA_MODE)
rasx["q_hr_c"] = 0.005 * rasx["a_hr_c"] * NORMA["q0hr_c"]

# ---------------- 2. ГИДРАВЛИЧЕСКИЙ РАСЧЁТ В1 ----------------
n_et_pr = N_PR                 # один стояк — одна квартира на этаже
n_st = n_et_pr * N_ET
MAG = TRASSA["magistral"]      # участки магистрали от тройника на восток: (x_от, x_до, L, N, DN)
ST_V1 = TRASSA["stoyaki_v1"]   # имя -> (x, y)


def F_(v):
    return f"{v:.2f}".replace(".", ",")


def put_k_stoyaku(nm):
    """Участки магистрали от тройника у насосной до ответвления на стояк nm (от стояка к тройнику)."""
    x, y = ST_V1[nm][2], ST_V1[nm][1]        # точка ответвления на магистрали
    out = []
    if x < X_NASOS:            # стояк западнее тройника — отдельная ветка
        out.append(("магистраль: тройник - " + nm, n_st, r(X_NASOS - x, 2)))
    else:
        for x0, x1, l_, n_, dn_ in MAG:
            out.append((f"магистраль x = {F_(x0)}…{F_(x1)}", n_, l_))
            if abs(x1 - x) < 1e-6:
                break
    return out[::-1]


def raschet_v1(l_kv, nm):
    uchastki = []                 # (имя, N, L)
    for n_, l_ in l_kv:
        uchastki.append(("кв. разводка", n_, l_))
    for k in range(N_ET, 1, -1):
        uchastki.append((f"стояк {nm}, эт. {k}-{k - 1}", n_et_pr * (N_ET - k + 1), H_ET))
    uchastki.append((f"стояк {nm}, эт. 1 - магистраль", n_st,
                     r(Z_UZEL - Z_MAG + abs(ST_V1[nm][1] - Y_MAG) + abs(ST_V1[nm][0] - ST_V1[nm][2]), 2)))
    uchastki += put_k_stoyaku(nm)
    uchastki.append(("напорная линия: установка - тройник магистрали", N, L_NAP))
    res = []
    for nom, (imya, n_, l_) in enumerate(uchastki, 1):
        a, q = q_sec(n_, P_c, NORMA["q0_c"])
        vid_tr = "стояк" if imya.startswith("стояк") else ("подводка" if imya.startswith("кв.") else "магистраль")
        dmin = {"стояк": 25, "магистраль": 32, "подводка": 15}[vid_tr]
        if imya.startswith("напорная"):
            dmin = 50                 # по патрубку коллектора установки
        dn, v, i = podbor(q, shevelev_steel, VGP, dmin, V_MAX[vid_tr])
        res.append(dict(n=nom, imya=imya, L=l_, N=n_, P=P_c, NP=n_ * P_c, a=a, q=q, dn=dn, v=v, i=i,
                        iL=i * l_, h=i * l_ * (1 + K_MS)))
    return res


# диктующий стояк — с наибольшими потерями до верхнего прибора (все стояки — по одной квартире на этаже)
poteri = {nm: sum(u["h"] for u in raschet_v1(DIKT_VARIANTY["душевая сетка над ванной"]["L_KV"], nm)) for nm in ST_V1}
ST_DIKT = max(poteri, key=poteri.get)


varianty = {}
for nazv, dv in DIKT_VARIANTY.items():
    tab = raschet_v1(dv["L_KV"], ST_DIKT)
    varianty[nazv] = dict(tab=tab, sum_h=sum(u["h"] for u in tab), z=(N_ET - 1) * H_ET + dv["z"], z_pr=dv["z"])
# диктующий — тот, для которого z + Σh больше (остальные слагаемые H_тр у вариантов общие)
DIKT = max(varianty, key=lambda k: varianty[k]["z"] + varianty[k]["sum_h"])
v1 = varianty[DIKT]["tab"]
sum_h_v1 = varianty[DIKT]["sum_h"]
Z_DIKT = varianty[DIKT]["z_pr"]

# Ввод — на холодный расход: проектируются только В1 и К1, горячая вода готовится вне здания
# (методичка Хургина, Гул: «ввод рассчитывается на расход, не учитывающий подачу воды на ГВС»)
dn_vv, v_vv, i_vv = podbor(rasx["q_c"], colebrook_pe, PE)
h_vvod = i_vv * L_VVOD * (1 + K_MS)

# ---------------- 3. СЧЁТЧИКИ ----------------
def podbor_schetchik(q_T, q_s, dop_kryl=5.0, dop_turb=2.5):
    for dn in sorted(T121):
        expl, S = T121[dn]
        if expl < q_T:
            continue
        h = S * q_s ** 2
        dop = dop_kryl if dn <= 40 else dop_turb
        if h <= dop:
            return dn, expl, S, h, dop
    raise ValueError


sch_dom = podbor_schetchik(rasx["q_T_c"], rasx["q_c"])
q_kv = q_sec(N_PR, P_c, NORMA["q0_c"])[1]
sch_kv = (15, T121[15][0], T121[15][1], T121[15][1] * q_kv ** 2, 5.0)

# ---------------- 4. ТРЕБУЕМЫЙ НАПОР, НАСОС ----------------
z_gor_verh = Z_ZEML_VVOD - (H_PROMERZ + 0.5)          # верх трубы городской сети
z_dikt = (N_ET - 1) * H_ET + Z_DIKT
H_geom = z_dikt - z_gor_verh
H_vod = sch_dom[3] + sch_kv[3]
H_tr = H_geom + sum_h_v1 + H_SV + H_vod + h_vvod
H_nas = H_tr - H_GAR
z_niz = 0.8                                            # смеситель ванны 1-го этажа
H_st_niz = H_GAR + H_nas - (z_niz - z_gor_verh)        # без учёта потерь — наихудший случай
et_reg = [k for k in range(1, N_ET + 1)
          if H_GAR + H_nas - ((k - 1) * H_ET + z_niz - z_gor_verh) > 45.0]

# ---------------- 5. К1: СТОЯКИ ----------------
k1_st = []
for nm in sorted(TRASSA["stoyaki_k1"], key=lambda t: int(t.split("-")[1])):
    n_ = N_PR * N_ET
    a, qt = q_sec(n_, P_tot, NORMA["q0_tot"])
    qs = qt + A1["унитаз со смывным бачком"]["q0s"]
    qdop = K_STOYAKI[("ПП", 110, 45)][110]          # стояки из полипропилена ГОСТ 32414-2013
    k1_st.append(dict(st=nm, N=n_, NP=n_ * P_tot, a=a, q_tot=qt, q_s=qs, q_dop=qdop, ok=qs <= qdop))

# ---------------- 6. К1: ГОРИЗОНТАЛЬНЫЕ УЧАСТКИ И ДВОРОВАЯ СЕТЬ ----------------
Q0S2 = A1["ванна со смесителем"]["q0s"]                # 1,1 л/с, как в методичке


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    j = max(k for k in range(len(xs)) if xs[k] <= x)
    return ys[j] + (ys[j + 1] - ys[j]) * (x - xs[j]) / (xs[j + 1] - xs[j])


def ks_tab(n_, l_):
    """K_s по табл. 5.1 с линейной интерполяцией по L, затем по N."""
    rows = sorted(T51)
    po_l = [_interp(l_, T51_L, T51[nr]) for nr in rows]
    return _interp(n_, rows, po_l)


def hd_dlya(q, d, i):
    lo, hi = 0.01, 0.95
    for _ in range(60):
        m = (lo + hi) / 2
        if flow(d, i, m, 0.014)[1] < q:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


UKL = {100: [10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50], 150: [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25, 30]}


def podbor_k1(q, d, K, d_nar):
    i_min = max(1 / d_nar, I_MIN_K1[d])
    for u in UKL[d]:
        i = u / 1000
        if i < i_min - 1e-12:
            continue
        hd = hd_dlya(q, d, i)
        v = flow(d, i, hd, 0.014)[0]
        if hd <= 0.6 and hd >= 0.3 and v >= 0.7 and v * math.sqrt(hd) >= K:
            return i, hd, v, "расчётный"
    # безрасчётный: условие не выполнимо из-за малого расхода -> i >= 1/d
    i = next(u for u in UKL[d] if u / 1000 >= i_min - 1e-12) / 1000
    hd = hd_dlya(q, d, i)
    return i, hd, flow(d, i, hd, 0.014)[0], "безрасчётный (i ≥ 1/d)"


def k1_uch(imya, n_, l_, d, K, d_nar):
    a = alpha_b2(n_ * P_hr_tot, ALPHA_MODE)
    qhr = 0.005 * a * NORMA["q0hr_tot"]
    ks = ks_tab(n_, l_)
    qs = qhr / 3.6 + ks * Q0S2
    i, hd, v, tip = podbor_k1(qs, d, K, d_nar)
    return dict(imya=imya, L=l_, N=n_, P=P_hr_tot, a=a, q_hr=qhr, q0s=Q0S2, Ks=ks, q=qs, d=d, hd=hd, v=v,
                K=v * math.sqrt(hd), i=i, iL=i * l_, tip=tip)


n_kv_st = N_PR * N_ET           # приборов на стояке К1
(xA, yA), (xB, yB), (xC, yC) = ST_K["A"], ST_K["B"], ST_K["C"]
D45, Y_SB, Y_ST_D = 0.2, 8.2, 12.8 + 0.06 + 0.26
for nm, (x, y) in TRASSA["stoyaki_k1"].items():          # сверка положения стояков с моделью
    assert any(abs(x - xx) < 1e-3 and abs(y - yy) < 1e-3 for xx, yy in
               list(ST_K.values()) + [(2 * L_SEK - a_, b_) for a_, b_ in ST_K.values()]), nm
L_C_B = r(D45 + (Y_SB - 0.15 - (yC + D45)) + 0.15 * math.sqrt(2) + (xC - 0.15 - (xB - 0.3)), 2)
L_B_VYP = r((xB - 0.3) - (xA + 0.3) + 0.3 * math.sqrt(2), 2)
L_VYP = 5.0                                            # от наружной стены до КК
L_A_KK = r(Y_ST_D - (yA + D45) + D45 * math.sqrt(2) + L_VYP, 2)
k1_vnutr = [
    k1_uch("сборный: ст. кв. В - ст. кв. Б (чугун SML)", n_kv_st, L_C_B, 100, 0.6, 110),
    k1_uch("сборный: ст. кв. Б - выпуск (чугун SML)", 2 * n_kv_st, L_B_VYP, 100, 0.6, 110),
    k1_uch("выпуск: ст. кв. А - КК (чугун SML)", 3 * n_kv_st, L_A_KK, 100, 0.6, 110),
]
# Дворовая сеть вдоль фасада Д в 5 м от стены: выпуск секции 2 (торец по оси 21) -> КК-1, промежуточный КК-2 у стыка
# секций (не реже чем через 35 м при d = 150), выпуск секции 1 (торец по оси 1) -> КК-3; городские сети у торца по оси 1.
X_GOR = -15.0
X_KRASN = -10.0
x_kk1, x_kk2, x_kk3, x_kkk = 2 * L_SEK - xA, L_SEK, xA, X_KRASN + 1.2
dvor = [
    k1_uch("КК-1 - КК-2 (ПЭ гофр. Ø160)", 3 * n_kv_st, r(x_kk1 - x_kk2, 2), 150, 0.5, 160),
    k1_uch("КК-2 - КК-3 (ПЭ гофр. Ø160)", 3 * n_kv_st, r(x_kk2 - x_kk3, 2), 150, 0.5, 160),
    k1_uch("КК-3 - ККК (ПЭ гофр. Ø160)", 6 * n_kv_st, r(x_kk3 - x_kkk, 2), 150, 0.5, 160),
    k1_uch("ККК - ГКК (ПЭ гофр. Ø160)", 6 * n_kv_st, r(x_kkk - X_GOR, 2), 150, 0.5, 160),
]
assert all(u["L"] <= 35.0 for u in dvor), "расстояние между колодцами больше 35 м"
zeml = {"КК-1": 100.85, "КК-2": 100.70, "КК-3": 100.55, "ККК": 100.40, "ГКК": 100.30}
z_vyp_lotok = Z0_ABS - 2.00                            # лоток выпуска у стены: -2,000
lotok = {}
lotok["выпуск у стены"] = z_vyp_lotok
lotok["выпуск в КК (Ø100)"] = z_vyp_lotok - k1_vnutr[2]["i"] * L_VYP
lotok["КК-1"] = lotok["выпуск в КК (Ø100)"] + 0.100 - 0.150          # шелыга в шелыгу
lotok["КК-2"] = lotok["КК-1"] - dvor[0]["iL"]
lotok["КК-3"] = lotok["КК-2"] - dvor[1]["iL"]
lotok["ККК"] = lotok["КК-3"] - dvor[2]["iL"]
lotok["ГКК"] = lotok["ККК"] - dvor[3]["iL"]
glub = {k: zeml[k] - lotok[k] for k in ("КК-1", "КК-2", "КК-3", "ККК", "ГКК")}
vyp_v_kk3_ok = lotok["выпуск в КК (Ø100)"] + 0.100 >= lotok["КК-3"] + 0.150 - 1e-9
k1_vnutr[2]["kon"] = lotok["выпуск в КК (Ø100)"]
k1_vnutr[2]["nach"] = k1_vnutr[2]["kon"] + k1_vnutr[2]["iL"]
k1_vnutr[1]["kon"] = z_vyp_lotok + k1_vnutr[2]["i"] * (Y_ST_D - (Y_SB + 0.3))
k1_vnutr[1]["nach"] = k1_vnutr[1]["kon"] + k1_vnutr[1]["iL"]
k1_vnutr[0]["kon"] = k1_vnutr[1]["nach"]
k1_vnutr[0]["nach"] = k1_vnutr[0]["kon"] + k1_vnutr[0]["iL"]
for u, (a_, b_) in zip(dvor, [("КК-1", "КК-2"), ("КК-2", "КК-3"), ("КК-3", "ККК"), ("ККК", "ГКК")]):
    u["nach"], u["kon"] = lotok[a_], lotok[b_]
perepad_gkk = lotok["ГКК"] - (Z_GKK_GOR + 0.400)        # над шелыгой городского коллектора
min_glub = max(H_PROMERZ - 0.3, 0.7 + 0.150)                         # H0 = max(H_пр − 0,3; 0,7 + d), как в примерах ПЗ кафедры

# ---------------- ВЫВОД ----------------
F = lambda v, n=3: f"{v:.{n}f}".replace(".", ",")
L = []
w = L.append
w("# Расчёт систем В1 и К1 — вариант 3\n")
w("Сгенерировано `calc/raschet_v3.py`; руками не править — менять допущения в скрипте и перезапускать.\n")
w("## Принятые допущения\n")
w(f"- Квартир на этаже в секции: **{N_KV}** (по плану — три санузла); всего квартир {n_kv_vsego}.")
w(f"- Приборы в квартире: {', '.join(PRIBORY)} — {N_PR} шт.")
w("- Проектируются системы В1 и К1; горячее водоснабжение — вне объёма проекта (вода готовится вне здания). "
  "Поэтому ввод, общедомовой счётчик, насосная установка и сеть В1 — на холодный расход q^c; "
  "К1 — на общий расход q^tot (в канализацию уходит и холодная, и горячая вода).")
w("- Норма: табл. А.2, жилые дома с ваннами от 1500 мм с душами.")
w(f"- α по табл. Б.2 — режим «{ALPHA_MODE}» (ближайшее меньшее табличное NP, как в примерах методички).")
w("- Трубы В1: сталь ВГП оцинкованная ГОСТ 3262-75; потери по формулам Шевелёва, расчётный диаметр d_вн − 1 мм (сверено с табл. 1 Шевелёва: 1000i совпадает до 0,3 %, `proverka_shevelev.py`).")
w("- Ввод: ПЭ100 SDR17, потери по Колбруку–Уайту (Δ = 0,01 мм) — **сверить по программе Шевелёва**.")
w("- Стояки В1 и К1 — у каждой квартиры свои (СП 30, п. 18.6; как в образце): 3 стояка В1 и 3 стояка К1 на секцию, "
  "секция 2 — зеркальная копия секции 1 относительно оси 11. Трасса — из модели Revit (`calc/trassa_v3.json`).")
w("- К1: стояки и поэтажные отводы — полипропилен ГОСТ 32414-2013 (Ø110, Ø50), присоединения приборов косыми тройниками 45°; "
  "в подвале и выпуски — чугун SML DN100, переход стояков двумя отводами 45° (п. 18.4); дворовая сеть — ПЭ гофрированная Ø160 "
  "(у Лукиных d = 150), n = 0,014.")
w(f"- Генплан (произвольно, как в образце): городские В1 Ø{D_GOR_V} и К1 Ø{D_GOR_K} у торца здания со стороны оси 1, "
  f"красная линия в {-X_KRASN:.0f} м от торца; 0,000 = {F(Z0_ABS, 2)}; земля 100,70 → 100,30 к городской сети.\n")

w("## 1. Расходы воды\n")
w("| Величина | Формула | Значение |\n|---|---|---|")
w(f"| Число жителей U | U₀·n_кв·n_эт·n_сек = 3,8·{N_KV}·{N_ET}·{N_SEK} | {U} чел. |")
w(f"| Число приборов N | {N_PR}·{N_KV}·{N_ET}·{N_SEK} | {N} шт. |")
w(f"| Суточный общий Q_сут^tot | 180·U/1000 | {F(rasx['Q_sut_tot'], 2)} м³/сут |")
w(f"| Суточный холодный Q_сут^c | (180−70)·U/1000 | {F(rasx['Q_sut_c'], 2)} м³/сут |")
w(f"| Среднечасовой q_T^c | Q_сут^c/24 | {F(rasx['q_T_c'], 3)} м³/ч |")
w(f"| P^tot | 11,6·U/(3600·N·0,3) | {F(P_tot, 5)} |")
w(f"| P^c | 5,1·U/(3600·N·0,2) | {F(P_c, 5)} |")
w(f"| q^tot (сек.) | 5·α·0,3, α = f({F(N * P_tot)}) = {F(rasx['a_tot'])} | {F(rasx['q_tot'])} л/с |")
w(f"| q^c (сек.) | 5·α·0,2, α = f({F(N * P_c)}) = {F(rasx['a_c'])} | {F(rasx['q_c'])} л/с |")
w(f"| P_hr^tot | P·3600·0,3/300 | {F(P_hr_tot, 5)} |")
w(f"| q_hr^tot | 0,005·α·300, α = f({F(N * P_hr_tot)}) = {F(rasx['a_hr_tot'])} | {F(rasx['q_hr_tot'])} м³/ч |")
w(f"| P_hr^c | P·3600·0,2/200 | {F(P_hr_c, 5)} |")
w(f"| q_hr^c | 0,005·α·200, α = f({F(N * P_hr_c)}) = {F(rasx['a_hr_c'])} | {F(rasx['q_hr_c'])} м³/ч |\n")

w("## 2. Гидравлический расчёт В1 (диктующее направление)\n")
w(f"Диктующий стояк — {ST_DIKT}: потери от тройника у насосной до верхнего прибора у него наибольшие "
  f"({', '.join(f'{nm}: {F(h, 2)} м' for nm, h in sorted(poteri.items(), key=lambda t: int(t[0].split('-')[1])))}). "
  f"Диктующий прибор — {DIKT} в квартире 11-го этажа на этом стояке. Сравнивались два кандидата "
  "(одинаковые слагаемые H_тр опущены):\n")
w("| Прибор | Высота над полом, м | Отметка, м | Σh, м | Отметка + Σh, м |\n|---|---|---|---|---|")
for k, vv in varianty.items():
    w(f"| {k} | {F(vv['z_pr'], 2)} | {F(vv['z'], 2)} | {F(vv['sum_h'], 2)} | {F(vv['z'] + vv['sum_h'], 2)} |")
w("")
w("| № | Участок | L, м | N | P^c | NP | α | q, л/с | DN | v, м/с | i | iL | h = iL(1+0,3) |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for u in v1:
    w(f"| {u['n']} | {u['imya']} | {F(u['L'], 2)} | {u['N']} | {F(u['P'], 5)} | {F(u['NP'], 4)} | {F(u['a'])} | {F(u['q'])} | {u['dn']} | {F(u['v'], 2)} | {F(u['i'], 4)} | {F(u['iL'], 3)} | {F(u['h'], 3)} |")
w(f"\nΣh по сети В1 = **{F(sum_h_v1, 2)} м**.\n")
w(f"**Ввод:** q^c = {F(rasx['q_c'])} л/с, ПЭ100 Ø{dn_vv}, v = {F(v_vv, 2)} м/с, i = {F(i_vv, 4)}, "
  f"L = {F(L_VVOD, 1)} м, h_ввод = {F(h_vvod, 2)} м. Два ввода не требуются: квартир {n_kv_vsego} < 400, пожарных кранов нет.\n")

w("## 3. Счётчики воды\n")
w("| Узел | Подбор по | DN | q_экспл, м³/ч | S | q, л/с | h = S·q², м | допустимо, м |\n|---|---|---|---|---|---|---|---|")
w(f"| Общедомовой | q_T = {F(rasx['q_T_c'])} м³/ч | {sch_dom[0]} | {F(sch_dom[1], 1)} | {sch_dom[2]} | {F(rasx['q_c'])} | {F(sch_dom[3], 2)} | {F(sch_dom[4], 1)} |")
w(f"| Квартирный (В1) | 4 прибора | 15 | 1,2 | 14,5 | {F(q_kv)} | {F(sch_kv[3], 2)} | 5,0 |")
w("\nОбщедомовой узел — с обводной линией (один ввод).\n")

w("## 4. Требуемый напор и насосная установка\n")
w(f"- Верх городской трубы: земля у ГВК {F(Z_ZEML_VVOD, 2)} − (1,7 + 0,5) = {F(z_gor_verh, 2)} м (отн.).")
w(f"- Диктующий прибор ({DIKT}): {N_ET - 1}·3,2 + {F(Z_DIKT, 2)} = {F(z_dikt, 2)} м.")
w(f"- H_geom = {F(z_dikt, 2)} − ({F(z_gor_verh, 2)}) = {F(H_geom, 2)} м.")
w(f"- H_тр = H_geom + Σh + H_св + ΣH_вод + h_ввод = {F(H_geom, 2)} + {F(sum_h_v1, 2)} + {F(H_SV, 1)} + {F(H_vod, 2)} + {F(h_vvod, 2)} = **{F(H_tr, 2)} м**.")
w(f"- H_гар = {F(H_GAR, 1)} м < H_тр → нужна повысительная установка: **H_р = {F(H_nas, 2)} м, Q = {F(rasx['q_c'])} л/с = {F(rasx['q_c'] * 3.6, 2)} м³/ч** "
  "(холодный расход: установка питает только В1). Подбор по каталогу — установка из 2 насосов (рабочий + резервный) с частотным регулированием.")
w(f"- Гидростатический напор у нижнего прибора без расхода ≈ {F(H_st_niz, 1)} м; на этажах {', '.join(map(str, et_reg)) or '—'} он больше 45 м → "
  "на поквартирных узлах этих этажей регуляторы давления (п. 8.22).\n" if et_reg else
  f"- Гидростатический напор у нижнего прибора ≈ {F(H_st_niz, 1)} м ≤ 45 м — регуляторы давления не требуются.\n")

w("## 5. К1: пропускная способность стояков\n")
w("| Стояк | N | NP^tot | α | q^tot, л/с | q^s = q^tot + 1,6 | Допустимо (К.1, ПП 110/110, 45°) | Вывод |\n|---|---|---|---|---|---|---|---|")
for s in k1_st:
    w(f"| {s['st']} | {s['N']} | {F(s['NP'], 4)} | {F(s['a'])} | {F(s['q_tot'])} | {F(s['q_s'])} | {F(s['q_dop'], 2)} | {'обеспечена' if s['ok'] else 'НЕ обеспечена'} |")
w("\nВытяжная часть стояков выводится выше кровли (здание выше 5 этажей).\n")

w("## 6. К1: горизонтальные участки, выпуск и дворовая сеть\n")
w("| Участок | L, м | N | P_hr^tot | α | q_hr, м³/ч | q₀s | K_s | q^sL, л/с | d | h/d | V, м/с | V√(h/d) | i | iL | Лоток: начало | конец | Тип |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for u in k1_vnutr + dvor:
    w(f"| {u['imya']} | {F(u['L'], 2)} | {u['N']} | {F(u['P'], 5)} | {F(u['a'])} | {F(u['q_hr'])} | {F(u['q0s'], 1)} | {F(u['Ks'], 2)} | {F(u['q'], 2)} | {u['d']} | {F(u['hd'], 2)} | {F(u['v'], 2)} | {F(u['K'], 2)} | {F(u['i'], 3)} | {F(u['iL'], 3)} | {F(u['nach'], 2)} | {F(u['kon'], 2)} | {u['tip']} |")
w("\n**Отметки дворовой сети (абс.)**\n")
w("| Точка | Земля | Лоток | Глубина |\n|---|---|---|---|")
w(f"| Выпуск у стены | — | {F(lotok['выпуск у стены'], 2)} | — |")
for k in ("КК-1", "КК-2", "КК-3", "ККК", "ГКК"):
    w(f"| {k} | {F(zeml[k], 2)} | {F(lotok[k], 2)} | {F(glub[k], 2)} |")
w(f"\nНаименьшая глубина лотка H₀ = max(H_пр − 0,3; 0,7 + d) = max(1,7 − 0,3; 0,7 + 0,15) = {F(min_glub, 2)} м: "
  f"{'выполняется' if min(glub.values()) >= min_glub else 'НЕ выполняется'} во всех колодцах. "
  f"Выпуск секции 1 (такой же, лоток у стены −2,000) приходит в КК-3 {'не ниже шелыги дворовой трубы' if vyp_v_kk3_ok else 'НИЖЕ шелыги дворовой трубы'}. "
  "Наибольшее расстояние между колодцами 35 м (d = 150) соблюдено: промежуточный КК-2 у стыка секций. "
  f"Лоток городского коллектора Ø400 в ГКК («по месту») принят {F(Z_GKK_GOR, 2)}, шелыга {F(Z_GKK_GOR + 0.4, 2)}; "
  f"дворовая труба входит выше шелыги на {F(perepad_gkk, 2)} м.\n")

with open(os.path.join(HERE, "..", "RASCHET_V3.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
with open(os.path.join(HERE, "rezultaty_v3.json"), "w", encoding="utf-8") as f:
    json.dump(dict(U=U, N=N, rasx=rasx, P=dict(tot=P_tot, c=P_c, hr_tot=P_hr_tot, hr_c=P_hr_c), v1=v1,
                   vvod=dict(dn=dn_vv, v=v_vv, i=i_vv, h=h_vvod), schetchik_dom=sch_dom, H_tr=H_tr, H_nas=H_nas,
                   et_reg=et_reg, k1_stoyaki=k1_st, k1=k1_vnutr + dvor, lotok=lotok, zeml=zeml, stoyaki_v1=ST_V1, st_dikt=ST_DIKT, poteri_st=poteri,
                   dikt=DIKT, varianty={k: dict(z=vv["z"], z_pr=vv["z_pr"], sum_h=vv["sum_h"]) for k, vv in varianty.items()},
                   z_gor_verh=z_gor_verh, z_dikt=z_dikt, H_geom=H_geom, H_vod=H_vod, sch_kv=sch_kv, q_kv=q_kv,
                   L_vvod=L_VVOD, H_st_niz=H_st_niz, glub=glub, min_glub=min_glub, perepad_gkk=perepad_gkk,
                   Z_GKK_GOR=Z_GKK_GOR, Z0_ABS=Z0_ABS, n_kv=n_kv_vsego, N_KV=N_KV, U0=U0, sum_h_v1=sum_h_v1,
                   iznach=dict(N_SEK=N_SEK, N_ET=N_ET, H_ET=H_ET, H_PODVAL=H_PODVAL, T_PEREKR=T_PEREKR, DH_POL=DH_POL,
                               H_PROMERZ=H_PROMERZ, H_GAR=H_GAR, D_GOR_V=D_GOR_V, D_GOR_K=D_GOR_K)),
              f, ensure_ascii=False, indent=1)
print("\n".join(L))
