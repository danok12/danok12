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
TXT = "ГОСТ тип Б"            # текстовый стиль: ГОСТ 2.304, тип Б

# ---------- единое оформление всех листов курсовой ----------
# Все листы собираются из этих констант, общих слоёв (LAYERS), одного размерного
# стиля, типов линий ГОСТ 2.303, рамки со штампом и общих функций (image_title,
# volume_table, level, axis_bubble ...), поэтому линии, текст и элементы на всех
# чертежах работы одинаковые. Новый лист - только через них же.
# Высоты шрифта - только из ряда ГОСТ 2.304: 2,5; 3,5; 5 мм.
H_TEXT, H_HEAD, H_BIG = 2.5, 3.5, 5.0     # мм: основной текст; заголовок таблицы, цифры листа; крупный
H_TITLE = H_BIG                            # наименование изображения
H_AXIS = H_BIG                             # марка оси: в 1,5-2 раза крупнее размерных чисел (ГОСТ Р 21.101)
NARROW = 0.8                               # сжатие надписей листа
TITLE_Y = 283                              # наименования изображений - у верхней рамки
TAB_X, TAB_Y = 128, 64                     # таблица объёмов - в нижней полосе слева от штампа
M2, M3 = "м{\\H0.6x;\\A2;2}", "м{\\H0.6x;\\A2;3}"   # м2, м3: уменьшенная цифра вверху строки

doc = ezdxf.new("R2010", setup=["linetypes"])
doc.units = ezdxf.units.M
doc.header["$LWDISPLAY"] = 1
doc.header["$DWGCODEPAGE"] = "ANSI_1251"      # кириллица
doc.header["$MEASUREMENT"] = 1
doc.header["$DIMDSEP"] = ord(",")
doc.header["$PSLTSCALE"] = 1                  # штрихи типов линий - в мм листа при любом масштабе экрана
# ГОСТ 2.303, длины в мм листа: штрихпунктирная тонкая - штрихи 5-30, промежутки 3-5;
# штриховая - штрихи 2-8, промежутки 1-2
DASHDOT, DASH = "ГОСТ_штрихпунктирная", "ГОСТ_штриховая"
DD_STROKE, DD_GAP, DD_DOT = 20.0, 1.5, 1.0
doc.linetypes.add(DASHDOT, pattern=[DD_STROKE + 2 * DD_GAP + DD_DOT, DD_STROKE, -DD_GAP, DD_DOT, -DD_GAP],
                  description="Штрихпунктирная тонкая ГОСТ 2.303 ____ - ____ - ____")
doc.linetypes.add(DASH, pattern=[7.5, 6.0, -1.5], description="Штриховая ГОСТ 2.303 __ __ __ __")
# GOST Common - шрифт Autodesk по ГОСТ 2.304 тип Б (прописные 6/10 h, строчные 7/10 h,
# интервал 2/10 h); ставится вместе с AutoCAD и Revit, поэтому есть там, где печатаем
GOST_FILE, GOST_FAMILY = "GOST_Common.ttf", "GOST Common"
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
    "ПВ_штриховка": (8, 18, True),      # тонкие линии по ГОСТ 2.303 - не тоньше s/3 = 0,17 мм
    "Размеры": (3, 18, True),
    "Рамка": (7, 70, True),
    "Штамп": (7, 25, True),
    "Надписи": (7, 25, True),
    "Видовой_экран": (8, 13, False),
    "Котлован": (7, 50, True),
    "Котлован_низ": (7, 25, True),
    "Бергштрихи": (7, 18, True),
    "Оси": (7, 18, True),
    "Конструкции": (7, 50, True),
    "Штриховка": (8, 18, True),
}
for name, (color, lw, plot) in LAYERS.items():
    lay = doc.layers.add(name, color=color, lineweight=lw)
    lay.dxf.plot = int(plot)

ds = doc.dimstyles.new("М1-2000")
for k, v in dict(dimtxsty=TXT, dimtxt=2.5, dimscale=SC, dimtsz=1.3, dimasz=2.5,
                 dimexe=1.5, dimexo=0.0, dimgap=0.8, dimdec=2, dimzin=8,
                 dimdsep=ord(","), dimtad=1, dimtih=0, dimtoh=0, dimlfac=1.0,
                 dimclrd=3, dimclre=3, dimclrt=3, dimtix=1, dimtmove=0, dimtfill=1,
                 dimdle=1.5).items():          # ГОСТ 2.307: размерная линия выходит за выносные на 1-3 мм
    ds.dxf.set(k, v)
for name, sc in (("М1-500", 0.5), ("М1-50", 0.05)):   # лист 2: размеры в мм (модель в м)
    d2 = doc.dimstyles.duplicate_entry("М1-2000", name)
    d2.dxf.dimscale = sc
    d2.dxf.dimlfac = 1000
    d2.dxf.dimdec = 0

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

# ---------- номера фигур ----------
LABEL_SHIFT = {"8'": (34, 28)}   # ручные сдвиги подписи (м): 8' закрыта котлованом
for fig in R.FIGS:
    cx, cy = map(f, fig["c"])
    dx, dy = LABEL_SHIFT.get(fig["name"], (0, 0))
    h_mm = H_HEAD if fig["F"] > 2500 else H_TEXT
    mtext(fig["name"], (cx + dx, cy + dy), h_mm, "Номера_фигур")

# ---------- ПВ / ПН ----------
ZONE = {"ПВ": (50, 28), "ПН": (450, 228)}
for t, p in ZONE.items():
    mtext(t, p, H_BIG, "ПВ_ПН")

# ---------- размеры до точек нулевых работ ----------
DOFF = 2.0 * SC          # отступ размерной линии от стороны квадрата, м


def dim(p1, p2, base, angle, override=None, style="М1-2000"):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=style,
                           override=override or {}, dxfattribs={"layer": "Размеры"})
    d.render()


def dim_text_outside(p1, p2, base, angle, style, sc, loc):
    """Размер, число которого не помещается между выносными: число в точке loc
    без выноски; продолжение размерной линии под числом чертится отдельно."""
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=style,
                           dxfattribs={"layer": "Размеры"})
    d.set_location(loc, leader=False)
    d.render()


def dim_on_shelf(p1, p2, base, angle, style, loc):
    """Размер с числом на полке линии-выноски (ГОСТ 2.307); loc - середина числа."""
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=style,
                           dxfattribs={"layer": "Размеры"})
    d.set_location(loc, leader=True)
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

# ---------- рабочие отметки в вершинах ----------
# после размеров: маска отметки ложится поверх концов размерных линий у вершины,
# а сдвиг 1,8 мм выводит её из-под засечки
for j in range(R.NY + 1):
    for i in range(R.NX + 1):
        x, y = R.xy(i, j)
        hv = R.h(i, j)
        mtext(fmt(hv), (f(x) + 1.8 * SC, f(y) + 0.8 * SC), H_TEXT, "Отметки", MA.BOTTOM_LEFT)
        msp.add_circle((f(x), f(y)), 0.5 * SC, dxfattribs={"layer": "Отметки"})

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

# ================= лист A3 =================
def a3(psp):
    """Параметры печати листа: A3 альбомный 1:1 на «DWG To PDF» без полей,
    веса линий - из слоёв, цвета - как на экране (acad.ctb)."""
    psp.page_setup(size=(420, 297), margins=(0, 0, 0, 0), units="mm", scale=(1, 1),
                   name="ISO_full_bleed_A3", device="DWG To PDF.pc3")
    psp.dxf_layout.dxf.current_style_sheet = "acad.ctb"
    for v in psp.query("VIEWPORT"):            # главный экран листа - на слое 0, иначе AUDIT AutoCAD ругается
        if v.dxf.id == 1:
            v.dxf.layer = "0"


psp = doc.layouts.get("Layout1")
doc.layouts.rename("Layout1", "Лист 1")
a3(psp)
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


def txt(s, pos, h=H_TEXT, align=TA.MIDDLE_CENTER, layer="Штамп", width=None):
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


# ---------- общие элементы оформления (константы - в начале файла) ----------
def num(v):
    return f"{round(f(v), 2):,.2f}".replace(",", " ").replace(".", ",")


def image_title(s, pos):
    txt(s, pos, H_TITLE, layer="Надписи", width=NARROW)


def volume_table(title, tab, cw):
    """Таблица объёмов: заголовок над ней, строки 7 мм; первый столбец - по левому
    краю, остальные - по центру."""
    txt(title, (TAB_X, TAB_Y), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
    for r, row in enumerate(tab):
        y = TAB_Y - 3 - 7 * r
        x = TAB_X
        for c, s in enumerate(row):
            pl([(x, y), (x + cw[c], y), (x + cw[c], y - 7), (x, y - 7)], "Штамп", True)
            al = TA.MIDDLE_LEFT if c == 0 else TA.MIDDLE_CENTER
            px = x + 1.5 if c == 0 else x + cw[c] / 2
            txt(s, (px, y - 3.5), H_TEXT, al, "Надписи", NARROW)
            x += cw[c]


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
        txt(s, (X0 + (colx[k] + colx[k + 1]) / 2, Y0 + 32.5), H_TEXT, width=NARROW)
    rows = [("Разработал", "Буев Д.Р."), ("Проверил", "Забелина О.Б."),
            ("Т. контр.", ""), ("", ""), ("Н. контр.", ""), ("Утв.", "")]
    for k, (role, who) in enumerate(rows):
        y = Y0 + 27.5 - 5 * k
        txt(role, (X0 + 1, y), H_TEXT, TA.MIDDLE_LEFT, width=NARROW)
        txt(who, (X0 + 21, y), H_TEXT, TA.MIDDLE_LEFT, width=NARROW)
    txt("НИУ МГСУ 08.05.01 - КР - 2026", (X0 + 125, Y0 + 50), H_HEAD)
    mt("Разработка технологической карты на производство\\Pземляных работ. Вариант 2, грунт - супесь",
       (X0 + 125, Y0 + 37.5), H_TEXT, 115)
    mt("Графическая часть\\Pкурсовой работы", (X0 + 100, Y0 + 22.5), H_TEXT, 66)
    txt("Стадия", (X0 + 142.5, Y0 + 27.5), H_TEXT, width=NARROW)
    txt("Лист", (X0 + 157.5, Y0 + 27.5), H_TEXT, width=NARROW)
    txt("Листов", (X0 + 175, Y0 + 27.5), H_TEXT, width=NARROW)
    txt("У", (X0 + 142.5, Y0 + 20), H_HEAD)
    txt(str(sheet), (X0 + 157.5, Y0 + 20), H_HEAD)
    if sheets:
        txt(str(sheets), (X0 + 175, Y0 + 20), H_HEAD)
    mt(name, (X0 + 100, Y0 + 7.5), H_TEXT, 68)
    mt("\\W0.8;Кафедра технологий\\Pи организации строительного\\Pпроизводства", (X0 + 160, Y0 + 7.5),
       H_TEXT, 48)

    # заголовок листа
    if title:
        image_title(title, (217.5, TITLE_Y))


frame_and_stamp(1, 2, "План строительной площадки\\Pс рабочими отметками и ЛНР\\PМ 1:2000",
                "План строительной площадки с рабочими отметками и линией нулевых работ  М 1:2000")

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
txt("Условные обозначения", (LX, LY), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
items = [
    ("lnr", "линия нулевых работ (ЛНР)"),
    ("hatch", "ПВ - планировочная выемка"),
    ("box", "ПН - планировочная насыпь"),
    ("mark", "рабочая отметка, м (+ насыпь, - выемка)"),
    ("fig", "номер фигуры; со штрихом - насыпная часть квадрата"),
    ("dim", "расстояние до точки нулевых работ, м"),
    ("pit", "контур котлована"),
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
        txt("+0,15", (sx0 + 2.8, y - 0.7), H_TEXT, TA.BOTTOM_LEFT, "Отметки")
    elif kind == "fig":
        txt("7'", (sx0 + 7, y), H_HEAD, TA.MIDDLE_CENTER, "Номера_фигур")
    elif kind == "dim":
        psp.add_line((sx0, y - 1.5), (sx1, y - 1.5), dxfattribs={"layer": "Размеры"})
        for xx in (sx0, sx1):
            psp.add_line((xx - 0.9, y - 2.4), (xx + 0.9, y - 0.6), dxfattribs={"layer": "Размеры"})
        txt("37,5", ((sx0 + sx1) / 2, y - 0.7), H_TEXT, TA.BOTTOM_CENTER, "Размеры")
    elif kind == "pit":
        pl([(sx0, y - 2.5), (sx1, y - 2.5), (sx1, y + 2.5), (sx0, y + 2.5)], "Котлован", True)
        pl([(sx0 + 0.8, y - 1.7), (sx1 - 0.8, y - 1.7), (sx1 - 0.8, y + 1.7), (sx0 + 0.8, y + 1.7)],
           "Котлован_низ", True)
    txt("- " + label, (sx1 + 3, y), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)

# ---------- сводка объёмов ----------
Vc = sum(g["V"] for g in R.FIGS if g["sign"] < 0)
Vf = sum(g["V"] for g in R.FIGS if g["sign"] > 0)
Fc = sum(g["F"] for g in R.FIGS if g["sign"] < 0)
Ff = sum(g["F"] for g in R.FIGS if g["sign"] > 0)
volume_table("Объемы планировочных работ",
             [("", f"F, {M2}", f"V, {M3}"),
              ("Выемка ПВ", num(Fc), num(Vc)),
              ("Насыпь ПН", num(Ff), num(Vf)),
              (f"ПН / Kор, Kор = {K_OR:.2f}".replace(".", ","), "", num(f(Vf) / K_OR))],
             [34, 32, 30])

# ================= лист 2: котлован =================
# Оформление по СПДС: ГОСТ Р 21.101 (отметки, оси, выноски), ГОСТ 2.303 (линии),
# ГОСТ 2.304 (шрифт тип Б), ГОСТ 2.305 (обозначение разреза), ГОСТ 2.306 (штриховки),
# ГОСТ 2.307 (размеры: в мм, засечки). Отметки - в метрах от 0,000 = проектная отметка планировки.
S5, S50 = 0.5, 0.05                    # м модели в 1 мм листа: М 1:500 и М 1:50
DX2 = 800.0                            # план котлована 1:500 - копия, сдвинутая по x
NDX, NDY = 2000.0, 0.0                 # разрез 1:50: ось стены x = 0, естественная поверхность y = 0
X0, Y0 = f(K.X0) + DX2, f(K.Y0)
DT = f(K.D_NIZ + K.L_OTK)              # ось -> бровка
DNZ = f(K.D_NIZ)
HR_ = f(K.HR)


def line(p1, p2, layer, **kw):
    at = {"layer": layer}
    at.update(kw)
    return msp.add_line(p1, p2, dxfattribs=at)


def axis_bubble(c, r, s_, sc):
    """Маркировочный кружок оси: шрифт в 1,5-2 раза крупнее размерных чисел (ГОСТ Р 21.101)."""
    msp.add_circle(c, r, dxfattribs={"layer": "Оси"})
    mtext(s_, c, H_AXIS, "Оси", mask=False, sc=sc)


def axis_line(p0, p1, sc):
    """Ось от кружка p0 в сторону p1. Длина подогнана под целое число периодов,
    чтобы линия начиналась и кончалась штрихом (ГОСТ 2.303)."""
    (x0, y0), (x1, y1) = p0, p1
    L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    cyc = DD_STROKE + 2 * DD_GAP + DD_DOT
    n = max(0, round((L / sc - DD_STROKE) / cyc))
    k = (DD_STROKE + n * cyc) * sc / L
    line(p0, (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k), "Оси", linetype=DASHDOT)


def dot(c, sc):
    """Точка на конце выноски (ГОСТ 2.316), диаметр 1 мм."""
    h = msp.add_hatch(color=7, dxfattribs={"layer": "Надписи"})
    h.paths.add_edge_path().add_arc(c, 0.5 * sc, 0, 360)


def level(p, value, sc, side=1, ext_from=None, down=False):
    """Знак отметки уровня (ГОСТ Р 21.101): стрелка 90° вершиной на уровень,
    полка со значением в метрах. Слой «Отметки» - как рабочие отметки на листе 1.
    side: 1 - полка вправо, -1 - влево; down - знак под уровнем."""
    x, y = p
    a = 2.0 * sc
    v = -a if down else a
    if ext_from is not None:                    # выносная линия уровня от изображения
        line((ext_from, y), (x + side * 1.0 * sc, y), "Отметки")
    line((x - a, y + v), (x, y), "Отметки")
    line((x, y), (x + a, y + v), "Отметки")
    shelf = 11.0 * sc
    line((x - side * a, y + v), (x + side * shelf, y + v), "Отметки")
    tx = x + 0.6 * sc if side > 0 else x - shelf + 0.4 * sc
    if down:
        mtext(value, (tx, y + v - 0.5 * sc), H_TEXT, "Отметки", MA.TOP_LEFT, mask=False, sc=sc)
    else:
        mtext(value, (tx, y + v + 0.5 * sc), H_TEXT, "Отметки", MA.BOTTOM_LEFT, mask=False, sc=sc)


def soil(points, sc, step=6.0, n=3, gap=0.9, ln_=2.2):
    """Грунт естественный (ГОСТ 2.306): группы по n штрихов под 45° вдоль контура,
    со стороны грунта - справа по ходу обхода."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        nx, ny = uy, -ux                         # нормаль в сторону грунта
        dx, dy = (nx - ux) / 2 ** 0.5, (ny - uy) / 2 ** 0.5
        t = 1.5 * sc
        while t + (n - 1) * gap * sc <= L - 0.5 * sc:
            for k in range(n):
                px, py = x1 + ux * (t + k * gap * sc), y1 + uy * (t + k * gap * sc)
                line((px, py), (px + dx * ln_ * sc, py + dy * ln_ * sc), "Штриховка")
            t += step * sc


def section_mark(x, y0, y1, sc, label, look=-1):
    """Штрих линии разреза (ГОСТ 2.305): от y0 к y1 (8-20 мм), стрелка по взгляду
    в 2-3 мм от внешнего конца штриха."""
    # разомкнутая линия: толщина от s до 1,5s (ГОСТ 2.303), s = 0,5 мм
    msp.add_lwpolyline([(x, y0), (x, y1)], dxfattribs={"layer": "Конструкции", "const_width": 0.7 * sc})
    ya = y1 - (y1 - y0) / abs(y1 - y0) * 2.5 * sc
    line((x, ya), (x + look * 5.0 * sc, ya), "Конструкции", lineweight=25)
    msp.add_lwpolyline([(x + look * 2.5 * sc, ya, 1.2 * sc, 0.0), (x + look * 5.0 * sc, ya)], format="xyse",
                       dxfattribs={"layer": "Конструкции"})
    mtext(label, (x + look * 7.5 * sc, ya), H_BIG, "Надписи", mask=False, sc=sc)


# ---------- план котлована М 1:500 ----------
draw_pit(dx=DX2, berg=True)
R1, R2 = 3.0, 6.0                      # ряды размеров от бровки, м (6 и 12 мм на листе)
yb, yt, xl = Y0 - DT, Y0 + 30 + DT, X0 - DT
BUB = 2.0                              # кружок оси диаметром 8 мм
for s_, x in (("1", X0), ("2", X0 + 18), ("3", X0 + 60)):
    axis_line((x, yb - R2 - 3.0), (x, yt + 1.5), S5)
    axis_bubble((x, yb - R2 - 3.0 - BUB), BUB, s_, S5)
for s_, y in (("А", Y0), ("Б", Y0 + 12), ("В", Y0 + 30)):
    axis_line((xl - 12.0 - 3.0, y), (X0 + 60 + DT + 1.5, y), S5)
    axis_bubble((xl - 12.0 - 3.0 - BUB, y), BUB, s_, S5)
st5 = "М1-500"
dim((X0, yb - 1), (X0 + 18, yb - 1), (0, yb - R1), 0, style=st5)
dim((X0 + 18, yb - 1), (X0 + 60, yb - 1), (0, yb - R1), 0, style=st5)
dim((X0, yb - 1), (X0 + 60, yb - 1), (0, yb - R2), 0, style=st5)
dim((X0 - DNZ, Y0 + 30 + DNZ), (X0 + 60 + DNZ, Y0 + 30 + DNZ), (0, yt + R1), 0, style=st5)
dim((X0 - DT, yt), (X0 + 60 + DT, yt), (0, yt + R2), 0, style=st5)
dim((xl - 1, Y0), (xl - 1, Y0 + 12), (xl - R1, 0), 90, style=st5)
dim((xl - 1, Y0 + 12), (xl - 1, Y0 + 30), (xl - R1, 0), 90, style=st5)
dim((xl - 1, Y0), (xl - 1, Y0 + 30), (xl - R2, 0), 90, style=st5)
dim((X0 - DNZ, Y0 - DNZ), (X0 - DNZ, Y0 + 30 + DNZ), (xl - 9.0, 0), 90, style=st5)
dim((xl, Y0 - DT), (xl, yt), (xl - 12.0, 0), 90, style=st5)
# пандус: длина, ширина, уклон
(xe, y1), (_, y2) = [(f(a) + DX2, f(b)) for a, b in RG["end"]]
xb = f(K.PAN_X) + DX2
g1, g2 = f(RG["gap"][0]), f(RG["gap"][1])
dim((xb, y2), (xe, y2), (0, g2 + 3.0), 0, style=st5)
# ширина пандуса 6 мм на листе - число не помещается между выносными, поэтому
# оно на продолжении размерной линии за верхней выносной (ГОСТ 2.307)
TXT_W = 6.5                                    # длина «3000» шрифтом 2,5 мм, мм листа
xd = xe + 3.0
dim_text_outside((xe, y1), (xe, y2), (xd, 0), 90, st5, S5,
                 (xd - (0.8 + 1.25) * S5, y2 + (1.5 + 0.8 + TXT_W / 2) * S5))
line((xd, y2 + 1.5 * S5), (xd, y2 + (1.5 + 0.8 + TXT_W + 0.5) * S5), "Размеры")
# бергштрихи на откосах пандуса: от бровки к подошве, через 2 мм листа
for (pb, pe), ytoe in zip(RG["brow"], (y1, y2)):
    (bx0, by0), (bx1, by1) = (f(pb[0]) + DX2, f(pb[1])), (f(pe[0]) + DX2, f(pe[1]))
    xx, odd = bx0 + 1.0, False
    while xx < bx1 - 0.5:
        yb_ = by0 + (by1 - by0) * (xx - bx0) / (bx1 - bx0)
        if abs(yb_ - ytoe) > 0.3:
            ye_ = yb_ + (ytoe - yb_) * (0.5 if odd else 1.0)
            line((xx, yb_), (xx, ye_), "Бергштрихи")
        xx += 1.0; odd = not odd
ya = g1 - 2.5
line((xe - 1.0, ya), (xb + 4.0, ya), "Размеры")
msp.add_lwpolyline([(xb + 6.0, ya, 0.7, 0.0), (xb + 4.0, ya)], format="xyse", dxfattribs={"layer": "Размеры"})
mtext("i=" + K.f(K.I_PAN), ((xb + xe) / 2 + 1.0, ya - 0.6), H_TEXT, "Размеры", MA.TOP_CENTER, mask=False, sc=S5)
# отметка дна на плане - в прямоугольнике
bx, by = X0 + 30, Y0 + 21
mtext(f"-{float(K.NK):.3f}".replace(".", ","), (bx, by), H_TEXT, "Отметки", mask=False, sc=S5)
msp.add_lwpolyline([(bx - 3.6, by - 1.4), (bx + 3.6, by - 1.4), (bx + 3.6, by + 1.4), (bx - 3.6, by + 1.4)],
                   close=True, dxfattribs={"layer": "Отметки"})
# разрез 1-1: по левому крылу (между осями 1 и 2), взгляд на запад;
# штрих 10 мм, обозначение подальше от кружка оси 1
xs = X0 + 12
section_mark(xs, yb - R2 - 1.0, yb - R2 - 6.0, S5, "1")
section_mark(xs, yt + R2 + 1.0, yt + R2 + 6.0, S5, "1")


# ---------- разрез 1-1 (фрагмент) М 1:50 ----------
def N(x, y):
    return (NDX + x, NDY + y)


HK_, L_ = f(K.HK), f(K.L_OTK)
XB, XT = -(DNZ + L_), -DNZ                     # бровка и низ откоса
YP = -HK_ + f(K.H_PODS)
YBP = YP + f(K.H_BP)
YFP = YBP + f(K.H_FP)
YW, XR, GL = 0.3, 1.0, -4.8                   # верх стены (обрыв), обрыв справа, начало земли
D_FP, D_BP, D_ST = f(K.D_FP), f(K.D_BP), f(K.D_ST)
ground = [N(GL, 0), N(XB, 0), N(XT, -HK_), N(XR, -HK_)]
msp.add_lwpolyline(ground, dxfattribs={"layer": "Котлован"})
soil(ground, S50)


def layer3(x0, y0, x1, y1, pattern, scale, angle=0.0):
    """Слой до обрыва справа: левая, верхняя и нижняя грани - основной линией, штриховка."""
    msp.add_lwpolyline([N(x1, y1), N(x0, y1), N(x0, y0), N(x1, y0)], dxfattribs={"layer": "Конструкции"})
    for pat, sc_, ang in pattern:
        h = msp.add_hatch(color=8, dxfattribs={"layer": "Штриховка"})
        h.set_pattern_fill(pat, scale=sc_, angle=ang, color=8)
        h.paths.add_polyline_path([N(x0, y0), N(x1, y0), N(x1, y1), N(x0, y1)], is_closed=True)


layer3(XT, -HK_, XR, YP, [("AR-SAND", 0.004, 0)], 0)                      # подсыпка (щебень)
layer3(-D_BP, YP, XR, YBP, [("AR-CONC", 0.004, 0)], 0)                    # бетон
layer3(-D_FP, YBP, XR, YFP, [("ANSI31", 0.03, 0), ("AR-CONC", 0.004, 0)], 0)   # железобетон
wall = [N(D_ST, YFP), N(D_ST, YW), N(-D_ST, YW), N(-D_ST, YFP)]
msp.add_lwpolyline([N(-D_ST, YW), N(-D_ST, YFP)], dxfattribs={"layer": "Конструкции"})
msp.add_lwpolyline([N(D_ST, YFP), N(D_ST, YW)], dxfattribs={"layer": "Конструкции"})
for pat, sc_ in (("ANSI31", 0.03), ("AR-CONC", 0.004)):
    h = msp.add_hatch(color=8, dxfattribs={"layer": "Штриховка"})
    h.set_pattern_fill(pat, scale=sc_, color=8)
    h.paths.add_polyline_path(wall, is_closed=True)
line(N(-D_BP, YBP), N(XR, YBP), "Конструкции", lineweight=70)            # гидроизоляция
# линии обрыва (тонкие, с изломом)
YM = (YBP + YFP) / 2
msp.add_lwpolyline([N(XR, -HK_ - 0.15), N(XR, YM - 0.06), N(XR + 0.08, YM - 0.02), N(XR - 0.08, YM + 0.02),
                    N(XR, YM + 0.06), N(XR, YFP + 0.15)], dxfattribs={"layer": "Надписи"})
msp.add_lwpolyline([N(-D_ST - 0.15, YW), N(-0.06, YW), N(-0.02, YW + 0.08), N(0.02, YW - 0.08),
                    N(0.06, YW), N(D_ST + 0.15, YW)], dxfattribs={"layer": "Надписи"})
# ось А
axis_line(N(0, YW + 0.25), N(0, -HK_ - 0.3), S50)
axis_bubble(N(0, YW + 0.25 + 0.2), 0.2, "А", S50)
# проектная поверхность планировки - тонкая штриховая
line(N(GL, HR_), N(-D_ST, HR_), "Котлован_низ", linetype=DASH)
mtext(f"1:{K.f(K.M)}", N((XB + XT) / 2 - 0.3, -HK_ / 2), H_TEXT, "Надписи", rot=-56.2, mask=False, sc=S50)
# отметки уровней, м
mk = lambda y: ("+" if y - HR_ > 1e-9 else "-" if y - HR_ < -1e-9 else "") + f"{abs(y - HR_):.3f}".replace(".", ",")
level(N(GL + 0.4, HR_), "0,000", S50)
line(N(XB, 0), N(XB + 0.75, 0), "Размеры")
level(N(XB + 0.55, 0), mk(0), S50, down=True)
level(N(XT - 0.9, -HK_), mk(-HK_), S50, ext_from=NDX + XT)
level(N(-0.45, YFP), mk(YFP), S50, side=-1)
# размеры, мм
st50 = "М1-50"
yd1, yd2 = -HK_ - 0.45, -HK_ - 0.95           # ряды размеров: 9 и 19 мм под дном
pt = lambda x: N(x, 0 if x == XB else -HK_)
for a, b in ((XB, XT), (XT, -D_BP), (-D_FP, -D_ST)):
    dim(pt(a), pt(b), N(0, yd1), 0, {"dimtad": 1}, style=st50)
# 200 мм = 4 мм листа: число не помещается между выносными (ГОСТ 2.307)
W200 = 2.1 * 2.5 * S50                         # «200» шрифтом 2,5 мм, м модели
dim_on_shelf(pt(-D_BP), pt(-D_FP), N(0, yd1), 0, st50,            # между двумя 500 - на полке
             N((-D_BP - D_FP) / 2 + 0.25, yd1 - 0.21))
x200 = 1.5 * S50 + 0.8 * S50                   # у оси - на продолжении размерной линии
dim_text_outside(pt(-D_ST), pt(0), N(0, yd1), 0, st50, S50,
                 N(x200 + W200 / 2, yd1 + (0.8 + 1.25) * S50))
line(N(1.5 * S50, yd1), N(x200 + W200 + 0.5 * S50, yd1), "Размеры")
dim(N(XB, 0), N(0, -HK_), N(0, yd2), 0, style=st50)
# многослойная выноска (сверху вниз - как слои)
LAY = [(YM, f"Фундаментная плита - {int(K.H_FP * 1000)}"),
       (YBP, "Гидроизоляция - 2 слоя"),
       ((YP + YBP) / 2, f"Бетонная подготовка - {int(K.H_BP * 1000)}"),
       ((-HK_ + YP) / 2, f"Подсыпка из щебня - {int(K.H_PODS * 1000)}")]
XL = 0.6
SH0, SHD, SHL = -0.25, 0.3, 2.6               # верхняя полка, шаг полок, длина полки
line(N(XL, LAY[-1][0]), N(XL + 0.35, SH0 - SHD * (len(LAY) - 1)), "Надписи")
line(N(XL + 0.35, SH0 - SHD * (len(LAY) - 1)), N(XL + 0.35, SH0), "Надписи")
for k_, (yy, s_) in enumerate(LAY):
    dot(N(XL, yy) if k_ == len(LAY) - 1 else N(XL + 0.35 * (yy - LAY[-1][0]) / (SH0 - SHD * 3 - LAY[-1][0]), yy),
        S50)
    ys = SH0 - SHD * k_
    line(N(XL + 0.35, ys), N(XL + 0.35 + SHL, ys), "Надписи")
    mtext(s_, N(XL + 0.4, ys + 0.03), H_TEXT, "Надписи", MA.BOTTOM_LEFT, mask=False, sc=S50)

# ---------- лист ----------
psp = doc.layouts.new("Лист 2")
a3(psp)
frame_and_stamp(2, None, "План котлована М 1:500.\\PРазрез 1-1 М 1:50", None)


def viewport(px0, py0, px1, py1, mx0, my0, sc):
    w_, h_ = px1 - px0, py1 - py0
    v = psp.add_viewport(center=((px0 + px1) / 2, (py0 + py1) / 2), size=(w_, h_),
                         view_center_point=(mx0 + w_ * sc / 2, my0 + h_ * sc / 2), view_height=h_ * sc)
    v.dxf.layer = "Видовой_экран"
    v.dxf.flags = v.dxf.flags | 16384
    return v


# компоновка как на листе 1: изображения сверху, таблица объёмов в нижней полосе
# на том же месте; разрез справа над примечаниями и штампом
viewport(25, 153, 257, 277, xl - 12.0 - 3.0 - 2 * BUB - 2.0, yb - R2 - 3.0 - 2 * BUB - 1.0, S5)
viewport(230, 77, 413, 164, NDX + GL - 0.3, NDY - HK_ - 1.1, S50)
image_title("План котлована  М 1:500", (141, TITLE_Y))
image_title("Разрез 1-1  М 1:50", (321.5, 168))

volume_table("Объемы работ по котловану",
             [("Наименование работ", f"V, {M3}"),
              ("Разработка грунта в котловане (с пандусом)", num(K.V_K)),
              ("Устройство подсыпки из щебня", num(K.V_PODS)),
              ("Устройство бетонной подготовки", num(K.V_BP)),
              ("Обратная засыпка пазух", num(K.V_OZ))],
             [66, 30])                     # ширина 96 мм - как у таблицы листа 1
# примечания - над основной надписью (ГОСТ 2.316), шириной не более её
mt("1. Размеры даны в миллиметрах, отметки - в метрах.\\P"
   "2. За отметку 0,000 принята проектная отметка планировки площадки.",
   (232, 63), H_TEXT, 181, MA.BOTTOM_LEFT, "Надписи")

if "VIEWPORTS" in doc.layers:                   # слой ezdxf для главных экранов - больше не нужен
    doc.layers.remove("VIEWPORTS")
out = "План_ЛНР_вариант2.dxf"
doc.saveas(out)
print("saved", out, "viewport", vw, vh, vc)
