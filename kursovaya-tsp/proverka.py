"""Сквозная проверка: Excel и DXF против точного расчёта raschet.py, kotlovan.py, balans.py."""
import ezdxf, openpyxl
from fractions import Fraction as Fr
import raschet as R
import kotlovan as KT
import balans as B

ok = True
wb = openpyxl.load_workbook("Объёмы_планировки_вариант2.xlsx", data_only=True)
K = wb["Исходные данные"]["B4"].value


def bad(*msg):
    global ok
    ok = False
    print(*msg)


def near(a, b, tol=1e-6):
    return a is not None and abs(a - float(b)) <= tol


def check_excel(tag, P, k, b, s_lnr, s_vol, s_pit, s_bal):
    """Листы одного состояния (черновик или окончательные отметки) против расчёта."""
    n = 0
    by = {g["name"]: g for g in P["FIGS"]}
    seen = set()
    for row in wb[s_vol].iter_rows(min_row=6, max_row=20):    # строки квадратов 1..15
        for start in (0, 4):                                      # ПВ: A..D, ПН: E..I
            name = row[start].value
            if name == "—":
                continue
            g = by[name]
            seen.add(name)
            want = [g["F"], g["hcp"], g["V"]] + ([g["V"] / K] if g["sign"] > 0 else [])
            for c, w in zip(row[start + 1:], want):
                n += 1
                if not near(c.value, w, 1e-9):
                    bad(tag, "Excel расходится:", name, c.coordinate, c.value, float(w))
    if seen != set(by): bad(tag, "в таблице не все фигуры:", set(by) - seen)
    exc = [float(z["x1"]) for z in sorted(P["ZP"], key=lambda z: (z["p1"], z["p2"]))]
    got = [wb[s_lnr][f"G{r}"].value for r in range(5, 5 + len(exc))]
    if len(got) != len(exc) or any(not near(g_, e, 1e-9) for g_, e in zip(got, exc)):
        bad(tag, "ЛНР в Excel расходится")
    # откосы по контуру: строки 25 (выемка), 26 (насыпь); итоги F31 (Vв), F32 (Vн)
    w3 = wb[s_vol]
    for r, sgn in ((25, -1), (26, 1)):
        s = P["SLOPES"][sgn]
        for col, w in (("B", s["sum_h"]), ("C", s["n"]), ("D", s["L"]), ("E", s["m"]), ("F", s["V"])):
            n += 1
            if not near(w3[f"{col}{r}"].value, w, 1e-9): bad(tag, "откосы расходятся:", col, r, w3[f"{col}{r}"].value, float(w))
    if not near(w3["F31"].value, P["VV"], 1e-9) or not near(w3["F32"].value, P["VN"], 1e-9):
        bad(tag, "итоги с откосами расходятся:", w3["F31"].value, float(P["VV"]), w3["F32"].value, float(P["VN"]))
    # котлован
    w4 = wb[s_pit]
    got = {w4[f"B{r}"].value: w4[f"C{r}"].value for r in range(5, w4.max_row + 1) if w4[f"B{r}"].value}
    want = {"hр": k["HR"], "hр.сл": KT.H_RSL, "hк": k["HK"], "m": k["M"], "l": k["L_OTK"], "Fк.н": k["F_KN"],
            "Fк.в": k["F_KV"], "Fк.с.п": k["F_ST"], "Fф.п": k["F_FP"], "Fб.п": k["F_BP"], "Vпан": k["V_PAN"],
            "Vк": k["V_K"], "Vподс": k["V_PODS"], "Vб.п": k["V_BP"], "Vф.п": k["V_FP"], "Vк.с.п": k["V_KSP"],
            "Vп.ч": k["V_PCH"], "Vо.з": k["V_OZ"], "hср.углов": sum(k["H_CORNERS"]) / 6}
    for key, w in want.items():
        n += 1
        if not near(got.get(key), w): bad(tag, "котлован в Excel расходится:", key, got.get(key), float(w))
    if [w4[f"C{r}"].value for r in range(5, 90) if w4[f"A{r}"].value == "Котлован в зоне"] != \
            ["насыпи" if k["IN_FILL"] else "выемки"]:
        bad(tag, "зона котлована в Excel не та")
    # сводный баланс
    w5 = wb[s_bal]
    for ref, w in (("C7", b["SUM_V"]), ("E7", b["SUM_NK"]), ("C8", b["BALANCE"]), ("D12", b["F_PL"]),
                   ("D13", b["DH_EXACT"]), ("D14", b["DH"])):
        n += 1
        if not near(w5[ref].value, w): bad(tag, "баланс в Excel расходится:", ref, w5[ref].value, float(w))
    print(f"Excel, {tag}: сверено {n} значений, {len(exc)} точек нуля; баланс {b['BALANCE']:.2f} м3"
          f" ({b['PCT']:.2f} %)")


check_excel("черновик", R.P0, KT.K0, B.B0, "ЛНР", "Объёмы", "Котлован", "Сводный баланс")
check_excel("окончательные", B.P1, B.K1, B.B1, "ЛНР (оконч.)", "Объёмы (оконч.)", "Котлован (оконч.)",
            "Баланс (оконч.)")

# 2. Отметки в Excel: черновик = вариант 2; окончательные = черновик + Δh
marks = [wb["Исходные данные"][f"B{8 + k}"].value for k in range(1, 25)]
if marks != [float(v) for v in R.H]: bad("Отметки в Excel не совпадают")
marks1 = [wb["Отметки (оконч.)"][f"D{8 + k}"].value for k in range(1, 25)]
if any(not near(a, b_, 1e-12) for a, b_ in zip(marks1, B.H1)): bad("Окончательные отметки в Excel не совпадают")
if not B.B1["OK"]: bad("после поправки Δh баланс больше 5 %:", B.B1["PCT"])

# 2а. Грунт котлована, распределение, средняя дальность (табл. 3-6) = raspredelenie.py
import raspredelenie as RS
w7 = wb["Табл. 3 котлован"]
for ref, w in (("C5", RS.V_K * RS.K_P), ("E5", RS.V_PIT_FILL * RS.K_P), ("F5", RS.V_PIT_FILL * RS.K_OR),
               ("E7", RS.V_OZ / RS.K_OR * RS.K_P), ("F7", RS.V_OZ), ("F8", RS.V_PODS), ("F9", RS.V_OZ)):
    if not near(w7[ref].value, w, 1e-6): bad("табл. 3 расходится:", ref, w7[ref].value, float(w))
if not near(w7["C10"].value, w7["E10"].value, 1e-6): bad("табл. 3: Σ с kр по разработке и укладке не равны")
w8 = wb["Табл. 4 распределение"]
nrow = 7 + len(RS.FILL)
col_chk = chr(ord("C") + len(RS.CUT) + 2)          # столбец «Σ по строке − объём» - за выемками, котлованом, недостачей
chk = [w8[f"{col_chk}{r}"].value for r in range(7, nrow)] + [c.value for c in w8[nrow + 1][2:2 + len(RS.CUT) + 2]]
if len(chk) != len(RS.FILL) + len(RS.CUT) + 2: bad("табл. 4: не все проверочные ячейки")
if any(v is None or abs(v) > 1e-6 for v in chk): bad("табл. 4: суммы по строкам или столбцам не сходятся", chk)
if RS.crossings(): bad("стрелки землеройно-транспортных машин пересекаются:", RS.crossings())
for sh, t in (("Табл. 5 скрепер", RS.T5), ("Табл. 6 самосвал", RS.T6)):
    if not near(wb[sh]["C15"].value, t[4], 1e-6): bad(sh, "Lср расходится:", wb[sh]["C15"].value, t[4])
print(f"Табл. 3-6: котлован -> насыпь {float(RS.V_PIT_FILL):.2f} м3, недостача {float(sum(RS.SHORT.values())):.2f} м3,"
      f" Lср ЗТМ {RS.T5[4]:.2f} м, самосвалы {RS.T6[4]:.2f} м")

# 2б. Комплекты машин (п. 2.3: табл. 7, экскаватор, самосвалы) = mashiny.py
import mashiny as MS
w10, n7 = wb["Табл. 7 варианты"], 0
for col, var, starts in (("C", MS.VAR1, (13, 20, 26)), ("G", MS.VAR2, (13, 20, 26, 32, 38))):
    if len(var["rows"]) != len(starts): bad("табл. 7: число машин не то", col)
    for r0, row in zip(starts, var["rows"]):
        for dr, key in enumerate(("V", "H", "M", "Vdn", "n"), start=1):
            n7 += 1
            if not near(w10[f"{col}{r0 + dr}"].value, row[key], 1e-6):
                bad("табл. 7 расходится:", f"{col}{r0 + dr}", row["mach"][0], key, w10[f"{col}{r0 + dr}"].value,
                    float(row[key]))
    for r, key in ((45, "SUM_M"), (46, "V_PER_M"), (47, "M_PER_V"), (48, "DAYS")):
        n7 += 1
        if not near(w10[f"{col}{r}"].value, var[key], 1e-6): bad("табл. 7: итог расходится", col, r, key)
if f"вариант {MS.VAR_OK}" not in (w10["A50"].value or ""): bad("табл. 7: в Excel принят другой вариант")
w11 = wb["2.3.2 Экскаватор, самосвалы"]
for ref, w in (("C12", MS.EX_NAME), ("C14", MS.H_EX), ("C16", MS.H_KOP), ("C18", MS.M_EX), ("C25", MS.V_GRK),
               ("C26", MS.M_KOV)):
    n7 += 1
    v = w11[ref].value
    if (v != w) if isinstance(w, str) else not near(v, w, 1e-9): bad("2.3.2 расходится:", ref, v, w)
for k, t in enumerate(MS.TRUCKS):
    r = 34 + k
    for col, key in (("I", "n"), ("O", "Tc"), ("Q", "N"), ("S", "Ha")):
        n7 += 1
        if not near(w11[f"{col}{r}"].value, t[key], 1e-9): bad("самосвалы расходятся:", t["name"], key)
r_sel = 34 + len(MS.TRUCKS) + 1
if w11[f"C{r_sel}"].value != MS.TR["name"] or w11[f"C{r_sel + 2}"].value != MS.TR["N"]:
    bad("принят другой самосвал:", w11[f"C{r_sel}"].value, MS.TR["name"])
if MS.EX_HK < MS.H_KOP: bad("экскаватор не достаёт до дна котлована")
if not MS.KOVSH_PRIL6 or f"{float(MS.V_KOV):g}".replace(".", ",") not in MS.KOVSH_PRIL6:
    bad("ковш экскаватора не по прил. 6:", MS.KOVSH_PRIL6)
print(f"П. 2.3: сверено {n7} значений; принят вариант {MS.VAR_OK}, экскаватор {MS.EX_NAME},"
      f" самосвалы {MS.TR['name']} x {MS.TR['N']}")

# 3. DXF: ЛНР проходит ровно через все точки нулевых работ, подписи на месте -
#    на черновике (лист 1, y как есть) и на окончательном плане (лист 2, сдвиг OY2)
class MC:                       # как в make_dxf.py: сдвиг окончательного плана в модели, Мв на разрезах
    OY2, VS, OY0 = -1000.0, 20.0, -4000.0


doc = ezdxf.readfile("План_ЛНР_вариант2.dxf")
msp = doc.modelspace()
texts = [e.plain_text() for e in msp if e.dxftype() == "MTEXT"]
pt = lambda x, y: (round(float(x), 6), round(float(y), 6))


def fmt(v):
    """Отметка на чертеже - до 0,01 м, половина вверх (как fmt в make_dxf.py)."""
    q = int(abs(Fr(v)) * 100 + Fr(1, 2))
    return ("+" if v > 0 else "-") + f"{q // 100},{q % 100:02d}"


in_plan = lambda y, oy: oy - 60 <= y <= oy + 360
for tag, P, oy, extra in (("черновик", R.P0, 0.0, [500.0, 300.0]), ("окончательный", B.P1, MC.OY2, []),
                         ("первый чертёж", R.P0, MC.OY0, [500.0, 300.0])):
    zp = {pt(z["pt"][0], float(z["pt"][1]) + oy) for z in P["ZP"]}
    if not any({pt(x, y) for x, y, *_ in e.get_points()} == zp for e in msp if e.dxf.layer == "ЛНР"):
        bad(tag, "ЛНР в DXF не совпадает с точками нуля")
    plan_texts = [e.plain_text() for e in msp if e.dxftype() == "MTEXT" and in_plan(e.dxf.insert.y, oy)]
    for v in P["H"]:
        if fmt(v) not in plan_texts: bad(tag, "нет отметки", fmt(v))
    # размеры: до каждой точки нуля - один (x1 или x2), на черновике ещё габариты 500 и 300
    meas = sorted(round(d.get_measurement(), 6) for d in msp.query("DIMENSION")
                  if d.dxf.dimstyle == "М1-2000" and in_plan(d.dxf.defpoint.y, oy))
    for v in extra:
        if v in meas: meas.remove(v)
        else: bad(tag, "нет габаритного размера", v)
    want = [{round(float(z["x1"]), 6), round(float(z["x2"]), 6)} for z in P["ZP"]]
    for w in want:
        hit = next((m for m in meas if m in w), None)
        if hit is None: bad(tag, "нет размера до точки нуля", w)
        else: meas.remove(hit)
    if meas: bad(tag, "лишние размеры на плане:", meas)
for g in R.FIGS:
    if g["name"] not in texts: bad("нет подписи фигуры", g["name"])
hk = f"hк = {round(float(B.K1['HK']) * 1000)}"
if sum(1 for e in msp if e.dxftype() == "DIMENSION" and e.dxf.get("text", "").replace("<>", "") == "hк = "
       and abs(e.get_measurement() * 1000 / MC.VS - float(B.K1["HK"]) * 1000) < 0.5) != 2:
    bad("на разрезах нет двух размеров", hk)
LAYOUT_NAMES = ("Лист 1", "Лист 2", "Лист 3", "Лист 4", "Лист 1 (первый)")
bad_styles = {e.dxf.style for L in (msp, *(doc.paperspace(n) for n in LAYOUT_NAMES), *doc.blocks)
              for e in L if e.dxftype() in ("TEXT", "MTEXT")} - {"ГОСТ тип Б"}
if bad_styles: bad("текст не ГОСТ тип Б:", bad_styles)
if doc.audit().has_errors: bad("аудит DXF нашёл ошибки")

# 4. Совместимость с nanoCAD/AutoCAD (ошибки, найденные при открытии в nanoCAD)
psps = [doc.paperspace(n) for n in LAYOUT_NAMES]
for psp in psps:
    vps = sorted((e.dxf.status, e.dxf.id) for e in psp if e.dxftype() == "VIEWPORT")
    if not vps or vps[0][0] != 1 or len(vps) < 2:
        bad("нет главного видового экрана листа или рабочего экрана:", psp.name, vps)
layouts = (msp, *psps, *doc.blocks)
if any(e.dxftype() == "TEXT" for L in layouts for e in L):
    bad("есть однострочный TEXT - nanoCAD сдвигает его при центровке")
SAFE = set(map(chr, range(32, 127))) | {chr(c) for c in range(0x410, 0x450)} | set("ЁёН№")
chars = {ch for L in layouts for e in L if e.dxftype() == "MTEXT"
         for ch in e.plain_text() if ch not in SAFE and ch != "\n"}
if chars: bad("символы, которых может не быть в шрифте ГОСТ:", chars)
print("DXF: ЛНР и отметки - черновик и окончательный план; листов", len(psps),
      "; стили текста ок" if not bad_styles else "")

# 4а. Оформление для AutoCAD (ошибки, найденные при печати из AutoCAD 2026)
for name in ("ГОСТ тип Б", "Standard"):
    if doc.styles.get(name).dxf.font.lower() != "gost_b.ttf":
        bad(f"стиль {name} не на шрифте GOST type B (GOST_B.TTF)")
for psp in psps:
    d = psp.dxf_layout.dxf
    if (d.plot_configuration_file, d.paper_size) != ("DWG To PDF.pc3", "ISO_full_bleed_A3_(420.00_x_297.00_MM)"):
        bad("параметры печати не A3 DWG To PDF:", psp.name, d.plot_configuration_file, d.paper_size)
    if any(v.dxf.id == 1 and v.dxf.layer != "0" for v in psp.query("VIEWPORT")):
        bad("главный видовой экран не на слое 0 (AUDIT AutoCAD):", psp.name)
lts = {e.dxf.linetype for e in msp if e.dxf.hasattr("linetype")} - {"ByLayer", "BYLAYER", "Continuous"}
if not lts <= {"ГОСТ_штрихпунктирная", "ГОСТ_штриховая"} or doc.header.get("$PSLTSCALE") != 1:
    bad("типы линий не по ГОСТ 2.303 в мм листа:", lts, doc.header.get("$PSLTSCALE"))
if any(e.dxf.get("ltscale", 1) != 1 for e in msp):
    bad("у объектов свой масштаб типа линии - штрихи на листе будут не той длины")

# 5. Котлован на планах: контуры в DXF = расчёту (черновик - K0, окончательный - K1)
for tag, k, oy in (("черновик", KT.K0, 0.0), ("окончательный", B.K1, MC.OY2)):
    niz = {pt(x, float(y) + oy) for x, y in k["NIZ"]}
    verh = {pt(x, float(y) + oy) for x, y in k["VERH"]}
    polys = [{pt(x, y) for x, y, *_ in e.get_points()} for e in msp if e.dxftype() == "LWPOLYLINE"
             and e.dxf.layer in ("Котлован", "Котлован_низ")]
    if niz not in polys: bad(tag, "подошва котлована на плане не совпадает с расчётом")
    if not any(verh <= p_ for p_ in polys): bad(tag, "бровка котлована на плане не совпадает с расчётом")
if any(e.dxf.layer in ("Котлован", "Котлован_низ") and in_plan(e.get_points()[0][1], MC.OY0)
       for e in msp.query("LWPOLYLINE")):
    bad("на первом чертеже не должно быть котлована")
print("Котлован: контуры на обоих планах и hк на разрезах совпадают с расчётом" if ok else "")
print("ВСЁ СХОДИТСЯ" if ok else "ЕСТЬ РАСХОЖДЕНИЯ")
