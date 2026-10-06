# -*- coding: utf-8 -*-
"""Проверка модели перед выдачей (IronPython, pyRevit): шрифт ГОСТ (тип Б, «GOST Common») во всех типах текста,
размеров, отметок, таблиц и в семействах марок и основной надписи; коллизии сетей — В1 с К1, трубы с приборами,
трубы вдоль стен, приборы в стенах.

Как у преподавателя: на листах шрифт «GOST Common» (обычный, не курсив).
"""
import math
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
from System.Collections.Generic import List
import kvv

M = kvv.M
MM = kvv.MM
SHRIFT = u'GOST Common'


class Zagruzka(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = False
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues.Value = False
        return True


def _shrift_tipa(t):
    p = t.get_Parameter(DB.BuiltInParameter.TEXT_FONT)
    return p.AsString() if p is not None else None


def _postavit_shrift(t):
    p = t.get_Parameter(DB.BuiltInParameter.TEXT_FONT)
    if p is None or p.IsReadOnly or p.AsString() == SHRIFT:
        return False
    p.Set(SHRIFT)
    return True


def shrift_v_proekte(doc, log):
    """Типы текста, размеров и отметок проекта — шрифт GOST Common. В транзакции."""
    bylo = {}
    n = 0
    for cls in (DB.TextNoteType, DB.DimensionType, DB.SpotDimensionType):
        for t in DB.FilteredElementCollector(doc).OfClass(cls):
            f = _shrift_tipa(t)
            if f is None:
                continue
            bylo[f] = bylo.get(f, 0) + 1
            if _postavit_shrift(t):
                n += 1
    log(u'шрифты типов текста/размеров/отметок были:', bylo, u'| заменено на', SHRIFT, u':', n)
    # таблицы (экспликация): тексты тела, заголовков и названия — тип текста с GOST Common
    tt = None
    for t in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType):
        if _shrift_tipa(t) == SHRIFT and abs(t.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).AsDouble() - 2.5 * MM) < 1e-6:
            tt = t
            break
    ns = 0
    for vs in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule):
        if vs.IsTemplate or vs.IsTitleblockRevisionSchedule:
            continue
        for a in ('BodyTextTypeId', 'HeaderTextTypeId', 'TitleTextTypeId'):
            try:
                if tt is not None:
                    setattr(vs, a, tt.Id)
                    ns += 1
            except Exception:
                pass
    log(u'таблицы: тексты переведены на', SHRIFT, u'—', ns, u'назначений')


def shrift_v_semeystvah(doc, log, kategorii):
    """Семейства аннотаций (марки, основная надпись, заголовки видов): тексты и метки — GOST Common.
    Вне транзакции (правка семейства и загрузка обратно)."""
    fams = {}
    for bic in kategorii:
        for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(bic):
            f = s_.Family
            if f.IsEditable:
                fams[f.Id.IntegerValue] = f
    n_f, n_t, nesh = 0, 0, {}
    for f in fams.values():
        try:
            fd = doc.EditFamily(f)
        except Exception as ex:
            log(u'  семейство не открыть:', f.Name, ex)
            continue
        try:
            plohie = []
            for t in DB.FilteredElementCollector(fd).OfClass(DB.TextElementType):
                sf = _shrift_tipa(t)
                if sf is not None and sf != SHRIFT:
                    plohie.append(t)
                    nesh[sf] = nesh.get(sf, 0) + 1
            if plohie:
                tr = DB.Transaction(fd, u'КВВ: шрифт ГОСТ')
                tr.Start()
                for t in plohie:
                    _postavit_shrift(t)
                tr.Commit()
                fd.LoadFamily(doc, Zagruzka())
                n_f += 1
                n_t += len(plohie)
                log(u'  шрифт в семействе', f.Name, u':', len(plohie), u'типов текста')
        finally:
            try:
                fd.Close(False)
            except Exception:
                pass
    log(u'семейства аннотаций: проверено', len(fams), u'| исправлено семейств', n_f, u'типов текста', n_t,
        u'| были шрифты', nesh)


# ---------------- коллизии ----------------
def metka(e):
    try:
        p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    except Exception:
        return u''
    return (p.AsString() or u'') if p is not None and p.HasValue else u''


def tverdye(e):
    opt = DB.Options()
    opt.DetailLevel = DB.ViewDetailLevel.Fine
    out = []

    def obhod(geo):
        for g in geo:
            if isinstance(g, DB.Solid) and g.Volume > 1e-9:
                out.append(g)
            elif isinstance(g, DB.GeometryInstance):
                obhod(g.GetInstanceGeometry())
    try:
        obhod(e.get_Geometry(opt))
    except Exception:
        pass
    return out


def obem_peresecheniya(a, b):
    v = 0.0
    for sa in tverdye(a):
        for sb in tverdye(b):
            try:
                r = DB.BooleanOperationsUtils.ExecuteBooleanOperation(sa, sb, DB.BooleanOperationsType.Intersect)
                if r is not None:
                    v += r.Volume
            except Exception:
                pass
    return v


def soedineny(a, b):
    """Элементы соединены соединителями (напрямую) — их касание не коллизия."""
    def cons(e):
        if isinstance(e, Plumbing.Pipe):
            return list(e.ConnectorManager.Connectors)
        mm = getattr(e, 'MEPModel', None)
        if mm is None or mm.ConnectorManager is None:
            return []
        return list(mm.ConnectorManager.Connectors)
    for c in cons(a):
        for r in c.AllRefs:
            if r.Owner.Id == b.Id:
                return True
    return False


def centr(e):
    bb = e.get_BoundingBox(None)
    if bb is None:
        return u'?'
    p = (bb.Min + bb.Max).Multiply(0.5)
    return u'(%.2f, %.2f, %.2f)' % (p.X / M, p.Y / M, p.Z / M)


def kollizii(doc, log):
    """В1 с К1; трубы и фитинги с сантехприборами (кроме присоединённых); трубы вдоль стен; приборы в стенах."""
    kat_seti = [DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting,
                DB.BuiltInCategory.OST_PipeAccessory]
    seti = []
    for bic in kat_seti:
        seti += [e for e in DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType()
                 if metka(e).startswith(u'КВВ-')]
    v1 = [e for e in seti if metka(e).startswith(u'КВВ-В1')]
    k1_ids = List[DB.ElementId]([e.Id for e in seti if metka(e).startswith(u'КВВ-К1')])
    log(u'элементов сетей: В1', len(v1), u'| К1', k1_ids.Count)
    itogi = {}

    def zap(vid, opis):
        itogi.setdefault(vid, []).append(opis)

    # 1. В1 и К1
    for e in v1:
        bb = e.get_BoundingBox(None)
        if bb is None or k1_ids.Count == 0:
            continue
        f = DB.ElementIntersectsElementFilter(e)
        for k in DB.FilteredElementCollector(doc, k1_ids).WherePasses(
                DB.BoundingBoxIntersectsFilter(DB.Outline(bb.Min, bb.Max))).WherePasses(f):
            zap(u'В1 пересекает К1', u'%d × %d %s' % (e.Id.IntegerValue, k.Id.IntegerValue, centr(e)))
    # 2. сети и сантехприборы (кроме соединённых и подводок, входящих в прибор у соединителя)
    pr = list(DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_PlumbingFixtures)
              .WhereElementIsNotElementType())
    pr_ids = List[DB.ElementId]([p.Id for p in pr])
    for e in seti:
        if not isinstance(e, Plumbing.Pipe):
            continue
        bb = e.get_BoundingBox(None)
        if bb is None:
            continue
        for p in DB.FilteredElementCollector(doc, pr_ids).WherePasses(
                DB.BoundingBoxIntersectsFilter(DB.Outline(bb.Min, bb.Max))).WherePasses(
                DB.ElementIntersectsElementFilter(e)):
            if soedineny(e, p):
                continue
            v = obem_peresecheniya(e, p)
            if v > (0.02 * M) ** 3:
                zap(u'труба проходит через прибор', u'%d × %s %s, объём %.0f см³' % (
                    e.Id.IntegerValue, p.Symbol.FamilyName, centr(e), v / (0.01 * M) ** 3))
    # 3. трубы вдоль стен (проход поперёк — нормально): длина трубы в стене больше её толщины в 1,5 раза
    steny = list(DB.FilteredElementCollector(doc).OfClass(DB.Wall))
    st_ids = List[DB.ElementId]([w.Id for w in steny])
    for e in seti:
        if not isinstance(e, Plumbing.Pipe):
            continue
        bb = e.get_BoundingBox(None)
        c = e.Location.Curve
        for w in DB.FilteredElementCollector(doc, st_ids).WherePasses(
                DB.BoundingBoxIntersectsFilter(DB.Outline(bb.Min, bb.Max))).WherePasses(
                DB.ElementIntersectsElementFilter(e)):
            v = obem_peresecheniya(e, w)
            s_tr = math.pi * (e.get_Parameter(DB.BuiltInParameter.RBS_PIPE_OUTER_DIAMETER).AsDouble() / 2) ** 2
            if s_tr <= 0:
                continue
            dlina = v / s_tr
            if dlina > w.Width * 1.5 + 0.05 * M:
                zap(u'труба вдоль стены', u'%d %s в стене %s, %.2f м' % (
                    e.Id.IntegerValue, centr(e), DB.Element.Name.GetValue(w.WallType), dlina / M))
    # 4. приборы в стенах
    for p in pr:
        bb = p.get_BoundingBox(None)
        if bb is None:
            continue
        for w in DB.FilteredElementCollector(doc, st_ids).WherePasses(
                DB.BoundingBoxIntersectsFilter(DB.Outline(bb.Min, bb.Max))).WherePasses(
                DB.ElementIntersectsElementFilter(p)):
            v = obem_peresecheniya(p, w)
            if v > (0.03 * M) ** 3:
                zap(u'прибор в стене', u'%s %s, объём %.0f см³' % (p.Symbol.FamilyName, centr(p),
                                                                  v / (0.01 * M) ** 3))
    if not itogi:
        log(u'КОЛЛИЗИЙ НЕТ: В1/К1, трубы/приборы, трубы вдоль стен, приборы в стенах')
    for vid, sp in sorted(itogi.items()):
        log(u'КОЛЛИЗИЯ:', vid, u'—', len(sp))
        for s in sp[:15]:
            log(u'   ', s)
    return itogi
