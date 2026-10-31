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
# деформационный шов между секциями: у каждой секции своя торцевая стена 250 мм по своей оси (11 и 12),
# зазор 50 мм (как у Глушкова, чат КРП 05.10); секция 2 — зеркало секции 1 относительно середины шва
T_TORC, SHOV = 0.25, 0.05
DSH = T_TORC + SHOV                 # расстояние между осями 11 и 12
ZERK = 2 * L_SEK + DSH              # x' = ZERK - x для секции 2
N_SEK, N_ET, H_ET = IZ["N_SEK"], IZ["N_ET"], IZ["H_ET"]
OSI_X = [0.0, 3.5, 6.5, 9.2, 10.0, 12.5, 13.7, 15.7, 16.5, 19.0, 22.5]      # оси 1-11 секции 1
OSI_Y = [("А", 0.0), ("Б", 1.3), ("В", 6.8), ("Г", 11.3), ("Д", 12.8)]
B = 12.8
L = ZERK                      # между крайними осями (1 и 22)
# стены по указанию Глушкова (чат КРП 12.10): наружные 580 мм, несущие внутренние 250, перегородки 100
T_NAR, T_NES = 0.58, 0.25
H = T_NES / 2                 # от оси несущей стены до её грани
E = 0.09                      # ось наружной стены 580 мм смещена наружу: внутренняя грань в 200 мм от коорд. оси
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
YV = 6.8                      # несущая стена по оси В, 250 мм: грани 6,675 и 6,925
VN, VV = YV - H, YV + H
# подвал (техподполье), как в образце преподавателя: вдоль всего здания — коридор между стеной по оси В и стеной
# по y = 9,40 (250 мм, грани 9,275 и 9,525; ширина в чистоте 2,35 м) — в нём магистраль В1 (y 7,20), сборные
# трубопроводы К1 (y 8,20) и низ стояков кв. Б и В (В1 — y 7,74, К1 — y 8,94); по сторонам — несколько крупных
# помещений с дверями из коридора
YK = 9.4
KN, KS = YK - H, YK + H
# тёплые стены лоджий по осям Б и Г (580 мм): грань со стороны комнаты — как у прежней стены 520 (1,52 и 11,09)
Y_LB, Y_LG = 1.52 - T_NAR / 2, 11.09 + T_NAR / 2
X_PER_A = 0.30                # кв. А: перегородка шахты (грани 0,25 и 0,35), прослойка 0,20…0,25 у наружной стены
X_KOR_A = 0.69                # кв. А: ось короба шахты (обшивка 50 мм, грани 0,665 и 0,715)
STENY_SEK = [
    # тёплые стены лоджий (580 мм) по осям Б и Г в пролётах 1-2 и 10-11; направление — наружной стороной в лоджию
    # (наружная грань стены Revit — слева по ходу): по оси Б — справа налево, по оси Г — слева направо
    ((3.5 - H, Y_LB), (0.2, Y_LB), "nar", "etazhi"), ((0.2, Y_LG), (3.5 - H, Y_LG), "nar", "etazhi"),
    ((22.5 - H, Y_LB), (19.0 + H, Y_LB), "nar", "etazhi"), ((19.0 + H, Y_LG), (22.5 - H, Y_LG), "nar", "etazhi"),
    # несущие 250 мм (на этажах)
    ((3.5, Y_IN0), (3.5, 5.53), "nes", "etazhi"), ((3.5, VV), (3.5, Y_IN1), "nes", "etazhi"),
    ((6.5, Y_IN0), (6.5, 5.53), "nes", "etazhi"), ((6.5, VV), (6.5, Y_IN1), "nes", "etazhi"),
    ((9.2, Y_IN0), (9.2, 5.53), "nes", "etazhi"),
    ((10.0, 8.105), (10.0, Y_IN1), "nes", "etazhi"), ((12.5, 8.105), (12.5, Y_IN1), "nes", "etazhi"),
    ((13.7, Y_IN0), (13.7, 5.53), "nes", "etazhi"),
    ((15.7, VV), (15.7, Y_IN1), "nes", "etazhi"),
    ((16.5, Y_IN0), (16.5, 5.53), "nes", "etazhi"),
    ((19.0, Y_IN0), (19.0, Y_IN1), "nes", "etazhi"),
    ((0.2, YV), (17.83, YV), "nes", "etazhi"), ((19.0 + H, YV), (22.5 - H, YV), "nes", "etazhi"),
    # подвал: стены коридора на всю длину секции и поперечные стены только между крупными помещениями
    ((0.2, YV), (22.5 - H, YV), "nes", "podval"), ((0.2, YK), (22.5 - H, YK), "nes", "podval"),
    ((3.5, Y_IN0), (3.5, VN), "nes", "podval"), ((6.5, Y_IN0), (6.5, VN), "nes", "podval"),     # насосная
    ((13.7, Y_IN0), (13.7, VN), "nes", "podval"), ((19.0, Y_IN0), (19.0, VN), "nes", "podval"),
    ((6.5, KS), (6.5, Y_IN1), "nes", "podval"), ((12.5, KS), (12.5, Y_IN1), "nes", "podval"),
    ((19.0, KS), (19.0, Y_IN1), "nes", "podval"),
    # приямок лифта: западная стена шахты в подвале (на этажах — стена по оси 4) и северная
    ((9.2, 3.32), (9.2, 5.575), "nes", "podval"), ((9.2 + H, 5.575), (10.78, 5.575), "beton", "podval"),
    # коридоры (перегородки 100 мм)
    ((3.5 + H, 5.575), (9.2 - H, 5.575), "per", "etazhi"),
    ((13.7 + H, 5.575), (19.0 - H, 5.575), "per", "etazhi"),
    ((6.5 + H, 8.055), (12.5 - H, 8.055), "per", "etazhi"),
    # входы в квартиры А и В — перегородки поперёк коридора у откосов на плане задания (x 8,4 и 14,6);
    # между ними — этажная площадка, с неё же через проём в стене по оси В — вход в квартиру Б
    ((8.39, 5.625), (8.39, VN), "per", "etazhi"), ((14.62, 5.625), (14.62, VN), "per", "etazhi"),
    # лифтовая шахта и проход у лифта, простенки тамбура
    ((10.68, 3.32), (10.68, 5.525), "beton", "vse"), ((9.2 + H, 3.42), (10.78, 3.42), "beton", "vse"),
    ((9.2 + H, 5.575), (9.84, 5.575), "per", "etazhi"), ((10.43, 5.575), (10.78, 5.575), "per", "etazhi"),
    # проход от входа в подъезд к лифту — только на 1-м этаже (на типовых этажах это часть лестничной площадки)
    ((10.61, 1.52), (10.61, 3.32), "per", "Этаж 01"), ((10.865, Y_IN0), (10.865, Y_LB - T_NAR / 2), "per", "Этаж 01"),
    ((9.79, Y_LB), (9.2 + H, Y_LB), "nar", "etazhi"), ((11.19, Y_LB), (10.54, Y_LB), "nar", "etazhi"),
    ((13.7 - H, Y_LB), (12.84, Y_LB), "nar", "etazhi"),
    # санузел кв. А (оси 1-2 / Б-В): перегородка по оси x 2,32 (сдвинута от 1,97 на плане — ванна 1500 с коробом).
    # Шахта стояков не примыкает к наружной стене (Глушков, чат КРП 10.10 и 12.10): воздушная прослойка 50 мм,
    # перегородка 100 мм, шахта 315 мм в свету, короб
    ((0.2, 4.165), (2.56, 4.165), "per", "etazhi"), ((2.32, 4.215), (2.32, VN), "per", "etazhi"),
    ((X_KOR_A + 0.025, 5.75), (2.27, 5.75), "per", "etazhi"), ((X_KOR_A, 4.215), (X_KOR_A, VN), "korob", "etazhi"),
    ((X_PER_A, 4.215), (X_PER_A, VN), "per", "etazhi"),
    # санузел кв. Б (оси 7-8 / В-Г)
    ((13.62, VV), (13.62, 9.54), "per", "etazhi"), ((13.67, 9.49), (15.7 - H, 9.49), "per", "etazhi"),
    ((13.67, 7.855), (15.19, 7.855), "per", "etazhi"), ((15.215, VV), (15.215, 9.44), "korob", "etazhi"),
    # санузел кв. В (оси 8-9 / В-Г) — зеркально санузлу Б относительно оси 8
    ((17.78, VV), (17.78, 9.54), "per", "etazhi"), ((15.7 + H, 9.49), (17.73, 9.49), "per", "etazhi"),
    ((16.21, 7.855), (17.73, 7.855), "per", "etazhi"), ((16.185, VV), (16.185, 9.44), "korob", "etazhi"),
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
# подвал: электрощитовая — в помещении со входом с улицы, через неё не проходит ни одна труба (через электрощитовые
# прокладка водопровода и канализации не допускается); стояки кв. А — в техподполье у торца
POMESCH_PODVAL = [
    (5.0, 3.0, "Насосная"), (11.0, 7.7, "Коридор"), (1.85, 3.0, "Техподполье"), (8.0, 3.0, "Техподполье"),
    (16.3, 3.0, "Электрощитовая"), (20.7, 3.0, "Помещение СС"), (3.4, 10.8, "Венткамера"),
    (9.5, 10.8, "Блок кладовых"), (15.7, 10.8, "Блок кладовых"), (20.7, 10.8, "Техподполье"),
]
# границы помещений в открытых проёмах (кухня — прихожая), типовой этаж
RAZDEL_ETAZH = [((2.56, 4.165), (3.5 - H, 4.165)), ((12.5 + H, 9.54), (13.57, 9.54)),
                ((17.83, 9.54), (19.0 - H, 9.54))]

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
    (2.87, YV, D760, "etazhi", (0, 1)), (8.85, YV, D860, "etazhi", (0, 1)),
    (8.39, 6.11, D860, "etazhi", (-1, 0)), (14.62, 6.11, D860, "etazhi", (1, 0)),     # входы в кв. А и В
    (2.32, 4.60, D760, "etazhi", (1, 0)), (2.32, 6.20, D760, "etazhi", (1, 0)),       # ванная и уборная кв. А
    (13.62, 7.40, D760, "etazhi", (-1, 0)), (13.62, 9.05, D760, "etazhi", (-1, 0)),
    (17.78, 7.40, D760, "etazhi", (1, 0)), (17.78, 9.05, D760, "etazhi", (1, 0)),
    (12.34, -E, D_VH, "Этаж 01", (0, -1)), (9.92, -E, D860, "Этаж 01", (0, -1)),      # вход в подъезд, выход у лифта
    (1.20, Y_LG, BDV, "etazhi", (0, -1)), (21.29, Y_LG, BDV, "etazhi", (0, -1)),      # балконные двери на лоджии
    (1.20, Y_LB, BDV, "etazhi", (0, 1)), (21.29, Y_LB, BDV, "etazhi", (0, 1)),        # по осям Г и Б
    # подвал (техподполье): вход с улицы через приямок по фасаду А; из коридора — двери во все помещения и проход
    # в коридор соседней секции через торцевые стены у деформационного шва
    (15.1, -E, D860, "Подвал", (0, -1)),
    (1.85, YV, D860, "Подвал", (0, -1)), (5.0, YV, D860, "Подвал", (0, -1)), (8.0, YV, D860, "Подвал", (0, -1)),
    (16.3, YV, D860, "Подвал", (0, -1)), (20.7, YV, D860, "Подвал", (0, -1)),
    (3.4, YK, D860, "Подвал", (0, 1)), (9.5, YK, D860, "Подвал", (0, 1)), (14.0, YK, D860, "Подвал", (0, 1)),
    (20.7, YK, D860, "Подвал", (0, 1)),
    (22.5, 7.8, D860, "Подвал", (-1, 0)),
]
# окна: (x, y, тип, где, подоконник)
OKNA_SEK = []
for x in (1.6, 4.955, 8.155, 11.2, 14.0, 17.24, 20.75):
    OKNA_SEK.append((x, B + E, OK_2, "etazhi", 0.9))
for x in (1.6, 4.99, 7.82, 15.03, 17.70, 20.75):
    OKNA_SEK.append((x, -E, OK_2, "etazhi", 0.9))
OKNA_SEK += [(12.34, -E, OK_2, "verh", 1.2), (9.92, -E, OK_1, "verh", 1.2),      # лестничная клетка на 2-11 эт.
             # окна рядом с балконными дверями (блок «дверь + окно», простенок 30 мм)
             (2.10, Y_LB, OK_1, "etazhi", 0.8), (20.39, Y_LB, OK_1, "etazhi", 0.8),
             (2.10, Y_LG, OK_1, "etazhi", 0.8), (20.39, Y_LG, OK_1, "etazhi", 0.8)]
# лестница: двухмаршевая, марш вверх от этажной площадки на юг (слева), второй марш на север (справа)
LESTNICA_SEK = dict(m1=((11.435, 5.62), (11.435, 3.30), 1.11), m2=((12.79, 3.30), (12.79, 5.62), 1.08))
# отверстия в перекрытиях: лестничная клетка и шахта лифта
OTVERSTIYA_SEK = [[(9.2 + H, 3.32), (9.2 + H, 5.525), (13.7 - H, 5.525), (13.7 - H, 1.52), (10.78, 1.52),
                   (10.78, 3.32)]]

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

# ---------------- благоустройство у здания: земля, крыльца, приямки (03, режим zemlya) ----------------
# 30.10, замечание «почему двери на втором этаже»: в модели не было земли, подвал (−3,0…0,0) стоял над землёй целиком
# и входные двери на 0,000 выглядели как на втором этаже. Земля — поверхность по рельефу генплана (genplan_v3.py
# пишет сетку отметок в genplan_v3.json), отверстие под здание по наружным граням фундаментных стен и под приямки.
T_FUND = 0.316
ZD_GAB = [round(-E - T_FUND / 2, 3), round(-E - T_FUND / 2, 3), round(ZERK + E + T_FUND / 2, 3),
          round(B + E + T_FUND / 2, 3)]            # x0, y0, x1, y1 — наружные грани фундаментных стен
Y_FAS_A = -E - T_NAR / 2                            # наружная грань стен этажей по оси А
# крыльцо у входа в подъезд и выхода у лифта (двери x 9,92 и 12,34 по оси А, 1-й этаж): площадка 1,6 м от стены,
# верх −0,020 (порог), ступени 0,30 м к земле — на всю ширину площадки
KRYLCO_SEK = dict(x0=9.92 - 0.43 - 0.30, x1=12.34 + 0.68 + 0.30, glub=1.60, verh=-0.02, prostup=0.30)
# приямок входа в подвал (дверь x 15,1 по оси А на уровне подвала): в свету 1,2 м, площадка у двери 1,0 м,
# марш к земле на юг; стенки — бетон 200 мм
PRIYAMOK_SEK = dict(x=15.1, shir=1.20, ploshchadka=1.00, stupen=0.28, t_st=0.20)
kryltsa, priyamki = [], []
for M_ in SEKCII:
    a, b = sorted((M_.x(KRYLCO_SEK["x0"]), M_.x(KRYLCO_SEK["x1"])))
    kryltsa.append(dict(x0=round(a, 3), x1=round(b, 3), y1=round(Y_FAS_A, 3),
                        y0=round(Y_FAS_A - KRYLCO_SEK["glub"], 3), verh=KRYLCO_SEK["verh"],
                        prostup=KRYLCO_SEK["prostup"]))
    xc = M_.x(PRIYAMOK_SEK["x"])
    priyamki.append(dict(x=round(xc, 3), shir=PRIYAMOK_SEK["shir"], y_stena=ZD_GAB[1],
                         ploshchadka=PRIYAMOK_SEK["ploshchadka"], stupen=PRIYAMOK_SEK["stupen"],
                         t_st=PRIYAMOK_SEK["t_st"], z_niz=Z_P))
# крыльцо не над приямком, приямок у двери подвала
for kr_ in kryltsa:
    for pr_ in priyamki:
        assert pr_["x"] + pr_["shir"] / 2 + pr_["t_st"] < kr_["x0"] - 0.5 or             pr_["x"] - pr_["shir"] / 2 - pr_["t_st"] > kr_["x1"] + 0.5, ("приямок у крыльца", kr_, pr_)
zemlya = dict(zdanie=ZD_GAB, kryltsa=kryltsa, priyamki=priyamki)

# ================= ПРИБОРЫ И СЕТИ =================
P_C = REZ["P"]["c"]
N_PR = 4
ET_REG = set(REZ["et_reg"])          # этажи с регуляторами давления на квартирных вводах
VGP = {15: 15.7, 20: 21.2, 25: 27.1, 32: 35.9, 40: 41.0, 50: 53.0}


def shevelev_v(q, dn):
    d = (VGP[dn] - 1.0) / 1000
    return q / 1000 / (math.pi * d * d / 4)


PPR_VN = {20: 13.2, 25: 16.6, 32: 21.2, 40: 26.6, 50: 33.2}      # ППР PN20 (ADSK_Полипропилен_PN20): d вн, мм


def ppr_v(q, d):
    dv = PPR_VN[d] / 1000
    return q / 1000 / (math.pi * dv * dv / 4)


def d_ppr_po_n(n, dmin, vmax=1.5):
    """Диаметр ППР PN20 по числу приборов выше сечения: v ≤ vmax (α по Б.2 интерполяцией)."""
    q = 5 * alpha_b2(n * P_C, "interp") * 0.2
    for d in (20, 25, 32, 40, 50):
        if d >= dmin and ppr_v(q, d) <= vmax:
            return d
    return 50


def dn_po_n(n, dmin):
    """Диаметр В1 по числу приборов выше сечения — правилом raschet_v3.py (v ≤ 1,2 м/с)."""
    q = 5 * alpha_b2(n * P_C, "floor") * 0.2
    for dn in (25, 32, 40, 50):
        if dn >= dmin and shevelev_v(q, dn) <= 1.2:
            return dn
    return 50


pribory, seti, troyniki, kresty, armatura, svyazi, mufty, stoyaki = [], [], [], [], [], [], [], []
arm_svyazi = []     # арматура, свинченная с арматурой: [id выхода, id входа] (узел учёта — одной сборкой)
gabarity_pr = []          # (id, x0, y0, x1, y1, z0, z1)

# соединители приборов, мм, в системе семейства (журнал кнопки «02»); ванна ВСт 1500
SOED = {"vanna": dict(cold=(-12, 425, 700), hot=(-12, 275, 700), san=(200, 350, 95)),
        "unitaz": dict(cold=(-200, -95, 700), san=(0, -55, 155)),        # «Косой выпуск»: 45° вниз к стене
        "umyv": dict(cold=(12, -75, 800), hot=(-12, -75, 800), san=(57, -180, 558)),
        "moyka": dict(cold=(407, -30, 850), hot=(382, -30, 850), san=(352, -130, 558))}
# направления патрубков в системе семейства (журнал кнопки «02»), где они не вертикальные: к ним — по оси патрубка
SOED_DIR = {"unitaz": {"cold": (-1.0, 0.0, 0.0)}}
PR_DIR = {}             # точка соединителя (округлённая) -> направление патрубка в координатах здания
STENA = {}              # соединитель умывальника и мойки -> (к стене x, y, расстояние до грани стены, м)
# Холодная вода подводится слева (если смотреть на прибор спереди) — как в образце и по СП 30 (холодная левее
# горячей). У умывальника, мойки и ванны ADSK холодная справа -> экземпляры отражаются относительно оси симметрии.
ZERKALO = {"umyv": ("x", 0.0), "moyka": ("x", 400.0), "vanna": ("y", 350.0)}
GABARIT = {"vanna": (-12, 0, 0, 1500, 700, 550), "unitaz": (-200, -660, 0, 200, 0, 750),
           "umyv": (-275, -420, 0, 275, 0, 915), "moyka": (0, -490, 0, 800, 35, 965)}
PR_FAM = {"vanna": ("ADSK_Ванна стальная эмалированная_ГОСТ23695-2016", "ВСт 1500"),
          "unitaz": ("ADSK_Унитаз напольный_ГОСТ 30493-2017", "Косой выпуск"),
          "umyv": ("ADSK_Умывальник со смесителем", "Умывальник"),
          "moyka": ("ADSK_Мойка кухонная со смесителем", "Мойка кухонная со смесителем и сифоном")}
ARM = {"kran15": ("VALTEC_VT.214.N_КранШаровой ВР", '1/2"', -0.024, 0.024),
       # водомерный узел (30.10, «Старые системы»): фланцевые задвижка ADL KR11 и фильтр ADL IS40, DN50 — параметр
       # типа «DN»; соединители по локальной оси Y (OS_Y): 140 и 326 мм между фланцами
       "zadv50": ("ADL_Задвижка_KR11", "ADL_Задвижка_KR11", -0.070, 0.070),
       "filtr50": ("ADL_Фильтр сетчатый фланцевый_IS40", "ADL_Фильтр сетчатый фланцевый_IS40", -0.163, 0.163),
       # кран ВР-НР (замечание 28.10): в начале квартирного узла — НР в фильтр; у бачка унитаза — НР в гибкую подводку
       "kran15vn": ("VALTEC_VT.215.N_КранШаровой ВР-НР", '1/2"', -0.024, 0.033),
       # фильтр перед общедомовым счётчиком: в семействе DN15, DN25 задаётся «ADSK_Диаметр условный» (kvv_seti)
       "filtr25": ("ADSK_Фильтр механический сетчатый муфтовый ВР", "Фильтр сетчатый муфтовый ВР-ВР", -0.028, 0.028),
       "kran25": ("VALTEC_VT.214.N_КранШаровой ВР", '1"', -0.032, 0.032),
       # кран пары стояков с ручкой вбок — тот же VT.214 на вертикальной рабочей плоскости (05: семейство переводится
       # на рабочую плоскость; поворот вокруг оси трубы Revit не даёт — вложенная ручка)
       "kran25wp": ("VALTEC_VT.214.N_КранШаровой ВР", '1"', -0.032, 0.032),
       "kran32wp": ("VALTEC_VT.214.N_КранШаровой ВР", '1 1/4"', -0.036, 0.036),
       "kran32": ("VALTEC_VT.214.N_КранШаровой ВР", '1 1/4"', -0.036, 0.036),
       "kran40": ("VALTEC_VT.214.N_КранШаровой ВР", '1 1/2"', -0.042, 0.041),
       "kran50": ("VALTEC_VT.214.N_КранШаровой ВР", '2"', -0.050, 0.049),
       "filtr15": ("ADSK_Фильтр механический сетчатый муфтовый ВР", "Фильтр сетчатый муфтовый ВР-ВР", -0.016, 0.016),
       # с импульсным выходом — дистанционная передача показаний (СП 30, п. 12.13); геометрия та же, L = 110 мм
       "sch15": ("Квартирный счетчик воды_Пульсар",
                 "Квартирный счетчик воды Ду15 импульсный выход, Qn=1,5 м3/ч, L=110мм (присоединители в комплекте)",
                 -0.055, 0.055),
       "reg15": ("VALTEC_VT.089.N_Редуктор давления мембранный", "DN 15", -0.041, 0.0),
       # обратный клапан в конце квартирного узла (замечание преподавателя); в семействе DN25 — размер DN15
       # задаётся параметром экземпляра (kvv_seti), соединители на ±15 мм
       "obr15": ("ADSK_Клапан обратный пружинный_Муфтовый_DN15-50", "Обратный клапан пружинный", -0.015, 0.015),
       # общедомовой счётчик ВСХН-25 «Тепловодомер» (семейство из проекта пользователя, kvv_seti.tvm_schetchik),
       # соединители на ±130 мм
       "sch25": ("КрыльчатыеСчетчикиХолоднойВоды_Стандарт_Тепловодомер", "DN25_IP54_Металлический_260_Класс_В", -0.130, 0.130)}


def R(v):
    return [round(c, 4) for c in v]


def rot(x, y, th):
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    return x * c - y * s, x * s + y * c


def mir_lok(key, lx, ly, zk=None):
    zk = zk or ZERKALO.get(key)
    if zk:
        os_, c = zk
        if os_ == "x":
            lx = 2 * c - lx
        else:
            ly = 2 * c - ly
    return lx, ly


def pribor(key, x, y, th, ur, zf, mir=False):
    pid = len(pribory)
    zk = ("x", 0.0) if mir else ZERKALO.get(key)
    pribory.append(dict(id=pid, fam=PR_FAM[key][0], tip=PR_FAM[key][1], x=round(x, 4), y=round(y, 4),
                        th=round(th, 3), ur=ur, key=key, mir=dict(os=zk[0], c=zk[1] / 1000) if zk else None))
    c = {}
    for k, (lx, ly, lz) in SOED[key].items():
        lx, ly = mir_lok(key, lx, ly, zk)
        dx, dy = rot(lx / 1000, ly / 1000, th)
        c[k] = (x + dx, y + dy, zf + lz / 1000)
        nd = SOED_DIR.get(key, {}).get(k)
        if nd is not None:
            ndx, ndy = mir_lok(key, nd[0], nd[1], (zk[0], 0.0)) if zk else (nd[0], nd[1])
            wx, wy = rot(ndx, ndy, th)
            PR_DIR[tuple(round(v, 4) for v in c[k])] = (round(wx, 6), round(wy, 6), nd[2])
    if key in ("umyv", "moyka"):
        lx, ly, lz = SOED[key]["cold"]
        wx_, wy_ = rot(0.0, 1.0, th)
        STENA[tuple(round(v, 4) for v in c["cold"])] = (round(wx_, 6), round(wy_, 6),
                                                        -ly / 1000 + (0.035 if key == "moyka" else 0.0))
    g = GABARIT[key]
    xs, ys = [], []
    for lx in (g[0], g[3]):
        for ly in (g[1], g[4]):
            mx, my = mir_lok(key, lx, ly, zk)
            dx, dy = rot(mx / 1000, my / 1000, th)
            xs.append(x + dx)
            ys.append(y + dy)
    gabarity_pr.append((pid, min(xs), min(ys), max(xs), max(ys), zf + g[2] / 1000, zf + g[5] / 1000))
    pribory[-1]["soed"] = {k: R(v) for k, v in c.items()}
    return pid, c


VEK = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}


def pribor2(key, M, wloc, face, along, zf, ur, mir=False):
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
    return pribor(key, x, y, th, ur, zf, mir)


def truba(sys_, pt, d, pts, ur):
    rid = len(seti)
    seti.append(dict(id=rid, sys=sys_, pt=pt, d=d, pts=[R(p) for p in pts], ur=ur))
    return rid


def svyaz(a, b):
    svyazi.append(dict(a=a, b=b))


def troynik(m1, m2, b):
    troyniki.append(dict(m1=m1, m2=m2, b=b))


OS_Y = ("zadv50", "filtr50")         # семейства с соединителями по локальной оси Y


def arm(key, p, d, ur):
    """Арматура с входом в точке p по направлению d (2D — горизонтально, 3D (0, 0, ±1) — вертикально: в Revit
    экземпляр поворачивается вокруг горизонтальной оси, kvv_seti)."""
    fam, tip, xin, xout = ARM[key]
    d = tuple(d) + (0.0,) * (3 - len(d))
    vert = abs(d[2]) > 0.5
    th = 0.0 if vert else math.degrees(math.atan2(d[1], d[0])) - (90.0 if key in OS_Y else 0.0)
    ins = tuple(p[i] - d[i] * xin for i in range(3))
    out = tuple(ins[i] + d[i] * xout for i in range(3))
    aid = len(armatura)
    zap = dict(id=aid, key=key, fam=fam, tip=tip, x=round(ins[0], 4), y=round(ins[1], 4), z=round(ins[2], 4),
               th=round(th, 3), ur=ur)
    if vert:
        zap["vert"] = -1 if d[2] < 0 else 1
    if key == "obr15":
        zap["dn"] = 15
        # стрелка семейства — против его оси X (вход → выход): экземпляр разворачивается (замечание 28.10)
        zap["perev"] = True
    if key == "filtr25":
        zap["dn"] = 25
    if key in OS_Y:
        zap["dn"] = 50
    if vert and key == "kran15vn":
        # кран VALTEC не поворачивается на вертикаль (вложенная ручка «на рабочей плоскости»): семейство переводится
        # на рабочую плоскость, экземпляр ставится на вертикальную плоскость (kvv_seti)
        zap["wp"] = True
    armatura.append(zap)
    return aid, out


arm_pribor = []     # арматура и приборы встык: [id арматуры, id прибора, вид соединителя]
gibkie = []         # гибкие подводки от водорозетки к смесителю: [id водорозетки, id прибора, вид соединителя]
PODVOD_XY = {}      # прибор -> точки подводки в плане (подъём к водорозетке, кран у бачка): не коллизия с прибором
VR_DX, VR_DZ = 0.016, 0.012


def vodorozetka(vyhod, napr, d, ur):
    """Водорозетка ППР d x 1/2": резьба в точке vyhod, смотрит по napr (в плане), гнездо — вниз. Возвращает (id,
    точка гнезда — конец подъёма трубы)."""
    o = (vyhod[0] - napr[0] * VR_DX, vyhod[1] - napr[1] * VR_DX, vyhod[2] - VR_DZ)
    aid = len(armatura)
    armatura.append(dict(id=aid, key="vr%d" % d, fam="ADSK_Полипропилен_Водорозетка ВР", tip=u"%d х 1/2\"" % d,
                         x=round(o[0], 4), y=round(o[1], 4), z=round(o[2], 4),
                         th=round(math.degrees(math.atan2(napr[1], napr[0])), 3), ur=ur))
    return aid, o


T_KOROB = 0.05          # обшивка короба ванны (ГКЛВ)


def tochka_vr(conn):
    """Резьба водорозетки умывальника и мойки: на стене (45 мм от грани), в 0,30 м ниже смесителя."""
    w = STENA[tuple(round(v, 4) for v in conn)]
    return (conn[0] + w[0] * (w[2] - 0.045), conn[1] + w[1] * (w[2] - 0.045), conn[2] - 0.30)


def y_podvoda(conn):
    """Линия ответвления к прибору: у умывальника и мойки — по линии подъёма к водорозетке (без короткого колена),
    у остальных — по соединителю."""
    ck = tuple(round(v, 4) for v in conn)
    if ck in STENA:
        return tochka_vr(conn)[1] + STENA[ck][1] * VR_DX
    dr = PR_DIR.get(ck)
    if dr is not None and abs(dr[2]) < 0.5:              # бачок унитаза: по линии подъёма к крану
        return conn[1] + dr[1] * 0.15
    return conn[1]


def podvod_k_priboru(p, conn, fid, xh, z, d, ur, konec=False):
    """Подводка ППР от точки разводки p к соединителю холодной воды прибора с водорозеткой или краном:
    ванна — водорозетка в коробе, резьба в смеситель; умывальник и мойка — водорозетка на стене в 0,30 м ниже
    смесителя, к смесителю — гибкая подводка (в модели нет); бачок унитаза — кран шаровой ВР-НР с переходником (муфта
    комбинированная), НР — в гибкую подводку бачка. Возвращает (точки трубы, арматура в конце, встык с прибором)."""
    ck = tuple(round(v, 4) for v in conn)
    dr = PR_DIR.get(ck)
    if dr is not None and abs(dr[2]) < 0.5:              # бачок унитаза: патрубок вбок
        a = (conn[0] + dr[0] * 0.15, conn[1] + dr[1] * 0.15)
        k_in = (conn[0] + dr[0] * 0.057, conn[1] + dr[1] * 0.057, conn[2])
        pts = [p, (a[0], a[1], z), (a[0], a[1], conn[2]), k_in]
        aid, out = arm("kran15vn", k_in, (-dr[0], -dr[1]), ur)
        PODVOD_XY.setdefault(fid, []).extend([a, k_in[:2], conn[:2]])
        return pts, aid, True
    if ck in utoplen:
        # ванна: смеситель — на лицевой плоскости короба ГКЛВ 50 мм; водорозетка — за обшивкой, в шахте, резьбой к
        # смесителю (удлинитель смесителя проходит сквозь обшивку, в модели его нет)
        s_ = math.copysign(1.0, conn[0] - xh)
        aid, o = vodorozetka((conn[0] - s_ * T_KOROB, conn[1], conn[2]), (s_, 0.0), d, ur)
        pts = [p, (o[0], conn[1], z), o]
        PODVOD_XY.setdefault(fid, []).extend([o[:2], conn[:2]])
        gibkie.append([aid, fid, "cold"])
        return pts, aid, False
    vyh = tochka_vr(conn)                                # умывальник, мойка: на стене под смесителем
    w = STENA[ck]
    # подъём ближе 80 мм к линии разводки (мойки кв. Б и В: стояк и разводка — прямо за мойкой) — с самой линии,
    # без короткого колена
    ox, oy = vyh[0] + w[0] * VR_DX, vyh[1] + w[1] * VR_DX
    if 1e-6 < abs(ox - p[0]) < 0.08 and abs(oy - p[1]) < 1e-6:
        vyh = (p[0] - w[0] * VR_DX, vyh[1], vyh[2])
    elif 1e-6 < abs(oy - p[1]) < 0.08 and abs(ox - p[0]) < 1e-6:
        vyh = (vyh[0], p[1] - w[1] * VR_DX, vyh[2])
    aid, o = vodorozetka(vyh, (-w[0], -w[1]), d, ur)
    pts = [p, (o[0], p[1], z), (o[0], o[1], z), o]
    PODVOD_XY.setdefault(fid, []).extend([o[:2], conn[:2], (o[0], p[1])])
    gibkie.append([aid, fid, "cold"])
    return pts, aid, False


L_NIP = 0.03       # ниппель между арматурой узла учёта


def vetka(sys_, pt, d, pts_do, napr, items, ur, gap=0.02, first=0.07, sborka=False):
    """Труба до арматуры items по направлению napr. sborka — арматура свинчена одна с другой (вход следующей — в
    выходе предыдущей), труба — только до первой и после последней; иначе между ними отрезки длиной gap."""
    p = pts_do[-1]
    napr = tuple(napr) + (0.0,) * (3 - len(napr))
    p_in = (p[0] + napr[0] * first, p[1] + napr[1] * first, p[2] + napr[2] * first)
    r0 = truba(sys_, pt, d, pts_do + [p_in], ur)
    prev = (r0, 1)
    pred = None
    # «nip» в items — ниппель между соседними арматурами (отрезок стальной трубы DN15 длиной L_NIP), как латунные
    # ниппели между приборами узла учёта на фото образца 28.10
    seq = []
    for k_ in items:
        if k_ == "nip" and seq:
            seq[-1] = (seq[-1][0], True)
        else:
            seq.append((k_, False))
    items = [k_ for k_, _ in seq]
    for i, (key, nip) in enumerate(seq):
        aid, out = arm(key, p_in, napr, ur)
        if pred is None:
            svyaz(prev, dict(arm=aid, side="in"))
        else:
            arm_svyazi.append([pred, aid])
        if nip and i < len(seq) - 1:
            q = tuple(out[j] + napr[j] * L_NIP for j in range(3))
            r = truba(sys_, "stal", 15, [out, q], ur)
            svyaz((r, 0), dict(arm=aid, side="out"))
            prev, pred, p_in = (r, 1), None, q
            continue
        if sborka and i < len(items) - 1:
            p_in, pred = out, aid
            continue
        p_in = (out[0] + napr[0] * gap, out[1] + napr[1] * gap, out[2] + napr[2] * gap)
        r = truba(sys_, pt, d, [out, p_in], ur)
        svyaz((r, 0), dict(arm=aid, side="out"))
        prev, pred = (r, 1), None
    return r0, prev, p_in


Z_RAZV = 0.25       # ось поквартирной разводки над полом — как в образце преподавателя (+0,250)
Z_UZEL = 1.5        # тройник квартирного ответвления на стояке В1 — как в образце (+1,500 от пола)
L_UZLA = 0.45       # от оси стояка до опуска узла вдоль стены шахты: за подходом к бачку унитаза (0,15 м по оси патрубка)
I_OTV = 0.03        # уклон поэтажных отводов Ø50
I_UN = 0.02         # уклон отвода от унитаза Ø110
# ось двухплоскостной крестовины К1 над полом: низ трубы Ø110 — на уровне чистого пола (в образце лоток +0,009);
# отводы Ø50 и Ø110 идут над полом, не в плите перекрытия (замечание преподавателя 21.10.2026)
Z_KREST = 0.055


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


def k_priboru(p, conn, xh, z, konec=False):
    d = PR_DIR.get(tuple(round(v, 4) for v in conn))
    if konec and d is not None and abs(d[2]) < 0.5:
        # патрубок вбок (бачок унитаза): последние 150 мм — по оси патрубка, чтобы муфта комбинированная ППР встала
        # соосно (переходы и муфты ставятся только между соосными соединителями)
        a = (conn[0] + d[0] * 0.15, conn[1] + d[1] * 0.15)
        pts = [(p[0], a[1], z), (a[0], a[1], z), (a[0], a[1], conn[2]), conn]
        return [q for i, q in enumerate(pts) if i == 0 or math.dist(q, pts[i - 1]) > 1e-6]
    if tuple(round(v, 4) for v in conn) in utoplen:
        # подъём внутри короба в 150 мм от соединителя (патрубок смесителя ванны DN15 — подводка ППР Ø20):
        # на горизонтальном отрезке — отвод и муфта комбинированная ППР 20 х 1/2"
        dx = abs(conn[0] - xh)
        xv = xh if 0.15 <= dx < 0.21 else conn[0] - math.copysign(0.15, conn[0] - xh)
        pts = [p] + ([(xv, conn[1], z)] if abs(xv - p[0]) > 1e-6 else [])
        return pts + [(xv, conn[1], conn[2]), conn]
    if abs(conn[0] - p[0]) < 0.005:            # соединитель над линией разводки — прямой подъём
        return [p, conn]
    return [p, (conn[0], conn[1], z), conn]


def dl3(rid):
    return sum(math.dist(a, b) for a, b in zip(seti[rid]["pts"][:-1], seti[rid]["pts"][1:]))


razvodka_kv = {}        # кв. верхнего этажа: прибор -> [(N, L)] от прибора до стояка — для гидравлического расчёта


def nogi(xh, y0, z, ftaps, ur, d_vetki=25, puti=None):
    """Ветка разводки ППР от точки (xh, y0, z) вдоль оси Y. ftaps — [(соединитель, id прибора, обход)], по порядку;
    последний прибор — конец ветки. Ветка — Ø25 (на 3–4 прибора v ≤ 1,5 м/с), подводки к приборам — Ø20."""
    ids, uzly, cur = [], [], [(xh, y0, z)]
    for i, (conn, fid, obhod) in enumerate(ftaps):
        if i < len(ftaps) - 1:
            p = (xh, y_podvoda(conn), z)
            cur.append(p)
            ids.append(truba("V1", "ppr", d_vetki, cur, ur))
            uzly.append((p, conn, fid))
            cur = [p]
        else:
            xe = xh
            for (wx, wy) in (obhod or []):
                cur.append((wx, wy, z))
                xe = wx
            pts_, aid, vstyk = podvod_k_priboru((xe, y_podvoda(conn), z), conn, fid, xe, z, d_vetki, ur, konec=True)
            for q in pts_:
                if math.dist(q, cur[-1]) > 1e-6:
                    cur.append(q)
            ids.append(truba("V1", "ppr", d_vetki, cur, ur))
            svyaz((ids[-1], 1), dict(arm=aid, side="in"))
            if vstyk:
                arm_pribor.append([aid, fid, "cold"])
    rbs = []
    for i, (p, conn, fid) in enumerate(uzly):
        pts_, aid, vstyk = podvod_k_priboru(p, conn, fid, xh, z, 20, ur)
        rb = truba("V1", "ppr", 20, [q for j, q in enumerate(pts_) if j == 0 or math.dist(q, pts_[j - 1]) > 1e-6], ur)
        troynik((ids[i], 1), (ids[i + 1], 0), (rb, 0))
        svyaz((rb, 1), dict(arm=aid, side="in"))
        if vstyk:
            arm_pribor.append([aid, fid, "cold"])
        rbs.append(rb)
    if puti is not None:
        n = len(ftaps)
        for j, (conn, fid, obhod) in enumerate(ftaps):
            put = [(1, round(dl3(rbs[j]), 3), 20)] if j < n - 1 else []
            put += [(n - i, round(dl3(ids[i]), 3), d_vetki) for i in range(j, -1, -1)]
            puti[pribory[fid]["key"]] = put
    return ids[0]


def kv_v1(k, zf, ur, rs_v, stoyak_xy, napr, nogi_, klyuch=None):
    """Квартирный узел ввода — как в образце преподавателя: тройник на стояке на Z_UZEL, шаровой кран на отводе от
    стояка, опуск вдоль стены шахты — фильтр, регулятор давления (этажи ET_REG), счётчик, обратный клапан
    (в конце узла); внизу на Z_RAZV — разводка ППР по линии стояка двумя ветками (nogi_ — списки приборов)."""
    xr, yr = stoyak_xy
    z1 = zf + Z_UZEL
    y_op = yr + napr[1] * L_UZLA
    # как в образце (фото 28.10): отвод от стояка без арматуры, на опуске — кран ВР-НР, фильтр, регулятор,
    # счётчик, обратный клапан одной сборкой на резьбе; муфты комбинированные ППР 25 х 1/2" — над краном и под
    # клапаном. Кран VALTEC вертикально ставится на рабочую плоскость (kvv_seti, «wp»)
    ra = truba("V1", "ppr", 25, [(xr, yr, z1), (xr, y_op, z1)], ur)
    rs_v.append((z1, (ra, 0)))
    # как на фото образца: кран — ниппель — косой фильтр — ниппель — регулятор — ниппель — счётчик (присоединители
    # в комплекте) — обратный клапан; ручка крана, циферблаты счётчика и регулятора — к помещению (замечание 30.10
    # «кран должен быть расположен к нам»): кв. А и В — в сторону +x секции, кв. Б — −x
    items = ["kran15vn", "nip", "filtr15", "nip"] + (["reg15", "nip"] if k in ET_REG else []) + ["sch15", "obr15"]
    sx_ = 1.0 if (klyuch or "0")[0] == "0" else -1.0
    k_pom = [(-sx_ if (klyuch or "A")[-1] == "B" else sx_), 0.0]
    n0 = len(armatura)
    rv, (rn, _), p = vetka("V1", "ppr", 25, [(xr, y_op, z1)], (0, 0, -1), items, ur, gap=0.16, first=0.15,
                           sborka=True)
    svyaz((ra, 1), (rv, 0))
    for a_ in armatura[n0:]:
        if a_["key"] == "kran15vn" and a_.get("wp"):
            # ручка крана — к помещению: у VT.215 на плоскости ручка смотрит против нормали (снимок 30.10)
            a_["norm"] = [-k_pom[0], -k_pom[1]]
        elif a_["key"] == "filtr15" and a_.get("vert"):
            a_["lico"] = [-k_pom[1], k_pom[0]]         # отросток косого фильтра — вправо от смотрящего (как на фото)
        elif a_.get("vert"):
            a_["lico"] = k_pom                         # циферблаты счётчика и регулятора — к помещению (kvv_seti)
    seti[rn]["pts"] = seti[rn]["pts"][:1] + [R((xr, y_op, zf + Z_RAZV))]
    puti = {}
    starty = [nogi(xr, y_op, zf + Z_RAZV, f, ur, puti=puti) for f in nogi_]
    if len(starty) == 1:
        svyaz((rn, 1), (starty[0], 0))
    else:
        troynik((starty[0], 0), (starty[1], 0), (rn, 1))
    if klyuch is not None and k == N_ET:
        uzel = round(Z_UZEL - Z_RAZV + L_UZLA, 3)          # опуск узла и отвод с краном до тройника стояка
        razvodka_kv[klyuch] = {kl: put + [(N_PR, uzel, 25)] for kl, put in puti.items()}


def otvod_k1(x_l, y_r, z_r, napr, pr, ur):
    """Поэтажный отвод Ø50 вдоль x = x_l к крестовине стояка (x_l, y_r, z_r): приборы pr = [(соединитель, id)],
    первый — дальний (мойка), затем умывальник и ванна; унитаз — отдельно, в другой патрубок крестовины.
    Присоединения — косые тройники 45° (п. 18.5 СП 30); уклон I_OTV. Высокий слив (мойка, умывальник) — опуск и
    косой участок; низкий (ванна, выпуск на +0,095) — без опуска: от выпуска по его оси и косо, с уклоном не
    меньше I_OTV до тройника."""
    def zl(y):
        return z_r + I_OTV * abs(y - y_r)

    def prisoed(conn, yj, dl):
        """Точки присоединения прибора к отводу в тройнике (x_l, yj)."""
        zt = zl(yj)
        z_opusk = zt + I_OTV * dl * math.sqrt(2)
        if conn[2] - z_opusk >= 0.10:                      # есть место под отвод: опуск и косой участок
            return [conn, (conn[0], conn[1], z_opusk), (x_l, yj, zt)]
        a = 0.10                                           # по оси выпуска к коробу, затем косо 45°
        sx = math.copysign(1.0, x_l - conn[0])
        p1 = (conn[0] + sx * a, conn[1])
        L_ = a + math.hypot(x_l - p1[0], yj - p1[1])
        z1 = conn[2] - (conn[2] - zt) * a / L_
        return [conn, (p1[0], p1[1], z1), (x_l, yj, zt)]
    J = []
    for conn, _ in pr:
        dl = abs(conn[0] - x_l)
        if conn[2] - (z_r + 0.10) < 0.10:                  # низкий слив: косой участок короче на прямую вставку
            dl = max(dl - 0.10, 0.0)
        J.append((conn[1] + napr * dl, dl))
    (c0, f0), (y0, dl0) = pr[0], J[0]
    if dl0 < 0.02:                     # слив над линией отвода: опуск и отвод 90° в начале линии
        pts = [c0, (x_l, c0[1], zl(c0[1])), (x_l, y_r, z_r)]
    else:
        pts = prisoed(c0, y0, dl0) + [(x_l, y_r, z_r)]
    rr = razrezat("K1", "pp", 50, pts, [(x_l, yj) for yj, _ in J[1:]], ur)
    svyaz((rr[0], 0), dict(fix=f0, kind="san"))
    for i, ((conn, fid), (yj, dl)) in enumerate(zip(pr[1:], J[1:])):
        st_ = truba("K1", "pp", 50, prisoed(conn, yj, dl), ur)
        svyaz((st_, 0), dict(fix=fid, kind="san"))
        troynik((rr[i], 1), (rr[i + 1], 0), (st_, 1))
    return rr[-1]


def unitaz_k1(ct, pt_, xk, yk, z_c, ur):
    """Отвод от унитаза Ø110 (тип «Косой выпуск»: выпуск на +0,155 вниз под 45° к стене) — по оси выпуска до высоты
    крестовины, затем к стояку с уклоном I_UN; конец — на оси стояка (патрубок крестовины Ø110)."""
    s = ct["san"]
    L_ = math.hypot(xk - s[0], yk - s[1])
    ux, uy = (xk - s[0]) / L_, (yk - s[1]) / L_
    d45 = (s[2] - z_c - I_UN * L_) / (1.0 - I_UN)          # горизонтальная длина участка 45°
    p1 = (s[0] + ux * d45, s[1] + uy * d45, s[2] - d45)
    r = truba("K1", "pp", 110, [s, p1, (xk, yk, z_c)], ur)
    svyaz((r, 0), dict(fix=pt_, kind="san"))
    return r


# стояки квартир в локальных координатах секции: (В1, К1). По замечанию преподавателя (21.10.2026) стояк В1 —
# рядом с канализационным, в той же шахте за унитазом, со стороны стены; узел учёта и разводка — по линии стояка В1
# Расстояние между трубами К1 и В1 — 100 мм в свету (Глушков, чат КРП 10.10): оси в 175 мм (Ø110 и Ø40)
# кв. Б и В: стояк В1 — за мойкой (мойка в 85 мм от стены по оси 8, подводка к ней — отступом 85 мм)
ST_V = {"A": (0.41, 6.22), "B": (15.51, 7.42), "C": (15.89, 7.42)}
ST_K = {"A": (0.585, 6.22), "B": (15.325, 7.42), "C": (16.075, 7.43)}


def unitaz_hol(M, wloc, face, along, zf, ur, napr_y, y_st):
    """Унитаз; подводка к бачку — со стороны приборов (по ходу разводки от узла), иначе экземпляр отражается:
    у бачка только холодная вода, правило «холодная слева» к нему не относится."""
    pt_, ct = pribor2("unitaz", M, wloc, face, along, zf, ur)
    if (ct["cold"][1] - y_st) * napr_y < 0:
        pribory.pop()
        gabarity_pr.pop()
        pt_, ct = pribor2("unitaz", M, wloc, face, along, zf, ur, mir=True)
    return pt_, ct


def k1_kvartira(M, kv, zf, ur, st, ct, pt_, pr, napr):
    """К1 квартиры: крестовина двухплоскостная 110×50 на стояке — в один патрубок унитаз, в другой отвод Ø50 от
    остальных приборов (сначала все приборы, унитаз последним — к стояку отдельно)."""
    xk, yk = M.x(ST_K[kv][0]), ST_K[kv][1]
    z_c = zf + Z_KREST
    r_un = unitaz_k1(ct, pt_, xk, yk, z_c, ur)
    last = otvod_k1(xk, yk, z_c, napr, pr, ur)
    st["k" + kv].append((z_c, [(r_un, 1), (last, 1)]))


def kv_A(M, zf, ur, k, st):
    f_kor = X_KOR_A + 0.025                                   # грань короба шахты со стороны санузла
    pt_, ct = unitaz_hol(M, "-x", f_kor + 0.06, 6.22, zf, ur, -1, ST_V["A"][1])   # 60 мм от короба — под подводку
    pv, cv = pribor2("vanna", M, "-x", f_kor, 5.00, zf, ur)
    pu, cu = pribor2("umyv", M, "-x", f_kor, 4.625, zf, ur)
    pm, cm = pribor2("moyka", M, "-x", 0.20, 3.25, zf, ur)
    utoplen.add(tuple(round(v, 4) for v in cv["cold"]))
    xr, yr = M.x(ST_V["A"][0]), ST_V["A"][1]
    nog = [[(cv["cold"], pv, None), (cu["cold"], pu, None), (cm["cold"], pm, None)], [(ct["cold"], pt_, None)]]
    kv_v1(k, zf, ur, st["vA"], (xr, yr), (0, -1), nog, klyuch="%dA" % M.s)
    k1_kvartira(M, "A", zf, ur, st, ct, pt_, [(cm["san"], pm), (cu["san"], pu), (cv["san"], pv)], +1)


def kv_BC(M, zf, ur, k, st, kv):
    if kv == "B":
        w, face, face_k, y_un = "+x", 15.19, 15.49, 7.42
    else:
        w, face, face_k, y_un = "-x", 16.21, 15.91, 7.43
    # мойка — в 85 мм от грани стены по оси 8 (15,575 / 15,825): выпуск мойки над отводом К1 по оси стояка, за мойкой
    # проходит ветка В1 от стояка
    otstup = -0.05 if w == "+x" else 0.05      # унитаз в 50 мм от короба — место под подводку к бачку
    pt_, ct = unitaz_hol(M, w, face + otstup, y_un, zf, ur, +1, ST_V[kv][1])
    pv, cv = pribor2("vanna", M, w, face, 7.94, zf, ur)
    pu, cu = pribor2("umyv", M, w, face, 9.00, zf, ur)
    pm, cm = pribor2("moyka", M, w, face_k, 9.60, zf, ur)
    utoplen.add(tuple(round(v, 4) for v in cv["cold"]))
    xr, yr = M.x(ST_V[kv][0]), ST_V[kv][1]
    nog = [[(cv["cold"], pv, None), (cu["cold"], pu, None), (cm["cold"], pm, None)], [(ct["cold"], pt_, None)]]
    kv_v1(k, zf, ur, st["v" + kv], (xr, yr), (0, 1), nog, klyuch="%d%s" % (M.s, kv))
    k1_kvartira(M, kv, zf, ur, st, ct, pt_, [(cm["san"], pm), (cu["san"], pu), (cv["san"], pv)], -1)


kresty2 = []            # крестовины двухплоскостные К1: стояк, унитаз Ø110, отвод Ø50


def napr_vetki(ref):
    """Горизонтальное направление от оси стояка вдоль ветки (по последним точкам трубы ветки)."""
    r = seti[ref[0]]
    a, b = (r["pts"][0], r["pts"][1]) if ref[1] == 0 else (r["pts"][-1], r["pts"][-2])
    dx, dy = b[0] - a[0], b[1] - a[1]
    L_ = math.hypot(dx, dy)
    return [round(dx / L_, 4), round(dy / L_, 4)]


def stoyak(imya, sys_, x, y, uzly, niz, verh, ur_niz, d_fun, pt):
    """Стояк участками между узлами. runs — первые трубы участков (к ним снизу тройники), koncy — последние (их конец
    — отметка узла). У ППР смена диаметра — не в тройнике (у тройников ADSK нет перехода по проходу): в начале
    участка 0,15 м прежнего диаметра и муфта переходная."""
    uzly = sorted(uzly, key=lambda u: u[0])
    zz = [niz] + [u[0] for u in uzly] + [verh]
    runs, koncy, d_pred = [], [], None
    for i in range(len(zz) - 1):
        if zz[i + 1] - zz[i] < 1e-6:
            continue
        d = d_fun(i, len(uzly))
        if pt == "ppr" and d_pred is not None and d != d_pred and zz[i + 1] - zz[i] > 0.5:
            z_p = zz[i] + 0.15
            r1 = truba(sys_, pt, d_pred, [(x, y, zz[i]), (x, y, z_p)], ur_niz(zz[i]))
            r2 = truba(sys_, pt, d, [(x, y, z_p), (x, y, zz[i + 1])], ur_niz(z_p))
            svyaz((r1, 1), (r2, 0))
            runs.append(r1)
            koncy.append(r2)
        else:
            r = truba(sys_, pt, d, [(x, y, zz[i]), (x, y, zz[i + 1])], ur_niz(zz[i]))
            runs.append(r)
            koncy.append(r)
        d_pred = d
    for i, (z, vetv) in enumerate(uzly):
        a, b = koncy[i], runs[i + 1] if i + 1 < len(runs) else None
        if b is None:
            svyaz((a, 1), vetv[0])
        elif len(vetv) == 1:
            troynik((a, 1), (b, 0), vetv[0])
        elif sys_ == "K1":
            kresty2.append(dict(x=round(x, 4), y=round(y, 4), z=round(z, 4), m_niz=(a, 1), m_verh=(b, 0),
                                b110=vetv[0], b50=vetv[1], d110=napr_vetki(vetv[0]), d50=napr_vetki(vetv[1]),
                                ur=ur_niz(z)))
        else:
            kresty.append(dict(m1=(a, 1), m2=(b, 0), b1=vetv[0], b2=vetv[1]))
    stoyaki.append(dict(imya=imya, sys=sys_, x=round(x, 4), y=round(y, 4), niz=round(niz, 3), verh=round(verh, 3),
                        runs=koncy))
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
    # противопожарные муфты на полипропиленовых стояках К1 — под каждым междуэтажным перекрытием и под покрытием,
    # вплотную к низу плиты. Под перекрытием над подвалом муфты нет: ниже плиты стояк чугунный (переход SML — ПП
    # на Z_PP = −0,35 уходит в толщу плиты, полипропилен начинается внутри неё)
    for kv in "ABC":
        xk, yk = ST_K[kv]
        for k in range(1, N_ET + 1):
            z = round(k * H_ET - IZ["T_PEREKR"] - 0.05, 3)
            mufty.append(dict(x=round(M.x(xk), 4), y=yk, z=z, ur=ur_po_z(z)))


# нумерация стояков по часовой стрелке от северо-запада: северные (Б, В) слева направо, затем южные (А) справа налево
def nomera():
    sev = sorted([(M.x(ST_V[kv][0]), M.s, kv) for M in SEKCII for kv in "BC"])
    yug = sorted([(M.x(ST_V["A"][0]), M.s, "A") for M in SEKCII], reverse=True)
    return {(s, kv): i + 1 for i, (_, s, kv) in enumerate(sev + yug)}


NOM = nomera()

# ---------------- подвал: стояки В1, магистраль, ввод, насосная ----------------
Z_MAG = -0.6                            # отметка оси магистрали у тройника насосной (x = X_TR)
# магистраль — с уклоном 0,002 в одну сторону: от западного конца к восточному, к спускным кранам у основания
# Ст.В1-5 и у восточного поливочного крана (СП 30, п. 11.19; примечание «уклон 0,002 в сторону сливной арматуры», как
# в образце). Не «от тройника в обе стороны»: проход тройника насосной должен быть прямым (30.10 Revit не ставил тройник
# между участками 0,002 вверх и вниз). Ответвление и основание стояка — на отметке магистрали в точке врезки
I_MAG = 0.002
X_TR = 4.0


def zm(x):
    return round(Z_MAG - I_MAG * (x - X_TR), 4)
Y_MAG = 7.20
UR_P = "Подвал"
VYTYAZHKA = 0.2                        # вытяжная часть над неэксплуатируемой кровлей (п. 18.18 СП 30)

# стояки В1 — ППР PN20 от основания в подвале (Z_MAG) до узла верхнего этажа. Подводка от магистрали — сталь до
# крана у основания стояка, после крана — ППР. Сталь В1 и чугун К1 в плане не пересекаются (замечание
# преподавателя 21.10.2026): кв. А — в обход низа стояка К1 с юга, кв. Б и В — одним ответвлением между стояками К1
# (тройник и по крану на каждый стояк)
podvod = {}
DX_A_, X_PARA_ = 0.35, 15.70            # = DX_A, X_PARA ниже (врезки ответвлений)
for M in SEKCII:
    for kv in "ABC":
        x, y = M.x(ST_V[kv][0]), ST_V[kv][1]
        uzly = [(z, [b]) for z, b in st[M.s]["v" + kv]]

        def d_fun(i, n_uzl):
            return d_ppr_po_n(N_PR * (n_uzl - i) if i > 0 else N_PR * n_uzl, 25, 1.2)
        imya = "Ст.В1-%d" % NOM[(M.s, kv)]
        x_vr = x + DX_A_ * M.sx() if kv == "A" else M.x(X_PARA_)    # врезка ответвления в магистраль
        runs = stoyak(imya, "V1", x, y, uzly, zm(x_vr), max(z for z, _ in uzly), ur_po_z, d_fun, "ppr")
        podvod[imya] = [x, y, runs[0], d_fun(0, len(uzly)), N_PR * N_ET, x, kv, M, 0.0, 0.0]

DX_A = 0.35                             # кв. А: врезка в магистраль в 0,35 м от оси стояка В1 (за низом стояка К1)
Y_OBH = 0.37                            # кв. А: подводка южнее оси стояков на 0,37 м — мимо прочистки низа К1
X_PARA = 15.70                          # кв. Б и В: врезка посередине между стояками К1 (лок. x)


def dn_mag(n):
    return dn_po_n(n, 32)


def kran_dn(d):
    return {25: "kran25", 32: "kran32", 40: "kran40"}[d]


probki = []        # пробки ГОСТ 8963 на спускных кранах: конец штуцера (kvv_seti.probki)


def probka(aid, out, napr, L=0.03):
    """За спускным краном 1/2" — штуцер (отрезок стальной трубы DN15) и пробка на его конце (замечание 30.10:
    «крышки» на спусках). Пробку ставит 05 (kvv_seti.probki) по точке конца."""
    napr = tuple(napr) + (0.0,) * (3 - len(napr))
    q = tuple(out[i] + napr[i] * L for i in range(3))
    r = truba("V1", "stal", 15, [out, q], UR_P)
    svyaz((r, 0), dict(arm=aid, side="out"))
    probki.append(dict(x=round(q[0], 4), y=round(q[1], 4), z=round(q[2], 4)))


def osnovanie(ra, r_st):
    """Основание стояка В1: тройник — стояк вверх, вниз — спуск: ППР того же диаметра 0,12 м, переход на Ø20,
    колено и кран шаровой 1/2" горизонтально (замечание 28.10: краны для перекрытия и слива воды; краны VALTEC
    вертикально не ставятся)."""
    x, y, z = seti[r_st]["pts"][0]
    d = seti[r_st]["d"]
    # вниз 0,12 м (тройник на оси стояка), переход на Ø20, колено и горизонтально — к магистрали, под неё
    h = math.copysign(1.0, Y_MAG - y)
    q1, q2, q3 = (x, y, z - 0.12), (x, y, z - 0.24), (x, y + h * 0.12, z - 0.24)
    r1 = truba("V1", "ppr", d, [(x, y, z), q1], UR_P)
    r2 = truba("V1", "ppr", 20, [q1, q2, q3], UR_P)
    svyaz((r1, 1), (r2, 0))
    aid, out = arm("kran15", q3, (0, h), UR_P)
    svyaz((r2, 1), dict(arm=aid, side="in"))
    probka(aid, out, (0, h))
    troynik((r_st, 0), (r1, 0), (ra, 1))


def podvod_A(nm):
    """Кв. А: от магистрали на юг, мимо низа стояка К1 на запад (с краном), на север к основанию стояка В1."""
    x, y, r_st, d_st, n, _, kv, M = podvod[nm][:8]
    x_b, y_o = x + DX_A * M.sx(), y - Y_OBH
    d = dn_po_n(n, 25)
    z = zm(x_b)
    r0 = truba("V1", "stal", d, [(x_b, Y_MAG, z), (x_b, y_o, z)], UR_P)
    r1, (ra, _), p = vetka("V1", "stal", d, [(x_b, y_o, z)], (-M.sx(), 0), [kran_dn(d)], UR_P, first=0.10)
    svyaz((r0, 1), (r1, 0))
    seti[ra]["pt"], seti[ra]["d"] = "ppr", d_st
    seti[ra]["pts"] = seti[ra]["pts"][:1] + [R((x, y_o, z)), R((x, y, z))]
    osnovanie(ra, r_st)
    podvod[nm][5], podvod[nm][8], podvod[nm][9] = x_b, 0.0, abs(Y_MAG - y_o) + abs(x_b - x) + Y_OBH
    return r0


def podvod_para(M, nm_b, nm_c):
    """Кв. Б и В: одно ответвление от магистрали посередине между стояками К1 на север до линии стояков В1, тройник,
    по крану на каждый стояк."""
    y_ = podvod[nm_b][1]
    x_m = M.x(X_PARA)
    n2 = podvod[nm_b][4] + podvod[nm_c][4]
    z = zm(x_m)
    r0 = truba("V1", "stal", dn_po_n(n2, 25), [(x_m, Y_MAG, z), (x_m, y_, z)], UR_P)
    koncy = []
    for nm in (nm_b, nm_c):
        x, y, r_st, d_st, n = podvod[nm][:5]
        d = dn_po_n(n, 25)
        s_ = 1 if x > x_m else -1
        # краны пары смотрят входом в общий тройник, ручки VALTEC шли навстречу и перекрывали одна другую
        # (замечание 30.10). У второго крана ручка вбок, на север (к проходу, прочь от магистрали): кран на
        # вертикальной рабочей плоскости с нормалью +Y (kvv_seti.na_ploskost)
        kl = kran_dn(d) + ("wp" if nm == nm_c else "")
        r1, (ra, _), p = vetka("V1", "stal", d, [(x_m, y_, z)], (s_, 0), [kl], UR_P, first=0.07)
        if nm == nm_c:
            assert armatura[-1]["key"] == kl
            armatura[-1]["wp"], armatura[-1]["norm"] = True, [0.0, -1.0]     # нормаль плоскости −Y: ручка на +Y
        seti[ra]["pt"], seti[ra]["d"] = "ppr", d_st
        seti[ra]["pts"] = seti[ra]["pts"][:1] + [R((x, y, z))]
        osnovanie(ra, r_st)
        koncy.append(r1)
        podvod[nm][5], podvod[nm][8], podvod[nm][9] = x_m, abs(y_ - Y_MAG), abs(x - x_m)
    troynik((koncy[0], 0), (koncy[1], 0), (r0, 1))
    return r0


otbory = []                             # врезки в магистраль: (x, N, построить ответвление -> труба от магистрали)
for M in SEKCII:
    nmA, nmB, nmC = ["Ст.В1-%d" % NOM[(M.s, kv)] for kv in "ABC"]
    otbory.append((podvod[nmA][0] + DX_A * M.sx(), podvod[nmA][4], lambda nm=nmA: podvod_A(nm)))
    otbory.append((M.x(X_PARA), podvod[nmB][4] + podvod[nmC][4],
                   lambda M_=M, b=nmB, c=nmC: podvod_para(M_, b, c)))
vostok = sorted([o for o in otbory if o[0] > X_TR], key=lambda o: o[0])
zapad = [o for o in otbory if o[0] < X_TR]

prev_end, ost = None, sum(o[1] for o in vostok)
x_prev = X_TR
mag_vost = []
uchastki_mag = []                      # для сверки с расчётом: (откуда, куда, длина, N)
for i, o in enumerate(vostok):
    x = o[0]
    r = truba("V1", "stal", dn_mag(ost), [(x_prev, Y_MAG, zm(x_prev)), (x, Y_MAG, zm(x))], UR_P)
    uchastki_mag.append((round(x_prev, 3), round(x, 3), round(x - x_prev, 3), ost, dn_mag(ost)))
    mag_vost.append(r)
    ost -= o[1]
    if prev_end is not None:
        troynik(prev_end, (r, 0), (vostok[i - 1][2](), 0))
    prev_end = (r, 1)
    x_prev = x
# поливочные краны (СП 30.13330.2020, п. 5.4.4: в нишах наружных стен, по одному на 60–70 м периметра; периметр
# здания ~117 м — два крана, по одному на торце каждой секции): врезка в магистраль у торца, подводка к торцевой
# стене южнее подводки к стояку кв. А, подъём до +0,500 и выход через стену — кран водоразборный на фасаде
X_POL = 1.0                             # врезка — в 1 м от оси торцевой стены (до ответвления к крайнему стояку)
Z_POL = 0.5
Y_POL = 2.90                            # у торца южнее мойки кв. А: подъём не через санузел, мимо низа К1
DN_POL = 25                             # кран VALTEC VT.051 — патрубок 1"
krany_pol = []


def polivochnyy(M_, x_t):
    sx = M_.sx()
    x_in = M_.x(0.25)                    # у внутренней грани торцевой стены (0,20)
    x_nar = M_.x(-E - T_NAR / 2)         # наружная грань
    y_k = Y_POL
    # в подвале — кран перекрытия и спускной кран (замечание 28.10)
    s_ = math.copysign(1.0, x_in - x_t)
    z = zm(x_t)
    r0 = truba("V1", "stal", DN_POL, [(x_t, Y_MAG, z), (x_t, y_k, z)], UR_P)
    r1, (r2, _), p_ = vetka("V1", "stal", DN_POL, [(x_t, y_k, z)], (s_, 0), ["kran%d" % DN_POL], UR_P,
                            first=0.12)
    svyaz((r0, 1), (r1, 0))
    x_sp = p_[0] + s_ * 0.13
    seti[r2]["pts"] = seti[r2]["pts"][:1] + [R((x_sp, y_k, z))]
    r_sp = truba("V1", "stal", 15, [(x_sp, y_k, z), (x_sp, y_k + 0.12, z)], UR_P)
    a_sp, o_sp = arm("kran15", (x_sp, y_k + 0.12, z), (0, 1), UR_P)
    svyaz((r_sp, 1), dict(arm=a_sp, side="in"))
    probka(a_sp, o_sp, (0, 1))
    r = truba("V1", "stal", DN_POL, [(x_sp, y_k, z), (x_in, y_k, z), (x_in, y_k, Z_POL),
                                     (x_nar, y_k, Z_POL)], UR_P)
    troynik((r2, 1), (r, 0), (r_sp, 0))
    aid = len(armatura)
    armatura.append(dict(id=aid, key="kran_pol", fam="VALTEC_VT.051.N_Кран поливочный", tip="VT.051",
                         x=round(x_nar, 4), y=round(y_k, 4), z=Z_POL, th=0.0 if sx > 0 else 180.0, ur=UR_P))
    svyaz((r, 1), dict(arm=aid, side="in"))
    krany_pol.append(dict(sek=M_.s, x=round(x_nar, 3), y=round(y_k, 3), z=Z_POL))
    return r0


# восточный конец магистрали (секция 2): последний участок — до врезки, после врезки — к ответвлению кв. А
r_last = prev_end[0]
x_pol2 = SEKCII[-1].x(X_POL)
seti[r_last]["pts"][-1] = R((x_pol2, Y_MAG, zm(x_pol2)))
r_e2 = truba("V1", "stal", seti[r_last]["d"], [(x_pol2, Y_MAG, zm(x_pol2)), (vostok[-1][0], Y_MAG, zm(vostok[-1][0]))],
             UR_P)
troynik((r_last, 1), (r_e2, 0), (polivochnyy(SEKCII[-1], x_pol2), 0))
svyaz((r_e2, 1), (vostok[-1][2](), 0))
o_z = zapad[0]
r_zap = truba("V1", "stal", dn_mag(o_z[1]), [(X_TR, Y_MAG, Z_MAG), (X_POL, Y_MAG, zm(X_POL))], UR_P)
r_zap2 = truba("V1", "stal", dn_mag(o_z[1]), [(X_POL, Y_MAG, zm(X_POL)), (o_z[0], Y_MAG, zm(o_z[0]))], UR_P)
troynik((r_zap, 1), (r_zap2, 0), (polivochnyy(SEKCII[0], X_POL), 0))
svyaz((r_zap2, 1), (o_z[2](), 0))

nas = json.load(open(os.path.join(HERE, "..", "calc", "nasos_v3.json"), encoding="utf-8"))
XP, YP = 5.0, 4.0                       # установка COR-2 (соединители коллекторов на локальной -X)
Z_FUND = 0.27                           # установка на фундаменте 270 мм (как в образце), Revit: kvv_seti.fundament_nasosa
p_vs = (XP, YP - 0.361, Z_P + Z_FUND + 0.168)
p_nap = (XP, YP + 0.480, Z_P + Z_FUND + 0.168)
oborud = [dict(fam="COR-MVL_2_32_Revit2019(08.25)", tip=nas["tip"], x=XP, y=YP, th=0, ur=UR_P,
               vs=R(p_vs), nap=R(p_nap))]
# напорная линия установки до тройника магистрали (проектируется только В1: ГВС вне объёма проекта)
N_VSE = sum(v[4] for v in podvod.values())
# у стальных тройников ADSK ответвление не больше прохода: перед тройником магистрали — переход на диаметр прохода
D_NAP2 = max(seti[r_zap]["d"], seti[mag_vost[0]]["d"])
Y_NAP2 = Y_MAG - 0.25
r_nap = truba("V1", "stal", 50, [p_nap, (X_TR, p_nap[1], p_nap[2]), (X_TR, p_nap[1], Z_MAG), (X_TR, Y_NAP2, Z_MAG)],
              UR_P)
svyaz((r_nap, 0), dict(obor=0, kind="nap"))
r_nap2 = truba("V1", "stal", D_NAP2, [(X_TR, Y_NAP2, Z_MAG), (X_TR, Y_MAG, Z_MAG)], UR_P)
svyaz((r_nap, 1), (r_nap2, 0))
troynik((r_zap, 0), (mag_vost[0], 0), (r_nap2, 1))
L_NAP = round(sum(math.dist(a, b) for r_ in (r_nap, r_nap2)
                  for a, b in zip(seti[r_]["pts"][:-1], seti[r_]["pts"][1:])), 2)

Z_VV = -2.5
Y_ST_A = -E - T_NAR / 2                 # наружная грань стены по оси А
r_vv = truba("V1", "pe", 63, [(X_TR, Y_ST_A - 2.0, Z_VV), (X_TR, Y_IN0, Z_VV)], UR_P)
Z_VU = -2.0
r_v1 = truba("V1", "stal", 50, [(X_TR, Y_IN0, Z_VV), (X_TR, 1.43, Z_VV), (X_TR, 1.43, Z_VU), (X_TR, 1.73, Z_VU)], UR_P)
svyaz((r_vv, 1), (r_v1, 0))
# водомерный узел (30.10, по замечанию «собери правильно, все части — из «Семейства ВК»): тройник обвода — задвижка
# KR11 DN50 и фильтр IS40 DN50 на фланцах встык — переход 50/DN_SCH — счётчик — тройник с контрольно-спускным краном
# (СП 30, п. 12.9) — переход — задвижка KR11 DN50 — тройник обвода; на обводной линии — задвижка KR11 DN50,
# опломбированная закрытой (п. 12.10–12.11). Переходы 50/25 Revit ставит сам (муфты ГОСТ 8957)
Y_OUT = 3.46                            # выходной тройник обвода (до 30.10 — 3,25: узел на фланцевой арматуре длиннее)
r_a, (r_b, _), p = vetka("V1", "stal", 50, [(X_TR, 1.73, Z_VU)], (0, 1), ["zadv50", "filtr50"], UR_P, first=0.10,
                         sborka=True)
# второй контрольный кран — не далее 0,5 м после первой задвижки (СП 30, п. 12.9): тройник на участке DN50 сразу
# за фильтром (0,40 м от фланца задвижки), кран 1/2" вбок, штуцер с пробкой; дальше DN50 0,10 м и переход на DN_SCH
Y_T = round(p[1] + 0.07, 3)
Y_P1 = round(Y_T + 0.17, 3)            # тройник 50×15 + переход 50/DN_SCH (Revit): при 0,10 оставалось 7,5 мм трубы
seti[r_b]["pts"] = seti[r_b]["pts"][:1] + [R((X_TR, Y_T, Z_VU))]
r_b2 = truba("V1", "stal", 50, [(X_TR, Y_T, Z_VU), (X_TR, Y_P1, Z_VU)], UR_P)
r_k1 = truba("V1", "stal", 15, [(X_TR, Y_T, Z_VU), (X_TR + 0.15, Y_T, Z_VU)], UR_P)     # выход тройника 50×15 длиннее
a_k1, o_k1 = arm("kran15", (X_TR + 0.15, Y_T, Z_VU), (1, 0), UR_P)
svyaz((r_k1, 1), dict(arm=a_k1, side="in"))
probka(a_k1, o_k1, (1, 0))
troynik((r_b, 1), (r_b2, 0), (r_k1, 0))
DN_SCH = REZ["schetchik_dom"][0]        # общедомовой счётчик — по расчёту (холодный расход)
r_sch, (r_sch2, _), p = vetka("V1", "stal", DN_SCH, [(X_TR, Y_P1, Z_VU)], (0, 1), ["sch%d" % DN_SCH], UR_P,
                              first=0.10)
Y_KSK = round(p[1] + 0.06, 3)
seti[r_sch2]["pts"] = seti[r_sch2]["pts"][:1] + [R((X_TR, Y_KSK, Z_VU))]
Y_P2 = round(Y_KSK + 0.16, 3)          # тройник КСК + переход DN_SCH/50 (Revit) — 0,10 мало, оставалось 3 мм трубы
r_sch3 = truba("V1", "stal", DN_SCH, [(X_TR, Y_KSK, Z_VU), (X_TR, Y_P2, Z_VU)], UR_P)
r_ksk = truba("V1", "stal", 15, [(X_TR, Y_KSK, Z_VU), (X_TR + 0.12, Y_KSK, Z_VU)], UR_P)
a_ksk, o_ksk = arm("kran15", (X_TR + 0.12, Y_KSK, Z_VU), (1, 0), UR_P)
svyaz((r_ksk, 1), dict(arm=a_ksk, side="in"))
probka(a_ksk, o_ksk, (1, 0))
troynik((r_sch2, 1), (r_sch3, 0), (r_ksk, 0))
svyaz((r_b2, 1), (r_sch, 0))
r_c, (r_d, _), p = vetka("V1", "stal", 50, [(X_TR, Y_P2, Z_VU)], (0, 1), ["zadv50"], UR_P, first=0.08)
svyaz((r_sch3, 1), (r_c, 0))
seti[r_d]["pts"] = seti[r_d]["pts"][:1] + [R((X_TR, Y_OUT, Z_VU))]
r_vs = truba("V1", "stal", 50, [(X_TR, Y_OUT, Z_VU), (X_TR, p_vs[1], Z_VU), (X_TR, p_vs[1], p_vs[2]), p_vs], UR_P)
svyaz((r_vs, 1), dict(obor=0, kind="vs"))
r_o1, (r_o2, _), p = vetka("V1", "stal", 50, [(X_TR, 1.73, Z_VU), (X_TR - 0.2, 1.73, Z_VU)], (0, 1), ["zadv50"],
                           UR_P, first=0.4)
seti[r_o2]["pts"] = seti[r_o2]["pts"][:1] + [R((X_TR - 0.2, Y_OUT, Z_VU)), R((X_TR, Y_OUT, Z_VU))]
troynik((r_v1, 1), (r_a, 0), (r_o1, 0))
troynik((r_d, 1), (r_vs, 0), (r_o2, 1))

# ---------------- подвал: стояки К1, сборные трубопроводы, выпуски ----------------
# Как в образце преподавателя (замечание 21.10.2026 «вытащить канализацию из земли»): сборные трубопроводы — под
# потолком подвала (лоток у дальнего стояка −0,80, уклон 0,02), у наружной стены по оси Д — опуск с прочисткой
# вверху и переход в выпуск двумя отводами 45° (п. 18.4 СП 30). Выпуск — в 3 м от торцевой стены (X_V) с уклоном
# 0,01 (как в образце: «К1 Ø100 l = 3 м; i = 0.01»). П. 18.5: стояки присоединяются к сборному трубопроводу под 45°.
Z_PP = -0.35
Y_ST_D = B + E + T_NAR / 2
LOT_ST = -2.0                           # лоток выпуска у наружной стены (99,00 абс.)
I_VN = 0.02                             # сборные трубопроводы в подвале
I_VYP = 0.01                            # выпуски
R110 = 0.055
D45 = 0.2
Y_SB = 8.2
X_V = 3.0                               # ось выпуска от оси 1 (лок.): 3,3 м от наружной грани торцевой стены
LOT_0 = -0.80                           # лоток у начала сборного трубопровода (у дальнего стояка кв. В)
# Как в образце преподавателя (лотки −0,67…−1,04 при 12 этажах), решение пользователя 29.10: от крестовины 1-го
# этажа до перехода стояка в горизонтальный ~0,6–0,98 м < 1 м — отступление от СП 30, п. 18.4 (NORMY.md)
Y_OP = B - 0.2 - 0.25                   # опуск — в 0,25 м от внутренней грани стены по оси Д
DY_T = 0.45                             # тройник сборного кв. Б, В на линии выпуска — в 0,45 м севернее Y_SB


def dlina(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts[:-1], pts[1:]))


def s_uklonom(tochki, z0, i=I_VN):
    """Точки плана с отметками оси: от z0 в первой точке вниз по ходу с уклоном i."""
    out, z = [], z0
    for k, (x, y) in enumerate(tochki):
        if k:
            z -= i * math.hypot(x - tochki[k - 1][0], y - tochki[k - 1][1])
        out.append((x, y, z))
    return out


L_PR = 0.30                             # отрезок за косым тройником против течения — к заглушке-прочистке
zaglushki = []


def niz_stoyaka(x, y, plan):
    """Низ стояка К1: вертикаль, отвод 45° и косой тройник 45° на горизонтальном участке (п. 18.4–18.5 СП 30);
    за тройником против течения — короткий отрезок с заглушкой: прочистка «Пр.» в начале горизонтального участка
    (п. 18.26 СП 30, как в образце). Возвращает (труба от стояка до тройника, горизонтальный участок от тройника)."""
    (x1, y1, z1) = plan[0]
    ux, uy = plan[1][0] - x1, plan[1][1] - y1
    L_ = math.hypot(ux, uy)
    ux, uy = ux / L_, uy / L_
    r_v = truba("K1", "sml", 100, [(x, y, Z_PP), (x, y, z1 + D45), (x1, y1, z1)], UR_P)
    p_pr = (x1 - ux * L_PR, y1 - uy * L_PR, z1 + I_VN * L_PR)
    r_pr = truba("K1", "sml", 100, [p_pr, (x1, y1, z1)], UR_P)
    r_g = truba("K1", "sml", 100, plan, UR_P)
    troynik((r_pr, 1), (r_g, 0), (r_v, 1))
    zaglushki.append(dict(r=r_pr, end=0, x=round(p_pr[0], 3), y=round(p_pr[1], 3), z=round(p_pr[2], 3)))
    return r_v, r_g


vypuski = []
k1_podval = {}
for M in SEKCII:
    sx = M.sx()
    (xA, yA), (xB, yB), (xC, yC) = [(M.x(ST_K[kv][0]), ST_K[kv][1]) for kv in "ABC"]
    xV = M.x(X_V)
    y_t = Y_SB + DY_T
    # кв. В -> кв. Б -> косым тройником в линию выпуска
    plan_C = [(xC, yC + D45), (xC, Y_SB - 0.15), (xC - 0.15 * sx, Y_SB), (xB - 0.3 * sx, Y_SB),
              (xV + DY_T * sx, Y_SB), (xV, y_t)]
    pC = s_uklonom(plan_C, LOT_0 + R110)
    r_vC, r_sb1 = niz_stoyaka(xC, yC, pC[:4])
    # СП 30, п. 18.30, табл. 18.1: между прочистками на d 100 — не более 15 м. От прочистки у стояка кв. Б до опуска
    # было 16,9 м — на повороте к линии выпуска косой тройник и прочистка (отрезок прямо по ходу с заглушкой)
    r_sb2a = truba("K1", "sml", 100, pC[3:5], UR_P)
    ux, uy = pC[4][0] - pC[3][0], pC[4][1] - pC[3][1]
    L_ = math.hypot(ux, uy)
    p_pr2 = (pC[4][0] + ux / L_ * 0.2, pC[4][1] + uy / L_ * 0.2, pC[4][2] - I_VN * 0.2)
    r_pr2 = truba("K1", "sml", 100, [pC[4], p_pr2], UR_P)
    r_sb2 = truba("K1", "sml", 100, pC[4:], UR_P)
    troynik((r_sb2a, 1), (r_pr2, 0), (r_sb2, 0))
    zaglushki.append(dict(r=r_pr2, end=1, x=round(p_pr2[0], 3), y=round(p_pr2[1], 3), z=round(p_pr2[2], 3)))
    z_t = pC[-1][2]
    plan_B = [(xB, yB + D45), (xB, Y_SB - 0.3), (xB - 0.3 * sx, Y_SB)]
    pB = s_uklonom(plan_B, pC[3][2] + I_VN * dlina(plan_B))
    r_vB, r_st2 = niz_stoyaka(xB, yB, pB)
    troynik((r_sb1, 1), (r_sb2a, 0), (r_st2, 1))
    # кв. А — линия выпуска: на север, на восток под потолком до X_V, на север к опуску у стены
    plan_A = [(xA, yA + D45), (xA, Y_SB - 0.15), (xA + 0.15 * sx, Y_SB), (xV - 0.15 * sx, Y_SB), (xV, Y_SB + 0.15),
              (xV, y_t)]
    pA = s_uklonom(plan_A, z_t + I_VN * dlina(plan_A))
    r_vA, r_a1 = niz_stoyaka(xA, yA, pA)
    p_op = (xV, Y_OP, z_t - I_VN * (Y_OP - y_t))
    r_a2 = truba("K1", "sml", 100, [pA[-1], p_op], UR_P)
    troynik((r_a1, 1), (r_a2, 0), (r_sb2, 1))
    # опуск: вверху тройник и прочистка (отрезок к стене с заглушкой), внизу два отвода 45° в выпуск
    p_pr = (xV, Y_OP + 0.15, p_op[2] - I_VN * 0.15)
    r_pr = truba("K1", "sml", 100, [p_op, p_pr], UR_P)
    zaglushki.append(dict(r=r_pr, end=1, x=round(p_pr[0], 3), y=round(p_pr[1], 3), z=round(p_pr[2], 3)))
    z_b = LOT_ST + R110 + I_VYP * (Y_ST_D - (Y_OP + D45))
    y_kon = Y_ST_D + 1.0
    r_op = truba("K1", "sml", 100, [p_op, (xV, Y_OP, z_b + D45), (xV, Y_OP + D45, z_b),
                                    (xV, y_kon, z_b - I_VYP * (y_kon - Y_OP - D45))], UR_P)
    troynik((r_a2, 1), (r_pr, 0), (r_op, 0))
    vypuski.append(dict(sek=M.s, x=round(xV, 3), y_stena=round(Y_ST_D, 3), lotok=round(LOT_ST, 3)))
    k1_podval[M.s] = dict(
        L_CB=round(dlina(plan_C[:4]), 3), L_BT=round(dlina(plan_C[3:]), 3), L_AT=round(dlina(plan_A), 3),
        L_TO=round(Y_OP - y_t, 3), L_OP=round(p_op[2] - z_b, 3), L_VYP_IN=round(Y_ST_D - Y_OP - D45, 3),
        lot_C=round(pC[0][2] - R110, 3), lot_B=round(pB[0][2] - R110, 3), lot_A=round(pA[0][2] - R110, 3),
        lot_T=round(z_t - R110, 3), lot_OP=round(p_op[2] - R110, 3), lot_niz=round(z_b - R110, 3))
    for kv, (x, y), r_niz in (("A", (xA, yA), r_vA), ("B", (xB, yB), r_vB), ("C", (xC, yC), r_vC)):
        imya = "Ст.К1-%d" % NOM[(M.s, kv)]
        runs = stoyak(imya, "K1", x, y, st[M.s]["k" + kv], Z_PP, Z_KR + VYTYAZHKA, ur_po_z,
                      lambda i, n: 110, "pp")
        svyaz((runs[0], 0), (r_niz, 0))


# ---------------- проверки ----------------
TOL = 0.002
TOLSH = {"nar": T_NAR, "fund": 0.316, "nes": T_NES, "per": 0.10, "beton": 0.20, "korob": 0.05}
ZST = {"etazhi": (0.0, Z_KR), "podval": (Z_P, 0.0), "vse": (Z_P, Z_KR), "Этаж 01": (0.0, H_ET)}
NAR_D = {("stal", 15): 0.0213, ("stal", 20): 0.0268, ("stal", 25): 0.0335, ("stal", 32): 0.0423,
         ("stal", 40): 0.048, ("stal", 50): 0.060, ("pp", 50): 0.050, ("pp", 110): 0.110, ("sml", 100): 0.110,
         ("pe", 63): 0.063, ("ppr", 20): 0.020, ("ppr", 25): 0.025, ("ppr", 32): 0.032, ("ppr", 40): 0.040,
         ("ppr", 50): 0.050}


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
            if zb <= sza + TOL or za >= szb - TOL:      # касание по высоте (прибор 1-го этажа над стеной подвала)
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
    for fid_, pts_ in PODVOD_XY.items():
        soed_xy.setdefault(fid_, []).extend(pts_)
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
            z_niz = za + (0.15 if pribory[pid]["key"] == "vanna" else 0.0)   # под ванной — сифон и отвод
            for i in range(1, 20):
                q = [p1[k] + (p2[k] - p1[k]) * i / 20 for k in range(3)]
                if x0 + rad < q[0] < x1 - rad and y0 + rad < q[1] < y1 - rad and z_niz < q[2] < zb:
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
        if p["key"] == "unitaz":
            continue                    # у бачка только холодная — подводка со стороны разводки (unitaz_hol)
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
         ("stal", 50): 0.065, ("pp", 50): 0.06, ("pp", 110): 0.07, ("sml", 100): 0.10, ("pe", 63): 0.07,
         ("ppr", 20): 0.03, ("ppr", 25): 0.035, ("ppr", 32): 0.04, ("ppr", 40): 0.045, ("ppr", 50): 0.05}


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
    for t in kresty2:                   # двухплоскостная 110×50: патрубки на 65 мм от оси, низ — 121 мм
        fit_konec[tuple(t["m_niz"])] = 0.121
        for k in ("m_verh", "b110", "b50"):
            fit_konec[tuple(t[k])] = 0.065
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
            if L_ < nado + 0.005:
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
    T = {"nar": T_NAR, "nes": T_NES, "per": 0.10, "beton": 0.20, "korob": 0.05}

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
    T = {"nar": T_NAR, "nes": T_NES, "per": 0.10, "beton": 0.20, "korob": 0.05, "fund": 0.316}
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
# стояки В1: x, y, x врезки в магистраль, длина общей части ответвления (кв. Б и В — на два стояка), своей части
trassa_v3 = dict(stoyaki_v1={nm: [round(v[0], 3), v[1], round(v[5], 3), round(v[8], 3), round(v[9], 3),
                                  "%d%s" % (v[7].s, v[6])] for nm, v in podvod.items()},
                 magistral=uchastki_mag,
                 x_troynik=X_TR, y_mag=Y_MAG, z_mag=Z_MAG, vypuski=vypuski, l_nap=L_NAP, n_vse=N_VSE,
                 zerkalo=ZERK, x_shov=round(L_SEK + DSH / 2, 3),
                 stoyaki_k1={s["imya"]: [s["x"], s["y"]] for s in stoyaki if s["sys"] == "K1"},
                 krany_pol=krany_pol, zaglushki=zaglushki, x_v=X_V, k1_podval=k1_podval[0],
                 uzel=dict(z_uzel=Z_UZEL, z_razv=Z_RAZV, l_uzla=L_UZLA, z_krest=Z_KREST),
                 razvodka=razvodka_kv)
json.dump(trassa_v3, open(os.path.join(HERE, "..", "calc", "trassa_v3.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

geo = dict(pomescheniya=pomescheniya, razdeliteli=razdeliteli, pribory=pribory, seti=seti, troyniki=troyniki, kresty=kresty, kresty2=kresty2, armatura=armatura, svyazi=svyazi, arm_svyazi=arm_svyazi, arm_pribor=arm_pribor, gibkie=gibkie,
           mufty=mufty, stoyaki=stoyaki, oborud=oborud, dveri=dveri, lestnicy=lestnicy,
           zaglushki=zaglushki, krany_pol=krany_pol, probki=probki,
           sistemy=dict(V1="ADSK_Водопровод_В1", K1="ADSK_Канализация_К1"),
           tipy_trub=dict(stal="ADSK_Сталь водогазопроводная_Оцинкованная_ГОСТ 3262-75",
                          pp="ADSK_Полипропилен раструбный_ГОСТ 32414-2013",
                          sml="ADSK_Чугун_Безраструбный SML_DIN EN 877",
                          pe="ADSK_Полиэтилен ПЭ100 SDR17_ГОСТ 18599-2001",
                          ppr="ADSK_Полипропилен_PN20"),
           urovni=urovni, osi=osi, steny=steny, okna=okna, perekr=perekr, krovlya=krovlya, zemlya=zemlya,
           tipy=dict(nar="ADSK_Наружная отделка_Кирпич250_Слоистая кладка330_580",
                     fund="ADSK_Фундамент_Бетон300_Гидроизоляция16_316",
                     nes="ADSK_Внутренняя_Кирпич_250",
                     per="ADSK_Перегородка_ПГП_100",
                     korob="КВВ_Короб_ГКЛВ_50",
                     beton="ADSK_Внутренняя_Бетон_200",
                     perekr="ADSK_Перекрытие_Плита с полом_Бетон200 стяжка80 плитка20_300",
                     pol_podv="ADSK_Фундамент_Бетон200_Двухслойная Гидроизоляция249_449",
                     krovlya="ADSK_Плоская кровля по бетонному основанию_290"))

with open(os.path.join(HERE, "geometriya_v3.json"), "w", encoding="utf-8") as f:
    json.dump(geo, f, ensure_ascii=False, indent=1)
