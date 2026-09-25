"""Чертёж: план строительной площадки с рабочими отметками и ЛНР, М 1:2000.

Модель - в метрах в натуральную величину (площадка 500 x 300 м, начало
в левом нижнем углу). Лист A3 - в пространстве листа: рамка, штамп
по форме 3 ГОСТ Р 21.101, видовой экран 1:2000 (1 мм листа = 2 м).
Открывается в AutoCAD как есть; сохранить как DWG - «Сохранить как».
"""
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA, MTextEntityAlignment as MA
import raschet as R

K_OR = 1.04
SC = 2.0                      # метров модели в 1 мм листа (М 1:2000)
TXT = "ГОСТ тип Б"            # текстовый стиль: ГОСТ 2.304, шрифт GOST_B.TTF

doc = ezdxf.new("R2010", setup=["linetypes"])
doc.units = ezdxf.units.M
doc.header["$LWDISPLAY"] = 1
doc.header["$DWGCODEPAGE"] = "ANSI_1251"      # кириллица
doc.header["$MEASUREMENT"] = 1
doc.header["$DIMDSEP"] = ord(",")
GOST_FILE, GOST_FAMILY = "GOST_B.TTF", "GOST type B"
st = doc.styles.add(TXT, font=GOST_FILE)
st.set_extended_font_data(GOST_FAMILY)
std = doc.styles.get("Standard")              # и стиль по умолчанию - тоже ГОСТ тип Б
std.dxf.font = GOST_FILE
std.set_extended_font_data(GOST_FAMILY)

LAYERS = {  # имя: (цвет ACI, вес линии в сотых мм, печатать)
    "Сетка": (7, 25, True),
    "ЛНР": (1, 70, True),
    "Отметки": (5, 18, True),
    "Номера_фигур": (7, 25, True),
    "ПВ_ПН": (7, 35, True),
    "ПВ_штриховка": (8, 13, True),
    "Размеры": (3, 18, True),
    "Рамка": (7, 70, True),
    "Штамп": (7, 25, True),
    "Надписи": (7, 25, True),
    "Видовой_экран": (8, 13, False),
}
for name, (color, lw, plot) in LAYERS.items():
    lay = doc.layers.add(name, color=color, lineweight=lw)
    lay.dxf.plot = int(plot)

ds = doc.dimstyles.new("М1-2000")
for k, v in dict(dimtxsty=TXT, dimtxt=2.5, dimscale=SC, dimtsz=1.3, dimasz=2.5,
                 dimexe=1.5, dimexo=0.0, dimgap=0.8, dimdec=2, dimzin=8,
                 dimdsep=ord(","), dimtad=1, dimtih=0, dimtoh=0, dimlfac=1.0,
                 dimclrd=3, dimclre=3, dimclrt=3, dimtix=1, dimtmove=0, dimtfill=1).items():
    ds.dxf.set(k, v)

msp = doc.modelspace()
f = float


def fmt(v, sign=True):
    s = f"{abs(f(v)):.2f}".replace(".", ",")
    if not sign or v == 0:
        return s
    return ("+" if v > 0 else "-") + s        # дефис: в шрифте ГОСТ нет знака «минус»


def mtext(text, pos, h_mm, layer, align=MA.MIDDLE_CENTER, mask=True, rot=0):
    mt = msp.add_mtext(text, dxfattribs={"layer": layer, "style": TXT,
                                         "char_height": h_mm * SC, "rotation": rot})
    mt.set_location(pos, attachment_point=align)
    if mask:
        mt.set_bg_color("canvas", scale=1.2)    # маска цветом фона: штриховка не идёт сквозь текст
    return mt


# ---------- сетка ----------
W, Hh = R.A * R.NX, R.A * R.NY
for j in range(R.NY + 1):
    msp.add_line((0, j * R.A), (W, j * R.A), dxfattribs={"layer": "Сетка"})
for i in range(R.NX + 1):
    msp.add_line((i * R.A, 0), (i * R.A, Hh), dxfattribs={"layer": "Сетка"})

# ---------- штриховка выемки ----------
for fig in R.FIGS:
    if fig["sign"] < 0:
        hat = msp.add_hatch(color=8, dxfattribs={"layer": "ПВ_штриховка"})
        hat.set_pattern_fill("ANSI31", scale=2.4, color=8)
        hat.paths.add_polyline_path([(f(x), f(y)) for x, y in fig["poly"]], is_closed=True)

# ---------- линия нулевых работ ----------
segs = []
for sq in range(1, R.NX * R.NY + 1):
    figs = [g for g in R.FIGS if g["sq"] == sq]
    if len(figs) == 2:
        zs = [p for p, lb in zip(figs[0]["poly"], figs[0]["labels"]) if lb[0] == "z"]
        segs.append([tuple(map(f, zs[0])), tuple(map(f, zs[1]))])
chain = segs.pop(0)
while segs:                                    # сцепляем отрезки в одну полилинию
    for s in segs:
        if s[0] == chain[-1]: chain.append(s[1]); break
        if s[1] == chain[-1]: chain.append(s[0]); break
        if s[0] == chain[0]: chain.insert(0, s[1]); break
        if s[1] == chain[0]: chain.insert(0, s[0]); break
    else:
        raise RuntimeError("ЛНР разрывается - несколько участков")
    segs.remove(s)
msp.add_lwpolyline(chain, dxfattribs={"layer": "ЛНР", "const_width": 0.6 * SC})

# ---------- рабочие отметки в вершинах ----------
for j in range(R.NY + 1):
    for i in range(R.NX + 1):
        x, y = R.xy(i, j)
        hv = R.h(i, j)
        mtext(fmt(hv), (f(x) + 1.0 * SC, f(y) + 0.8 * SC), 2.5, "Отметки", MA.BOTTOM_LEFT)
        msp.add_circle((f(x), f(y)), 0.5 * SC, dxfattribs={"layer": "Отметки"})

# ---------- номера фигур ----------
LABEL_SHIFT = {}   # ручные сдвиги подписи (м), если центр тяжести неудачен
for fig in R.FIGS:
    cx, cy = map(f, fig["c"])
    dx, dy = LABEL_SHIFT.get(fig["name"], (0, 0))
    h_mm = 3.5 if fig["F"] > 2500 else 2.5
    mtext(fig["name"], (cx + dx, cy + dy), h_mm, "Номера_фигур")

# ---------- ПВ / ПН ----------
ZONE = {"ПВ": (50, 28), "ПН": (450, 228)}
for t, p in ZONE.items():
    mtext(t, p, 5, "ПВ_ПН")

# ---------- размеры до точек нулевых работ ----------
DOFF = 2.0 * SC          # отступ размерной линии от стороны квадрата, м


def dim(p1, p2, base, angle, override=None):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="М1-2000",
                           override=override or {}, dxfattribs={"layer": "Размеры"})
    d.render()


def adjacent(q1, q2):
    """Фигуры, у которых отрезок q1-q2 - сторона; -> [(фигура, сторона ±1)]."""
    res = []
    for g in R.FIGS:
        pts = [tuple(map(f, p)) for p in g["poly"]]
        n = len(pts)
        for k in range(n):
            if {pts[k], pts[(k + 1) % n]} == {q1, q2}:
                cx, cy = map(f, g["c"])
                side = (cy > q1[1]) if q1[1] == q2[1] else (cx > q1[0])
                res.append((g, 1 if side else -1))
    return res


BORDER_OFF = {"top": 7.0 * SC, "other": 2.0 * SC}
for z in R.ZP:
    a, b = z["p1"], z["p2"]
    ia, ja = (a - 1) % (R.NX + 1), (a - 1) // (R.NX + 1)
    ib, jb = (b - 1) % (R.NX + 1), (b - 1) // (R.NX + 1)
    pa, pb = tuple(map(f, R.xy(ia, ja))), tuple(map(f, R.xy(ib, jb)))
    pz = tuple(map(f, z["pt"]))
    horiz = ja == jb
    for q1, q2 in ((pa, pz), (pz, pb)):
        adj = adjacent(q1, q2)
        if len(adj) == 1:                 # граница площадки - размер снаружи
            side = -adj[0][1]
            top = horiz and q1[1] == Hh
            off = BORDER_OFF["top"] if top else BORDER_OFF["other"]
        else:                             # внутри - со стороны большей фигуры
            side = max(adj, key=lambda t: t[0]["F"])[1]
            off = BORDER_OFF["other"]
        if horiz:
            base = (q1[0], q1[1] + side * off)
            dim(q1, q2, base, 0, {"dimtad": 1 if side > 0 else 4})
        else:
            lo, hi = sorted((q1, q2), key=lambda p: p[1])
            base = (q1[0] + side * off, q1[1])
            dim(lo, hi, base, 90, {"dimtad": 4 if side > 0 else 1})

# ---------- габаритные размеры ----------
for i in range(R.NX):
    dim((i * R.A, 0), ((i + 1) * R.A, 0), (0, -11 * SC), 0)
dim((0, 0), (W, 0), (0, -18 * SC), 0)
for j in range(R.NY):
    dim((0, j * R.A), (0, (j + 1) * R.A), (-6 * SC, 0), 90)
dim((0, 0), (0, Hh), (-13 * SC, 0), 90)

# ================= лист A3 =================
psp = doc.layouts.get("Layout1")
doc.layouts.rename("Layout1", "Лист 1")
psp.page_setup(size=(420, 297), margins=(0, 0, 0, 0), units="mm")
# page_setup создаёт главный видовой экран листа (id 1) - без него nanoCAD
# и AutoCAD не показывают остальные видовые экраны, поэтому его не трогаем


def pl(pts, layer="Штамп", closed=False, lw=None):
    at = {"layer": layer}
    if lw is not None: at["lineweight"] = lw
    psp.add_lwpolyline(pts, close=closed, dxfattribs=at)


def ln(p1, p2, lw=25):
    psp.add_line(p1, p2, dxfattribs={"layer": "Штамп", "lineweight": lw})


TA2MA = {TA.MIDDLE_CENTER: MA.MIDDLE_CENTER, TA.MIDDLE_LEFT: MA.MIDDLE_LEFT,
         TA.BOTTOM_LEFT: MA.BOTTOM_LEFT, TA.BOTTOM_CENTER: MA.BOTTOM_CENTER}


def txt(s, pos, h=2.5, align=TA.MIDDLE_CENTER, layer="Штамп", width=None):
    """Однострочная надпись. Пишется как MTEXT: у однострочного TEXT с
    центровкой nanoCAD не пересчитывает точку вставки и сдвигает текст."""
    content = (f"\\W{width};" if width else "") + s
    m = psp.add_mtext(content, dxfattribs={"layer": layer, "style": TXT, "char_height": h})
    m.set_location(pos, attachment_point=TA2MA[align])
    return m


def mt(s, pos, h, width, align=MA.MIDDLE_CENTER, layer="Штамп"):
    m = psp.add_mtext(s, dxfattribs={"layer": layer, "style": TXT, "char_height": h, "width": width})
    m.set_location(pos, attachment_point=align)
    return m


pl([(0, 0), (420, 0), (420, 297), (0, 297)], layer="Видовой_экран", closed=True)
pl([(20, 5), (415, 5), (415, 292), (20, 292)], layer="Рамка", closed=True)

# штамп: форма 3, 185 x 55, правый нижний угол рамки
X0, Y0 = 415 - 185, 5
pl([(X0, Y0), (415, Y0), (415, Y0 + 55), (X0, Y0 + 55)], closed=True, lw=70)
colx = [0, 10, 20, 30, 40, 55, 65]
# левая часть: 4 строки изменений, строка заголовков, 6 строк подписей
for c in colx[1:]:
    y_bot = Y0 + 30 if c in (10, 30) else Y0       # «Разработал» и фамилия - по 2 столбца
    ln((X0 + c, y_bot), (X0 + c, Y0 + 55), 70 if c == 65 else 25)
for r in range(1, 11):
    y = Y0 + 5 * r
    ln((X0, y), (X0 + 65, y), 70 if r in (6, 7) else 25)
# правая часть
for y in (Y0 + 45, Y0 + 30, Y0 + 15):
    ln((X0 + 65, y), (415, y), 70)
ln((X0 + 135, Y0), (X0 + 135, Y0 + 30), 70)
ln((X0 + 135, Y0 + 25), (415, Y0 + 25), 25)
ln((X0 + 150, Y0 + 15), (X0 + 150, Y0 + 30), 25)
ln((X0 + 165, Y0 + 15), (X0 + 165, Y0 + 30), 25)

hdr = ["Изм.", "Кол.уч.", "Лист", "№док.", "Подп.", "Дата"]
for k, s in enumerate(hdr):
    txt(s, (X0 + (colx[k] + colx[k + 1]) / 2, Y0 + 32.5), 2.0, width=0.8)
rows = [("Разработал", "Буев Д.Р."), ("Проверил", "Забелина О.Б."),
        ("Т. контр.", ""), ("", ""), ("Н. контр.", ""), ("Утв.", "")]
for k, (role, name) in enumerate(rows):
    y = Y0 + 27.5 - 5 * k
    txt(role, (X0 + 1, y), 2.0, TA.MIDDLE_LEFT, width=0.8)
    txt(name, (X0 + 21, y), 2.0, TA.MIDDLE_LEFT, width=0.8)
txt("НИУ МГСУ 08.05.01 - КР - 2026", (X0 + 125, Y0 + 50), 3.5)
mt("Разработка технологической карты на производство\\Pземляных работ. Вариант 2, грунт - супесь",
   (X0 + 125, Y0 + 37.5), 2.5, 115)
mt("Графическая часть\\Pкурсовой работы", (X0 + 100, Y0 + 22.5), 2.5, 66)
txt("Стадия", (X0 + 142.5, Y0 + 27.5), 2.0, width=0.8)
txt("Лист", (X0 + 157.5, Y0 + 27.5), 2.0, width=0.8)
txt("Листов", (X0 + 175, Y0 + 27.5), 2.0, width=0.8)
txt("У", (X0 + 142.5, Y0 + 20), 3.0)
txt("1", (X0 + 157.5, Y0 + 20), 3.0)
mt("План строительной площадки\\Pс рабочими отметками и ЛНР\\PМ 1:2000", (X0 + 100, Y0 + 7.5), 2.5, 68)
mt("Кафедра технологий\\Pи организации строительного\\Pпроизводства", (X0 + 160, Y0 + 7.5), 2.0, 48)

# заголовок листа
txt("План строительной площадки с рабочими отметками и линией нулевых работ  М 1:2000",
    (217.5, 283), 5, layer="Надписи", width=0.8)

# видовой экран: модель x -34..524, y -44..326 м
VX0, VY0, VX1, VY1 = -34.0, -44.0, 524.0, 326.0
vw, vh = (VX1 - VX0) / SC, (VY1 - VY0) / SC
vc = (217.5, 72 + vh / 2)
vp = psp.add_viewport(center=vc, size=(vw, vh),
                      view_center_point=((VX0 + VX1) / 2, (VY0 + VY1) / 2), view_height=vh * SC)
vp.dxf.layer = "Видовой_экран"
vp.dxf.flags = vp.dxf.flags | 16384              # экран заблокирован: масштаб 1:2000 не собьётся

# ---------- условные обозначения ----------
LX, LY = 26, 64
txt("Условные обозначения", (LX, LY), 3.0, TA.BOTTOM_LEFT, "Надписи", 0.8)
items = [
    ("lnr", "линия нулевых работ (ЛНР)"),
    ("hatch", "ПВ - планировочная выемка"),
    ("box", "ПН - планировочная насыпь"),
    ("mark", "рабочая отметка, м (+ насыпь, - выемка)"),
    ("fig", "номер фигуры; со штрихом - насыпная часть квадрата"),
    ("dim", "расстояние до точки нулевых работ, м"),
]
for k, (kind, label) in enumerate(items):
    y = LY - 7 - 7.5 * k
    sx0, sx1 = LX, LX + 14
    if kind == "lnr":
        psp.add_lwpolyline([(sx0, y), (sx1, y)], dxfattribs={"layer": "ЛНР", "const_width": 0.6})
    elif kind in ("hatch", "box"):
        pts = [(sx0, y - 2.5), (sx1, y - 2.5), (sx1, y + 2.5), (sx0, y + 2.5)]
        pl(pts, "Сетка", True)
        if kind == "hatch":
            hat = psp.add_hatch(color=8, dxfattribs={"layer": "ПВ_штриховка"})
            hat.set_pattern_fill("ANSI31", scale=1.2, color=8)
            hat.paths.add_polyline_path(pts, is_closed=True)
    elif kind == "mark":
        psp.add_circle((sx0 + 1, y - 1.5), 0.5, dxfattribs={"layer": "Отметки"})
        txt("+0,15", (sx0 + 2, y - 1), 2.5, TA.BOTTOM_LEFT, "Отметки", 0.8)
    elif kind == "fig":
        txt("7'", (sx0 + 7, y), 3.5, TA.MIDDLE_CENTER, "Номера_фигур")
    elif kind == "dim":
        psp.add_line((sx0, y - 1.5), (sx1, y - 1.5), dxfattribs={"layer": "Размеры"})
        for xx in (sx0, sx1):
            psp.add_line((xx - 0.9, y - 2.4), (xx + 0.9, y - 0.6), dxfattribs={"layer": "Размеры"})
        txt("37,5", ((sx0 + sx1) / 2, y - 0.7), 2.5, TA.BOTTOM_CENTER, "Размеры", 0.8)
    txt("- " + label, (sx1 + 3, y), 2.5, TA.MIDDLE_LEFT, "Надписи", 0.8)

# ---------- сводка объёмов ----------
Vc = sum(g["V"] for g in R.FIGS if g["sign"] < 0)
Vf = sum(g["V"] for g in R.FIGS if g["sign"] > 0)
Fc = sum(g["F"] for g in R.FIGS if g["sign"] < 0)
Ff = sum(g["F"] for g in R.FIGS if g["sign"] > 0)
TX, TY = 128, 64
txt("Объёмы планировочных работ", (TX, TY), 3.0, TA.BOTTOM_LEFT, "Надписи", 0.8)
def num(v):
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


tab = [("", "F, м{\\H0.6x;\\A2;2}", "V, м{\\H0.6x;\\A2;3}"),   # м2, м3: уменьшенная цифра вверху строки
       ("Выемка ПВ", num(f(Fc)), num(f(Vc))),
       ("Насыпь ПН", num(f(Ff)), num(f(Vf))),
       (f"ПН / Kор, Kор = {K_OR:.2f}".replace(".", ","), "", num(f(Vf) / K_OR))]
cw = [34, 32, 30]
for r, row in enumerate(tab):
    y = TY - 3 - 7 * r
    x = TX
    for c, s in enumerate(row):
        pl([(x, y), (x + cw[c], y), (x + cw[c], y - 7), (x, y - 7)], "Штамп", True)
        al = TA.MIDDLE_LEFT if c == 0 else TA.MIDDLE_CENTER
        px = x + 1.5 if c == 0 else x + cw[c] / 2
        txt(s, (px, y - 3.5), 2.5, al, "Надписи", 0.8)
        x += cw[c]

out = "План_ЛНР_вариант2.dxf"
doc.saveas(out)
print("saved", out, "viewport", vw, vh, vc)
