# -*- coding: utf-8 -*-
"""Генеральный план М 1:500, системы В1 и К1 (лист 8 комплекта, А2) — по образцу преподавателя.

Данные — из расчёта (calc/rezultaty_v3.json, calc/trassa_v3.json): колодцы дворовой сети, длины, уклоны, отметки
лотков и земли, ввод. Рельеф (горизонтали через 0,1 м) подобран так, чтобы земля у колодцев совпала с расчётом,
а ввод и выпуски лежали не выше допустимого по промерзанию.

Скрипт пишет genplan_v3.scr (команды AutoLISP для консольного AutoCAD: entmake, без загрузки .lsp — защита
SECURELOAD их не пускает), запускает accoreconsole, сохраняет genplan_v3.dwg и печатает genplan_v3.pdf (А2, 1:500).
Чертёж — в пространстве модели в метрах, рамка и штамп вычерчены в масштабе 1:500 (1 мм листа = 0,5 м).
Данные для продольного профиля дворовой сети — genplan_v3.json.
"""
import io
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KURS = os.path.dirname(HERE)
REZ = json.load(open(os.path.join(KURS, "calc", "rezultaty_v3.json"), encoding="utf-8"))
TR = json.load(open(os.path.join(KURS, "calc", "trassa_v3.json"), encoding="utf-8"))
ACC = r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe"

# ---------------- исходные данные ----------------
Z0 = REZ["Z0_ABS"]                              # 0,000 = 101,00
H_PR = REZ["iznach"]["H_PROMERZ"]               # 1,7 м
D_GOR_V, D_GOR_K = REZ["iznach"]["D_GOR_V"], REZ["iznach"]["D_GOR_K"]
ZERK, X_SHOV = TR["zerkalo"], TR["x_shov"]
E = 0.06
X_NAR0, X_NAR1 = -E - 0.26, ZERK + E + 0.26     # наружные грани торцевых стен
Y_NAR0, Y_NAR1 = -E - 0.26, 12.8 + E + 0.26     # наружные грани стен по осям А и Д
L_VYP = 5.0                                     # от наружной стены до КК (как в расчёте)
Y_DVOR = Y_NAR1 + L_VYP
X_GOR, X_KRASN = -15.0, -10.0                   # городская канализация и красная линия (как в расчёте)
X_GOR_V = -12.5                                 # городской водопровод — между ними
X_VV = TR["x_troynik"]                          # ввод входит в насосную по оси x = 4,0
L_VK = 6.5                                      # ВК-1 — стена
Y_VK = Y_NAR0 - L_VK
L_GVK = X_VV - X_GOR_V                          # ГВК — ВК-1
assert abs(L_GVK + L_VK - (REZ["L_vvod"] - 2.0)) < 1e-6, "длина ввода не совпадает с расчётом (23 м до стены)"
Z_VV_OTN = -2.50                                # ось ввода у стены (модель Revit)
Z_VV_GVK = 98.20                                # ось ввода у ГВК (врезка в бок городской трубы Ø250, верх 98,30)

vyp = sorted(TR["vypuski"], key=lambda v: v["x"])
KOL = {"ГКК": (X_GOR, Y_DVOR), "ККК": (X_KRASN + 1.2, Y_DVOR), "КК-3": (vyp[0]["x"], Y_DVOR),
       "КК-2": (X_SHOV, Y_DVOR), "КК-1": (vyp[1]["x"], Y_DVOR), "ГВК": (X_GOR_V, Y_VK), "ВК-1": (X_VV, Y_VK)}
DVOR = [u for u in REZ["k1"] if u["imya"].startswith("КК") or u["imya"].startswith("ККК")]
PARY = [("КК-1", "КК-2"), ("КК-2", "КК-3"), ("КК-3", "ККК"), ("ККК", "ГКК")]
for u, (a, b) in zip(DVOR, PARY):
    L_ = abs(KOL[a][0] - KOL[b][0])
    assert abs(L_ - u["L"]) < 0.01, (u["imya"], L_, u["L"])
U_VYP = [u for u in REZ["k1"] if u["imya"].startswith("выпуск")][0]
LOT_VYP = REZ["lotok"]["выпуск у стены"]


# ---------------- рельеф ----------------
def pchip(xs, ys):
    """Монотонная кубическая интерполяция (Фритч — Карлсон) с линейным продолжением за концы."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [d[0]] + [0.0] * (n - 2) + [d[-1]]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


ZEML = REZ["zeml"]
_tz = sorted((KOL[k][0], ZEML[k]) for k in ("ГКК", "ККК", "КК-3", "КК-2", "КК-1"))
F = pchip([a for a, _ in _tz], [b for _, b in _tz])
Z_ZEML_GVK = Z0 - 0.50                          # земля у ГВК — как в расчёте (Z_ZEML_VVOD = -0,50)
P_Y = Y_DVOR - Y_VK                             # период волны горизонталей: нули на линии колодцев и у ГВК
A_LIN = Z_ZEML_GVK - F(X_GOR_V)
A_VOL = 0.05


def G(y):
    return A_LIN * (Y_DVOR - y) / P_Y + A_VOL * math.sin(2 * math.pi * (y - Y_DVOR) / P_Y)


def zeml(x, y):
    return F(x) + G(y)


def x_po_z(z, y, lo=-200.0, hi=250.0):
    """Абсцисса точки горизонтали z на ординате y (рельеф монотонен по x)."""
    c = z - G(y)
    for _ in range(80):
        mid = (lo + hi) / 2
        if F(mid) < c:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# проверки: земля у колодцев, глубина ввода и выпусков
for k in ("ГКК", "ККК", "КК-3", "КК-2", "КК-1"):
    assert abs(zeml(*KOL[k]) - ZEML[k]) < 0.005, (k, zeml(*KOL[k]), ZEML[k])
assert abs(zeml(*KOL["ГВК"]) - Z_ZEML_GVK) < 0.005
R_VV = 0.0315                                   # наружный радиус ПЭ Ø63
i_vv = (Z0 + Z_VV_OTN - Z_VV_GVK) / (L_GVK + L_VK)
proverki = []
for nm, (x, y), zc in (("у ГВК", KOL["ГВК"], Z_VV_GVK), ("у ВК-1", KOL["ВК-1"], Z_VV_GVK + i_vv * L_GVK),
                       ("у стены", (X_VV, Y_NAR0), Z0 + Z_VV_OTN)):
    zz = zeml(x, y)
    glub = zz - (zc - R_VV)
    proverki.append(("ввод " + nm, round(zz, 2), round(zc, 3), round(glub, 2), H_PR + 0.5))
    assert glub >= H_PR + 0.5 - 1e-6, ("ввод мелко", nm, glub)
for v in vyp:
    zz = zeml(v["x"], Y_NAR1)
    glub = zz - LOT_VYP
    proverki.append(("выпуск x=%.2f" % v["x"], round(zz, 2), LOT_VYP, round(glub, 2), REZ["min_glub"]))
    assert glub >= REZ["min_glub"] - 1e-6, ("выпуск мелко", v, glub)

# ---------------- лист: А3 (как все листы комплекта), 1:500 ----------------
S = 0.5                                         # м модели на 1 мм листа
X0, Y0 = 15.0 - 195 * S, 6.0 - 185 * S          # левый нижний угол листа в модели: план — по центру поля


def L(xs, ys):
    """Точка листа (мм) -> модель (м)."""
    return (X0 + xs * S, Y0 + ys * S)


def hm(mm):
    return mm * S


# ---------------- AutoLISP ----------------
cmd = []


def s_(t):
    t = t.replace("\\", "\\\\").replace('"', '\\"').replace("Ø", "%%c")
    t.encode("cp1251")                          # всё, что пишем, должно быть в cp1251 (скрипт читается в ANSI)
    return '"' + t + '"'


def p_(p):
    return "(%.4f %.4f 0.0)" % (p[0], p[1])


def sloy(nm, cvet, ves, tip="Continuous", rgb=None):
    """Слой; rgb — точный цвет (как у систем на листах Revit)."""
    tc = " '(420 . %d)" % (rgb[0] * 65536 + rgb[1] * 256 + rgb[2]) if rgb else ""
    cmd.append('(if (not (tblsearch "LAYER" %s)) (entmake (list \'(0 . "LAYER") \'(100 . "AcDbSymbolTableRecord") '
               '\'(100 . "AcDbLayerTableRecord") (cons 2 %s) \'(70 . 0) \'(62 . %d)%s (cons 6 %s) \'(370 . %d))))'
               % (s_(nm), s_(nm), cvet, tc, s_(tip), ves))


def otrezok(a, b, sl, ves=None):
    v = "'(370 . %d) " % ves if ves is not None else ""
    cmd.append("(entmake (list '(0 . \"LINE\") (cons 8 %s) %s'(10 . %s) '(11 . %s)))"
               % (s_(sl), v, p_(a)[1:-1].join(("(", ")")), p_(b)[1:-1].join(("(", ")"))))


def polilinia(pts, sl, zamk=False, ves=None):
    """LWPOLYLINE; длинные — кусками по 40 вершин (длина строки скрипта)."""
    if len(pts) > 40 and not zamk:
        for i in range(0, len(pts) - 1, 39):
            polilinia(pts[i:i + 40], sl, False, ves)
        return
    v = "'(370 . %d) " % ves if ves is not None else ""
    ver = " ".join("'(10 %.4f %.4f)" % (x, y) for x, y in pts)
    cmd.append("(entmake (list '(0 . \"LWPOLYLINE\") '(100 . \"AcDbEntity\") (cons 8 %s) %s'(100 . \"AcDbPolyline\") "
               "'(90 . %d) '(70 . %d) %s))" % (s_(sl), v, len(pts), 1 if zamk else 0, ver))


def okr(c, r, sl, ves=None):
    v = "'(370 . %d) " % ves if ves is not None else ""
    cmd.append("(entmake (list '(0 . \"CIRCLE\") (cons 8 %s) %s'(10 %.4f %.4f 0.0) '(40 . %.4f)))"
               % (s_(sl), v, c[0], c[1], r))


def tekst(p, h, t, sl, rot=0.0, vyr="L", maska=False, prik=None):
    """TEXT; vyr: L — влево, C — по центру, R — вправо (по базовой линии), M — по середине.
    maska — многострочный текст с маской фона: горизонтали под надписью не видны (не пересекают текст)."""
    if maska:
        prik = prik or {"L": 7, "C": 8, "R": 9, "M": 5}[vyr]
        cmd.append("(entmake (list '(0 . \"MTEXT\") '(100 . \"AcDbEntity\") (cons 8 %s) '(100 . \"AcDbMText\") "
                   "'(10 %.4f %.4f 0.0) '(40 . %.4f) '(41 . 0.0) '(71 . %d) '(72 . 1) (cons 1 %s) '(7 . \"КВВ_ГОСТ\") "
                   "'(50 . %.6f) '(90 . 3) '(63 . 256) '(45 . 1.15) '(441 . 0)))"
                   % (s_(sl), p[0], p[1], h, prik, s_(t), rot))
        return
    j = {"L": (0, 0), "C": (1, 0), "R": (2, 0), "M": (1, 2)}[vyr]
    tail = "" if j == (0, 0) else " '(72 . %d) '(73 . %d) '(11 %.4f %.4f 0.0)" % (j[0], j[1], p[0], p[1])
    cmd.append("(entmake (list '(0 . \"TEXT\") (cons 8 %s) '(7 . \"КВВ_ГОСТ\") '(10 %.4f %.4f 0.0) '(40 . %.4f) "
               "'(41 . 0.8) '(50 . %.6f) (cons 1 %s)%s))" % (s_(sl), p[0], p[1], h, rot, s_(t), tail))


def shirina(t, h):
    return len(t) * h * 0.56                    # GOST Common, сжатие 0,8 (как текст ADSK на листах Revit)


def vynoska(p, polka, st, t1, t2, sl, h=1.25):
    """Выноска как в образце: наклонная линия от трубы к началу полки, полка — в сторону от трубы (линия не
    проходит через текст), текст над полкой и под ней с зазором (маска текста не закрывает полку)."""
    dl = max(shirina(t1, h), shirina(t2 or "", h)) + 0.8
    x0, y0 = polka
    st = 1 if x0 >= p[0] else -1
    xa, xb = (x0, x0 + dl) if st > 0 else (x0 - dl, x0)
    polilinia([p, (x0, y0), (xb if st > 0 else xa, y0)], "ГП_Выноски", ves=18)
    xm = (xa + xb) / 2
    tekst((xm, y0 + 0.25 * h), h, t1, sl, vyr="C", maska=True, prik=8)       # низ текста — над полкой
    if t2:
        tekst((xm, y0 - 0.3 * h), h, t2, sl, vyr="C", maska=True, prik=2)    # верх текста — под полкой


def F2(v, n=2):
    return ("%.*f" % (n, v)).replace(".", ",")


# ---------------- построение ----------------
cmd.append('(setvar "CMDECHO" 0)')
cmd.append("(entmake (list '(0 . \"STYLE\") '(100 . \"AcDbSymbolTableRecord\") '(100 . \"AcDbTextStyleTableRecord\") "
           "'(2 . \"КВВ_ГОСТ\") '(70 . 0) '(40 . 0.0) '(41 . 0.8) '(50 . 0.0) '(71 . 0) '(42 . 2.5) "
           "'(3 . \"GOST_Common.ttf\") '(4 . \"\")))")
cmd.append("(if (not (tblsearch \"LTYPE\" \"КВВ_ШТРИХ\")) (entmake (list '(0 . \"LTYPE\") '(100 . \"AcDbSymbolTableRecord\") "
           "'(100 . \"AcDbLinetypeTableRecord\") '(2 . \"КВВ_ШТРИХ\") '(70 . 0) '(3 . \"Штрих 4-2 мм при 1:500\") "
           "'(72 . 65) '(73 . 2) '(40 . 3.0) '(49 . 2.0) '(74 . 0) '(49 . -1.0) '(74 . 0))))")
# цвета систем — как на листах Revit (ADSK_Водопровод_В1, ADSK_Канализация_К1)
RGB_V1, RGB_K1 = (0, 127, 255), (165, 41, 0)
for nm, cv, ves, tip, rgb in (("ГП_Здание", 7, 50, "Continuous", None), ("ГП_К1", 14, 50, "Continuous", RGB_K1),
                              ("ГП_В1", 150, 50, "Continuous", RGB_V1), ("ГП_К1_город", 14, 70, "Continuous", RGB_K1),
                              ("ГП_В1_город", 150, 70, "Continuous", RGB_V1), ("ГП_КЛЗ", 1, 35, "КВВ_ШТРИХ", None),
                              ("ГП_Горизонтали", 7, 18, "Continuous", None), ("ГП_Текст", 7, 18, "Continuous", None),
                              ("ГП_Текст_К1", 14, 18, "Continuous", RGB_K1),
                              ("ГП_Текст_В1", 150, 18, "Continuous", RGB_V1),
                              ("ГП_Текст_КЛЗ", 1, 18, "Continuous", None), ("ГП_Выноски", 7, 18, "Continuous", None),
                              ("ГП_Рамка", 7, 50, "Continuous", None), ("ГП_Штамп", 7, 25, "Continuous", None)):
    sloy(nm, cv, ves, tip, rgb)

# горизонтали
OKNO = (-25.0, -16.0, 55.0, 28.0)
zmin = min(zeml(x, y) for x in (OKNO[0], OKNO[2]) for y in [OKNO[1] + k * 0.5 for k in range(89)])
zmax = max(zeml(x, y) for x in (OKNO[0], OKNO[2]) for y in [OKNO[1] + k * 0.5 for k in range(89)])
gorizontali = []
z = math.ceil(zmin * 10 - 1e-9) / 10
while z <= zmax + 1e-9:
    kus, tek = [], []
    yy = OKNO[1]
    while yy <= OKNO[3] + 1e-9:
        x = x_po_z(z, yy)
        if OKNO[0] <= x <= OKNO[2]:
            tek.append((x, yy))
        elif tek:
            kus.append(tek)
            tek = []
        yy += 0.5
    if tek:
        kus.append(tek)
    for k_ in kus:
        if len(k_) >= 3:
            polilinia(k_, "ГП_Горизонтали", ves=18)
    if kus and len(kus[-1]) >= 3:
        (xa, ya), (xb, yb) = kus[-1][-2], kus[-1][-1]
        if X_GOR - 2.0 <= xb <= X_KRASN + 1.5:        # верхний конец у городских сетей — подпись на нижнем конце
            (xb, yb), (xa, ya) = kus[0][0], kus[0][1]
        ang = math.atan2(yb - ya, xb - xa)
        if abs(ang) > math.pi / 2:                    # текст не вверх ногами
            ang += math.pi if ang < 0 else -math.pi
        tekst((xb + 0.3 * math.cos(ang), yb + 0.3 * math.sin(ang)), hm(2.0), F2(z, 1), "ГП_Горизонтали", rot=ang)
    gorizontali.append(round(z, 1))
    z = round(z + 0.1, 1)

# здание
polilinia([(X_NAR0, Y_NAR0), (X_NAR1, Y_NAR0), (X_NAR1, Y_NAR1), (X_NAR0, Y_NAR1)], "ГП_Здание", zamk=True, ves=50)
otrezok((X_SHOV, Y_NAR0), (X_SHOV, Y_NAR1), "ГП_Здание", ves=25)                # деформационный шов
tekst(((X_NAR0 + X_NAR1) / 2, Y_NAR0 + 3.6), hm(3.5), "0,000 = %s" % F2(Z0), "ГП_Текст", vyr="M", maska=True)

# городские сети и красная линия
Y_G0, Y_G1 = OKNO[1] - 1.0, OKNO[3] + 1.0
for x, sl, slt, nm, dy in ((X_GOR, "ГП_К1_город", "ГП_Текст_К1", "К1", 0.8), (X_GOR_V, "ГП_В1_город", "ГП_Текст_В1", "В1", 2.6),
                           (X_KRASN, "ГП_КЛЗ", "ГП_Текст_КЛЗ", "КЛЗ", 0.8)):
    otrezok((x, Y_G0), (x, Y_G1), sl)
    tekst((x, Y_G1 + dy), hm(2.5), nm, slt, vyr="C", maska=True)                # «В1» выше — не слипается с «К1» и «КЛЗ»

# колодцы
R_KK, R_GKK = 0.6, 1.0
for k, (x, y) in KOL.items():
    r = R_GKK if k == "ГКК" else R_KK
    okr((x, y), r, "ГП_В1" if "В" in k else "ГП_К1", ves=50)
POD = {"ГКК": (-3.6, 1.2, "L"), "ККК": (-0.4, 1.0, "L"), "КК-3": (0.8, 0.9, "L"), "КК-2": (0.8, 0.9, "L"),
       "КК-1": (-0.8, 0.9, "R"), "ГВК": (0.9, 0.9, "L"), "ВК-1": (0.9, 0.9, "L")}
for k, (dx, dy, vy) in POD.items():
    x, y = KOL[k]
    tekst((x + dx, y + dy), hm(2.5), k, "ГП_Текст_В1" if "В" in k else "ГП_Текст_К1", vyr=vy, maska=True)


def mezhdu(a, b, ra, rb):
    """Отрезок между окружностями колодцев (от края до края)."""
    (xa, ya), (xb, yb) = a, b
    d = math.hypot(xb - xa, yb - ya)
    ux, uy = (xb - xa) / d, (yb - ya) / d
    return (xa + ux * ra, ya + uy * ra), (xb - ux * rb, yb - uy * rb)


# дворовая канализация Ø160
for a, b in PARY:
    p, q = mezhdu(KOL[a], KOL[b], R_GKK if a == "ГКК" else R_KK, R_GKK if b == "ГКК" else R_KK)
    otrezok(p, q, "ГП_К1")
# выпуски Ø100 — от стены до КК
for v in vyp:
    k = "КК-3" if v["x"] < ZERK / 2 else "КК-1"
    otrezok((v["x"], Y_NAR1), (v["x"], Y_DVOR - R_KK), "ГП_К1")
# водопровод: ГВК — ВК-1 — стена
p, q = mezhdu(KOL["ГВК"], KOL["ВК-1"], R_KK, R_KK)
otrezok(p, q, "ГП_В1")
otrezok((X_VV, Y_VK + R_KK), (X_VV, Y_NAR0), "ГП_В1")

# подписи сетей (выноски), как в образце: «К1 Ø160 / l = …; i = …»
u = {a + "-" + b: d_ for d_, (a, b) in zip(DVOR, PARY)}


def podp_k1(a, b):
    d_ = u[a + "-" + b]
    return "К1 Ø160", "l = %s м; i = %s" % (F2(d_["L"]), F2(d_["i"], 3))


xm = (KOL["КК-1"][0] + KOL["КК-2"][0]) / 2
vynoska((xm, Y_DVOR), (xm - 2.0, Y_DVOR + 4.2), 1, *podp_k1("КК-1", "КК-2"), sl="ГП_Текст")
xm = (KOL["КК-2"][0] + KOL["КК-3"][0]) / 2
vynoska((xm, Y_DVOR), (xm - 2.0, Y_DVOR + 4.2), 1, *podp_k1("КК-2", "КК-3"), sl="ГП_Текст")
xm = (KOL["КК-3"][0] + KOL["ККК"][0]) / 2
vynoska((xm, Y_DVOR), (-17.5, Y_DVOR + 3.6), -1, *podp_k1("КК-3", "ККК"), sl="ГП_Текст")
xm = (KOL["ККК"][0] + KOL["ГКК"][0]) / 2
vynoska((xm + 1.5, Y_DVOR), (-17.5, Y_DVOR - 3.4), -1, *podp_k1("ККК", "ГКК"), sl="ГП_Текст")
# выпуски
for i_, v in enumerate(vyp):
    st = 1 if v["x"] < ZERK / 2 else -1
    nom = 1 if v["x"] < ZERK / 2 else 2
    ym = (Y_NAR1 + Y_DVOR - R_KK) / 2
    vynoska((v["x"], ym), (v["x"] + st * 2.2, ym + 0.4), st, "К1 Ø100",
            "l = %s м; i = %s" % (F2(L_VYP, 1), F2(U_VYP["i"], 2)), sl="ГП_Текст")
    vynoska((v["x"], Y_NAR1 - 0.1), (v["x"] + st * 2.2, Y_NAR1 - 2.6), st, "Выпуск К1-%d Ø100" % nom,
            "на отм. %s (%s)" % (F2(LOT_VYP), F2(LOT_VYP - Z0, 3)), sl="ГП_Текст")
# ввод
vynoska((X_VV, (Y_VK + R_KK + Y_NAR0) / 2), (X_VV + 2.2, Y_NAR0 - 2.6), 1, "Ввод В1-1 Ø63",
        "l = %s м; на отм. %s (%s)" % (F2(L_VK, 1), F2(Z0 + Z_VV_OTN), F2(Z_VV_OTN, 3)), sl="ГП_Текст")
vynoska(((KOL["ГВК"][0] + KOL["ВК-1"][0]) / 2, Y_VK), (-2.5, Y_VK - 3.0), 1, "В1 Ø63",
        "l = %s м" % F2(L_GVK, 1), sl="ГП_Текст")

# заголовок
tekst(L(195, 245), hm(5.0), "Генеральный план. Системы В1, К1 ( 1 : 500)", "ГП_Текст", vyr="C")   # как заголовки Revit


# ---------------- рамка и основная надпись (форма 3), А2 ----------------
def ramka_mm(x0, y0, x1, y1, sl="ГП_Рамка", ves=None):
    polilinia([L(x0, y0), L(x1, y0), L(x1, y1), L(x0, y1)], sl, zamk=True, ves=ves)


def lin_mm(x0, y0, x1, y1, ves=25):
    otrezok(L(x0, y0), L(x1, y1), "ГП_Штамп", ves=ves)


def t_mm(x, y, h, t, vyr="M", rot=0.0):
    tekst(L(x, y), hm(h), t, "ГП_Текст", rot=rot, vyr=vyr)


W_, H_ = 420.0, 297.0
ramka_mm(0, 0, W_, H_, ves=18)                                  # граница листа
ramka_mm(20, 5, W_ - 5, H_ - 5, ves=70)                         # рамка
# основная надпись 185 x 55
sx, sy = W_ - 5 - 185, 5
ramka_mm(sx, sy, sx + 185, sy + 55, sl="ГП_Штамп", ves=70)
for k in range(1, 11):                                          # строки левой части по 5 мм
    lin_mm(sx, sy + 5 * k, sx + 65, sy + 5 * k, ves=50 if k in (6, 7) else 18)
for xk in (10, 20, 30, 40):                                     # колонки над шапкой (изменения и шапка)
    lin_mm(sx + xk, sy + 30, sx + xk, sy + 55, ves=50)
for xk in (20, 40):
    lin_mm(sx + xk, sy, sx + xk, sy + 30, ves=50)
for xk in (55, 65):
    lin_mm(sx + xk, sy, sx + xk, sy + 55, ves=50)
lin_mm(sx + 65, sy + 45, sx + 185, sy + 45, ves=50)
lin_mm(sx + 65, sy + 30, sx + 185, sy + 30, ves=50)
lin_mm(sx + 65, sy + 15, sx + 185, sy + 15, ves=50)
lin_mm(sx + 135, sy, sx + 135, sy + 30, ves=50)
lin_mm(sx + 135, sy + 25, sx + 185, sy + 25, ves=18)
for xk in (150, 165):
    lin_mm(sx + xk, sy + 15, sx + xk, sy + 30, ves=50)
for x_, t in ((5, "Изм."), (15, "Кол.уч."), (25, "Лист"), (35, "№док."), (47.5, "Подп."), (60, "Дата")):
    t_mm(sx + x_, sy + 32.5, 2.0, t)
t_mm(sx + 1, sy + 26.6, 2.0, "Разраб.", vyr="L")
t_mm(sx + 1, sy + 21.6, 2.0, "Пров.", vyr="L")
t_mm(sx + 125, sy + 50, 3.5, "НИУ МГСУ 08.03.01*-КП-2026 - ВК")
t_mm(sx + 125, sy + 37.5, 2.5, "Системы холодного водоснабжения и водоотведения здания")
t_mm(sx + 100, sy + 22.5, 2.5, "Наименование здания. Жилой дом. Вариант 3")       # как в штампе листов Revit
for x_, t in ((142.5, "Стадия"), (157.5, "Лист"), (175, "Листов")):
    t_mm(sx + x_, sy + 27.5, 2.0, t)
for x_, t in ((142.5, "У"), (157.5, "8"), (175, "8")):
    t_mm(sx + x_, sy + 20, 3.5, t)
t_mm(sx + 100, sy + 7.5, 2.5, "Генеральный план. Системы В1, К1")
t_mm(sx + 160, sy + 11, 2.0, "НИУ МГСУ ИИЭСМ")
t_mm(sx + 160, sy + 7.3, 2.0, "Кафедра «Водоснабжение и")
t_mm(sx + 160, sy + 3.6, 2.0, "водоотведение»")
t_mm(W_ - 74, 1.3, 2.5, "Формат А3", vyr="L")
t_mm(W_ - 37, 1.3, 2.5, "297 x 420", vyr="L")
# дополнительные графы у подшивки
for y0, y1, t in ((5, 30, "Инв. № подл."), (30, 65, "Подп. и дата"), (65, 90, "Взам. инв. №")):
    ramka_mm(8, y0, 20, y1, sl="ГП_Штамп", ves=50)
    lin_mm(13, y0, 13, y1, ves=50)
    t_mm(10.5, (y0 + y1) / 2, 2.5, t, rot=math.pi / 2)
ramka_mm(5, 90, 20, 155, sl="ГП_Штамп", ves=50)
lin_mm(10, 90, 10, 155, ves=50)
lin_mm(15, 90, 15, 155, ves=18)
lin_mm(10, 110, 20, 110, ves=18)
lin_mm(10, 130, 20, 130, ves=18)
t_mm(7.5, 122.5, 2.5, "Согласовано", rot=math.pi / 2)

# ---------------- сохранить, печать ----------------
DS = HERE.replace("\\", "/")
DWG, PDF = DS + "/genplan_v3.dwg", DS + "/genplan_v3.pdf"
a0, a1 = L(0, 0), L(W_, H_)
cmd.append('(command "_.ZOOM" "_E")')
cmd.append('(command "_.SAVEAS" "2018" %s)' % s_(DWG))
cmd.append('(command "_.-PLOT" "_Y" "" "DWG To PDF.pc3" "ISO без полей A3 (420.00 x 297.00 мм)" "_M" "_L" "_N" "_W" '
           '(list %.4f %.4f) (list %.4f %.4f) "2=1" "_C" "_Y" "." "_Y" "" %s "_N" "_Y")'
           % (a0[0], a0[1], a1[0], a1[1], s_(PDF)))
cmd.append("_.QUIT")
cmd.append("_Y")


def zapusk():
    scr = os.path.join(HERE, "genplan_v3.scr")
    io.open(scr, "w", encoding="cp1251").write("\n".join(cmd) + "\n")
    for f_ in (DWG, PDF):
        if os.path.exists(f_):
            os.remove(f_)
    log = os.path.join(HERE, "_tmp", "acad_log.txt")
    if not os.path.isdir(os.path.dirname(log)):
        os.makedirs(os.path.dirname(log))
    with open(log + ".raw", "wb") as f:
        try:
            subprocess.run([ACC, "/s", scr], stdout=f, stdin=subprocess.DEVNULL, timeout=300)
        except subprocess.TimeoutExpired:
            print("AutoCAD: превышено время")
    out = open(log + ".raw", "rb").read().decode("utf-16-le", errors="replace")
    io.open(log, "w", encoding="utf-8").write(out)
    oshibki = [s for s in out.splitlines() if "ошибка" in s.lower() or "неизвестная команда" in s.lower()
               or "error" in s.lower()]
    return oshibki


# данные для профиля дворовой сети
dannye = dict(
    kolodcy={k: dict(x=round(x, 3), y=round(y, 3), zeml=round(zeml(x, y), 3)) for k, (x, y) in KOL.items()},
    lotok=REZ["lotok"], uchastki=[dict(ot=a, do=b, L=d_["L"], i=d_["i"], d=160) for d_, (a, b) in zip(DVOR, PARY)],
    vypusk=dict(L=L_VYP, i=U_VYP["i"], lotok_stena=LOT_VYP), vvod=dict(L_vk=L_VK, L_gvk=L_GVK, z_stena=Z0 + Z_VV_OTN,
                                                                        z_gvk=Z_VV_GVK),
    gorizontali=gorizontali, z0=Z0)
json.dump(dannye, io.open(os.path.join(HERE, "genplan_v3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    print("горизонтали:", gorizontali)
    for p in proverki:
        print("проверка глубины: %s — земля %s, ось/лоток %s, глубина %s м (нужно не менее %s)" % p)
    print("команд AutoLISP:", len(cmd), "| самая длинная строка:", max(len(c) for c in cmd))
    if "--bez-autocad" not in sys.argv:
        osh = zapusk()
        print("DWG:", os.path.exists(DWG), "| PDF:", os.path.exists(PDF))
        for s in osh[:20]:
            print("  AutoCAD:", s)
