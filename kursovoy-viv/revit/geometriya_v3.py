"""Геометрия модели варианта 3 для Revit: оси, уровни, стены, двери, окна, лестницы, перекрытия, приборы, трубы.

Запуск: py geometriya_v3.py  ->  geometriya_v3.json (читают кнопки вкладки «Курсовой ВиВ»), сводка и проверки в консоли.

Система координат: X вдоль здания от оси 1, Y от оси А, Z от 0,000; всё в метрах.
Секция 1 — оси 1–11. Секция 2 — зеркальная копия секции 1 относительно оси 11 (стык секций), X' = 45 − x.
Стены, проёмы и окна сняты с растрового плана задания (kursovoy-viv/pz/plan_v3.png): линии распознаны программно,
координаты приведены к осям (несущие стены 420 мм по осям, перегородки 100 мм).
Санузлы — по образцу преподавателя: приборы вдоль короба (обшивка 50 мм), трубы в коробе, стояки В1 и К1 в коробе
за унитазом, у каждой квартиры свои (СП 30.13330.2020, п. 18.6); холодная вода к приборам слева.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REZ = json.load(open(os.path.join(HERE, "..", "calc", "rezultaty_v3.json"), encoding="utf-8"))
IZ = REZ["iznach"]
sys.path.insert(0, os.path.join(HERE, "..", "calc"))
from normy import alpha_b2          # noqa: E402

L_SEK = 22.5
# деформационный шов между секциями: у каждой секции своя торцевая стена 420 мм по своей оси (11 и 12),
# зазор 30 мм; секция 2 — зеркало секции 1 относительно середины шва
T_TORC, SHOV = 0.42, 0.03
DSH = T_TORC + SHOV                 # расстояние между осями 11 и 12
ZERK = 2 * L_SEK + DSH              # x' = ZERK - x для секции 2
N_SEK, N_ET, H_ET = IZ["N_SEK"], IZ["N_ET"], IZ["H_ET"]
OSI_X = [0.0, 3.5, 6.5, 9.2, 10.0, 12.5, 13.7, 15.7, 16.5, 19.0, 22.5]      # оси 1-11 секции 1
OSI_Y = [("А", 0.0), ("Б", 1.3), ("В", 6.8), ("Г", 11.3), ("Д", 12.8)]
B = 12.8
L = ZERK                      # между крайними осями (1 и 22)
E = 0.06                      # ось наружной стены 520 мм смещена наружу от координационной оси
Y_IN0, Y_IN1 = 0.2, B - 0.2   # внутренние грани наружных стен по осям А и Д
Z_P = -IZ["H_PODVAL"]
Z_KR = N_ET * H_ET            # верх перекрытия последнего этажа (плоская кровля)


class Sek(object):
    """Перевод локальных координат секции в координаты здания (секция 2 — зеркало относительно середины шва)."""

    def __init__(self, s):
        self.s = s
        self.mir = s == 1

    def x(self, v):
        return ZERK - v if self.mir else v

    def sx(self):
        return -1 if self.mir else 1

    def p(self, x, y, z=None):
        return (self.x(x), y) if z is None else (self.x(x), y, z)

    def d(self, dx, dy):
        return (dx * self.sx(), dy)


SEKCII = [Sek(s) for s in range(N_SEK)]

# ---------------- уровни ----------------
urovni = [dict(imya="Подвал", z=Z_P)]
urovni += [dict(imya="Этаж %02d" % k, z=round((k - 1) * H_ET, 3)) for k in range(1, N_ET + 1)]
urovni.append(dict(imya="Кровля", z=round(Z_KR, 3)))
ETAZHI = [u["imya"] for u in urovni if u["imya"].startswith("Этаж")]

# ---------------- оси ----------------
osi_x = sorted(set([round(x, 3) for x in OSI_X] + [round(ZERK - x, 3) for x in OSI_X]))     # 1-11 и 12-22
osi = [dict(imya=str(i + 1), p1=[x, -2.5], p2=[x, B + 2.5]) for i, x in enumerate(osi_x)]
osi += [dict(imya=nm, p1=[-2.5, y], p2=[L + 2.5, y]) for nm, y in OSI_Y]

# ================= АРХИТЕКТУРА СЕКЦИИ (локальные координаты секции 1) =================
# стена: (p1, p2, тип, где): где = etazhi | podval | vse
YV = 6.8                      # несущая стена по оси В, 420 мм: грани 6,59 и 7,01
VN, VV = YV - 0.21, YV + 0.21
STENY_SEK = [
    # тёплые стены лоджий (520 мм) по осям Б и Г в пролётах 1-2 и 10-11; направление — наружной стороной в лоджию
    # (наружная грань стены Revit — слева по ходу): по оси Б — справа налево, по оси Г — слева направо
    ((3.29, 1.26), (0.2, 1.26), "nar", "etazhi"), ((0.2, 11.35), (3.29, 11.35), "nar", "etazhi"),
    ((22.29, 1.26), (19.21, 1.26), "nar", "etazhi"), ((19.21, 11.35), (22.29, 11.35), "nar", "etazhi"),
    # несущие 420 мм
    # ось 2: на этажах в зоне коридора стены нет (план задания), в подвале — на всю глубину
    ((3.5, Y_IN0), (3.5, Y_IN1), "nes", "podval"),
    ((3.5, Y_IN0), (3.5, 5.53), "nes", "etazhi"), ((3.5, VV), (3.5, Y_IN1), "nes", "etazhi"),
    ((6.5, Y_IN0), (6.5, 5.53), "nes", "vse"), ((6.5, VV), (6.5, Y_IN1), "nes", "vse"),
    ((9.2, Y_IN0), (9.2, 5.53), "nes", "vse"),
    ((10.0, 8.105), (10.0, Y_IN1), "nes", "vse"), ((12.5, 8.105), (12.5, Y_IN1), "nes", "vse"),
    ((13.7, Y_IN0), (13.7, 5.53), "nes", "vse"),
    ((15.7, VV), (15.7, Y_IN1), "nes", "vse"),
    ((16.5, Y_IN0), (16.5, 5.53), "nes", "vse"),
    ((19.0, Y_IN0), (19.0, Y_IN1), "nes", "vse"),
    ((0.2, YV), (17.83, YV), "nes", "vse"), ((19.21, YV), (22.29, YV), "nes", "vse"),
    # коридоры (перегородки 100 мм)
    ((3.71, 5.575), (8.99, 5.575), "per", "etazhi"),
    ((13.91, 5.575), (18.79, 5.575), "per", "etazhi"),
    ((6.71, 8.055), (12.29, 8.055), "per", "etazhi"),
    # входы в квартиры А и В — перегородки поперёк коридора у откосов на плане задания (x 8,4 и 14,6);
    # между ними — этажная площадка, с неё же через проём в стене по оси В — вход в квартиру Б
    ((8.39, 5.625), (8.39, VN), "per", "etazhi"), ((14.62, 5.625), (14.62, VN), "per", "etazhi"),
    # лифтовая шахта и проход у лифта, простенки тамбура
    ((10.68, 3.32), (10.68, 5.525), "beton", "vse"), ((9.41, 3.42), (10.78, 3.42), "beton", "vse"),
    ((9.41, 5.575), (9.84, 5.575), "per", "etazhi"), ((10.43, 5.575), (10.78, 5.575), "per", "etazhi"),
    # проход от входа в подъезд к лифту — только на 1-м этаже (на типовых этажах это часть лестничной площадки)
    ((10.61, 1.52), (10.61, 3.32), "per", "Этаж 01"), ((10.865, Y_IN0), (10.865, 1.0), "per", "Этаж 01"),
    ((9.79, 1.26), (9.41, 1.26), "nar", "etazhi"), ((11.19, 1.26), (10.54, 1.26), "nar", "etazhi"),
    ((13.49, 1.26), (12.84, 1.26), "nar", "etazhi"),
    # санузел кв. А (оси 1-2 / Б-В): перегородка по оси x 2,27 (сдвинута от 1,97 на плане — ванна 1500 с коробом)
    ((0.2, 4.165), (2.51, 4.165), "per", "etazhi"), ((2.27, 4.215), (2.27, VN), "per", "etazhi"),
    ((0.5, 5.75), (2.22, 5.75), "per", "etazhi"), ((0.475, 4.215), (0.475, VN), "korob", "etazhi"),
    # санузел кв. Б (оси 7-8 / В-Г)
    ((13.62, VV), (13.62, 9.54), "per", "etazhi"), ((13.67, 9.49), (15.49, 9.49), "per", "etazhi"),
    ((13.67, 7.855), (15.19, 7.855), "per", "etazhi"), ((15.215, VV), (15.215, 9.44), "korob", "etazhi"),
    # санузел кв. В (оси 8-9 / В-Г) — зеркально санузлу Б относительно оси 8
    ((17.78, VV), (17.78, 9.54), "per", "etazhi"), ((15.91, 9.49), (17.73, 9.49), "per", "etazhi"),
    ((16.21, 7.855), (17.73, 7.855), "per", "etazhi"), ((16.185, VV), (16.185, 9.44), "korob", "etazhi"),
    # подвал (техподполье): насосная с водомерным узлом — отсек в осях 2-3 / А-В, перегородка с дверью в коридор
    ((3.71, 5.575), (6.29, 5.575), "per", "podval"),
]
STENA_OS11 = ((22.5, Y_IN0), (22.5, Y_IN1), "nes", "vse")        # торцевая стена секции у деформационного шва

# помещения (точка внутри, наименование, группа: 0 — общие, 1/2/3 — кв. А/Б/В); нумерация «этаж.группа.номер»
POMESCH_ETAZH = [
    (11.9, 3.0, "Лестнично-лифтовой холл", 0),
    (5.0, 6.1, "Прихожая", 1), (1.5, 2.8, "Кухня", 1), (1.7, 9.0, "Жилая комната", 1),
    (5.0, 3.0, "Жилая комната", 1), (7.8, 3.0, "Жилая комната", 1), (1.2, 5.0, "Ванная", 1), (1.2, 6.2, "Уборная", 1),
    (1.7, 12.1, "Лоджия", 1), (1.7, 0.6, "Лоджия", 1),
    (9.5, 7.5, "Прихожая", 2), (14.0, 11.0, "Кухня", 2), (5.0, 9.8, "Жилая комната", 2),
    (8.2, 10.3, "Жилая комната", 2), (11.2, 10.3, "Жилая комната", 2), (14.4, 8.6, "Ванная", 2), (14.4, 7.4, "Уборная", 2),
    (16.0, 6.1, "Прихожая", 3), (17.3, 11.0, "Кухня", 3), (15.1, 3.0, "Жилая комната", 3),
    (17.7, 3.0, "Жилая комната", 3), (20.7, 4.0, "Жилая комната", 3), (20.7, 9.0, "Жилая комната", 3),
    (16.9, 8.6, "Ванная", 3), (16.9, 7.4, "Уборная", 3), (20.7, 12.1, "Лоджия", 3), (20.7, 0.6, "Лоджия", 3),
]
POMESCH_PODVAL = [
    (5.0, 3.0, "Насосная"), (12.0, 3.0, "Техподполье"), (1.6, 3.0, "Техподполье"), (1.6, 11.0, "Техподполье"),
    (5.0, 11.0, "Техподполье"), (8.2, 11.0, "Техподполье"), (20.7, 3.0, "Техподполье"), (20.7, 11.0, "Техподполье"),
]
# границы помещений в открытых проёмах (кухня — прихожая), типовой этаж
RAZDEL_ETAZH = [((2.51, 4.165), (3.29, 4.165)), ((12.71, 9.54), (13.57, 9.54)), ((17.83, 9.54), (18.79, 9.54))]

D760 = ["AC_Дверь_Однопольная_Деревянная", "760х2080h М Л"]
D860 = ["AC_Дверь_Однопольная_Деревянная", "860х2080h М Л"]
D_VH = ["AC_Дверь_Двупольная_Стальная", "1360х2080h Н"]
OK_2 = ["B2B_Окно_2створки", "1470(870)х1320h"]
OK_1 = ["B2B_Окно_1створка", "870х1460h"]
BDV = ["B2B_БДверь_1створка", "870х2060h Л"]
# двери: (x, y, тип, где, (dx, dy) — куда открывается полотно); хост — стена, на оси которой лежит точка.
# Открывание: комнатные и балконные — в комнату, ванная и уборная — наружу (в прихожую), входные в квартиры —
# внутрь квартиры, двери лифтового холла — к лестнице (путь эвакуации), входы в подъезд — наружу.
DVERI_SEK = [
    (4.985, 5.575, D760, "etazhi", (0, -1)),
    (7.255, 5.575, D760, "etazhi", (0, -1)),
    (6.5, 7.605, D760, "etazhi", (-1, 0)), (8.015, 8.055, D760, "etazhi", (0, 1)),
    (11.155, 8.055, D760, "etazhi", (0, 1)),
    (15.84, 5.575, D760, "etazhi", (0, -1)), (17.055, 5.575, D760, "etazhi", (0, -1)),
    (19.0, 6.115, D760, "etazhi", (1, 0)), (19.0, 7.605, D760, "etazhi", (1, 0)),
    # в комнату кв. А (с отступом 0,1 м от стены уборной — не в одном углу с её дверью) и вход в кв. Б
    (2.82, YV, D760, "etazhi", (0, 1)), (8.85, YV, D860, "etazhi", (0, 1)),
    (8.39, 6.11, D860, "etazhi", (-1, 0)), (14.62, 6.11, D860, "etazhi", (1, 0)),     # входы в кв. А и В
    (2.27, 4.60, D760, "etazhi", (1, 0)), (2.27, 6.20, D760, "etazhi", (1, 0)),       # ванная и уборная кв. А
    (13.62, 7.40, D760, "etazhi", (-1, 0)), (13.62, 9.05, D760, "etazhi", (-1, 0)),
    (17.78, 7.40, D760, "etazhi", (1, 0)), (17.78, 9.05, D760, "etazhi", (1, 0)),
    (12.34, -E, D_VH, "Этаж 01", (0, -1)), (9.92, -E, D860, "Этаж 01", (0, -1)),      # вход в подъезд, выход у лифта
    (1.20, 11.35, BDV, "etazhi", (0, -1)), (21.29, 11.35, BDV, "etazhi", (0, -1)),    # балконные двери на лоджии
    (1.20, 1.26, BDV, "etazhi", (0, 1)), (21.29, 1.26, BDV, "etazhi", (0, 1)),        # по осям Г и Б
    # подвал (техподполье): вход с улицы через приямок по фасаду А, насосная, двери во все отсеки
    (15.1, -E, D860, "Подвал", (0, -1)), (5.0, 5.575, D860, "Подвал", (0, 1)),
    (3.5, 6.1, D860, "Подвал", (-1, 0)), (1.6, YV, D860, "Подвал", (0, 1)),
    (5.0, YV, D860, "Подвал", (0, 1)), (8.0, YV, D860, "Подвал", (0, 1)),
    (19.0, 6.1, D860, "Подвал", (1, 0)), (19.0, 7.6, D860, "Подвал", (1, 0)),
]
# окна: (x, y, тип, где, подоконник)
OKNA_SEK = []
for x in (1.6, 4.955, 8.155, 11.2, 14.0, 17.24, 20.75):
    OKNA_SEK.append((x, B + E, OK_2, "etazhi", 0.9))
for x in (1.6, 4.99, 7.82, 15.03, 17.70, 20.75):
    OKNA_SEK.append((x, -E, OK_2, "etazhi", 0.9))
OKNA_SEK += [(12.34, -E, OK_2, "verh", 1.2), (9.92, -E, OK_1, "verh", 1.2),      # лестничная клетка на 2-11 эт.
             # окна рядом с балконными дверями (блок «дверь + окно», простенок 30 мм)
             (2.10, 1.26, OK_1, "etazhi", 0.8), (20.39, 1.26, OK_1, "etazhi", 0.8),
             (2.10, 11.35, OK_1, "etazhi", 0.8), (20.39, 11.35, OK_1, "etazhi", 0.8)]
# лестница: двухмаршевая, марш вверх от этажной площадки на юг (слева), второй марш на север (справа)
LESTNICA_SEK = dict(m1=((11.435, 5.62), (11.435, 3.30), 1.11), m2=((12.79, 3.30), (12.79, 5.62), 1.08))
# отверстия в перекрытиях: лестничная клетка и шахта лифта
OTVERSTIYA_SEK = [[(9.41, 3.32), (9.41, 5.525), (13.49, 5.525), (13.49, 1.52), (10.78, 1.52), (10.78, 3.32)]]

# ---------------- архитектура здания ----------------
X_SHOV = L_SEK + T_TORC / 2         # наружная грань торцевой стены секции 1 у шва
# контур секции 1 по часовой (наружу — внешняя сторона стен); сторону у шва закрывает торцевая стена по оси 11
KONTUR_SEK = [(-E, -E), (-E, B + E), (X_SHOV, B + E), (X_SHOV, -E)]
NAR_SEK = [((-E, -E), (-E, B + E)), ((-E, B + E), (X_SHOV, B + E)), ((X_SHOV, -E), (-E, -E))]
steny, dveri, okna, lestnicy, otverstiya = [], [], [], [], []


def stena(p1, p2, tip, gde):
    steny.append(dict(p1=[round(p1[0], 3), round(p1[1], 3)], p2=[round(p2[0], 3), round(p2[1], 3)], tip=tip, gde=gde))


FUND_IN0, FUND_IN1 = -E + 0.158, B + E - 0.158    # внутренние грани фундаментных стен подвала


def v_podvale(p1, p2):
    """Стена в подвале доходит до фундаментной: торцы на внутренних гранях наружных стен этажа (0,2 / 12,6)
    переносятся на грани фундаментных стен (иначе между стенами подвала и фундаментом остаётся щель)."""
    def ok(p):
        x, y = p
        y = FUND_IN0 if abs(y - Y_IN0) < 1e-6 else (FUND_IN1 if abs(y - Y_IN1) < 1e-6 else y)
        x = FUND_IN0 if abs(x - Y_IN0) < 1e-6 else x
        return (x, y)
    return ok(p1), ok(p2)


def steny_sek():
    out = [(a, b, "nar", "etazhi") for a, b in NAR_SEK] + [(a, b, "fund", "podval") for a, b in NAR_SEK]
    for p1, p2, tip, gde in STENY_SEK + [STENA_OS11]:
        if gde == "vse":
            out.append((p1, p2, tip, "etazhi"))
            q1, q2 = v_podvale(p1, p2)
            out.append((q1, q2, tip, "podval"))
        elif gde == "podval":
            q1, q2 = v_podvale(p1, p2)
            out.append((q1, q2, tip, gde))
        else:
            out.append((p1, p2, tip, gde))
    return out


otv_sek = {}
pomescheniya, razdeliteli = [], []
for M in SEKCII:
    sch = {}
    for x, y, imya, gr in POMESCH_ETAZH:
        grp = 1 + gr + 4 * M.s
        sch[grp] = sch.get(grp, 0) + 1
        pomescheniya.append(dict(uroven="Этаж 02", x=round(M.x(x), 3), y=y, imya=imya,
                                 nomer="02.%02d.%02d" % (grp, sch[grp])))
    for k, (x, y, imya) in enumerate(POMESCH_PODVAL, 1):
        pomescheniya.append(dict(uroven="Подвал", x=round(M.x(x), 3), y=y, imya=imya,
                                 nomer="00.%02d.%02d" % (1 + M.s, k)))
    for p1, p2 in RAZDEL_ETAZH:
        razdeliteli.append(dict(uroven="Этаж 02", p1=list(M.p(*p1)), p2=list(M.p(*p2))))
    for p1, p2, tip, gde in steny_sek():
        if M.mir:          # отражение меняет обход: концы местами, чтобы наружная сторона стен осталась снаружи
            p1, p2 = p2, p1
        stena(M.p(*p1), M.p(*p2), tip, gde)
    for x, y, tip, gde, (ox, oy) in DVERI_SEK:
        dveri.append(dict(x=round(M.x(x), 3), y=y, tip=tip, gde=gde, otkr=list(M.d(ox, oy))))
    for x, y, tip, gde, pod in OKNA_SEK:
        okna.append(dict(x=round(M.x(x), 3), y=y, tip=tip, gde=gde, podokonnik=pod))
    m = {}
    for k, ((a, b), (c, d), w) in LESTNICA_SEK.items():
        m[k] = dict(p1=list(M.p(a, b)), p2=list(M.p(c, d)), shir=w)
    lestnicy.append(m)
    otv_sek[M.s] = [[[round(M.x(x), 3), y] for x, y in poly] for poly in OTVERSTIYA_SEK]
    otverstiya += otv_sek[M.s]


def kontur_sek(M):
    pts = [list(M.p(x, y)) for x, y in KONTUR_SEK]
    return pts[::-1] if M.mir else pts


# перекрытия и покрытие — отдельно по секциям (шов проходит через все конструкции)
perekr = [dict(uroven=u, kontur=kontur_sek(M), tip="perekr", otverstiya=otv_sek[M.s]) for u in ETAZHI for M in SEKCII]
perekr += [dict(uroven="Подвал", kontur=kontur_sek(M), tip="pol_podv", otverstiya=[]) for M in SEKCII]
krovlya = [dict(uroven="Кровля", kontur=kontur_sek(M), tip="krovlya") for M in SEKCII]

# ================= ПРИБОРЫ И СЕТИ =================
P_C = REZ["P"]["c"]
N_PR = 4
ET_REG = set(REZ["et_reg"])          # этажи с регуляторами давления на квартирных вводах
VGP = {15: 15.7, 20: 21.2, 25: 27.1, 32: 35.9, 40: 41.0, 50: 53.0}


def shevelev_v(q, dn):
    d = (VGP[dn] - 1.0) / 1000
    return q / 1000 / (math.pi * d * d / 4)


def dn_po_n(n, dmin):
    """Диаметр В1 по числу приборов выше сечения — правилом raschet_v3.py (v ≤ 1,2 м/с)."""
    q = 5 * alpha_b2(n * P_C, "floor") * 0.2
    for dn in (25, 32, 40, 50):
        if dn >= dmin and shevelev_v(q, dn) <= 1.2:
            return dn
    return 50


pribory, seti, troyniki, kresty, armatura, svyazi, mufty, stoyaki = [], [], [], [], [], [], [], []
gabarity_pr = []          # (id, x0, y0, x1, y1, z0, z1)

# соединители приборов, мм, в системе семейства (журнал кнопки «02»); ванна ВСт 1500
SOED = {"vanna": dict(cold=(-12, 425, 700), hot=(-12, 275, 700), san=(200, 350, 95)),
        "unitaz": dict(cold=(-200, -95, 700), san=(0, -70, 180)),
        "umyv": dict(cold=(12, -75, 800), hot=(-12, -75, 800), san=(57, -180, 558)),
        "moyka": dict(cold=(407, -30, 850), hot=(382, -30, 850), san=(352, -130, 558))}
# Холодная вода подводится слева (если смотреть на прибор спереди) — как в образце и по СП 30 (холодная левее
# горячей). У умывальника, мойки и ванны ADSK холодная справа -> экземпляры отражаются относительно оси симметрии.
ZERKALO = {"umyv": ("x", 0.0), "moyka": ("x", 400.0), "vanna": ("y", 350.0)}
GABARIT = {"vanna": (-12, 0, 0, 1500, 700, 550), "unitaz": (-200, -660, 0, 200, 0, 750),
           "umyv": (-275, -420, 0, 275, 0, 915), "moyka": (0, -490, 0, 800, 35, 965)}
PR_FAM = {"vanna": ("ADSK_Ванна стальная эмалированная_ГОСТ23695-2016", "ВСт 1500"),
          "unitaz": ("ADSK_Унитаз напольный_ГОСТ 30493-2017", "Прямой выпуск"),
          "umyv": ("ADSK_Умывальник со смесителем", "Умывальник"),
          "moyka": ("ADSK_Мойка кухонная со смесителем", "Мойка кухонная со смесителем и сифоном")}
ARM = {"kran15": ("VALTEC_VT.214.N_КранШаровой ВР", '1/2"', -0.024, 0.024),
       "kran25": ("VALTEC_VT.214.N_КранШаровой ВР", '1"', -0.032, 0.032),
       "kran32": ("VALTEC_VT.214.N_КранШаровой ВР", '1 1/4"', -0.036, 0.036),
       "kran40": ("VALTEC_VT.214.N_КранШаровой ВР", '1 1/2"', -0.042, 0.041),
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
    if key in ZERKALO:
        os_, c = ZERKALO[key]
        if os_ == "x":
            lx = 2 * c - lx
        else:
            ly = 2 * c - ly
    return lx, ly


def pribor(key, x, y, th, ur, zf):
    pid = len(pribory)
    zk = ZERKALO.get(key)
    pribory.append(dict(id=pid, fam=PR_FAM[key][0], tip=PR_FAM[key][1], x=round(x, 4), y=round(y, 4),
                        th=round(th, 3), ur=ur, key=key, mir=dict(os=zk[0], c=zk[1] / 1000) if zk else None))
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
    pribory[-1]["soed"] = {k: R(v) for k, v in c.items()}
    return pid, c


VEK = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}


def pribor2(key, M, wloc, face, along, zf, ur):
    """Прибор у стены. wloc — направление от прибора к стене (лок.), face — координата грани стены (лок.);
    along — для умывальника и унитаза центр, для мойки и ванны начало диапазона вдоль стены."""
    wx, wy = VEK[wloc]
    wx *= M.sx()
    th0 = math.degrees(math.atan2(wy, wx))
    th = th0 - 180 if key == "vanna" else th0 - 90
    th = (th + 180) % 360 - 180
    po_x = wx != 0
    n_face = M.x(face) if po_x else face

    def P(n, a):
        return (n, a) if po_x else (a, n)
    if key in ("umyv", "unitaz"):
        a = along if po_x else M.x(along)
        x, y = P(n_face, a)
    else:
        dl = 0.8 if key == "moyka" else 0.7
        otst = 0.035 if key == "moyka" else 0.012
        n0 = n_face - (wx if po_x else wy) * otst
        u = rot(1, 0, th) if key == "moyka" else rot(0, 1, th)
        ua = u[1] if po_x else u[0]
        if po_x:
            lo, hi = along, along + dl
        else:
            lo, hi = sorted([M.x(along), M.x(along + dl)])
        x, y = P(n0, lo if ua > 0 else hi)
    return pribor(key, x, y, th, ur, zf)


def truba(sys_, pt, d, pts, ur):
    rid = len(seti)
    seti.append(dict(id=rid, sys=sys_, pt=pt, d=d, pts=[R(p) for p in pts], ur=ur))
    return rid


def svyaz(a, b):
    svyazi.append(dict(a=a, b=b))


def troynik(m1, m2, b):
    troyniki.append(dict(m1=m1, m2=m2, b=b))


def arm(key, p, d, ur):
    fam, tip, xin, xout = ARM[key]
    th = math.degrees(math.atan2(d[1], d[0]))
    ins = (p[0] - d[0] * xin, p[1] - d[1] * xin, p[2])
    out = (ins[0] + d[0] * xout, ins[1] + d[1] * xout, p[2])
    aid = len(armatura)
    armatura.append(dict(id=aid, key=key, fam=fam, tip=tip, x=round(ins[0], 4), y=round(ins[1], 4), z=round(ins[2], 4),
                         th=round(th, 3), ur=ur))
    return aid, out


def vetka(sys_, pt, d, pts_do, napr, items, ur, gap=0.02, first=0.07):
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


Z_RAZV = 0.3        # ось поквартирной разводки над полом (методичка: 15-40 см)
Z_UZEL = 1.0        # квартирный узел учёта на ответвлении от стояка: кран, фильтр, счётчик, регулятор
I_OTV = 0.03        # уклон поэтажных отводов Ø50
I_UN = 0.02         # уклон отвода от унитаза Ø110
Z_TR50 = -0.09      # тройник стояка для отвода Ø50 (в конструкции пола), ниже тройника унитаза на вылет двух тройников


def razrezat(sys_, pt, d, pts3, rez, ur):
    out, cur = [], [pts3[0]]
    for a, b in zip(pts3[:-1], pts3[1:]):
        na_otr = []
        for (x, y) in rez:
            L_ = math.hypot(b[0] - a[0], b[1] - a[1])
            t = math.hypot(x - a[0], y - a[1])
            if L_ > 0 and 1e-6 < t < L_ - 1e-6 and abs(t + math.hypot(b[0] - x, b[1] - y) - L_) < 1e-6:
                na_otr.append((t, (x, y, a[2] + (b[2] - a[2]) * t / L_)))
        for _, p in sorted(na_otr):
            cur.append(p)
            out.append(truba(sys_, pt, d, cur, ur))
            cur = [p]
        cur.append(b)
    out.append(truba(sys_, pt, d, cur, ur))
    return out


utoplen = set()         # соединители, лежащие в плоскости обшивки короба (ванны): подъём внутри короба


def k_priboru(p, conn, xh, z):
    if tuple(round(v, 4) for v in conn) in utoplen:
        # подъём внутри короба в 110 мм от соединителя: патрубок смесителя ванны DN20, подводка DN15 —
        # на горизонтальном участке помещаются отвод и переход 15х20 (иначе Revit оставляет обрезок трубы)
        dx = abs(conn[0] - xh)
        xv = xh if 0.11 <= dx < 0.16 else conn[0] - math.copysign(0.11, conn[0] - xh)
        pts = [p] + ([(xv, conn[1], z)] if abs(xv - p[0]) > 1e-6 else [])
        return pts + [(xv, conn[1], conn[2]), conn]
    if abs(conn[0] - p[0]) < 0.005:            # соединитель над линией разводки — прямой подъём
        return [p, conn]
    return [p, (conn[0], conn[1], z), conn]


def nogi(xh, y0, z, ftaps, ur):
    """Ветка разводки от точки (xh, y0, z) вдоль оси Y. ftaps — [(соединитель, id прибора, обход)], по порядку;
    последний прибор — конец ветки (обход — точки (x, y) перед ним, например выход из короба на кухню)."""
    ids, uzly, cur = [], [], [(xh, y0, z)]
    for i, (conn, fid, obhod) in enumerate(ftaps):
        if i < len(ftaps) - 1:
            p = (xh, conn[1], z)
            cur.append(p)
            ids.append(truba("V1", "stal", 15, cur, ur))
            uzly.append((p, conn, fid))
            cur = [p]
        else:
            xe = xh
            for (wx, wy) in (obhod or []):
                cur.append((wx, wy, z))
                xe = wx
            cur += k_priboru((xe, conn[1], z), conn, xe, z)
            ids.append(truba("V1", "stal", 15, cur, ur))
            svyaz((ids[-1], 1), dict(fix=fid, kind="cold"))
    for i, (p, conn, fid) in enumerate(uzly):
        rb = truba("V1", "stal", 15, k_priboru(p, conn, xh, z), ur)
        troynik((ids[i], 1), (ids[i + 1], 0), (rb, 0))
        svyaz((rb, 1), dict(fix=fid, kind="cold"))
    return ids[0]


def kv_v1(k, zf, ur, rs_v, stoyak_xy, napr, y_op, nogi_, xh=None):
    """Квартирный ввод: тройник на стояке на высоте Z_UZEL, узел учёта вдоль шахты, опуск к разводке на y_op,
    одна или две ветки разводки (nogi_ — список списков приборов) по линии x = xh (по умолчанию — ось стояка)."""
    xr, yr = stoyak_xy
    xh = xr if xh is None else xh
    z1 = zf + Z_UZEL
    items = ["kran15", "filtr15", "sch15"] + (["reg15"] if k in ET_REG else [])
    r0, (ra, _), p = vetka("V1", "stal", 15, [(xr, yr, z1)], napr, items, ur, first=0.15)
    rs_v.append((z1, (r0, 0)))
    hvost = [R((xr, y_op, z1))] + ([R((xh, y_op, z1))] if abs(xh - xr) > 1e-6 else []) + [R((xh, y_op, zf + Z_RAZV))]
    seti[ra]["pts"] = seti[ra]["pts"][:1] + hvost
    starty = [nogi(xh, y_op, zf + Z_RAZV, f, ur) for f in nogi_]
    if len(starty) == 1:
        svyaz((ra, 1), (starty[0], 0))
    else:
        troynik((starty[0], 0), (starty[1], 0), (ra, 1))


def otvod_k1(x_l, y_r, z_r, napr, pr, ur):
    """Поэтажный отвод Ø50 вдоль x = x_l к стояку (x_l, y_r): приборы pr = [(соединитель, id)], первый — дальний.
    Присоединения — опуск и косой участок 45° в плане (косые тройники, п. 18.5 СП 30); уклон I_OTV."""
    def zl(y):
        return z_r + I_OTV * abs(y - y_r)
    J = [(conn[1] + napr * abs(conn[0] - x_l), abs(conn[0] - x_l)) for conn, _ in pr]
    (c0, f0), (y0, dl0) = pr[0], J[0]
    if dl0 < 0.02:                     # слив над линией отвода: опуск и отвод 90° в начале линии
        pts = [c0, (x_l, c0[1], zl(c0[1])), (x_l, y_r, z_r)]
    else:
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


# стояки квартир в локальных координатах секции: (В1, К1)
# В1 — у стены (разводка вдоль стены и в коробе, и на кухне); К1 — на одной линии со сливом мойки, чтобы отвод
# от мойки шёл прямо, без коротких косых вставок
# В1 — у стены шахты, на 0,32 м от стояка К1 в сторону ванны: разводка В1 не проходит мимо стояка К1
# (как в образце преподавателя), подводка к бачку обрывается в 0,2 м от стояка К1
ST_V = {"A": (0.425, 5.90), "B": (15.265, 7.74), "C": (16.135, 7.75)}
ST_K = {"A": (0.365, 6.22), "B": (15.325, 7.42), "C": (16.075, 7.43)}
# линия поквартирной разводки — у стены шахты, на оси патрубка мойки (подъём к мойке прямой); отводы К1 идут
# по оси стояка К1 ближе к коробу, стояк В1 — у короба
X_RAZV = {"A": 0.265, "B": 15.425, "C": 15.975}


def kv_A(M, zf, ur, k, st):
    pt_, ct = pribor2("unitaz", M, "-x", 0.55, 6.22, zf, ur)     # 50 мм от короба — место под подводку
    pv, cv = pribor2("vanna", M, "-x", 0.50, 5.00, zf, ur)
    pu, cu = pribor2("umyv", M, "-x", 0.50, 4.625, zf, ur)
    pm, cm = pribor2("moyka", M, "-x", 0.20, 3.25, zf, ur)
    utoplen.add(tuple(round(v, 4) for v in cv["cold"]))
    xr, yr = M.x(ST_V["A"][0]), ST_V["A"][1]
    y_op = 5.15                               # опуск ниже подвода к ванне: узел учёта (0,75 м) — от стояка до опуска
    nog = [[(cv["cold"], pv, None), (ct["cold"], pt_, None)], [(cu["cold"], pu, None), (cm["cold"], pm, None)]]
    kv_v1(k, zf, ur, st["vA"], (xr, yr), (0, -1), y_op, nog, xh=M.x(X_RAZV["A"]))
    xk, yk = M.x(ST_K["A"][0]), ST_K["A"][1]
    zt, r_un = unitaz_k1(ct, pt_, xk, yk, ur)
    st["kA"].append((zt, [(r_un, 1)]))
    last = otvod_k1(xk, yk, zf + Z_TR50, +1, [(cm["san"], pm), (cu["san"], pu), (cv["san"], pv)], ur)
    st["kA"].append((zf + Z_TR50, [(last, 1)]))


def kv_BC(M, zf, ur, k, st, kv):
    if kv == "B":
        w, face, face_k, y_un, y_op = "+x", 15.19, 15.49, 7.42, 8.49
    else:
        w, face, face_k, y_un, y_op = "-x", 16.21, 15.91, 7.43, 8.50
    otstup = -0.05 if w == "+x" else 0.05      # унитаз в 50 мм от короба — место под подводку к бачку
    pt_, ct = pribor2("unitaz", M, w, face + otstup, y_un, zf, ur)
    pv, cv = pribor2("vanna", M, w, face, 7.94, zf, ur)
    pu, cu = pribor2("umyv", M, w, face, 9.00, zf, ur)
    pm, cm = pribor2("moyka", M, w, face_k, 9.60, zf, ur)
    utoplen.add(tuple(round(v, 4) for v in cv["cold"]))
    xr, yr = M.x(ST_V[kv][0]), ST_V[kv][1]
    # опуск выше подвода к ванне: узел учёта от стояка до опуска; вниз — ванна и унитаз, вверх — умывальник и мойка
    nog = [[(cv["cold"], pv, None), (ct["cold"], pt_, None)], [(cu["cold"], pu, None), (cm["cold"], pm, None)]]
    kv_v1(k, zf, ur, st["v" + kv], (xr, yr), (0, 1), y_op, nog, xh=M.x(X_RAZV[kv]))
    xk, yk = M.x(ST_K[kv][0]), ST_K[kv][1]
    zt, r_un = unitaz_k1(ct, pt_, xk, yk, ur)
    st["k" + kv].append((zt, [(r_un, 1)]))
    last = otvod_k1(xk, yk, zf + Z_TR50, -1, [(cm["san"], pm), (cu["san"], pu), (cv["san"], pv)], ur)
    st["k" + kv].append((zf + Z_TR50, [(last, 1)]))


def stoyak(imya, sys_, x, y, uzly, niz, verh, ur_niz, d_fun, pt):
    uzly = sorted(uzly, key=lambda u: u[0])
    zz = [niz] + [u[0] for u in uzly] + [verh]
    runs = []
    for i in range(len(zz) - 1):
        if zz[i + 1] - zz[i] < 1e-6:
            continue
        runs.append(truba(sys_, pt, d_fun(i, len(uzly)), [(x, y, zz[i]), (x, y, zz[i + 1])], ur_niz(zz[i])))
    for i, (z, vetv) in enumerate(uzly):
        a, b = runs[i], runs[i + 1] if i + 1 < len(runs) else None
        if b is None:
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
st = {}
for M in SEKCII:
    st[M.s] = dict(vA=[], vB=[], vC=[], kA=[], kB=[], kC=[])
    for k in range(1, N_ET + 1):
        zf, ur = (k - 1) * H_ET, "Этаж %02d" % k
        kv_A(M, zf, ur, k, st[M.s])
        kv_BC(M, zf, ur, k, st[M.s], "B")
        kv_BC(M, zf, ur, k, st[M.s], "C")
        for kv in "ABC":
            xk, yk = ST_K[kv]
            mufty.append(dict(x=round(M.x(xk), 4), y=yk, z=round(zf + H_ET - IZ["T_PEREKR"] - 0.05, 3), ur=ur))


# нумерация стояков по часовой стрелке от северо-запада: северные (Б, В) слева направо, затем южные (А) справа налево
def nomera():
    sev = sorted([(M.x(ST_V[kv][0]), M.s, kv) for M in SEKCII for kv in "BC"])
    yug = sorted([(M.x(ST_V["A"][0]), M.s, "A") for M in SEKCII], reverse=True)
    return {(s, kv): i + 1 for i, (_, s, kv) in enumerate(sev + yug)}


NOM = nomera()

# ---------------- подвал: стояки В1, магистраль, ввод, насосная ----------------
Z_MAG = -0.6
Y_MAG = 7.20
UR_P = "Подвал"
VYTYAZHKA = 0.2                        # вытяжная часть над неэксплуатируемой кровлей (п. 18.18 СП 30)

OTSTUP_PODV = {"A": 0.15, "B": -0.15, "C": 0.15}
podvod = {}
for M in SEKCII:
    for kv in "ABC":
        x, y = M.x(ST_V[kv][0]), ST_V[kv][1]
        uzly = [(z, [b]) for z, b in st[M.s]["v" + kv]]

        def d_fun(i, n_uzl):
            return dn_po_n(N_PR * (n_uzl - i) if i > 0 else N_PR * n_uzl, 25)
        imya = "Ст.В1-%d" % NOM[(M.s, kv)]
        runs = stoyak(imya, "V1", x, y, uzly, Z_MAG, max(z for z, _ in uzly), ur_po_z, d_fun, "stal")
        # подводка от магистрали — в 0,15 м от оси стояка в сторону санузла (под ним в подвале свободно),
        # чтобы не задеть низ стояка К1; у стояка — перегиб
        x_b = x + OTSTUP_PODV[kv] * M.sx()
        podvod[imya] = (x, y, runs[0], d_fun(0, len(uzly)), N_PR * N_ET, x_b)

X_TR = 4.0
x_st = {nm: podvod[nm][5] for nm in podvod}
vostok = sorted([nm for nm in podvod if x_st[nm] > X_TR], key=lambda nm: x_st[nm])
zapad = [nm for nm in podvod if x_st[nm] < X_TR]


def dn_mag(n):
    return dn_po_n(n, 32)


def otvetvlenie(nm):
    """Ответвление от магистрали к стояку с краном у основания стояка."""
    x, y, r_st, d, n, x_b = podvod[nm]
    napr = (0, 1) if y > Y_MAG else (0, -1)
    kran = {25: "kran25", 32: "kran32", 40: "kran40"}[d]
    r0, (ra, _), p = vetka("V1", "stal", d, [(x_b, Y_MAG, Z_MAG)], napr, [kran], UR_P, first=0.15)
    seti[ra]["pts"] = seti[ra]["pts"][:1] + [R((x_b, y, Z_MAG)), R((x, y, Z_MAG))]
    svyaz((ra, 1), (r_st, 0))
    return r0


prev_end, ost = None, sum(podvod[nm][4] for nm in vostok)
x_prev = X_TR
mag_vost = []
uchastki_mag = []                      # для сверки с расчётом: (откуда, куда, длина, N)
for i, nm in enumerate(vostok):
    x = x_st[nm]
    r = truba("V1", "stal", dn_mag(ost), [(x_prev, Y_MAG, Z_MAG), (x, Y_MAG, Z_MAG)], UR_P)
    uchastki_mag.append((round(x_prev, 3), round(x, 3), round(x - x_prev, 3), ost, dn_mag(ost)))
    mag_vost.append(r)
    ost -= podvod[nm][4]
    if prev_end is not None:
        troynik(prev_end, (r, 0), (otvetvlenie(vostok[i - 1]), 0))
    prev_end = (r, 1)
    x_prev = x
svyaz(prev_end, (otvetvlenie(vostok[-1]), 0))
nm_z = zapad[0]
r_zap = truba("V1", "stal", dn_mag(podvod[nm_z][4]), [(X_TR, Y_MAG, Z_MAG), (x_st[nm_z], Y_MAG, Z_MAG)], UR_P)
svyaz((r_zap, 1), (otvetvlenie(nm_z), 0))

nas = json.load(open(os.path.join(HERE, "..", "calc", "nasos_v3.json"), encoding="utf-8"))
XP, YP = 5.0, 4.0                       # установка COR-2 (соединители коллекторов на локальной -X)
p_vs = (XP, YP - 0.361, Z_P + 0.168)
p_nap = (XP, YP + 0.480, Z_P + 0.168)
oborud = [dict(fam="COR-MVL_2_32_Revit2019(08.25)", tip=nas["tip"], x=XP, y=YP, th=0, ur=UR_P,
               vs=R(p_vs), nap=R(p_nap))]
# напорная линия установки до тройника магистрали (проектируется только В1: ГВС вне объёма проекта)
N_VSE = sum(podvod[nm][4] for nm in podvod)
r_nap = truba("V1", "stal", 50, [p_nap, (X_TR, p_nap[1], p_nap[2]), (X_TR, p_nap[1], Z_MAG), (X_TR, Y_MAG, Z_MAG)],
              UR_P)
svyaz((r_nap, 0), dict(obor=0, kind="nap"))
troynik((r_zap, 0), (mag_vost[0], 0), (r_nap, 1))
L_NAP = round(sum(math.dist(a, b) for a, b in zip(seti[r_nap]["pts"][:-1], seti[r_nap]["pts"][1:])), 2)

Z_VV = -2.5
Y_ST_A = -E - 0.26                      # наружная грань стены по оси А
r_vv = truba("V1", "pe", 63, [(X_TR, Y_ST_A - 2.0, Z_VV), (X_TR, Y_IN0, Z_VV)], UR_P)
Z_VU = -2.0
r_v1 = truba("V1", "stal", 50, [(X_TR, Y_IN0, Z_VV), (X_TR, 1.5, Z_VV), (X_TR, 1.5, Z_VU), (X_TR, 1.8, Z_VU)], UR_P)
svyaz((r_vv, 1), (r_v1, 0))
r_a, (r_b, _), p = vetka("V1", "stal", 50, [(X_TR, 1.8, Z_VU)], (0, 1), ["kran50"], UR_P, first=0.15)
seti[r_b]["pts"] = seti[r_b]["pts"][:1] + [R((X_TR, 2.35, Z_VU))]
DN_SCH = REZ["schetchik_dom"][0]        # общедомовой счётчик — по расчёту (холодный расход)
r_sch = truba("V1", "stal", DN_SCH, [(X_TR, 2.35, Z_VU), (X_TR, 2.85, Z_VU)], UR_P)  # место счётчика
svyaz((r_b, 1), (r_sch, 0))
r_c, (r_d, _), p = vetka("V1", "stal", 50, [(X_TR, 2.85, Z_VU)], (0, 1), ["kran50"], UR_P, first=0.12)
svyaz((r_sch, 1), (r_c, 0))
seti[r_d]["pts"] = seti[r_d]["pts"][:1] + [R((X_TR, 3.25, Z_VU))]
r_vs = truba("V1", "stal", 50, [(X_TR, 3.25, Z_VU), (X_TR, p_vs[1], Z_VU), (X_TR, p_vs[1], p_vs[2]), p_vs], UR_P)
svyaz((r_vs, 1), dict(obor=0, kind="vs"))
r_o1, (r_o2, _), p = vetka("V1", "stal", 50, [(X_TR, 1.8, Z_VU), (X_TR - 0.2, 1.8, Z_VU)], (0, 1), ["kran50"],
                           UR_P, first=0.4)
seti[r_o2]["pts"] = seti[r_o2]["pts"][:1] + [R((X_TR - 0.2, 3.25, Z_VU)), R((X_TR, 3.25, Z_VU))]
troynik((r_v1, 1), (r_a, 0), (r_o1, 0))
troynik((r_d, 1), (r_vs, 0), (r_o2, 1))

# ---------------- подвал: стояки К1, сборные трубопроводы, выпуски ----------------
# П. 18.4 СП 30: переход стояка в горизонталь — два отвода по 45°; п. 18.5: стояки присоединяются к сборному
# трубопроводу в горизонтальной плоскости под 45° (косой тройник), повороты — не менее двух фасонных частей.
Z_PP = -0.35
Y_ST_D = B + E + 0.26
LOT_ST = -2.0                           # лоток выпуска у наружной стены (99,00 абс.)
I_VN = 0.02
R110 = 0.055
D45 = 0.2
Y_SB = 8.2


def put_z(tochki, z_konec):
    L_ = [0.0]
    for p1, p2 in zip(tochki[:-1], tochki[1:]):
        L_.append(L_[-1] + math.hypot(p2[0] - p1[0], p2[1] - p1[1]))
    return [(x, y, z_konec + I_VN * (L_[-1] - l)) for (x, y), l in zip(tochki, L_)]


def niz_stoyaka(x, y, plan):
    (x1, y1, z1) = plan[0]
    return [(x, y, Z_PP), (x, y, z1 + D45)] + plan


vypuski = []
for M in SEKCII:
    sx = M.sx()
    (xA, yA), (xB, yB), (xC, yC) = [(M.x(ST_K[kv][0]), ST_K[kv][1]) for kv in "ABC"]
    z_vyp = lambda y: LOT_ST + R110 + I_VN * (Y_ST_D - y)          # noqa: E731
    y_tr = Y_SB + 0.3
    r_vy1 = truba("K1", "sml", 100, niz_stoyaka(xA, yA, [(xA, yA + D45, z_vyp(yA + D45)), (xA, y_tr, z_vyp(y_tr))]),
                  UR_P)
    r_vy2 = truba("K1", "sml", 100, [(xA, y_tr, z_vyp(y_tr)), (xA, Y_ST_D + 1.0, z_vyp(Y_ST_D + 1.0))], UR_P)
    vypuski.append(dict(sek=M.s, x=round(xA, 3), y_stena=round(Y_ST_D, 3), lotok=round(LOT_ST, 3)))
    trassa = [(xC, yC + D45), (xC, Y_SB - 0.15), (xC - 0.15 * sx, Y_SB), (xB - 0.3 * sx, Y_SB),
              (xA + 0.3 * sx, Y_SB), (xA, y_tr)]
    pz = put_z(trassa, z_vyp(y_tr))
    r_sb1 = truba("K1", "sml", 100, niz_stoyaka(xC, yC, pz[:4]), UR_P)
    r_sb2 = truba("K1", "sml", 100, pz[3:], UR_P)
    troynik((r_vy1, 1), (r_vy2, 0), (r_sb2, 1))
    t2 = put_z([(xB, yB + D45), (xB, Y_SB - 0.3), (xB - 0.3 * sx, Y_SB)], pz[3][2])
    r_st2 = truba("K1", "sml", 100, niz_stoyaka(xB, yB, t2), UR_P)
    troynik((r_sb1, 1), (r_sb2, 0), (r_st2, 1))
    for kv, (x, y), r_niz in (("A", (xA, yA), r_vy1), ("B", (xB, yB), r_st2), ("C", (xC, yC), r_sb1)):
        imya = "Ст.К1-%d" % NOM[(M.s, kv)]
        runs = stoyak(imya, "K1", x, y, st[M.s]["k" + kv], Z_PP, Z_KR + VYTYAZHKA, ur_po_z,
                      lambda i, n: 110, "pp")
        svyaz((runs[0], 0), (r_niz, 0))

# ---------------- проверки ----------------
TOL = 0.002
TOLSH = {"nar": 0.52, "fund": 0.316, "nes": 0.42, "per": 0.10, "beton": 0.20, "korob": 0.05}
ZST = {"etazhi": (0.0, Z_KR), "podval": (Z_P, 0.0), "vse": (Z_P, Z_KR), "Этаж 01": (0.0, H_ET)}
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
    d1 = [p2[i] - p1[i] for i in range(3)]
    d2 = [q2[i] - q1[i] for i in range(3)]
    r = [p1[i] - q1[i] for i in range(3)]
    a_ = sum(v * v for v in d1)
    e_ = sum(v * v for v in d2)
    f_ = sum(d2[i] * r[i] for i in range(3))
    if a_ < 1e-12 and e_ < 1e-12:
        return math.dist(p1, q1)
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
    return math.dist(cp, cq)


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
    # 1. трубы и стены: вдоль стены нельзя, поперёк — проход
    for rid, p1, p2, rad in segs:
        vert = abs(p1[0] - p2[0]) < 1e-6 and abs(p1[1] - p2[1]) < 1e-6
        for x0, y0, x1, y1, os_, (za, zb), w in stn:
            if max(p1[2], p2[2]) < za + TOL or min(p1[2], p2[2]) > zb - TOL:
                continue
            if vert:
                if x0 - rad + TOL < p1[0] < x1 + rad - TOL and y0 - rad + TOL < p1[1] < y1 + rad - TOL:
                    zap("вертикальная труба в стене", (rid, p1, w["tip"]))
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
                zap("прибор в стене", (pid, pribory[pid]["key"], (round(x0, 3), round(y0, 3)), w["tip"], w["p1"]))
    po_et = {}
    for g_ in gabarity_pr:
        po_et.setdefault(round(g_[5], 2), []).append(g_)
    for lst in po_et.values():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a_, b_ = lst[i], lst[j]
                if min(a_[3], b_[3]) - max(a_[1], b_[1]) > TOL and min(a_[4], b_[4]) - max(a_[2], b_[2]) > TOL:
                    zap("приборы пересекаются", (pribory[a_[0]]["key"], pribory[b_[0]]["key"], a_[1:3]))
    # 3. приборы не перекрывают двери (зона открывания 0,7 м по обе стороны)
    stn_po_dveri = []
    for d in dveri:
        if d["gde"] != "etazhi":
            continue
        shir = int(d["tip"][1][:3]) / 1000.0
        for x0, y0, x1, y1, os_, z_, w in stn:
            if x0 - 1e-6 <= d["x"] <= x1 + 1e-6 and y0 - 1e-6 <= d["y"] <= y1 + 1e-6:
                if os_ == "x":
                    stn_po_dveri.append((d["x"] - shir / 2, d["y"] - 0.7, d["x"] + shir / 2, d["y"] + 0.7, d))
                else:
                    stn_po_dveri.append((d["x"] - 0.7, d["y"] - shir / 2, d["x"] + 0.7, d["y"] + shir / 2, d))
                break
        else:
            zap("дверь не на стене", (d["x"], d["y"], d["tip"][1]))
    for pid, x0, y0, x1, y1, za, zb in gabarity_pr:
        if pribory[pid]["ur"] != "Этаж 01":
            continue
        for dx0, dy0, dx1, dy1, d in stn_po_dveri:
            if min(x1, dx1) - max(x0, dx0) > 0.01 and min(y1, dy1) - max(y0, dy0) > 0.01:
                zap("прибор у двери", (pribory[pid]["key"], (round(x0, 2), round(y0, 2)), (d["x"], d["y"])))
    for o in okna:
        for x0, y0, x1, y1, os_, z_, w in stn:
            if x0 - 1e-6 <= o["x"] <= x1 + 1e-6 and y0 - 1e-6 <= o["y"] <= y1 + 1e-6:
                break
        else:
            zap("окно не на стене", (o["x"], o["y"]))
    # 4. трубы и приборы (кроме подводок и отводов к соединителям этого прибора)
    soed_xy = {}
    for sv in svyazi:
        b_ = sv["b"]
        if isinstance(b_, dict) and "fix" in b_:
            r = seti[sv["a"][0]]
            p = r["pts"][0] if sv["a"][1] == 0 else r["pts"][-1]
            soed_xy.setdefault(b_["fix"], []).append(p)
    for rid, p1, p2, rad in segs:
        for pid, x0, y0, x1, y1, za, zb in gabarity_pr:
            if pribory[pid]["key"] == "moyka":       # под мойкой — тумба, подводки и сифон там и проходят
                continue
            if max(p1[2], p2[2]) < za or min(p1[2], p2[2]) > zb:
                continue
            if max(p1[0], p2[0]) < x0 or min(p1[0], p2[0]) > x1 or max(p1[1], p2[1]) < y0 or min(p1[1], p2[1]) > y1:
                continue
            if any(math.dist(q[:2], e[:2]) < 0.005 for q in soed_xy.get(pid, []) for e in (p1, p2)):
                continue
            for i in range(1, 20):
                q = [p1[k] + (p2[k] - p1[k]) * i / 20 for k in range(3)]
                if x0 + rad < q[0] < x1 - rad and y0 + rad < q[1] < y1 - rad and za < q[2] < zb:
                    zap("труба через прибор", (rid, pribory[pid]["key"], [round(v, 3) for v in q]))
                    break
    # 5. трубы между собой
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
                d = seg_dist(p1, p2, q1, q2)
                if d >= r1 + r2 - TOL:
                    continue
                if min(math.dist(e, f) for e in (p1, p2) for f in (q1, q2)) < 0.01 or \
                        any(seg_dist(e, e, q1, q2) < 0.01 for e in (p1, p2)) or \
                        any(seg_dist(f, f, p1, p2) < 0.01 for f in (q1, q2)):
                    continue
                zap("трубы пересекаются", (ra, rb, round(d, 4), [round(v, 3) for v in p1], [round(v, 3) for v in q1]))
    # 6. холодная вода слева у каждого прибора (смотрим на прибор спереди, лицом к стене)
    for p in pribory:
        c = p["soed"]
        if "hot" not in c:
            # унитаз: холодная по локальной -X
            lx = rot(-1, 0, p["th"])
            nap = (c["cold"][0] - p["x"]) * lx[0] + (c["cold"][1] - p["y"]) * lx[1]
            if nap <= 0:
                zap("холодная не слева", (p["id"], p["key"]))
            continue
        w_vec = rot(0, 1, p["th"]) if p["key"] != "vanna" else rot(-1, 0, p["th"])
        levo = (-w_vec[1], w_vec[0])
        if (c["cold"][0] - c["hot"][0]) * levo[0] + (c["cold"][1] - c["hot"][1]) * levo[1] <= 0:
            zap("холодная не слева", (p["id"], p["key"], p["ur"]))
    return kol


VYLET = {("stal", 15): 0.03, ("stal", 20): 0.035, ("stal", 25): 0.04, ("stal", 32): 0.05, ("stal", 40): 0.055,
         ("stal", 50): 0.065, ("pp", 50): 0.06, ("pp", 110): 0.12, ("sml", 100): 0.10, ("pe", 63): 0.07}


def proverka_fitingov(kol):
    """Отрезок не короче суммы вылетов фитингов на его концах; тройник: магистраль на одной прямой."""
    def zap(vid, opis):
        kol.setdefault(vid, []).append(opis)
    fit_konec = {}                       # (run, end) -> требуемый вылет фитинга на этом конце
    for t in troyniki:
        dm = seti[t["m1"][0]]
        v_m = VYLET[(dm["pt"], dm["d"])]
        for k in ("m1", "m2"):
            fit_konec[tuple(t[k])] = v_m
        rb = seti[t["b"][0]]
        fit_konec[tuple(t["b"])] = v_m + (0.06 if rb["d"] < dm["d"] else 0.0)
    for t in kresty:
        for k in ("m1", "m2", "b1", "b2"):
            fit_konec[tuple(t[k])] = 0.12
    for sv in svyazi:
        if isinstance(sv["b"], dict) and sv["b"].get("kind") == "cold" and pribory[sv["b"]["fix"]]["key"] == "vanna":
            fit_konec[tuple(sv["a"])] = 0.06          # переход 15х20 на патрубок смесителя ванны
        if isinstance(sv["b"], list):
            ra_, rb_ = seti[sv["a"][0]], seti[sv["b"][0]]
            dop = 0.06 if (ra_["d"], ra_["pt"]) != (rb_["d"], rb_["pt"]) else 0.0
            fit_konec[tuple(sv["a"])] = VYLET[(ra_["pt"], ra_["d"])] + dop
            fit_konec[tuple(sv["b"])] = VYLET[(rb_["pt"], rb_["d"])] + dop
    for r in seti:
        pts = r["pts"]
        v = VYLET[(r["pt"], r["d"])]
        n = len(pts) - 1
        for i in range(n):
            L_ = math.dist(pts[i], pts[i + 1])
            nado = (v if i > 0 else fit_konec.get((r["id"], 0), 0.0)) + \
                (v if i < n - 1 else fit_konec.get((r["id"], 1), 0.0))
            if L_ < nado + 0.01:
                zap("отрезок короче фитингов", (r["id"], r["sys"], r["d"], round(L_, 3), round(nado, 3), pts[i]))

    def napr(ref):
        r = seti[ref[0]]
        a, b = (r["pts"][0], r["pts"][1]) if ref[1] == 0 else (r["pts"][-1], r["pts"][-2])
        d = [b[i] - a[i] for i in range(3)]
        L_ = math.sqrt(sum(x * x for x in d))
        return [x / L_ for x in d], a
    for t in troyniki:
        (d1, p1), (d2, p2), (d3, p3) = napr(t["m1"]), napr(t["m2"]), napr(t["b"])
        if max(math.dist(p1, p2), math.dist(p1, p3)) > 0.002:
            zap("тройник: концы не в одной точке", (t, round(math.dist(p1, p2), 4), round(math.dist(p1, p3), 4)))
        if sum(a * b for a, b in zip(d1, d2)) > -0.999:
            zap("тройник: магистраль не на одной прямой", (t, [round(x, 3) for x in p1]))


OTLADKA = False


def proverka_svyaznosti(kol, uroven="etazhi", shag=0.05):
    """Заливка от площадки перед квартирами в каждой секции (типовой этаж) или с улицы (1-й этаж: вход в подъезд).
    Помещения, куда не попасть через двери (без выхода), — замечание. Узкие пространства (шахты за коробами,
    < 0,6 м) и шахта лифта не считаются."""
    from collections import deque
    x0, y0, x1, y1 = -E - 1.0, -E - 1.0, ZERK + E + 1.0, B + E + 1.0       # улица обходит здание
    nx, ny = int((x1 - x0) / shag) + 1, int((y1 - y0) / shag) + 1
    zan = bytearray(nx * ny)
    T = {"nar": 0.52, "nes": 0.42, "per": 0.10, "beton": 0.20, "korob": 0.05}

    def kletki(xa, ya, xb, yb):
        i0, i1 = max(0, int((min(xa, xb) - x0) / shag)), min(nx - 1, int((max(xa, xb) - x0) / shag))
        j0, j1 = max(0, int((min(ya, yb) - y0) / shag)), min(ny - 1, int((max(ya, yb) - y0) / shag))
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                yield j * nx + i

    def pryamoug(w, rasshir=0.0):
        (xa, ya), (xb, yb) = w["p1"], w["p2"]
        t = T[w["tip"]] / 2 + rasshir
        if abs(ya - yb) < 1e-6:
            return xa, ya - t, xb, ya + t
        return xa - t, ya, xa + t, yb
    if uroven == "Подвал":
        T["fund"] = 0.316
        st_et = [w for w in steny if w["gde"] in ("podval", "vse") and w["tip"] in T]
    else:
        st_et = [w for w in steny if w["gde"] in ("etazhi", "vse", uroven) and w["tip"] in T]
    for w in st_et:
        for k in kletki(*pryamoug(w)):
            zan[k] = 1
    shir = {"760": 0.80, "860": 0.90, "1360": 1.40, "870": 0.91}
    for d in dveri:
        if d["gde"] not in (("Подвал",) if uroven == "Подвал" else ("etazhi", uroven)):
            continue
        w_ = shir[d["tip"][1][:4].rstrip("х")]
        for w in st_et:
            (xa, ya), (xb, yb) = w["p1"], w["p2"]
            t = T[w["tip"]] / 2 + 0.002
            if abs(ya - yb) < 1e-6 and abs(d["y"] - ya) <= t and min(xa, xb) - 1e-6 <= d["x"] <= max(xa, xb) + 1e-6:
                for k in kletki(d["x"] - w_ / 2, ya - t - shag, d["x"] + w_ / 2, ya + t + shag):
                    zan[k] = 0
            elif abs(xa - xb) < 1e-6 and abs(d["x"] - xa) <= t and min(ya, yb) - 1e-6 <= d["y"] <= max(ya, yb) + 1e-6:
                for k in kletki(xa - t - shag, d["y"] - w_ / 2, xa + t + shag, d["y"] + w_ / 2):
                    zan[k] = 0

    metka = [0] * (nx * ny)                 # 0 — не размечено, 1 — снаружи, 2 — достижимо, 3.. — прочие
    def zaliv(k0, m):
        q = deque([k0])
        metka[k0] = m
        n, sx, sy, xs, ys = 0, 0.0, 0.0, [], []
        while q:
            k = q.popleft()
            n += 1
            i, j = k % nx, k // nx
            sx += i
            sy += j
            xs.append(i)
            ys.append(j)
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < nx and 0 <= jj < ny:
                    kk = jj * nx + ii
                    if not zan[kk] and not metka[kk]:
                        metka[kk] = m
                        q.append(kk)
        return n, (x0 + sx / n * shag, y0 + sy / n * shag), (max(xs) - min(xs)) * shag, (max(ys) - min(ys)) * shag
    zaliv(0, 1)
    if uroven == "Этаж 01" and OTLADKA:
        for (px, py) in ((12.34, -0.4), (12.34, 0.1), (12.34, 0.6), (12.0, 1.1), (12.0, 1.4), (12.0, 2.5), (12.0, 5.0),
                         (12.0, 5.8), (11.45, 6.1), (10.0, 0.6), (10.0, 2.0)):
            k = int((py - y0) / shag) * nx + int((px - x0) / shag)
            print("ОТЛАДКА", px, py, "занято" if zan[k] else "свободно", "метка", metka[k])
    for M in SEKCII:
        if uroven == "Подвал":
            break                               # подвал — только с улицы (вход через приямок)
        xs_, ys_ = M.x(11.45), 6.1
        k = int((ys_ - y0) / shag) * nx + int((xs_ - x0) / shag)
        if uroven == "Этаж 01" and metka[k] != 1:
            kol.setdefault("1-й этаж: площадка недоступна с улицы", []).append((round(xs_, 2), ys_))
        if not metka[k]:
            zaliv(k, 2)
    m = 3
    lift = [(M.x(10.0), 4.4) for M in SEKCII]
    for k in range(nx * ny):
        if zan[k] or metka[k]:
            continue
        n, (cx, cy), dx, dy = zaliv(k, m)
        m += 1
        S = n * shag * shag
        if S < 0.5 or min(dx, dy) < 0.6 or S / max(dx, dy) < 0.5:
            continue                                    # шахты за коробами и щели вдоль стен
        if any(abs(cx - lx) < 0.8 and abs(cy - ly) < 1.2 for lx, ly in lift):
            continue                                    # шахта лифта
        kol.setdefault("помещение без выхода (%s)" % uroven, []).append((round(cx, 2), round(cy, 2), round(S, 1), round(dx, 2), round(dy, 2)))


kol = proverka()
proverka_fitingov(kol)
def proverka_proemov_dverey(kol):
    """Трубы не должны проходить через проёмы дверей (ширина двери × толщина стены × высота 2,1 м)."""
    T = {"nar": 0.52, "nes": 0.42, "per": 0.10, "beton": 0.20, "korob": 0.05, "fund": 0.316}
    shir = {"760": 0.80, "860": 0.90, "1360": 1.40, "870": 0.91}
    korobki = []
    for d in dveri:
        w_ = shir[d["tip"][1][:4].rstrip("х")]
        if d["gde"] == "etazhi":
            urovni_z = [(k - 1) * H_ET for k in range(1, N_ET + 1)]
        elif d["gde"] == "Подвал":
            urovni_z = [Z_P]
        else:
            urovni_z = [0.0]
        for w in steny:
            if w["tip"] not in T:
                continue
            (xa, ya), (xb, yb) = w["p1"], w["p2"]
            t = T[w["tip"]] / 2 + 0.002
            if abs(ya - yb) < 1e-6 and abs(d["y"] - ya) <= t and min(xa, xb) <= d["x"] <= max(xa, xb):
                box = (d["x"] - w_ / 2, ya - t, d["x"] + w_ / 2, ya + t)
                break
            if abs(xa - xb) < 1e-6 and abs(d["x"] - xa) <= t and min(ya, yb) <= d["y"] <= max(ya, yb):
                box = (xa - t, d["y"] - w_ / 2, xa + t, d["y"] + w_ / 2)
                break
        else:
            continue
        for z0 in urovni_z:
            korobki.append((box, z0, z0 + 2.1, d))
    for r in seti:
        for a, b in zip(r["pts"][:-1], r["pts"][1:]):
            L_ = math.dist(a, b)
            n = max(1, int(L_ / 0.03))
            for (bx0, by0, bx1, by1), z0, z1, d in korobki:
                if max(a[2], b[2]) < z0 or min(a[2], b[2]) > z1:
                    continue
                for i in range(n + 1):
                    t_ = i / n
                    x, y, z = (a[0] + (b[0] - a[0]) * t_, a[1] + (b[1] - a[1]) * t_, a[2] + (b[2] - a[2]) * t_)
                    if bx0 < x < bx1 and by0 < y < by1 and z0 < z < z1:
                        kol.setdefault("труба в проёме двери", []).append((r["id"], r["sys"], d["x"], d["y"], round(z, 2)))
                        break


proverka_svyaznosti(kol)
proverka_svyaznosti(kol, "Этаж 01")
proverka_proemov_dverey(kol)
proverka_svyaznosti(kol, "Подвал")
if not kol:
    print("ПРОВЕРКИ ПРОЙДЕНЫ: коллизий нет, холодная вода слева у всех приборов, двери свободны")
for vid, lst in kol.items():
    print("ЗАМЕЧАНИЕ: %s — %d" % (vid, len(lst)))
    for x in lst[:6]:
        print("   ", x)

# ---------------- сводка для расчёта ----------------
dl = {}
for r in seti:
    L_ = sum(math.dist(a, b) for a, b in zip(r["pts"][:-1], r["pts"][1:]))
    dl.setdefault((r["sys"], r["pt"], r["d"]), 0.0)
    dl[(r["sys"], r["pt"], r["d"])] += L_
print("длины труб, м:", {"%s %s %s" % k: round(v, 1) for k, v in sorted(dl.items())})
print("стояки В1:", {nm: (round(v[0], 3), v[1]) for nm, v in sorted(podvod.items())})
print("магистраль (от, до, L, N, DN):", uchastki_mag)
print("приборов", len(pribory), "труб", len(seti), "тройников", len(troyniki), "арматуры", len(armatura),
      "муфт", len(mufty), "стен", len(steny), "дверей", len(dveri), "окон", len(okna))
trassa_v3 = dict(stoyaki_v1={nm: [round(v[0], 3), v[1], round(v[5], 3)] for nm, v in podvod.items()},
                 magistral=uchastki_mag,
                 x_troynik=X_TR, y_mag=Y_MAG, z_mag=Z_MAG, vypuski=vypuski, l_nap=L_NAP, n_vse=N_VSE,
                 zerkalo=ZERK, x_shov=round(L_SEK + DSH / 2, 3),
                 stoyaki_k1={s["imya"]: [s["x"], s["y"]] for s in stoyaki if s["sys"] == "K1"})
json.dump(trassa_v3, open(os.path.join(HERE, "..", "calc", "trassa_v3.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

geo = dict(pomescheniya=pomescheniya, razdeliteli=razdeliteli, pribory=pribory, seti=seti, troyniki=troyniki, kresty=kresty, armatura=armatura, svyazi=svyazi,
           mufty=mufty, stoyaki=stoyaki, oborud=oborud, dveri=dveri, lestnicy=lestnicy,
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
                     krovlya="ADSK_Плоская кровля по бетонному основанию_290"))

with open(os.path.join(HERE, "geometriya_v3.json"), "w", encoding="utf-8") as f:
    json.dump(geo, f, ensure_ascii=False, indent=1)
