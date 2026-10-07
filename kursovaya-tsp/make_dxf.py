"""Графическая часть - только листы из разд. 3 методички, каждый A3:
  Лист 1 - черновик: план площадки с рабочими отметками и ЛНР, М 1:2000;
  Лист 2 - план площадки с окончательными рабочими отметками (после Δh), ЛНР
           и обводами, Мг 1:2000, Мв 1:100;
  Лист 3 - продольный 1-1 и поперечный 2-2 разрезы площадки по котловану, Мг 1:2000, Мв 1:100.

Модель - в метрах в натуральную величину (площадка 500 x 300 м, начало
в левом нижнем углу); окончательный план и разрезы - копии ниже по y.
Листы - в пространстве листа: рамка, штамп по форме 3 ГОСТ Р 21.101,
видовые экраны 1:2000 (1 мм листа = 2 м). DWG и PDF - через vypusk_acad.py.
"""
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA, MTextEntityAlignment as MA
from fractions import Fraction as Fr
import raschet as R
import kotlovan as K
import balans as B

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
# GOST type B - шрифт АСКОН по ГОСТ 2.304-81 тип Б (прописные 6/10 h, строчные 7/10 h,
# интервал 2/10 h), файл GOST_B.TTF, как в КОМПАС-3D; должен быть установлен в Windows
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
    "ПВ_штриховка": (8, 18, True),      # тонкие линии по ГОСТ 2.303 - не тоньше s/3 = 0,17 мм
    "Размеры": (3, 18, True),
    "Рамка": (7, 70, True),
    "Штамп": (7, 25, True),
    "Надписи": (7, 25, True),
    "Видовой_экран": (8, 13, False),
    "Котлован": (7, 50, True),
    "Котлован_низ": (7, 25, True),
    "Бергштрихи": (7, 18, True),
    "Обводы": (7, 25, True),             # внешняя граница обводов площадки
    "Профиль": (7, 50, True),            # поверхность грунта на разрезах
    "Проектная": (1, 25, True),          # проектная плоскость на разрезах
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
VS = 20.0          # разрезы и обводы: Мв 1:100 на плане Мг 1:2000 - 1 м высоты = 10 мм листа = 20 м модели
d2 = doc.dimstyles.duplicate_entry("М1-2000", "Мв1-100")   # высоты на разрезах - в мм
d2.dxf.dimlfac = 1000 / VS
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


# ================= план площадки: общий для черновика (лист 1) и окончательного (лист 2) =================
W, Hh = R.A * R.NX, R.A * R.NY
DOFF = 2.0 * SC          # отступ размерной линии от стороны квадрата, м
OY2 = -1000.0            # окончательный план - копия в модели ниже черновика


def line(p1, p2, layer, **kw):
    at = {"layer": layer}
    at.update(kw)
    return msp.add_line(p1, p2, dxfattribs=at)


def dim(p1, p2, base, angle, override=None, style="М1-2000", text="<>"):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=style, text=text,
                           override=override or {}, dxfattribs={"layer": "Размеры"})
    d.render()


def lnr_chain(P):
    """ЛНР одной полилинией через все точки нулевых работ."""
    segs = []
    for sq in range(1, R.NX * R.NY + 1):
        figs = [g for g in P["FIGS"] if g["sq"] == sq]
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
    return chain


def adjacent(P, q1, q2):
    """Фигуры, у которых отрезок q1-q2 - сторона; -> [(фигура, сторона ±1)]."""
    res = []
    for g in P["FIGS"]:
        pts = [tuple(map(f, p)) for p in g["poly"]]
        n = len(pts)
        for k in range(n):
            if {pts[k], pts[(k + 1) % n]} == {q1, q2}:
                cx, cy = map(f, g["c"])
                side = (cy > q1[1]) if q1[1] == q2[1] else (cx > q1[0])
                res.append((g, 1 if side else -1))
    return res


def draw_pit(k, dx=0.0, dy=0.0):
    """Контуры котлована: бровка (с пандусом) - толстая, подошва - тонкая."""
    P = lambda p: (f(p[0]) + dx, f(p[1]) + dy)
    rg = K.ramp_geometry(k)
    V, Nz = k["VERH"], k["NIZ"]
    xr = V[3][0]
    g1, g2 = rg["gap"]
    (xe, y1), (_, y2) = rg["end"]
    top = [(xr, g2), V[4], V[5], V[0], V[1], V[2], V[3], (xr, g1), (xe, y1), (xe, y2)]
    msp.add_lwpolyline([P(p) for p in top], close=True, dxfattribs={"layer": "Котлован"})
    msp.add_lwpolyline([P(p) for p in Nz], close=True, dxfattribs={"layer": "Котлован_низ"})
    for a, b in rg["toe"] + rg["edge"]:
        msp.add_line(P(a), P(b), dxfattribs={"layer": "Котлован_низ"})


def site_plan(P, k, oy=0.0, final=False):
    """План площадки 1:2000. Черновик (лист 1): штриховка ПВ, номера фигур, габаритные
    размеры. Окончательный (лист 2, прил. 10): без них, размеры до точек нуля на
    границе - внутрь площадки (снаружи - обводы)."""
    O = lambda x, y: (f(x), f(y) + oy)
    for j in range(R.NY + 1):
        line(O(0, j * R.A), O(W, j * R.A), "Сетка")
    for i in range(R.NX + 1):
        line(O(i * R.A, 0), O(i * R.A, Hh), "Сетка")
    if not final:                                   # штриховка выемки
        for fig in P["FIGS"]:
            if fig["sign"] < 0:
                hat = msp.add_hatch(color=8, dxfattribs={"layer": "ПВ_штриховка"})
                hat.set_pattern_fill("ANSI31", scale=2.4, color=8)
                hat.paths.add_polyline_path([O(x, y) for x, y in fig["poly"]], is_closed=True)
    msp.add_lwpolyline([O(*p) for p in lnr_chain(P)], dxfattribs={"layer": "ЛНР", "const_width": 0.6 * SC})
    if not final:                                   # номера фигур
        shift = {"8'": (34, 28)}                    # ручные сдвиги подписи (м): 8' закрыта котлованом
        for fig in P["FIGS"]:
            cx, cy = map(f, fig["c"])
            dx, dy = shift.get(fig["name"], (0, 0))
            mtext(fig["name"], O(cx + dx, cy + dy), H_HEAD if fig["F"] > 2500 else H_TEXT, "Номера_фигур")
    for t, p in {"ПВ": (50, 28), "ПН": (450, 228)}.items():
        mtext(t, O(*p), H_BIG, "ПВ_ПН")

    # размеры до точек нулевых работ
    border_off = {"top": 7.0 * SC, "other": 2.0 * SC}
    for z in P["ZP"]:
        a, b = z["p1"], z["p2"]
        ia, ja = (a - 1) % (R.NX + 1), (a - 1) // (R.NX + 1)
        ib, jb = (b - 1) % (R.NX + 1), (b - 1) // (R.NX + 1)
        pa, pb = tuple(map(f, R.xy(ia, ja))), tuple(map(f, R.xy(ib, jb)))
        pz = tuple(map(f, z["pt"]))
        horiz = ja == jb
        for q1, q2 in ((pa, pz), (pz, pb)):
            adj = adjacent(P, q1, q2)
            if len(adj) == 1:                 # граница площадки - размер снаружи
                side = -adj[0][1]
                top = horiz and q1[1] == Hh
                off = border_off["top"] if top or final else border_off["other"]   # окончательный - за обводами
            else:                             # внутри - со стороны большей фигуры
                side = max(adj, key=lambda t: t[0]["F"])[1]
                off = border_off["other"]
            if horiz:
                dim(O(*q1), O(*q2), O(q1[0], q1[1] + side * off), 0, {"dimtad": 1 if side > 0 else 4})
            else:
                lo, hi = sorted((q1, q2), key=lambda p: p[1])
                dim(O(*lo), O(*hi), O(q1[0] + side * off, q1[1]), 90, {"dimtad": 4 if side > 0 else 1})
    if not final:                                   # габаритные размеры
        for i in range(R.NX):
            dim(O(i * R.A, 0), O((i + 1) * R.A, 0), O(0, -11 * SC), 0)
        dim(O(0, 0), O(W, 0), O(0, -18 * SC), 0)
        for j in range(R.NY):
            dim(O(0, j * R.A), O(0, (j + 1) * R.A), O(-6 * SC, 0), 90)
        dim(O(0, 0), O(0, Hh), O(-13 * SC, 0), 90)
    draw_pit(k, dy=oy)
    if final:
        obvody(P, oy)                               # до отметок: маска отметки ложится поверх штрихов

    # рабочие отметки в вершинах - после размеров: маска ложится поверх концов размерных
    # линий у вершины, сдвиг 1,8 мм выводит её из-под засечки
    for j in range(R.NY + 1):
        for i in range(R.NX + 1):
            x, y = map(f, R.xy(i, j))
            hv = P["h"](i, j)
            mtext(fmt4(hv) if final else fmt(hv), O(x + 1.8 * SC, y + 0.8 * SC), H_TEXT, "Отметки",
                  MA.BOTTOM_LEFT)
            msp.add_circle(O(x, y), 0.5 * SC, dxfattribs={"layer": "Отметки"})


def fmt4(v):
    """Окончательная рабочая отметка: h + Δh, четыре знака."""
    s = f"{abs(f(v)):.4f}".replace(".", ",")
    return s if v == 0 else ("+" if v > 0 else "-") + s


site_plan(R.P0, K.K0)                               # лист 1: черновик

# ================= листы 2 и 3: окончательный план с обводами, разрезы по котловану =================
TICK = 5.0               # шаг бергштрихов, м модели (2,5 мм листа)


def perimeter_points(P):
    """Стороны контура по часовой от левого верхнего угла: [(нормаль наружу,
    [(x, y, h), ...] от начала стороны к концу, с точками нуля)]."""
    corners = [(0, 0), (R.NX, 0), (R.NX, R.NY), (0, R.NY)]           # узлы (i, j)
    normals = [(0, 1), (1, 0), (0, -1), (-1, 0)]                      # верх, право, низ, лево
    sides = []
    for s in range(4):
        (i1, j1), (i2, j2) = corners[s], corners[(s + 1) % 4]
        n = max(abs(i2 - i1), abs(j2 - j1))
        di, dj = (i2 - i1) // n, (j2 - j1) // n
        pts = []
        for t in range(n + 1):
            p = (i1 + di * t, j1 + dj * t)
            x, y = map(f, R.xy(*p))
            pts.append((x, y, P["h"](*p)))
            if t < n:
                q = (p[0] + di, p[1] + dj)
                h1, h2 = P["h"](*p), P["h"](*q)
                if h1 * h2 < 0:
                    tt = abs(h1) / (abs(h1) + abs(h2))
                    (x2, y2) = map(f, R.xy(*q))
                    pts.append((x + (x2 - x) * f(tt), y + (y2 - y) * f(tt), Fr(0)))
        sides.append((normals[s], pts))
    return sides


def obvody(P, oy):
    """Обводы площадки: снаружи контура - полоса шириной |h|·VS (Мв 1:100),
    в точках нуля сходит на нет; бергштрихи - от бровки: у выемки бровка -
    внешняя граница полосы, у насыпи - контур площадки."""
    sides = perimeter_points(P)
    for (nx, ny), pts in sides:
        outer = [(x + nx * f(abs(h)) * VS, y + ny * f(abs(h)) * VS + oy) for x, y, h in pts]
        msp.add_lwpolyline(outer, dxfattribs={"layer": "Обводы"})
        # бергштрихи по участкам между соседними точками
        L = abs(pts[-1][0] - pts[0][0]) + abs(pts[-1][1] - pts[0][1])
        ux, uy = (pts[-1][0] - pts[0][0]) / L, (pts[-1][1] - pts[0][1]) / L
        t, odd = TICK, False
        while t < L - TICK / 2:
            for (x1, y1, h1), (x2, y2, h2) in zip(pts, pts[1:]):
                a = abs(x1 - pts[0][0]) + abs(y1 - pts[0][1])
                b = abs(x2 - pts[0][0]) + abs(y2 - pts[0][1])
                if a <= t <= b:
                    w = (t - a) / (b - a)
                    hv = f(h1) + (f(h2) - f(h1)) * w
                    break
            d = abs(hv) * VS
            if d > 0.6:
                px, py = pts[0][0] + ux * t, pts[0][1] + uy * t + oy
                ln_ = d if not odd else d / 2
                if hv < 0:              # выемка: штрих от внешней границы к контуру
                    sx, sy = px + nx * d, py + ny * d
                    line((sx, sy), (sx - nx * ln_, sy - ny * ln_), "Бергштрихи")
                else:                   # насыпь: от контура наружу
                    line((px, py), (px + nx * ln_, py + ny * ln_), "Бергштрихи")
            t += TICK; odd = not odd
    # углы: внешние границы сторон сходятся по диагонали угла
    for s in range(4):
        (nx1, ny1), pts1 = sides[s - 1]
        (nx2, ny2), pts2 = sides[s]
        x, y, h = pts2[0]
        d = f(abs(h)) * VS
        a = (x + nx1 * d, y + ny1 * d + oy)
        b = (x + nx2 * d, y + ny2 * d + oy)
        c = (x + (nx1 + nx2) * d, y + (ny1 + ny2) * d + oy)
        msp.add_lwpolyline([a, c, b], dxfattribs={"layer": "Обводы"})
        line((x, y + oy), c, "Обводы")


def level_mark(p, value, ang=0.0, side=1, down=False):
    """Знак отметки уровня (ГОСТ Р 21.101): стрелка 90° вершиной на уровень, полка
    со значением в метрах; ang - поворот знака, side - полка вправо/влево, down - под уровнем."""
    from math import cos, sin, radians
    c, s_ = cos(radians(ang)), sin(radians(ang))
    T = lambda u, v: (p[0] + u * c - v * s_, p[1] + u * s_ + v * c)
    a = 2.0 * SC
    v = -a if down else a
    shelf = 11.0 * SC
    line(T(-a, v), T(0, 0), "Отметки")
    line(T(0, 0), T(a, v), "Отметки")
    line(T(-side * a, v), T(side * shelf, v), "Отметки")
    tx = 0.6 * SC if side > 0 else -shelf + 0.4 * SC
    ty = v - 0.5 * SC if down else v + 0.5 * SC
    al = MA.TOP_LEFT if down else MA.BOTTOM_LEFT
    mtext(value, T(tx, ty), H_TEXT, "Отметки", al, mask=False, rot=ang)


def lev(v):
    """Отметка уровня относительно проектной плоскости, м, три знака (ГОСТ Р 21.101)."""
    s = f"{abs(f(v)):.3f}".replace(".", ",")
    return s if abs(f(v)) < 5e-4 else ("+" if v > 0 else "-") + s


def soil(points, step=6.0, n=3, gap=0.9, ln_=2.2):
    """Грунт естественный (ГОСТ 2.306): группы по n штрихов под 45° вдоль линии,
    со стороны грунта - справа по ходу обхода; размеры - в мм листа."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if L < 1e-9:
            continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        nx, ny = uy, -ux
        dx, dy = (nx - ux) / 2 ** 0.5, (ny - uy) / 2 ** 0.5
        t = 1.5 * SC
        while t + (n - 1) * gap * SC <= L - 0.5 * SC:
            for kk in range(n):
                px, py = x1 + ux * (t + kk * gap * SC), y1 + uy * (t + kk * gap * SC)
                line((px, py), (px + dx * ln_ * SC, py + dy * ln_ * SC), "Штриховка")
            t += step * SC


def profile(P, fixed, along, coord):
    """Рабочие отметки вдоль линии разреза: along='x' - при y = coord, 'y' - при x = coord.
    -> [(s, h)] в узлах сетки и точках нуля (вдоль линии h меняется линейно)."""
    hf = P["h"]
    n = R.NX if along == "x" else R.NY
    pts = []
    for t in range(n + 1):
        s = Fr(R.A * t)
        h = K.h_work(hf, s, coord) if along == "x" else K.h_work(hf, coord, s)
        if pts and pts[-1][1] * h < 0:
            s0, h0 = pts[-1]
            pts.append((s0 + (s - s0) * abs(h0) / (abs(h0) + abs(h)), Fr(0)))
        pts.append((s, h))
    return pts


OY3 = -2000.0            # лист 3: разрезы - в модели ниже окончательного плана
Y_SEC = {"x": OY3, "y": OY3 - 200.0}       # проектная линия разреза 1-1 и 2-2, м модели
X_SEC = {"x": 0.0, "y": 100.0}             # начало разреза (поперечный - по центру под продольным)


def section(P, k, along):
    """Разрез площадки по котловану, Мг 1:2000, Мв 1:100: along='x' - продольный 1-1
    (по y = центр котлована, вид на север), 'y' - поперечный 2-2 (по x = центр котлована,
    вид на запад: юг слева). Проектная плоскость - тонкая красная, поверхность грунта -
    основная линия; выемка заштрихована, как ПВ на листе 1; под поверхностью в насыпи -
    обозначение грунта (ГОСТ 2.306)."""
    cx, cy = map(f, K.CENTER)
    x0, yl = X_SEC[along], Y_SEC[along]
    M = lambda s, h: (x0 + f(s), yl - f(h) * VS)                     # h > 0 (насыпь) - грунт ниже
    L = W if along == "x" else Hh
    prof = profile(P, along, along, cy if along == "x" else cx)
    # котлован по линии разреза: верх (бровка) и низ (подошва)
    dt, dn = K.D_NIZ + k["L_OTK"], K.D_NIZ
    if along == "x":
        lo_t, hi_t, lo_b, hi_b = K.X0 - dt, K.X0 + K.BX + dt, K.X0 - dn, K.X0 + K.BX + dn
    else:
        y_lo = K.Y0 + K.CUT_Y                        # x центра - в пределах выреза
        lo_t, hi_t, lo_b, hi_b = y_lo - dt, K.Y0 + K.BY + dt, y_lo - dn, K.Y0 + K.BY + dn

    def hs(s):
        for (s0, h0), (s1, h1) in zip(prof, prof[1:]):
            if s0 <= s <= s1:
                return h0 + (h1 - h0) * (s - s0) / (s1 - s0)

    ref = sorted(set(prof) | {(lo_t, hs(lo_t)), (hi_t, hs(hi_t))})
    outside = lambda s0, s1: s1 <= lo_t or s0 >= hi_t
    h0, h1 = prof[0][1], prof[-1][1]
    d0, d1 = f(abs(h0)) * VS, f(abs(h1)) * VS
    g0, g1 = (x0 - d0, M(0, h0)[1]), (x0 + L + d1, M(L, h1)[1])       # откосы на краях - как обводы
    line(M(0, 0), M(L, 0), "Проектная")
    line(M(0, 0), g0, "Профиль")
    line(M(L, 0), g1, "Профиль")
    msp.add_lwpolyline([g0] + [M(s, h) for s, h in ref if s <= lo_t], dxfattribs={"layer": "Профиль"})
    msp.add_lwpolyline([M(s, h) for s, h in ref if s >= hi_t] + [g1], dxfattribs={"layer": "Профиль"})
    top = k["HR"] + K.H_RSL                          # верх котлована ниже проектной плоскости
    msp.add_lwpolyline([M(lo_t, hs(lo_t)), M(lo_t, top), M(lo_b, K.NK), M(hi_b, K.NK),
                        M(hi_t, top), M(hi_t, hs(hi_t))], dxfattribs={"layer": "Котлован"})
    for (s0, h0_), (s1, h1_) in zip(ref, ref[1:]):
        if outside(s0, s1) and h0_ <= 0 and h1_ <= 0 and (h0_ < 0 or h1_ < 0):     # выемка
            hat = msp.add_hatch(color=8, dxfattribs={"layer": "ПВ_штриховка"})
            hat.set_pattern_fill("ANSI31", scale=1.2, color=8)
            hat.paths.add_polyline_path([M(s0, 0), M(s1, 0), M(s1, h1_), M(s0, h0_)], is_closed=True)
    runs, run = [], []                               # поверхность в насыпи - обозначение грунта
    for (s0, h0_), (s1, h1_) in zip(ref, ref[1:]):
        if outside(s0, s1) and h0_ >= 0 and h1_ >= 0:
            run = run or [M(s0, h0_)]
            run.append(M(s1, h1_))
        elif run:
            runs.append(run); run = []
    if run: runs.append(run)
    for r_ in runs:
        soil(r_)                                     # грунт - справа по ходу (ниже линии)
    # рабочие отметки в узлах сетки - над проектной линией (как в прил. 10), маска поверх штриховки
    for s, h in prof:
        if h == 0 or s % R.A:
            continue
        p = M(s, 0)
        mtext(fmt4(h), (p[0] + 0.6 * SC, p[1] + 0.6 * SC), H_TEXT, "Отметки", MA.BOTTOM_LEFT)
    # отметки уровней (выносные от углов котлована) и глубина котлована
    sm = lo_t - 30.0                                 # знаки отметок - левее котлована, полка к нему
    level_mark(M(L - (60.0 if along == "x" else 70.0), 0), "0,000")   # между отметками узлов
    for s_from, h_lev, val, down in ((lo_t, top, lev(-top), True), (lo_b, K.NK, lev(-K.NK), False)):
        if h_lev:
            line(M(s_from, h_lev), M(sm - 3.0, h_lev), "Отметки")
        level_mark(M(sm, h_lev), val, down=down)
    dim(M(hi_t, top), M(hi_b, K.NK), M(hi_t + 8.0, 0), 90, style="Мв1-100", text="hк = <>")


def section_mark(p, d, look, label):
    """Положение разреза на плане (ГОСТ 2.305): штрих разомкнутой линии 10 мм от точки p
    в направлении d (наружу), стрелка взгляда look в 2,5 мм от внешнего конца, обозначение."""
    (x, y), (dx, dy), (lx, ly) = p, d, look
    e = (x + dx * 10 * SC, y + dy * 10 * SC)
    msp.add_lwpolyline([p, e], dxfattribs={"layer": "Профиль", "const_width": 0.7 * SC})
    a = (x + dx * 7.5 * SC, y + dy * 7.5 * SC)                       # 2,5 мм от внешнего конца
    tip = (a[0] + lx * 5 * SC, a[1] + ly * 5 * SC)
    line(a, (a[0] + lx * 2.5 * SC, a[1] + ly * 2.5 * SC), "Надписи")
    msp.add_lwpolyline([(a[0] + lx * 2.5 * SC, a[1] + ly * 2.5 * SC, 1.2 * SC, 0.0), tip], format="xyse",
                       dxfattribs={"layer": "Надписи"})
    mtext(label, (tip[0] + lx * 2.5 * SC + dx * 0.0, tip[1] + ly * 2.5 * SC), H_BIG, "Надписи", mask=False)


site_plan(B.P1, B.K1, OY2, final=True)               # лист 2: окончательный план
cx_, cy_ = map(f, K.CENTER)
OUT_L, OUT_R, OUT_B, OUT_T = -32.0, W + 40.0, -34.0, Hh + 38.0      # за обводами и размерами
section_mark((OUT_L, cy_ + OY2), (-1, 0), (0, 1), "1")
section_mark((OUT_R, cy_ + OY2), (1, 0), (0, 1), "1")
section_mark((cx_, OUT_B + OY2), (0, -1), (-1, 0), "2")
section_mark((cx_, OUT_T + OY2), (0, 1), (-1, 0), "2")
section(B.P1, B.K1, "x")                              # лист 3: разрезы
section(B.P1, B.K1, "y")


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
        txt(role, (X0 + 1.5, y), H_TEXT, TA.MIDDLE_LEFT, width=NARROW)
        txt(who, (X0 + 21.5, y), H_TEXT, TA.MIDDLE_LEFT, width=NARROW)
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


frame_and_stamp(1, 3, "План строительной площадки\\Pс рабочими отметками и ЛНР\\PМ 1:2000",
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
Vc, Vf = R.P0["VV"], R.P0["VN"]                    # с откосами по контуру площадки (с. 10)
Fc = sum(g["F"] for g in R.FIGS if g["sign"] < 0)
Ff = sum(g["F"] for g in R.FIGS if g["sign"] > 0)
volume_table("Объемы планировочных работ",
             [("", f"F, {M2}", f"V, {M3}"),
              ("Выемка ПВ", num(Fc), num(Vc)),
              ("Насыпь ПН", num(Ff), num(Vf)),
              (f"ПН / Kор, Kор = {K_OR:.2f}".replace(".", ","), "", num(f(Vf) / K_OR))],
             [34, 32, 30])

# ================= лист 2: окончательный план с обводами (разд. 3, п. 2) =================
def viewport(px0, py0, px1, py1, mx0, my0):
    """Видовой экран 1:2000: прямоугольник листа (мм) -> модель от (mx0, my0)."""
    w_, h_ = px1 - px0, py1 - py0
    v = psp.add_viewport(center=((px0 + px1) / 2, (py0 + py1) / 2), size=(w_, h_),
                         view_center_point=(mx0 + w_ * SC / 2, my0 + h_ * SC / 2), view_height=h_ * SC)
    v.dxf.layer = "Видовой_экран"
    v.dxf.flags = v.dxf.flags | 16384                # экран заблокирован: масштаб не собьётся
    return v


psp = doc.layouts.new("Лист 2")
a3(psp)
frame_and_stamp(2, None, "План площадки с окончательными\\Pрабочими отметками и обводами\\PМг 1:2000, Мв 1:100",
                "План строительной площадки с окончательными рабочими отметками, ЛНР и обводами  "
                "Мг 1:2000, Мв 1:100")
# модель x -65..575, y OY2-62..OY2+362: план, обводы, размеры, обозначения разрезов
viewport(57.5, 60, 377.5, 272, -65.0, OY2 - 62.0)

# ================= лист 3: разрезы по котловану (разд. 3, п. 3) =================
psp = doc.layouts.new("Лист 3")
a3(psp)
frame_and_stamp(3, None, "Продольный и поперечный\\Pразрезы площадки по котловану\\PМг 1:2000, Мв 1:100", None)
# проектная линия 1-1 - на 262 мм листа, 2-2 - на 100 мм ниже; оба по центру листа
viewport(25, 75, 410, 270, 250.0 - (410 - 25), OY3 - (262 - 75) * SC)
image_title("Продольный разрез 1-1  Мг 1:2000, Мв 1:100", (217.5, TITLE_Y))
image_title("Поперечный разрез 2-2  Мг 1:2000, Мв 1:100", (217.5, TITLE_Y - 100))

if "VIEWPORTS" in doc.layers:                   # слой ezdxf для главных экранов - больше не нужен
    doc.layers.remove("VIEWPORTS")
out = "План_ЛНР_вариант2.dxf"
doc.saveas(out)
print("saved", out, "viewport", vw, vh, vc)
