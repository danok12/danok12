"""Excel-книга расчёта систем В1 и К1 (вариант 3) с живыми формулами.

Запуск: python build_excel.py  ->  ../Raschet_VV_variant3.xlsx
Все результаты в книге считаются формулами Excel; из Python берутся только исходные данные
(длины участков, числа приборов, диаметры — из rezultaty_v3.json) и справочные таблицы СП 30.
Книгу можно использовать для любого варианта: менять жёлтые ячейки.
"""
import json
import os

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from normy import A2_ZHILYE, B1, B1_P, B2, T51, T51_L, T121
from raschet_v3 import PE, VGP, D_ZAPAS

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "rezultaty_v3.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "..", "Raschet_VV_variant3.xlsx")

FONT = "Times New Roman"
F_IN = Font(name=FONT, size=11, color="0000FF")          # исходные данные
F_CALC = Font(name=FONT, size=11, color="000000")        # формулы
F_LINK = Font(name=FONT, size=11, color="008000")        # ссылки на другой лист
F_HEAD = Font(name=FONT, size=11, bold=True)
F_TITLE = Font(name=FONT, size=13, bold=True)
F_NOTE = Font(name=FONT, size=10, italic=True, color="555555")
FILL_IN = PatternFill("solid", fgColor="FFFF99")
FILL_HEAD = PatternFill("solid", fgColor="DDEBF7")
FILL_RES = PatternFill("solid", fgColor="E2EFDA")
THIN = Side(style="thin", color="808080")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

wb = Workbook()
wb.remove(wb.active)


def sheet(name, widths):
    ws = wb.create_sheet(name)
    for k, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(k)].width = w
    ws.sheet_view.showGridLines = False
    return ws


def put(ws, ref, value, kind="calc", fmt=None, bold=False, align=CENTER, fill=None, border=True):
    c = ws[ref]
    c.value = value
    c.font = {"in": F_IN, "calc": F_CALC, "link": F_LINK, "head": F_HEAD, "title": F_TITLE, "note": F_NOTE}[kind]
    if bold:
        c.font = Font(name=FONT, size=11, bold=True, color=c.font.color.rgb if c.font.color else "000000")
    if kind == "in":
        c.fill = FILL_IN
    if kind == "head":
        c.fill = FILL_HEAD
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt
    if kind == "title":
        align = Alignment(horizontal="left", vertical="center", wrap_text=False)
    if align:
        c.alignment = align
    if border and kind not in ("title", "note"):
        c.border = BOX
    return c


def name(nm, ref):
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


# ---------------- формулы-генераторы ----------------
def alpha_f(N, P):
    """α по п. 5.3 СП 30: табл. Б.1 при P > 0,1 и N ≤ 200 (двойная интерполяция), иначе Б.2 (интерполяция по NP)."""
    x = f"({N}*{P})"
    m = f"MATCH({x},B2_NP,1)"
    b2 = (f"IF({x}<INDEX(B2_NP,1),0.2,IF({x}>=INDEX(B2_NP,ROWS(B2_NP)),INDEX(B2_A,ROWS(B2_NP)),"
          f"INDEX(B2_A,{m})+({x}-INDEX(B2_NP,{m}))*(INDEX(B2_A,{m}+1)-INDEX(B2_A,{m}))/(INDEX(B2_NP,{m}+1)-INDEX(B2_NP,{m}))))")
    pj = f"MIN(MATCH({P},B1_P,1),COLUMNS(B1_P)-1)"
    tp = f"MIN(1,({P}-INDEX(B1_P,1,{pj}))/(INDEX(B1_P,1,{pj}+1)-INDEX(B1_P,1,{pj})))"
    nc = f"MAX({N},INDEX(B1_N,1))"
    nr = f"MIN(MATCH({nc},B1_N,1),ROWS(B1_N)-1)"
    tn = f"MIN(1,({nc}-INDEX(B1_N,{nr}))/(INDEX(B1_N,{nr}+1)-INDEX(B1_N,{nr})))"
    g = lambda r, c: f"INDEX(B1_G,{r},{c})"
    b1 = (f"((1-{tn})*((1-{tp})*{g(nr, pj)}+{tp}*{g(nr, pj + '+1')})"
          f"+{tn}*((1-{tp})*{g(nr + '+1', pj)}+{tp}*{g(nr + '+1', pj + '+1')}))")
    return f"IF(AND({P}>0.1,{N}<=200),{b1},{b2})"


def ks_f(N, L):
    """K_s по табл. 5.1 СП 30 — двойная линейная интерполяция по N и L (с ограничением по краям таблицы)."""
    nc = f"MAX({N},INDEX(T51_N,1))"
    nr = f"MIN(MATCH({nc},T51_N,1),ROWS(T51_N)-1)"
    tn = f"MIN(1,({nc}-INDEX(T51_N,{nr}))/(INDEX(T51_N,{nr}+1)-INDEX(T51_N,{nr})))"
    lc = f"MAX({L},INDEX(T51_L,1,1))"
    lj = f"MIN(MATCH({lc},T51_L,1),COLUMNS(T51_L)-1)"
    tl = f"MIN(1,({lc}-INDEX(T51_L,1,{lj}))/(INDEX(T51_L,1,{lj}+1)-INDEX(T51_L,1,{lj})))"
    g = lambda r, c: f"INDEX(T51_G,{r},{c})"
    return (f"(1-{tn})*((1-{tl})*{g(nr, lj)}+{tl}*{g(nr, lj + '+1')})"
            f"+{tn}*((1-{tl})*{g(nr + '+1', lj)}+{tl}*{g(nr + '+1', lj + '+1')})")


def pavl_q(h, Dm, i, n):
    """Расход, л/с, в круглой трубе по Шези–Павловскому при наполнении h (доля d)."""
    th = f"(2*ACOS(1-2*{h}))"
    w = f"({Dm}^2/8*({th}-SIN({th})))"
    R = f"({w}/({Dm}*{th}/2))"
    y = f"(2.5*SQRT({n})-0.13-0.75*SQRT({R})*(SQRT({n})-0.1))"
    return f"1000*{w}*{R}^{y}/{n}*SQRT({R}*{i})"


def pavl_v(h, Dm, i, n):
    th = f"(2*ACOS(1-2*{h}))"
    w = f"({Dm}^2/8*({th}-SIN({th})))"
    R = f"({w}/({Dm}*{th}/2))"
    y = f"(2.5*SQRT({n})-0.13-0.75*SQRT({R})*(SQRT({n})-0.1))"
    return f"{R}^{y}/{n}*SQRT({R}*{i})"


# =============== справочные листы ===============
ws = sheet("ТаблБ2", [12, 10, 50])
put(ws, "A1", "СП 30.13330.2020, табл. Б.2: α при P > 0,1 и любом N, а также при P ≤ 0,1 и N > 200 (при NP < 0,015 α = 0,200)", "title", align=LEFT)
put(ws, "A2", "NP", "head"); put(ws, "B2", "α", "head")
keys = sorted(B2)
for k, npv in enumerate(keys):
    put(ws, f"A{3 + k}", npv, "in", "0.000"); put(ws, f"B{3 + k}", B2[npv], "in", "0.000")
last = 2 + len(keys)
name("B2_NP", f"ТаблБ2!$A$3:$A${last}"); name("B2_A", f"ТаблБ2!$B$3:$B${last}")

ws = sheet("ТаблБ1", [8] + [8] * 10)
put(ws, "A1", "СП 30.13330.2020, табл. Б.1: α при P > 0,1 и N ≤ 200", "title", align=LEFT)
put(ws, "A2", "N \\ P", "head")
put(ws, "A3", "N", "head")
for j, pv in enumerate(B1_P):
    put(ws, f"{get_column_letter(2 + j)}3", pv, "in", "0.000")
rowsN = sorted(B1)
for r, nv in enumerate(rowsN):
    put(ws, f"A{4 + r}", nv, "in", "0")
    for j, a in enumerate(B1[nv]):
        put(ws, f"{get_column_letter(2 + j)}{4 + r}", a, "in", "0.00")
lr = 3 + len(rowsN)
name("B1_P", "ТаблБ1!$B$3:$K$3"); name("B1_N", f"ТаблБ1!$A$4:$A${lr}"); name("B1_G", f"ТаблБ1!$B$4:$K${lr}")

ws = sheet("Табл5_1", [8] + [7] * 13)
put(ws, "A1", "СП 30.13330.2020, табл. 5.1: коэффициент K_s по числу приборов N и длине участка L, м", "title", align=LEFT)
put(ws, "A3", "N \\ L", "head")
for j, lv in enumerate(T51_L):
    put(ws, f"{get_column_letter(2 + j)}3", lv, "in", "0")
for r, nv in enumerate(sorted(T51)):
    put(ws, f"A{4 + r}", nv, "in", "0")
    for j, kv in enumerate(T51[nv]):
        put(ws, f"{get_column_letter(2 + j)}{4 + r}", kv, "in", "0.00")
lr = 3 + len(T51)
name("T51_N", f"Табл5_1!$A$4:$A${lr}"); name("T51_L", "Табл5_1!$B$3:$N$3"); name("T51_G", f"Табл5_1!$B$4:$N${lr}")

ws = sheet("ТаблА2", [44, 11, 11, 11, 11, 11, 11, 11, 11, 8])
put(ws, "A1", "СП 30.13330.2020, табл. А.2, п. 1 «Жилые дома квартирного типа» (на 1 жителя)", "title", align=LEFT)
hdr = ["Водопотребители", "q_u^tot, л/сут", "q_u^h, л/сут", "q_hr,u^tot, л/ч", "q_hr,u^h, л/ч",
       "q_0^tot, л/с", "q_0,hr^tot, л/ч", "q_0^c (q_0^h), л/с", "q_0,hr^c, л/ч", "T, ч"]
for j, h in enumerate(hdr):
    put(ws, f"{get_column_letter(1 + j)}2", h, "head")
for r, (nm, z) in enumerate(A2_ZHILYE.items()):
    row = 3 + r
    vals = [nm, z["q_u_tot"], z["q_u_h"], z["q_hr_tot"], z["q_hr_h"], z["q0_tot"], z["q0hr_tot"], z["q0_c"], z["q0hr_c"], z["T"]]
    for j, v in enumerate(vals):
        put(ws, f"{get_column_letter(1 + j)}{row}", v, "in", None if j == 0 else "0.0##", align=LEFT if j == 0 else CENTER)
lrA2 = 2 + len(A2_ZHILYE)
name("A2_NAME", f"ТаблА2!$A$3:$A${lrA2}"); name("A2_TAB", f"ТаблА2!$A$3:$J${lrA2}")

ws = sheet("Табл12_1", [10, 13, 13, 16, 14, 16])
put(ws, "A1", "СП 30.13330.2020, табл. 12.1 и п. 12.16: счётчики воды", "title", align=LEFT)
for j, h in enumerate(["DN, мм", "q экспл., м³/ч", "S, м/(л/с)²", "Допустимые потери, м", "Подходит?", ""]):
    if h:
        put(ws, f"{get_column_letter(1 + j)}2", h, "head")
for r, dn in enumerate(sorted(T121)):
    row = 3 + r
    put(ws, f"A{row}", dn, "in", "0")
    put(ws, f"B{row}", T121[dn][0], "in", "0.0")
    put(ws, f"C{row}", T121[dn][1], "in", "0.00E+00")
    put(ws, f"D{row}", 5.0 if dn <= 40 else 2.5, "in", "0.0")
    put(ws, f"E{row}", f"=AND(B{row}>=Напор!$C$5,C{row}*Напор!$C$6^2<=D{row})", "calc")
lr12 = 2 + len(T121)
put(ws, f"A{lr12 + 1}", "Допустимые потери (п. 12.16): крыльчатые (DN ≤ 40) — 5 м, турбинные — 2,5 м. Счётчик подбирается по среднечасовому расходу (п. 12.14).", "note", align=LEFT)
name("T121_DN", f"Табл12_1!$A$3:$A${lr12}"); name("T121_S", f"Табл12_1!$C$3:$C${lr12}"); name("T121_OK", f"Табл12_1!$E$3:$E${lr12}")

ws = sheet("Трубы", [10, 14, 16, 4, 12, 14])
put(ws, "A1", "Трубы: сталь ВГП оцинкованная (ГОСТ 3262-75) и ПЭ100 SDR17", "title", align=LEFT)
for j, h in enumerate(["DN", "d_вн, мм", "d_расч = d_вн − 1, мм"]):
    put(ws, f"{get_column_letter(1 + j)}2", h, "head")
for r, dn in enumerate(sorted(VGP)):
    put(ws, f"A{3 + r}", dn, "in", "0"); put(ws, f"B{3 + r}", VGP[dn], "in", "0.0")
    put(ws, f"C{3 + r}", f"=B{3 + r}-{D_ZAPAS}", "calc", "0.0")
lrv = 2 + len(VGP)
put(ws, "E2", "ПЭ, Ø нар.", "head"); put(ws, "F2", "d_вн, мм", "head")
for r, dn in enumerate(sorted(PE)):
    put(ws, f"E{3 + r}", dn, "in", "0"); put(ws, f"F{3 + r}", PE[dn], "in", "0.0")
lrp = 2 + len(PE)
put(ws, f"A{max(lrv, lrp) + 2}", "Расчётный диаметр Шевелёва для стальных труб d_вн − 1 мм сверен с табл. 1 «Таблиц для гидравлического расчёта водопроводных труб» (1000i совпадает до 0,3 %).", "note", align=LEFT)
name("VGP_DN", f"Трубы!$A$3:$A${lrv}"); name("VGP_DR", f"Трубы!$C$3:$C${lrv}")
name("PE_DN", f"Трубы!$E$3:$E${lrp}"); name("PE_DV", f"Трубы!$F$3:$F${lrp}")

# =============== Исходные данные ===============
ws = sheet("Исходные", [52, 16, 14, 14, 14, 30])
wb.move_sheet("Исходные", offset=-wb.index(wb["Исходные"]))
put(ws, "A1", "Исходные данные (вариант 3). Жёлтые ячейки — вводимые данные, остальное считается формулами", "title", align=LEFT)
I = D["iznach"]
rows = [
    ("Этажность n_эт", I["N_ET"], "0", "B3"), ("Число секций n_сек", I["N_SEK"], "0", "B4"),
    ("Заселённость N_кв.жит, чел./кв.", D["U0"], "0.0", "B5"), ("Высота этажа, м", I["H_ET"], "0.00", "B6"),
    ("Расчётное время T, ч", 24, "0", "B7"), ("Гарантийный напор H_гар, м", I["H_GAR"], "0.0", "B8"),
    ("Глубина промерзания, м", I["H_PROMERZ"], "0.00", "B9"),
]
for k, (t, v, fmt, ref) in enumerate(rows):
    put(ws, f"A{3 + k}", t, "head", align=LEFT); put(ws, ref, v, "in", fmt)
put(ws, "A11", "Водопотребители (табл. А.2)", "head", align=LEFT)
put(ws, "B11", "ванны от 1500 мм с душами", "in", align=LEFT)
ws.merge_cells("B11:E11")
dv = DataValidation(type="list", formula1="=A2_NAME", allow_blank=False)
ws.add_data_validation(dv); dv.add("B11")
put(ws, "A13", "Квартиры на этаже одной секции", "head", align=LEFT)
for j, h in enumerate(["Тип квартиры", "Квартир на этаже секции", "Приборов с холодной водой", "Приборов с горячей водой"]):
    put(ws, f"{get_column_letter(1 + j)}14", h, "head")
types = [("3–4-комнатная (санузел + кухня: мойка, умывальник, ванна, унитаз)", D["N_KV"], 4, 3), ("—", 0, 0, 0), ("—", 0, 0, 0)]
for r, (t, n, nc, nh) in enumerate(types):
    put(ws, f"A{15 + r}", t, "in", align=LEFT); put(ws, f"B{15 + r}", n, "in", "0")
    put(ws, f"C{15 + r}", nc, "in", "0"); put(ws, f"D{15 + r}", nh, "in", "0")
calc_rows = [
    ("Квартир на этаже здания n_кв", "=SUM(B15:B17)*B4", "0", "Σ квартир секции × n_сек"),
    ("Всего квартир", "=B19*B3", "0", "n_кв · n_эт"),
    ("Число водопотребителей U, чел.", "=ROUNDUP(B5*B19*B3,0)", "0", "U = N_кв.жит · n_кв · n_эт (округление вверх)"),
    ("Число приборов N (холодная и общая вода)", "=SUMPRODUCT(B15:B17,C15:C17)*B4*B3", "0", "N = Σ(n_пр · n_кв) · n_эт"),
    ("Число приборов N^h (горячая вода)", "=SUMPRODUCT(B15:B17,D15:D17)*B4*B3", "0", "без унитазов"),
]
for k, (t, f, fmt, note) in enumerate(calc_rows):
    put(ws, f"A{19 + k}", t, "head", align=LEFT); put(ws, f"B{19 + k}", f, "calc", fmt, fill=FILL_RES)
    put(ws, f"C{19 + k}", note, "note", align=LEFT, border=False)
put(ws, "A25", "Нормы по табл. А.2 для выбранных водопотребителей", "head", align=LEFT)
for j, h in enumerate(["q_u^tot, л/сут", "q_u^h, л/сут", "q_hr,u^tot, л/ч", "q_hr,u^h, л/ч", "q_0^tot, л/с", "q_0,hr^tot, л/ч", "q_0^c=q_0^h, л/с", "q_0,hr^c, л/ч"]):
    put(ws, f"A{26 + j}", h, "head", align=LEFT)
    put(ws, f"B{26 + j}", f"=INDEX(A2_TAB,MATCH($B$11,A2_NAME,0),{2 + j})", "link", "0.0##")
put(ws, "A35", "Условные обозначения: синий шрифт на жёлтом — исходные данные; чёрный — формулы; зелёный — ссылки на другие листы.", "note", align=LEFT)

# =============== Расходы ===============
ws = sheet("Расходы", [9, 6, 7, 7, 9, 9, 8, 9, 10, 9, 10, 9, 8, 9, 10, 9, 8, 10])
put(ws, "A1", "Расчёт расходов воды (СП 30.13330.2020, разд. 5): суточные, среднечасовые, секундные, часовые", "title", align=LEFT)
heads = ["Вода", "T, ч", "U", "N", "q_u, л/сут", "q_hr,u, л/ч", "q_0, л/с", "q_0,hr, л/ч", "q_u,m, м³/сут",
         "q_T, м³/ч", "P", "NP", "α", "q, л/с", "P_hr", "NP_hr", "α_hr", "q_hr, м³/ч"]
for j, h in enumerate(heads):
    put(ws, f"{get_column_letter(1 + j)}3", h, "head")
src = {"tot": ("B26", "B28", "B30", "B31", "B22"), "h": ("B27", "B29", "B32", "B33", "B23"), "c": (None, None, "B32", "B33", "B22")}
for r, vid in enumerate(["tot", "h", "c"]):
    row = 4 + r
    qu, qhr, q0, q0hr, Nref = src[vid]
    put(ws, f"A{row}", vid, "head")
    put(ws, f"B{row}", "=Исходные!$B$7", "link", "0")
    put(ws, f"C{row}", "=Исходные!$B$21", "link", "0")
    put(ws, f"D{row}", f"=Исходные!{Nref}", "link", "0")
    if vid == "c":
        put(ws, f"E{row}", "=Исходные!B26-Исходные!B27", "link", "0.0")
        put(ws, f"F{row}", "=Исходные!B28-Исходные!B29", "link", "0.0")
    else:
        put(ws, f"E{row}", f"=Исходные!{qu}", "link", "0.0")
        put(ws, f"F{row}", f"=Исходные!{qhr}", "link", "0.0")
    put(ws, f"G{row}", f"=Исходные!{q0}", "link", "0.00")
    put(ws, f"H{row}", f"=Исходные!{q0hr}", "link", "0")
    put(ws, f"I{row}", f"=E{row}*C{row}/1000", "calc", "0.00")
    put(ws, f"J{row}", f"=I{row}/B{row}", "calc", "0.000")
    put(ws, f"K{row}", f"=F{row}*C{row}/(G{row}*D{row}*3600)", "calc", "0.00000")
    put(ws, f"L{row}", f"=D{row}*K{row}", "calc", "0.000")
    put(ws, f"M{row}", "=" + alpha_f(f"D{row}", f"K{row}"), "calc", "0.000")
    put(ws, f"N{row}", f"=5*G{row}*M{row}", "calc", "0.000", fill=FILL_RES)
    put(ws, f"O{row}", f"=3600*K{row}*G{row}/H{row}", "calc", "0.00000")
    put(ws, f"P{row}", f"=D{row}*O{row}", "calc", "0.000")
    put(ws, f"Q{row}", "=" + alpha_f(f"D{row}", f"O{row}"), "calc", "0.000")
    put(ws, f"R{row}", f"=0.005*Q{row}*H{row}", "calc", "0.000", fill=FILL_RES)
notes = [
    "Формулы (п. 5 СП 30.13330.2020):",
    "q_u,m = q_u·U/1000 — суточный расход; для холодной воды q_u^c = q_u^tot − q_u^h, q_hr,u^c = q_hr,u^tot − q_hr,u^h.",
    "q_T = q_u,m / T — среднечасовой расход.",
    "P = q_hr,u·U / (q_0·N·3600) — вероятность действия приборов (п. 5.4); q = 5·q_0·α (п. 5.3).",
    "α = f(NP): табл. Б.2 с линейной интерполяцией y = y1 + (x − x1)·(y2 − y1)/(x2 − x1); при P > 0,1 и N ≤ 200 — табл. Б.1 (интерполяция по N и P).",
    "P_hr = 3600·P·q_0 / q_0,hr (п. 5.9); q_hr = 0,005·α_hr·q_0,hr, м³/ч (п. 5.10).",
    "Для горячей воды N^h — число приборов с горячей водой (без унитазов).",
]
for k, t in enumerate(notes):
    put(ws, f"A{9 + k}", t, "note", align=Alignment(horizontal="left", vertical="center", wrap_text=False))

# =============== В1: гидравлический расчёт ===============
ws = sheet("В1", [5, 40, 8, 7, 9, 9, 9, 8, 9, 9, 9, 9, 9, 10])
put(ws, "A1", "Гидравлический расчёт сети В1 по диктующему направлению (диктующий прибор — душевая сетка над ванной, 11 этаж, Ст.В1-4)", "title", align=LEFT)
put(ws, "B3", "P^c", "head", align=LEFT); put(ws, "C3", "=Расходы!K6", "link", "0.00000")
put(ws, "B4", "q_0^c, л/с", "head", align=LEFT); put(ws, "C4", "=Расходы!G6", "link", "0.00")
put(ws, "B5", "K_м.с (хоз-питьевой водопровод жилого здания)", "head", align=LEFT); put(ws, "C5", 0.3, "in", "0.00")
h = ["№", "Участок", "L, м", "N", "NP", "α", "q, л/с", "DN", "d_расч, мм", "v, м/с", "1000i", "iL, м", "h, м", "v в норме?"]
for j, t in enumerate(h):
    put(ws, f"{get_column_letter(1 + j)}7", t, "head")
DESCR = lambda s: (s.replace("кв. разводка", "квартирная разводка").replace("стояк, эт.", "Ст.В1-4, эт.")
                   .replace("магистраль с2: ст.2 - ст.1", "магистраль Ст.В1-4 – Ст.В1-3")
                   .replace("магистраль: с2 ст.1 - с1 ст.2", "магистраль Ст.В1-3 – Ст.В1-2")
                   .replace("магистраль: с1 ст.2 - тройник у насосной", "магистраль Ст.В1-2 – насосная")
                   .replace("тройник - насосная (после ответвления на ГВС)", "в насосной (после ответвления на ГВС)"))
first = 8
for k, u in enumerate(D["v1"]):
    row = first + k
    put(ws, f"A{row}", k + 1, "calc", "0")
    put(ws, f"B{row}", DESCR(u["imya"]), "in", align=LEFT)
    put(ws, f"C{row}", u["L"], "in", "0.00")
    put(ws, f"D{row}", u["N"], "in", "0")
    put(ws, f"E{row}", f"=D{row}*$C$3", "calc", "0.0000")
    put(ws, f"F{row}", "=" + alpha_f(f"D{row}", "$C$3"), "calc", "0.000")
    put(ws, f"G{row}", f"=5*$C$4*F{row}", "calc", "0.000")
    put(ws, f"H{row}", u["dn"], "in", "0")
    put(ws, f"I{row}", f"=INDEX(VGP_DR,MATCH(H{row},VGP_DN,0))", "calc", "0.0")
    put(ws, f"J{row}", f"=G{row}/1000/(PI()*(I{row}/1000)^2/4)", "calc", "0.00")
    put(ws, f"K{row}", f"=1000*IF(J{row}<1.2,0.000912*J{row}^2/(I{row}/1000)^1.3*(1+0.867/J{row})^0.3,0.00107*J{row}^2/(I{row}/1000)^1.3)", "calc", "0.0")
    put(ws, f"L{row}", f"=K{row}/1000*C{row}", "calc", "0.000")
    put(ws, f"M{row}", f"=L{row}*(1+$C$5)", "calc", "0.000")
    vmax = 1.5 if u["imya"].startswith("кв.") else 1.2
    put(ws, f"N{row}", f'=IF(AND(J{row}>=0.3,J{row}<={vmax}),"да","нет")', "calc")
lastv = first + len(D["v1"]) - 1
put(ws, f"L{lastv + 1}", "Σh, м", "head"); put(ws, f"M{lastv + 1}", f"=SUM(M{first}:M{lastv})", "calc", "0.00", fill=FILL_RES)
put(ws, f"A{lastv + 2}", "Потери по Шевелёву для неновых стальных труб: v < 1,2 м/с — i = 0,000912·v²/d^1,3·(1 + 0,867/v)^0,3; v ≥ 1,2 м/с — i = 0,00107·v²/d^1,3 (d — расчётный диаметр, м). Скорость: магистраль и стояки до 1,2 м/с, подводки до 1,5 м/с.", "note", align=Alignment(wrap_text=False))
SUMH = f"В1!$M${lastv + 1}"
rv = lastv + 4
put(ws, f"B{rv}", "Ввод (общий расход — ГВС готовится в ИТП здания)", "head", align=LEFT)
vv = [("q^tot, л/с", "=Расходы!N4", "0.000", "link"), ("Ø ПЭ100 SDR17, мм", D["vvod"]["dn"], "0", "in"),
      ("d_вн, мм", f"=INDEX(PE_DV,MATCH(C{rv + 2},PE_DN,0))", "0.0", "calc"),
      ("v, м/с", f"=C{rv + 1}/1000/(PI()*(C{rv + 3}/1000)^2/4)", "0.00", "calc"),
      ("Re (ν = 1,31·10⁻⁶ м²/с)", f"=C{rv + 4}*C{rv + 3}/1000/1.31E-6", "0", "calc"),
      ("λ (Свами–Джейн, Δ = 0,01 мм)", f"=0.25/LOG10(0.00001/(3.7*C{rv + 3}/1000)+5.74/C{rv + 5}^0.9)^2", "0.0000", "calc"),
      ("i", f"=C{rv + 6}/(C{rv + 3}/1000)*C{rv + 4}^2/(2*9.81)", "0.0000", "calc"),
      ("Длина ввода L, м", D["L_vvod"], "0.0", "in"),
      ("h_ввод = i·L·(1 + K_м.с), м", f"=C{rv + 7}*C{rv + 8}*(1+$C$5)", "0.00", "calc")]
for k, (t, v, fmt, kind) in enumerate(vv):
    put(ws, f"B{rv + 1 + k}", t, "head", align=LEFT); put(ws, f"C{rv + 1 + k}", v, kind, fmt)
HVV = f"В1!$C${rv + 9}"
ws[f"C{rv + 9}"].fill = FILL_RES

# =============== Напор: счётчики, H_тр, насос ===============
ws = sheet("Напор", [52, 14, 14, 30])
put(ws, "A1", "Счётчики воды, требуемый напор и насосная установка", "title", align=LEFT)
put(ws, "A3", "Общедомовой счётчик (пп. 12.14–12.16)", "head", align=LEFT)
put(ws, "A5", "Среднечасовой расход q_T^tot, м³/ч", "head", align=LEFT); put(ws, "C5", "=Расходы!J4", "link", "0.000")
put(ws, "A6", "Секундный расход q^tot, л/с", "head", align=LEFT); put(ws, "C6", "=Расходы!N4", "link", "0.000")
put(ws, "A7", "Принят DN (наименьший подходящий по табл. 12.1)", "head", align=LEFT); put(ws, "C7", "=INDEX(T121_DN,MATCH(TRUE,T121_OK,0))", "calc", "0", fill=FILL_RES)
put(ws, "A8", "S, м/(л/с)²", "head", align=LEFT); put(ws, "C8", "=INDEX(T121_S,MATCH(C7,T121_DN,0))", "calc", "0.000")
put(ws, "A9", "h_сч = S·q², м", "head", align=LEFT); put(ws, "C9", "=C8*C6^2", "calc", "0.00")
put(ws, "A11", "Квартирный счётчик холодной воды", "head", align=LEFT)
put(ws, "A12", "Приборов в квартире (холодная вода)", "head", align=LEFT); put(ws, "C12", "=Исходные!C15", "link", "0")
put(ws, "A13", "α = f(N·P^c)", "head", align=LEFT); put(ws, "C13", "=" + alpha_f("C12", "Расходы!K6"), "calc", "0.000")
put(ws, "A14", "q = 5·q_0^c·α, л/с", "head", align=LEFT); put(ws, "C14", "=5*Расходы!G6*C13", "calc", "0.000")
put(ws, "A15", "DN 15, S = 14,5; h_сч = S·q², м", "head", align=LEFT); put(ws, "C15", "=14.5*C14^2", "calc", "0.00")
put(ws, "A17", "Требуемый напор (формула H_тр = H_geom + Σh + H_св + ΣH_сч + h_ввод)", "head", align=LEFT)
items = [
    ("Отметка земли у ГВК (отн. 0,000), м", -0.5, "0.000", "in"),
    ("Верх трубы городской сети = земля − (H_пром + 0,5), м", "=C18-(Исходные!B9+0.5)", "0.000", "calc"),
    ("Высота диктующего прибора над полом (душевая сетка), м", 1.95, "0.00", "in"),
    ("Отметка диктующего прибора = (n_эт − 1)·h_эт + z_пр, м", "=(Исходные!B3-1)*Исходные!B6+C20", "0.000", "calc"),
    ("H_geom, м", "=C21-C19", "0.00", "calc"),
    ("Σh по сети В1, м", f"={SUMH}", "0.00", "link"),
    ("H_св (п. 8.21), м", 20, "0.0", "in"),
    ("ΣH_сч, м", "=C9+C15", "0.00", "calc"),
    ("h_ввод, м", f"={HVV}", "0.00", "link"),
    ("H_тр, м", "=C22+C23+C24+C25+C26", "0.00", "calc"),
    ("H_гар, м", "=Исходные!B8", "0.0", "link"),
    ("Напор насосной установки H_нас = H_тр − H_гар, м", "=MAX(0,C27-C28)", "0.00", "calc"),
    ("Подача Q = q^tot, м³/ч", "=Расходы!N4*3.6", "0.00", "calc"),
]
for k, (t, v, fmt, kind) in enumerate(items):
    put(ws, f"A{18 + k}", t, "head", align=LEFT); put(ws, f"C{18 + k}", v, kind, fmt)
for ref in ("C27", "C29", "C30"):
    ws[ref].fill = FILL_RES
put(ws, "A32", "Гидростатический напор у нижнего прибора этажа (смеситель ванны, 0,8 м) — п. 8.22: более 45 м → регулятор давления", "head", align=LEFT)
put(ws, "B33", "Этаж", "head"); put(ws, "C33", "H, м", "head"); put(ws, "D33", "Регулятор давления", "head")
for k in range(int(I["N_ET"])):
    row = 34 + k
    put(ws, f"B{row}", k + 1, "calc", "0")
    put(ws, f"C{row}", f"=$C$28+$C$29-((B{row}-1)*Исходные!$B$6+0.8-$C$19)", "calc", "0.0")
    put(ws, f"D{row}", f'=IF(C{row}>45,"нужен","не нужен")', "calc")

# =============== К1 ===============
ws = sheet("К1", [34, 8, 8, 9, 9, 9, 9, 9, 9, 9, 8, 9, 9, 9, 9, 10, 10])
put(ws, "A1", "Канализация К1: стояки, горизонтальные участки, отметки дворовой сети", "title", align=LEFT)
put(ws, "A3", "Пропускная способность стояков (q^s = q^tot + q_0^s; табл. К.1 — ПВХ Ø110, отводы Ø110 под 45°)", "head", align=LEFT)
for j, t in enumerate(["Стояки", "N", "NP^tot", "α", "q^tot, л/с", "q_0^s, л/с", "q^s, л/с", "Допустимо, л/с", "Вывод"]):
    put(ws, f"{get_column_letter(1 + j)}4", t, "head")
for r, s in enumerate(D["k1_stoyaki"]):
    row = 5 + r
    put(ws, f"A{row}", ["Ст.К1-1, Ст.К1-3", "Ст.К1-2, Ст.К1-4"][r], "in", align=LEFT)
    put(ws, f"B{row}", s["N"], "in", "0")
    put(ws, f"C{row}", f"=B{row}*Расходы!$K$4", "calc", "0.000")
    put(ws, f"D{row}", "=" + alpha_f(f"B{row}", "Расходы!$K$4"), "calc", "0.000")
    put(ws, f"E{row}", f"=5*Расходы!$G$4*D{row}", "calc", "0.000")
    put(ws, f"F{row}", 1.6, "in", "0.0")
    put(ws, f"G{row}", f"=E{row}+F{row}", "calc", "0.000")
    put(ws, f"H{row}", s["q_dop"], "in", "0.00")
    put(ws, f"I{row}", f'=IF(G{row}<=H{row},"обеспечена","НЕ обеспечена")', "calc")

put(ws, "A8", "Горизонтальные участки: q^sL = q_hr^tot/3,6 + K_s·q_0^s1 (п. 5.7); подбор по формуле Павловского (как таблицы Лукиных), n = 0,014", "head", align=LEFT)
put(ws, "A9", "P_hr^tot", "head", align=LEFT); put(ws, "B9", "=Расходы!O4", "link", "0.00000")
put(ws, "C9", "q_0,hr^tot", "head"); put(ws, "D9", "=Расходы!H4", "link", "0")
put(ws, "E9", "q_0^s1, л/с", "head"); put(ws, "F9", 1.1, "in", "0.0")
put(ws, "G9", "n", "head"); put(ws, "H9", 0.014, "in", "0.000")
hk = ["Участок", "L, м", "N", "NP_hr", "α_hr", "q_hr, м³/ч", "K_s", "q^sL, л/с", "d, мм", "i", "K", "h/d", "V, м/с", "V√(h/d)", "Условие (2.3)", "Лоток: начало", "Лоток: конец"]
for j, t in enumerate(hk):
    put(ws, f"{get_column_letter(1 + j)}11", t, "head")
names = ["Ст.К1-4 – Ст.К1-3 (чугун SML)", "Ст.К1-3 – КК-1, выпуск К1-2 (чугун SML)", "КК-1 – КК-2 (ПЭ гофр. Ø160)", "КК-2 – ККК (ПЭ гофр. Ø160)", "ККК – ГКК (ПЭ гофр. Ø160)"]
kk = [0.6, 0.6, 0.5, 0.5, 0.5]
for r, u in enumerate(D["k1"]):
    row = 12 + r
    put(ws, f"A{row}", names[r], "in", align=LEFT)
    put(ws, f"B{row}", u["L"], "in", "0.00")
    put(ws, f"C{row}", u["N"], "in", "0")
    put(ws, f"D{row}", f"=C{row}*$B$9", "calc", "0.000")
    put(ws, f"E{row}", "=" + alpha_f(f"C{row}", "$B$9"), "calc", "0.000")
    put(ws, f"F{row}", f"=0.005*E{row}*$D$9", "calc", "0.000")
    put(ws, f"G{row}", "=" + ks_f(f"C{row}", f"B{row}"), "calc", "0.00")
    put(ws, f"H{row}", f"=F{row}/3.6+G{row}*$F$9", "calc", "0.00")
    put(ws, f"I{row}", u["d"], "in", "0")
    put(ws, f"J{row}", u["i"], "in", "0.000")
    put(ws, f"K{row}", kk[r], "in", "0.0")
    col = get_column_letter(2 + r)   # столбец на листе «Павловский»
    put(ws, f"L{row}", (f"=IFERROR(INDEX(Павловский!$A$6:$A$91,MATCH(H{row},Павловский!{col}$6:{col}$91,1))"
                        f"+(H{row}-INDEX(Павловский!{col}$6:{col}$91,MATCH(H{row},Павловский!{col}$6:{col}$91,1)))*0.01"
                        f"/(INDEX(Павловский!{col}$6:{col}$91,MATCH(H{row},Павловский!{col}$6:{col}$91,1)+1)"
                        f"-INDEX(Павловский!{col}$6:{col}$91,MATCH(H{row},Павловский!{col}$6:{col}$91,1))),\"вне таблицы\")"), "calc", "0.00")
    put(ws, f"M{row}", "=" + pavl_v(f"L{row}", f"(I{row}/1000)", f"J{row}", "$H$9"), "calc", "0.00")
    put(ws, f"N{row}", f"=M{row}*SQRT(L{row})", "calc", "0.00")
    put(ws, f"O{row}", f'=IF(AND(N{row}>=K{row},M{row}>=0.7,L{row}>=0.3),"выполнено","безрасчётный, i ≥ 1/d")', "calc")
put(ws, "A18", "Если условие V√(h/d) ≥ K не выполнимо из-за малого расхода и стояки уже объединены в один выпуск, участок безрасчётный: i ≥ 1/d (п. 19.1 СП 30). Принято: внутри здания i = 0,02; дворовая сеть d150 — i = 0,008 (СП 32).", "note", align=Alignment(wrap_text=False))

put(ws, "A20", "Отметки (абсолютные), м", "head", align=LEFT)
L = D["lotok"]; Z = D["zeml"]
el = [("0,000 здания", D["Z0_ABS"], "0.00", "in"), ("Лоток выпуска у стены (отн.)", -2.0, "0.000", "in"),
      ("Лоток выпуска у стены (абс.)", "=B21+B22", "0.00", "calc"), ("Длина выпуска от стены до КК-1, м", 5.0, "0.0", "in"),
      ("Лоток Ø100 при входе в КК-1", "=B23-J13*B24", "0.00", "calc"),
      ("Лоток Ø150 в КК-1 (шелыга в шелыгу)", "=B25+I13/1000-I14/1000", "0.00", "calc")]
for k, (t, v, fmt, kind) in enumerate(el):
    put(ws, f"A{21 + k}", t, "head", align=LEFT); put(ws, f"B{21 + k}", v, kind, fmt)
# начало/конец внутренних участков
put(ws, "Q13", "=B25", "calc", "0.00"); put(ws, "P13", "=Q13+J13*B13", "calc", "0.00")
put(ws, "Q12", "=P13", "calc", "0.00"); put(ws, "P12", "=Q12+J12*B12", "calc", "0.00")
put(ws, "P14", "=B26", "calc", "0.00"); put(ws, "Q14", "=P14-J14*B14", "calc", "0.00")
put(ws, "P15", "=Q14", "calc", "0.00"); put(ws, "Q15", "=P15-J15*B15", "calc", "0.00")
put(ws, "P16", "=Q15", "calc", "0.00"); put(ws, "Q16", "=P16-J16*B16", "calc", "0.00")
put(ws, "A28", "Колодцы дворовой сети", "head", align=LEFT)
for j, t in enumerate(["Колодец", "Земля", "Лоток", "Глубина", "H_0 = max(H_пр − 0,3; 0,7 + d)", "Проверка"]):
    put(ws, f"{get_column_letter(1 + j)}29", t, "head")
wells = [("КК-1", Z["КК-1"], "=P14"), ("КК-2", Z["КК-2"], "=P15"), ("ККК", Z["ККК"], "=P16"), ("ГКК", Z["ГКК"], "=Q16")]
for k, (wn, zv, lf) in enumerate(wells):
    row = 30 + k
    put(ws, f"A{row}", wn, "in"); put(ws, f"B{row}", zv, "in", "0.00"); put(ws, f"C{row}", lf, "calc", "0.00")
    put(ws, f"D{row}", f"=B{row}-C{row}", "calc", "0.00")
    put(ws, f"E{row}", "=MAX(Исходные!$B$9-0.3,0.7+$I$14/1000)", "calc", "0.00")
    put(ws, f"F{row}", f'=IF(D{row}>=E{row},"достаточна","мала")', "calc")
put(ws, "A35", "Лоток городского коллектора Ø400 в ГКК (по месту, принят)", "head", align=LEFT); put(ws, "B35", D["Z_GKK_GOR"], "in", "0.00")
put(ws, "A36", "Превышение лотка дворовой трубы над шелыгой коллектора, м", "head", align=LEFT); put(ws, "B36", "=C33-(B35+0.4)", "calc", "0.00")

# =============== Павловский: вспомогательная таблица q(h/d) ===============
ws = sheet("Павловский", [8, 11, 11, 11, 11, 11])
put(ws, "A1", "Вспомогательная таблица: расход q, л/с, при наполнении h/d для участков К1 (формула Шези с C по Павловскому)", "title", align=LEFT)
put(ws, "A3", "d, м", "head"); put(ws, "A4", "i", "head"); put(ws, "A5", "h/d", "head")
for r in range(5):
    col = get_column_letter(2 + r)
    put(ws, f"{col}3", f"=К1!I{12 + r}/1000", "link", "0.000")
    put(ws, f"{col}4", f"=К1!J{12 + r}", "link", "0.000")
    put(ws, f"{col}5", f"=К1!A{12 + r}", "link", align=Alignment(wrap_text=True))
for k in range(86):
    row = 6 + k
    put(ws, f"A{row}", round(0.05 + 0.01 * k, 2), "calc", "0.00")
    for r in range(5):
        col = get_column_letter(2 + r)
        put(ws, f"{col}{row}", "=" + pavl_q(f"$A{row}", f"{col}$3", f"{col}$4", "К1!$H$9"), "calc", "0.000")

# =============== Справка ===============
ws = sheet("Справка", [110])
wb.move_sheet("Справка", offset=-wb.index(wb["Справка"]))
txt = [
    "Расчёт систем внутреннего водопровода В1 и канализации К1 жилого здания — курсовой проект, вариант 3 (НИУ МГСУ, кафедра «Водоснабжение и водоотведение»)",
    "",
    "Как пользоваться:",
    "1. Жёлтые ячейки с синим шрифтом — исходные данные; их можно менять. Всё остальное считается формулами.",
    "2. Лист «Исходные»: этажность, секции, заселённость, типы квартир и приборы, тип водопотребителей (выпадающий список по табл. А.2).",
    "3. Лист «Расходы»: суточные, среднечасовые, секундные и часовые расходы общей, горячей и холодной воды (как на занятиях).",
    "4. Лист «В1»: гидравлический расчёт по диктующему направлению — длины, числа приборов и диаметры вводятся, α, q, v, 1000i, потери считаются.",
    "5. Лист «Напор»: подбор счётчиков, требуемый напор, напор и подача насосной установки, проверка гидростатического напора по этажам.",
    "6. Лист «К1»: стояки, горизонтальные участки (K_s, q^sL, h/d, V, условие незасоряемости), отметки лотков и глубина колодцев.",
    "7. Листы «ТаблА2», «ТаблБ1», «ТаблБ2», «Табл5_1», «Табл12_1», «Трубы», «Павловский» — справочные таблицы СП и вспомогательные расчёты.",
    "",
    "Нормативная база: СП 30.13330.2020 «Внутренний водопровод и канализация зданий» (с изменениями № 1–5); СП 32.13330.2018 «Канализация. Наружные сети и сооружения» (с изменениями);",
    "Ф.А. Шевелёв, А.Ф. Шевелёв «Таблицы для гидравлического расчёта водопроводных труб»; А.А. Лукиных, Н.А. Лукиных «Таблицы для гидравлического расчёта канализационных сетей и дюкеров».",
    "",
    "α определяется по табл. Б.2 (при P > 0,1 и N ≤ 200 — по табл. Б.1) с линейной интерполяцией между строками: y = y1 + (x − x1)·(y2 − y1)/(x2 − x1).",
    "Расчёт канализации по формуле Павловского сверен с таблицами Лукиных (d = 100, 150, 250 мм, 25 точек, расхождение ≤ 0,7 %);",
    "потери в стальных трубах — с табл. 1 Шевелёва (DN15–65, 32 точки, 1000i ≤ 0,3 %).",
    "Условные обозначения: синий — исходные данные; чёрный — формулы; зелёный — ссылки на другие листы; светло-зелёная заливка — основные результаты.",
]
for k, t in enumerate(txt):
    c = ws.cell(row=1 + k, column=1, value=t)
    c.font = F_TITLE if k == 0 else Font(name=FONT, size=11)
    c.alignment = Alignment(wrap_text=True, vertical="top")

ORDER = ["Справка", "Исходные", "Расходы", "В1", "Напор", "К1", "ТаблА2", "ТаблБ1", "ТаблБ2", "Табл5_1", "Табл12_1", "Трубы", "Павловский"]
wb._sheets = [wb[n] for n in ORDER]
wb.active = 1
for w in wb.worksheets:
    w.sheet_properties.pageSetUpPr.fitToPage = True
    w.page_setup.orientation = "landscape"
    w.page_setup.fitToWidth = 1
    w.page_setup.fitToHeight = 0
wb.save(OUT)
print("записано:", OUT)
