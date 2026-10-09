"""Книга Excel: отметки, точки нулевых работ, объёмы ПВ/ПН, котлован, сводный баланс -
по черновику и по окончательным отметкам (после поправки Δh). Всё на формулах."""
import subprocess
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.comments import Comment
import raschet as R
import kotlovan as KT
import balans as B

FONT = "GOST type B"            # ГОСТ 2.304, тип Б (файл GOST_B.TTF)
thin = Side(style="thin")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
F_IN = Font(name=FONT, size=12, color="0000FF")          # исходные данные
F_LINK = Font(name=FONT, size=12, color="008000")        # ссылка на другой лист
F_CALC = Font(name=FONT, size=12)
F_B = Font(name=FONT, size=12, bold=True)
F_T = Font(name=FONT, size=14, bold=True)
F_NOTE = Font(name=FONT, size=11, italic=True)
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


A1 = f"'{S1}'!$B$3"             # сторона квадрата
A2 = f"{A1}^2"
KOR = f"'{S1}'!$B$4"

# ---------- лист 1: исходные данные ----------
ws["A1"] = "Курсовая работа «Технологическая карта на производство земляных работ». Вариант 2"
ws["A1"].font = F_T
cell(ws, "A3", "Сторона квадрата сетки a, м", F_CALC, al=LEFT)
cell(ws, "B3", R.A, F_IN)
cell(ws, "A4", "Коэффициент остаточного разрыхления Kор", F_CALC, al=LEFT)
cell(ws, "B4", float(B.K_OR), F_IN, "0.00", fill=YEL)
ws["B4"].comment = Comment(
    "Супесь: kо.р = 1,03…1,05 (прил. 2 методички). "
    "Принято 1,04 — по указанию преподавателя брать в этом диапазоне.", "расчёт")
cell(ws, "A5", "Грунт", F_CALC, al=LEFT)
cell(ws, "B5", "супесь", F_IN)
cell(ws, "A6", "Число квадратов", F_CALC, al=LEFT)
cell(ws, "B6", R.NX * R.NY, F_IN)
cell(ws, "A7", "Коэффициент первоначального разрыхления kр", F_CALC, al=LEFT)
cell(ws, "B7", 1.15, F_IN, "0.00", fill=YEL)
ws["B7"].comment = Comment("Супесь: kр = 1,12…1,17 (прил. 2 методички). Принято 1,15 — решение пользователя.",
                           "расчёт")
ws["D3"] = "Редактировать можно только синие ячейки (жёлтая — принятое допущение)."
ws["D4"] = "Рабочая отметка h = Hкр − Hчёрн: «−» — выемка (ПВ), «+» — насыпь (ПН)."
ws["D5"] = "Отметки — вариант 2. Вершины нумеруются построчно слева направо, сверху вниз."
for r in ("D3", "D4", "D5"):
    ws[r].font = F_NOTE

cell(ws, "A8", "№ вершины", F_B, fill=HEAD)
cell(ws, "B8", "h, м", F_B, fill=HEAD)
HREF0 = {}
for k, v in enumerate(R.H, start=1):
    r = 8 + k
    cell(ws, f"A{r}", f"h{k}")
    cell(ws, f"B{r}", float(v), F_IN, "0.00")
    HREF0[k] = f"'{S1}'!$B${r}"
COLS6 = "DEFGHI"


def grid(sh, top, col_val, fmt):
    """Схема сетки: подпись вершины и значение из столбца col_val этого листа."""
    sh[f"D{top}"] = "Схема сетки (вид в плане, квадрат 100×100 м)"
    sh[f"D{top}"].font = F_B
    for j in range(R.NY + 1):
        for i in range(R.NX + 1):
            n = R.vnum(i, j)
            cell(sh, f"{COLS6[i]}{top + 1 + 2 * j}", f"h{n}", Font(name=FONT, size=9, color="808080"))
            cell(sh, f"{COLS6[i]}{top + 2 + 2 * j}", f"={col_val}{8 + n}", F_CALC, fmt)
    for c in COLS6:
        sh.column_dimensions[c].width = 9


grid(ws, 8, "B", "0.00")
ws.column_dimensions["A"].width = 44
ws.column_dimensions["B"].width = 10


# ---------- ЛНР ----------
def sheet_lnr(name, P, HREF, title):
    w2 = wb.create_sheet(name)
    w2["A1"] = title
    w2["A1"].font = F_T
    w2["A2"] = "x1 = a·|h1| / (|h1| + |h2|) — расстояние от вершины 1 до точки нуля;  x2 = a − x1"
    w2["A2"].font = Font(name=FONT, size=12, italic=True)
    hdr = ["№ т.0", "Сторона", "Вершина 1", "h1, м", "Вершина 2", "h2, м",
           "x1 (от верш. 1), м", "x2 (от верш. 2), м"]
    for k, t in enumerate(hdr):
        cell(w2, f"{'ABCDEFGH'[k]}4", t, F_B, fill=HEAD)
    zrow = {}
    for k, z in enumerate(sorted(P["ZP"], key=lambda z: (z["p1"], z["p2"])), start=1):
        r = 4 + k
        zrow[(z["p1"], z["p2"])] = r
        horiz = z["p2"] == z["p1"] + 1
        cell(w2, f"A{r}", k)
        cell(w2, f"B{r}", "горизонтальная" if horiz else "вертикальная")
        cell(w2, f"C{r}", f"h{z['p1']}")
        cell(w2, f"D{r}", f"={HREF[z['p1']]}", F_LINK, "0.0000")
        cell(w2, f"E{r}", f"h{z['p2']}")
        cell(w2, f"F{r}", f"={HREF[z['p2']]}", F_LINK, "0.0000")
        cell(w2, f"G{r}", f"={A1}*ABS(D{r})/(ABS(D{r})+ABS(F{r}))", F_CALC, "0.00")
        cell(w2, f"H{r}", f"={A1}-G{r}", F_CALC, "0.00")
    for c, wd in zip("ABCDEFGH", (7, 16, 11, 10, 11, 10, 18, 18)):
        w2.column_dimensions[c].width = wd
    return zrow


# ---------- объёмы планировки ----------
def sheet_volumes(name, P, HREF, zrow, s_lnr, title):
    w3 = wb.create_sheet(name)
    w3["A1"] = title
    w3["A1"].font = F_T
    w3["A2"] = "Vi = Fi · hср,i;   hср,i = (|h1| + |h2| + … + |hn|) / n, в точках нуля h = 0"
    w3["A2"].font = Font(name=FONT, size=12, italic=True)

    def dist(v, e):
        """Ссылка на расстояние от вершины v до точки нуля на стороне e."""
        r = zrow[e]
        return f"'{s_lnr}'!$G${r}" if v == e[0] else f"'{s_lnr}'!$H${r}"

    def describe(f):
        vs = [lb[1] for lb in f["labels"] if lb[0] == "v"]
        zs = [lb[1] for lb in f["labels"] if lb[0] == "z"]
        kind = {4: "квадрат", 1: "треугольник", 2: "трапеция", 3: "пятиугольник"}[len(vs)]
        txt = ", ".join(f"h{v}" for v in vs)
        if zs:
            txt += "; т.0 на " + ", ".join(f"h{a}–h{b}" for a, b in zs)
        return kind, vs, zs, txt

    def area_formula(vs, zs, other_ref):
        if len(vs) == 4:
            return f"={A2}"
        if len(vs) == 1:
            v = vs[0]
            return f"={dist(v, zs[0])}*{dist(v, zs[1])}/2"
        if len(vs) == 2:
            d = [dist(next(v for v in vs if v in e), e) for e in zs]
            return f"=({d[0]}+{d[1]})/2*{A1}"
        return f"={A2}-{other_ref}"

    def hcp_formula(f):
        parts = [f"ABS({HREF[lb[1]]})" if lb[0] == "v" else "0" for lb in f["labels"]]
        return f"=({'+'.join(parts)})/{len(parts)}"

    # Одна таблица, как на доске: верхняя строка шапки делит её на ПВ и ПН,
    # строки - по квадратам 1..15, где части нет - прочерк.
    R_GRP, R_HDR = 4, 5
    R1 = R_HDR + 1
    NSQ = R.NX * R.NY
    RS = R1 + NSQ                       # строка итогов по фигурам
    COLS = {-1: "ABCD", 1: "EFGHI"}     # ПВ: № F hср V;  ПН: № F hср V Vгр
    FIGS = P["FIGS"]
    fcell = {}
    for g in FIGS:
        fcell[g["name"]] = f"${COLS[g['sign']][1]}${R1 + g['sq'] - 1}"

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
            part = [g for g in FIGS if g["sq"] == sq and g["sign"] == sgn]
            if not part:
                for c in cn:
                    cell(w3, f"{c}{r}", "—")
                continue
            f = part[0]
            kind, vs, zs, txt = describe(f)
            sibling = [g for g in FIGS if g["sq"] == sq and g is not f]
            other = fcell[sibling[0]["name"]] if sibling else None
            cell(w3, f"{cn[0]}{r}", f["name"], F_B)
            w3[f"{cn[0]}{r}"].comment = Comment(f"{kind}: {txt}", "расчёт")
            cell(w3, f"{cn[1]}{r}", area_formula(vs, zs, other), F_CALC, "0.00")
            cell(w3, f"{cn[2]}{r}", hcp_formula(f), F_CALC, "0.0000")
            cell(w3, f"{cn[3]}{r}", f"={cn[1]}{r}*{cn[2]}{r}", F_CALC, "0.00")
            if sgn > 0:
                cell(w3, f"{cn[4]}{r}", f"={cn[3]}{r}/{KOR}", F_CALC, "0.00")

    for sgn in (-1, 1):
        cn = COLS[sgn]
        cell(w3, f"{cn[0]}{RS}", "Σ", F_B)
        cell(w3, f"{cn[2]}{RS}", "")
        for c in (cn[1], cn[3]) + ((cn[4],) if sgn > 0 else ()):
            cell(w3, f"{c}{RS}", f"=SUM({c}{R1}:{c}{RS - 1})", F_B, "0.00")

    # откосы по контуру площадки (с. 10)
    ro = RS + 2
    w3[f"A{ro}"] = "Откосы по контуру площадки: ΣV = (Σh / n)² · Σl · m / 2  (с. 10 методички)"
    w3[f"A{ro}"].font = F_B
    for c, t in zip("ABCDEF", ("Зона", "Σh, м", "n", "Σl, м", "m", "V, м³")):
        cell(w3, f"{c}{ro + 1}", t, F_B, fill=HEAD)
    per = [(p, R.vnum(*p)) for p, _ in R.perimeter()]
    sl_ref = {}
    for k_, (sgn, zone) in enumerate(((-1, "выемка"), (1, "насыпь"))):
        r = ro + 2 + k_
        verts = [v for (p, v) in per if P["H"][v - 1] * sgn > 0]
        parts = []
        for k in range(len(per)):
            (p1, v1), (p2, v2) = per[k], per[(k + 1) % len(per)]
            h1, h2 = P["H"][v1 - 1], P["H"][v2 - 1]
            if h1 * sgn >= 0 and h2 * sgn >= 0:
                parts.append(A1)
            elif h1 * sgn > 0 or h2 * sgn > 0:
                e = (min(v1, v2), max(v1, v2))
                parts.append(dist(v1 if h1 * sgn > 0 else v2, e))
        cell(w3, f"A{r}", zone)
        w3[f"A{r}"].comment = Comment("вершины на контуре: " + ", ".join(f"h{v}" for v in verts), "расчёт")
        cell(w3, f"B{r}", "=" + "+".join(f"ABS({HREF[v]})" for v in verts), F_CALC, "0.0000")
        cell(w3, f"C{r}", len(verts))
        cell(w3, f"D{r}", "=" + "+".join(parts), F_CALC, "0.00")
        cell(w3, f"E{r}", float(R.M_OTK), F_IN, "0.00")
        w3[f"E{r}"].comment = Comment("супесь, глубина до 1,5 м — 1:0,25 (прил. 3)", "расчёт")
        cell(w3, f"F{r}", f"=(B{r}/C{r})^2*D{r}*E{r}/2", F_CALC, "0.00")
        sl_ref[sgn] = f"F{r}"

    rt = ro + 5
    w3[f"A{rt}"] = "Итого с откосами (ΣVв.геом, ΣVн.геом в табл. 2)"
    w3[f"A{rt}"].font = F_B
    rows = [
        ("Площадь ПВ + ПН, м² (проверка)", f"=B{RS}+F{RS}", "0.00"),
        ("Площадь площадки 5 × 3 × a², м²", f"='{S1}'!$B$6*{A2}", "0.00"),
        ("ΣVв.геом — выемка: фигуры + откосы, м³", f"=D{RS}+{sl_ref[-1]}", "0.00"),
        ("ΣVн.геом — насыпь: фигуры + откосы, м³", f"=H{RS}+{sl_ref[1]}", "0.00"),
        ("ΣVн.геом / Kор — грунта в плотном теле на насыпь, м³", f"=F{rt + 4}/{KOR}", "0.00"),
    ]
    for k, (t, fml, fmt) in enumerate(rows):
        r = rt + 1 + k
        w3.merge_cells(f"A{r}:E{r}")
        cell(w3, f"A{r}", t, F_CALC, al=LEFT)
        for c in "BCDE":
            w3[f"{c}{r}"].border = BOX
        cell(w3, f"F{r}", fml, F_B, fmt)
    for c, wd in zip("ABCDEFGHI", (10, 11, 9, 11, 10, 11, 9, 11, 13)):
        w3.column_dimensions[c].width = wd
    w3.row_dimensions[R_HDR].height = 32
    return {"VV": f"'{name}'!$F${rt + 3}", "VN": f"'{name}'!$F${rt + 4}"}


# ---------- котлован ----------
def sheet_pit(name, HREF, title):
    w4 = wb.create_sheet(name)
    w4["A1"] = title
    w4["A1"].font = F_T
    w4["A2"] = ("Задание 4, вариант 2 — только габариты; грунт — супесь. Здание — вариант размещения 8: "
                "центр здания в центре квадрата 8.")
    w4["A2"].font = F_NOTE
    for c, t in zip("ABCDE", ("Параметр", "Обозн.", "Значение", "Ед.", "Формула / источник")):
        cell(w4, f"{c}4", t, F_B, fill=HEAD)
    KR = {}             # ключ -> адрес значения
    _r = [5]

    def krow(key, nm, sym, val, unit="м", note="", fmt="0.000", section=False):
        r = _r[0]
        _r[0] += 1
        if section:
            w4.merge_cells(f"A{r}:E{r}")
            cell(w4, f"A{r}", nm, F_B, al=LEFT, fill=HEAD)
            for c in "BCDE":
                w4[f"{c}{r}"].border = BOX
            return
        KR[key] = f"$C${r}"
        cell(w4, f"A{r}", nm, F_CALC, al=LEFT)
        cell(w4, f"B{r}", sym)
        isin = not (isinstance(val, str) and val.startswith("="))
        cell(w4, f"C{r}", val, F_IN if isin else F_CALC, fmt)
        cell(w4, f"D{r}", unit)
        cell(w4, f"E{r}", note, Font(name=FONT, size=10, italic=True), al=LEFT)

    k = lambda key: KR[key]
    H = lambda n: HREF[n]
    krow(None, "Исходные данные — Задание 4, вариант 2", None, None, section=True)
    krow("NK", "Глубина котлована по заданию (от планировочной отметки)", "Нк", 2.4)
    krow("HFP", "Высота фундаментной плиты", "Нф.п", 0.4)
    krow("HBP", "Толщина бетонной подготовки", "hб.п", 0.15)
    krow("HPODS", "Толщина подсыпки (щебень)", "hподс", 0.1)
    krow("HRSL", "Толщина растительного слоя", "hр.сл", float(KT.H_RSL), note="методичка, с. 11: 200 мм")
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
    krow("X0", "Левая ось здания (центр в центре квадрата 8)", "X0", f"={k('XQ')}+{A1}/2-{k('LZ')}/2", fmt="0.0")
    krow("Y0", "Нижняя ось здания", "Y0", f"={k('YQ')}+{A1}/2-{k('BZ')}/2", fmt="0.0")

    krow(None, "Привязки от осей здания", None, None, section=True)
    krow("DST", "Ось → наружная грань стены", "", f"={k('BST')}/2")
    krow("DFP", "Ось → край фундаментной плиты", "A", f"={k('DST')}+{k('VYL')}")
    krow("DBP", "Ось → край бетонной подготовки", "", f"={k('DFP')}+{k('VBP')}")
    krow("DN", "Ось → низ откоса (подошва котлована)", "", f"={k('DBP')}+{k('VRZ')}")
    krow("C", "Рабочая зона от плиты до откоса", "C", f"={k('DN')}-{k('DFP')}", note="не менее 0,6 м")
    krow("RKR", "Радиус поворотной платформы крана", "r", float(KT.R_KRAN), note="лекция", fmt="0.0")
    krow("CP", "Со стороны съезда: от плиты до низа откоса", "c", f"=1+2*{k('RKR')}+1",
         note="лекция: c = 1 + 2r + 1 - место для крана на дне", fmt="0.0")
    krow("DE", "Ось → низ откоса со стороны съезда (правая)", "", f"={k('DFP')}+{k('CP')}")

    krow(None, "Положение котлована относительно ЛНР", None, None, section=True)
    krow("M0", "Крутизна откоса при Нк (предварительно)", "m0", f"=IF({k('NK')}<=1.5,0.25,IF({k('NK')}<=3,0.67,0.85))",
         "", "прил. 3, супесь: до 1,5 — 0,25; до 3 — 0,67; до 5 — 0,85", fmt="0.00")
    krow("D0", "Ось → бровка (предварительно)", "", f"={k('DN')}+{k('NK')}*{k('M0')}")
    krow("D0E", "Ось → бровка со стороны съезда (предварительно)", "", f"={k('DE')}+{k('NK')}*{k('M0')}")
    krow("HMEAN", "Среднее рабочих отметок по углам котлована", "hср.углов", "=AVERAGE(H{0}:H{1})",
         note="таблица углов ниже; «+» — насыпь", fmt="0.0000")
    krow("ZONE", "Котлован в зоне", "", f'=IF({k("HMEAN")}>0,"насыпи","выемки")', "", "ЛНР пересекает котлован — по среднему")
    krow("HR", "Рабочая отметка в центре котлована (центр квадрата 8)", "hр",
         f"=({H(9)}+{H(10)}+{H(15)}+{H(16)})/4", note="билинейно; в центре квадрата = среднее h9, h10, h15, h16",
         fmt="0.0000")
    krow("HK", "Фактическая глубина котлована", "hк",
         f'=IF({k("ZONE")}="насыпи",{k("NK")}-{k("HRSL")}-{k("HR")},{k("NK")}-{k("HRSL")})',
         note="hк = Нк − hр.сл − hр (с. 11; hр — только в насыпи)", fmt="0.0000")

    krow(None, "Откосы и контуры", None, None, section=True)
    krow("M", "Коэффициент откоса (супесь)", "m", f"=IF({k('HK')}<=1.5,0.25,IF({k('HK')}<=3,0.67,0.85))", "",
         "прил. 3", fmt="0.00")
    krow("L", "Заложение откоса", "l", f"={k('HK')}*{k('M')}", note="l = hк · m", fmt="0.0000")
    cut = f"{k('LV')}*{k('BV')}"
    fl = lambda d: f"=({k('LZ')}+2*{d})*({k('BZ')}+2*{d})-{cut}"
    # Г-образный контур: габарит L·B без выреза; вырез по x шире на (de − d) - правая сторона у съезда дальше
    krow("LN", "Низ котлована: длина", "", f"={k('LZ')}+{k('DN')}+{k('DE')}", fmt="0.000")
    krow("BN", "Низ котлована: ширина", "", f"={k('BZ')}+2*{k('DN')}", fmt="0.000")
    krow("FN", "Площадь по низу", "Fк.н",
         f"={k('LN')}*{k('BN')}-({k('LV')}-{k('DN')}+{k('DE')})*{k('BV')}", "м²",
         "L·B − вырез (42 − d + dс) × 12", fmt="0.00")
    krow("LVV", "Верх котлована: длина", "", f"={k('LN')}+2*{k('L')}", fmt="0.000")
    krow("BVV", "Верх котлована: ширина", "", f"={k('BN')}+2*{k('L')}", fmt="0.000")
    krow("FV", "Площадь по верху", "Fк.в",
         f"={k('LVV')}*{k('BVV')}-({k('LV')}-{k('DN')}+{k('DE')})*{k('BV')}", "м²", fmt="0.00")
    krow("FST", "Площадь по наружному контуру стен", "Fк.с.п", fl(k("DST")), "м²", fmt="0.00")
    krow("FFP", "Площадь фундаментной плиты", "Fф.п", fl(k("DFP")), "м²", fmt="0.00")
    krow("FBP", "Площадь бетонной подготовки", "Fб.п", fl(k("DBP")), "м²", fmt="0.00")

    krow(None, "Съезд (пандус): один, двусторонний проезд", None, None, section=True)
    krow("BP", "Ширина съезда", "bп", float(KT.B_PAN), note="методичка: 6 м — двусторонний; лекция: один съезд — 6 м",
         fmt="0.0")
    krow("IP", "Уклон съезда", "i", float(KT.I_PAN), "", "методичка 0,10–0,15; лекция m' = 8…15", fmt="0.00")
    krow("NP", "Коэффициент заложения съезда", "m'", f"=1/{k('IP')}", "", "m' = 1 / i", fmt="0.00")
    krow("LP", "Длина съезда в плане (от низа откоса)", "", f"={k('HK')}*{k('NP')}", fmt="0.000")
    krow("VP", "Объём съезда сверх откоса котлована", "Vс",
         f"={k('HK')}^2/6*(3*{k('BP')}+2*{k('M')}*{k('HK')}*({k('NP')}-{k('M')})/{k('NP')})*({k('NP')}-{k('M')})",
         "м³", "лекция: hк²/6·(3bп + 2m·hк·(m' − m)/m')·(m' − m)", fmt="0.00")

    krow(None, "Объёмы", None, None, section=True)
    krow("VOSN", "Котлован без пандуса", "",
         f"={k('HK')}/3*({k('FN')}+{k('FV')}+SQRT({k('FN')}*{k('FV')}))", "м³", "hк/3·(Fк.н + Fк.в + √(Fк.н·Fк.в))",
         fmt="0.00")
    krow("VK", "Объём котлована со съездом", "Vк", f"={k('VOSN')}+{k('VP')}", "м³", fmt="0.00")
    krow("VPODS", "Подсыпка", "Vподс", f"={k('FN')}*{k('HPODS')}", "м³", "Fк.н · hподс", fmt="0.00")
    krow("VBPV", "Бетонная подготовка", "Vб.п", f"={k('FBP')}*{k('HBP')}", "м³", "Fб.п · hб.п", fmt="0.00")
    krow("VGI", "Гидроизоляция", "Vг.и", 0, "м³", "2 слоя рулонной, толщина в задании не дана", fmt="0.00")
    krow("VST", "Защитная стяжка", "Vст", 0, "м³", "в задании нет", fmt="0.00")
    krow("VFP", "Фундаментная плита", "Vф.п", f"={k('FFP')}*{k('HFP')}", "м³", "Fф.п · Нф.п", fmt="0.00")
    krow("HST", "Высота стен ниже естественной поверхности", "",
         f"={k('HK')}-{k('HFP')}-{k('HBP')}-{k('HPODS')}", note="Нп − |hгр| − hр.сл − hр = hк − Нф.п − hб.п − hподс",
         fmt="0.000")
    krow("VKSP", "Стены подвала по наружному контуру", "Vк.с.п", f"={k('FST')}*{k('HST')}", "м³", fmt="0.00")
    krow("VPCH", "Подземная часть здания", "Vп.ч", f"={k('VFP')}+{k('VKSP')}", "м³", "Vф.п + Vк.с.п", fmt="0.00")
    krow("VPAZ", "Засыпка пазух — привозной песок", "Vп.с",
         f"={k('VOSN')}-{k('VPCH')}-{k('VPODS')}-{k('VBPV')}-{k('VGI')}-{k('VST')}", "м³",
         "котлован без съезда − Vп.ч − Vподс − Vб.п − Vг.и − Vст", fmt="0.00")
    krow("VS", "Засыпка съезда — местный грунт", "Vс", f"={k('VP')}", "м³", fmt="0.00")
    krow("VOZ", "Обратная засыпка всего", "Vо.з", f"={k('VPAZ')}+{k('VS')}", "м³",
         "Vк − Vп.ч − Vподс − Vб.п − Vг.и − Vст (с. 14)", fmt="0.00")

    # углы котлована по бровке (предварительно, при Нк) - рабочие отметки билинейно по квадрату 8
    rc = _r[0] + 1
    w4[f"A{rc}"] = "Рабочие отметки по углам котлована (бровка при Нк), билинейная интерполяция в квадрате 8"
    w4[f"A{rc}"].font = F_B
    for c, t in zip("ABCDEFGH", ("Угол", "x отн. осей", "y отн. осей", "X, м", "Y, м", "u", "v", "h, м")):
        cell(w4, f"{c}{rc + 1}", t, F_B, fill=HEAD)
    d0 = k("D0")
    d0e = k("D0E")
    corn = [("1", f"-{d0}", f"-{d0}"), ("2", f"{k('LZ')}-{k('LV')}+{d0}", f"-{d0}"),
            ("3", f"{k('LZ')}-{k('LV')}+{d0}", f"{k('BV')}-{d0}"), ("4", f"{k('LZ')}+{d0e}", f"{k('BV')}-{d0}"),
            ("5", f"{k('LZ')}+{d0e}", f"{k('BZ')}+{d0}"), ("6", f"-{d0}", f"{k('BZ')}+{d0}")]
    for n_, (nm, xr, yr) in enumerate(corn):
        r = rc + 2 + n_
        cell(w4, f"A{r}", nm)
        cell(w4, f"B{r}", "=" + xr, F_CALC, "0.000")
        cell(w4, f"C{r}", "=" + yr, F_CALC, "0.000")
        cell(w4, f"D{r}", f"={k('X0')}+B{r}", F_CALC, "0.000")
        cell(w4, f"E{r}", f"={k('Y0')}+C{r}", F_CALC, "0.000")
        cell(w4, f"F{r}", f"=(D{r}-{k('XQ')})/{A1}", F_CALC, "0.0000")
        cell(w4, f"G{r}", f"=(E{r}-{k('YQ')})/{A1}", F_CALC, "0.0000")
        cell(w4, f"H{r}", f"={H(15)}*(1-F{r})*(1-G{r})+{H(16)}*F{r}*(1-G{r})+{H(9)}*(1-F{r})*G{r}+{H(10)}*F{r}*G{r}",
             F_CALC, "0.0000")
    hm = w4[k("HMEAN").replace("$", "")]
    hm.value = hm.value.format(rc + 2, rc + 7)
    w4[f"A{rc + 8}"] = ("Вершины квадрата 8: h15 — левый нижний, h16 — правый нижний, h9 — левый верхний, "
                        "h10 — правый верхний.")
    w4[f"A{rc + 8}"].font = Font(name=FONT, size=10, italic=True)
    for c, wd in zip("ABCDEFGH", (52, 10, 12, 8, 44, 9, 9, 10)):
        w4.column_dimensions[c].width = wd
    return {key: f"'{name}'!{ref}" for key, ref in KR.items()}


# ---------- сводный баланс (табл. 2) ----------
def sheet_balance(name, tot, KR, title, sub):
    w5 = wb.create_sheet(name)
    w5["A1"] = title
    w5["A1"].font = F_T
    w5["A2"] = sub
    w5["A2"].font = F_NOTE
    for c, t in zip("ABCDE", ("№", "Вид работы", "Выемка Vв, м³", "Насыпь Vн, м³", "Vн / Kор, м³")):
        cell(w5, f"{c}4", t, F_B, fill=HEAD)
    cell(w5, "A5", 1); cell(w5, "B5", "В призмах (планировка с откосами)", al=LEFT)
    cell(w5, "C5", f"={tot['VV']}", F_LINK, "0.00")
    cell(w5, "D5", f"={tot['VN']}", F_LINK, "0.00")
    cell(w5, "E5", f"=D5/{KOR}", F_CALC, "0.00")
    cell(w5, "A6", 2); cell(w5, "B6", "В котловане (Vк; засыпка съезда Vс — пазухи засыпаются привозным песком)",
                            al=LEFT)
    cell(w5, "C6", f"={KR['VK']}", F_LINK, "0.00")
    cell(w5, "D6", f"={KR['VS']}", F_LINK, "0.00")
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
         f"='{S1}'!$B$6*{A2}-IF({KR['ZONE']}=\"насыпи\",{KR['FV']},0)", "0.00"),
        ("Поправка Δh = (Vв − Vн/Kор) / Fпл, м («−» — понижение)", "=C8/D12", "0.000000"),
        ("Δh, принятое (до 0,0001 м)", "=ROUND(D13,4)", "0.0000"),
    ]
    for n_, (t, fml, fmt) in enumerate(rows5):
        r = 10 + n_
        w5.merge_cells(f"A{r}:C{r}")
        cell(w5, f"A{r}", t, al=LEFT)
        for c in "BC":
            w5[f"{c}{r}"].border = BOX
        cell(w5, f"D{r}", fml, F_B, fmt)
    for c, wd in zip("ABCDE", (5, 52, 16, 16, 16)):
        w5.column_dimensions[c].width = wd
    return f"'{name}'!$D$14"


# ---------- черновик ----------
Z0 = sheet_lnr("ЛНР (черн.)", R.P0, HREF0, "Точки нулевых работ на сторонах квадратов (черновик)")
T0 = sheet_volumes("Табл. 1 объёмы (черн.)", R.P0, HREF0, Z0, "ЛНР (черн.)", "Объёмы планировочных работ (метод квадратов), черновик")
KR0 = sheet_pit("Котлован (черн.)", HREF0, "Котлован по черновику: контуры, размеры, объём (п. 2.2.2 методички)")
DH = sheet_balance("Табл. 2 баланс (черн.)", T0, KR0, "Сводная ведомость объёмов разрабатываемого грунта (табл. 2)",
                   "По черновику — до корректировки средней отметки планировки")

# ---------- окончательные отметки: h' = h + Δh ----------
S1b = "Отметки (оконч.)"
w6 = wb.create_sheet(S1b)
w6["A1"] = "Окончательные рабочие отметки: h' = h + Δh (п. 2.2.3 методички)"
w6["A1"].font = F_T
cell(w6, "A3", "Поправка Δh, м", F_CALC, al=LEFT)
cell(w6, "B3", f"={DH}", F_LINK, "0.0000")
for c, t in zip("ABCD", ("№ вершины", "h, м", "Δh, м", "h' = h + Δh, м")):
    cell(w6, f"{c}8", t, F_B, fill=HEAD)
HREF1 = {}
for k in range(1, len(R.H) + 1):
    r = 8 + k
    cell(w6, f"A{r}", f"h{k}")
    cell(w6, f"B{r}", f"={HREF0[k]}", F_LINK, "0.00")
    cell(w6, f"C{r}", "=$B$3", F_CALC, "0.0000")
    cell(w6, f"D{r}", f"=B{r}+C{r}", F_CALC, "0.0000")
    HREF1[k] = f"'{S1b}'!$D${r}"
w6.column_dimensions["A"].width = 16
for c in "BCD":
    w6.column_dimensions[c].width = 14
COLS_B = "FGHIJK"
w6["F8"] = "Схема сетки (вид в плане)"
w6["F8"].font = F_B
for j in range(R.NY + 1):
    for i in range(R.NX + 1):
        n = R.vnum(i, j)
        cell(w6, f"{COLS_B[i]}{9 + 2 * j}", f"h{n}", Font(name=FONT, size=9, color="808080"))
        cell(w6, f"{COLS_B[i]}{10 + 2 * j}", f"=D{8 + n}", F_CALC, "0.0000")
for c in COLS_B:
    w6.column_dimensions[c].width = 9

Z1 = sheet_lnr("ЛНР (оконч.)", B.P1, HREF1, "Точки нулевых работ по окончательным отметкам")
T1 = sheet_volumes("Табл. 1 объёмы (оконч.)", B.P1, HREF1, Z1, "ЛНР (оконч.)",
                   "Объёмы планировочных работ по окончательным отметкам")
KR1 = sheet_pit("Котлован (оконч.)", HREF1, "Котлован по окончательным отметкам (котлован в насыпи — пересчёт)")
sheet_balance("Табл. 2 баланс (оконч.)", T1, KR1, "Сводная ведомость объёмов разрабатываемого грунта (табл. 2)",
              "По окончательным отметкам — после поправки Δh")

# ---------- табл. 3: баланс земляных работ по котловану (п. 2.2.4; форма - с доски) ----------
import raspredelenie as RS
KP = f"'{S1}'!$B$7"
w7 = wb.create_sheet("Табл. 3 котлован")
w7["A1"] = "Баланс земляных работ по котловану (табл. 3; форма - с доски), по окончательным отметкам"
w7["A1"].font = F_T
w7["A2"] = ("Пазухи засыпаются привозным песком (грунт площадки - супесь, не песок). В отвал у котлована - только "
            "грунт для засыпки съезда; остальной грунт котлована - в транспортные средства: в насыпь планировки, "
            "излишек - на вывоз (с. 16).")
w7["A2"].font = F_NOTE
for rng, t in (("A4:E4", "Выемка"), ("G4:J4", "Насыпь")):
    w7.merge_cells(rng)
    cell(w7, rng[:2], t, F_B, fill=HEAD)
for c in "BCDE":
    w7[f"{c}4"].border = BOX
for c in "HIJ":
    w7[f"{c}4"].border = BOX
w7.merge_cells("D5:E5")
for c, t in zip("ABCD", ("№ п/п", "Место разработки грунта", "Объём разработки грунта, м³ (плотное тело)",
                          "Место укладки грунта и его объём, м³ (с kр)")):
    cell(w7, f"{c}5", t, F_B, fill=HEAD)
w7["E5"].border = BOX
for c, t in zip("GHIJ", ("№ п/п", "Место устройства насыпи", "Геометрический объём насыпи, м³",
                          "Потребный объём грунта V / kо.р, м³")):
    cell(w7, f"{c}5", t, F_B, fill=HEAD)
VOSN1, VS1, VPAZ1, VPODS1 = KR1["VOSN"], KR1["VS"], KR1["VPAZ"], KR1["VPODS"]
rl4 = 7 + len(RS.FILL)                                    # строка Σ в табл. 4
cut4 = chr(ord("C") + len(RS.CUT) - 1)                    # последний столбец выемок в табл. 4
rows3 = [  # выемка: №, место, объём, место укладки, объём с kр | насыпь: №, место, геом., потребный
    (1, "Котлован", f"={VOSN1}", "Отвал (засыпка съезда)", f"=J8*{KP}",
     1, "Пазухи сооружения - песок из карьера", f"={VPAZ1}", f"=I6/{KOR}"),
    (2, "Съезд", f"={VS1}", "Транспортные средства", f"=(C8-J8)*{KP}",
     2, "Съезд - грунт котлована из отвала", f"={VS1}", f"=I7/{KOR}"),
]
for r, row in zip((6, 7), rows3):
    for c, v in zip("ABCDEGHIJ", row):
        isf = isinstance(v, str) and v.startswith("=")
        cell(w7, f"{c}{r}", v, F_LINK if isf and v.startswith("='") else F_CALC, "0.00" if isf else None,
             al=CEN if isf or isinstance(v, int) else LEFT)
cell(w7, "B8", "ΣVв", F_B, al=LEFT); cell(w7, "A8", "")
cell(w7, "C8", "=C6+C7", F_B, "0.00")
cell(w7, "D8", "Σ (с kр)", F_B, al=LEFT)
cell(w7, "E8", "=E6+E7", F_B, "0.00")
cell(w7, "G8", ""); cell(w7, "H8", "ΣVн местного грунта (песок - привозной)", F_B, al=LEFT)
cell(w7, "I8", "")
cell(w7, "J8", "=J7", F_B, "0.00")
T3B = [
    ("Объём грунта в отвал (засыпка съезда): ΣVн · kр, м³", "=E6"),
    ("В транспортные средства: (ΣVв − ΣVн) · kр, м³", "=E7"),
    ("   из них в насыпь планировки (табл. 4), с kр, м³",
     f"=MIN(C8-J8,'Табл. 4 распределение'!B{rl4}-SUM('Табл. 4 распределение'!C5:{cut4}5))*{KP}"),
    ("   вывоз (лишний грунт), с kр, м³", "=E11-E12"),
    ("Привозится из карьера: песок для засыпки пазух, плотное тело / с kр, м³", "=J6"),
    ("Привозится из карьера: щебень для подсыпки Vподс / kо.р, м³", f"={VPODS1}/{KOR}"),
    ("Проверка: отвал + транспорт − ΣVв · kр (должно быть 0)", f"=E6+E7-C8*{KP}"),
]
for k_, (t, fml) in enumerate(T3B):
    r = 10 + k_
    w7.merge_cells(f"A{r}:D{r}")
    cell(w7, f"A{r}", t, al=LEFT)
    for c in "BCD":
        w7[f"{c}{r}"].border = BOX
    cell(w7, f"E{r}", fml, F_CALC, "0.00")
cell(w7, "F14", f"=E14*{KP}", F_CALC, "0.00")
cell(w7, "F15", f"=E15*{KP}", F_CALC, "0.00")
for c, wd in zip("ABCDEFGHIJ", (6, 22, 16, 22, 13, 11, 6, 34, 16, 18)):
    w7.column_dimensions[c].width = wd
w7.row_dimensions[5].height = 48

# ---------- табл. 4: баланс распределения земляных масс (п. 2.2.5) ----------
w8 = wb.create_sheet("Табл. 4 распределение")
w8["A1"] = "Баланс распределения земляных масс (табл. 4 методички): из выемок и котлована в насыпь, м³"
w8["A1"].font = F_T
w8["A2"] = ("Минимум моментов V·l (l - между центрами тяжести фигур): сначала выемки (ЗТМ), затем котлован "
            "(самосвалы); остаток - недостача, подвоз из карьера. Выемка - плотное тело, насыпь - Vн / kо.р.")
w8["A2"].font = F_NOTE
srcs = [g["name"] for g in RS.CUT] + ["Котлован", "Недостача"]
cols8 = [chr(ord("C") + k) for k in range(len(srcs))]
cell(w8, "A4", "Выемка", F_B, fill=HEAD); cell(w8, "B4", "№", F_B, fill=HEAD)
cell(w8, "A5", "", fill=HEAD); cell(w8, "B5", "Объём", F_B, fill=HEAD)
for c, nm in zip(cols8, srcs):
    cell(w8, f"{c}4", nm, F_B, fill=HEAD)
for c, g in zip(cols8, RS.CUT):
    cell(w8, f"{c}5", float(g["V"]), F_IN, "0.00")
cell(w8, f"{cols8[-2]}5", float(RS.V_PIT_FILL), F_IN, "0.00")
cell(w8, f"{cols8[-1]}5", float(sum(RS.SHORT.values())), F_IN, "0.00")
cell(w8, "A6", "Насыпь №", F_B, fill=HEAD); cell(w8, "B6", "Объём", F_B, fill=HEAD)
for c in cols8:
    cell(w8, f"{c}6", "", fill=HEAD)
for k, g in enumerate(RS.FILL):
    r = 7 + k
    cell(w8, f"A{r}", g["name"], F_B)
    cell(w8, f"B{r}", float(g["V"] / RS.K_OR), F_IN, "0.00")
    for i, c in enumerate(cols8[:-2]):
        v = RS.ZTM.get((i, k))
        cell(w8, f"{c}{r}", float(v) if v else None, F_IN, "0.00")
    v = RS.PIT.get((0, k))
    cell(w8, f"{cols8[-2]}{r}", float(v) if v else None, F_IN, "0.00")
    v = RS.SHORT.get(k)
    cell(w8, f"{cols8[-1]}{r}", float(v) if v else None, F_IN, "0.00")
rl = 7 + len(RS.FILL)
cell(w8, f"A{rl}", "Σ", F_B); cell(w8, f"B{rl}", f"=SUM(B7:B{rl - 1})", F_B, "0.00")
for c in cols8:
    cell(w8, f"{c}{rl}", f"=SUM({c}7:{c}{rl - 1})", F_B, "0.00")
cc = chr(ord(cols8[-1]) + 1)
cell(w8, f"{cc}6", "Проверка: Σ по строке − объём", F_B, fill=HEAD)
for r in range(7, rl):
    cell(w8, f"{cc}{r}", f"=SUM({cols8[0]}{r}:{cols8[-1]}{r})-B{r}", F_CALC, "0.00")
cell(w8, f"A{rl + 1}", "Проверка: Σ по столбцу − объём", al=LEFT)
w8.merge_cells(f"A{rl + 1}:B{rl + 1}")
for c in cols8:
    cell(w8, f"{c}{rl + 1}", f"={c}{rl}-{c}5", F_CALC, "0.00")
w8.column_dimensions["A"].width = 12
w8.column_dimensions["B"].width = 11
for c in cols8:
    w8.column_dimensions[c].width = 10
w8.column_dimensions[cc].width = 18
w8.row_dimensions[6].height = 32


# ---------- табл. 5, 6: средняя дальность (п. 2.2.6), метод статических моментов ----------
def sheet_mean(name, title, data, labels):
    """Как в методичке: столбцы - фигуры (выемка, насыпь), строки - V, x, y, Mx = x·V, My = y·V."""
    rs, rd, *_ = data
    w9 = wb.create_sheet(name)
    w9["A1"] = title
    w9["A1"].font = F_T
    cols = [chr(ord("B") + k) for k in range(len(rs) + len(rd))]
    cell(w9, "A3", "№ фигур", F_B, fill=HEAD)
    for c, (nm, *_), zone in zip(cols, rs + rd, [labels[0]] * len(rs) + [labels[1]] * len(rd)):
        cell(w9, f"{c}2", zone, F_B, fill=HEAD)
        cell(w9, f"{c}3", nm, F_B, fill=HEAD)
    cell(w9, "A2", "", fill=HEAD)
    for r, t in zip(range(4, 9), ("V, м³", "x, м", "y, м", "Mx = x·V", "My = y·V")):
        cell(w9, f"A{r}", t, F_B)
    for c, (nm, v, x, y, *_ ) in zip(cols, rs + rd):
        cell(w9, f"{c}4", float(v), F_IN, "0.00")
        cell(w9, f"{c}5", x, F_IN, "0.00")
        cell(w9, f"{c}6", y, F_IN, "0.00")
        cell(w9, f"{c}7", f"={c}5*{c}4", F_CALC, "0.0")
        cell(w9, f"{c}8", f"={c}6*{c}4", F_CALC, "0.0")
    a1, a2 = cols[0], cols[len(rs) - 1]
    b1, b2 = cols[len(rs)], cols[-1]
    res = [
        (f"Центр тяжести «{labels[0]}»: Lx = ΣMx / ΣV, м", f"=SUM({a1}7:{a2}7)/SUM({a1}4:{a2}4)"),
        (f"Центр тяжести «{labels[0]}»: Ly = ΣMy / ΣV, м", f"=SUM({a1}8:{a2}8)/SUM({a1}4:{a2}4)"),
        (f"Центр тяжести «{labels[1]}»: Lx, м", f"=SUM({b1}7:{b2}7)/SUM({b1}4:{b2}4)"),
        (f"Центр тяжести «{labels[1]}»: Ly, м", f"=SUM({b1}8:{b2}8)/SUM({b1}4:{b2}4)"),
        ("Средняя дальность Lср = √((Lxв − Lxн)² + (Lyв − Lyн)²), м", "=SQRT((C11-C13)^2+(C12-C14)^2)"),
    ]
    for k, (t, fml) in enumerate(res):
        r = 11 + k
        w9.merge_cells(f"A{r}:B{r}")
        cell(w9, f"A{r}", t, al=LEFT)
        w9[f"B{r}"].border = BOX
        cell(w9, f"C{r}", fml, F_B, "0.00")
    w9.column_dimensions["A"].width = 30
    for c in cols:
        w9.column_dimensions[c].width = 11
    return f"'{name}'!$C$15"


L5 = sheet_mean("Табл. 5 скрепер",
                "Средняя дальность перемещения грунта скрепером (бульдозером): выемка — насыпь (табл. 5)",
                RS.T5, ("Выемка", "Насыпь"))
sheet_mean("Табл. 6 самосвал", "Средняя дальность перемещения грунта автосамосвалом: котлован — насыпь (табл. 6)",
           RS.T6, ("Котлован", "Насыпь"))

# ---------- п. 2.3: назначение комплекта машин (нормы - ЕНиР Е2-1) ----------
import mashiny as MS
F_SM = Font(name=FONT, size=10, italic=True)
SN = "2.3 Грунт и нормы ЕНиР"
wn = wb.create_sheet(SN)
wn["A1"] = "Назначение комплекта машин (п. 2.3 методички): грунт и нормы времени ЕНиР Е2-1"
wn["A1"].font = F_T
for r, (t, v, fmt) in enumerate((
        ("Наименование и краткая характеристика грунта", f"{MS.GRUNT} ({MS.GRUNT_SRC})", None),
        ("Группа грунта в зависимости от трудности разработки",
         f"одноковшовые экскаваторы — {MS.GR_EXC}; скреперы — {MS.GR_SCR}; бульдозеры — {MS.GR_BUL}", None),
        ("Средняя плотность в естественном залегании, кг/м³", MS.RHO, "0")), start=3):
    cell(wn, f"A{r}", t, al=LEFT)
    wn.merge_cells(f"B{r}:G{r}")
    cell(wn, f"B{r}", v, F_IN, fmt, al=LEFT)
    for c in "CDEFG":
        wn[f"{c}{r}"].border = BOX
RHO = f"'{SN}'!$B$5"
for c, t in zip("ABCDEFG", ("Машина", "Марка", "Обоснование (ЕНиР Е2-1)", "Нвр, маш.-ч на 100 м³",
                            "Добавлять на каждые следующие 10 м", "Нвр дана до, м", "Условия")):
    cell(wn, f"{c}7", t, F_B, fill=HEAD)
NORM = {}                                           # машина -> строка
for r, (key, m) in enumerate((("bul_ved", MS.BUL_VED), ("skr_ved", MS.SKR_VED), ("rykhl", MS.RYKHL),
                              ("bul_raz", MS.BUL_RAZ), ("katok", MS.KATOK), ("tolkach", MS.TOLKACH)), start=8):
    role, brand, src, a, b, L0, note = m
    NORM[key] = r
    cell(wn, f"A{r}", role + (" (ведущая, вариант 1)" if key == "bul_ved" else " (ведущая, вариант 2)"
                              if key == "skr_ved" else " (разравнивание)" if key == "bul_raz" else ""), al=LEFT)
    cell(wn, f"B{r}", brand, al=LEFT)
    cell(wn, f"C{r}", src, al=LEFT)
    cell(wn, f"D{r}", float(a) if a is not None else "Нвр скрепера / k", F_IN if a is not None else F_CALC,
         "0.00" if a is not None else None)
    cell(wn, f"E{r}", float(b) if b is not None else "—", F_IN if b is not None else F_CALC, "0.00")
    cell(wn, f"F{r}", L0 if L0 is not None else "—", F_IN if L0 is not None else F_CALC)
    cell(wn, f"G{r}", note, F_SM, al=LEFT)
wn["A15"] = ("Добавка на расстояние сверх указанного в норме - пропорционально: Нвр = Нвр.до + добавка · (Lср − L) / 10. "
             "Толкач: Нвр скрепера, делённая на число обслуживаемых скреперов (Е2-1-21, примеч. 2; прил. 5).")
wn["A15"].font = F_NOTE
for c, wd in zip("ABCDEFG", (40, 40, 28, 14, 16, 12, 46)):
    wn.column_dimensions[c].width = wd
wn.row_dimensions[7].height = 48
NR = lambda col, key: f"'{SN}'!${col}${NORM[key]}"

# ---------- табл. 7: варианты с различными ведущими машинами (п. 2.3.1) ----------
S7 = "Табл. 7 варианты"
w10 = wb.create_sheet(S7)
w10["A1"] = "Варианты с различными ведущими машинами (табл. 7 методички), вертикальная планировка"
w10["A1"].font = F_T
w10["A2"] = ("Vдн = 100·N·8 / Нвр;  Mсм = Нвр·V / (100·8);  nвед = Mсм / (m·t);  n = nвед·Vдн.вед / Vдн.об "
             "(с. 25-27; Нвр - на 100 м³). Ведущая машина и толкач - V с kр, рыхлитель - V в плотном теле.")
w10["A2"].font = F_NOTE
cut_cols = cols8[:len(RS.CUT)]
PAR = [("Средняя дальность перемещения грунта Lср (табл. 5), м", f"={L5}", F_LINK, "0.00"),
       ("Грунт выемок в насыпь (табл. 4), в плотном теле V, м³",
        f"=SUM('Табл. 4 распределение'!{cut_cols[0]}5:{cut_cols[-1]}5)", F_LINK, "0.00"),
       ("То же с коэффициентом первоначального разрыхления V·kр, м³", f"=C5*{KP}", F_CALC, "0.00"),
       ("Объём насыпи - разравнивание и уплотнение Vн, м³", f"='Табл. 4 распределение'!B{rl}*{KOR}", F_LINK, "0.00"),
       ("Число смен в сутках m (N), по 8 ч", MS.M_SM, F_IN, "0"),
       ("Срок планировочных работ t, дн. (5-20, для обоих вариантов)", MS.T_DN, F_IN, "0"),
       ("Скреперов на один трактор-толкач (прил. 5)", MS.SKR_NA_TOLKACH, F_IN, "0")]
for r, (t, v, fnt, fmt) in enumerate(PAR, start=4):
    w10.merge_cells(f"A{r}:B{r}")
    cell(w10, f"A{r}", t, al=LEFT)
    w10[f"B{r}"].border = BOX
    cell(w10, f"C{r}", v, fnt, fmt, fill=YEL if r in (8, 9, 10) else None)
LSR, V7, VKR7, VN7, MSM, TDN, KTOL = (f"$C${r}" for r in range(4, 11))


def block7(c0, r0, title, brand, V, H, lead=None):
    """Блок машины в табл. 7: заголовок, V, Нвр, Mсм, Vдн, n. c0 - столбец подписи; -> адреса."""
    a, b, c = c0, chr(ord(c0) + 1), chr(ord(c0) + 2)
    cell(w10, f"{a}{r0}", title, F_B, al=LEFT, fill=HEAD)
    w10.merge_cells(f"{b}{r0}:{c}{r0}")
    cell(w10, f"{b}{r0}", brand, F_SM, al=LEFT, fill=HEAD)
    w10[f"{c}{r0}"].border = BOX
    sub = "вед" if lead is None else "об"
    rows = [(f"V, м³", "", V, "0.00"), (f"Нвр {sub}, маш.-ч", "", H, "0.0000"),
            (f"Mсм {sub}, маш.-см", "", f"={c}{r0 + 2}*{c}{r0 + 1}/800", "0.00"),
            (f"Vдн {sub}, м³/дн", "", f"=100*{MSM}*8/{c}{r0 + 2}", "0.00")]
    if lead is None:
        rows.append(("n, шт.", f"={c}{r0 + 3}/({MSM}*{TDN})", f"=ROUNDUP(ROUND({b}{r0 + 5},6),0)", "0"))
    else:
        rows.append(("n, шт.", f"={lead['n']}*{lead['vdn']}/{c}{r0 + 4}", f"=ROUNDUP(ROUND({b}{r0 + 5},6),0)", "0"))
    for k, (t, note, v, fmt) in enumerate(rows, start=1):
        r = r0 + k
        cell(w10, f"{a}{r}", t, al=LEFT)
        cell(w10, f"{b}{r}", note, F_CALC, "0.000")
        cell(w10, f"{c}{r}", v, F_LINK if isinstance(v, str) and v.startswith("='") else F_CALC, fmt)
    return {"V": f"{c}{r0 + 1}", "H": f"{c}{r0 + 2}", "M": f"{c}{r0 + 3}", "vdn": f"{c}{r0 + 4}",
            "n": f"{c}{r0 + 5}"}


for c0, t in (("A", "Вариант 1"), ("E", "Вариант 2")):
    w10.merge_cells(f"{c0}12:{chr(ord(c0) + 2)}12")
    cell(w10, f"{c0}12", t, F_B, fill=HEAD)
    for c in (chr(ord(c0) + 1), chr(ord(c0) + 2)):
        w10[f"{c}12"].border = BOX
lead_h = lambda key: f"={NR('D', key)}+{NR('E', key)}*({LSR}-{NR('F', key)})/10"
B1v = block7("A", 13, "Ведущая машина — бульдозер", MS.BUL_VED[1], f"={VKR7}", lead_h("bul_ved"))
B2v = block7("E", 13, "Ведущая машина — скрепер", MS.SKR_VED[1], f"={VKR7}", lead_h("skr_ved"))
w10["B14"] = "объём с коэффициентом первоначального разрыхления"
w10["B14"].font = F_SM
w10["B14"].alignment = LEFT
for c0 in "AE":
    w10.merge_cells(f"{c0}19:{chr(ord(c0) + 2)}19")
    cell(w10, f"{c0}19", "Обеспечивающие машины", F_B, al=LEFT)
    for c in (chr(ord(c0) + 1), chr(ord(c0) + 2)):
        w10[f"{c}19"].border = BOX
V1 = [B1v, block7("A", 20, "Трактор-рыхлитель", MS.RYKHL[1], f"={V7}", f"={NR('D', 'rykhl')}", B1v),
      block7("A", 26, "Каток", MS.KATOK[1], f"={VN7}", f"={NR('D', 'katok')}", B1v)]
w10["B21"] = "объём в плотном теле"
w10["B21"].font = F_SM
w10["B21"].alignment = LEFT
V2 = [B2v, block7("E", 20, "Трактор-рыхлитель", MS.RYKHL[1], f"={V7}", f"={NR('D', 'rykhl')}", B2v),
      block7("E", 26, "Бульдозер", MS.BUL_RAZ[1], f"={VN7}", f"={NR('D', 'bul_raz')}", B2v),
      block7("E", 32, "Каток", MS.KATOK[1], f"={VN7}", f"={NR('D', 'katok')}", B2v),
      block7("E", 38, "Трактор-толкач", MS.TOLKACH[1], f"={VKR7}", f"={B2v['H']}/{KTOL}", B2v)]
TOT7 = [("Mсм вед + ΣMсм об, маш.-см", lambda v: "=" + "+".join(b["M"] for b in v), "0.00"),
        ("V / (Mсм вед + ΣMсм об), м³/маш.-см", None, "0.00"),
        ("(Mсм вед + ΣMсм об) / V, маш.-см/м³", None, "0.00000"),
        ("Продолжительность работ ведущими машинами, дн.", None, "0.0")]
for c0, v in (("A", V1), ("E", V2)):
    a, b, c = c0, chr(ord(c0) + 1), chr(ord(c0) + 2)
    for k, (t, fn, fmt) in enumerate(TOT7):
        r = 45 + k
        w10.merge_cells(f"{a}{r}:{b}{r}")
        cell(w10, f"{a}{r}", t, F_B if k < 3 else F_CALC, al=LEFT)
        w10[f"{b}{r}"].border = BOX
        fml = (fn(v) if k == 0 else f"={v[0]['V']}/{c}45" if k == 1 else f"={c}45/{v[0]['V']}" if k == 2
               else f"={v[0]['M']}/({v[0]['n']}*{MSM})")
        cell(w10, f"{c}{r}", fml, F_B if k < 3 else F_CALC, fmt)
w10.merge_cells("A50:G50")
cell(w10, "A50", '=IF(C47<G47,"Принимается вариант 1 - ведущая машина бульдозер: меньше маш.-см на 1 м³",'
                 '"Принимается вариант 2 - ведущая машина скрепер: меньше маш.-см на 1 м³")', F_B, al=LEFT)
for c in "BCDEFG":
    w10[f"{c}50"].border = BOX
for c, wd in zip("ABCDEFG", (34, 30, 13, 3, 34, 30, 13)):
    w10.column_dimensions[c].width = wd

# ---------- п. 2.3.2: экскаватор и автосамосвалы ----------
S8 = "2.3.2 Экскаватор, самосвалы"
w11 = wb.create_sheet(S8)
w11["A1"] = "Машины для разработки грунта в котловане (п. 2.3.2): экскаватор и автосамосвалы"
w11["A1"].font = F_T
for r, (t, v, fnt, fmt) in enumerate((
        ("Объём котлована Vк, м³", f"={KR1['VK']}", F_LINK, "0.00"),
        ("Глубина котлована hк, м", f"={KR1['HK']}", F_LINK, "0.0000"),
        ("Число смен в сутках m", f"='{S7}'!{MSM}", F_LINK, "0")), start=3):
    w11.merge_cells(f"A{r}:B{r}")
    cell(w11, f"A{r}", t, al=LEFT)
    w11[f"B{r}"].border = BOX
    cell(w11, f"C{r}", v, fnt, fmt)
# прил. 6 - справа
cell(w11, "E11", "Прил. 6: ёмкость ковша по объёму сооружения", F_B, al=LEFT, box=False)
for c, t in zip("EFGH", ("Ковш, м³", "Vк от, м³", "Vк до, м³", "Подходит")):
    cell(w11, f"{c}12", t, F_B, fill=HEAD)
for k, (q, a, b) in enumerate(MS.PRIL6):
    r = 13 + k
    cell(w11, f"E{r}", q)
    cell(w11, f"F{r}", a, F_IN, "0")
    cell(w11, f"G{r}", b if b < 10 ** 9 else "—", F_IN, "0")
    cell(w11, f"H{r}", f'=IF(AND($C$3>=F{r},$C$3<=IF(ISNUMBER(G{r}),G{r},1E+99)),"да","")')
hdr = ("Экскаватор (обратная лопата)", "Привод", "Ковш q, м³", "Обоснование (ЕНиР Е2-1)", "Нвр, маш.-ч на 100 м³ (I гр., с погрузкой)",
       "Псм = 100·8 / Нвр, м³/смену", "Hк max для котлованов, м", "Rmax, м", "Высота выгрузки, м",
       "Недобор (прил. 7), см")
for c, t in zip("ABCDEFGHIJ", hdr):
    cell(w11, f"{c}7", t, F_B, fill=HEAD)
for k, e in enumerate(MS.EXC):
    r = 8 + k
    nm, pr, q, H, src, hk, R_, hv, nd = e
    for c, v, fmt in zip("ABCDEFGHIJ", (nm, pr, float(q), src, float(H), f"=100*8/E{r}", float(hk), float(R_),
                                        float(hv), nd),
                         (None, None, "0.00", None, "0.0", "0.00", "0.0", "0.0", "0.0", "0")):
        cell(w11, f"{c}{r}", v, F_CALC if c == "F" else F_IN, fmt, al=LEFT if c in "ABD" else CEN)
SEL = "MATCH(MAX($F$8:$F$10),$F$8:$F$10,0)"
EXR = [("Принят экскаватор - наибольшая производительность", f"=INDEX($A$8:$A$10,{SEL})", None),
       ("Ковш q, м³", f"=INDEX($C$8:$C$10,{SEL})", "0.00"),
       ("Нвр, маш.-ч на 100 м³", f"=INDEX($E$8:$E$10,{SEL})", "0.0"),
       ("Недобор, м", f"=INDEX($J$8:$J$10,{SEL})/100", "0.00"),
       ("Глубина копания экскаватором hк − недобор, м", "=C4-C15", "0.0000"),
       ("Проверка: Hк max не меньше глубины копания", f'=IF(INDEX($G$8:$G$10,{SEL})>=C16,"выполняется","НЕТ")', None),
       ("Mсм = Нвр·Vк / (100·8), маш.-см", "=C14*C3/800", "0.00"),
       ("Продолжительность одним экскаватором Mсм / m, дн.", "=C18/C5", "0.0")]
for k, (t, fml, fmt) in enumerate(EXR):
    r = 12 + k
    w11.merge_cells(f"A{r}:B{r}")
    cell(w11, f"A{r}", t, F_B if k == 0 else F_CALC, al=LEFT)
    w11[f"B{r}"].border = BOX
    cell(w11, f"C{r}", fml, F_B if k == 0 else F_CALC, fmt)
# автосамосвалы (с. 28-29, прил. 8)
cell(w11, "A21", "Автосамосвалы (с. 28-29, прил. 8)", F_B, al=LEFT, box=False)
TRP = [("Коэффициент наполнения ковша kнап (табл. 8: 0,8-1,0)", float(MS.K_NAP), F_IN, "0.00"),
       ("Коэффициент первоначального разрыхления kр", f"={KP}", F_LINK, "0.00"),
       ("Плотность грунта γ, т/м³", f"={RHO}/1000", F_LINK, "0.000"),
       ("Грунт в ковше в плотном теле Vгр.к = q·kнап / kр, м³", "=C13*C22/C23", F_CALC, "0.0000"),
       ("Масса грунта в ковше Mковша = Vгр.к·γ, т", "=C25*C24", F_CALC, "0.0000"),
       ("Дальность транспортирования L, км (до карьера, отвала)", float(MS.L_TR), F_IN, "0.0"),
       ("Установка под погрузку Ту.п, мин", float(MS.T_UP), F_IN, "0.0"),
       ("Установка под разгрузку Ту.р, мин", float(MS.T_UR), F_IN, "0.0"),
       ("Разгрузка Тр, мин", float(MS.T_R), F_IN, "0.0"),
       ("Маневрирование Тм, мин", float(MS.T_M), F_IN, "0.0")]
for k, (t, v, fnt, fmt) in enumerate(TRP):
    r = 22 + k
    w11.merge_cells(f"A{r}:B{r}")
    cell(w11, f"A{r}", t, al=LEFT)
    w11[f"B{r}"].border = BOX
    cell(w11, f"C{r}", v, fnt, fmt, fill=YEL if r == 22 else None)
hdrt = ("Модель", "Va, м³", "Па, т", "Погрузочная высота, м", "Uгр, км/ч", "Uпор, км/ч", "Па / Mковша",
        "Va / q", "n (целое меньшее)", "6 ≤ n ≤ 11", "Va пл = n·Vгр.к, м³", "Тп = Va пл·Нвр / 100 · 60, мин",
        "Тпр гр = L / Uгр · 60, мин", "Тпр пор = L / Uпор · 60, мин", "Тцикла, мин", "Тцикла / Тп",
        "N, шт.", "Va р = q·kнап·n, м³", "Нвр а = Тцикла / (Va р·60), маш.-ч/м³", "Нвр а подходящих")
TC = [chr(ord("A") + k) for k in range(len(hdrt))]
for c, t in zip(TC, hdrt):
    cell(w11, f"{c}33", t, F_B, fill=HEAD)
for k, t in enumerate(MS.PRIL8):
    r = 34 + k
    nm, Va, Pa, hp, ug, up = t
    vals = [(nm, F_IN, None), (float(Va), F_IN, "0.0"), (float(Pa), F_IN, "0.00"), (float(hp), F_IN, "0.00"),
            (ug, F_IN, "0"), (up, F_IN, "0"),
            (f"=C{r}/$C$26", F_CALC, "0.00"), (f"=B{r}/$C$13", F_CALC, "0.00"),
            (f"=INT(ROUND(MIN(G{r},H{r}),6))", F_CALC, "0"), (f'=IF(AND(I{r}>=6,I{r}<=11),"да","нет")', F_CALC, None),
            (f"=I{r}*$C$25", F_CALC, "0.000"), (f"=K{r}*$C$14/100*60", F_CALC, "0.00"),
            (f"=$C$27/E{r}*60", F_CALC, "0.00"), (f"=$C$27/F{r}*60", F_CALC, "0.00"),
            (f"=$C$28+L{r}+M{r}+N{r}+$C$29+$C$30+$C$31", F_CALC, "0.00"), (f"=O{r}/L{r}", F_CALC, "0.00"),
            (f"=ROUNDUP(ROUND(P{r},6),0)", F_CALC, "0"), (f"=$C$13*$C$22*I{r}", F_CALC, "0.00"),
            (f"=O{r}/(R{r}*60)", F_CALC, "0.0000"), (f'=IF(J{r}="да",S{r},"")', F_CALC, "0.0000")]
    for c, (v, fnt, fmt) in zip(TC, vals):
        cell(w11, f"{c}{r}", v, fnt, fmt, al=LEFT if c == "A" else CEN)
re_ = 34 + len(MS.PRIL8) - 1
SELT = f"MATCH(MIN($T$34:$T${re_}),$T$34:$T${re_},0)"
for k, (t, fml, fmt) in enumerate((
        ("Принят автосамосвал - наименьшая Нвр а из подходящих", f"=INDEX($A$34:$A${re_},{SELT})", None),
        ("Ковшей в кузове n", f"=INDEX($I$34:$I${re_},{SELT})", "0"),
        ("Количество автосамосвалов N ≥ Тцикла / Тп, шт.", f"=INDEX($Q$34:$Q${re_},{SELT})", "0"),
        ("Нвр а, маш.-ч/м³", f"=INDEX($S$34:$S${re_},{SELT})", "0.0000"))):
    r = re_ + 2 + k
    w11.merge_cells(f"A{r}:B{r}")
    cell(w11, f"A{r}", t, F_B if k == 0 else F_CALC, al=LEFT)
    w11[f"B{r}"].border = BOX
    cell(w11, f"C{r}", fml, F_B if k == 0 else F_CALC, fmt)
for c in TC:
    w11.column_dimensions[c].width = 11
for c, wd in (("A", 42), ("B", 22), ("C", 14), ("D", 26), ("E", 13)):
    w11.column_dimensions[c].width = wd
w11.row_dimensions[7].height = 64
w11.row_dimensions[33].height = 62

# ---------- содержание: все таблицы курсовой - в одном файле, каждая на своём листе ----------
DESCR = {
    "Исходные данные": "Рабочие отметки варианта 2, коэффициенты kо.р и kр",
    "ЛНР (черн.)": "Точки нулевых работ (п. 2.2.1), черновик",
    "Табл. 1 объёмы (черн.)": "Ведомость объёмов работ по вертикальной планировке (табл. 1), черновик",
    "Котлован (черн.)": "Контуры, размеры и объём котлована (п. 2.2.2), черновик",
    "Табл. 2 баланс (черн.)": "Сводная ведомость объёмов грунта (табл. 2) и поправка Δh (п. 2.2.3)",
    "Отметки (оконч.)": "Окончательные рабочие отметки h + Δh",
    "ЛНР (оконч.)": "Точки нулевых работ по окончательным отметкам",
    "Табл. 1 объёмы (оконч.)": "Ведомость объёмов работ по вертикальной планировке (табл. 1), окончательная",
    "Котлован (оконч.)": "Котлован по окончательным отметкам: съезд, обратная засыпка",
    "Табл. 2 баланс (оконч.)": "Сводная ведомость объёмов грунта (табл. 2), окончательная",
    "Табл. 3 котлован": "Баланс земляных работ по котловану (табл. 3, п. 2.2.4)",
    "Табл. 4 распределение": "Баланс распределения земляных масс (табл. 4, п. 2.2.5)",
    "Табл. 5 скрепер": "Средняя дальность перемещения грунта скрепером (табл. 5, п. 2.2.6)",
    "Табл. 6 самосвал": "Средняя дальность перемещения грунта автосамосвалом (табл. 6, п. 2.2.6)",
    "2.3 Грунт и нормы ЕНиР": "Характеристика грунта и нормы времени машин по ЕНиР Е2-1 (п. 2.3)",
    "Табл. 7 варианты": "Варианты с различными ведущими машинами (табл. 7, п. 2.3.1)",
    "2.3.2 Экскаватор, самосвалы": "Выбор экскаватора и автосамосвалов (п. 2.3.2)",
}
wc = wb.create_sheet("Содержание", 0)
wc["A1"] = "Курсовая работа по ТСП «Технологическая карта на производство земляных работ», вариант 2: таблицы расчёта"
wc["A1"].font = F_T
for c, t in zip("ABC", ("№", "Лист", "Содержание")):
    cell(wc, f"{c}3", t, F_B, fill=HEAD)
sheets = [sh.title for sh in wb.worksheets if sh.title != "Содержание"]
assert set(sheets) == set(DESCR), set(sheets) ^ set(DESCR)
for k, nm in enumerate(sheets, start=1):
    r = 3 + k
    cell(wc, f"A{r}", k)
    c_ = cell(wc, f"B{r}", nm, Font(name=FONT, size=12, color="0000FF", underline="single"), al=LEFT)
    c_.hyperlink = f"#'{nm}'!A1"
    cell(wc, f"C{r}", DESCR[nm], al=LEFT)
wc.column_dimensions["A"].width = 5
wc.column_dimensions["B"].width = 30
wc.column_dimensions["C"].width = 80
wb.active = 0

for sh in wb.worksheets:
    sh.sheet_view.zoomScale = 110
    sh.page_setup.paperSize = sh.PAPERSIZE_A4
    sh.page_setup.orientation = "landscape"
    sh.sheet_properties.pageSetUpPr.fitToPage = True
    sh.page_setup.fitToWidth = 1
    sh.page_setup.fitToHeight = 1          # каждый лист печатается на одну страницу

out = Path(__file__).resolve().parent / "Объёмы_планировки_вариант2.xlsx"
wb.save(out)

# openpyxl пишет формулы без значений - пересчёт и сохранение самим Excel (COM)
ps = (f"$xl = New-Object -ComObject Excel.Application; $xl.Visible = $false; $xl.DisplayAlerts = $false; "
      f"$wb = $xl.Workbooks.Open('{out}'); $xl.CalculateFull(); $wb.Save(); $wb.Close(); $xl.Quit()")
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print(out.name, "- формулы пересчитаны в Excel" if r.returncode == 0 else f"- Excel не пересчитал: {r.stderr}")
