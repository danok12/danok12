"""Чертёж: план строительной площадки с рабочими отметками и ЛНР, М 1:2000.

Модель - в метрах в натуральную величину (площадка 500 x 300 м, начало
в левом нижнем углу). Лист A3 - в пространстве листа: рамка, штамп
по форме 3 ГОСТ Р 21.101, видовой экран 1:2000 (1 мм листа = 2 м).
Открывается в AutoCAD как есть; сохранить как DWG - «Сохранить как».
"""
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA, MTextEntityAlignment as MA
import raschet as R
import kotlovan as K

K_OR = 1.04
SC = 2.0                      # метров модели в 1 мм листа (М 1:2000)
TXT = "ГОСТ тип Б"            # текстовый стиль: ГОСТ 2.304, шрифт GOST_B.TTF

doc = ezdxf.new("R2010", setup=["linetypes"])
doc.units = ezdxf.units.M
doc.header["$LWDISPLAY"] = 1
doc.header["$DWGCODEPAGE"] = "ANSI_1251"      # кириллица
doc.header["$MEASUREMENT"] = 1
doc.header["$DIMDSEP"] = ord(",")
doc.header["$PSLTSCALE"] = 0                  # масштаб типов линий задаётся у объектов в метрах модели
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
    "Котлован": (6, 50, True),
    "Котлован_низ": (6, 25, True),
    "Бергштрихи": (6, 18, True),
    "Оси": (7, 18, True),
    "Конструкции": (7, 50, True),
    "Штриховка": (8, 13, True),
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
for name, sc in (("М1-500", 0.5), ("М1-50", 0.05)):   # для листа 2
    d2 = doc.dimstyles.duplicate_entry("М1-2000", name)
    d2.dxf.dimscale = sc
    d2.dxf.dimdec = 3 if sc < 0.1 else 2

msp = doc.modelspace()
f = float


def fmt(v, sign=True):
    s = f"{abs(f(v)):.2f}".replace(".", ",")
    if not sign or v == 0:
        return s
    return ("+" if v > 0 else "-") + s        # дефис: в шрифте ГОСТ нет знака «минус»


def mtext(text, pos, h_mm, layer, align=MA.MIDDLE_CENTER, mask=True, rot=0, sc=SC):
    mt = msp.add_mtext(text, dxfattribs={"layer": layer, "style": TXT,
                                         "char_height": h_mm * sc, "rotation": rot})
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
LABEL_SHIFT = {"8'": (34, 28)}   # ручные сдвиги подписи (м): 8' закрыта котлованом
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


def dim(p1, p2, base, angle, override=None, style="М1-2000"):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=style,
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

# ---------- котлован ----------
RG = K.ramp_geometry()


def draw_pit(dx=0.0, dy=0.0, berg=False):
    """Контуры котлована: бровка (с пандусом) - толстая, подошва - тонкая."""
    P = lambda p: (f(p[0]) + dx, f(p[1]) + dy)
    V, Nz = K.VERH, K.NIZ
    xr = V[3][0]
    g1, g2 = RG["gap"]
    (xe, y1), (_, y2) = RG["end"]
    top = [(xr, g2), V[4], V[5], V[0], V[1], V[2], V[3], (xr, g1), (xe, y1), (xe, y2)]
    msp.add_lwpolyline([P(p) for p in top], close=True, dxfattribs={"layer": "Котлован"})
    msp.add_lwpolyline([P(p) for p in Nz], close=True, dxfattribs={"layer": "Котлован_низ"})
    for a, b in RG["toe"] + RG["edge"]:
        msp.add_line(P(a), P(b), dxfattribs={"layer": "Котлован_низ"})
    if not berg:
        return
    # бергштрихи: от бровки к подошве, через 1 м, длинный/короткий попеременно
    l = f(K.L_OTK)
    n = len(V)
    for k in range(n):
        (x1, y1_), (x2, y2_) = map(P, (V[k], V[(k + 1) % n]))
        L = abs(x2 - x1) + abs(y2_ - y1_)
        ux, uy = (x2 - x1) / L, (y2_ - y1_) / L
        nx, ny = -uy, ux                       # внутрь котлована (обход против часовой)
        t, odd = l, False
        while t <= L - l + 1e-9:
            px, py = x1 + ux * t, y1_ + uy * t
            if k == 3 and f(g1) - 0.5 + dy <= py <= f(g2) + 0.5 + dy:   # пандус
                t += 1.0; continue
            ln_ = l if not odd else l / 2
            msp.add_line((px, py), (px + nx * ln_, py + ny * ln_), dxfattribs={"layer": "Бергштрихи"})
            t += 1.0; odd = not odd


draw_pit()
mtext("Котлован", tuple(map(f, K.CENTER)), 2.5, "Котлован", mask=True)

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


def frame_and_stamp(sheet, sheets, name, title):
    """Рамка листа A3 и штамп по форме 3 на текущем листе psp."""
    X0, Y0 = 415 - 185, 5
    pl([(0, 0), (420, 0), (420, 297), (0, 297)], layer="Видовой_экран", closed=True)
    pl([(20, 5), (415, 5), (415, 292), (20, 292)], layer="Рамка", closed=True)

    # штамп: форма 3, 185 x 55, правый нижний угол рамки
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
    for k, (role, who) in enumerate(rows):
        y = Y0 + 27.5 - 5 * k
        txt(role, (X0 + 1, y), 2.0, TA.MIDDLE_LEFT, width=0.8)
        txt(who, (X0 + 21, y), 2.0, TA.MIDDLE_LEFT, width=0.8)
    txt("НИУ МГСУ 08.05.01 - КР - 2026", (X0 + 125, Y0 + 50), 3.5)
    mt("Разработка технологической карты на производство\\Pземляных работ. Вариант 2, грунт - супесь",
       (X0 + 125, Y0 + 37.5), 2.5, 115)
    mt("Графическая часть\\Pкурсовой работы", (X0 + 100, Y0 + 22.5), 2.5, 66)
    txt("Стадия", (X0 + 142.5, Y0 + 27.5), 2.0, width=0.8)
    txt("Лист", (X0 + 157.5, Y0 + 27.5), 2.0, width=0.8)
    txt("Листов", (X0 + 175, Y0 + 27.5), 2.0, width=0.8)
    txt("У", (X0 + 142.5, Y0 + 20), 3.0)
    txt(str(sheet), (X0 + 157.5, Y0 + 20), 3.0)
    if sheets:
        txt(str(sheets), (X0 + 175, Y0 + 20), 3.0)
    mt(name, (X0 + 100, Y0 + 7.5), 2.5, 68)
    mt("Кафедра технологий\\Pи организации строительного\\Pпроизводства", (X0 + 160, Y0 + 7.5), 2.0, 48)

    # заголовок листа
    if title:
        txt(title, (217.5, 283), 5, layer="Надписи", width=0.8)


frame_and_stamp(1, 2, "План строительной площадки\\Pс рабочими отметками,\\PЛНР и котлованом М 1:2000",
                "План строительной площадки с рабочими отметками, линией нулевых работ и котлованом  М 1:2000")

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
    ("pit", "котлован: бровка и подошва (с пандусом)"),
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
    elif kind == "pit":
        pl([(sx0, y - 2.5), (sx1, y - 2.5), (sx1, y + 2.5), (sx0, y + 2.5)], "Котлован", True)
        pl([(sx0 + 0.8, y - 1.7), (sx1 - 0.8, y - 1.7), (sx1 - 0.8, y + 1.7), (sx0 + 0.8, y + 1.7)],
           "Котлован_низ", True)
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

# ================= лист 2: котлован =================
S5, S50 = 0.5, 0.05                    # м модели в 1 мм листа: М 1:500 и М 1:50
DX2 = 800.0                            # план котлована 1:500 - копия, сдвинутая по x
NDX, NDY = 2000.0, 0.0                 # узел 1:50 - в своих координатах (ось стены x=0, земля y=0)
X0, Y0 = f(K.X0) + DX2, f(K.Y0)
DT = f(K.D_NIZ + K.L_OTK)              # ось -> бровка
DNZ = f(K.D_NIZ)


def m2(x, y):
    return (x, y)


def line(p1, p2, layer, **kw):
    at = {"layer": layer}
    at.update(kw)
    return msp.add_line(p1, p2, dxfattribs=at)


def circle_label(c, r, s, sc):
    msp.add_circle(c, r, dxfattribs={"layer": "Оси"})
    mtext(s, c, 3.5, "Оси", mask=False, sc=sc)


# --- план котлована М 1:500 ---
draw_pit(dx=DX2, berg=True)
st = [(f(x) + DX2, f(y)) for x, y in K.ST]
msp.add_lwpolyline(st, close=True, dxfattribs={"layer": "Конструкции", "linetype": "DASHED",
                                               "ltscale": 2.0, "lineweight": 25})
AX_V = [("1", X0), ("2", X0 + 18), ("3", X0 + 60)]
AX_H = [("А", Y0), ("Б", Y0 + 12), ("В", Y0 + 30)]
R1, R2 = 3.5, 6.5                      # ряды размеров от бровки, м (7 и 13 мм на листе)
yb = Y0 - DT                           # бровка снизу
yt = Y0 + 30 + DT                      # бровка сверху
xl = X0 - DT                           # бровка слева
BUB = 2.0                              # радиус кружка оси, м (8 мм на листе)
for s_, x in AX_V:
    line((x, yt + 1.0), (x, yb - R2 - 3.0), "Оси", linetype="CENTER", ltscale=2.4)
    circle_label((x, yb - R2 - 3.0 - BUB), BUB, s_, S5)
for s_, y in AX_H:
    line((X0 + 60 + DT + 1.0, y), (xl - 14.5 - 3.0, y), "Оси", linetype="CENTER", ltscale=2.4)
    circle_label((xl - 14.5 - 3.0 - BUB, y), BUB, s_, S5)
# размеры: снизу - оси; сверху - котлован по низу и по верху; слева - оси и котлован
dim((X0, yb - 1), (X0 + 18, yb - 1), (0, yb - R1), 0, style="М1-500")
dim((X0 + 18, yb - 1), (X0 + 60, yb - 1), (0, yb - R1), 0, style="М1-500")
dim((X0, yb - 1), (X0 + 60, yb - 1), (0, yb - R2), 0, style="М1-500")
dim((X0 - DNZ, Y0 + 30 + DNZ), (X0 + 60 + DNZ, Y0 + 30 + DNZ), (0, yt + R1), 0, style="М1-500")
dim((X0 - DT, yt), (X0 + 60 + DT, yt), (0, yt + R2), 0, style="М1-500")
dim((xl - 1, Y0), (xl - 1, Y0 + 12), (xl - R1, 0), 90, style="М1-500")
dim((xl - 1, Y0 + 12), (xl - 1, Y0 + 30), (xl - R1, 0), 90, style="М1-500")
dim((xl - 1, Y0), (xl - 1, Y0 + 30), (xl - R2, 0), 90, style="М1-500")
dim((X0 - DNZ, Y0 - DNZ), (X0 - DNZ, Y0 + 30 + DNZ), (xl - 11.0, 0), 90, style="М1-500")
dim((xl, Y0 - DT), (xl, yt), (xl - 14.5, 0), 90, style="М1-500")
# пандус
(xe, y1), (_, y2) = [(f(a) + DX2, f(b)) for a, b in RG["end"]]
xb = f(K.PAN_X) + DX2
g2 = f(RG["gap"][1])
dim((xb, y2), (xe, y2), (0, g2 + 3.5), 0, style="М1-500")
dim((xe, y1), (xe, y2), (xe + 3.0, 0), 90, style="М1-500")
mtext("Пандус, i = " + K.f(K.I_PAN), ((xb + xe) / 2 + 2, f(RG["gap"][0]) - 3.0), 2.5, "Надписи", sc=S5)
mtext("Котлован", (X0 + 30, Y0 + 21), 3.5, "Надписи", sc=S5)
mtext(f"подошва: hк = {K.f(K.HK)} м от естественной поверхности", (X0 + 30, Y0 + 16.5), 2.5,
      "Надписи", sc=S5)
mtext("контур здания\\P(наружная\\Pгрань стен)", (X0 + 9, Y0 + 6.0), 2.0, "Надписи", sc=S5, mask=True)
# разрез 1-1 через ось А у оси 1+9 м, взгляд на запад (влево)
xs = X0 + 5
for yy0, yy1 in ((yb - 0.4, yb - 2.4), (yt + 0.4, yt + 2.4)):
    msp.add_lwpolyline([(xs, yy0), (xs, yy1)], dxfattribs={"layer": "Конструкции", "const_width": 0.35})
    msp.add_lwpolyline([(xs, yy1), (xs - 1.8, yy1), (xs - 3.0, yy1)], dxfattribs={"layer": "Конструкции"})
    pl_ = msp.add_lwpolyline([(xs - 1.8, yy1, 0.9, 0.0), (xs - 3.0, yy1)], format="xyse",
                             dxfattribs={"layer": "Конструкции"})
    mtext("1", (xs - 4.4, yy1), 3.5, "Надписи", mask=False, sc=S5)

# --- узел: разрез 1-1 (фрагмент) М 1:50 ---
def N(x, y):
    return (NDX + x, NDY + y)


HK_, L_ = f(K.HK), f(K.L_OTK)
XB, XT = -(DNZ + L_), -DNZ                     # бровка и низ откоса
YP, YBP, YFP, YW = -HK_ + f(K.H_PODS), -HK_ + f(K.H_PODS + K.H_BP), -HK_ + f(K.H_PODS + K.H_BP + K.H_FP), 0.35
XR = 1.0                                       # обрыв справа
D_FP, D_BP, D_ST = f(K.D_FP), f(K.D_BP), f(K.D_ST)
GL = -5.2                                      # начало линии земли слева
HR_ = f(K.HR)
# грунт: полоса штриховки вдоль поверхности, откоса и дна
ground = [N(GL, 0), N(XB, 0), N(XT, -HK_), N(XR, -HK_)]
msp.add_lwpolyline(ground, dxfattribs={"layer": "Котлован", "lineweight": 50})
band = ground + [N(XR, -HK_ - 0.15), N(XT - 0.1, -HK_ - 0.15), N(XB - 0.12, -0.15), N(GL, -0.15)]
hat = msp.add_hatch(color=8, dxfattribs={"layer": "Штриховка"})
hat.set_pattern_fill("ANSI31", scale=0.03, angle=90, color=8)
hat.paths.add_polyline_path(band, is_closed=True)


def rect(x0, y0, x1, y1, pattern=None, angle=0, scale=0.025, lw=50):
    pts = [N(x0, y0), N(x1, y0), N(x1, y1), N(x0, y1)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "Конструкции", "lineweight": lw})
    if pattern:
        h = msp.add_hatch(color=8, dxfattribs={"layer": "Штриховка"})
        h.set_pattern_fill(pattern, scale=scale, angle=angle, color=8)
        h.paths.add_polyline_path(pts, is_closed=True)


rect(XT, -HK_, XR, YP, "ANSI37", 0, 0.02, 25)           # подсыпка (щебень)
rect(-D_BP, YP, XR, YBP, "ANSI31", 90, 0.02, 25)        # бетонная подготовка
rect(-D_FP, YBP, XR, YFP, "ANSI31", 0, 0.025)           # фундаментная плита
rect(-D_ST, YFP, D_ST, YW, "ANSI31", 0, 0.025)          # стена подвала
line(N(-D_BP, YBP + 0.012), N(XR, YBP + 0.012), "Конструкции", lineweight=35)   # гидроизоляция
# обрыв справа
YM = (YBP + YFP) / 2
msp.add_lwpolyline([N(XR, -HK_ - 0.25), N(XR, YM - 0.06), N(XR + 0.08, YM - 0.02), N(XR - 0.08, YM + 0.02),
                    N(XR, YM + 0.06), N(XR, YFP + 0.15)], dxfattribs={"layer": "Конструкции", "lineweight": 18})
# ось А
line(N(0, -HK_ - 0.35), N(0, YW + 0.3), "Оси", linetype="CENTER", ltscale=0.24)
circle_label(N(0, YW + 0.3 + 0.2), 0.2, "А", S50)
# проектная поверхность (после планировки - насыпь hр)
line(N(GL, HR_), N(XR + 0.6, HR_), "Котлован_низ", linetype="DASHED", ltscale=0.2)
mtext(f"проектная поверхность планировки (насыпь +{K.f(K.HR)})", N(GL + 0.05, HR_ + 0.06), 2.0,
      "Надписи", MA.BOTTOM_LEFT, sc=S50)
mtext("естественная поверхность", N(GL + 0.05, -0.06), 2.0, "Надписи", MA.TOP_LEFT, sc=S50)
mtext(f"1:{K.f(K.M)}", N((XB + XT) / 2 - 0.35, -HK_ / 2), 2.5, "Надписи", rot=-56.2, sc=S50)
mtext("обратная\\Pзасыпка", N(-1.05, -0.9), 2.5, "Надписи", sc=S50)
# размеры
yd1, yd2 = -HK_ - 0.5, -HK_ - 0.85
for a, b in ((XB, XT), (XT, -D_BP), (-D_BP, -D_FP), (-D_FP, -D_ST), (-D_ST, 0)):
    dim(N(a, -HK_ if a != XB else 0), N(b, -HK_), N(0, yd1), 0, {"dimtad": 1}, style="М1-50")
dim(N(XB, 0), N(0, -HK_), N(0, yd2), 0, style="М1-50")
dim(N(XT, -HK_), N(XB, 0), N(GL + 0.9, 0), 90, style="М1-50")
dim(N(XT, -HK_), N(GL, HR_), N(GL + 0.4, 0), 90, style="М1-50")
mtext("hк", N(GL + 0.72, -HK_ / 2 - 0.45), 2.5, "Надписи", sc=S50)
mtext("Нк", N(GL + 0.22, -HK_ / 2 - 0.45), 2.5, "Надписи", sc=S50)
# выноски слоёв
LBL = [((0.1, YW - 0.3), "Стена подвала 400"),
       ((0.6, (YBP + YFP) / 2), f"Фундаментная плита {int(K.H_FP * 1000)}"),
       ((0.75, YBP), "Гидроизоляция, 2 слоя"),
       ((0.85, (YP + YBP) / 2), f"Бетонная подготовка {int(K.H_BP * 1000)}"),
       ((0.95, (-HK_ + YP) / 2), f"Подсыпка (щебень) {int(K.H_PODS * 1000)}")]
for k_, ((px, py), s_) in enumerate(LBL):
    ty = 0.35 - 0.38 * k_
    line(N(px, py), N(1.9, ty), "Надписи")
    line(N(1.9, ty), N(4.6, ty), "Надписи")
    mtext(s_, N(1.95, ty + 0.03), 2.5, "Надписи", MA.BOTTOM_LEFT, mask=False, sc=S50)

# --- лист ---
psp = doc.layouts.new("Лист 2")
psp.page_setup(size=(420, 297), margins=(0, 0, 0, 0), units="mm")
frame_and_stamp(2, None, "Котлован. План М 1:500,\\Pразрез 1-1 (фрагмент) М 1:50", None)


def viewport(px0, py0, px1, py1, mx0, my0, sc):
    w_, h_ = px1 - px0, py1 - py0
    v = psp.add_viewport(center=((px0 + px1) / 2, (py0 + py1) / 2), size=(w_, h_),
                         view_center_point=(mx0 + w_ * sc / 2, my0 + h_ * sc / 2), view_height=h_ * sc)
    v.dxf.layer = "Видовой_экран"
    v.dxf.flags = v.dxf.flags | 16384
    return v


viewport(25, 153, 257, 277, xl - 14.5 - 3.0 - 2 * BUB - 2.0, yb - R2 - 3.0 - 2 * BUB - 2.0, S5)
viewport(25, 60, 228, 148, NDX + GL - 0.3, NDY - HK_ - 1.0, S50)
txt("План котлована  М 1:500", (141, 281), 5, layer="Надписи", width=0.8)
txt("1-1 (фрагмент)  М 1:50", (126.5, 151), 3.5, layer="Надписи", width=0.8)


def table(x0, ytop, cols, rows, title, h=6.0):
    txt(title, (x0, ytop + 1.5), 3.0, TA.BOTTOM_LEFT, "Надписи", 0.8)
    for r, row in enumerate(rows):
        y = ytop - h * r
        x = x0
        for c, (s_, w_) in enumerate(zip(row, cols)):
            pl([(x, y), (x + w_, y), (x + w_, y - h), (x, y - h)], "Штамп", True)
            al = TA.MIDDLE_LEFT if c == 0 else TA.MIDDLE_CENTER
            txt(s_, (x + 1.2 if c == 0 else x + w_ / 2, y - h / 2), 2.5, al, "Надписи", 0.8)
            x += w_


M2, M3 = "м{\\H0.6x;\\A2;2}", "м{\\H0.6x;\\A2;3}"
nf = lambda v, n=2: f"{round(float(v), n):,.{n}f}".replace(",", " ").replace(".", ",")
P = [("Параметр", "Обозн.", "Значение"),
     ("Глубина по заданию, м", "Нк", K.f(K.NK)),
     ("Рабочая отметка в центре, м", "hр", "+" + K.f(K.HR)),
     ("Фактическая глубина, м", "hк", K.f(K.HK)),
     ("Откос (супесь, hк до 3 м)", "1:m", "1:" + K.f(K.M)),
     ("Заложение откоса, м", "l", K.f(K.L_OTK)),
     ("Низ котлована, м", "", f"{K.f(K.BX + 2 * K.D_NIZ)} x {K.f(K.BY + 2 * K.D_NIZ)}"),
     ("Верх котлована, м", "", f"{K.f(K.BX + 2 * (K.D_NIZ + K.L_OTK), 2)} x {K.f(K.BY + 2 * (K.D_NIZ + K.L_OTK), 2)}"),
     (f"Площадь по низу, {M2}", "Fк.н", nf(K.F_KN)),
     (f"Площадь по верху, {M2}", "Fк.в", nf(K.F_KV)),
     ("Пандус: ширина x длина, м", "bп", f"{K.f(K.B_PAN)} x {K.f(K.L_PAN)}")]
table(262, 274, (80, 20, 46), P, "Параметры котлована")
V = [("Объём", "Обозн.", f"V, {M3}"),
     ("Котлован без пандуса", "", nf(K.V_OSN)),
     ("Пандус", "Vпан", nf(K.V_PAN)),
     ("Котлован всего", "Vк", nf(K.V_K)),
     ("Подсыпка (щебень)", "Vподс", nf(K.V_PODS)),
     ("Бетонная подготовка", "Vб.п", nf(K.V_BP)),
     ("Подземная часть здания", "Vп.ч", nf(K.V_PCH)),
     ("Обратная засыпка", "Vо.з", nf(K.V_OZ))]
table(262, 196, (80, 20, 46), V, "Объёмы котлована")
NOTE = ("Примечания\\P"
        "1. Размеры - в метрах. Грунт - супесь, откос по прил. 3 методички.\\P"
        "2. Здание - вариант размещения 8: центр здания совпадает с центром квадрата 8.\\P"
        f"3. Котлован пересечён ЛНР; среднее рабочих отметок по углам +{K.f(sum(K.H_CORNERS_F) / 6, 3)} - "
        "котлован в зоне насыпи и разрабатывается от естественной поверхности: "
        f"hк = Нк - hр = {K.f(K.NK)} - {K.f(K.HR)} = {K.f(K.HK)} м.\\P"
        "4. Низ котлована - 1,4 м от осей: 0,2 до грани стены + 0,5 вылет плиты + "
        "0,2 выход подготовки + 0,5 рабочая зона.\\P"
        f"5. Пандус принят однополосный: bп = {K.f(K.B_PAN)} м, i = {K.f(K.I_PAN)}.")
mt(NOTE, (25, 56), 2.5, 200, MA.TOP_LEFT, "Надписи")

out = "План_ЛНР_вариант2.dxf"
doc.saveas(out)
print("saved", out, "viewport", vw, vh, vc)
