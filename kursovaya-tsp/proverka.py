"""Сквозная проверка: Excel и DXF против точного расчёта raschet.py."""
import ezdxf, openpyxl
import raschet as R

ok = True
# 1. Excel: каждое значение таблиц совпадает с расчётом в Fraction
wb = openpyxl.load_workbook("Объёмы_планировки_вариант2.xlsx", data_only=True)
K = wb["Исходные данные"]["B4"].value
by = {g["name"]: g for g in R.FIGS}
n = 0
seen = set()
for row in wb["Объёмы"].iter_rows(min_row=6, max_row=20):   # строки квадратов 1..15
    for start in (0, 4):                                      # ПВ: A..D, ПН: E..I
        name = row[start].value
        if name == "—":
            continue
        g = by[name]
        seen.add(name)
        want = [g["F"], g["hcp"], g["V"]] + ([g["V"] / K] if g["sign"] > 0 else [])
        for c, w in zip(row[start + 1:], want):
            n += 1
            if c.value is None or abs(c.value - float(w)) > 1e-9:
                ok = False; print("Excel расходится:", name, c.coordinate, c.value, float(w))
if seen != set(by): ok = False; print("в таблице не все фигуры:", set(by) - seen)
exc = [float(z["x1"]) for z in sorted(R.ZP, key=lambda z: (z["p1"], z["p2"]))]
got = [wb["ЛНР"][f"G{r}"].value for r in range(5, 5 + len(exc))]
if any(abs(a - b) > 1e-9 for a, b in zip(exc, got)): ok = False; print("ЛНР в Excel расходится")
print(f"Excel: сверено {n} значений объёмов и {len(exc)} точек нуля")

# 2. Отметки в Excel = отметки варианта 2
marks = [wb["Исходные данные"][f"B{8 + k}"].value for k in range(1, 25)]
if marks != [float(v) for v in R.H]: ok = False; print("Отметки в Excel не совпадают")

# 3. DXF: ЛНР проходит ровно через все точки нулевых работ, подписи на месте
doc = ezdxf.readfile("План_ЛНР_вариант2.dxf")
msp = doc.modelspace()
lnr = [e for e in msp if e.dxf.layer == "ЛНР"][0]
verts = {(round(x, 6), round(y, 6)) for x, y, *_ in lnr.get_points()}
zp = {(round(float(z["pt"][0]), 6), round(float(z["pt"][1]), 6)) for z in R.ZP}
if verts != zp: ok = False; print("ЛНР в DXF не совпадает с точками нуля")
texts = [e.plain_text() for e in msp if e.dxftype() == "MTEXT"]
for g in R.FIGS:
    if g["name"] not in texts: ok = False; print("нет подписи фигуры", g["name"])
fmt = lambda v: ("+" if v > 0 else "−") + f"{abs(float(v)):.2f}".replace(".", ",")
for v in R.H:
    if fmt(v) not in texts: ok = False; print("нет отметки", fmt(v))
bad_styles = {e.dxf.style for L in (msp, doc.paperspace("Лист 1"), *doc.blocks)
              for e in L if e.dxftype() in ("TEXT", "MTEXT")} - {"ГОСТ тип Б"}
if bad_styles: ok = False; print("текст не ГОСТ тип Б:", bad_styles)
if doc.audit().has_errors: ok = False; print("аудит DXF нашёл ошибки")
print("DXF: ЛНР через", len(zp), "точек нуля; фигур", len(R.FIGS), "; стили текста ок" if not bad_styles else "")
print("ВСЁ СХОДИТСЯ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ")
