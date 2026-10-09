"""Графическая часть - только листы из разд. 3 методички, каждый A3:
  Лист 1 - черновик: план площадки с рабочими отметками и ЛНР, М 1:2000;
  Лист 2 - план площадки с окончательными рабочими отметками (после Δh), ЛНР
           и обводами, Мг 1:2000, Мв 1:100;
  Лист 3 - продольный 1-1 и поперечный 2-2 разрезы площадки по котловану, Мг 1:2000, Мв 1:100;
  Лист 4 - картограмма перемещения земляных масс, М 1:2000;
  «Лист 1 (первый)» - первый чертёж: черновик до котлована, только отметки и ЛНР (вне комплекта).

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
    "Перемещения": (7, 35, True),        # стрелки картограммы
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
    """Рабочая отметка до 0,01 м (половина - вверх), на всех листах одинаково; расчёт - точный."""
    q = int(abs(Fr(v)) * 100 + Fr(1, 2))
    s = f"{q // 100},{q % 100:02d}"
    if not sign or q == 0:
        return s
    return ("+" if v > 0 else "-") + s        # дефис: в шрифте ГОСТ нет знака «минус»


def mtext(text, pos, h_mm, layer, align=MA.MIDDLE_CENTER, mask=True, rot=0, sc=SC):
    mt = msp.add_mtext(text, dxfattribs={"layer": layer, "style": TXT,
                                         "char_height": h_mm * sc, "rotation": rot})
    mt.set_location(pos, attachment_point=align)
    if mask:
        mt.set_bg_color("canvas", scale=1.2)    # маска цветом фона: штриховка не идёт сквозь текст
    return mt


def text_w(s_, h_mm):
    """Ширина надписи шрифтом ГОСТ тип Б, м модели (прописные и цифры - 0,7 h с интервалом)."""
    return len(s_.replace(M3, "м3")) * 0.7 * h_mm * SC


def box(cx, cy, w, h, ang=0.0):
    """Повёрнутый прямоугольник w x h с центром (cx, cy) -> его четыре угла."""
    from math import cos, sin, radians
    c, s_ = cos(radians(ang)), sin(radians(ang))
    return [(cx + u * c - v * s_, cy + u * s_ + v * c) for u, v in
            ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def rect(x0, y0, x1, y1):
    return [(min(x0, x1), min(y0, y1)), (max(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1)),
            (min(x0, x1), max(y0, y1))]


def overlap(a, b):
    """Пересечение выпуклых многоугольников - теорема о разделяющей оси."""
    for poly in (a, b):
        for k in range(len(poly)):
            (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
            ax, ay = y1 - y2, x2 - x1
            if abs(ax) + abs(ay) < 1e-12:           # вырожденная сторона (треугольник)
                continue
            pa = [ax * x + ay * y for x, y in a]
            pb = [ax * x + ay * y for x, y in b]
            if max(pa) <= min(pb) or max(pb) <= min(pa):
                return False
    return True


def cost(bb, obstacles, me="-"):
    """Наложение: надпись на надписи - вес 10, на чужой линии - 1 (маска её аккуратно прервёт).
    me - владелец рамки: свои препятствия не считаются (у общих владелец None)."""
    return sum(w_ for o, w_, own in obstacles if own != me and overlap(bb, o))


def along(pts, w_, step=4.0, r=0.6, own=None):
    """Линия как препятствие: квадратики через step м вдоль ломаной pts."""
    from math import hypot
    res = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        n = max(1, int(hypot(x2 - x1, y2 - y1) / step))
        for k in range(n + 1):
            x, y = x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n
            res.append((rect(x - r, y - r, x + r, y + r), w_, own))
    return res


# ================= план площадки: общий для черновика (лист 1) и окончательного (лист 2) =================
LABEL_SHIFT = {"8'": (34, 28)}     # подпись фигуры 8' - в свободный угол квадрата: центр фигуры закрыт котлованом
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


def site_plan(P, k, oy=0.0, kind="draft"):
    """План площадки 1:2000. kind: "draft" - черновик (лист 1): штриховка ПВ, номера фигур,
    габаритные размеры; "final" - окончательный (лист 2, прил. 10): обводы, размеры до
    точек нуля на границе - за обводами; "carto" - основа картограммы (лист 4): номера
    и объёмы фигур рисует kartogramma()."""
    final, draft = kind == "final", kind == "draft"
    O = lambda x, y: (f(x), f(y) + oy)
    for j in range(R.NY + 1):
        line(O(0, j * R.A), O(W, j * R.A), "Сетка")
    for i in range(R.NX + 1):
        line(O(i * R.A, 0), O(i * R.A, Hh), "Сетка")
    if draft:                                       # штриховка выемки
        for fig in P["FIGS"]:
            if fig["sign"] < 0:
                hat = msp.add_hatch(color=8, dxfattribs={"layer": "ПВ_штриховка"})
                hat.set_pattern_fill("ANSI31", scale=2.4, color=8)
                hat.paths.add_polyline_path([O(x, y) for x, y in fig["poly"]], is_closed=True)
    msp.add_lwpolyline([O(*p) for p in lnr_chain(P)], dxfattribs={"layer": "ЛНР", "const_width": 0.6 * SC})
    if draft:                                       # номера фигур
        shift = LABEL_SHIFT if k else {}
        for fig in P["FIGS"]:
            cx, cy = map(f, fig["c"])
            dx, dy = shift.get(fig["name"], (0, 0))
            mtext(fig["name"], O(cx + dx, cy + dy), H_HEAD if fig["F"] > 2500 else H_TEXT, "Номера_фигур")
    for t, p in {"ПВ": (50, 28), "ПН": (450, 228)}.items():
        if kind != "carto":
            mtext(t, O(*p), H_BIG, "ПВ_ПН")

    # размер до точки нулевых работ - один, от угла квадрата (рис. 4, рис. 11, прил. 10): от вершины 1
    # (как x1 в книге Excel), если там тесно - от вершины 2; на картограмме их нет (с. 18)
    TH, GAP = H_TEXT * SC, 0.8 * SC
    marks = [(O(*map(f, R.xy(i, j))), fmt(P["h"](i, j))) for j in range(R.NY + 1) for i in range(R.NX + 1)]

    def mark_box(p, s_, q, shift=(0.0, 0.0)):
        """Отметка у вершины p: q = 0 - вверх-вправо (основное место), 1 - вниз-вправо, 2 - вверх-влево,
        3 - вниз-влево. -> (точка вставки, выравнивание, рамка)."""
        w_ = text_w(s_, H_TEXT)
        right, up = q in (0, 1), q in (0, 2)
        x = p[0] + shift[0] + (1.8 * SC if right else -1.8 * SC)
        y = p[1] + shift[1] + (0.8 * SC if up else -0.8 * SC)
        al = {(1, 1): MA.BOTTOM_LEFT, (1, 0): MA.TOP_LEFT, (0, 1): MA.BOTTOM_RIGHT, (0, 0): MA.TOP_RIGHT}
        return (x, y), al[(right, up)], rect(x, y, x + (w_ if right else -w_), y + (TH if up else -TH))

    obst = along([O(*q) for q in lnr_chain(P)], 1)
    if k:
        pit_v = [O(*map(f, v)) for v in k["VERH"]]
        obst.append((rect(min(x for x, _ in pit_v) - 2, min(y for _, y in pit_v) - 2,
                          max(x for x, _ in pit_v) + 2 * SC + 12, max(y for _, y in pit_v) + 2), 10, None))
    band = [(q_, 10, None) for q_ in band_quads(P, oy)] if final else []
    # рабочие отметки: основное место - вверх-вправо от вершины. На окончательном плане у края
    # площадки там обводы - отметка встаёт внутрь квадрата (как в прил. 10), а если внутри
    # тесно - за обводы
    placed = []
    for p, s_ in marks:
        if final:
            top, right = p[1] == Hh + oy, p[0] == W
            bottom = p[1] == oy
            inside = ([1, 3] if top and not right else [3] if top else [2] if right and bottom
                      else [2, 3] if right else [])
            cands = [mark_box(p, s_, q) for q in inside] + [mark_box(p, s_, 0)]
            out = (0.0, 1.0) if top else (1.0, 0.0) if right else None
            if out:
                for t in range(1, 81):                # за обводы - до первого свободного места
                    c = mark_box(p, s_, 0, (out[0] * 0.5 * t, out[1] * 0.5 * t))
                    if not cost(c[2], band):
                        cands.append(c)
                        break
            cands += [mark_box(p, s_, q) for q in (1, 2, 3) if q not in inside]
            obs = band + obst + [(b_, 10, None) for _, _, b_ in placed]
            placed.append(min(cands, key=lambda c: cost(c[2], obs) + 0.01 * cands.index(c)))
        else:
            placed.append(mark_box(p, s_, 0))
    dims_obst = []
    if kind != "carto":
        default = [(bb, 10, None) for _, _, bb in placed]
        border_off = {"top": 7.0 * SC, "other": 2.0 * SC}
        for z in P["ZP"]:
            a, b = z["p1"], z["p2"]
            ia, ja = (a - 1) % (R.NX + 1), (a - 1) // (R.NX + 1)
            ib, jb = (b - 1) % (R.NX + 1), (b - 1) // (R.NX + 1)
            pa, pb = tuple(map(f, R.xy(ia, ja))), tuple(map(f, R.xy(ib, jb)))
            pz = tuple(map(f, z["pt"]))
            horiz = ja == jb
            cands = []
            for q1, q2 in ((pa, pz), (pb, pz)):           # от вершины 1, затем от вершины 2
                adj = adjacent(P, q1, q2)
                if len(adj) == 1:                         # граница площадки - размер снаружи
                    top = horiz and q1[1] == Hh
                    sides = [(-adj[0][1], border_off["top"] if top or final else border_off["other"])]
                else:                                     # внутри - со стороны большей фигуры, затем другой
                    s0 = max(adj, key=lambda t: t[0]["F"])[1]
                    sides = [(s0, border_off["other"]), (-s0, border_off["other"])]
                cands += [(q1, q2, side, off) for side, off in sides]
            best = None
            for rank, (q1, q2, side, off) in enumerate(cands):
                L = abs(q2[0] - q1[0]) if horiz else abs(q2[1] - q1[1])
                w_ = text_w(f"{L:.2f}".rstrip("0").rstrip("."), H_TEXT)
                (x1, y1), (x2, y2) = O(*q1), O(*q2)
                if horiz:
                    yd = y1 + side * off
                    xm = (x1 + x2) / 2
                    ty = yd + GAP if side > 0 else yd - GAP - TH
                    tb = rect(xm - w_ / 2, ty, xm + w_ / 2, ty + TH)
                    lines_ = [rect(x1, yd - 0.3, x2, yd + 0.3), rect(x1 - 0.3, y1, x1 + 0.3, yd + side * 1.5 * SC),
                              rect(x2 - 0.3, y2, x2 + 0.3, yd + side * 1.5 * SC)]
                else:
                    xd = x1 + side * off
                    ym = (y1 + y2) / 2
                    tx = xd + GAP if side > 0 else xd - GAP - TH
                    tb = rect(tx, ym - w_ / 2, tx + TH, ym + w_ / 2)
                    lines_ = [rect(xd - 0.3, y1, xd + 0.3, y2), rect(x1, y1 - 0.3, xd + side * 1.5 * SC, y1 + 0.3),
                              rect(x2, y2 - 0.3, xd + side * 1.5 * SC, y2 + 0.3)]
                texts_ = [(o, 10, None) for o, w__, _ in dims_obst if w__ == 10]
                c_ = (cost(tb, default + band + obst + texts_)
                      + sum(cost(l_, [(o, 5, None) for o, _, _ in default + texts_]) for l_ in lines_)
                      + 0.01 * rank)
                if best is None or c_ < best[0]:
                    best = (c_, q1, q2, side, off, tb, lines_)
            _, q1, q2, side, off, tb, lines_ = best
            dims_obst += [(tb, 10, None)] + [(l_, 5, None) for l_ in lines_]
            if horiz:
                dim(O(*q1), O(*q2), O(q1[0], q1[1] + side * off), 0, {"dimtad": 1 if side > 0 else 4})
            else:
                lo, hi = sorted((q1, q2), key=lambda q: q[1])
                dim(O(*lo), O(*hi), O(q1[0] + side * off, q1[1]), 90, {"dimtad": 4 if side > 0 else 1})
    if draft:                                       # габаритные размеры площадки
        dim(O(0, 0), O(W, 0), O(0, -10 * SC), 0)
        dim(O(0, 0), O(0, Hh), O(-10 * SC, 0), 90)
    if k:
        draw_pit(k, dy=oy)
    if final:
        obvody(P, oy)                               # до отметок: маска отметки ложится поверх штрихов

    for (pos, al, bb), (p, s_) in zip(placed, marks):   # отметки - поверх размеров (маска)
        mtext(s_, pos, H_TEXT, "Отметки", al)
        msp.add_circle(p, 0.5 * SC, dxfattribs={"layer": "Отметки"})
    return [bb for _, _, bb in placed]



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


def band_quads(P, oy):
    """Полоса обводов как выпуклые многоугольники: по участкам сторон и в углах."""
    sides = perimeter_points(P)
    res = []
    for (nx, ny), pts in sides:
        o = [(x + nx * f(abs(h)) * VS, y + ny * f(abs(h)) * VS + oy) for x, y, h in pts]
        for (x1, y1, _), (x2, y2, _), a, b in zip(pts, pts[1:], o, o[1:]):
            res.append([(x1, y1 + oy), (x2, y2 + oy), b, a])
    for s_ in range(4):
        (nx1, ny1), _ = sides[s_ - 1]
        (nx2, ny2), pts2 = sides[s_]
        x, y, h = pts2[0]
        d = f(abs(h)) * VS
        res.append([(x, y + oy), (x + nx1 * d, y + ny1 * d + oy), (x + (nx1 + nx2) * d, y + (ny1 + ny2) * d + oy),
                    (x + nx2 * d, y + ny2 * d + oy)])
    return res


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
    if along == "x":                                 # справа - сторона съезда (c = 7 м от плиты)
        lo_t, hi_t = K.X0 - dt, K.X0 + K.BX + K.D_PAN + k["L_OTK"]
        lo_b, hi_b = K.X0 - dn, K.X0 + K.BX + K.D_PAN
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
        mtext(fmt(h), (p[0] + 0.6 * SC, p[1] + 0.6 * SC), H_TEXT, "Отметки", MA.BOTTOM_LEFT)
    # отметки уровней верха и дна котлована (выносные от углов) и глубина котлована
    sm = lo_t - 30.0                                 # знаки отметок - левее котлована, полка к нему
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


site_plan(R.P0, K.K0)                               # лист 1: черновик
OY0 = -4000.0                                       # первый чертёж: тот же черновик без котлована
site_plan(R.P0, None, OY0)
site_plan(B.P1, B.K1, OY2, "final")                 # лист 2: окончательный план
cx_, cy_ = map(f, K.CENTER)
OUT_L, OUT_R, OUT_B, OUT_T = -32.0, W + 40.0, -34.0, Hh + 38.0      # за обводами и размерами
section_mark((OUT_L, cy_ + OY2), (-1, 0), (0, 1), "1")
section_mark((OUT_R, cy_ + OY2), (1, 0), (0, 1), "1")
section_mark((cx_, OUT_B + OY2), (0, -1), (-1, 0), "2")
section_mark((cx_, OUT_T + OY2), (0, 1), (-1, 0), "2")
section(B.P1, B.K1, "x")                              # лист 3: разрезы
section(B.P1, B.K1, "y")

# ================= лист 4: картограмма перемещения земляных масс (разд. 3, п. 4; п. 2.2.5) =================
import raspredelenie as RS
from math import atan2, degrees, hypot

OY4 = -3000.0            # картограмма - в модели ниже разрезов
vol = lambda v: f"{f(v):,.2f}".replace(",", " ").replace(".", ",")


def zigzag(p, q, step=1.25, amp=0.6, sc=SC):
    """Волнистая линия (бульдозер, рис. 11) от p до q; шаг и размах - в мм листа."""
    (x1, y1), (x2, y2) = p, q
    L = hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    n = max(2, int(L / (step * sc)))
    pts = [p]
    for k in range(1, n):
        t, a = L * k / n, amp * sc * (1 if k % 2 else -1)
        pts.append((x1 + ux * t - uy * a, y1 + uy * t + ux * a))
    pts.append(q)
    return pts


def move_line(p, q, kind):
    """Линия перемещения грунта от центра тяжести p к центру тяжести q (с. 18, рис. 10, 11):
    скрепер - сплошная, бульдозер - волнистая, самосвал - штриховая; наконечник 3 мм."""
    (x1, y1), (x2, y2) = p, q
    L = hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    ah = 3.0 * SC
    e = (x2 - ux * ah, y2 - uy * ah)
    if kind == "бульдозер":
        msp.add_lwpolyline(zigzag(p, e), dxfattribs={"layer": "Перемещения"})
    elif kind == "самосвал":
        line(p, e, "Перемещения", linetype=DASH)
    else:
        line(p, e, "Перемещения")
    msp.add_lwpolyline([(e[0], e[1], 1.0 * SC, 0.0), (x2, y2)], format="xyse", dxfattribs={"layer": "Перемещения"})


def label_frame(p, q, v, l):
    """Подписи стрелки: над линией - объём, под линией - расстояние. -> данные для расстановки."""
    (x1, y1), (x2, y2) = p, q
    L = hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    ang = degrees(atan2(uy, ux))
    nx, ny = -uy, ux
    if ang > 90 or ang < -90:                        # текст - не вверх ногами
        ang += 180; nx, ny = -nx, -ny
    s1, s2 = f"{vol(v)} {M3}", f"{l:.1f} м".replace(".", ",")
    w = max(text_w(s1, H_TEXT), text_w(s2, H_TEXT))
    hh = 2 * (H_TEXT + 0.7) * SC
    cands = []
    for t in sorted((k / 40 for k in range(4, 37)), key=lambda t: abs(t - 0.5)):
        m = (x1 + ux * L * t, y1 + uy * L * t)
        cands.append((m, box(m[0], m[1], w, hh, ang)))
    return {"s1": s1, "s2": s2, "ang": ang, "n": (nx, ny), "cands": cands}


def kartogramma(oy):
    """Объёмы в фигурах (выемка - плотное тело, насыпь - с kо.р), номера фигур,
    стрелки перемещений из табл. 4, грунт котлована, недостача. Сначала все линии,
    затем надписи - их маска ложится поверх линий; места надписей подбираются
    с наименьшим наложением друг на друга, на отметки, ЛНР и стрелки."""
    O = lambda x, y: (f(x), f(y) + oy)
    ends = []
    for a, b, v, l, kind in RS.MOVES:
        p = RS.PIT_C if a == "котлован" else RS.C(next(g for g in RS.CUT if g["name"] == a))
        q = RS.C(next(g for g in RS.FILL if g["name"] == b))
        move_line(O(*p), O(*q), kind)
        ends.append((O(*p), O(*q), v, l))
    T = lambda poly: (poly, 10, None)                # надпись-препятствие
    lines_ = []                                      # ЛНР и линии стрелок: точки через 4 м, вес 1
    pts = [O(*p) for p in lnr_chain(RS.P)]
    segs = [(a_, b_, None) for a_, b_ in zip(pts, pts[1:])] + [(p, q, k) for k, (p, q, _, _) in enumerate(ends)]
    for (x1, y1), (x2, y2), own in segs:
        n = max(1, int(hypot(x2 - x1, y2 - y1) / 4.0))
        for k in range(n + 1):
            x, y = x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n
            lines_.append((rect(x - 0.6, y - 0.6, x + 0.6, y + 0.6), 1, own))
    for poly in (RS.KT["VERH"], RS.KT["NIZ"]):                 # контур котлована - тоже линия
        lines_ += along([O(*map(f, q)) for q in poly + poly[:1]], 1)
    fixed = [T(b_) for b_ in MARKS4]                 # рабочие отметки в вершинах (site_plan)
    px, py = RS.PIT_C
    s_pit = f"{vol(RS.V_PIT_FILL)} {M3}"
    wp = text_w(s_pit, H_TEXT)
    fixed.append(T(rect(px - wp / 2, py + oy - (1.2 + H_TEXT) * SC, px + wp / 2, py + oy - 1.2 * SC)))
    for j, v in RS.SHORT.items():
        cx, cy = map(f, RS.FILL[j]["c"])
        s_ = f"недостача {vol(v)} {M3}"
        fixed.append(T(rect(cx - text_w(s_, H_TEXT) / 2, cy + oy - (6.0 + H_TEXT) * SC,
                            cx + text_w(s_, H_TEXT) / 2, cy + oy - 6.0 * SC)))
    # подписи фигур: объём над центром тяжести и номер слева внизу - или наоборот,
    # смотря куда уходят стрелки
    figlab = []
    for g in RS.P["FIGS"]:
        cx, cy = map(f, g["c"])
        dx, dy = LABEL_SHIFT.get(g["name"], (0, 0))      # как на листе 1; кружок - в центре тяжести
        cx, cy = cx + dx, cy + dy
        v = g["V"] if g["sign"] < 0 else g["V"] / RS.K_OR
        hn = H_HEAD if g["F"] > 2500 else H_TEXT
        s_ = f"{vol(v)} {M3}"
        w, wn = text_w(s_, H_TEXT), text_w(g["name"], hn)
        Y = cy + oy
        var = []
        for sv in (1, -1):                           # 1 - объём сверху, -1 - снизу
            vb = rect(cx - w / 2, Y + sv * 1.2 * SC, cx + w / 2, Y + sv * (1.2 + H_TEXT) * SC) if sv > 0 else \
                rect(cx - w / 2, Y - (1.2 + H_TEXT) * SC, cx + w / 2, Y - 1.2 * SC)
            nb = rect(cx - 1.2 * SC - wn, Y - (1.2 + hn) * SC, cx - 1.2 * SC, Y - 1.2 * SC) if sv > 0 else \
                rect(cx - 1.2 * SC - wn, Y + 1.2 * SC, cx - 1.2 * SC, Y + (1.2 + hn) * SC)
            c_ = sum(cost(b_, lines_ + fixed, "фигура") for b_ in (vb, nb))
            var.append((c_, sv, vb, nb))
        c_, sv, vb, nb = min(var, key=lambda t: t[0])
        fixed += [T(vb), T(nb)]
        figlab.append((g, cx, cy, hn, s_, sv))
    # подписи стрелок: сначала короткие (у них меньше места), затем два круга улучшения
    frames = [label_frame(*e) for e in ends]
    place = {}
    order = sorted(range(len(ends)), key=lambda k: hypot(ends[k][1][0] - ends[k][0][0], ends[k][1][1] - ends[k][0][1]))
    for rnd in range(3):
        for k in order:
            others = [T(place[o][1]) for o in place if o != k]
            obst = lines_ + fixed + others
            place[k] = min(frames[k]["cands"], key=lambda c: cost(c[1], obst, k))
    # подпись легла на текст: перебор всех сочетаний её положений с каждой подписью,
    # которая занимает её возможные места
    for rnd in range(2):
        for i in range(len(ends)):
            rest_i = lines_ + fixed + [T(place[o][1]) for o in place if o != i]
            if cost(place[i][1], rest_i, i) < 10:
                continue
            for j in range(len(ends)):
                if j == i or not any(overlap(c[1], place[j][1]) for c in frames[i]["cands"]):
                    continue
                rest = lines_ + fixed + [T(place[o][1]) for o in place if o not in (i, j)]
                ci = [(c, cost(c[1], rest, i)) for c in frames[i]["cands"]]
                cj = [(c, cost(c[1], rest, j)) for c in frames[j]["cands"]]
                best = min(((a, b) for a in ci for b in cj),
                           key=lambda ab: ab[0][1] + ab[1][1] + 20 * overlap(ab[0][0][1], ab[1][0][1]))
                place[i], place[j] = best[0][0], best[1][0]
    for k, fr in enumerate(frames):
        (mx, my), _ = place[k]
        nx, ny = fr["n"]
        mtext(fr["s1"], (mx + nx * 0.7 * SC, my + ny * 0.7 * SC), H_TEXT, "Перемещения", MA.BOTTOM_CENTER,
              rot=fr["ang"])
        mtext(fr["s2"], (mx - nx * 0.7 * SC, my - ny * 0.7 * SC), H_TEXT, "Перемещения", MA.TOP_CENTER,
              rot=fr["ang"])
    for g, cx, cy, hn, s_, sv in figlab:             # подписи фигур - поверх линий
        msp.add_circle(O(*map(f, g["c"])), 0.4 * SC, dxfattribs={"layer": "Перемещения"})
        mtext(g["name"], O(cx - 1.2 * SC, cy - sv * 1.2 * SC), hn, "Номера_фигур",
              MA.TOP_RIGHT if sv > 0 else MA.BOTTOM_RIGHT)
        mtext(s_, O(cx, cy + sv * 1.2 * SC), H_TEXT, "Номера_фигур", MA.BOTTOM_CENTER if sv > 0 else MA.TOP_CENTER)
    for j, v in RS.SHORT.items():                    # недостача - подвоз из карьера (с. 15)
        cx, cy = map(f, RS.FILL[j]["c"])
        mtext(f"недостача {vol(v)} {M3}", O(cx, cy - 6.0 * SC), H_TEXT, "Номера_фигур", MA.TOP_CENTER)
    msp.add_circle(O(px, py), 0.4 * SC, dxfattribs={"layer": "Перемещения"})   # грунт котлована в насыпь
    mtext(s_pit, O(px, py - 1.2 * SC), H_TEXT, "Номера_фигур", MA.TOP_CENTER)


MARKS4 = site_plan(RS.P, RS.KT, OY4, "carto")        # лист 4: картограмма
kartogramma(OY4)


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


frame_and_stamp(1, 4, "План строительной площадки\\Pс рабочими отметками и ЛНР\\PМ 1:2000",
                "План строительной площадки с рабочими отметками и линией нулевых работ  М 1:2000")

# видовой экран: модель x -34..524, y -44..326 м
VX0, VY0, VX1, VY1 = -34.0, -44.0, 524.0, 326.0
VX0_1, VY0_1, VX1_1, VY1_1 = VX0, VY0, VX1, VY1
vw, vh = (VX1 - VX0) / SC, (VY1 - VY0) / SC
vc = (217.5, 72 + vh / 2)
vp = psp.add_viewport(center=vc, size=(vw, vh),
                      view_center_point=((VX0 + VX1) / 2, (VY0 + VY1) / 2), view_height=vh * SC)
vp.dxf.layer = "Видовой_экран"
vp.dxf.flags = vp.dxf.flags | 16384              # экран заблокирован: масштаб 1:2000 не собьётся

# ---------- условные обозначения, сводка объёмов ----------
LX, LY = 26, 64


def legend_and_volumes(pit=True):
    """Условные обозначения и таблица объёмов черновика (лист 1 и первый чертёж)."""
    txt("Условные обозначения", (LX, LY), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
    items = [
        ("lnr", "линия нулевых работ (ЛНР)"),
        ("hatch", "ПВ - планировочная выемка"),
        ("box", "ПН - планировочная насыпь"),
        ("mark", "рабочая отметка, м (+ насыпь, - выемка)"),
        ("fig", "номер фигуры; со штрихом - насыпная часть квадрата"),
        ("dim", "расстояние до точки нулевых работ, м"),
        ("pit", "контур котлована"),
    ][:None if pit else -1]
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

    # сводка объёмов
    Vc, Vf = R.P0["VV"], R.P0["VN"]                    # с откосами по контуру площадки (с. 10)
    Fc = sum(g["F"] for g in R.FIGS if g["sign"] < 0)
    Ff = sum(g["F"] for g in R.FIGS if g["sign"] > 0)
    volume_table("Объемы планировочных работ",
                 [("", f"F, {M2}", f"V, {M3}"),
                  ("Выемка ПВ", num(Fc), num(Vc)),
                  ("Насыпь ПН", num(Ff), num(Vf)),
                  (f"ПН / Kор, Kор = {K_OR:.2f}".replace(".", ","), "", num(f(Vf) / K_OR))],
                 [34, 32, 30])


legend_and_volumes()

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

# ================= лист 4: картограмма перемещения земляных масс (разд. 3, п. 4) =================
psp = doc.layouts.new("Лист 4")
a3(psp)
frame_and_stamp(4, None, "Картограмма перемещения\\Pземляных масс\\PМ 1:2000",
                "Картограмма перемещения земляных масс  М 1:2000")
vp = psp.add_viewport(center=vc, size=(vw, vh),                  # план - на том же месте, что на листе 1
                      view_center_point=((VX0_1 + VX1_1) / 2, (VY0_1 + VY1_1) / 2 + OY4), view_height=vh * SC)
vp.dxf.layer = "Видовой_экран"
vp.dxf.flags = vp.dxf.flags | 16384
txt("Условные обозначения", (LX, LY), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)   # как на листе 1
txt("Грунт перемещается:", (LX, LY - 7), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)
for k, (kind, label) in enumerate((("скрепер", "скрепером"), ("бульдозер", "бульдозером"), ("самосвал", "самосвалом"))):
    y = LY - 14.5 - 7.5 * k
    sx0, sx1 = LX, LX + 14
    e = (sx1 - 3.0, y)
    if kind == "бульдозер":
        psp.add_lwpolyline(zigzag((sx0, y), e, sc=1.0), dxfattribs={"layer": "Перемещения"})
    else:
        at = {"layer": "Перемещения"}
        if kind == "самосвал":
            at["linetype"] = DASH
        psp.add_line((sx0, y), e, dxfattribs=at)
    psp.add_lwpolyline([(e[0], e[1], 1.0, 0.0), (sx1, y)], format="xyse", dxfattribs={"layer": "Перемещения"})
    txt("- " + label, (sx1 + 3, y), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)

# ================= первый чертёж: черновик до котлована - только рабочие отметки и ЛНР =================
# не входит в комплект листов по разд. 3 методички; оформление - как у листа 1
psp = doc.layouts.new("Лист 1 (первый)")
a3(psp)
frame_and_stamp(1, None, "План строительной площадки\\Pс рабочими отметками и ЛНР\\PМ 1:2000",
                "План строительной площадки с рабочими отметками и линией нулевых работ  М 1:2000")
vp = psp.add_viewport(center=vc, size=(vw, vh),
                      view_center_point=((VX0_1 + VX1_1) / 2, (VY0_1 + VY1_1) / 2 + OY0), view_height=vh * SC)
vp.dxf.layer = "Видовой_экран"
vp.dxf.flags = vp.dxf.flags | 16384
legend_and_volumes(pit=False)

if "VIEWPORTS" in doc.layers:                   # слой ezdxf для главных экранов - больше не нужен
    doc.layers.remove("VIEWPORTS")
out = "План_ЛНР_вариант2.dxf"
doc.saveas(out)
print("saved", out, "viewport", vw, vh, vc)
