"""Геометрия модели варианта 3 для Revit: оси, уровни, стены, окна, перекрытия, приборы, трубопроводы.

Запуск: py geometriya_v3.py  ->  geometriya_v3.json (читают кнопки вкладки «Курсовой ВиВ»).

Система координат: X вдоль здания от оси 1 секции 1, Y от оси А, Z от 0,000; всё в метрах.
Секция 2 — копия секции 1, сдвинутая на 22,5 м (пристроена по оси 11). План снят с растрового плана задания
(kursovoy-viv/pz/plan_v3.png, масштаб ≈ 54,4 px/м); положения стояков и магистралей — как в calc/raschet_v3.py.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REZ = json.load(open(os.path.join(HERE, "..", "calc", "rezultaty_v3.json"), encoding="utf-8"))
IZ = REZ["iznach"]

L_SEK = 22.5
N_SEK, N_ET, H_ET = IZ["N_SEK"], IZ["N_ET"], IZ["H_ET"]
OSI_X = [0.0, 3.5, 6.5, 9.2, 10.0, 12.5, 13.7, 15.7, 16.5, 19.0, 22.5]      # оси 1-11 секции
OSI_Y = [("А", 0.0), ("Б", 1.3), ("В", 6.8), ("Г", 11.3), ("Д", 12.8)]
B = 12.8                      # ширина в осях
L = L_SEK * N_SEK             # длина в осях

# ---------------- уровни ----------------
urovni = [dict(imya="Подвал", z=-IZ["H_PODVAL"])]
urovni += [dict(imya="Этаж %02d" % k, z=round((k - 1) * H_ET, 3)) for k in range(1, N_ET + 1)]
urovni.append(dict(imya="Кровля", z=round(N_ET * H_ET, 3)))
ETAZHI = [u["imya"] for u in urovni if u["imya"].startswith("Этаж")]

# ---------------- оси ----------------
osi = []
for s in range(N_SEK):
    for k, x in enumerate(OSI_X):
        nom = s * (len(OSI_X) - 1) + k + 1
        if s > 0 and k == 0:
            continue                       # ось 1 секции 2 = ось 11 секции 1
        osi.append(dict(imya=str(nom), p1=[s * L_SEK + x, -2.5], p2=[s * L_SEK + x, B + 2.5]))
for nm, y in OSI_Y:
    osi.append(dict(imya=nm, p1=[-2.5, y], p2=[L + 2.5, y]))

# ---------------- стены ----------------
# Наружные: ось проходит в 200 мм от внутренней грани, стена 520 -> ось стены смещена наружу на 60 мм.
E = 0.06
# обход по часовой стрелке: так Revit считает наружной стороной стены внешнюю (иначе окна не режут проём)
kontur = [(-E, -E), (-E, B + E), (L + E, B + E), (L + E, -E)]
steny = []


def stena(p1, p2, tip, gde):
    steny.append(dict(p1=[round(p1[0], 3), round(p1[1], 3)], p2=[round(p2[0], 3), round(p2[1], 3)], tip=tip, gde=gde))


for i in range(4):
    stena(kontur[i], kontur[(i + 1) % 4], "nar", "etazhi")
    stena(kontur[i], kontur[(i + 1) % 4], "fund", "podval")

YV = 6.85                     # ось несущей стены по оси В (420 мм): грани 6,64 и 7,06
VN, VV = YV - 0.21, YV + 0.21
Y_IN0, Y_IN1 = 0.2, B - 0.2   # внутренние грани наружных стен


def sekciya(ox, posl):
    """Стены одной секции; posl — последняя секция (её ось 11 — наружная стена)."""
    def w(x1, y1, x2, y2, tip, gde="etazhi"):
        stena((ox + x1, y1), (ox + x2, y2), tip, gde)
    # несущие 420
    for x1, x2 in ((0.2, 2.3), (3.1, 8.4), (9.15, 17.6), (18.7, 22.3)):
        w(x1, YV, x2, YV, "nes", "vse")
    for x in (3.5, 19.0):
        w(x, Y_IN0, x, VN, "nes", "vse")
        w(x, VV, x, Y_IN1, "nes", "vse")
    if not posl:
        w(22.5, Y_IN0, 22.5, Y_IN1, "nes", "vse")
    for x in (9.2, 13.7):                       # лестнично-лифтовой узел
        w(x, Y_IN0, x, VN, "nes", "vse")
    # шахта лифта
    for a, b in (((9.4, 3.4), (10.9, 3.4)), ((10.9, 3.4), (10.9, 5.6)), ((10.9, 5.6), (9.4, 5.6))):
        w(a[0], a[1], b[0], b[1], "beton", "vse")
    # перегородки этажей
    per = [((6.5, Y_IN0), (6.5, VN)), ((6.5, VV), (6.5, Y_IN1)), ((9.2, VV), (9.2, Y_IN1)), ((12.5, VV), (12.5, Y_IN1)),
           ((0.2, 1.3), (3.3, 1.3)), ((3.7, 1.3), (6.4, 1.3)), ((19.2, 1.3), (22.3, 1.3)),
           ((0.2, 11.3), (3.3, 11.3)), ((19.2, 11.3), (22.3, 11.3)),
           # санузел кв. 1 (оси 1-2 / Б-В): перегородки примыкают к коробу у наружной стены
           ((2.05, 4.15), (2.05, VN)), ((0.43, 4.15), (2.1, 4.15)), ((0.43, 5.85), (1.55, 5.85)),
           # санузлы кв. 2 и 3 (оси 7-9 / В-Г) и шахта между ними по оси 8
           ((13.6, VV), (13.6, 9.55)), ((13.6, 9.55), (15.22, 9.55)), ((15.5, VV), (15.5, 10.5)),
           ((15.8, VV), (15.8, 10.5)), ((16.08, 9.55), (17.7, 9.55)), ((17.7, VV), (17.7, 9.55))]
    for a, b in per:
        w(a[0], a[1], b[0], b[1], "per")
    # короба (зашивка ГКЛВ 50 мм) с трубопроводами вдоль стен санузлов, как в образце
    for a, b in (((0.405, 3.20), (0.405, VN)), ((15.245, VV), (15.245, 10.5)), ((16.055, VV), (16.055, 10.5))):
        w(a[0], a[1], b[0], b[1], "korob")
    # подвал: насосная и водомерный узел в осях 2-4 / Б-В секции 1
    if ox == 0:
        w(3.7, 1.3, 8.99, 1.3, "per", "podval")


for s in range(N_SEK):
    sekciya(s * L_SEK, s == N_SEK - 1)

# ---------------- окна и двери ----------------
okna = []
for s in range(N_SEK):
    ox = s * L_SEK
    for x in (1.75, 5.0, 8.1, 11.2, 14.0, 17.2, 20.7):
        okna.append(dict(x=ox + x, y=B + E, tip="okno", gde="etazhi"))
    for x in (1.75, 5.0, 7.7, 14.7, 17.4, 20.7):
        okna.append(dict(x=ox + x, y=-E, tip="okno", gde="etazhi"))
    okna.append(dict(x=ox + 11.3, y=-E, tip="dver_vh", gde="Этаж 01"))

# ---------------- перекрытия ----------------
perekr = [dict(uroven=u, kontur=kontur, tip="perekr") for u in ETAZHI]
perekr.append(dict(uroven="Подвал", kontur=kontur, tip="pol_podv"))
krovlya = dict(uroven="Кровля", kontur=kontur, tip="krovlya")

# ================= ПРИБОРЫ И СЕТИ =================
import math
import sys

sys.path.insert(0, os.path.join(HERE, "..", "calc"))
from normy import alpha_b2          # noqa: E402

P_C = REZ["P"]["c"]
N_PR = 4
ET_REG = set(REZ["et_reg"])          # этажи с регуляторами давления на квартирных вводах
VGP = {15: 15.7, 20: 21.2, 25: 27.1, 32: 35.9, 40: 41.0, 50: 53.0}


def shevelev(q, dn):
    d = (VGP[dn] - 1.0) / 1000
    v = q / 1000 / (math.pi * d * d / 4)
    return v


def dn_stoyaka(n):
    """Диаметр стояка В1 по числу приборов выше сечения — тем же правилом, что в raschet_v3.py."""
    q = 5 * alpha_b2(n * P_C, "floor") * 0.2
    for dn in (25, 32, 40, 50):
        if shevelev(q, dn) <= 1.2:
            return dn
    return 50


pribory, seti, troyniki, kresty, armatura, svyazi, mufty, stoyaki = [], [], [], [], [], [], [], []

# соединители приборов, мм, в системе семейства (журнал кнопки «02»)
SOED = {"vanna": dict(cold=(-12, 425, 700), san=(200, 350, 95)),          # ВСт 1500
        "unitaz": dict(cold=(-200, -95, 700), san=(0, -70, 180)),
        "umyv": dict(cold=(12, -75, 800), san=(57, -180, 558)),
        "moyka": dict(cold=(407, -30, 850), san=(352, -130, 558))}
# Холодная вода подводится слева (если смотреть на прибор спереди) — как в образце и по СП 30 (холодная левее
# горячей). У умывальника, мойки и ванны ADSK холодная справа -> экземпляры отражаются относительно оси симметрии.
ZERKALO = {"umyv": ("x", 0.0), "moyka": ("x", 400.0), "vanna": ("y", 350.0)}
# габариты по журналу «00 Диагностика» (min x, min y, min z, max x, max y, max z), мм, без отражения
GABARIT = {"vanna": (-12, 0, 0, 1500, 700, 550), "unitaz": (-200, -660, 0, 200, 0, 750),
           "umyv": (-275, -420, 0, 275, 0, 915), "moyka": (0, -490, 0, 800, 35, 965)}
PR_FAM = {"vanna": ("ADSK_Ванна стальная эмалированная_ГОСТ23695-2016", "ВСт 1500"),
          "unitaz": ("ADSK_Унитаз напольный_ГОСТ 30493-2017", "Прямой выпуск"),
          "umyv": ("ADSK_Умывальник со смесителем", "Умывальник"),
          "moyka": ("ADSK_Мойка кухонная со смесителем", "Мойка кухонная со смесителем и сифоном")}
# арматура: семейство, тип, x соединителя «вход» и «выход» по локальной оси X, м
ARM = {"kran15": ("VALTEC_VT.214.N_КранШаровой ВР", '1/2"', -0.024, 0.024),
       "kran25": ("VALTEC_VT.214.N_КранШаровой ВР", '1"', -0.032, 0.032),
       "kran32": ("VALTEC_VT.214.N_КранШаровой ВР", '1 1/4"', -0.036, 0.036),
       "kran50": ("VALTEC_VT.214.N_КранШаровой ВР", '2"', -0.050, 0.049),
       "filtr15": ("ADSK_Фильтр механический сетчатый муфтовый ВР", "Фильтр сетчатый муфтовый ВР-ВР", -0.016, 0.016),
       "sch15": ("Квартирный счетчик воды_Пульсар",
                 "Квартирный счетчик воды Ду15 без интерфейса, Qn=1,5 м3/ч, L=110мм (присоединители в комплекте)",
                 -0.055, 0.055),
       "reg15": ("VALTEC_VT.089.N_Редуктор давления мембранный", "DN 15", -0.041, 0.0)}


def R(v):
    return [round(c, 4) for c in v]


def rot(x, y, th):
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    return x * c - y * s, x * s + y * c


def mir_lok(key, lx, ly):
    """Локальные координаты (мм) с учётом отражения экземпляра."""
    if key in ZERKALO:
        os_, c = ZERKALO[key]
        if os_ == "x":
            lx = 2 * c - lx
        else:
            ly = 2 * c - ly
    return lx, ly


gabarity_pr = []          # (id, x0, y0, x1, y1, z0, z1) — для проверки коллизий


def pribor(key, x, y, th, ur, zf):
    pid = len(pribory)
    zk = ZERKALO.get(key)
    pribory.append(dict(id=pid, fam=PR_FAM[key][0], tip=PR_FAM[key][1], x=round(x, 4), y=round(y, 4), th=th, ur=ur,
                        mir=dict(os=zk[0], c=zk[1] / 1000) if zk else None))
    c = {}
    for k, (lx, ly, lz) in SOED[key].items():
        lx, ly = mir_lok(key, lx, ly)
        dx, dy = rot(lx / 1000, ly / 1000, th)
        c[k] = (x + dx, y + dy, zf + lz / 1000)
    g = GABARIT[key]
    xs, ys = [], []
    for lx in (g[0], g[3]):
        for ly in (g[1], g[4]):
            mx, my = mir_lok(key, lx, ly)
            dx, dy = rot(mx / 1000, my / 1000, th)
            xs.append(x + dx)
            ys.append(y + dy)
    gabarity_pr.append((pid, min(xs), min(ys), max(xs), max(ys), zf + g[2] / 1000, zf + g[5] / 1000))
    return pid, c


def truba(sys_, pt, d, pts, ur):
    rid = len(seti)
    seti.append(dict(id=rid, sys=sys_, pt=pt, d=d, pts=[R(p) for p in pts], ur=ur))
    return rid


def svyaz(a, b):
    svyazi.append(dict(a=a, b=b))


def troynik(m1, m2, b):
    troyniki.append(dict(m1=m1, m2=m2, b=b))


def arm(key, p, d, ur):
    """Арматура с соединителем «вход» в точке p, ось по направлению d. Возвращает id и точку «выхода»."""
    fam, tip, xin, xout = ARM[key]
    th = math.degrees(math.atan2(d[1], d[0]))
    ins = (p[0] - d[0] * xin, p[1] - d[1] * xin, p[2])
    out = (ins[0] + d[0] * xout, ins[1] + d[1] * xout, p[2])
    aid = len(armatura)
    armatura.append(dict(id=aid, key=key, fam=fam, tip=tip, x=round(ins[0], 4), y=round(ins[1], 4), z=round(ins[2], 4),
                         th=round(th, 3), ur=ur))
    return aid, out


def vetka(sys_, pt, d, pts_do, napr, items, ur, gap=0.03, first=0.07):
    """Ветка: ломаная pts_do, затем арматура items подряд по направлению napr.
    Возвращает (id первой трубы, (id последней арматуры, точка её выхода))."""
    p = pts_do[-1]
    p_in = (p[0] + napr[0] * first, p[1] + napr[1] * first, p[2])
    r0 = truba(sys_, pt, d, pts_do + [p_in], ur)
    prev = (r0, 1)
    for key in items:
        aid, out = arm(key, p_in, napr, ur)
        svyaz(prev, dict(arm=aid, side="in"))
        p_in = (out[0] + napr[0] * gap, out[1] + napr[1] * gap, out[2])
        r = truba(sys_, pt, d, [out, p_in], ur)
        svyaz((r, 0), dict(arm=aid, side="out"))
        prev = (r, 1)
    return r0, prev, p_in


Z_RAZV = 0.3        # ось поквартирной разводки над полом
Z_UZEL = 1.0        # квартирный узел учёта (стояк -> кран -> фильтр -> счётчик -> регулятор)
I_OTV = 0.03        # уклон поэтажных отводов Ø50
I_UN = 0.02         # уклон отвода от унитаза Ø110
Z_TR50 = -0.06      # тройник стояка для отвода Ø50 (в конструкции пола)


def otvod50(tochki, z_end, ur):
    """Отвод Ø50 по точкам (x, y) от дальнего прибора к стояку с уклоном I_OTV; z_end — у стояка."""
    L = [0.0]
    for a, b in zip(tochki[:-1], tochki[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    tot = L[-1]
    return [(x, y, z_end + I_OTV * (tot - s)) for (x, y), s in zip(tochki, L)]


def z_na(pts3, x, y):
    """z отвода в точке (x, y), лежащей на одном из его отрезков."""
    for a, b in zip(pts3[:-1], pts3[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        t = math.hypot(x - a[0], y - a[1])
        if L > 0 and abs(t + math.hypot(b[0] - x, b[1] - y) - L) < 1e-6:
            return a[2] + (b[2] - a[2]) * t / L
    raise ValueError((x, y))


def razrezat(sys_, pt, d, pts3, rez, ur):
    """Разбить ломаную pts3 в точках rez (x, y) под тройники. Возвращает список id труб по порядку."""
    out, cur = [], [pts3[0]]
    for a, b in zip(pts3[:-1], pts3[1:]):
        na_otr = []
        for (x, y) in rez:
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            t = math.hypot(x - a[0], y - a[1])
            if L > 0 and 1e-6 < t < L - 1e-6 and abs(t + math.hypot(b[0] - x, b[1] - y) - L) < 1e-6:
                na_otr.append((t, (x, y, a[2] + (b[2] - a[2]) * t / L)))
        for _, p in sorted(na_otr):
            cur.append(p)
            out.append(truba(sys_, pt, d, cur, ur))
            cur = [p]
        cur.append(b)
    out.append(truba(sys_, pt, d, cur, ur))
    return out


fid_utopl = set()        # округлённые координаты соединителей, утопленных в обшивку короба (ванны)


def nogi(xh, y0, z, ftaps, ur):
    """Ветка разводки от тройника (xh, y0, z) вдоль оси Y; ftaps — [(соединитель, id прибора)] по порядку.
    Последний прибор — конец ветки, к остальным — подводки от тройников. Возвращает id первой трубы."""
    ids, uzly, cur = [], [], [(xh, y0, z)]

    def k_priboru(p, conn):
        # подъём под соединителем; если соединитель утоплен в обшивку короба (ванна) — подъём внутри короба
        # в 70 мм от соединителя и выход к смесителю горизонтально сквозь обшивку
        if tuple(round(v, 4) for v in conn) in fid_utopl:
            xv = conn[0] - math.copysign(0.07, conn[0] - xh)
            return [p, (xv, conn[1], z), (xv, conn[1], conn[2]), conn]
        return [p, (conn[0], conn[1], z), conn]
    for i, (conn, fid) in enumerate(ftaps):
        p = (xh, conn[1], z)
        if i < len(ftaps) - 1:
            cur.append(p)
            ids.append(truba("V1", "stal", 15, cur, ur))
            uzly.append((p, conn, fid))
            cur = [p]
        else:
            cur += k_priboru(p, conn)
            ids.append(truba("V1", "stal", 15, cur, ur))
            svyaz((ids[-1], 1), dict(fix=fid, kind="cold"))
    for i, (p, conn, fid) in enumerate(uzly):
        rb = truba("V1", "stal", 15, k_priboru(p, conn), ur)
        troynik((ids[i], 1), (ids[i + 1], 0), (rb, 0))
        svyaz((rb, 1), dict(fix=fid, kind="cold"))
    return ids[0]


def kv_v1(k, zf, ur, rs_v, pre, napr, post, xh, ytr, yug, sever):
    """Квартирный ввод: тройник на стояке, узел учёта, опуск к разводке, две ветки от тройника."""
    z1 = pre[0][2]
    items = ["kran15", "filtr15", "sch15"] + (["reg15"] if k in ET_REG else [])
    r0, (ra, _), p = vetka("V1", "stal", 15, pre, napr, items, ur)
    rs_v.append((z1, (r0, 0)))
    seti[ra]["pts"] = seti[ra]["pts"][:1] + [R(q) for q in post] + [R((xh, ytr, zf + Z_RAZV))]
    a = nogi(xh, ytr, zf + Z_RAZV, yug, ur)
    b = nogi(xh, ytr, zf + Z_RAZV, sever, ur)
    troynik((a, 0), (b, 0), (ra, 1))


def otvod_k1(x_l, y_r, z_r, napr, pr, ur):
    """Поэтажный отвод Ø50 вдоль x = x_l к стояку (x_l, y_r) с уклоном I_OTV. Приборы pr = [(соединитель, id)],
    первый — дальний (начало отвода). Присоединения — опуск и косой участок 45° в плане (косой тройник)."""
    def zl(y):
        return z_r + I_OTV * abs(y - y_r)
    J = [(conn[1] + napr * abs(conn[0] - x_l), abs(conn[0] - x_l)) for conn, _ in pr]
    (c0, f0), (y0, dl0) = pr[0], J[0]
    zA = min(c0[2], zl(y0) + I_OTV * dl0 * math.sqrt(2))
    pts = [c0, (c0[0], c0[1], zA), (x_l, y0, zl(y0)), (x_l, y_r, z_r)]
    rr = razrezat("K1", "pp", 50, pts, [(x_l, yj) for yj, _ in J[1:]], ur)
    svyaz((rr[0], 0), dict(fix=f0, kind="san"))
    for i, ((conn, fid), (yj, dl)) in enumerate(zip(pr[1:], J[1:])):
        zs = min(conn[2], zl(yj) + I_OTV * dl * math.sqrt(2))
        st_ = truba("K1", "pp", 50, [conn, (conn[0], conn[1], zs), (x_l, yj, zl(yj))], ur)
        svyaz((st_, 0), dict(fix=fid, kind="san"))
        troynik((rr[i], 1), (rr[i + 1], 0), (st_, 1))
    return rr[-1]


def unitaz_k1(ct, pt_, xk, yk, ur):
    zt = ct["san"][2] - I_UN * math.hypot(ct["san"][0] - xk, ct["san"][1] - yk)
    r = truba("K1", "pp", 110, [ct["san"], (xk, yk, zt)], ur)
    svyaz((r, 0), dict(fix=pt_, kind="san"))
    return zt, r


def kvartira_1(ox, zf, ur, k, st_s):
    """Квартира 1, санузел в осях 1-2 / Б-В: приборы вдоль короба у наружной стены (оси 1), стояки в коробе."""
    pu, cu = pribor("umyv", ox + 0.43, 4.55, 90, ur, zf)
    pv, cv = pribor("vanna", ox + 0.442, 5.10, 0, ur, zf)
    fid_utopl.add(tuple(round(v, 4) for v in cv["cold"]))
    pm, cm = pribor("moyka", ox + 0.465, 3.25, 90, ur, zf)
    pt_, ct = pribor("unitaz", ox + 0.43, 6.25, 90, ur, zf)
    xr, yr, z1 = ox + 0.225, 6.52, zf + Z_UZEL
    kv_v1(k, zf, ur, st_s["v1"], [(xr, yr, z1)], (0, -1), [(xr, 5.97, z1)], xr, 5.97,
          [(cv["cold"], pv), (cu["cold"], pu), (cm["cold"], pm)], [(ct["cold"], pt_)])
    xk, yk = ox + 0.31, 6.25
    zt, r_un = unitaz_k1(ct, pt_, xk, yk, ur)
    st_s["k1"].append((zt, [(r_un, 1)]))
    last = otvod_k1(xk, yk, zf + Z_TR50, +1, [(cm["san"], pm), (cu["san"], pu), (cv["san"], pv)], ur)
    st_s["k1"].append((zf + Z_TR50, [(last, 1)]))


def kvartiry_23(ox, zf, ur, k, st_s):
    """Квартиры 2 и 3: санузлы в осях 7-9 / В-Г. Между ними шахта по оси 8 со стояком В1 (общий, по расчёту);
    стояки К1 у каждой квартиры свои (СП 30, п. 18.6) — в коробах вдоль стен шахты."""
    xv, yv = ox + 15.65, 7.85
    for kv, th, xyu, xyv, thv, xym, xyt, xa, xh, xk, z_uz, napr_x in (
            (2, -90, (15.22, 8.65), (15.208, 8.32), 180, (15.185, 10.45), (15.22, 7.35), 15.59, 15.435, 15.35,
             Z_UZEL, -1),
            (3, 90, (16.08, 8.65), (16.092, 7.62), 0, (16.115, 9.65), (16.08, 7.35), 15.71, 15.865, 15.95,
             Z_UZEL + 0.15, 1)):
        pu, cu = pribor("umyv", ox + xyu[0], xyu[1], th, ur, zf)
        pv, cv = pribor("vanna", ox + xyv[0], xyv[1], thv, ur, zf)
        fid_utopl.add(tuple(round(v, 4) for v in cv["cold"]))
        pm, cm = pribor("moyka", ox + xym[0], xym[1], th, ur, zf)
        pt_, ct = pribor("unitaz", ox + xyt[0], xyt[1], th, ur, zf)
        z1 = zf + z_uz
        xa_, xh_, xk_ = ox + xa, ox + xh, ox + xk
        kv_v1(k, zf, ur, st_s["v2"], [(xv, yv, z1), (xa_, yv, z1)], (0, 1), [(xa_, 8.50, z1), (xh_, 8.50, z1)],
              xh_, 8.50, [(cv["cold"], pv), (ct["cold"], pt_)], [(cu["cold"], pu), (cm["cold"], pm)])
        yk = 7.35
        zt, r_un = unitaz_k1(ct, pt_, xk_, yk, ur)
        key = "k%d" % kv
        st_s[key].append((zt, [(r_un, 1)]))
        last = otvod_k1(xk_, yk, zf + Z_TR50, -1, [(cm["san"], pm), (cu["san"], pu), (cv["san"], pv)], ur)
        st_s[key].append((zf + Z_TR50, [(last, 1)]))


def stoyak(imya, sys_, x, y, uzly, niz, verh, ur_niz, d_fun, pt):
    """Стояк: трубы между узлами; узел (z, [концы ответвлений]) -> тройник (1 ответвление) или крестовина (2).
    niz/verh — z концов стояка. d_fun(i) — диаметр участка выше i-го узла."""
    uzly = sorted(uzly, key=lambda u: u[0])
    zz = [niz] + [u[0] for u in uzly] + [verh]
    runs = []
    for i in range(len(zz) - 1):
        if zz[i + 1] - zz[i] < 1e-6:
            continue
        runs.append(truba(sys_, pt, d_fun(i), [(x, y, zz[i]), (x, y, zz[i + 1])], ur_niz(zz[i])))
    for i, (z, vetv) in enumerate(uzly):
        a, b = runs[i], runs[i + 1] if i + 1 < len(runs) else None
        if b is None:                                   # верхний узел — отвод вместо тройника
            svyaz((a, 1), vetv[0])
        elif len(vetv) == 1:
            troynik((a, 1), (b, 0), vetv[0])
        else:
            kresty.append(dict(m1=(a, 1), m2=(b, 0), b1=vetv[0], b2=vetv[1]))
    stoyaki.append(dict(imya=imya, sys=sys_, x=round(x, 4), y=round(y, 4), niz=round(niz, 3), verh=round(verh, 3),
                        runs=runs))
    return runs


def ur_po_z(z):
    k = int(math.floor((z + 1e-6) / H_ET)) + 1
    return "Подвал" if z < -1e-6 else "Этаж %02d" % min(max(k, 1), N_ET)


# ---------------- этажи ----------------
K1_ST = [(0.31, 6.25), (15.35, 7.35), (15.95, 7.35)]       # стояки К1 секции: кв. 1, 2, 3
st = {}
for s in range(N_SEK):
    ox = s * L_SEK
    st[s] = dict(v1=[], v2=[], k1=[], k2=[], k3=[])
    for k in range(1, N_ET + 1):
        zf, ur = (k - 1) * H_ET, "Этаж %02d" % k
        kvartira_1(ox, zf, ur, k, st[s])
        kvartiry_23(ox, zf, ur, k, st[s])
        # противопожарные муфты под перекрытиями, через которые проходят полимерные стояки К1 (п. 18.9 СП 30)
        for (xk, yk) in K1_ST:
            mufty.append(dict(x=ox + xk, y=yk, z=round(zf + H_ET - IZ["T_PEREKR"] - 0.05, 3), ur=ur))

# ---------------- подвал: магистраль, ввод, насосная, выпуски ----------------
Z_MAG = -0.6
Y_MAG = 7.60
UR_P = "Подвал"
Z_P = -IZ["H_PODVAL"]
Z_KR = N_ET * H_ET                     # верх перекрытия последнего этажа (плоская кровля)
VYTYAZHKA = 0.2                        # вытяжная часть над неэксплуатируемой кровлей

# стояки В1: нижний конец — на отметке магистрали, внизу отвод к ответвлению от магистрали
podvod = {}
for s in range(N_SEK):
    ox = s * L_SEK
    for nom, (x, y), key, kv in ((1, (ox + 0.225, 6.52), "v1", 1), (2, (ox + 15.65, 7.85), "v2", 2)):
        uzly = [(z, [b]) for z, b in st[s][key]]
        n_vsego = N_PR * kv * N_ET

        def d_fun(i, uzly=uzly, kv=kv):
            vyshe = N_PR * (len(uzly) - i)            # приборов выше i-го узла (узел = квартира)
            return dn_stoyaka(vyshe if i > 0 else N_PR * kv * N_ET)
        imya = "Ст.В1-%d" % (s * 2 + nom)
        runs = stoyak(imya, "V1", x, y, uzly, Z_MAG, max(z for z, _ in uzly), ur_po_z, d_fun, "stal")
        podvod[imya] = (x, y, runs[0], d_fun(0), n_vsego)

# магистраль: тройник у насосной (4,0; Y_MAG), на восток к стоякам 2, 3, 4, на запад к стояку 1
X_TR = 4.0
x_st = {nm: podvod[nm][0] for nm in podvod}
vostok = sorted([nm for nm in podvod if x_st[nm] > X_TR], key=lambda nm: x_st[nm])
zapad = [nm for nm in podvod if x_st[nm] < X_TR]
n_st = {nm: podvod[nm][4] for nm in podvod}


def dn_mag(n):
    q = 5 * alpha_b2(n * P_C, "floor") * 0.2
    for dn in (32, 40, 50):
        if shevelev(q, dn) <= 1.2:
            return dn
    return 50


def otvetvlenie(nm, ot_mag_y):
    """Ответвление от магистрали к стояку: кран у основания стояка и отвод вверх."""
    x, y, r_st, d, n = podvod[nm]
    napr = (0, 1) if y > ot_mag_y else (0, -1)
    kran = {25: "kran25", 32: "kran32"}.get(d, "kran32")
    r0, (ra, _), p = vetka("V1", "stal", d, [(x, ot_mag_y, Z_MAG)], napr, [kran], UR_P, first=0.06)
    seti[ra]["pts"] = seti[ra]["pts"][:1] + [R((x, y, Z_MAG))]
    svyaz((ra, 1), (r_st, 0))
    return r0


prev_end, ost = None, sum(n_st.values()) - sum(n_st[nm] for nm in zapad)
x_prev = X_TR
mag_vost = []
for i, nm in enumerate(vostok):
    x = x_st[nm]
    posl = i == len(vostok) - 1
    r = truba("V1", "stal", dn_mag(ost), [(x_prev, Y_MAG, Z_MAG), (x, Y_MAG, Z_MAG)], UR_P)
    mag_vost.append(r)
    ost -= n_st[nm]
    if prev_end is not None:
        troynik(prev_end, (r, 0), (otvetvlenie(vostok[i - 1], Y_MAG), 0))
    prev_end = (r, 1)
    x_prev = x
svyaz(prev_end, (otvetvlenie(vostok[-1], Y_MAG), 0))
nm_z = zapad[0]
r_zap = truba("V1", "stal", dn_mag(n_st[nm_z]), [(X_TR, Y_MAG, Z_MAG), (x_st[nm_z], Y_MAG, Z_MAG)], UR_P)
svyaz((r_zap, 1), (otvetvlenie(nm_z, Y_MAG), 0))

# напорная линия от насосной установки, ответвление на ГВС (в ИТП), тройник магистрали
nas = json.load(open(os.path.join(HERE, "..", "calc", "nasos_v3.json"), encoding="utf-8"))
XP, YP = 5.0, 4.0                       # установка COR-2 (соединители коллекторов на локальной -X)
p_vs = (XP, YP - 0.361, Z_P + 0.168)
p_nap = (XP, YP + 0.480, Z_P + 0.168)
oborud = [dict(fam="COR-MVL_2_32_Revit2019(08.25)", tip=nas["tip"], x=XP, y=YP, th=0, ur=UR_P,
               vs=R(p_vs), nap=R(p_nap))]
Y_GVS = 5.5
r_n1 = truba("V1", "stal", 50, [p_nap, (X_TR, p_nap[1], p_nap[2]), (X_TR, p_nap[1], Z_MAG), (X_TR, Y_GVS, Z_MAG)],
             UR_P)
svyaz((r_n1, 0), dict(obor=0, kind="nap"))
r_n2 = truba("V1", "stal", 40, [(X_TR, Y_GVS, Z_MAG), (X_TR, Y_MAG, Z_MAG)], UR_P)
r_gvs = truba("V1", "stal", 40, [(X_TR, Y_GVS, Z_MAG), (X_TR - 0.6, Y_GVS, Z_MAG)], UR_P)
troynik((r_n1, 1), (r_n2, 0), (r_gvs, 0))
troynik((r_zap, 0), (mag_vost[0], 0), (r_n2, 1))

# ввод ПЭ100 Ø63 через стену по оси А, водомерный узел с обводной линией, всас установки
Z_VV = -2.5
Y_ST_A = -E - 0.26                      # наружная грань стены по оси А
r_vv = truba("V1", "pe", 63, [(X_TR, Y_ST_A - 2.0, Z_VV), (X_TR, Y_IN0, Z_VV)], UR_P)
Z_VU = -2.0
r_v1 = truba("V1", "stal", 50, [(X_TR, Y_IN0, Z_VV), (X_TR, 1.5, Z_VV), (X_TR, 1.5, Z_VU), (X_TR, 1.8, Z_VU)], UR_P)
svyaz((r_vv, 1), (r_v1, 0))
# основная линия узла: кран - участок под счётчик DN40 - кран
r_a, (r_b, _), p = vetka("V1", "stal", 50, [(X_TR, 1.8, Z_VU)], (0, 1), ["kran50"], UR_P, first=0.15)
seti[r_b]["pts"] = seti[r_b]["pts"][:1] + [R((X_TR, 2.12, Z_VU))]
r_sch = truba("V1", "stal", 40, [(X_TR, 2.12, Z_VU), (X_TR, 2.62, Z_VU)], UR_P)      # место счётчика DN40
svyaz((r_b, 1), (r_sch, 0))
r_c, (r_d, _), p = vetka("V1", "stal", 50, [(X_TR, 2.62, Z_VU)], (0, 1), ["kran50"], UR_P, first=0.08)
svyaz((r_sch, 1), (r_c, 0))
seti[r_d]["pts"] = seti[r_d]["pts"][:1] + [R((X_TR, 3.0, Z_VU))]
r_vs = truba("V1", "stal", 50, [(X_TR, 3.0, Z_VU), (X_TR, p_vs[1], Z_VU), (X_TR, p_vs[1], p_vs[2]), p_vs], UR_P)
svyaz((r_vs, 1), dict(obor=0, kind="vs"))
# обводная линия с опломбированным краном
r_o1, (r_o2, _), p = vetka("V1", "stal", 50, [(X_TR, 1.8, Z_VU), (X_TR - 0.4, 1.8, Z_VU)], (0, 1), ["kran50"],
                           UR_P, first=0.4)
seti[r_o2]["pts"] = seti[r_o2]["pts"][:1] + [R((X_TR - 0.4, 3.0, Z_VU)), R((X_TR, 3.0, Z_VU))]
troynik((r_v1, 1), (r_a, 0), (r_o1, 0))
troynik((r_d, 1), (r_vs, 0), (r_o2, 1))

# стояки К1: внизу чугун SML до -0,350, выше полипропилен; выпуски через стену по оси Д.
# П. 18.4 СП 30: переход стояка в горизонталь — два отвода по 45°; п. 18.5: стояки присоединяются к сборному
# трубопроводу в горизонтальной плоскости под 45° (косой тройник), повороты — не менее двух фасонных частей.
Z_PP = -0.35
Y_ST_D = B + E + 0.26                   # наружная грань стены по оси Д
LOT_ST = -2.0                           # лоток выпуска у наружной стены (расчёт: 99,00 абс.)
I_VN = 0.02
R110 = 0.055
D45 = 0.2                               # вынос косого участка между отводами 45°
Y_SB = 8.0                              # сборный трубопровод секции в подвале


def put_z(tochki, z_konec):
    """z по ломаной (x, y) с уклоном I_VN, если в последней точке z = z_konec (вода течёт к концу)."""
    L = [0.0]
    for p1, p2 in zip(tochki[:-1], tochki[1:]):
        L.append(L[-1] + math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    return [(x, y, z_konec + I_VN * (L[-1] - l)) for (x, y), l in zip(tochki, L)]


def niz_stoyaka(x, y, plan):
    """Низ стояка: вертикаль до отвода 45°, косой участок, далее горизонталь plan (z уже посчитаны)."""
    (x1, y1, z1) = plan[0]
    return [(x, y, Z_PP), (x, y, z1 + D45)] + plan


for s in range(N_SEK):
    ox = s * L_SEK
    (x1, y1), (x2, y2), (x3, y3) = [(ox + a_, b_) for a_, b_ in K1_ST]
    z_vyp = lambda y: LOT_ST + R110 + I_VN * (Y_ST_D - y)          # noqa: E731  ось выпуска по y
    y_tr = Y_SB + 0.3                                               # тройник сборного на выпуске
    # выпуск: от стояка 1 на север через стену по оси Д и на 1 м за неё
    r_vy1 = truba("K1", "sml", 100, niz_stoyaka(x1, y1, [(x1, y1 + D45, z_vyp(y1 + D45)), (x1, y_tr, z_vyp(y_tr))]),
                  UR_P)
    r_vy2 = truba("K1", "sml", 100, [(x1, y_tr, z_vyp(y_tr)), (x1, Y_ST_D + 1.0, z_vyp(Y_ST_D + 1.0))], UR_P)
    # сборный: от стояка 3 на север, поворот 2x45° на запад, по y = Y_SB, в выпуск косым тройником
    trassa = [(x3, y3 + D45), (x3, Y_SB - 0.15), (x3 - 0.15, Y_SB), (x2 - 0.3, Y_SB), (x1 + 0.3, Y_SB), (x1, y_tr)]
    pz = put_z(trassa, z_vyp(y_tr))
    r_sb1 = truba("K1", "sml", 100, niz_stoyaka(x3, y3, pz[:4]), UR_P)
    r_sb2 = truba("K1", "sml", 100, pz[3:], UR_P)
    troynik((r_vy1, 1), (r_vy2, 0), (r_sb2, 1))
    # стояк 2: отвод 45° на север, косой участок на северо-запад в сборный (косой тройник в плане)
    z_tr2 = pz[3][2]
    t2 = put_z([(x2, y2 + D45), (x2, Y_SB - 0.3), (x2 - 0.3, Y_SB)], z_tr2)
    r_st2 = truba("K1", "sml", 100, niz_stoyaka(x2, y2, t2), UR_P)
    troynik((r_sb1, 1), (r_sb2, 0), (r_st2, 1))
    for nom, (x, y), r_niz in ((1, (x1, y1), r_vy1), (2, (x2, y2), r_st2), (3, (x3, y3), r_sb1)):
        imya = "Ст.К1-%d" % (s * 3 + nom)
        runs = stoyak(imya, "K1", x, y, st[s]["k%d" % nom], Z_PP, Z_KR + VYTYAZHKA, ur_po_z, lambda i: 110, "pp")
        svyaz((runs[0], 0), (r_niz, 0))

# ---------------- проверка коллизий ----------------
TOL = 0.002
TOLSH = {"nar": 0.52, "fund": 0.316, "nes": 0.42, "per": 0.10, "beton": 0.20, "korob": 0.05}
ZST = {"etazhi": (0.0, Z_KR), "podval": (Z_P, 0.0), "vse": (Z_P, Z_KR)}
NAR_D = {("stal", 15): 0.0213, ("stal", 20): 0.0268, ("stal", 25): 0.0335, ("stal", 32): 0.0423,
         ("stal", 40): 0.048, ("stal", 50): 0.060, ("pp", 50): 0.050, ("pp", 110): 0.110, ("sml", 100): 0.110,
         ("pe", 63): 0.063}


def pryam_steny():
    out = []
    for w in steny:
        (x1, y1), (x2, y2) = w["p1"], w["p2"]
        t = TOLSH[w["tip"]] / 2
        if abs(y1 - y2) < 1e-9:
            out.append((min(x1, x2), y1 - t, max(x1, x2), y1 + t, "x", ZST[w["gde"]], w))
        else:
            out.append((x1 - t, min(y1, y2), x1 + t, max(y1, y2), "y", ZST[w["gde"]], w))
    return out


def seg_dist(p1, p2, q1, q2):
    """Минимальное расстояние между отрезками в 3D и параметры ближайших точек."""
    import itertools  # noqa: F401
    d1 = [p2[i] - p1[i] for i in range(3)]
    d2 = [q2[i] - q1[i] for i in range(3)]
    r = [p1[i] - q1[i] for i in range(3)]
    a_ = sum(v * v for v in d1)
    e_ = sum(v * v for v in d2)
    f_ = sum(d2[i] * r[i] for i in range(3))
    if a_ < 1e-12 and e_ < 1e-12:
        return math.dist(p1, q1), 0, 0
    if a_ < 1e-12:
        s_, t_ = 0.0, min(max(f_ / e_, 0), 1)
    else:
        c_ = sum(d1[i] * r[i] for i in range(3))
        if e_ < 1e-12:
            t_, s_ = 0.0, min(max(-c_ / a_, 0), 1)
        else:
            b_ = sum(d1[i] * d2[i] for i in range(3))
            den = a_ * e_ - b_ * b_
            s_ = min(max((b_ * f_ - c_ * e_) / den, 0), 1) if den > 1e-12 else 0.0
            t_ = (b_ * s_ + f_) / e_
            if t_ < 0:
                t_, s_ = 0.0, min(max(-c_ / a_, 0), 1)
            elif t_ > 1:
                t_, s_ = 1.0, min(max((b_ - c_) / a_, 0), 1)
    cp = [p1[i] + d1[i] * s_ for i in range(3)]
    cq = [q1[i] + d2[i] * t_ for i in range(3)]
    return math.dist(cp, cq), s_, t_


def proverka():
    stn = pryam_steny()
    kol = {}

    def zap(vid, opis):
        kol.setdefault(vid, []).append(opis)
    segs = []
    for r in seti:
        rad = NAR_D[(r["pt"], r["d"])] / 2
        for p1, p2 in zip(r["pts"][:-1], r["pts"][1:]):
            if math.dist(p1, p2) > 1e-4:
                segs.append((r["id"], p1, p2, rad))
    # 1. трубы и стены
    for rid, p1, p2, rad in segs:
        vert = abs(p1[0] - p2[0]) < 1e-6 and abs(p1[1] - p2[1]) < 1e-6
        for x0, y0, x1, y1, os_, (za, zb), w in stn:
            if max(p1[2], p2[2]) < za + TOL or min(p1[2], p2[2]) > zb - TOL:
                continue
            if vert:
                if x0 - rad + TOL < p1[0] < x1 + rad - TOL and y0 - rad + TOL < p1[1] < y1 + rad - TOL:
                    zap("стояк/вертикаль в стене", (rid, p1, w["tip"]))
                continue
            n = max(40, int(math.dist(p1[:2], p2[:2]) / 0.01))
            vnutri = 0
            for i in range(n + 1):
                x = p1[0] + (p2[0] - p1[0]) * i / n
                y = p1[1] + (p2[1] - p1[1]) * i / n
                if x0 - rad + TOL < x < x1 + rad - TOL and y0 - rad + TOL < y < y1 + rad - TOL:
                    vnutri += 1
            L_in = math.dist(p1[:2], p2[:2]) * vnutri / n
            tol_w = (x1 - x0) if os_ == "y" else (y1 - y0)
            if L_in > tol_w * 1.5 + 2 * rad + 0.03:
                zap("труба вдоль стены", (rid, p1, p2, w["tip"], round(L_in, 3)))
    # 2. приборы и стены, приборы между собой
    for pid, x0, y0, x1, y1, za, zb in gabarity_pr:
        for sx0, sy0, sx1, sy1, os_, (sza, szb), w in stn:
            if zb < sza or za > szb:
                continue
            if min(x1, sx1) - max(x0, sx0) > TOL and min(y1, sy1) - max(y0, sy0) > TOL:
                zap("прибор в стене", (pid, pribory[pid]["fam"][5:25], w["tip"]))
    po_et = {}
    for g_ in gabarity_pr:
        po_et.setdefault(round(g_[5], 2), []).append(g_)
    for lst in po_et.values():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a_, b_ = lst[i], lst[j]
                if min(a_[3], b_[3]) - max(a_[1], b_[1]) > TOL and min(a_[4], b_[4]) - max(a_[2], b_[2]) > TOL:
                    zap("приборы пересекаются", (pribory[a_[0]]["fam"][5:20], pribory[b_[0]]["fam"][5:20], a_[1:3]))
    # 3. трубы и приборы (кроме подводок/отводов, приходящих к соединителям этого прибора)
    soed_xy = {}
    for sv in svyazi:
        b_ = sv["b"]
        if isinstance(b_, dict) and "fix" in b_:
            r = seti[sv["a"][0]]
            p = r["pts"][0] if sv["a"][1] == 0 else r["pts"][-1]
            soed_xy.setdefault(b_["fix"], []).append(p)
    for rid, p1, p2, rad in segs:
        for pid, x0, y0, x1, y1, za, zb in gabarity_pr:
            if max(p1[2], p2[2]) < za or min(p1[2], p2[2]) > zb:
                continue
            if max(p1[0], p2[0]) < x0 or min(p1[0], p2[0]) > x1 or max(p1[1], p2[1]) < y0 or min(p1[1], p2[1]) > y1:
                continue
            svoi = any(math.dist(q[:2], e[:2]) < 0.005 for q in soed_xy.get(pid, []) for e in (p1, p2))
            if svoi:
                continue
            # пересечение отрезка с коробкой — по точкам
            n = 20
            for i in range(1, n):
                q = [p1[k] + (p2[k] - p1[k]) * i / n for k in range(3)]
                if x0 + rad < q[0] < x1 - rad and y0 + rad < q[1] < y1 - rad and za < q[2] < zb:
                    zap("труба через прибор", (rid, pribory[pid]["fam"][5:25], [round(v, 3) for v in q]))
                    break
    # 4. трубы между собой (сетка 0,5 м), кроме узлов соединения
    jac = {}
    for idx, (rid, p1, p2, rad) in enumerate(segs):
        for gx in range(int(math.floor(min(p1[0], p2[0]) / 0.5)), int(math.floor(max(p1[0], p2[0]) / 0.5)) + 1):
            for gy in range(int(math.floor(min(p1[1], p2[1]) / 0.5)), int(math.floor(max(p1[1], p2[1]) / 0.5)) + 1):
                for gz in range(int(math.floor(min(p1[2], p2[2]) / 0.5)), int(math.floor(max(p1[2], p2[2]) / 0.5)) + 1):
                    jac.setdefault((gx, gy, gz), []).append(idx)
    videl = set()
    for lst in jac.values():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a_, b_ = lst[i], lst[j]
                if (a_, b_) in videl:
                    continue
                videl.add((a_, b_))
                ra, p1, p2, r1 = segs[a_]
                rb, q1, q2, r2 = segs[b_]
                if ra == rb:
                    continue
                d, s_, t_ = seg_dist(p1, p2, q1, q2)
                if d >= r1 + r2 - TOL:
                    continue
                # узел соединения: оба отрезка подходят концами к общей точке
                if min(math.dist(e, f) for e in (p1, p2) for f in (q1, q2)) < 0.01 or                         any(seg_dist(e, e, q1, q2)[0] < 0.01 for e in (p1, p2)) or                         any(seg_dist(f, f, p1, p2)[0] < 0.01 for f in (q1, q2)):
                    continue
                zap("трубы пересекаются", (ra, rb, round(d, 4), [round(v, 3) for v in p1], [round(v, 3) for v in q1]))
    return kol


kol = proverka()
if not kol:
    print("КОЛЛИЗИЙ НЕТ")
for vid, lst in kol.items():
    print("КОЛЛИЗИИ: %s — %d" % (vid, len(lst)))
    for x in lst[:6]:
        print("   ", x)

# ---------------- сверка с расчётом ----------------
dl = {}
for r in seti:
    L_ = sum(math.dist(a, b) for a, b in zip(r["pts"][:-1], r["pts"][1:]))
    dl.setdefault((r["sys"], r["pt"], r["d"]), 0.0)
    dl[(r["sys"], r["pt"], r["d"])] += L_
print("длины труб, м:", {"%s %s %s" % k: round(v, 1) for k, v in sorted(dl.items())})
print("приборов", len(pribory), "труб", len(seti), "тройников", len(troyniki), "крестовин", len(kresty),
      "арматуры", len(armatura), "муфт", len(mufty))
geo = dict(pribory=pribory, seti=seti, troyniki=troyniki, kresty=kresty, armatura=armatura, svyazi=svyazi,
           mufty=mufty, stoyaki=stoyaki, oborud=oborud,
           sistemy=dict(V1="ADSK_Водопровод_В1", K1="ADSK_Канализация_К1"),
           tipy_trub=dict(stal="ADSK_Сталь водогазопроводная_Оцинкованная_ГОСТ 3262-75",
                          pp="ADSK_Полипропилен раструбный_ГОСТ 32414-2013",
                          sml="ADSK_Чугун_Безраструбный SML_DIN EN 877",
                          pe="ADSK_Полиэтилен ПЭ100 SDR17_ГОСТ 18599-2001"),
           urovni=urovni, osi=osi, steny=steny, okna=okna, perekr=perekr, krovlya=krovlya,
           tipy=dict(nar="ADSK_Наружная_Кирпич380 ут100 мм шт20-шт20_520",
                     fund="ADSK_Фундамент_Бетон300_Гидроизоляция16_316",
                     nes="ADSK_Внутренняя_Кирпич380 шт20-шт20_420",
                     per="ADSK_Перегородка_ПГП_100",
                     korob="КВВ_Короб_ГКЛВ_50",
                     beton="ADSK_Внутренняя_Бетон_200",
                     perekr="ADSK_Перекрытие_Плита с полом_Бетон200 стяжка80 плитка20_300",
                     pol_podv="ADSK_Фундамент_Бетон200_Двухслойная Гидроизоляция249_449",
                     krovlya="ADSK_Плоская кровля по бетонному основанию_290",
                     okno=["B2B_Окно_2створки", "1470(870)х1320h"],
                     dver_vh=["AC_Дверь_Двупольная_Стальная", "1360х2080h Н"]),
           podokonnik=0.9)

with open(os.path.join(HERE, "geometriya_v3.json"), "w", encoding="utf-8") as f:
    json.dump(geo, f, ensure_ascii=False, indent=1)
print("уровней", len(urovni), "осей", len(osi), "стен", len(steny), "окон", len(okna))
