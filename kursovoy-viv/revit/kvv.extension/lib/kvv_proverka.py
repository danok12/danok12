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
        imya = f.Name                       # после LoadFamily объект семейства недействителен
        try:
            fd = doc.EditFamily(f)
        except Exception as ex:
            log(u'  семейство не открыть:', imya, ex)
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
                log(u'  шрифт в семействе', imya, u':', len(plohie), u'типов текста')
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
    # стык без логической связи: конец трубы у соединителя прибора (заход в патрубок сифона) — не коллизия
    for ca in cons(a):
        for cb in cons(b):
            try:
                if ca.Origin.DistanceTo(cb.Origin) < 0.03 * M:
                    return True
            except Exception:
                pass
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
            # вложенный сифон прибора (мойки, умывальника, ванны): труба присоединена к самому прибору
            sup = getattr(p, 'SuperComponent', None)
            if sup is not None and soedineny(e, sup):
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
    # 5. трубы одной системы налегают на трубы и арматуру той же системы (не соединённые напрямую): так у счётчика
    #    после неудачного перехода трубы оказались вложены друг в друга
    for pref in (u'КВВ-В1', u'КВВ-К1'):
        svoi = [e for e in seti if metka(e).startswith(pref) and (
            isinstance(e, Plumbing.Pipe) or e.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_PipeAccessory))]
        ids = List[DB.ElementId]([e.Id for e in svoi])
        bylo = set()
        for e in svoi:
            if not isinstance(e, Plumbing.Pipe):
                continue
            bb = e.get_BoundingBox(None)
            for q in DB.FilteredElementCollector(doc, ids).WherePasses(
                    DB.BoundingBoxIntersectsFilter(DB.Outline(bb.Min, bb.Max))).WherePasses(
                    DB.ElementIntersectsElementFilter(e)):
                if q.Id == e.Id or soedineny(e, q):
                    continue
                kl = tuple(sorted((e.Id.IntegerValue, q.Id.IntegerValue)))
                if kl in bylo:
                    continue
                bylo.add(kl)
                v = obem_peresecheniya(e, q)
                if v > 20 * (0.01 * M) ** 3:
                    zap(u'налегание в ' + pref[4:], u'%d × %d %s, объём %.0f см³' % (
                        e.Id.IntegerValue, q.Id.IntegerValue, centr(e), v / (0.01 * M) ** 3))
    if not itogi:
        log(u'КОЛЛИЗИЙ НЕТ: В1/К1, трубы/приборы, трубы вдоль стен, приборы в стенах, налегания в системах')
    for vid, sp in sorted(itogi.items()):
        log(u'КОЛЛИЗИЯ:', vid, u'—', len(sp))
        for s in sp[:15]:
            log(u'   ', s)
    return itogi


# ---------------- 3D-виды для осмотра модели ----------------
VID_3D = u'КВВ_3D_Здание и сети'
VID_3D_PODVAL = u'КВВ_3D_Подвал'
KAT_SETI = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting,
            DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_MechanicalEquipment)
KAT_ZDANIE = (DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_Roofs,
              DB.BuiltInCategory.OST_Stairs)
KAT_SKRYT = (DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_Grids, DB.BuiltInCategory.OST_Rooms,
             DB.BuiltInCategory.OST_Doors, DB.BuiltInCategory.OST_Windows, DB.BuiltInCategory.OST_StairsRailing)


def _sploshnaya_zalivka(doc):
    for f in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
        fp = f.GetFillPattern()
        if fp.IsSolidFill and fp.Target == DB.FillPatternTarget.Drafting:
            return f.Id
    return DB.ElementId.InvalidElementId


def _filtr_sistemy(doc, imya, metka_):
    """Фильтр вида: элементы сетей с «Комментарием», начинающимся с метки системы (КВВ-В1 / КВВ-К1)."""
    for f in DB.FilteredElementCollector(doc).OfClass(DB.ParameterFilterElement):
        if f.Name == imya:
            return f
    kat = List[DB.ElementId]([DB.ElementId(c) for c in KAT_SETI])
    pravilo = DB.ParameterFilterRuleFactory.CreateBeginsWithRule(
        DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS), metka_)
    return DB.ParameterFilterElement.Create(doc, imya, kat, DB.ElementParameterFilter(pravilo))


def vidy_3d(doc, log):
    """Рабочие 3D-виды для осмотра (не для листов): всё здание и подвал с первым этажом. Стены и перекрытия —
    прозрачные, сети — цветом своей системы (В1 синий, К1 коричневый), детализация «Высокая» (видны фитинги,
    арматура, переходы), стиль «Тонированный с кромками». В транзакции. Возвращает (вид здания, вид подвала)."""
    vft = [t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
           if t.ViewFamily == DB.ViewFamily.ThreeDimensional][0]
    zaliv = _sploshnaya_zalivka(doc)
    filtry = [(_filtr_sistemy(doc, u'КВВ_3D_В1', u'КВВ-В1'), DB.Color(0, 127, 255)),
              (_filtr_sistemy(doc, u'КВВ_3D_К1', u'КВВ-К1'), DB.Color(165, 41, 0)),
              (_filtr_sistemy(doc, u'КВВ_3D_оборудование', u'КВВ-О'), DB.Color(0, 160, 80))]
    vidy = []
    for imya in (VID_3D, VID_3D_PODVAL):
        v = None
        for e in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
            if not e.IsTemplate and e.Name == imya:
                v = e
        if v is None:
            v = DB.View3D.CreateIsometric(doc, vft.Id)
            v.Name = imya
        v.ViewTemplateId = DB.ElementId.InvalidElementId
        if v.IsLocked:
            v.Unlock()
        v.DetailLevel = DB.ViewDetailLevel.Fine
        v.DisplayStyle = DB.DisplayStyle.Shading
        try:
            v.Scale = 50
        except Exception:
            pass
        # в диспетчере проекта — среди вспомогательных видов, а не в группе «???»
        for p in v.Parameters:
            nm = p.Definition.Name
            if p.StorageType == DB.StorageType.String and not p.IsReadOnly:
                if u'Назначение' in nm:
                    p.Set(u'Вспомогательные виды')
                elif u'Раздел' in nm:
                    p.Set(u'3D для осмотра')
        prozr = DB.OverrideGraphicSettings()
        prozr.SetSurfaceTransparency(85)
        prozr.SetProjectionLineColor(DB.Color(190, 190, 190))
        for c in KAT_ZDANIE:
            cid = DB.ElementId(c)
            try:
                if v.CanCategoryBeHidden(cid):
                    v.SetCategoryHidden(cid, False)
                v.SetCategoryOverrides(cid, prozr)
            except Exception:
                pass
        for c in KAT_SETI + (DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel):
            cid = DB.ElementId(c)
            try:
                if v.CanCategoryBeHidden(cid):
                    v.SetCategoryHidden(cid, False)
            except Exception:
                pass
        for c in KAT_SKRYT:
            cid = DB.ElementId(c)
            try:
                if v.CanCategoryBeHidden(cid):
                    v.SetCategoryHidden(cid, True)
            except Exception:
                pass
        for f, cvet in filtry:
            if not v.IsFilterApplied(f.Id):
                v.AddFilter(f.Id)
            o = DB.OverrideGraphicSettings()
            o.SetProjectionLineColor(cvet)
            o.SetSurfaceForegroundPatternColor(cvet)
            if zaliv != DB.ElementId.InvalidElementId:
                o.SetSurfaceForegroundPatternId(zaliv)
            v.SetFilterOverrides(f.Id, o)
            v.SetFilterVisibility(f.Id, True)
        vidy.append(v)
    # подвал и первый этаж: секущий параллелепипед по зданию от низа подвала до +1,5 м
    zd = [w.get_BoundingBox(None) for w in DB.FilteredElementCollector(doc).OfClass(DB.Wall)]
    zd = [b for b in zd if b is not None]
    x0, y0 = min(b.Min.X for b in zd), min(b.Min.Y for b in zd)
    x1, y1 = max(b.Max.X for b in zd), max(b.Max.Y for b in zd)
    sb = DB.BoundingBoxXYZ()
    sb.Min = DB.XYZ(x0 - 3 * kvv.M, y0 - 3 * kvv.M, -3.6 * kvv.M)
    sb.Max = DB.XYZ(x1 + 3 * kvv.M, y1 + 3 * kvv.M, 1.5 * kvv.M)
    vidy[1].IsSectionBoxActive = True
    vidy[1].SetSectionBox(sb)
    vidy[0].IsSectionBoxActive = False
    log(u'3D-виды для осмотра:', VID_3D, u'и', VID_3D_PODVAL, u'| детализация высокая, стены прозрачные, '
        u'сети по системам')
    return vidy
