# -*- coding: utf-8 -*-
"""Оформление планов и схем по образцу преподавателя (IronPython, pyRevit): марки диаметров труб «В1-Ø25»,
марки ввода и выпусков, выноски «Водомерный узел» / «Насосная установка», высотные отметки на схемах,
размерные цепочки по осям, «R» и «Пр.» у ревизий и прочисток.

Всё, что ставится здесь, удаляется и ставится заново при повторном запуске (по типам марок / текста и по видам).
"""
import math
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
from System.Collections.Generic import List
import kvv

M = kvv.M
MM = kvv.MM

MARKA_TRUBY = (u'ADSK_M_Трубы_Сокращение для системы', u'Сокращение_Диаметр_13')
MARKA_VVOD = (u'ADSK_M_Трубы_Сокращение для системы', u'Ввод_Сокращение_Номер ввода_Диаметр')
MARKA_VYPUSK = (u'ADSK_M_Трубы_Сокращение для системы', u'Выпуск_Сокращение_Номер выпуска_Диаметр')
TEKST_VYNOSKI = u'КВВ_Выноска_2.5'
OTMETKA = [u'ADSK_Схема_Проектная_Отметка сверху_Вверх', u'ADSK_Схема_Абсолютная_Отметка сверху_Вверх']
NASOS = u'Насосная установка'


def metka(e):
    try:
        p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    except Exception:
        return u''
    return (p.AsString() or u'') if p is not None and p.HasValue else u''


def tip_marki(doc, fam, tip, kat=DB.BuiltInCategory.OST_PipeTags):
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(kat):
        if s.FamilyName == fam and DB.Element.Name.GetValue(s) == tip:
            if not s.IsActive:
                s.Activate()
            return s
    return None


def tip_teksta(doc, log):
    t = kvv.po_imeni(doc, DB.TextNoteType, TEKST_VYNOSKI)
    if t is not None:
        return t
    baza = kvv.po_imeni(doc, DB.TextNoteType, u'ADSK_Основной текст_2.5')
    if baza is None:
        baza = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType).FirstElement()
    t = baza.Duplicate(TEKST_VYNOSKI)
    t.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(2.5 * MM)
    t.get_Parameter(DB.BuiltInParameter.TEXT_BACKGROUND).Set(1)        # 1 — прозрачный
    log(u'создан тип текста', TEKST_VYNOSKI)
    return t


def ochistit(doc, vidy, tipy_marok, log):
    """Свои марки (по типам), выноски (по типу текста), отметки и размеры на своих видах — удалить."""
    tipy = set(s.Id.IntegerValue for s in tipy_marok if s is not None)
    tt = kvv.po_imeni(doc, DB.TextNoteType, TEKST_VYNOSKI)
    ud = set()
    for m in DB.FilteredElementCollector(doc).OfClass(DB.IndependentTag):
        if m.GetTypeId().IntegerValue in tipy:
            ud.add(m.Id.IntegerValue)
    if tt is not None:
        for tn in DB.FilteredElementCollector(doc).OfClass(DB.TextNote):
            if tn.GetTypeId() == tt.Id:
                ud.add(tn.Id.IntegerValue)
    for v in vidy:
        for e in DB.FilteredElementCollector(doc, v.Id).OfClass(DB.Dimension):
            if e.OwnerViewId == v.Id:
                ud.add(e.Id.IntegerValue)
        for e in DB.FilteredElementCollector(doc, v.Id).OfCategory(DB.BuiltInCategory.OST_SpotElevations)                 .WhereElementIsNotElementType():
            if e.OwnerViewId == v.Id:
                ud.add(e.Id.IntegerValue)
    ud = [DB.ElementId(i) for i in ud]
    if ud:
        doc.Delete(List[DB.ElementId](ud))
    log(u'удалено прежних марок, выносок, отметок и размеров:', len(ud))


class Zanyato(object):
    """Занятые места на виде (прямоугольники в координатах модели, план XY) — чтобы марки не налезали."""

    def __init__(self):
        self.pr = []

    def dobavit(self, x, y, hw, hh):
        self.pr.append((x - hw, y - hh, x + hw, y + hh))

    def svobodno(self, x, y, hw, hh):
        for (a, b, c, d) in self.pr:
            if x + hw > a and x - hw < c and y + hh > b and y - hh < d:
                return False
        return True


def truby_sistemy(doc, pref):
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        if metka(t).startswith(pref):
            yield t


def koncy(t):
    c = t.Location.Curve
    return c.GetEndPoint(0), c.GetEndPoint(1)


def marki_diametrov(doc, v, sist, sym, zan, log):
    """Марки «В1-Ø..» / «К1-Ø..» на горизонтальных участках плана: каждый диаметр — не чаще одного раза на
    участке радиусом 3 м (на этаже — примерно раз на квартиру), длинные участки — первыми."""
    k = v.Scale / 100.0
    zl = v.GenLevel.Elevation
    podval = zl < -1e-6
    if podval:
        z0, z1 = zl, 0.0
    else:
        z0, z1 = zl - 0.45 * M, zl + 3.0 * M
    pref = u'КВВ-' + sist
    lmin = (1.0 if podval else 0.25) * M
    kand = []
    for t in truby_sistemy(doc, pref):
        a, b = koncy(t)
        L = math.hypot(b.X - a.X, b.Y - a.Y)
        if L < lmin or abs(b.Z - a.Z) > 0.1 * L:
            continue
        if min(a.Z, b.Z) < z0 - 0.01 or max(a.Z, b.Z) > z1:
            continue
        kand.append((L, t, a, b))
    kand.sort(key=lambda q: -q[0])
    radius = (6.0 if podval else 2.2) * M
    bylo = []
    n = 0
    for L, t, a, b in kand:
        d = int(round(t.Diameter / MM))
        mx, my, mz = (a.X + b.X) / 2, (a.Y + b.Y) / 2, (a.Z + b.Z) / 2
        if any(dd == d and math.hypot(x - mx, y - my) < radius for x, y, dd in bylo):
            continue
        ux, uy = (b.X - a.X) / L, (b.Y - a.Y) / L
        gor = abs(ux) >= abs(uy)
        nx, ny = (0.0, 1.0) if gor else (-1.0, 0.0)
        hw, hh = (0.5 * k * M, 0.15 * k * M) if gor else (0.15 * k * M, 0.5 * k * M)     # «В1-Ø15» ≈ 10 x 3 мм
        mesto = None
        for s_ in (1, -1):
            off = 0.45 * k * M
            x, y = mx + s_ * nx * off, my + s_ * ny * off
            if zan.svobodno(x, y, hw, hh):
                mesto = (x, y)
                break
        if mesto is None:
            continue
        gol = DB.XYZ(mesto[0], mesto[1], mz)
        try:
            m = DB.IndependentTag.Create(doc, sym.Id, v.Id, DB.Reference(t), False,
                                         DB.TagOrientation.Horizontal if gor else DB.TagOrientation.Vertical, gol)
            m.TagHeadPosition = gol
        except Exception as ex:
            log(u'  марка диаметра не встала:', v.Name, d, ex)
            continue
        zan.dobavit(mesto[0], mesto[1], hw, hh)
        bylo.append((mx, my, d))
        n += 1
    log(u'  марок диаметров на', v.Name, n, u'(кандидатов', len(kand), u')')


def ustanovit_nomer(t, slovo, nomer, log):
    """Номер ввода/выпуска — в параметр трубы, имя которого содержит «номер ввода» / «номер выпуска»."""
    for p in t.Parameters:
        nm = p.Definition.Name.lower()
        if u'номер' in nm and slovo in nm and not p.IsReadOnly:
            if p.StorageType == DB.StorageType.String:
                p.Set(unicode(nomer))
            elif p.StorageType == DB.StorageType.Integer:
                p.Set(int(nomer))
            else:
                continue
            return p.Definition.Name
    # в шаблоне ADSK марки ввода/выпуска берут номер из того же параметра, что и марки стояков
    p = t.LookupParameter(u'ADSK_Номер стояка')
    if p is not None and not p.IsReadOnly:
        p.Set(unicode(nomer))
        return u'ADSK_Номер стояка'
    return None


def vvody_vypuski(doc, g, log):
    """Ввод В1 — труба, выходящая за наружную стену по оси А; выпуски К1 — за стену по оси Д (по возрастанию x)."""
    B, E = 12.8, 0.06
    vv, vyp = [], []
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        s_ = metka(t)
        a, b = koncy(t)
        if s_.startswith(u'КВВ-В1') and min(a.Y, b.Y) < (-E - 0.6) * M:
            vv.append(t)
        elif s_.startswith(u'КВВ-К1') and max(a.Y, b.Y) > (B + E + 0.6) * M:
            vyp.append(t)
    vyp.sort(key=lambda t: koncy(t)[0].X)
    if vv:
        imena = sorted(p.Definition.Name for p in vv[0].Parameters
                       if u'омер' in p.Definition.Name or u'вод' in p.Definition.Name.lower()
                       or u'ыпуск' in p.Definition.Name)
        log(u'параметры трубы ввода (номер/ввод/выпуск):', u'; '.join(imena))
    for i, t in enumerate(vv):
        nm = ustanovit_nomer(t, u'ввод', i + 1, log)
        log(u'ввод', i + 1, u'| параметр номера:', nm or u'НЕ НАЙДЕН')
    for i, t in enumerate(vyp):
        nm = ustanovit_nomer(t, u'выпуск', i + 1, log)
        log(u'выпуск', i + 1, u'| параметр номера:', nm or u'НЕ НАЙДЕН')
    return vv, vyp


def napravleniya(v):
    """Экранные «вправо» и «вверх» вида в координатах модели (для плана — X и Y)."""
    if isinstance(v, DB.View3D):
        return v.RightDirection, v.UpDirection
    return DB.XYZ.BasisX, DB.XYZ.BasisY


def marka_s_vynoskoy(doc, v, sym, t, tochka, dx, dy, log, zan=None):
    """Марка трубы с выноской: полка смещена на (dx, dy) в долях масштаба (листовые 10 мм = dx 1.0 при 1:100)."""
    k = v.Scale / 100.0
    r, u = napravleniya(v)
    gol = tochka + r.Multiply(dx * k * M) + u.Multiply(dy * k * M)
    try:
        m = DB.IndependentTag.Create(doc, sym.Id, v.Id, DB.Reference(t), True, DB.TagOrientation.Horizontal, gol)
        m.TagHeadPosition = gol
        if zan is not None and not isinstance(v, DB.View3D):
            zan.dobavit(gol.X, gol.Y, 1.8 * k * M, 0.35 * k * M)
        return m
    except Exception as ex:
        log(u'  марка с выноской не встала:', v.Name, ex)
        return None


def vynoska(doc, v, tnt, tekst, tochka, dx, dy, log, zan=None, gol=None):
    """Текст с выноской (TextNote + полка-выноска) — «Водомерный узел» и т. п. Место текста — смещение (dx, dy)
    в долях масштаба от точки или явно (gol)."""
    k = v.Scale / 100.0
    r, u = napravleniya(v)
    if gol is None:
        gol = tochka + r.Multiply(dx * k * M) + u.Multiply(dy * k * M)
    opt = DB.TextNoteOptions(tnt.Id)
    opt.HorizontalAlignment = DB.HorizontalTextAlignment.Left if dx >= 0 else DB.HorizontalTextAlignment.Right
    try:
        tn = DB.TextNote.Create(doc, v.Id, gol, tekst, opt)
        ld = tn.AddLeader(DB.TextNoteLeaderTypes.TNLT_STRAIGHT_L if dx >= 0 else DB.TextNoteLeaderTypes.TNLT_STRAIGHT_R)
        ld.End = tochka
        if zan is not None and not isinstance(v, DB.View3D):
            n_str = tekst.count(u'\r') + 1
            dl = max(len(s_) for s_ in tekst.split(u'\r'))
            hw = dl * 0.9 * k * M * 0.25
            zan.dobavit(gol.X + (hw if dx >= 0 else -hw), gol.Y - 0.2 * n_str * k * M, hw, 0.25 * n_str * k * M)
        return tn
    except Exception as ex:
        log(u'  выноска не встала:', v.Name, tekst, ex)
        return None


def tip_otmetki(doc, log):
    tipy = dict((DB.Element.Name.GetValue(t), t) for t in DB.FilteredElementCollector(doc).OfClass(DB.SpotDimensionType))
    for nm in OTMETKA:
        if nm in tipy:
            return tipy[nm]
    log(u'нет типа отметки', OTMETKA[0], u'| есть:', u', '.join(sorted(tipy.keys())[:12]))
    return None


def ssylki(t, v, tochno=False):
    """Ссылки геометрии трубы на виде: ось (линия) и грани; tochno — геометрия «Высокой» детализации без вида
    (на схеме в «Низкой» у трубы нет граней, а отметке лотка нужна нижняя образующая)."""
    opt = DB.Options()
    opt.ComputeReferences = True
    opt.IncludeNonVisibleObjects = True
    if tochno:
        opt.DetailLevel = DB.ViewDetailLevel.Fine
    else:
        opt.View = v
    linii, grani = [], []

    def obhod(geo):
        for go in geo:
            if isinstance(go, DB.Line) and go.Reference is not None:
                linii.append(go)
            elif isinstance(go, DB.Solid):
                for f in go.Faces:
                    if f.Reference is not None:
                        grani.append(f)
            elif isinstance(go, DB.GeometryInstance):
                obhod(go.GetInstanceGeometry())
    obhod(t.get_Geometry(opt))
    return linii, grani


def tip_otmetki_lotka(doc, baza, log):
    """Копия типа отметки с показом отметки низа (лотка) трубы."""
    if baza is None:
        return None
    nm = u'КВВ_Отметка лотка'
    for t in DB.FilteredElementCollector(doc).OfClass(DB.SpotDimensionType):
        if DB.Element.Name.GetValue(t) == nm:
            return t
    t = baza.Duplicate(nm)
    p = t.get_Parameter(DB.BuiltInParameter.SPOT_ELEV_DISPLAY_ELEVATIONS)
    if p is None:
        log(u'у типа отметки нет параметра «Отображать отметки»')
        return t
    znach = []
    for i in range(5):
        try:
            p.Set(i)
            znach.append((i, p.AsValueString() or u''))
        except Exception:
            pass
    niz = [i for i, s_ in znach if s_.startswith(u'Низ') or s_.startswith(u'Bottom') or u'низ' in s_.lower()]
    if niz:
        p.Set(niz[0])
    log(u'тип отметки лотка: варианты', znach, u'->', niz[:1])
    return t


class Otmetki(object):
    """Высотные отметки (SpotElevation) на трубах в аксонометрии / на плане."""

    def __init__(self, doc, v, tip, log):
        self.doc, self.v, self.tip, self.log = doc, v, tip, log
        self.n, self.oshibki, self.sposob = 0, 0, {}
        self.tnt, self.posl, self.tip_lotka = None, None, None

    def podpis(self, sd, tekst):
        """Подпись под полкой отметки («2 этаж»): сначала свойством Below, иначе текстом под полкой."""
        try:
            sd.Below = tekst
            self.sposob[u'below'] = self.sposob.get(u'below', 0) + 1
            return
        except Exception as ex:
            if u'below_err' not in self.sposob:
                self.sposob[u'below_err'] = unicode(ex)[:60]
        if self.tnt is None or self.posl is None:
            return
        bend, end = self.posl
        v = self.v
        k = v.Scale / 100.0
        r, u = napravleniya(v)
        x0 = bend if (end - bend).DotProduct(r) > 0 else end
        opt = DB.TextNoteOptions(self.tnt.Id)
        opt.HorizontalAlignment = DB.HorizontalTextAlignment.Left
        try:
            DB.TextNote.Create(self.doc, v.Id, x0 - u.Multiply(0.12 * k * M), tekst, opt)
        except Exception as ex:
            self.log(u'  подпись этажа не встала:', ex)

    def postavit(self, t, p, dx, dy, lotok=False):
        """Отметка на трубе t в точке p (на оси); полка смещена на (dx, dy) в долях масштаба.
        lotok — отметка лотка (низ трубы), иначе — оси."""
        v = self.v
        k = v.Scale / 100.0
        r, u = napravleniya(v)
        linii, grani = ssylki(t, v)
        cel = p
        if lotok:
            _, grani = ssylki(t, v, tochno=True)
            cel = p - DB.XYZ(0, 0, t.get_Parameter(DB.BuiltInParameter.RBS_PIPE_OUTER_DIAMETER).AsDouble() / 2.0)
        bend = cel + r.Multiply(dx * 0.5 * k * M) + u.Multiply(dy * k * M)
        end = bend + r.Multiply(dx * 0.5 * k * M)
        varianty = []
        if lotok:                            # сначала низ трубы (лоток), при неудаче — ось
            for f in grani:
                pr = f.Project(cel)
                if pr is not None and pr.Distance < 0.01 * M:
                    varianty.append((u'лоток', f.Reference, pr.XYZPoint))
        for ln in linii:
            varianty.append((u'ось', ln.Reference, ln.Project(p).XYZPoint if ln.Project(p) else p))
        for f in ([] if lotok else grani):
            pr = f.Project(cel)
            if pr is not None and pr.Distance < 0.02 * M:
                varianty.append((u'грань', f.Reference, pr.XYZPoint))
        for sp, ref, rp in varianty:
            try:
                sd = self.doc.Create.NewSpotElevation(v, ref, rp, bend, end, rp, True)
                if sd is None:
                    continue
                tip = self.tip_lotka if (lotok and self.tip_lotka is not None) else self.tip
                if tip is not None:
                    sd.ChangeTypeId(tip.Id)
                self.posl = (bend, end)
                self.n += 1
                self.sposob[sp] = self.sposob.get(sp, 0) + 1
                return sd
            except Exception as ex:
                err = ex
        self.oshibki += 1
        if self.oshibki <= 3:
            self.log(u'  отметка не встала:', v.Name, u'(%.2f, %.2f, %.2f)' % (p.X / M, p.Y / M, p.Z / M),
                     u'вариантов', len(varianty), err if varianty else u'')
        return None


def truba_v_tochke(doc, pref, p, dop=0.02, gor=None):
    """Труба системы, ось которой проходит через точку p (м, абс.)."""
    P = DB.XYZ(p[0] * M, p[1] * M, p[2] * M)
    for t in truby_sistemy(doc, pref):
        c = t.Location.Curve
        a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        if gor is not None:
            g_ = abs(b.Z - a.Z) < 0.2 * a.DistanceTo(b)
            if g_ != gor:
                continue
        pr = c.Project(P)
        if pr is not None and pr.Distance < dop * M:
            return t, pr.XYZPoint
    return None, None


def razmery_osey(doc, v, log):
    """Размерные цепочки по осям под планом и слева от него (как в образце): цепочка между соседними осями и
    общий размер между крайними."""
    osi = list(DB.FilteredElementCollector(doc).OfClass(DB.Grid))
    ver = sorted([gr for gr in osi if abs(gr.Curve.Direction.Y) > 0.9], key=lambda gr: gr.Curve.GetEndPoint(0).X)
    gor = sorted([gr for gr in osi if abs(gr.Curve.Direction.X) > 0.9], key=lambda gr: gr.Curve.GetEndPoint(0).Y)
    zl = v.GenLevel.Elevation
    n = 0
    for spisok, vdol_x in ((ver, True), (gor, False)):
        if len(spisok) < 2:
            continue
        # между наружной стеной (грань -0,32 м) и концами осей (-2,5 м): цепочка и общий размер
        for otstup, obsh in ((1.0, False), (2.1, True)):
            ra = DB.ReferenceArray()
            for gr in ([spisok[0], spisok[-1]] if obsh else spisok):
                ra.Append(DB.Reference(gr))
            if vdol_x:
                ln = DB.Line.CreateBound(DB.XYZ(0, -otstup * M, zl), DB.XYZ(1 * M, -otstup * M, zl))
            else:
                ln = DB.Line.CreateBound(DB.XYZ(-otstup * M, 0, zl), DB.XYZ(-otstup * M, 1 * M, zl))
            try:
                doc.Create.NewDimension(v, ln, ra)
                n += 1
            except Exception as ex:
                log(u'  размер не встал:', v.Name, ex)
    log(u'  размерных цепочек на', v.Name, n)


def tochka_na_y(t, y):
    """Точка оси трубы с координатой y (м) — для выпуска у наружной стены."""
    a, b = koncy(t)
    if abs(b.Y - a.Y) < 1e-9:
        return a
    s_ = (y * M - a.Y) / (b.Y - a.Y)
    s_ = max(0.0, min(1.0, s_))
    return a + (b - a).Multiply(s_)


def otmetki_stoyakov(doc, g, ot, sist, log):
    """Отметки на крайних стояках системы (у торцов здания — полки наружу): отметки этажей на стояке и отметки
    поэтажных ответвлений (В1) / верх вытяжной части (К1)."""
    pref = u'КВВ-' + (u'В1' if sist == u'V1' else u'К1')
    urovni = [(u_['imya'], u_['z']) for u_ in g['urovni'] if u_['imya'].startswith(u'Этаж')]
    xs = [s_['x'] for s_ in g['stoyaki'] if s_['sys'] == sist]
    x_min, x_max = min(xs), max(xs)
    for s_ in g['stoyaki']:
        if s_['sys'] != sist or s_['x'] not in (x_min, x_max):
            continue
        storona = -1.0 if s_['x'] == x_min else 1.0
        x, y = s_['x'], s_['y']
        # отметки этажей: на оси стояка на уровне чистого пола — полка в сторону от здания
        for imya, z in urovni:
            t, p = truba_v_tochke(doc, pref, (x, y, z), gor=False)
            if t is None:
                continue
            sd = ot.postavit(t, p, storona * 1.2, 0.35)
            if sd is not None:
                ot.podpis(sd, u'%d этаж' % int(imya.split()[-1]))
        if sist == u'V1':
            # ответвления к квартирам: горизонтальная труба от тройника стояка
            for rid in s_['runs']:
                z = g['seti'][rid]['pts'][-1][2]
                luchshaya = None
                for t in truby_sistemy(doc, pref):
                    a, b = koncy(t)
                    if abs(a.Z - b.Z) > 1e-3 or abs(a.Z - z * M) > 0.01 * M:
                        continue
                    for q in (a, b):
                        d = math.hypot(q.X - x * M, q.Y - y * M)
                        if d < 0.4 * M and (luchshaya is None or d < luchshaya[0]):
                            luchshaya = (d, t, q)
                if luchshaya is not None:
                    ot.postavit(luchshaya[1], luchshaya[2], -storona * 1.2, 0.35)
        else:
            verh = s_['verh']
            t, p = truba_v_tochke(doc, pref, (x, y, verh - 0.02), gor=False)
            if t is not None:
                ot.postavit(t, DB.XYZ(x * M, y * M, verh * M), storona * 1.6, 0.35)


def oformit_plan(doc, g, v, sist, tipy, tnt, zan, vvody, vypuski, tr, log):
    """План: размеры по осям, марки ввода/выпусков и выноски (подвал), марки диаметров."""
    podval = v.GenLevel.Elevation < -1e-6
    razmery_osey(doc, v, log)
    zan.dobavit(23.0 * M, -1.45 * M, 23.5 * M, 0.55 * M)          # размерные цепочки снизу
    zan.dobavit(-1.45 * M, 6.4 * M, 0.55 * M, 6.8 * M)            # и слева
    if podval and sist == u'В1':
        for t in vvody:
            a, b = koncy(t)
            nar = a if a.Y < b.Y else b
            m = marka_s_vynoskoy(doc, v, tipy['vvod'], t, DB.XYZ(nar.X, -1.0 * M, nar.Z), 0, 0, log)
            if m is not None:
                # полка марки ввода — ниже концов осей, между выносками
                m.TagHeadPosition = DB.XYZ(nar.X + 0.4 * M, -5.0 * M, nar.Z)
        x_tr = tr.get('x_troynik', 4.0)
        vynoska(doc, v, tnt, u'Водомерный узел', DB.XYZ(x_tr * M, 2.6 * M, -2.0 * M), 0, 0, log,
                gol=DB.XYZ(-3.6 * M, -4.75 * M, 0))
        for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_MechanicalEquipment) \
                .WhereElementIsNotElementType():
            if metka(e).startswith(u'КВВ-О'):
                vynoska(doc, v, tnt, NASOS + u'\r' + u'Wilo ' + DB.Element.Name.GetValue(e.Symbol),
                        e.Location.Point, 0, 0, log, gol=DB.XYZ(8.6 * M, -4.75 * M, 0))
        krany_podpisi(doc, v, tnt, g, tr, None, log)
    if podval and sist == u'К1':
        prochistki_revizii_podpisi(doc, v, tnt, tr, True, log)
        for t in vypuski:
            p = tochka_na_y(t, 13.12 + 0.6)
            marka_s_vynoskoy(doc, v, tipy['vypusk'], t, p, 1.2 if p.X < 23 * M else -1.2, 0.9, log, zan)
    marki_diametrov(doc, v, sist, tipy['truba'], zan, log)


def oformit_shemu(doc, g, v, sist, tipy, tnt, tip_ot, vvody, vypuski, tr, log):
    """Аксонометрическая схема: отметки, марки ввода/выпусков, выноски."""
    ot = Otmetki(doc, v, tip_ot, log)
    ot.tnt = tnt
    if sist == u'К1':
        ot.tip_lotka = tip_otmetki_lotka(doc, tip_ot, log)
    otmetki_stoyakov(doc, g, ot, u'V1' if sist == u'В1' else u'K1', log)
    if sist == u'В1':
        x_tr, y_mag, z_mag = tr.get('x_troynik', 4.0), tr.get('y_mag', 7.2), tr.get('z_mag', -0.6)
        for x in (x_tr + 1.5, tr.get('zerkalo', 45.45) - x_tr - 1.5):
            t, p = truba_v_tochke(doc, u'КВВ-В1', (x, y_mag, z_mag), gor=True)
            if t is not None:
                ot.postavit(t, p, 1.2, 0.5)
        for t in vvody:
            a, b = koncy(t)
            nar, vn = (a, b) if a.Y < b.Y else (b, a)
            p = nar + (vn - nar).Normalize().Multiply(0.4 * M)
            ot.postavit(t, p, -1.2, 0.5)
            marka_s_vynoskoy(doc, v, tipy['vvod'], t, p, -2.4, -1.4, log)
        vynoska(doc, v, tnt, u'Водомерный узел', DB.XYZ(x_tr * M, 2.6 * M, -2.0 * M), 2.5, -0.9, log)      # вправо-вниз: там свободно (левее — край вида)
        for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_MechanicalEquipment) \
                .WhereElementIsNotElementType():
            if metka(e).startswith(u'КВВ-О'):
                vynoska(doc, v, tnt, NASOS + u'\r' + u'Wilo ' + DB.Element.Name.GetValue(e.Symbol),
                        e.Location.Point, 2.5, 0.6, log)
        krany_podpisi(doc, v, tnt, g, tr, ot, log)
    else:
        prochistki_revizii_podpisi(doc, v, tnt, tr, False, log)
        for t in vypuski:
            p = tochka_na_y(t, 13.12)
            ot.postavit(t, p, 1.2, 0.5, lotok=True)
            marka_s_vynoskoy(doc, v, tipy['vypusk'], t, tochka_na_y(t, 13.12 + 0.6), 1.6, -1.2, log)
    log(u'  отметок на', v.Name, ot.n, u'| способ:', ot.sposob, u'| не встало', ot.oshibki)


def oformit_vse(doc, g, tr, plany, shemy, tip_marki_stoyaka, log):
    """Всё оформление планов и схем. plany / shemy — {имя вида: вид}."""
    tipy = {'truba': tip_marki(doc, *MARKA_TRUBY), 'vvod': tip_marki(doc, *MARKA_VVOD),
            'vypusk': tip_marki(doc, *MARKA_VYPUSK)}
    for k_, s_ in tipy.items():
        if s_ is None:
            log(u'НЕТ типа марки', k_)
            return
    tnt = tip_teksta(doc, log)
    tip_ot = tip_otmetki(doc, log)
    vidy = [v for v in list(plany.values()) + list(shemy.values()) if v is not None]
    ochistit(doc, vidy, list(tipy.values()), log)
    doc.Regenerate()
    vvody, vypuski = vvody_vypuski(doc, g, log)
    for nm, v in sorted(plany.items()):
        if v is None:
            continue
        zan = Zanyato()
        k = v.Scale / 100.0
        for m in DB.FilteredElementCollector(doc, v.Id).OfClass(DB.IndependentTag):
            if tip_marki_stoyaka is not None and m.GetTypeId() == tip_marki_stoyaka.Id:
                p = m.TagHeadPosition
                zan.dobavit(p.X, p.Y, 1.8 * k * M, 0.45 * k * M)
        for m in DB.FilteredElementCollector(doc, v.Id).OfCategory(DB.BuiltInCategory.OST_RoomTags) \
                .WhereElementIsNotElementType():
            try:
                p = m.TagHeadPosition
            except Exception:
                p = m.Location.Point
            zan.dobavit(p.X, p.Y, 0.4 * k * M, 0.12 * k * M)
        sist = u'В1' if nm.startswith(u'В1') else u'К1'
        try:
            oformit_plan(doc, g, v, sist, tipy, tnt, zan, vvody, vypuski, tr, log)
        except Exception:
            import traceback
            log(u'  ОШИБКА оформления плана', nm, traceback.format_exc())
    for nm, v in sorted(shemy.items()):
        if v is None:
            continue
        sist = u'В1' if nm.startswith(u'В1') else u'К1'
        try:
            oformit_shemu(doc, g, v, sist, tipy, tnt, tip_ot, vvody, vypuski, tr, log)
        except Exception:
            import traceback
            log(u'  ОШИБКА оформления схемы', nm, traceback.format_exc())


KRAN_POL = u'Кран водоразборный\rсо штуцером 1"'


def elementy_s_metkoy(doc, kat, tochno):
    return [e for e in DB.FilteredElementCollector(doc).OfCategory(kat).WhereElementIsNotElementType()
            if metka(e) == tochno]


def tochka_elementa(e):
    loc = e.Location
    if isinstance(loc, DB.LocationPoint):
        return loc.Point
    bb = e.get_BoundingBox(None)
    return (bb.Min + bb.Max).Multiply(0.5)


def storona_stoyaka(x, zerk):
    """В сторону от соседнего стояка: кв. А и Б — к торцу (влево в секции 1), кв. В — вправо; секция 2 зеркально."""
    sek2 = x > zerk / 2
    xl = zerk - x if sek2 else x
    s_ = -1 if xl < 15.7 else 1
    return -s_ if sek2 else s_


def prochistki_revizii_podpisi(doc, v, tnt, tr, plan, log):
    """«Пр.» у заглушек-прочисток (план подвала К1 и схема К1), «R» у ревизий (схема К1)."""
    zerk = tr.get('zerkalo', 45.45)
    n = 0
    for e in elementy_s_metkoy(doc, DB.BuiltInCategory.OST_PipeFitting, u'КВВ-К1-Пр'):
        p = tochka_elementa(e)
        s_ = storona_stoyaka(p.X / M, zerk)
        if vynoska(doc, v, tnt, u'Пр.', p, 1.0 * s_, -0.8, log) is not None:
            n += 1
    if not plan:
        for e in elementy_s_metkoy(doc, DB.BuiltInCategory.OST_PipeFitting, u'КВВ-К1-R'):
            p = tochka_elementa(e)
            s_ = storona_stoyaka(p.X / M, zerk)
            if p.X / M < 1.0 or p.X / M > zerk - 1.0:
                s_ = -s_                     # у крайних стояков снаружи — отметки этажей
            if vynoska(doc, v, tnt, u'R', p, 0.8 * s_, 0.35, log) is not None:
                n += 1
    log(u'  подписей «Пр.» и «R» на', v.Name, n)


def g_dn_pol(g):
    """Диаметр подводки к поливочному крану (из трассы: труба, кончающаяся у крана)."""
    k_ = g.get('krany_pol', [])
    if not k_:
        return 25
    for r in g['seti']:
        q = r['pts'][-1]
        if abs(q[0] - k_[0]['x']) < 0.01 and abs(q[1] - k_[0]['y']) < 0.01 and abs(q[2] - k_[0]['z']) < 0.01:
            return r['d']
    return 25


def krany_podpisi(doc, v, tnt, g, tr, ot, log):
    """«Кран водоразборный со штуцером 1"» у поливочных кранов: на плане подвала В1 — выноской над планом,
    на схеме — выноской и отметкой +0.500."""
    zerk = tr.get('zerkalo', 45.45)
    for k_ in g.get('krany_pol', []):
        p = DB.XYZ(k_['x'] * M, k_['y'] * M, k_['z'] * M)
        lev = k_['x'] < zerk / 2
        if ot is None:
            # план подвала (как у преподавателя): «Подъем В1 Ø25» — у подъёма у внутренней грани торцевой стены,
            # «Кран водоразборный…» — к наружной грани стены, где кран выходит на фасад
            s_ = 1.0 if lev else -1.0
            x_pod = 0.25 if lev else zerk - 0.25
            p_pod = DB.XYZ(x_pod * M, k_['y'] * M, -0.6 * M)
            vynoska(doc, v, tnt, u'Подъем В1\rØ%d' % g_dn_pol(g), p_pod, s_, 0, log,
                    gol=DB.XYZ((x_pod + s_ * 0.35) * M, (k_['y'] + 2.5) * M, 0))
            vynoska(doc, v, tnt, KRAN_POL.replace(u'\r', u' '), p, s_, 0, log,
                    gol=DB.XYZ((-3.9 if lev else zerk + 3.9) * M, 15.6 * M, 0))
        else:
            vynoska(doc, v, tnt, KRAN_POL, p, 0.3 if lev else 0.6, -2.4 if lev else -3.2, log)
            x_pod = 0.25 if lev else zerk - 0.25
            vynoska(doc, v, tnt, u'Подъем В1\rØ%d' % g_dn_pol(g),
                    DB.XYZ(x_pod * M, k_['y'] * M, -0.05 * M), -1.6 if lev else 2.2, -1.0, log)
            t = None
            for tt in truby_sistemy(doc, u'КВВ-В1'):
                a, b = koncy(tt)
                if min(a.DistanceTo(p), b.DistanceTo(p)) < 0.005 * M:
                    t = tt
                    break
            if t is not None:
                a, b = koncy(t)
                kon, dr = (a, b) if a.DistanceTo(p) < b.DistanceTo(p) else (b, a)
                q = kon + (dr - kon).Normalize().Multiply(0.15 * M)
                ot.postavit(t, q, -1.2 if lev else 1.2, -0.6)
