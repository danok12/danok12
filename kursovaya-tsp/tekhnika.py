"""Машины на технологических схемах - из библиотеки чертежей строительной техники
(«Строительная техника», DWG, прислал пользователь 15.10.2026 для корректного изображения машин;
нужные файлы сконвертированы AutoCAD в DXF и лежат в tekhnika/).

Каждый вид машины - блок в метрах: ось X - вперёд по ходу машины (к забою, к отвалу, к кабине),
Y - вверх (вид сбоку) или влево (план); начало - точка привязки вида. Из исходников берутся
только линии, дуги, окружности, полилинии и сплайны (без текста, размеров, осей и штриховки),
в блоке они на слое 0 с цветом и весом «по блоку» - вставка на слое «Машины» задаёт оформление.

Экскаватор ЭО-4121 с обратной лопатой нарисован в библиотеке с ковшом на наибольшей глубине
копания (5,8 м), поэтому его вид разделён на базу (ходовая часть, платформа, кабина) и рабочее
оборудование (стрела, рукоять, ковш с цилиндрами), которое поворачивается вокруг пяты стрелы,
чтобы ковш оказался на нужной отметке; цилиндр подъёма стрелы рисуется заново между шарнирами.
Самосвала КамАЗ-55111, катка и электротрамбовки в библиотеке нет: самосвал - МАЗ той же схемы
(6 x 4, кабина над двигателем) в масштабе по длине КамАЗ-55111; каток и трамбовка рисуются в make_dxf.py.
"""
from math import atan2, cos, sin, hypot, degrees, radians
from pathlib import Path
import ezdxf
from ezdxf import bbox, path
from ezdxf.math import Matrix44

SRC = Path(__file__).resolve().parent / "tekhnika"
KEEP = ("LINE", "ARC", "CIRCLE", "LWPOLYLINE", "SPLINE", "ELLIPSE", "SOLID")

# ---------- ЭО-4121 (EO4121O.DWG): масштаб - по наибольшей глубине копания ----------
EO_AXIS, EO_GROUND = 288.6, 99.22          # ось поворота платформы, уровень стоянки (ед. чертежа)
EO_SC = (EO_GROUND - 40.57) / 5.8          # 10,11 ед. на 1 м: Hк max ЭО-4121А = 5,8 м
EO_DROP = set("F8 108 109 1E6 105 106 107 1E5 101 102 103 104 2DF 217 2DE".split())   # зона копания, грунт
EO_CYL = set("13E 142 146 136 14C".split())                                           # цилиндр подъёма стрелы
EO = lambda x, y: ((EO_AXIS - x) / EO_SC, (y - EO_GROUND) / EO_SC)                     # -> м, вперёд = +X
EXC_PIVOT = EO(283.4, 119.32)              # пята стрелы
EXC_CYL_BASE = EO(279.85, 110.66)          # шарнир цилиндра на платформе
_A = EO(259.87, 111.86)                    # шарнир цилиндра на стреле
EXC_CYL_ROD = (_A[0] - EXC_PIVOT[0], _A[1] - EXC_PIVOT[1])
_T = EO(251.35, 41.96)                     # зубья ковша
EXC_TEETH = (_T[0] - EXC_PIVOT[0], _T[1] - EXC_PIVOT[1])
EXC_FRONT, EXC_REAR = (EO_AXIS - 271.05) / EO_SC, (320.05 - EO_AXIS) / EO_SC   # гусеница / противовес от оси


def _eo_front(e, b):
    """Рабочее оборудование: левее пяты стрелы, кроме переднего колеса гусеницы."""
    c = b.center
    return c.x < 279.5 and not (c.y < 108.5 and c.x > 268)


# ---------- виды: файл, окно (по центрам объектов), отбор, точка привязки, масштаб (м/ед.), вперёд = -x ----------
TRUCK_SC = 7.06 / (1112.578 - 1105.036)    # МАЗ -> длина КамАЗ-55111 7,06 м
DZ_PLAN_Y = 3.64 / 4.43                    # план бульдозера: отвал ДЗ-25 4,43 м -> ДЗ-35С 3,64 м
EK_SC = (306.15 - 271.05) / EO_SC / (366.92 - 361.76)   # план ЕК-270 -> длина гусеницы ЭО-4121
VIEWS = {
    "ЭО-4121А база": ("eo4121o.dxf", (268, 96, 325, 135), lambda e, b: e.dxf.handle not in EO_CYL
                      and e.dxftype() != "LINE" and not _eo_front(e, b), (EO_AXIS, EO_GROUND), 1 / EO_SC, True),
    "ЭО-4121А оборудование": ("eo4121o.dxf", (230, 34, 285, 125), lambda e, b: e.dxf.handle not in EO_CYL
                              and e.dxftype() != "LINE" and _eo_front(e, b), (283.4, 119.32), 1 / EO_SC, True),
    "ЭО-4121А план": ("ekskavatory.dxf", (360.4, 105.0, 371.8, 109.9), None, (364.31, 107.02), EK_SC, False),
    "Бульдозер сбоку": ("buldozery.dxf", (203.5, 67.2, 211.95, 72.0), None, (204.228, 68.405), 1.0, True),
    "Бульдозер план": ("buldozery.dxf", (203.5, 62.0, 211.95, 66.8), None, (204.228, 64.264),
                       (1.0, DZ_PLAN_Y), True),
    "Самосвал сбоку": ("avto_gruz.dxf", (1104.9, -95.8, 1112.6, -91.6), None, (1105.036, -95.393), TRUCK_SC, True),
    "Самосвал разгрузка": ("avto_gruz.dxf", (1120.4, -95.8, 1129.2, -87.6), None, (1120.592, -95.393),
                           TRUCK_SC, True),
    "Самосвал спереди": ("avto_gruz.dxf", (1114.8, -95.8, 1117.9, -91.9), None, (1116.667, -95.601),
                         TRUCK_SC, False),
    "Самосвал план": ("avto_gruz.dxf", (1104.9, -91.2, 1112.6, -88.1), None, (1105.036, -89.771), TRUCK_SC, True),
}
TRUCK_L = 7.06                             # длина самосвала, м (у вида сбоку начало - передний бампер)


def make_blocks(doc):
    """Определить блоки всех видов в doc; вернуть габариты {имя: (xmin, ymin, xmax, ymax)} в м."""
    cache, sizes = {}, {}
    for name, (fn, (x0, y0, x1, y1), pick, (ox, oy), sc, mirror) in VIEWS.items():
        if fn not in cache:
            cache[fn] = ezdxf.readfile(SRC / fn)
        src = cache[fn].modelspace()
        sx, sy = sc if isinstance(sc, tuple) else (sc, sc)
        m = Matrix44.translate(-ox, -oy, 0) @ Matrix44.scale(-sx if mirror else sx, sy, 1)
        blk = doc.blocks.new(name)
        for e in src:
            if e.dxftype() not in KEEP or (fn == "eo4121o.dxf" and e.dxf.handle in EO_DROP):
                continue
            b = bbox.extents([e], fast=True)
            if not b.has_data or not (x0 <= b.center.x <= x1 and y0 <= b.center.y <= y1):
                continue
            if pick and not pick(e, b):
                continue
            if sx != sy:                     # неравномерный масштаб: дуги и сплайны -> полилинии
                for pl_ in path.render_lwpolylines(blk, [path.make_path(e).transform(m)], distance=0.005):
                    pl_.dxf.layer, pl_.dxf.color, pl_.dxf.linetype, pl_.dxf.lineweight = "0", 0, "BYBLOCK", -2
                continue
            ne = e.copy()
            blk.add_foreign_entity(ne, copy=False)
            ne.dxf.layer, ne.dxf.color, ne.dxf.linetype, ne.dxf.lineweight = "0", 0, "BYBLOCK", -2
            if ne.dxftype() == "LWPOLYLINE":
                ne.dxf.const_width = 0
                pts = ne.get_points("xyseb")
                ne.set_points([(x, y, 0, 0, bl) for x, y, s_, e_, bl in pts], format="xyseb")
            ne.transform(m)
        ext = bbox.extents(blk, fast=True)
        sizes[name] = (ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y)
    return sizes


def exc_angle(v_teeth):
    """Поворот рабочего оборудования (рад, против часовой - вверх), чтобы зубья ковша были на
    отметке v_teeth (м от уровня стоянки) впереди машины; вылет при этом - постоянный."""
    tx, ty = EXC_TEETH
    L = hypot(tx, ty)
    dy = v_teeth - EXC_PIVOT[1]
    dx = (L * L - dy * dy) ** 0.5
    return atan2(dy, dx) - atan2(ty, tx)


def rot(p, a):
    return (p[0] * cos(a) - p[1] * sin(a), p[0] * sin(a) + p[1] * cos(a))


def exc_teeth(a):
    """Зубья ковша (м от оси на уровне стоянки) при повороте оборудования на a."""
    t = rot(EXC_TEETH, a)
    return (EXC_PIVOT[0] + t[0], EXC_PIVOT[1] + t[1])


if __name__ == "__main__":
    d = ezdxf.new("R2010")
    for k, v in make_blocks(d).items():
        print(f"{k:<24} {v[2] - v[0]:6.2f} x {v[3] - v[1]:5.2f} м  ({', '.join(f'{c:.2f}' for c in v)})")
    a = exc_angle(-2.0)
    print("ЭО-4121А: пята", [round(c, 2) for c in EXC_PIVOT], "вылет зубьев", round(hypot(*EXC_TEETH), 2),
          "м; ковш на -2,0 м: поворот", round(degrees(a), 1), "°, зубья", [round(c, 2) for c in exc_teeth(a)])
