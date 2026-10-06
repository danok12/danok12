"""Книга Excel: исходные отметки, точки нулевых работ, объёмы ПВ/ПН (с формулами)."""
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.comments import Comment
import raschet as R

FONT = "GOST type B"            # ГОСТ 2.304, тип Б (файл GOST_B.TTF)
thin = Side(style="thin")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
F_IN = Font(name=FONT, size=12, color="0000FF")          # исходные данные
F_LINK = Font(name=FONT, size=12, color="008000")        # ссылка на другой лист
F_CALC = Font(name=FONT, size=12)
F_B = Font(name=FONT, size=12, bold=True)
F_T = Font(name=FONT, size=14, bold=True)
YEL = PatternFill("solid", fgColor="FFFF00")
HEAD = PatternFill("solid", fgColor="DDEBF7")
CEN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

wb = Workbook()
S1 = "Исходные данные"
ws = wb.active
ws.title = S1


def cell(sh, ref, val, font=F_CALC, fmt=None, al=CEN, box=True, fill=None):
    c = sh[ref]
    c.value = val
    c.font = font
    c.alignment = al
    if fmt: c.number_format = fmt
    if box: c.border = BOX
    if fill: c.fill = fill
    return c


# ---------- лист 1: исходные данные ----------
ws["A1"] = "Курсовая работа «Технологическая карта на производство земляных работ». Вариант 2"
ws["A1"].font = F_T
cell(ws, "A3", "Сторона квадрата сетки a, м", F_CALC, al=LEFT)
cell(ws, "B3", R.A, F_IN)
cell(ws, "A4", "Коэффициент остаточного разрыхления Kор", F_CALC, al=LEFT)
cell(ws, "B4", 1.04, F_IN, "0.00", fill=YEL)
ws["B4"].comment = Comment(
    "Супесь: остаточное разрыхление 3–5 % (табл. П2.1 методички), Kор = 1,03…1,05. "
    "Принято 1,04 — по указанию преподавателя брать в этом диапазоне.", "расчёт")
cell(ws, "A5", "Грунт", F_CALC, al=LEFT)
cell(ws, "B5", "супесь", F_IN)
cell(ws, "A6", "Число квадратов", F_CALC, al=LEFT)
cell(ws, "B6", R.NX * R.NY, F_IN)
ws["D3"] = "Редактировать можно только синие ячейки (жёлтая — принятое допущение)."
ws["D4"] = "Рабочая отметка h = Hкр − Hчёрн: «−» — выемка (ПВ), «+» — насыпь (ПН)."
ws["D5"] = "Отметки — приложение 1 методички, вариант 2. Вершины нумеруются построчно слева направо, сверху вниз."
for r in ("D3", "D4", "D5"):
    ws[r].font = Font(name=FONT, size=11, italic=True)

cell(ws, "A8", "№ вершины", F_B, fill=HEAD)
cell(ws, "B8", "h, м", F_B, fill=HEAD)
HREF = {}
for k, v in enumerate(R.H, start=1):
    r = 8 + k
    cell(ws, f"A{r}", f"h{k}")
    cell(ws, f"B{r}", float(v), F_IN, "0.00")
    HREF[k] = f"'{S1}'!$B${r}"

ws["D8"] = "Схема сетки (вид в плане, квадрат 100×100 м)"
ws["D8"].font = F_B
cols = "DEFGHI"
for j in range(R.NY + 1):
    for i in range(R.NX + 1):
        n = R.vnum(i, j)
        cell(ws, f"{cols[i]}{9 + 2 * j}", f"h{n}", Font(name=FONT, size=9, color="808080"))
        cell(ws, f"{cols[i]}{10 + 2 * j}", f"=B{8 + n}", F_CALC, "0.00")
ws.column_dimensions["A"].width = 44
ws.column_dimensions["B"].width = 10
for c in cols: ws.column_dimensions[c].width = 9

# ---------- лист 2: ЛНР ----------
S2 = "ЛНР"
w2 = wb.create_sheet(S2)
w2["A1"] = "Точки нулевых работ на сторонах квадратов"
w2["A1"].font = F_T
w2["A2"] = "x1 = a·|h1| / (|h1| + |h2|) — расстояние от вершины 1 до точки нуля;  x2 = a − x1"
w2["A2"].font = Font(name=FONT, size=12, italic=True)
hdr = ["№ т.0", "Сторона", "Вершина 1", "h1, м", "Вершина 2", "h2, м",
       "x1 (от верш. 1), м", "x2 (от верш. 2), м"]
for k, t in enumerate(hdr):
    cell(w2, f"{'ABCDEFGH'[k]}4", t, F_B, fill=HEAD)
ZROW = {}
zp = sorted(R.ZP, key=lambda z: (z["p1"], z["p2"]))
for k, z in enumerate(zp, start=1):
    r = 4 + k
    ZROW[(z["p1"], z["p2"])] = r
    horiz = z["p2"] == z["p1"] + 1
    cell(w2, f"A{r}", k)
    cell(w2, f"B{r}", "горизонтальная" if horiz else "вертикальная")
    cell(w2, f"C{r}", f"h{z['p1']}")
    cell(w2, f"D{r}", f"={HREF[z['p1']]}", F_LINK, "0.00")
    cell(w2, f"E{r}", f"h{z['p2']}")
    cell(w2, f"F{r}", f"={HREF[z['p2']]}", F_LINK, "0.00")
    cell(w2, f"G{r}", f"='{S1}'!$B$3*ABS(D{r})/(ABS(D{r})+ABS(F{r}))", F_CALC, "0.00")
    cell(w2, f"H{r}", f"='{S1}'!$B$3-G{r}", F_CALC, "0.00")
for c, wd in zip("ABCDEFGH", (7, 16, 11, 9, 11, 9, 18, 18)):
    w2.column_dimensions[c].width = wd

# ---------- лист 3: объёмы ----------
S3 = "Объёмы"
w3 = wb.create_sheet(S3)
w3["A1"] = "Объёмы планировочных работ (метод квадратов)"
w3["A1"].font = F_T
w3["A2"] = "Vi = Fi · hср,i;   hср,i = (|h1| + |h2| + … + |hn|) / n, в точках нуля h = 0"
w3["A2"].font = Font(name=FONT, size=12, italic=True)
A2 = f"'{S1}'!$B$3^2"


def dist(v, e):
    """Ссылка на расстояние от вершины v до точки нуля на стороне e."""
    r = ZROW[e]
    return f"'{S2}'!$G${r}" if v == e[0] else f"'{S2}'!$H${r}"


FCELL = {}      # имя фигуры -> адрес ячейки F


def describe(f):
    vs = [lb[1] for lb in f["labels"] if lb[0] == "v"]
    zs = [lb[1] for lb in f["labels"] if lb[0] == "z"]
    kind = {4: "квадрат", 1: "треугольник", 2: "трапеция", 3: "пятиугольник"}[len(vs)]
    txt = ", ".join(f"h{v}" for v in vs)
    if zs:
        txt += "; т.0 на " + ", ".join(f"h{a}–h{b}" for a, b in zs)
    return kind, vs, zs, txt


def area_formula(f, vs, zs, other_ref):
    if len(vs) == 4:
        return f"={A2}"
    if len(vs) == 1:
        v = vs[0]
        return f"={dist(v, zs[0])}*{dist(v, zs[1])}/2"
    if len(vs) == 2:
        d = [dist(next(v for v in vs if v in e), e) for e in zs]
        return f"=({d[0]}+{d[1]})/2*'{S1}'!$B$3"
    return f"={A2}-{other_ref}"


def hcp_formula(f):
    parts = [f"ABS({HREF[lb[1]]})" if lb[0] == "v" else "0" for lb in f["labels"]]
    return f"=({'+'.join(parts)})/{len(parts)}"


# Одна таблица, как на доске: верхняя строка шапки делит её на ПВ и ПН,
# строки - по квадратам 1..15, где части нет - прочерк.
R_GRP, R_HDR = 4, 5
R1 = R_HDR + 1
NSQ = R.NX * R.NY
RS = R1 + NSQ                       # строка итогов
COLS = {-1: "ABCD", 1: "EFGHI"}     # ПВ: № F hср V;  ПН: № F hср V Vгр
for sq in range(1, NSQ + 1):
    for g in R.FIGS:
        if g["sq"] == sq:
            FCELL[g["name"]] = f"${COLS[g['sign']][1]}${R1 + sq - 1}"

w3.merge_cells(f"A{R_GRP}:D{R_GRP}")
w3.merge_cells(f"E{R_GRP}:I{R_GRP}")
cell(w3, f"A{R_GRP}", "Планировочная выемка (ПВ)", F_B, fill=HEAD)
cell(w3, f"E{R_GRP}", "Планировочная насыпь (ПН)", F_B, fill=HEAD)
for c in "BCDFGHI":
    w3[f"{c}{R_GRP}"].border = BOX
hdr = {-1: ["№ фигуры", "Fi, м²", "hср, м", "Vi, м³"],
       1: ["№ фигуры", "Fi, м²", "hср, м", "Vi, м³", "Vгр = Vi / Kор, м³"]}
for sgn in (-1, 1):
    for c, t in zip(COLS[sgn], hdr[sgn]):
        cell(w3, f"{c}{R_HDR}", t, F_B, fill=HEAD)

for sq in range(1, NSQ + 1):
    r = R1 + sq - 1
    for sgn in (-1, 1):
        cn = COLS[sgn]
        part = [g for g in R.FIGS if g["sq"] == sq and g["sign"] == sgn]
        if not part:
            for c in cn:
                cell(w3, f"{c}{r}", "—")
            continue
        f = part[0]
        kind, vs, zs, txt = describe(f)
        sibling = [g for g in R.FIGS if g["sq"] == sq and g is not f]
        other = FCELL[sibling[0]["name"]] if sibling else None
        cell(w3, f"{cn[0]}{r}", f["name"], F_B)
        w3[f"{cn[0]}{r}"].comment = Comment(f"{kind}: {txt}", "расчёт")
        cell(w3, f"{cn[1]}{r}", area_formula(f, vs, zs, other), F_CALC, "0.00")
        cell(w3, f"{cn[2]}{r}", hcp_formula(f), F_CALC, "0.000")
        cell(w3, f"{cn[3]}{r}", f"={cn[1]}{r}*{cn[2]}{r}", F_CALC, "0.00")
        if sgn > 0:
            cell(w3, f"{cn[4]}{r}", f"={cn[3]}{r}/'{S1}'!$B$4", F_CALC, "0.00")

for sgn in (-1, 1):
    cn = COLS[sgn]
    cell(w3, f"{cn[0]}{RS}", "Σ", F_B)
    cell(w3, f"{cn[2]}{RS}", "")
    for c in (cn[1], cn[3]) + ((cn[4],) if sgn > 0 else ()):
        cell(w3, f"{c}{RS}", f"=SUM({c}{R1}:{c}{RS - 1})", F_B, "0.00")
TOT = {-1: ("B", "D"), 1: ("F", "H", "I")}

rb = RS + 3
w3[f"A{rb - 1}"] = "Сопоставление объёмов"
w3[f"A{rb - 1}"].font = F_B
rows = [
    ("Площадь ПВ + ПН, м² (проверка)", f"=B{RS}+F{RS}", "0.00"),
    ("Площадь площадки 5 × 3 × a², м²", f"='{S1}'!$B$6*{A2}", "0.00"),
    ("ΣVпв — объём выемки, м³", f"=D{RS}", "0.00"),
    ("ΣVпн — объём насыпи, м³", f"=H{RS}", "0.00"),
    ("ΣVгр = ΣVпн / Kор — грунта в плотном теле на насыпь, м³", f"=I{RS}", "0.00"),
    ("Разница ΣVгр − ΣVпв, м³ («+» — не хватает грунта)", f"=F{rb + 4}-F{rb + 2}", "0.00"),
    ("Разница в % от ΣVпв", f"=F{rb + 5}/F{rb + 2}", "0.0%"),
]
for k, (t, fml, fmt) in enumerate(rows):
    w3.merge_cells(f"A{rb + k}:E{rb + k}")
    cell(w3, f"A{rb + k}", t, F_CALC, al=LEFT)
    for c in "BCDE":
        w3[f"{c}{rb + k}"].border = BOX
    cell(w3, f"F{rb + k}", fml, F_B, fmt)
note = rb + len(rows) + 1
w3[f"A{note}"] = ("Разницу покрывают в сводном балансе грунта: грунт из котлована, "
                  "завоз из резерва или поправка отметок Δh — следующий этап.")
w3[f"A{note}"].font = Font(name=FONT, size=11, italic=True)
w3.merge_cells(f"A{note}:I{note}")
w3[f"A{note}"].alignment = LEFT
w3.row_dimensions[note].height = 32
for c, wd in zip("ABCDEFGHI", (10, 11, 9, 11, 10, 11, 9, 11, 13)):
    w3.column_dimensions[c].width = wd
w3.row_dimensions[R_HDR].height = 32

# ---------- лист 4: котлован ----------
S4 = "Котлован"
w4 = wb.create_sheet(S4)
w4["A1"] = "Котлован: контуры, размеры, геометрический объём (п. 2.2.2 методички)"
w4["A1"].font = F_T
w4["A2"] = ("Задание 4, вариант 2 — только габариты; грунт — супесь. Здание — вариант размещения 8: "
            "центр здания в центре квадрата 8.")
w4["A2"].font = Font(name=FONT, size=11, italic=True)
for c, t in zip("ABCDE", ("Параметр", "Обозн.", "Значение", "Ед.", "Формула / источник")):
    cell(w4, f"{c}4", t, F_B, fill=HEAD)
KR = {}             # ключ -> адрес значения
_r = [5]


def krow(key, name, sym, val, unit="м", note="", font=None, fmt="0.000", section=False):
    r = _r[0]
    _r[0] += 1
    if section:
        w4.merge_cells(f"A{r}:E{r}")
        cell(w4, f"A{r}", name, F_B, al=LEFT, fill=HEAD)
        for c in "BCDE":
            w4[f"{c}{r}"].border = BOX
        return
    KR[key] = f"$C${r}"
    cell(w4, f"A{r}", name, F_CALC, al=LEFT)
    cell(w4, f"B{r}", sym)
    isin = not (isinstance(val, str) and val.startswith("="))
    cell(w4, f"C{r}", val, font or (F_IN if isin else F_CALC), fmt)
    cell(w4, f"D{r}", unit)
    cell(w4, f"E{r}", note, Font(name=FONT, size=10, italic=True), al=LEFT)


def k(key):
    return KR[key]


H = lambda n: HREF[n]
krow(None, "Исходные данные — Задание 4, вариант 2", None, None, section=True)
krow("NK", "Глубина котлована по заданию (от планировочной отметки)", "Нк", 2.4)
krow("HFP", "Высота фундаментной плиты", "Нф.п", 0.4)
krow("HBP", "Толщина бетонной подготовки", "hб.п", 0.15)
krow("HPODS", "Толщина подсыпки (щебень)", "hподс", 0.1)
krow("BST", "Толщина стены подвала (по оси)", "Bп", 0.4, note="схема размещения фундамента")
krow("VYL", "Вылет плиты за наружную грань стены", "", 0.5, note="схема: 500")
krow("VBP", "Выход бетонной подготовки за плиту", "", 0.2, note="схема: 200; методичка — не менее 0,2")
krow("VRZ", "От края подготовки до низа откоса", "", 0.5, note="схема: 500")
krow("LZ", "Длина здания по осям", "", 60, fmt="0.0")
krow("BZ", "Ширина здания по осям", "", 30, fmt="0.0")
krow("LV", "Вырез (правый нижний угол): длина", "", 42, fmt="0.0")
krow("BV", "Вырез: ширина", "", 12, fmt="0.0")
krow("XQ", "Левый нижний угол квадрата 8: x", "", 200, fmt="0")
krow("YQ", "Левый нижний угол квадрата 8: y", "", 100, fmt="0")
krow("X0", "Левая ось здания (центр в центре квадрата 8)", "X0", f"={k('XQ')}+'{S1}'!$B$3/2-{k('LZ')}/2", fmt="0.0")
krow("Y0", "Нижняя ось здания", "Y0", f"={k('YQ')}+'{S1}'!$B$3/2-{k('BZ')}/2", fmt="0.0")

krow(None, "Привязки от осей здания", None, None, section=True)
krow("DST", "Ось → наружная грань стены", "", f"={k('BST')}/2")
krow("DFP", "Ось → край фундаментной плиты", "A", f"={k('DST')}+{k('VYL')}")
krow("DBP", "Ось → край бетонной подготовки", "", f"={k('DFP')}+{k('VBP')}")
krow("DN", "Ось → низ откоса (подошва котлована)", "", f"={k('DBP')}+{k('VRZ')}")
krow("C", "Рабочая зона от плиты до откоса", "C", f"={k('DN')}-{k('DFP')}", note="не менее 0,6 м")

krow(None, "Положение котлована относительно ЛНР", None, None, section=True)
krow("M0", "Крутизна откоса при Нк (предварительно)", "m0", f"=IF({k('NK')}<=1.5,0.25,IF({k('NK')}<=3,0.67,0.85))",
     "", "прил. 3, супесь: до 1,5 — 0,25; до 3 — 0,67; до 5 — 0,85", fmt="0.00")
krow("D0", "Ось → бровка (предварительно)", "", f"={k('DN')}+{k('NK')}*{k('M0')}")
krow("HMEAN", "Среднее рабочих отметок по углам котлована", "hср.углов", "=AVERAGE(H{0}:H{1})",
     note="таблица углов ниже; «+» — насыпь", fmt="0.0000")
krow("ZONE", "Котлован в зоне", "", f'=IF({k("HMEAN")}>0,"насыпи","выемки")', "", "вариант 2: ЛНР пересекает котлован")
krow("HR", "Рабочая отметка в центре котлована (центр квадрата 8)", "hр",
     f"=({H(9)}+{H(10)}+{H(15)}+{H(16)})/4", note="билинейно; в центре квадрата = среднее h9, h10, h15, h16",
     fmt="0.0000")
krow("HK", "Фактическая глубина от естественной поверхности", "hк",
     f'=IF({k("ZONE")}="насыпи",{k("NK")}-{k("HR")},{k("NK")})', note="hк = Нк − hр (котлован в насыпи)", fmt="0.0000")

krow(None, "Откосы и контуры", None, None, section=True)
krow("M", "Коэффициент откоса (супесь)", "m", f"=IF({k('HK')}<=1.5,0.25,IF({k('HK')}<=3,0.67,0.85))", "",
     "прил. 3", fmt="0.00")
krow("L", "Заложение откоса", "l", f"={k('HK')}*{k('M')}", note="l = hк · m", fmt="0.0000")
cut = f"{k('LV')}*{k('BV')}"


def fl(d):
    return f"=({k('LZ')}+2*{d})*({k('BZ')}+2*{d})-{cut}"


krow("LN", "Низ котлована: длина", "", f"={k('LZ')}+2*{k('DN')}", fmt="0.000")
krow("BN", "Низ котлована: ширина", "", f"={k('BZ')}+2*{k('DN')}", fmt="0.000")
krow("FN", "Площадь по низу", "Fк.н", fl(k("DN")), "м²", "Г-образный контур: L·B − вырез 42 × 12", fmt="0.00")
krow("LVV", "Верх котлована: длина", "", f"={k('LN')}+2*{k('L')}", fmt="0.000")
krow("BVV", "Верх котлована: ширина", "", f"={k('BN')}+2*{k('L')}", fmt="0.000")
krow("FV", "Площадь по верху", "Fк.в", f"={k('LVV')}*{k('BVV')}-{cut}", "м²", fmt="0.00")
krow("FST", "Площадь по наружному контуру стен", "Fк.с.п", fl(k("DST")), "м²", fmt="0.00")
krow("FFP", "Площадь фундаментной плиты", "Fф.п", fl(k("DFP")), "м²", fmt="0.00")
krow("FBP", "Площадь бетонной подготовки", "Fб.п", fl(k("DBP")), "м²", fmt="0.00")

krow(None, "Пандус (принято: однополосный въезд автосамосвалов)", None, None, section=True)
krow("BP", "Ширина пандуса", "bп", 3, note="3 м — один проезд, 6 м — два", fmt="0.0")
krow("IP", "Уклон пандуса", "i", 0.1, "", "0,10–0,15 при вывозе самосвалами", fmt="0.00")
krow("NP", "Коэффициент заложения пандуса", "n", f"=1/{k('IP')}", "", "n = 1 / i", fmt="0.00")
krow("LP", "Длина пандуса в плане", "", f"={k('HK')}*{k('NP')}", fmt="0.000")
krow("VP", "Объём пандуса", "Vпан",
     f"={k('NP')}*({k('BP')}*{k('HK')}^2/2+{k('M')}*{k('HK')}^3/3)", "м³", "n·(bп·hк²/2 + m·hк³/3)", fmt="0.00")

krow(None, "Объёмы", None, None, section=True)
krow("VOSN", "Котлован без пандуса", "",
     f"={k('HK')}/3*({k('FN')}+{k('FV')}+SQRT({k('FN')}*{k('FV')}))", "м³", "hк/3·(Fк.н + Fк.в + √(Fк.н·Fк.в))", fmt="0.00")
krow("VK", "Объём котлована", "Vк", f"={k('VOSN')}+{k('VP')}", "м³", fmt="0.00")
krow("VPODS", "Подсыпка", "Vподс", f"={k('FN')}*{k('HPODS')}", "м³", "Fк.н · hподс", fmt="0.00")
krow("VBPV", "Бетонная подготовка", "Vб.п", f"={k('FBP')}*{k('HBP')}", "м³", "Fб.п · hб.п", fmt="0.00")
krow("VGI", "Гидроизоляция", "Vг.и", 0, "м³", "2 слоя рулонной, толщина в задании не дана", fmt="0.00")
krow("VST", "Защитная стяжка", "Vст", 0, "м³", "в задании нет", fmt="0.00")
krow("VFP", "Фундаментная плита", "Vф.п", f"={k('FFP')}*{k('HFP')}", "м³", "Fф.п · Нф.п", fmt="0.00")
krow("HST", "Высота стен ниже естественной поверхности", "",
     f"={k('HK')}-{k('HFP')}-{k('HBP')}-{k('HPODS')}", note="hк − Нф.п − hб.п − hподс", fmt="0.000")
krow("VKSP", "Стены подвала по наружному контуру", "Vк.с.п", f"={k('FST')}*{k('HST')}", "м³", fmt="0.00")
krow("VPCH", "Подземная часть здания", "Vп.ч", f"={k('VFP')}+{k('VKSP')}", "м³", "Vф.п + Vк.с.п", fmt="0.00")
krow("VOZ", "Обратная засыпка", "Vо.з",
     f"={k('VK')}-{k('VPCH')}-{k('VPODS')}-{k('VBPV')}-{k('VGI')}-{k('VST')}", "м³",
     "Vк − Vп.ч − Vподс − Vб.п − Vг.и − Vст", fmt="0.00")

# углы котлована по бровке (предварительно, при Нк) - рабочие отметки билинейно по квадрату 8
rc = _r[0] + 1
w4[f"A{rc}"] = "Рабочие отметки по углам котлована (бровка при Нк), билинейная интерполяция в квадрате 8"
w4[f"A{rc}"].font = F_B
for c, t in zip("ABCDEFGH", ("Угол", "x отн. осей", "y отн. осей", "X, м", "Y, м", "u", "v", "h, м")):
    cell(w4, f"{c}{rc + 1}", t, F_B, fill=HEAD)
d0 = k("D0")
CORN = [("1", f"-{d0}", f"-{d0}"), ("2", f"{k('LZ')}-{k('LV')}+{d0}", f"-{d0}"),
        ("3", f"{k('LZ')}-{k('LV')}+{d0}", f"{k('BV')}-{d0}"), ("4", f"{k('LZ')}+{d0}", f"{k('BV')}-{d0}"),
        ("5", f"{k('LZ')}+{d0}", f"{k('BZ')}+{d0}"), ("6", f"-{d0}", f"{k('BZ')}+{d0}")]
for n_, (nm, xr, yr) in enumerate(CORN):
    r = rc + 2 + n_
    cell(w4, f"A{r}", nm)
    cell(w4, f"B{r}", "=" + xr, F_CALC, "0.000")
    cell(w4, f"C{r}", "=" + yr, F_CALC, "0.000")
    cell(w4, f"D{r}", f"={k('X0')}+B{r}", F_CALC, "0.000")
    cell(w4, f"E{r}", f"={k('Y0')}+C{r}", F_CALC, "0.000")
    cell(w4, f"F{r}", f"=(D{r}-{k('XQ')})/'{S1}'!$B$3", F_CALC, "0.0000")
    cell(w4, f"G{r}", f"=(E{r}-{k('YQ')})/'{S1}'!$B$3", F_CALC, "0.0000")
    cell(w4, f"H{r}", f"={H(15)}*(1-F{r})*(1-G{r})+{H(16)}*F{r}*(1-G{r})+{H(9)}*(1-F{r})*G{r}+{H(10)}*F{r}*G{r}",
         F_CALC, "0.0000")
hm = w4[k("HMEAN").replace("$", "")]
hm.value = hm.value.format(rc + 2, rc + 7)
w4[f"A{rc + 8}"] = ("Вершины квадрата 8: h15 — левый нижний, h16 — правый нижний, h9 — левый верхний, "
                    "h10 — правый верхний. Отметки разного знака — котлован пересекает ЛНР.")
w4[f"A{rc + 8}"].font = Font(name=FONT, size=10, italic=True)
for c, wd in zip("ABCDEFGH", (52, 10, 12, 8, 44, 9, 9, 10)):
    w4.column_dimensions[c].width = wd
KROW_REF = dict(KR)

# ---------- лист 5: сводный баланс ----------
S5 = "Сводный баланс"
w5 = wb.create_sheet(S5)
w5["A1"] = "Сводная ведомость объёмов разрабатываемого грунта (табл. 2 методички)"
w5["A1"].font = F_T
w5["A2"] = "До корректировки средней отметки планировки"
w5["A2"].font = Font(name=FONT, size=11, italic=True)
for c, t in zip("ABCDE", ("№", "Вид работы", "Выемка Vв, м³", "Насыпь Vн, м³", "Vн / Kор, м³")):
    cell(w5, f"{c}4", t, F_B, fill=HEAD)
K4 = lambda key: f"'{S4}'!{KR[key]}"
KOR = f"'{S1}'!$B$4"
cell(w5, "A5", 1); cell(w5, "B5", "В призмах (планировка)", al=LEFT)
cell(w5, "C5", f"='{S3}'!D{RS}", F_LINK, "0.00")
cell(w5, "D5", f"='{S3}'!H{RS}", F_LINK, "0.00")
cell(w5, "E5", f"=D5/{KOR}", F_CALC, "0.00")
cell(w5, "A6", 2); cell(w5, "B6", "В котловане (Vк; обратная засыпка Vо.з)", al=LEFT)
cell(w5, "C6", f"={K4('VK')}", F_LINK, "0.00")
cell(w5, "D6", f"={K4('VOZ')}", F_LINK, "0.00")
cell(w5, "E6", f"=D6/{KOR}", F_CALC, "0.00")
cell(w5, "A7", ""); cell(w5, "B7", "Суммарные объёмы", F_B, al=LEFT)
for c in "CDE":
    cell(w5, f"{c}7", f"=SUM({c}5:{c}6)", F_B, "0.00")
cell(w5, "A8", ""); cell(w5, "B8", "Баланс Vв − Vн/Kор («−» — грунта не хватает)", F_B, al=LEFT)
w5.merge_cells("C8:E8")
cell(w5, "C8", "=C7-E7", F_B, "0.00")
for c in "DE":
    w5[f"{c}8"].border = BOX
rows5 = [
    ("Расхождение, % (допускается не более 5 %)", "=ABS(C8)/MAX(C7,E7)", "0.00%"),
    ("Вывод", '=IF(D10<=0.05,"баланс соблюдён",IF(C8<0,"не хватает грунта — нужен перерасчёт Нср (Δh)",'
              '"излишек грунта — нужен перерасчёт Нср (Δh)"))', None),
    ("Площадь площадки Fпл без котлована по верху (котлован в насыпи), м²",
     f"='{S1}'!$B$6*'{S1}'!$B$3^2-IF({K4('ZONE')}=\"насыпи\",{K4('FV')},0)", "0.00"),
    ("Поправка Δh = (Vв − Vн/Kор) / Fпл, м («−» — понижение)", "=C8/D12", "0.0000"),
]
for n_, (t, fml, fmt) in enumerate(rows5):
    r = 10 + n_
    w5.merge_cells(f"A{r}:C{r}")
    cell(w5, f"A{r}", t, al=LEFT)
    for c in "BC":
        w5[f"{c}{r}"].border = BOX
    cell(w5, f"D{r}", fml, F_B, fmt)
w5[f"A{15}"] = ("Δh — к следующему этапу: все рабочие отметки сдвигаются на Δh, заново строится ЛНР "
                "и пересчитываются объёмы и котлован.")
w5["A15"].font = Font(name=FONT, size=10, italic=True)
for c, wd in zip("ABCDE", (5, 52, 16, 16, 16)):
    w5.column_dimensions[c].width = wd

for sh in wb.worksheets:
    sh.sheet_view.zoomScale = 110
    sh.page_setup.paperSize = sh.PAPERSIZE_A4
    sh.page_setup.orientation = "landscape"
    sh.sheet_properties.pageSetUpPr.fitToPage = True
    sh.page_setup.fitToWidth = 1
    sh.page_setup.fitToHeight = 1          # каждый лист печатается на одну страницу

out = "Объёмы_планировки_вариант2.xlsx"
wb.save(out)
print(out, "итоги в строке", RS, "сравнение с", rb)
