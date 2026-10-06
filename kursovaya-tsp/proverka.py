"""Сквозная проверка: Excel и DXF против точного расчёта raschet.py."""
import ezdxf, openpyxl
import raschet as R
import kotlovan as KT

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
fmt = lambda v: ("+" if v > 0 else "-") + f"{abs(float(v)):.2f}".replace(".", ",")
for v in R.H:
    if fmt(v) not in texts: ok = False; print("нет отметки", fmt(v))
bad_styles = {e.dxf.style for L in (msp, doc.paperspace("Лист 1"), doc.paperspace("Лист 2"), *doc.blocks)
              for e in L if e.dxftype() in ("TEXT", "MTEXT")} - {"ГОСТ тип Б"}
if bad_styles: ok = False; print("текст не ГОСТ тип Б:", bad_styles)
if doc.audit().has_errors: ok = False; print("аудит DXF нашёл ошибки")

# 4. Совместимость с nanoCAD/AutoCAD (ошибки, найденные при открытии в nanoCAD)
psps = [doc.paperspace("Лист 1"), doc.paperspace("Лист 2")]
for psp, need in zip(psps, (2, 3)):
    vps = sorted((e.dxf.status, e.dxf.id) for e in psp if e.dxftype() == "VIEWPORT")
    if not vps or vps[0][0] != 1 or len(vps) < need:
        ok = False; print("нет главного видового экрана листа или рабочих экранов:", psp.name, vps)
layouts = (msp, *psps, *doc.blocks)
if any(e.dxftype() == "TEXT" for L in layouts for e in L):
    ok = False; print("есть однострочный TEXT - nanoCAD сдвигает его при центровке")
SAFE = set(map(chr, range(32, 127))) | {chr(c) for c in range(0x410, 0x450)} | set("ЁёН№")
bad = {ch for L in layouts for e in L if e.dxftype() == "MTEXT"
       for ch in e.plain_text() if ch not in SAFE and ch != "\n"}
if bad: ok = False; print("символы, которых может не быть в шрифте ГОСТ:", bad)
print("DXF: ЛНР через", len(zp), "точек нуля; фигур", len(R.FIGS), "; стили текста ок" if not bad_styles else "")

# 5. Котлован: Excel (формулы после пересчёта) = kotlovan.py; контуры в DXF = расчёту
w4 = wb["Котлован"]
got = {w4[f"B{r}"].value: w4[f"C{r}"].value for r in range(5, w4.max_row + 1) if w4[f"B{r}"].value}
want = {"hр": KT.HR, "hк": KT.HK, "m": KT.M, "l": KT.L_OTK, "Fк.н": KT.F_KN, "Fк.в": KT.F_KV,
        "Fк.с.п": KT.F_ST, "Fф.п": KT.F_FP, "Fб.п": KT.F_BP, "Vпан": KT.V_PAN, "Vк": KT.V_K,
        "Vподс": KT.V_PODS, "Vб.п": KT.V_BP, "Vф.п": KT.V_FP, "Vк.с.п": KT.V_KSP, "Vп.ч": KT.V_PCH, "Vо.з": KT.V_OZ}
for key, w in want.items():
    if got.get(key) is None or abs(got[key] - float(w)) > 1e-6:
        ok = False; print("Котлован в Excel расходится:", key, got.get(key), float(w))
if got.get("hср.углов") is None or abs(got["hср.углов"] - float(sum(KT.H_CORNERS) / 6)) > 1e-9:
    ok = False; print("среднее рабочих отметок по углам расходится")
if [w4[f"C{r}"].value for r in range(5, 80) if w4[f"A{r}"].value == "Котлован в зоне"] != ["насыпи"]:
    ok = False; print("зона котлована не «насыпи»")
w5 = wb["Сводный баланс"]
if abs(w5["C8"].value - KT.BALANCE) > 1e-6: ok = False; print("баланс расходится", w5["C8"].value, KT.BALANCE)
pit = [e for e in msp if e.dxf.layer == "Котлован_низ" and e.dxftype() == "LWPOLYLINE"]
niz = {(round(float(x), 6), round(float(y), 6)) for x, y in KT.NIZ}
if not any({(round(x, 6), round(y, 6)) for x, y, *_ in e.get_points()} == niz for e in pit):
    ok = False; print("подошва котлована на плане 1:2000 не совпадает с расчётом")
top = [e for e in msp if e.dxf.layer == "Котлован" and e.dxftype() == "LWPOLYLINE"]
verh = {(round(float(x), 6), round(float(y), 6)) for x, y in KT.VERH}
if not any(verh <= {(round(x, 6), round(y, 6)) for x, y, *_ in e.get_points()} for e in top):
    ok = False; print("бровка котлована на плане 1:2000 не совпадает с расчётом")
print(f"Котлован: сверено {len(want) + 2} величин Excel, контуры в DXF; баланс {KT.BALANCE:.2f} м3")
print("ВСЁ СХОДИТСЯ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ")
