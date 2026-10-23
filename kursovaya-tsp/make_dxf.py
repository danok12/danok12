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
    "Машины": (7, 25, True),             # машины на технологических схемах
    "Оси_движения": (7, 18, True),       # оси движения экскаватора, границы проходок и захваток
    "Транспорт": (1, 25, True),          # оси движения автосамосвалов
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
d3 = doc.dimstyles.duplicate_entry("М1-2000", "Схема")    # схемы без масштаба: размеры в мм листа,
d3.dxf.dimscale = 1.0                                      # текст размера задаётся явно

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
    final, draft, scheme = kind == "final", kind == "draft", kind == "scheme"
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
    if draft or final:                              # на картограмме и техсхеме размеров до точек нуля нет
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
    if draft or scheme:                             # габаритные размеры площадки
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

# ================= лист 5: схема производства работ по вертикальной планировке (разд. 3, п. 5; прил. 9) =================
import mashiny as MS
from math import sin, cos, pi

OY5 = -5000.0            # техсхема - в модели ниже картограммы
W08 = "\\W0.8;"        # сжатие надписей, как на листах


def glyph(p, ang, w=3.0, h=1.6, blade=True):
    """Машина в плане: прямоугольник w x h мм, у бульдозера - отвал спереди; ang - курс, град."""
    c, s_ = cos(ang * pi / 180), sin(ang * pi / 180)
    T = lambda u, v: (p[0] + (u * c - v * s_) * SC, p[1] + (u * s_ + v * c) * SC)
    msp.add_lwpolyline([T(-w / 2, -h / 2), T(w / 2, -h / 2), T(w / 2, h / 2), T(-w / 2, h / 2)], close=True,
                       dxfattribs={"layer": "Перемещения"})
    if blade:
        line(T(w / 2 + 0.4, -h / 2 - 0.4), T(w / 2 + 0.4, h / 2 + 0.4), "Перемещения")


def arrow_head(p, ang, L=1.8, wd=1.0):
    """Наконечник стрелки (мм листа) в точке p, направление ang, град."""
    c, s_ = cos(ang * pi / 180), sin(ang * pi / 180)
    b = (p[0] - c * L * SC, p[1] - s_ * L * SC)
    msp.add_lwpolyline([(b[0], b[1], wd * SC, 0.0), p], format="xyse", dxfattribs={"layer": "Перемещения"})


def shuttle(c, w=16.0, h=6.0, n=4):
    """Челночная схема бульдозера (прил. 9): рабочие ходы - сплошные, холостые - штриховые,
    машина со стрелкой - в начале верхнего хода; мм листа."""
    x0, x1 = c[0] - w / 2 * SC, c[0] + w / 2 * SC
    ys = [c[1] + (h / 2 - h * k / (n - 1)) * SC for k in range(n)]
    for k, y in enumerate(ys):
        line((x0, y), (x1, y), "Перемещения")
        if k + 1 < n:
            line((x1, y), (x0, ys[k + 1]), "Перемещения", linetype=DASH)
    arrow_head((x1 + 3.4 * SC, ys[0]), 0)
    line((x1, ys[0]), (x1 + 1.6 * SC, ys[0]), "Перемещения")
    glyph((x0 + 1.8 * SC, ys[0] + 1.4 * SC), 0)


def racetrack(c, w=20.0, h=6.0, n=3, gap=1.0):
    """Укатка катком «по замкнутой схеме» (прил. 9): вложенные овалы, каток на верхней прямой."""
    for k in range(n):
        ww, hh = w - 2 * k * gap, h - 2 * k * gap
        r = hh / 2
        pts = []
        for t in range(0, 181, 15):                      # правый полукруг
            a = -pi / 2 + t * pi / 180
            pts.append((c[0] + (ww / 2 - r + r * cos(a)) * SC, c[1] + r * sin(a) * SC))
        for t in range(0, 181, 15):                      # левый полукруг
            a = pi / 2 + t * pi / 180
            pts.append((c[0] + (-ww / 2 + r + r * cos(a)) * SC, c[1] + r * sin(a) * SC))
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "Перемещения"})
    arrow_head((c[0] + 3.0 * SC, c[1] + h / 2 * SC), 0)
    glyph((c[0] - 1.5 * SC, c[1] + h / 2 * SC), 0, w=2.6, h=2.0, blade=False)


def eight(a, b, B=14.0):
    """Скрепер «восьмёркой» (прил. 9) из выемки a в насыпь b через ЛНР; B - ширина петли, мм."""
    from math import atan2, degrees, hypot
    L = hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    vx, vy = -uy, ux
    cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ang = degrees(atan2(uy, ux))
    for k, (AA, BB) in enumerate(((L / 2, B * SC), (L / 2 - 2.0 * SC, (B - 3.0) * SC))):
        pts = []
        for i in range(0, 361, 6):
            t = i * pi / 180
            x_, y_ = AA * sin(t), BB * sin(t) * cos(t)
            pts.append((cx + ux * x_ + vx * y_, cy + uy * x_ + vy * y_))
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "Перемещения"})
    A_, B_ = L / 2, B * SC
    P = lambda t: (cx + ux * A_ * sin(t) + vx * B_ * sin(t) * cos(t), cy + uy * A_ * sin(t) + vy * B_ * sin(t) * cos(t))
    D = lambda t: degrees(atan2(uy * A_ * cos(t) + vy * B_ * cos(2 * t), ux * A_ * cos(t) + vx * B_ * cos(2 * t)))
    for t in (7 * pi / 4 + 0.35, pi / 4, 3 * pi / 4, 5 * pi / 4):   # гружёный ход вправо, порожний - обратно
        arrow_head(P(t), D(t))
    glyph(P(7 * pi / 4 - 0.2), D(7 * pi / 4 - 0.2), w=4.0, h=2.0, blade=False)   # скрепер у забоя
    glyph(P(7 * pi / 4 - 0.55), D(7 * pi / 4 - 0.55), w=3.0, h=1.6)               # толкач за ним


O5 = lambda x, y: (float(x), float(y) + OY5)
OPS = [  # (подпись, вид схемы, центр схемы в модели, м) - машины комплекта п. 2.3 (вариант 2)
    (f"Срезка растительного слоя\\Pбульдозером {MS.BUL_RAZ[1].split(',')[0]}", "shuttle", (50, 55)),
    (f"Рыхление грунта бульдозером-\\Pрыхлителем {MS.RYKHL[1].split(' на')[0]}", "shuttle", (50, 150)),
    (f"Окончательная планировка\\Pбульдозером {MS.BUL_RAZ[1].split(',')[0]}", "shuttle", (45, 240)),
    (f"Разравнивание грунта\\Pбульдозером {MS.BUL_RAZ[1].split(',')[0]}", "shuttle", (350, 245)),
    (f"Уплотнение грунта насыпи\\Pкатком {MS.KATOK[1].split(',')[0]}", "track", (250, 245)),
]
EIGHT = ((130, 130), (230, 225))                       # поперёк ЛНР у кв. 7 и 3, в стороне от котлована
# сначала схемы движения машин, затем план (сетка, ЛНР, отметки с маской - поверх линий схем), затем подписи
for text, kind, (x, y) in OPS:
    (shuttle if kind == "shuttle" else racetrack)(O5(x, y))
eight(O5(*EIGHT[0]), O5(*EIGHT[1]))
SCH = site_plan(B.P1, B.K1, OY5, "scheme")           # основа: окончательные отметки, ЛНР, котлован
# привязка котлована (бровка, левый нижний угол) к сетке - как в прил. 9
kx, ky = (float(v) for v in B.K1["VERH"][0])
dim(O5(200, ky), O5(kx, ky), O5(200, ky - 6.0 * SC), 0, {"dimtad": 4})
dim(O5(kx, 100), O5(kx, ky), O5(kx + 4.0 * SC, 100), 90, {"dimtad": 4})
for text, kind, (x, y) in OPS:
    mtext(W08 + text, O5(x, y + 6.0 * SC), H_TEXT, "Надписи", MA.BOTTOM_CENTER)
mtext(W08 + f"Разработка и перемещение\\Pгрунта скреперами {MS.SKR_VED[1].split(',')[0]},"
      f"\\Pтолкач {MS.TOLKACH[1]}", O5(150, 75), H_TEXT, "Надписи", MA.MIDDLE_CENTER)


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
    mt("\\W0.8;Кафедра технологии\\Pи организации строительного\\Pпроизводства", (X0 + 160, Y0 + 7.5),
       H_TEXT, 48)

    # заголовок листа
    if title:
        image_title(title, (217.5, TITLE_Y))


frame_and_stamp(1, 8, "План строительной площадки\\Pс рабочими отметками и ЛНР\\PМ 1:2000",
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

# ================= лист 5: схема производства работ по вертикальной планировке =================
psp = doc.layouts.new("Лист 5")
a3(psp)
frame_and_stamp(5, None, "Схема производства работ\\Pпо вертикальной планировке\\PМ 1:2000",
                "Схема производства работ по вертикальной планировке строительной площадки  М 1:2000")
vp = psp.add_viewport(center=vc, size=(vw, vh),                  # план - на том же месте, что на листе 1
                      view_center_point=((VX0_1 + VX1_1) / 2, (VY0_1 + VY1_1) / 2 + OY5), view_height=vh * SC)
vp.dxf.layer = "Видовой_экран"
vp.dxf.flags = vp.dxf.flags | 16384
MACH = [  # ведомость применяемой техники (п. 2.3, вариант 2); характеристики - ЕНиР Е2-1, табл. 1 параграфов
    ("Скрепер прицепной", "ДЗ-20 (Д-498), Т-100", 3, f"ковш 6,7 {M3}, захват 2,59 м, резание 0,3 м, слой 0,35 м, 79 кВт, 7 т"),
    ("Трактор-толкач", "Т-180", 1, "мощность 132 кВт (180 л.с.)"),
    ("Бульдозер-рыхлитель", "ДП-22С на ДЗ-35С, Т-180", 1, "3 зуба, рыхление до 0,5 м, ширина 1,67 м, 132 кВт"),
    ("Бульдозер", "ДЗ-35С (Д-575С), Т-180", 1, "отвал неповоротный 3,64 х 1,29 м, 132 кВт, оборудование 3,4 т"),
    ("Каток на пневмошинах", "ДУ-16В (Д-551В)", 1, "полуприцепной, полоса 2,6 м, слой до 0,35 м, 177 кВт, 25 т"),
]
assert [m[2] for m in MACH] == [MS.VAR2["rows"][0]["n"], MS.VAR2["rows"][4]["n"], MS.VAR2["rows"][1]["n"],
                                MS.VAR2["rows"][2]["n"], MS.VAR2["rows"][3]["n"]], "количество машин - из табл. 7"
txt("Ведомость применяемой техники", (LX, LY), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
CW5 = [38, 42, 13, 106]
for r, row in enumerate([("Наименование", "Марка", "Кол.", "Технические характеристики")] + MACH):
    y = LY - 3 - 7 * r
    x = LX
    for c, v in enumerate(row):
        pl([(x, y), (x + CW5[c], y), (x + CW5[c], y - 7), (x, y - 7)], "Штамп", True)
        left = r > 0 and c in (0, 1, 3)
        txt(str(v), (x + 1.5 if left else x + CW5[c] / 2, y - 3.5), H_TEXT,
            TA.MIDDLE_LEFT if left else TA.MIDDLE_CENTER, "Надписи", NARROW)
        x += CW5[c]

# ================= лист 6: схема разработки грунта и устройства дна котлована (разд. 3, п. 5; прил. 9) =================
# Как в прил. 9: план котлована с проходками экскаватора и разрез по забою; подчистка дна
# бульдозером - план и разрез; устройство подсыпки - план захваток и разрез. Без масштаба
# (планы котлована - в пропорциях его размеров); всё - в пространстве листа, мм.
# Котлован - по окончательным отметкам (B.K1), машины - п. 2.3.2 и ЕНиР Е2-1.
from math import asin, sqrt, radians, atan2, degrees, hypot
KK = B.K1
HK6, M6 = f(KK["HK"]), f(KK["M"])
R6 = f(MS.EX_R)                                      # наибольший радиус копания ЭО-4121А, м
NED6 = MS.NEDOBOR / 100                              # недобор, м (прил. 7)
HD6 = HK6 - NED6                                     # глубина копания экскаватором, м
V6 = [tuple(map(f, p)) for p in KK["VERH"]]
N6 = [tuple(map(f, p)) for p in KK["NIZ"]]
RG6 = K.ramp_geometry(KK)
XL6, XN6, XR6 = V6[0][0], V6[1][0], V6[3][0]         # бровка: левая сторона, край левого крыла, правая
YB6, YN6, YT6 = V6[0][1], V6[2][1], V6[4][1]         # бровка: низ крыла, низ правой части, верх
XE6 = f(RG6["end"][0][0])                            # конец съезда
YP1, YP2 = map(f, RG6["gap"])                        # разрыв бровки у съезда
YPC = f(KK["PAN_Y"] + K.B_PAN / 2)                   # ось съезда
B6 = 1.5 * R6                                        # торцевая проходка - не шире 1,5·Rmax (прил. 9)
Y12 = YT6 - B6                                       # граница проходок I и II
assert YN6 < Y12 and Y12 - YN6 <= B6 and YN6 - YB6 <= B6
PASSES = [  # (номер, x начала, x конца, y низа, y верха, ось автосамосвалов) - в м площадки
    ("I", XL6, XR6, Y12, YT6, YT6 + 3.0),
    ("II", XR6, XL6, YN6, Y12, YN6 - 3.0),
    ("III", XL6, XN6, YB6, YN6, YB6 - 3.0),
    ("IV", XR6, XE6, YPC - 3.0, YPC + 3.0, YP2 + 3.0),          # съезд
]
B_DOZ = 3.64                                         # отвал ДЗ-35С, м - ширина полосы подчистки
BUL6 = MS.BUL_RAZ[1].split(" ")[0]                   # бульдозер комплекта - подчистка и разравнивание подсыпки
KAT6 = MS.KATOK_POD[1].split(" ")[0]                 # каток для подсыпки (самоходный, въезжает по съезду)
EXT = 0.3 / NED6                                     # недобор и подсыпка на разрезах - утолщены (0,3 м)

psp = doc.layouts.new("Лист 6")
a3(psp)
frame_and_stamp(6, None, "Технологическая схема разработки\\Pгрунта и устройства дна котлована", None)


def pp(pts, layer, closed=False, lt=None, w=None):
    at = {"layer": layer}
    if lt:
        at["linetype"] = lt
    e = psp.add_lwpolyline(pts, close=closed, dxfattribs=at)
    if w:
        e.dxf.const_width = w
    return e


def arr(p, ang, L=2.5, wd=1.0, layer="Перемещения"):
    """Наконечник стрелки на листе: острие в p, направление ang, град."""
    c, s_ = cos(radians(ang)), sin(radians(ang))
    psp.add_lwpolyline([(p[0] - c * L, p[1] - s_ * L, wd, 0.0), (p[0], p[1], 0.0, 0.0)], format="xyse",
                       dxfattribs={"layer": layer})


def pdim(p1, p2, base, text, angle=0):
    d = psp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="Схема", text=text,
                           dxfattribs={"layer": "Размеры"})
    d.render()


def lbl(s, pos, align=MA.MIDDLE_CENTER, h=H_TEXT, rot=0):
    m = psp.add_mtext(W08 + s, dxfattribs={"layer": "Надписи", "style": TXT, "char_height": h, "rotation": rot})
    m.set_location(pos, attachment_point=align)
    return m


def callout(p, q, s, right=True):
    """Выноска: от точки p к полке в q, надпись над полкой."""
    e = (q[0] + (1 if right else -1) * (len(s) * 1.45 + 1), q[1])
    pp([p, q, e], "Надписи")
    lbl(s, ((q[0] + e[0]) / 2, q[1] + 0.6), MA.BOTTOM_CENTER)


def hatch6(pts, pattern, scale):
    h = psp.add_hatch(dxfattribs={"layer": "Штриховка"})
    h.set_pattern_fill(pattern, scale=scale)
    h.paths.add_polyline_path(pts, is_closed=True)


def soil_p(points, step=5.0, n=3, gap=0.7, ln_=1.6):
    """Грунт естественный (ГОСТ 2.306) вдоль линии, со стороны грунта - справа по ходу; мм листа."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        L = hypot(x2 - x1, y2 - y1)
        if L < 1e-9:
            continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        dx, dy = (uy - ux) / 2 ** 0.5, (-ux - uy) / 2 ** 0.5
        t = 1.0
        while t + (n - 1) * gap <= L - 0.5:
            for kk in range(n):
                px, py = x1 + ux * (t + kk * gap), y1 + uy * (t + kk * gap)
                pp([(px, py), (px + dx * ln_, py + dy * ln_)], "Штриховка")
            t += step


def brk(p, q):
    """Линия обрыва (сплошная тонкая с изломом, ГОСТ 2.303) от p к q."""
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    L = hypot(q[0] - p[0], q[1] - p[1])
    ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    pp([p, (mx - ux * 1.5, my - uy * 1.5), (mx - uy * 1.6 - ux * 0.5, my + ux * 1.6 - uy * 0.5),
        (mx + uy * 1.6 + ux * 0.5, my - ux * 1.6 + uy * 0.5), (mx + ux * 1.5, my + uy * 1.5), q], "Штриховка")


def cut6(p, d, look, label, L=6.0):
    """Положение разреза (ГОСТ 2.305): штрих L мм от p наружу по d, стрелка взгляда look, обозначение."""
    e = (p[0] + d[0] * L, p[1] + d[1] * L)
    pp([p, e], "Профиль", w=0.7)
    a = (p[0] + d[0] * (L - 2.0), p[1] + d[1] * (L - 2.0))
    tip = (a[0] + look[0] * 4.5, a[1] + look[1] * 4.5)
    pp([a, (a[0] + look[0] * 2.0, a[1] + look[1] * 2.0)], "Надписи")
    arr(tip, degrees(atan2(look[1], look[0])), L=2.5, wd=1.0, layer="Надписи")
    lbl(label, (tip[0] + look[0] * 2.2 + d[0] * 1.2, tip[1] + look[1] * 2.2 + d[1] * 1.2), h=H_HEAD)


# ---------- машины: блоки из библиотеки строительной техники (tekhnika.py), каток - свой ----------
import tekhnika as TK
TK_SIZE = TK.make_blocks(doc)


def mach(name, p, k, fwd=1, rot=0.0):
    """Вставка блока машины: p - точка привязки на листе, k - мм на 1 м, fwd = -1 - зеркально."""
    psp.add_blockref(name, p, dxfattribs={"xscale": k * fwd, "yscale": k, "rotation": rot, "layer": "Машины"})


def glyph6(p, ang, s, kind):
    """Машина в плане: p - середина машины (у экскаватора - ось поворота), ang - курс
    (у экскаватора - к забою), град; s - мм на 1 м."""
    c, s_ = cos(radians(ang)), sin(radians(ang))
    T = lambda u, v: (p[0] + (u * c - v * s_) * s, p[1] + (u * s_ + v * c) * s)
    if kind == "exc":
        mach("ЭО-4121А план", p, s, rot=ang)
    elif kind == "truck":
        mach("Самосвал план", T(TK.TRUCK_L / 2, 0), s, rot=ang)
    elif kind == "dozer":
        x0, _, x1, _ = TK_SIZE["Бульдозер план"]
        mach("Бульдозер план", T((x1 - x0) / 2, 0), s, rot=ang)
    elif kind == "roller":                               # каток - своим знаком: 4,8 x 1,9, оси колёс
        box_ = lambda u0, v0, u1, v1: pp([T(u0, v0), T(u1, v0), T(u1, v1), T(u0, v1)], "Машины", True)
        box_(-2.4, -0.95, 2.4, 0.95)
        for u in (-1.6, 1.6):
            pp([T(u, -0.95), T(u, 0.95)], "Машины")


def bar(X, p, q, w1, w2):
    """Звено: полоса от p до q (м) шириной w1 -> w2."""
    L_ = hypot(q[0] - p[0], q[1] - p[1])
    nx, ny = -(q[1] - p[1]) / L_, (q[0] - p[0]) / L_
    pp([X(p[0] + nx * w1 / 2, p[1] + ny * w1 / 2), X(q[0] + nx * w2 / 2, q[1] + ny * w2 / 2),
        X(q[0] - nx * w2 / 2, q[1] - ny * w2 / 2), X(p[0] - nx * w1 / 2, p[1] - ny * w1 / 2)], "Машины", True)


def exc_side(g, k, fwd, v_teeth):
    """ЭО-4121А сбоку (библиотека): g - ось поворота на уровне стоянки (мм листа), k - мм на 1 м,
    fwd = ±1 - к забою; оборудование повёрнуто так, что зубья ковша на отметке v_teeth (м).
    Возвращает зубья ковша (м от оси)."""
    X = lambda u, v: (g[0] + fwd * u * k, g[1] + v * k)
    a = TK.exc_angle(v_teeth)
    mach("ЭО-4121А база", g, k, fwd)
    mach("ЭО-4121А оборудование", X(*TK.EXC_PIVOT), k, fwd, rot=fwd * degrees(a))
    b_ = TK.EXC_CYL_BASE                                 # цилиндр подъёма стрелы - между шарнирами
    r_ = TK.rot(TK.EXC_CYL_ROD, a)
    e_ = (TK.EXC_PIVOT[0] + r_[0], TK.EXC_PIVOT[1] + r_[1])
    m_ = (b_[0] + (e_[0] - b_[0]) * 0.6, b_[1] + (e_[1] - b_[1]) * 0.6)
    bar(X, b_, m_, 0.26, 0.26)
    bar(X, m_, e_, 0.11, 0.11)
    for q in (b_, e_):
        psp.add_circle(X(*q), 0.08 * k, dxfattribs={"layer": "Машины"})
    return TK.exc_teeth(a)


def bucket6(c, k, lt=None):
    """Ковш отдельно (положение выгрузки), c - низ ковша."""
    pp([(c[0] - 0.5 * k, c[1] + 0.9 * k), (c[0] - 0.55 * k, c[1] + 0.3 * k), (c[0] - 0.2 * k, c[1]),
        (c[0] + 0.45 * k, c[1]), (c[0] + 0.5 * k, c[1] + 0.9 * k)], "Машины", True, lt=lt)


def truck_side(g, k, fwd, dump=False):
    """Автосамосвал сбоку (библиотека): g - середина машины на дороге; dump - кузов поднят."""
    mach("Самосвал разгрузка" if dump else "Самосвал сбоку", (g[0] + fwd * TK.TRUCK_L / 2 * k, g[1]), k, fwd)


def truck_front(g, k):
    """Автосамосвал спереди (едет на смотрящего): g - середина на дороге."""
    mach("Самосвал спереди", g, k)


def dozer_side(g, k, fwd):
    """Бульдозер сбоку (библиотека): отвал - в g + 2,85 м по ходу; возвращает низ отвала."""
    f_ = (g[0] + fwd * 2.85 * k, g[1])
    mach("Бульдозер сбоку", f_, k, fwd)
    return f_


def roller_side(g, k, fwd):
    """Каток ДУ-31А, самоходный на пневматических шинах, сбоку (в библиотеке катка нет):
    рама с балластным ящиком, моторный отсек, кабина, два ряда колёс; g - середина на опоре."""
    X = lambda u, v: (g[0] + fwd * u * k, g[1] + v * k)
    for u in (-1.7, 1.7):                                # колёса: шина, диск, ступица; крыло над колесом
        for r_ in (0.6, 0.38, 0.1):
            psp.add_circle(X(u, 0.6), r_ * k, dxfattribs={"layer": "Машины"})
        pp([X(u - 0.75, 0.95), X(u - 0.6, 1.35), X(u + 0.6, 1.35), X(u + 0.75, 0.95)], "Машины")
    pp([X(-2.55, 0.85), X(2.55, 0.85), X(2.55, 1.35), X(-2.55, 1.35)], "Машины", True)      # рама
    pp([X(0.1, 1.35), X(2.45, 1.35), X(2.3, 2.15), X(0.25, 2.15)], "Машины", True)          # балластный ящик
    pp([X(-2.5, 1.35), X(-0.3, 1.35), X(-0.3, 1.95), X(-2.35, 1.95)], "Машины", True)       # моторный отсек
    pp([X(-1.95, 1.95), X(-0.5, 1.95), X(-0.6, 3.0), X(-1.85, 3.0)], "Машины", True)        # кабина
    pp([X(-1.75, 2.2), X(-1.25, 2.2), X(-1.25, 2.8), X(-1.7, 2.8)], "Машины", True)         # окна
    pp([X(-1.1, 2.2), X(-0.7, 2.2), X(-0.75, 2.8), X(-1.1, 2.8)], "Машины", True)
    pp([X(-2.45, 1.95), X(-2.45, 2.5)], "Машины")                                          # выхлопная труба


def pit6(T, s):
    """Котлован на плане схемы: бровка с разрывом у съезда, подошва, съезд, бергштрихи."""
    P_ = lambda p: T(f(p[0]), f(p[1]))
    pp([T(XR6, YP2), T(*V6[4]), T(*V6[5]), T(*V6[0]), T(*V6[1]), T(*V6[2]), T(*V6[3]), T(XR6, YP1)], "Котлован")
    for a, b in RG6["brow"]:
        pp([P_(a), P_(b)], "Котлован")
    pp([P_(RG6["end"][0]), P_(RG6["end"][1])], "Котлован")
    pp([T(*p) for p in N6], "Котлован_низ", closed=True)
    for a, b in RG6["toe"] + RG6["edge"]:
        pp([P_(a), P_(b)], "Котлован_низ")
    step = 1.5                                           # бергштрихи через 1,5 мм, через один - короткие
    for i in range(6):
        a, b = T(*V6[i]), T(*V6[(i + 1) % 6])
        na, nb = T(*N6[i]), T(*N6[(i + 1) % 6])
        L = hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        t0 = max(0.0, (na[0] - a[0]) * ux + (na[1] - a[1]) * uy)
        t1 = min(L, (nb[0] - a[0]) * ux + (nb[1] - a[1]) * uy)
        nx, ny = -uy, ux
        d = (na[0] - a[0]) * nx + (na[1] - a[1]) * ny
        kk, t = 0, t0 + step / 2
        while t < t1:
            px, py = a[0] + ux * t, a[1] + uy * t
            if not (i == 3 and T(0, YP1)[1] - 0.3 < py < T(0, YP2)[1] + 0.3):
                ln_ = d if kk % 2 == 0 else d / 2
                pp([(px, py), (px + nx * ln_, py + ny * ln_)], "Бергштрихи")
            kk, t = kk + 1, t + step
    for (a, b), ((_, yt), _) in zip(RG6["brow"], RG6["toe"]):     # откосы съезда
        A, Bp = P_(a), P_(b)
        ytp = T(0, f(yt))[1]
        n = int(hypot(Bp[0] - A[0], Bp[1] - A[1]) / step)
        for kk in range(n):
            t = (kk + 0.5) / n
            px, py = A[0] + (Bp[0] - A[0]) * t, A[1] + (Bp[1] - A[1]) * t
            pp([(px, py), (px, py + (ytp - py) * (1 if kk % 2 == 0 else 0.5))], "Бергштрихи")


# ---------- план 1: разработка грунта экскаватором (прил. 9, торцевые проходки обратной лопаты) ----------
sA = 1.8
TA6 = lambda x, y: (52 + (x - XL6) * sA, 205 + (y - YB6) * sA)
image_title(f"Разработка грунта в котловане экскаватором {MS.EX_NAME}", (130, TITLE_Y))
pit6(TA6, sA)
pp([TA6(XL6, Y12), TA6(XR6, Y12)], "Оси_движения", lt=DASH)            # границы проходок
pp([TA6(XL6, YN6), TA6(XN6, YN6)], "Оси_движения", lt=DASH)
LSTEP = 2.5                                                             # передвижка l на схеме, м
for name, xs, xe, y0, y1, yt in PASSES:
    dr = 1 if xe > xs else -1                                           # направление хода экскаватора
    yc = (y0 + y1) / 2
    hw = (y1 - y0) / 2
    pp([TA6(xs + dr * 0.5, yc), TA6(xe - dr * 1.0, yc)], "Оси_движения", lt=DASHDOT)
    arr(TA6(xe - dr * 1.0, yc), 0 if dr > 0 else 180, layer="Оси_движения")
    xc = xs + dr * (R6 + 3.0)                                           # стоянка: забой - в сторону начала
    r = 0.8 * R6
    al = degrees(asin(min(1.0, hw / r)))
    a0 = 180 if dr > 0 else 0
    psp.add_arc(TA6(xc, yc), r * sA, a0 - al, a0 + al, dxfattribs={"layer": "Котлован"})
    for kk in range(-4, 5):                                             # откос забоя - штрихи к выработке
        a_ = radians(a0 + al * kk / 4.5)
        p0 = (TA6(xc, yc)[0] + cos(a_) * r * sA, TA6(xc, yc)[1] + sin(a_) * r * sA)
        ln_ = (M6 * HD6 * sA) * (1 if kk % 2 == 0 else 0.5)
        pp([p0, (p0[0] + cos(a_) * ln_, p0[1] + sin(a_) * ln_)], "Бергштрихи")
    for j in (1, 2):                                                    # следующие стоянки
        psp.add_circle(TA6(xc + dr * LSTEP * j, yc), 0.45, dxfattribs={"layer": "Оси_движения"})
    glyph6(TA6(xc, yc), 180 if dr > 0 else 0, sA, "exc")
    pp([TA6(xs, yt), TA6(xe - dr * 1.0, yt)], "Транспорт", lt=DASH)
    arr(TA6(xe - dr * 1.0, yt), 0 if dr > 0 else 180, layer="Транспорт")
    glyph6(TA6(xc + dr * 1.0, yt), 0 if dr > 0 else 180, sA, "truck")
    if name != "IV":
        pos = TA6(xe - dr * 4.0, yc)
        lbl(name, (pos[0], pos[1] + 2.8), h=H_HEAD)
# передвижка l - на проходке I
xc1, yc1 = XL6 + R6 + 3.0, (Y12 + YT6) / 2
pdim(TA6(xc1, yc1), TA6(xc1 + LSTEP, yc1), (0, TA6(0, yc1)[1] + 4.5), "l")
# размеры: ширины проходок, длина котлована, ширина съезда
for ya, yb, t_ in ((YT6, Y12, B6), (Y12, YN6, Y12 - YN6), (YN6, YB6, YN6 - YB6)):
    pdim(TA6(XL6, ya), TA6(XL6, yb), (34, 0), num(t_), angle=90)
pdim(TA6(XL6, YB6), TA6(XR6, YN6), (0, 194), num(XR6 - XL6))
pdim(TA6(XE6, f(RG6["end"][0][1])), TA6(XE6, f(RG6["end"][1][1])), (TA6(XE6, 0)[0] + 5, 0), num(K.B_PAN), angle=90)
lbl(f"проходка IV - съезд, i = {f(K.I_PAN):.1f}".replace(".", ","), TA6((XR6 + XE6) / 2 + 1, YP1 - 4.0))
yc3 = (YB6 + YN6) / 2                                                   # разрез 1-1 - по оси проходки III
cut6(TA6(XL6 - 1.0, yc3), (-1, 0), (0, -1), "1")
cut6(TA6(XN6 + 1.0, yc3), (1, 0), (0, -1), "1")

# ---------- план 2: подчистка дна котлована (прил. 9) ----------
sC = 1.2
TC6 = lambda x, y: (52 + (x - XL6) * sC, 129 + (y - YB6) * sC)
image_title("Подчистка дна котлована", (85, 189.5))
pit6(TC6, sC)
YE6, YTR6 = YT6 + 3.5, YT6 + 10.0                    # оси экскаватора и автосамосвалов у северной бровки
pp([TC6(XR6 - 2.0, YE6), TC6(XL6 + 1.0, YE6)], "Оси_движения", lt=DASHDOT)
arr(TC6(XL6 + 1.0, YE6), 180, layer="Оси_движения")
pp([TC6(XR6 + 1.0, YTR6), TC6(XL6 + 1.0, YTR6)], "Транспорт", lt=DASH)
arr(TC6(XL6 + 1.0, YTR6), 180, layer="Транспорт")
XST = [XR6 - 6.0 - 11.0 * j for j in range(4)]        # стоянки экскаватора
for j, x_ in enumerate(XST):
    psp.add_circle(TC6(x_, YE6), 0.45, dxfattribs={"layer": "Оси_движения"})
    lbl(f"ст.{j + 1}", (TC6(x_, YE6)[0], TC6(x_, YE6)[1] + 3.0), MA.BOTTOM_CENTER)
glyph6(TC6(XST[0], YE6), -90, sC, "exc")
glyph6(TC6(XST[0] - 9.0, YTR6), 180, sC, "truck")
# полосы бульдозера: рабочий ход - к экскаватору (на север), холостой - назад, со смещением на полосу
xs_ = []
x_ = N6[3][0] - B_DOZ / 2
while x_ > N6[0][0] + B_DOZ / 2 - 0.5:
    xs_.append(x_)
    x_ -= B_DOZ - 0.4                                  # перекрытие полос 0,3...0,5 м (прил. 9)
ytop = N6[4][1] - 2.0
for j, x_ in enumerate(xs_):
    ybot = (N6[2][1] if x_ > N6[1][0] else N6[0][1]) + 0.8
    pp([TC6(x_, ybot), TC6(x_, ytop)], "Перемещения")
    arr(TC6(x_, ytop), 90, L=1.6, wd=0.8)
    if j + 1 < len(xs_):
        nb = (N6[2][1] if xs_[j + 1] > N6[1][0] else N6[0][1]) + 0.8
        pp([TC6(x_, ytop - 1.5), TC6(xs_[j + 1], nb)], "Перемещения", lt=DASH)
glyph6(TC6(xs_[4], 152.0), 90, sC, "dozer")
for i in (0, 1, 3, 4, 5):                             # углы - подчистка вручную
    c_ = N6[i]
    pv, nx_ = N6[i - 1], N6[(i + 1) % 6]
    d1 = ((pv[0] - c_[0]) / hypot(pv[0] - c_[0], pv[1] - c_[1]), (pv[1] - c_[1]) / hypot(pv[0] - c_[0], pv[1] - c_[1]))
    d2 = ((nx_[0] - c_[0]) / hypot(nx_[0] - c_[0], nx_[1] - c_[1]), (nx_[1] - c_[1]) / hypot(nx_[0] - c_[0], nx_[1] - c_[1]))
    a_ = 2.2
    sq = [TC6(*c_), TC6(c_[0] + d1[0] * a_, c_[1] + d1[1] * a_),
          TC6(c_[0] + (d1[0] + d2[0]) * a_, c_[1] + (d1[1] + d2[1]) * a_), TC6(c_[0] + d2[0] * a_, c_[1] + d2[1] * a_)]
    pp(sq, "Машины", True)
    hatch6(sq, "ANSI37", 0.12)
pp([TC6(XE6 - 1.0, YPC), TC6(XR6 + 1.0, YPC)], "Перемещения", lt=DASH)   # въезд бульдозера по съезду
arr(TC6(XR6 + 1.0, YPC), 180, L=1.6, wd=0.8)
pdim(TC6(xs_[-1] - B_DOZ / 2, N6[0][1] + 14.0), TC6(xs_[-1] + B_DOZ / 2, N6[0][1] + 14.0),
     (0, TC6(0, N6[0][1] + 14.0)[1]), num(B_DOZ))
x22 = XST[0]                                          # разрез 2-2 - через стоянку 1
cut6(TC6(x22, YTR6 + 2.5), (0, 1), (1, 0), "2", L=5.0)
cut6(TC6(x22, YN6 - 1.0), (0, -1), (1, 0), "2", L=5.0)

# ---------- план 3: устройство подсыпки из щебня захватками (прил. 9) ----------
sD = 1.2
TD6 = lambda x, y: (52 + (x - XL6) * sD, 64 + (y - YB6) * sD)
image_title("Устройство подсыпки из щебня", (85, 121))
pit6(TD6, sD)
XZ = [N6[0][0], N6[1][0], (N6[1][0] + N6[3][0]) / 2, N6[3][0]]     # захватки 1-3 по низу котлована
for x_ in XZ[1:3]:
    pp([TD6(x_, N6[2][1]), TD6(x_, N6[4][1])], "Оси_движения", lt=DASH)
for (xa, xb), s_ in zip(zip(XZ, XZ[1:]), ("уплотнение", "разравнивание", "укладка")):
    pdim(TD6(xa, N6[4][1]), TD6(xb, N6[4][1]), (0, TD6(0, YT6 + 2.5)[1]), s_)
# захватка 1: проходы катка по замкнутой схеме, перекрытие 0,2...0,3 м (прил. 9)
cx1 = (XZ[0] + XZ[1]) / 2
for kk in range(3):
    w_, h_ = 16.0 - 2 * kk * 1.7, 7.0 - 2 * kk * 1.7
    rr = h_ / 2
    pts = []
    for t in range(0, 181, 15):
        a_ = -pi / 2 + t * pi / 180
        pts.append(TD6(cx1 + w_ / 2 - rr + rr * cos(a_), YPC + rr * sin(a_)))
    for t in range(0, 181, 15):
        a_ = pi / 2 + t * pi / 180
        pts.append(TD6(cx1 - w_ / 2 + rr + rr * cos(a_), YPC + rr * sin(a_)))
    pp(pts, "Перемещения", True)
arr(TD6(cx1 + 3.0, YPC + 3.5), 0, L=1.6, wd=0.8)
glyph6(TD6(cx1 - 2.0, YPC + 3.5), 0, sD, "roller")
# захватка 2: разравнивание бульдозером к захватке 1
for j, y_ in enumerate((148.0, 152.0, 160.0, 164.0)):
    pp([TD6(XZ[2] - 1.0, y_), TD6(XZ[1] + 1.5, y_)], "Перемещения")
    arr(TD6(XZ[1] + 1.0, y_), 180, L=1.6, wd=0.8)
glyph6(TD6((XZ[1] + XZ[2]) / 2 + 3.0, YPC), 180, sD, "dozer")
# захватка 3: щебень кучами, автосамосвал въезжает по съезду и разгружается задним ходом
for x_ in (XZ[2] + 2.0, XZ[2] + 5.5, XZ[2] + 9.0, XZ[2] + 12.5):
    for y_ in (147.5, 150.5, 161.5, 164.5):
        sq = [TD6(x_ - 1.1, y_ - 1.1), TD6(x_ + 1.1, y_ - 1.1), TD6(x_ + 1.1, y_ + 1.1), TD6(x_ - 1.1, y_ + 1.1)]
        pp(sq, "Машины", True)
        pp([sq[0], sq[2]], "Машины")
        pp([sq[1], sq[3]], "Машины")
glyph6(TD6(XZ[2] + 15.0, YPC), 0, sD, "truck")
pp([TD6(XE6 - 0.5, YPC), TD6(XZ[2] + 20.0, YPC)], "Транспорт", lt=DASH)
arr(TD6(XZ[2] + 19.5, YPC), 180, L=1.6, wd=0.8, layer="Транспорт")
pp([TD6(XZ[1] + 4.0, YB6 + 4.5), TD6(XZ[3] - 3.0, YB6 + 4.5)], "Перемещения")     # направление работ
arr(TD6(XZ[3] - 3.0, YB6 + 4.5), 0, L=2.5, wd=1.0)
lbl("направление работ", TD6((XZ[1] + XZ[3]) / 2, YB6 + 6.5), MA.BOTTOM_CENTER)
cut6(TD6(XL6 - 1.0, YPC), (-1, 0), (0, 1), "3")
cut6(TD6(XE6 + 1.0, YPC), (1, 0), (0, 1), "3")

# ---------- разрез 1-1: забой экскаватора (вид на юг - запад справа) ----------
k1 = 5.2
U1 = lambda u, v: (285.4 + u * k1, 240 + v * k1)
image_title("Разрез 1-1", (337, TITLE_Y))
ub = TK.EXC_FRONT + 1.75                             # бровка забоя: b = 1,5...2,0 м от гусениц (прил. 9)
ut = ub + M6 * HD6                                   # низ забоя
dz = HD6 + EXT * NED6                                # проектное дно на разрезе (недобор утолщён)
uw = ut + 13.0                                       # низ торцевого откоса котлована (выработка)
uwb = uw + M6 * dz                                   # бровка котлована
pp([U1(-4.5, 0), U1(ub, 0), U1(ut, -HD6), U1(uw + M6 * EXT * NED6, -HD6), U1(uwb, 0), U1(uwb + 1.8, 0)], "Профиль")
strip = [U1(ut, -HD6), U1(uw + M6 * EXT * NED6, -HD6), U1(uw, -dz), U1(ut, -dz)]
pp(strip, "Котлован_низ", True)
hatch6(strip, "ANSI31", 0.2)
soil_p([U1(-4.5, 0), U1(ub, 0), U1(ut, -HD6), U1(ut, -dz)])
soil_p([U1(ut, -dz), U1(uw, -dz), U1(uwb, 0), U1(uwb + 1.8, 0)])
tt = exc_side(U1(0, 0), k1, 1, -HD6)               # ковш на дне выработки
pp([U1(0, -0.8), U1(0, 6.6)], "Оси_движения", lt=DASHDOT)
lbl(MS.EX_NAME, U1(-0.4, 3.5), MA.BOTTOM_RIGHT)
pdim(U1(0, 6.2), U1(R6, 6.2), U1(0, 6.2), f"Rmax = {num(R6)}")
pdim(U1(0, -dz), U1(ut, -dz), U1(0, -3.4), "Rн min")
pdim(U1(ut, -dz), U1(tt[0], -dz), U1(0, -3.4), "l")
pdim(U1(0, -dz), U1(tt[0], -dz), U1(0, -4.6), "Rн max")
pdim(U1(TK.EXC_FRONT, 0.45), U1(ub, 0.45), U1(0, 0.45), "b")
pdim(U1(uwb, 0), U1(uw + M6 * EXT * NED6, -HD6), U1(uwb + 2.0, 0), num(HD6), angle=90)
pdim(U1(uwb, 0), U1(uw, -dz), U1(uwb + 3.6, 0), num(HK6), angle=90)
lbl(f"1:{num(M6)}", U1(uw - 0.6, -1.0), MA.MIDDLE_RIGHT)
callout(U1(ut + 9.0, -(HD6 + dz) / 2), U1(ut + 7.0, -3.9), f"недобор {num(NED6)} м", right=True)

# ---------- разрез 2-2: подчистка недобора бульдозером, погрузка экскаватором (вид на восток) ----------
k2 = 4.0
U2 = lambda u, v: (284 + u * k2, 165 + v * k2)
image_title("Разрез 2-2", (337, 210))
ue = 5.5                                             # ось экскаватора от оси автосамосвала (Rвыгр)
ub2 = ue + TK.EXC_FRONT + 1.75                       # бровка
ut2 = ub2 + M6 * HD6                                 # низ откоса на отметке недобора
ud2 = ub2 + M6 * dz                                  # низ откоса на проектной отметке
tu2 = ue + TK.exc_teeth(TK.exc_angle(-HD6 + 0.35))[0]   # ковш набирает грунт из кучи, собранной бульдозером
ux2 = tu2 + 1.4                                      # отвал бульдозера: левее - недобор, правее - дно зачищено
pp([U2(-4.5, 0), U2(ub2, 0), U2(ud2, -dz), U2(29.0, -dz)], "Профиль")
strip = [U2(ut2, -HD6), U2(ux2, -HD6), U2(ux2, -dz), U2(ud2, -dz)]
pp(strip, "Котлован_низ", True)
hatch6(strip, "ANSI31", 0.2)
soil_p([U2(-4.5, 0), U2(ub2, 0), U2(ud2, -dz), U2(29.0, -dz)])
brk(U2(29.0, 1.0), U2(29.0, -dz - 1.0))
heap = [U2(tu2 - 1.4, -HD6), U2(tu2 + 0.3, -HD6 + 0.6), U2(ux2 - 0.05, -HD6)]
pp(heap, "Машины", True)
hatch6(heap, "DOTS", 0.5)
truck_front(U2(0, 0), k2)
exc_side(U2(ue, 0), k2, 1, -HD6 + 0.35)
bucket6(U2(0, 3.45), k2, lt=DASH)                    # ковш над кузовом при выгрузке
P0, P1, P2 = U2(ue + 4.5, 3.6), U2(ue, 7.2), U2(0.9, 4.7)          # кривая Безье: поворот ковша к кузову
bz = [tuple((1 - t) ** 2 * P0[i] + 2 * t * (1 - t) * P1[i] + t * t * P2[i] for i in (0, 1))
      for t in [j / 16 for j in range(17)]]
pp(bz, "Машины", lt=DASH)
arr(bz[-1], degrees(atan2(P2[1] - P1[1], P2[0] - P1[0])), L=1.6, wd=0.8, layer="Машины")
xb = dozer_side(U2(ux2 + 2.85, -dz), k2, -1)         # бульдозер срезает недобор и толкает к экскаватору
for u_ in (0.0, ue):
    pp([U2(u_, -0.6), U2(u_, 6.8)], "Оси_движения", lt=DASHDOT)
pdim(U2(0, 6.8), U2(ue, 6.8), U2(0, 6.8), "Rвыгр")
pdim(U2(0, 0), U2(0, 3.45), U2(-2.4, 0), "Hвыгр", angle=90)
pdim(U2(-1.25, 0), U2(-1.25, 2.85), U2(-3.6, 0), num(MS.TR["hp"]), angle=90)
lbl(MS.TR["name"], U2(0, -1.0), MA.TOP_CENTER)
lbl(MS.EX_NAME, U2(ue - 0.4, 3.5), MA.BOTTOM_RIGHT)
lbl(BUL6, U2(ux2 + 3.7, -dz + 3.2), MA.BOTTOM_CENTER)
callout(U2(ux2 - 2.5, -(HD6 + dz) / 2), U2(ux2 + 0.5, -dz - 1.6), f"недобор {num(NED6)} м", right=True)

# ---------- разрез 3-3: подсыпка по захваткам (вид на север - запад слева), без масштаба ----------
k3 = 3.6
U3 = lambda u, v: (266 + u * k3, 106 + v * k3)
image_title("Разрез 3-3", (337, 136))
HP = EXT * NED6                                      # подсыпка 0,10 м на разрезе - 0,3 м (утолщена)
u1, u2, u3, u4 = M6 * HK6, 12.4, 23.4, 34.4          # низ откоса; границы захваток; начало съезда
ur = 39.5                                            # обрыв на съезде (уклон на схеме утрирован)
vr = -HK6 + (ur - u4) * 0.25
pp([U3(-2.4, 0), U3(0, 0), U3(u1, -HK6), U3(u4, -HK6), U3(ur, vr)], "Профиль")
soil_p([U3(-2.4, 0), U3(0, 0), U3(u1, -HK6), U3(u4, -HK6), U3(ur, vr)])
brk(U3(ur, vr + 1.2), U3(ur, vr - 1.2))
lay = [U3(u1 + M6 * 0.0, -HK6), U3(16.0, -HK6), U3(16.0, -HK6 + HP), U3(u1 - M6 * HP, -HK6 + HP)]
pp(lay, "Котлован_низ", True)
hatch6(lay, "DOTS", 0.5)
pile = [U3(16.0, -HK6), U3(16.0, -HK6 + 0.9), U3(15.0, -HK6 + HP)]
pp(pile, "Машины", True)
hatch6(pile, "DOTS", 0.5)
for uc in (25.0, 27.6):                              # кучи щебня
    tri = [U3(uc - 1.1, -HK6), U3(uc, -HK6 + 0.9), U3(uc + 1.1, -HK6)]
    pp(tri, "Машины", True)
    hatch6(tri, "DOTS", 0.5)
roller_side(U3(7.0, -HK6 + HP), k3, 1)
dozer_side(U3(16.05 + 2.85, -HK6), k3, -1)
truck_side(U3(31.0, -HK6), k3, 1, dump=True)
for (ua, ub_), s_ in zip(((u1, u2), (u2, u3), (u3, u4)), ("уплотнение", "разравнивание", "укладка")):
    pdim(U3(ua, -HK6), U3(ub_, -HK6), U3(0, -HK6 - 2.2), s_)
pdim(U3(0, 0), U3(u1, -HK6), U3(-1.8, 0), num(HK6), angle=90)
callout(U3(10.5, -HK6 + HP / 2), U3(11.0, 2.0), f"щебень {num(K.H_PODS)} м", right=True)
lbl(KAT6, U3(7.0, -HK6 + HP + 3.3), MA.BOTTOM_CENTER)
lbl(BUL6, U3(19.8, -HK6 + 3.2), MA.BOTTOM_CENTER)
lbl(MS.TR["name"], U3(31.0, 3.3), MA.BOTTOM_CENTER)
lbl(f"съезд, i = {f(K.I_PAN):.1f}".replace(".", ","), U3(39.0, 0.6), MA.BOTTOM_RIGHT)

# ---------- условные обозначения, примечания, ведомость машин ----------
LX6, LY6 = 172, 184
txt("Условные обозначения", (LX6, LY6), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
for j, (kind, s_) in enumerate((
        ("exc", "ось движения экскаватора, стоянка"),
        ("tr", "ось движения автосамосвалов"),
        ("doz", "рабочий и холостой ход бульдозера"),
        ("man", "подчистка дна вручную"),
        ("pile", "щебень, выгруженный кучами"),
        ("rol", "проходы катка"),
        ("num", "номер проходки экскаватора"))):
    y = LY6 - 5.5 - 6.2 * j
    sx0, sx1 = LX6, LX6 + 14
    if kind == "exc":
        pp([(sx0, y), (sx1 - 2.5, y)], "Оси_движения", lt=DASHDOT)
        arr((sx1, y), 0, layer="Оси_движения")
        psp.add_circle((sx0 + 4, y), 0.45, dxfattribs={"layer": "Оси_движения"})
    elif kind == "tr":
        pp([(sx0, y), (sx1 - 2.5, y)], "Транспорт", lt=DASH)
        arr((sx1, y), 0, layer="Транспорт")
    elif kind == "doz":
        pp([(sx0, y + 1.2), (sx1 - 2.0, y + 1.2)], "Перемещения")
        arr((sx1, y + 1.2), 0, L=1.6, wd=0.8)
        pp([(sx0, y - 1.2), (sx1, y - 1.2)], "Перемещения", lt=DASH)
    elif kind == "man":
        sq = [(sx0 + 4.5, y - 2), (sx0 + 9.5, y - 2), (sx0 + 9.5, y + 2), (sx0 + 4.5, y + 2)]
        pp(sq, "Машины", True)
        hatch6(sq, "ANSI37", 0.12)
    elif kind == "pile":
        sq = [(sx0 + 5, y - 1.6), (sx0 + 8.2, y - 1.6), (sx0 + 8.2, y + 1.6), (sx0 + 5, y + 1.6)]
        pp(sq, "Машины", True)
        pp([sq[0], sq[2]], "Машины")
        pp([sq[1], sq[3]], "Машины")
    elif kind == "rol":
        pp([(sx0 + 2, y - 1.5), (sx1 - 2, y - 1.5), (sx1, y), (sx1 - 2, y + 1.5), (sx0 + 2, y + 1.5),
            (sx0, y)], "Перемещения", True)
    elif kind == "num":
        txt("II", (sx0 + 7, y), H_HEAD, TA.MIDDLE_CENTER, "Надписи")
    txt("- " + s_, (sx1 + 3, y), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)

txt("Примечания", (LX6, 129), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
NOTES6 = [
    f"1. Котлован разрабатывается торцевыми проходками I-III шириной не более 1,5Rmax = {num(B6)} м "
    f"с недобором {num(NED6)} м (прил. 7); съезд - проходкой IV.",
    "2. Грунт грузится в автосамосвалы и весь вывозится в насыпь планировки: пазухи и съезд засыпаются "
    "привозным песком (табл. 3).",
    "3. Недобор срезается бульдозером и подается к экскаватору; у откосов и в углах дно подчищается вручную.",
    f"4. Подсыпка из щебня толщиной {num(K.H_PODS)} м устраивается захватками от дальнего конца котлована "
    "к съезду: укладка, разравнивание, уплотнение.",
    "5. Rmax, Rн min, Rн max - радиусы копания на уровне стоянки и дна; l - длина передвижки; "
    "Rвыгр, Hвыгр - радиус и высота выгрузки; b = 1,5...2,0 м - от гусениц до бровки забоя.",
]
mt(W08 + "\\P".join(NOTES6), (LX6, 126), H_TEXT, 81, MA.TOP_LEFT, "Надписи")

dec = lambda v, n: f"{f(v):.{n}f}".replace(".", ",")
MACH6 = [  # ведомость машин (п. 2.3.2; характеристики - прил. 8 и ЕНиР Е2-1, табл. 1 параграфов)
    ("Экскаватор, обратная лопата", MS.EX_NAME, 1,
     f"гидравлический, ковш {dec(MS.V_KOV, 2)} {M3}, Rmax {dec(MS.EX_R, 1)} м, Hк max {dec(MS.EX_HK, 1)} м, "
     f"Hв max {dec(MS.EX_HV, 1)} м"),
    ("Автосамосвал", MS.TR["name"], MS.TR["N"],
     f"кузов {dec(MS.TR['Va'], 1)} {M3}, грузоподъемность {dec(MS.TR['Pa'], 0)} т, погрузочная высота "
     f"{dec(MS.TR['hp'], 2)} м"),
    ("Бульдозер", "ДЗ-35С (Д-575С), Т-180", 1, "отвал неповоротный 3,64 х 1,29 м, 132 кВт"),
    ("Каток на пневмошинах", MS.KATOK_POD[1].split(",")[0], 1,
     "самоходный, полоса 1,9 м, слой до 0,35 м, 66 кВт, 16 т"),
]
txt("Ведомость машин", (LX, 58), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
CW6 = [44, 40, 10, 106]
for r, row in enumerate([("Наименование", "Марка", "Кол.", "Технические характеристики")] + MACH6):
    y = 58 - 3 - 7 * r
    x = LX
    for c, v in enumerate(row):
        pl([(x, y), (x + CW6[c], y), (x + CW6[c], y - 7), (x, y - 7)], "Штамп", True)
        left = r > 0 and c in (0, 1, 3)
        txt(str(v), (x + 1.5 if left else x + CW6[c] / 2, y - 3.5), H_TEXT,
            TA.MIDDLE_LEFT if left else TA.MIDDLE_CENTER, "Надписи", NARROW)
        x += CW6[c]

# ================= лист 7: схема производства работ по обратной засыпке (разд. 3, п. 5; прил. 9) =================
# Как прил. 9 (с. 47): план - котлован со зданием, резерв песка вдоль бровки, бульдозер сдвигает
# песок в пазуху, уплотнение электротрамбовками у стен, каток - не ближе 0,8 м от стены; разрез 1-1
# по этапам: устройство резерва автосамосвалом, засыпка пазухи бульдозером, послойное уплотнение.
# Пазухи и съезд - привозной песок (лекции 09.10 и 23.10: грунт не песок, табл. 3). Без масштаба.
psp = doc.layouts.new("Лист 7")
a3(psp)
frame_and_stamp(7, None, "Технологическая схема производства\\Pработ по обратной засыпке", None)
TRB = MS.TRAMB[1]                                    # электротрамбовка
H_SL7, N_SL7 = f(MS.H_SL), MS.N_SL                   # слой засыпки, число слоёв
ST = [tuple(map(f, p)) for p in K.contour(K.D_ST)]   # наружная грань стен
STI = [tuple(map(f, p)) for p in K.contour(-K.D_ST)] # внутренняя грань стен
FP7 = [tuple(map(f, p)) for p in K.contour(K.D_FP)]  # край фундаментной плиты
X07, Y07 = f(K.X0), f(K.Y0)
YW = ST[4][1]                                        # наружная грань северной стены
XW = ST[3][0]                                        # наружная грань восточной стены


def tramb(p, s=1.0):
    """Электротрамбовка в плане - условно: башмак с рукояткой; p - центр, s - множитель размера."""
    pp([(p[0] - 1.1 * s, p[1] - 0.9 * s), (p[0] + 1.1 * s, p[1] - 0.9 * s), (p[0] + 1.1 * s, p[1] + 0.9 * s),
        (p[0] - 1.1 * s, p[1] + 0.9 * s)], "Машины", True)
    pp([(p[0], p[1] + 0.9 * s), (p[0], p[1] + 2.6 * s)], "Машины")
    pp([(p[0] - 0.8 * s, p[1] + 2.6 * s), (p[0] + 0.8 * s, p[1] + 2.6 * s)], "Машины")


def tramb_side(g, k):
    """Электротрамбовка ИЭ-4502 сбоку: башмак 0,45 м, корпус, рукоятка; g - середина башмака на слое."""
    X = lambda u, v: (g[0] + u * k, g[1] + v * k)
    pp([X(-0.23, 0), X(0.23, 0), X(0.23, 0.08), X(-0.23, 0.08)], "Машины", True)
    pp([X(-0.17, 0.08), X(0.17, 0.08), X(0.14, 0.55), X(-0.14, 0.55)], "Машины", True)
    pp([X(-0.05, 0.5), X(-0.6, 1.05)], "Машины")
    pp([X(-0.72, 0.93), X(-0.48, 1.17)], "Машины")


def axis_mark(c, label, r=3.0):
    """Марка оси: окружность и буква/цифра (ГОСТ Р 21.101)."""
    psp.add_circle(c, r, dxfattribs={"layer": "Надписи"})
    lbl(label, c, h=H_HEAD)


# ---------- план: обратная засыпка пазух ----------
sP = 1.7
TP = lambda x, y: (38 + (x - 203) * sP, 178 + (y - 122) * sP)
image_title("Схема обратной засыпки пазух котлована", (137, TITLE_Y))
pit6(TP, sP)
wall = psp.add_hatch(dxfattribs={"layer": "Котлован"})        # стены - сплошной заливкой между гранями
wall.set_solid_fill(color=256)
wall.paths.add_polyline_path([TP(*p) for p in ST], is_closed=True)
wall.paths.add_polyline_path([TP(*p) for p in STI], is_closed=True)
pp([TP(*p) for p in ST], "Котлован", True)
pp([TP(*p) for p in FP7], "Котлован_низ", True)
for x_, s_ in ((X07, "1"), (X07 + K.BX - K.CUT_X, "2"), (X07 + K.BX, "3")):      # оси здания
    pp([TP(x_, 120 + 3 / sP), TP(x_, Y07 + K.BY + 1.5)], "Оси_движения", lt=DASHDOT)
    axis_mark(TP(x_, 120), s_)
for y_, s_ in ((Y07, "А"), (Y07 + K.CUT_Y, "Б"), (Y07 + K.BY, "В")):
    pp([TP(205 + 3 / sP, y_), TP(X07 + K.BX + 1.5, y_)], "Оси_движения", lt=DASHDOT)
    axis_mark(TP(205, y_), s_)
RES = [  # резерв песка вдоль бровки (за призмой обрушения - 1 м), ширина 5 м; север - уже частично израсходован
    (250.0, YT6 + 1.0, XR6, YT6 + 6.0),
    (XL6, YB6 - 6.0, XN6, YB6 - 1.0),
    (XN6 + 1.0, YN6 - 6.0, XR6, YN6 - 1.0),
    (XL6 - 6.0, YB6, XL6 - 1.0, YT6),
]
for x0_, y0_, x1_, y1_ in RES:
    q = [TP(x0_, y0_), TP(x1_, y0_), TP(x1_, y1_), TP(x0_, y1_)]
    pp(q, "Машины", True)
    hatch6(q, "DOTS", 0.5)
# северная пазуха: засыпано и уплотнено - уплотнение трамбовками - засыпка бульдозером
done = [TP(XL6 + 0.3, YW), TP(236.0, YW), TP(236.0, YT6 - 0.3), TP(XL6 + 0.3, YT6 - 0.3)]
hatch6(done, "ANSI31", 0.35)
pp(done, "Машины", True)
for x_ in (240.0, 245.0):
    tramb(TP(x_, (YW + YT6) / 2 - 0.4), 0.9)
for x_ in (251.5, 255.5, 259.5):                     # бульдозер: рабочий ход - к котловану, холостой - назад
    pp([TP(x_, YT6 + 5.5), TP(x_, YT6 + 0.4)], "Перемещения")
    arr(TP(x_, YT6 + 0.4), -90, L=1.6, wd=0.8)
for xa, xb in ((251.5, 255.5), (255.5, 259.5)):
    pp([TP(xa + 0.4, YT6 + 0.9), TP(xb - 0.4, YT6 + 5.5)], "Перемещения", lt=DASH)
glyph6(TP(263.5, YT6 + 4.0), -90, sP, "dozer")
YTR7 = YT6 + 9.0                                     # ось движения автосамосвалов вдоль резерва
pp([TP(XR6 + 3.0, YTR7), TP(248.0, YTR7)], "Транспорт", lt=DASH)
arr(TP(248.0, YTR7), 180, layer="Транспорт")
glyph6(TP(278.0, YTR7), 180, sP, "truck")
# широкая зона у съезда: песок - по съезду, каток - не ближе 0,8 м от стены, у стены - трамбовки
xr0 = XW + f(MS.KATOK_MIN)
for kk in range(2):
    w_ = 3.8 - 2 * kk * 0.95
    x0_, x1_ = xr0 + kk * 0.95, xr0 + kk * 0.95 + w_
    y0_, y1_ = N6[2][1] + 1.5 + kk * 0.95, YW - 1.0 - kk * 0.95
    rr = (x1_ - x0_) / 2
    pts = []
    for t in range(0, 181, 15):
        a_ = t * pi / 180
        pts.append(TP((x0_ + x1_) / 2 + rr * cos(a_), y1_ - rr + rr * sin(a_)))
    for t in range(180, 361, 15):
        a_ = t * pi / 180
        pts.append(TP((x0_ + x1_) / 2 + rr * cos(a_), y0_ + rr + rr * sin(a_)))
    pp(pts, "Перемещения", True)
glyph6(TP(xr0 + 0.95, (N6[2][1] + YW) / 2), 90, sP, "roller")
tramb(TP(XW + 0.4, N6[2][1] + 4.0), 0.9)
pp([TP(XE6 - 0.5, YPC), TP(XR6 - 1.0, YPC)], "Транспорт", lt=DASH)
arr(TP(XR6 - 1.0, YPC), 180, L=1.6, wd=0.8, layer="Транспорт")
callout(TP(xr0 + 2.0, 149.0), TP(xr0 + 9.0, 147.0), f"каток не ближе {dec(MS.KATOK_MIN, 1)} м от стены")
# резерв песка для засыпки съезда - у конца съезда (грунт площадки не песок, лекция 23.10)
OTV = [TP(XE6 + 2.0, YPC - 5.0), TP(XE6 + 7.0, YPC - 5.0), TP(XE6 + 7.0, YPC + 5.0), TP(XE6 + 2.0, YPC + 5.0)]
pp(OTV, "Машины", True)
hatch6(OTV, "DOTS", 0.5)
lbl("направление работ", TP(250.0, YW - 5.0), MA.BOTTOM_CENTER)
pp([TP(226.0, YW - 6.0), TP(274.0, YW - 6.0)], "Перемещения")
arr(TP(274.0, YW - 6.0), 0, L=2.5, wd=1.0)
cut6(TP(256.8, YTR7 + 1.0), (0, 1), (1, 0), "1", L=5.0)
cut6(TP(256.8, YW - 9.0), (0, -1), (1, 0), "1", L=5.0)


# ---------- разрез 1-1 по этапам (вид на восток: снаружи - слева, стена - справа) ----------
UB = M6 * HK6                                        # низ откоса
U_PODG, U_PL, U_ST = UB + 0.5, UB + 0.7, UB + 1.2    # край подготовки, плиты, наружная грань стены
V_PODS, V_PODG, V_PL = -HK6 + f(K.H_PODS), -HK6 + f(K.H_PODS + K.H_BP), -HK6 + f(K.H_PODS + K.H_BP + K.H_FP)
UR7 = U_ST + 2.9                                     # обрыв справа (внутри здания)


def stage_base(y0, k, x0, ul, fill_top=None, layers=0):
    """Общая часть разреза: грунт, откос, дно с подсыпкой, подготовка, плита, стена; бровка - в x0,
    уровень земли - y0, k - мм на 1 м, ul - левый край (м); fill_top - верх засыпки пазухи (м),
    layers - показать границы слоёв."""
    U = lambda u, v: (x0 + u * k, y0 + v * k)
    pp([U(ul, 0), U(0, 0), U(UB, -HK6), U(UR7, -HK6)], "Профиль")
    soil_p([U(ul, 0), U(0, 0), U(UB, -HK6), U(UR7, -HK6)])
    pp([U(UB - M6 * f(K.H_PODS), V_PODS), U(UR7, V_PODS)], "Котлован_низ")                    # подсыпка
    pp([U(U_PODG, V_PODS), U(U_PODG, V_PODG), U(UR7, V_PODG)], "Котлован_низ")                # подготовка
    pl_ = [U(U_PL, V_PODG), U(UR7, V_PODG), U(UR7, V_PL), U(U_PL, V_PL)]
    pp(pl_, "Профиль", True)                                                                 # плита
    hatch6(pl_, "ANSI31", 0.3)
    st_ = [U(U_ST, V_PL), U(U_ST + 0.4, V_PL), U(U_ST + 0.4, 1.0), U(U_ST, 1.0)]
    pp(st_, "Профиль", True)                                                                 # стена
    hatch6(st_, "ANSI31", 0.3)
    brk(U(UR7, 1.2), U(UR7, -HK6 - 0.8))
    brk(U(U_ST - 0.2, 1.0), U(U_ST + 0.6, 1.0))
    if fill_top is not None:                         # засыпка пазухи песком
        uf = -fill_top * M6
        poly = [U(uf, fill_top), U(M6 * (HK6 - f(K.H_PODS)), V_PODS), U(U_PODG, V_PODS), U(U_PODG, V_PODG),
                U(U_PL, V_PODG), U(U_PL, V_PL), U(U_ST, V_PL), U(U_ST, fill_top)]
        pp(poly, "Машины", True)
        hatch6(poly, "DOTS", 0.5)
        for kk in range(1, N_SL7 + 1):               # границы слоёв: засыпанные - сплошные, следующие - штриховые
            v_ = -HK6 + kk * H_SL7
            if not layers or v_ > 1e-6:
                continue
            ue_ = U_PL if v_ < V_PL else U_ST
            pp([U(-v_ * M6, v_), U(ue_, v_)], "Машины", lt=None if v_ <= fill_top + 1e-6 else DASH)
    return U


# этап 1: автосамосвал отсыпает песок в резерв за призмой обрушения
y1, k1_ = 240, 7.0
U = stage_base(y1, k1_, 356.5, -13.5)
image_title("Разрез 1-1. Устройство резерва песка", (337, TITLE_Y))
heap = [U(-6.0, 0), U(-3.5, 1.6), U(-1.0, 0)]
pp(heap, "Машины", True)
hatch6(heap, "DOTS", 0.5)
truck_side((U(-6.0 + 0.5 - TK.TRUCK_L / 2 - 0.6, 0)), k1_, -1, dump=True)
lbl(MS.TR["name"], U(-10.5, 5.0), MA.BOTTOM_CENTER)
pdim(U(-1.0, 0), U(0, 0), U(0, 2.3), "a")
callout(U(-3.0, 0.9), U(-1.5, 3.3), "резерв песка", right=True)

# этап 2: бульдозер сдвигает песок из резерва в пазуху
y2, k2_ = 176, 8.0
fill2 = -1.25
U = stage_base(y2, k2_, 347.0, -8.0)
image_title("Разрез 1-1. Засыпка пазухи бульдозером", (337, 210))
uf = -fill2 * M6
sand = [U(-0.15 * M6, -0.15), U(M6 * (HK6 - f(K.H_PODS)), V_PODS), U(U_PODG, V_PODS), U(U_PODG, V_PODG),
        U(U_PL, V_PODG), U(U_PL, V_PL), U(U_ST, V_PL), U(U_ST, fill2)]
pp(sand, "Машины", True)
hatch6(sand, "DOTS", 0.5)
lump = [U(-0.9, 0), U(-0.1, 0.55), U(0.25, 0)]       # песок перед отвалом
pp(lump, "Машины", True)
hatch6(lump, "DOTS", 0.5)
dozer_side(U(-0.15 - 2.85, 0), k2_, 1)
lbl(BUL6, U(-3.8, 3.2), MA.BOTTOM_CENTER)

# этап 3: послойное уплотнение электротрамбовками
y3, k3_ = 115, 14.0
done3 = 4                                            # засыпано и уплотнено слоёв
top3 = -HK6 + done3 * H_SL7
U = stage_base(y3, k3_, 319.5, -3.0, fill_top=top3, layers=done3)
image_title("Разрез 1-1. Уплотнение слоев электротрамбовками", (337, 136))
tramb_side(U(U_ST - 0.45, top3), k3_)
tramb_side(U(U_ST - 1.6, top3), k3_)
callout(U(U_ST - 0.45, top3 + 0.45), U(U_ST + 0.9, 0.6), f"электротрамбовки {TRB}", right=True)
pdim(U(UR7 - 0.5, -HK6), U(UR7 - 0.5, 0), U(UR7 - 0.5, 0), num(HK6), angle=90)
callout(U(1.0, top3 - H_SL7 / 2), U(-0.6, 0.9), f"hсл = {num(H_SL7)} м ({N_SL7} слоев)", right=False)

# ---------- условные обозначения, примечания, ведомость машин ----------
LX7, LY7 = 26, 160
txt("Условные обозначения", (LX7, LY7), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
for j, (kind, s_) in enumerate((
        ("res", "резерв песка"),
        ("done", "пазуха засыпана и уплотнена"),
        ("tr", "ось движения автосамосвалов"),
        ("doz", "рабочий и холостой ход бульдозера"),
        ("rol", "проходы катка"),
        ("trb", "уплотнение электротрамбовкой"))):
    y = LY7 - 5.5 - 6.2 * j
    sx0, sx1 = LX7, LX7 + 14
    if kind in ("res", "done", "otv"):
        q = [(sx0 + 2, y - 2), (sx1 - 2, y - 2), (sx1 - 2, y + 2), (sx0 + 2, y + 2)]
        pp(q, "Машины", True)
        hatch6(q, {"res": "DOTS", "done": "ANSI31", "otv": "ANSI37"}[kind], {"res": 0.5}.get(kind, 0.35))
    elif kind == "tr":
        pp([(sx0, y), (sx1 - 2.5, y)], "Транспорт", lt=DASH)
        arr((sx1, y), 0, layer="Транспорт")
    elif kind == "doz":
        pp([(sx0, y + 1.2), (sx1 - 2.0, y + 1.2)], "Перемещения")
        arr((sx1, y + 1.2), 0, L=1.6, wd=0.8)
        pp([(sx0, y - 1.2), (sx1, y - 1.2)], "Перемещения", lt=DASH)
    elif kind == "rol":
        pp([(sx0 + 2, y - 1.5), (sx1 - 2, y - 1.5), (sx1, y), (sx1 - 2, y + 1.5), (sx0 + 2, y + 1.5),
            (sx0, y)], "Перемещения", True)
    elif kind == "trb":
        tramb((sx0 + 7, y - 1.0), 0.9)
    txt("- " + s_, (sx1 + 3, y), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)

NX7 = 125
txt("Примечания", (NX7, LY7), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
NOTES7 = [
    f"1. Обратная засыпка пазух ведется после устройства подземной части здания привозным песком: "
    f"объем пазух {num(RS.V_PAZ)} {M3}, песка в плотном теле {num(RS.T3_PRIVOZ[0][1])} {M3} (табл. 3).",
    f"2. Песок завозится автосамосвалами {MS.TR['name']} в резерв вдоль бровки котлована за призмой обрушения (a); "
    "в широкую зону у съезда - по съезду.",
    f"3. Песок сдвигается в пазуху бульдозером {BUL6}, разравнивается вручную и уплотняется электротрамбовками "
    f"{TRB} слоями {num(H_SL7)} м ({N_SL7} слоев, глубина уплотнения {TRB} - {dec(MS.H_UPL, 1)} м); "
    f"в зоне у съезда не ближе {dec(MS.KATOK_MIN, 1)} м от стены - катком {KAT6}.",
    f"4. Съезд засыпается последним тоже привозным песком ({num(RS.T3_PRIVOZ[1][1])} {M3}): автосамосвалы "
    f"разгружаются на съезде, бульдозер разравнивает, каток {KAT6} уплотняет послойно.",
]
mt(W08 + "\\P".join(NOTES7), (NX7, LY7 - 3), H_TEXT, 100, MA.TOP_LEFT, "Надписи")

MACH7 = [
    ("Автосамосвал", MS.TR["name"], MS.TR["N"],
     f"кузов {dec(MS.TR['Va'], 1)} {M3}, грузоподъемность {dec(MS.TR['Pa'], 0)} т"),
    ("Бульдозер", "ДЗ-35С (Д-575С), Т-180", 1, "отвал неповоротный 3,64 х 1,29 м, 132 кВт"),
    ("Электротрамбовка", TRB, MS.N_TRAMB, f"уплотнение на {dec(MS.H_UPL, 1)} м за 2 прохода, башмак 350 х 450 мм, "
                                          "0,4 кВт, 81,5 кг"),
    ("Каток на пневмошинах", MS.KATOK_POD[1].split(",")[0], 1, "самоходный, полоса 1,9 м, слой до 0,35 м, 66 кВт, 16 т"),
]
txt("Ведомость машин и механизмов", (LX, 58), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
for r, row in enumerate([("Наименование", "Марка", "Кол.", "Технические характеристики")] + MACH7):
    y = 58 - 3 - 7 * r
    x = LX
    for c, v in enumerate(row):
        pl([(x, y), (x + CW6[c], y), (x + CW6[c], y - 7), (x, y - 7)], "Штамп", True)
        left = r > 0 and c in (0, 1, 3)
        txt(str(v), (x + 1.5 if left else x + CW6[c] / 2, y - 3.5), H_TEXT,
            TA.MIDDLE_LEFT if left else TA.MIDDLE_CENTER, "Надписи", NARROW)
        x += CW6[c]

# ================= лист 8: график производства земляных работ (разд. 3, п. 6; табл. 13) =================
# Форма табл. 13 методички: графы 1-9 - по калькуляции (табл. 12), календарная часть - дни со
# сменами; горизонтальные линии - продолжительность процессов по сменам, над линией - число
# исполнителей; вертикальные - технологические связи. Работа в 2 смены (у разравнивания и
# уплотнения насыпи - в 1 смену). Между планировкой и обратной засыпкой - устройство подземной
# части здания (вне карты). Без масштаба.
import kalkulyaciya as KL
psp = doc.layouts.new("Лист 8")
a3(psp)
frame_and_stamp(8, None, "График производства\\Pземляных работ", None)
image_title("График производства земляных работ", (217.5, TITLE_Y))
u_ = lambda s: s.replace("м²", M2).replace("м³", M3)

CW8 = [7, 50, 10, 12, 11, 11, 34, 9, 9, 10]            # графы 1-9 (+ №)
X8 = [22]
for w_ in CW8:
    X8.append(X8[-1] + w_)
XC0, XC1 = X8[-1], 410.0                                # календарная часть
DAYS1, DAYS2 = list(range(1, KL.BREAK_AFTER + 1)), list(range(KL.BREAK_AFTER + 1, KL.N_DAYS + 1))
WBR = 6.0                                               # столбец перерыва
DW = (XC1 - XC0 - WBR) / (len(DAYS1) + len(DAYS2))      # ширина дня, мм
XB0 = XC0 + len(DAYS1) * DW                             # начало столбца перерыва


def xday(d):
    """Левый край дня d в календаре."""
    return XC0 + (d - 1) * DW if d <= KL.BREAK_AFTER else XB0 + WBR + (d - KL.BREAK_AFTER - 1) * DW


YT8 = 276.0
HH1, HH2, HH3 = 18.0, 6.0, 5.0                          # шапка: заголовки, дни, номера граф / смены
RH = 12.0                                               # строка процесса
YH1, YH2, YH3 = YT8 - HH1, YT8 - HH1 - HH2, YT8 - HH1 - HH2 - HH3
YB8 = YH3 - RH * len(KL.SCHED)


def ln8(p, q, lw=25):
    psp.add_line(p, q, dxfattribs={"layer": "Штамп", "lineweight": lw})


# сетка таблицы: наружная рамка - основная линия, внутренние - тонкие
pp([(X8[0], YT8), (XC1, YT8), (XC1, YB8), (X8[0], YB8)], "Штамп", True).dxf.lineweight = 50
for c in range(1, len(X8)):
    ln8((X8[c], YH1 + 5 if c == 8 else YT8), (X8[c], YB8))
for k in range(len(KL.SCHED) + 1):
    ln8((X8[0], YH3 - RH * k), (XC1, YH3 - RH * k))
ln8((X8[0], YH3), (XC1, YH3), 50)
ln8((X8[7], YH1 + 5), (X8[9], YH1 + 5))                 # «Время выполнения» над сменами и днями
ln8((XC0, YH1), (XC1, YH1))                            # календарь: заголовок / дни
ln8((XC0, YH2), (XC1, YH2))                            # дни / смены
for d in DAYS1 + DAYS2:
    x_ = xday(d)
    ln8((x_, YH1), (x_, YB8), 25 if d != 1 else 25)
    ln8((x_ + DW / 2, YH2), (x_ + DW / 2, YB8), 13)     # граница смен
ln8((XB0, YH1), (XB0, YB8))
# шапка граф 1-9
HEAD8 = ["№ п/п", "Наименование процессов", "Ед. изм.", "Объем работ", "Затраты труда, чел.-дн",
         "Затраты машинного времени, маш.-см", "Исполнители", "Смены", "Дни", "Уп.т, %"]
VERT = {2, 3, 4, 5, 9}                                  # узкие графы - текст вертикально, как в форме
for c, s_ in enumerate(HEAD8):
    xm = (X8[c] + X8[c + 1]) / 2
    if c in (7, 8):
        lbl(s_, (xm, (YH1 + 5 + YH2) / 2), MA.MIDDLE_CENTER)
        continue
    if c in VERT:
        m = psp.add_mtext(W08 + s_, dxfattribs={"layer": "Надписи", "style": TXT, "char_height": H_TEXT,
                                                "rotation": 90, "width": HH1 + HH2 - 1})
        m.set_location((xm, (YT8 + YH2) / 2), attachment_point=MA.MIDDLE_CENTER)
    else:
        mt(W08 + s_, (xm, (YT8 + YH2) / 2), H_TEXT, CW8[c] - 1, MA.MIDDLE_CENTER, "Надписи")
mt(W08 + "Время выполнения работ", ((X8[7] + X8[9]) / 2, (YT8 + YH1 + 5) / 2), H_TEXT, X8[9] - X8[7] - 1,
   MA.MIDDLE_CENTER, "Надписи")
lbl("Смены / дни", ((XC0 + XC1) / 2, (YT8 + YH1) / 2), MA.MIDDLE_CENTER, h=H_HEAD)
for d in DAYS1 + DAYS2:
    lbl(str(d), (xday(d) + DW / 2, (YH1 + YH2) / 2), MA.MIDDLE_CENTER)
    for s_ in (1, 2):
        psp.add_mtext("\\W0.7;" + str(s_), dxfattribs={"layer": "Надписи", "style": TXT, "char_height": 2.0}) \
            .set_location((xday(d) + DW / 4 + (s_ - 1) * DW / 2, (YH2 + YH3) / 2), attachment_point=MA.MIDDLE_CENTER)
for c in range(len(HEAD8)):
    if c:                                               # номера граф 1-9 (№ п/п - без номера, как в форме)
        lbl(str(c), ((X8[c] + X8[c + 1]) / 2, (YH2 + YH3) / 2), MA.MIDDLE_CENTER)
ln8((X8[0], YH2), (XC0, YH2))
# перерыв: устройство подземной части здания
m = psp.add_mtext(W08 + "устройство подземной части здания (по отдельной технологической карте)",
                  dxfattribs={"layer": "Надписи", "style": TXT, "char_height": H_TEXT, "rotation": 90,
                              "width": YH3 - YB8 - 4})
m.set_location((XB0 + WBR / 2, (YH3 + YB8) / 2), attachment_point=MA.MIDDLE_CENTER)
hatch_ = psp.add_hatch(dxfattribs={"layer": "Штриховка"})
hatch_.set_pattern_fill("ANSI31", scale=0.5)
hatch_.paths.add_polyline_path([(XB0, YH1), (XB0 + WBR, YH1), (XB0 + WBR, YH2), (XB0, YH2)], is_closed=True)

# строки процессов и линии графика
YROW = []
for k, q in enumerate(KL.SCHED):
    y0, y1 = YH3 - RH * (k + 1), YH3 - RH * k
    ym = (y0 + y1) / 2
    YROW.append(ym)
    vals = [str(k + 1), q["name"], u_(q["unit"]), dec(q["vol"], 2), num(q["th"]), num(q["mach"]),
            ", ".join(f"{p} - {c_}" for p, c_ in q["crew"]), str(q["t"]), str(q["days"]), dec(q["upt"], 1)]
    for c, v in enumerate(vals):
        xm = (X8[c] + X8[c + 1]) / 2
        if c in (1, 6):
            mt(W08 + v, (X8[c] + 1.2, ym), H_TEXT, CW8[c] - 2, MA.MIDDLE_LEFT, "Надписи")
        else:
            lbl(v, (xm, ym), MA.MIDDLE_CENTER)
    # линия по занятым сменам; смежные смены - одной линией
    sh = q["shifts"]
    segs, cur = [], None
    for d, s_ in sh:
        xa = xday(d) + (s_ - 1) * DW / 2
        xb = xa + DW / 2
        if cur and abs(cur[1] - xa) < 1e-6:
            cur[1] = xb
        else:
            cur = [xa, xb]
            segs.append(cur)
    for xa, xb in segs:
        psp.add_lwpolyline([(xa, ym - 1.0), (xb, ym - 1.0)], dxfattribs={"layer": "Профиль", "const_width": 0.8})
    lbl(str(q["n"]), (segs[0][0] + 1.6, ym + 0.6), MA.BOTTOM_LEFT)

# технологические связи: (предшествующий, последующий) - вертикальная линия в момент начала последующего
LINKS = [(0, 1), (1, 2), (0, 3), (3, 4), (2, 5), (5, 6), (4, 7)]
for a_, b_ in LINKS:
    d, s_ = KL.SCHED[b_]["shifts"][0]
    x_ = xday(d) + (s_ - 1) * DW / 2
    ya, yb = YROW[a_] - 1.0, YROW[b_] - 1.0
    pp([(x_, ya), (x_, yb + 1.8)], "Перемещения")
    arr((x_, yb), -90, L=1.8, wd=0.9)

# условные обозначения и примечания
txt("Условные обозначения", (26, YB8 - 9), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
yl = YB8 - 15
psp.add_lwpolyline([(26, yl), (40, yl)], dxfattribs={"layer": "Профиль", "const_width": 0.8})
lbl("4", (27, yl + 1.6), MA.BOTTOM_LEFT)
txt("- работа процесса по сменам, над линией - число исполнителей", (43, yl), H_TEXT,
    TA.MIDDLE_LEFT, "Надписи", NARROW)
yl -= 7
for xa in (26, 30.5, 35):
    psp.add_lwpolyline([(xa, yl), (xa + 2.2, yl)], dxfattribs={"layer": "Профиль", "const_width": 0.8})
txt("- работа в одну смену в сутки", (43, yl), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)
yl -= 7
pp([(33, yl + 3), (33, yl - 1.2)], "Перемещения")
arr((33, yl - 3), -90, L=1.8, wd=0.9)
txt("- технологическая связь процессов", (43, yl), H_TEXT, TA.MIDDLE_LEFT, "Надписи", NARROW)
NOTES8 = [
    f"1. Затраты труда и машинного времени - по калькуляции (табл. 12, ЕНиР Е2-1); вспомогательные "
    f"операции включены в основные процессы.",
    f"2. Продолжительность t = Тр / n с округлением до целой смены (Тр - трудоемкость, чел.-дн; n - число "
    f"исполнителей); уровень производительности труда Уп.т = Тр / (n х t) = "
    f"{dec(min(q['upt'] for q in KL.SCHED), 1)}-{dec(max(q['upt'] for q in KL.SCHED), 1)} %.",
    f"3. Работы ведутся в {MS.M_SM} смены по 8 ч; разравнивание и уплотнение грунта насыпи - в 1 смену.",
    f"4. Продолжительность земляных работ - {KL.T_ZEML} дней без устройства подземной части здания.",
]
txt("Примечания", (140, YB8 - 9), H_HEAD, TA.BOTTOM_LEFT, "Надписи", NARROW)
mt(W08 + "\\P".join(NOTES8), (140, YB8 - 12), H_TEXT, 88, MA.TOP_LEFT, "Надписи")

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
