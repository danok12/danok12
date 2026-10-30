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
KAT_SETI = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_FlexPipeCurves, DB.BuiltInCategory.OST_PipeFitting,
            DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_MechanicalEquipment)
KAT_ZDANIE = (DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_Roofs,
              DB.BuiltInCategory.OST_Stairs)
KAT_SKRYT = (DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_Grids, DB.BuiltInCategory.OST_Rooms,
             DB.BuiltInCategory.OST_Doors, DB.BuiltInCategory.OST_Windows, DB.BuiltInCategory.OST_StairsRailing) + \
    tuple(getattr(DB.BuiltInCategory, k) for k in (u'OST_Toposolid', u'OST_Topography')
          if hasattr(DB.BuiltInCategory, k))          # земля (03, zemlya) закрывает ввод и выпуски


def _sploshnaya_zalivka(doc):
    for f in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
        fp = f.GetFillPattern()
        if fp.IsSolidFill and fp.Target == DB.FillPatternTarget.Drafting:
            return f.Id
    return DB.ElementId.InvalidElementId


def _filtr_sistemy(doc, imya, metka_):
    """Фильтр вида: элементы сетей с «Комментарием», начинающимся с метки системы (КВВ-В1 / КВВ-К1)."""
    kat = List[DB.ElementId]([DB.ElementId(c) for c in KAT_SETI])
    for f in DB.FilteredElementCollector(doc).OfClass(DB.ParameterFilterElement):
        if f.Name == imya:
            # существующий фильтр — с текущими категориями (30.10 добавлены гибкие трубы: подводки были серые)
            f.SetCategories(kat)
            return f
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
        # стены и перекрытия, скрытые на виде вручную при осмотре (30.10: стена 9-го этажа по оси А) — вернуть
        skr = [e.Id for c in KAT_ZDANIE
               for e in DB.FilteredElementCollector(doc).OfCategory(c).WhereElementIsNotElementType()
               if e.IsHidden(v)]
        if skr:
            v.UnhideElements(List[DB.ElementId](skr))
            log(u'вид', imya, u'| возвращено скрытых элементов здания', len(skr))
        # чужие фильтры (остались от шаблона ADSK: «Канализация», «Отверстия и ниши»… — скрывали К1) — убрать
        nashi = set(f.Id.IntegerValue for f, _ in filtry)
        for fid in list(v.GetFilters()):
            if fid.IntegerValue not in nashi:
                log(u'вид', imya, u'| убран фильтр', doc.GetElement(fid).Name)
                v.RemoveFilter(fid)
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


def sistemy(doc, log):
    """Сколько систем трубопроводов в модели и где система «рвётся»: соединённые соединители, у которых разные
    системы (или у одного нет системы). Сеть В1 должна быть одной системой «В1 1» (29.10 Revit показывал В1 21)."""
    import collections

    def soed(e):
        if isinstance(e, (Plumbing.Pipe, Plumbing.FlexPipe)):
            return list(e.ConnectorManager.Connectors)
        mm = getattr(e, 'MEPModel', None)
        if mm is None or mm.ConnectorManager is None:
            return []
        return [c for c in mm.ConnectorManager.Connectors if c.Domain == DB.Domain.DomainPiping]

    def imya_sist(c):
        try:
            s = c.MEPSystem
        except Exception:
            s = None
        return s.Name if s is not None else u'(нет)'

    def fam(e):
        if isinstance(e, DB.FamilyInstance):
            return e.Symbol.FamilyName
        return e.GetType().Name + u' ' + (DB.Element.Name.GetValue(e) or u'')

    po_tipu = collections.Counter()
    for s in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystem):
        tip = doc.GetElement(s.GetTypeId())
        po_tipu[DB.Element.Name.GetValue(tip) if tip else u'?'] += 1
    log(u'систем трубопроводов по типам:', dict(po_tipu))
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystemType):
        nm = DB.Element.Name.GetValue(t)
        if nm not in po_tipu:
            continue
        log(u'тип системы', nm, u'| классификация', t.SystemClassification)
        for pr in sorted(t.Parameters, key=lambda q: q.Definition.Name):
            try:
                v = pr.AsValueString() or pr.AsString() or u''
            except Exception:
                v = u'?'
            if v:
                log(u'    %s = %s' % (pr.Definition.Name, v))
    n_tr = sum(1 for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe) if metka(p).startswith(u'КВВ-В1'))
    log(u'труб В1 в модели:', n_tr)
    kat = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_FlexPipeCurves, DB.BuiltInCategory.OST_PipeFitting,
           DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_PlumbingFixtures,
           DB.BuiltInCategory.OST_MechanicalEquipment)
    granicy, primer, razmer = collections.Counter(), {}, collections.Counter()
    for k in kat:
        for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
            for c in soed(e):
                s1 = imya_sist(c)
                if s1.startswith(u'В1'):
                    razmer[s1] += 1
                if not c.IsConnected:
                    continue
                for r in c.AllRefs:
                    if r.Owner is None or r.Owner.Id == e.Id or r.Domain != DB.Domain.DomainPiping:
                        continue
                    s2 = imya_sist(r)
                    if s1 == s2 or not (s1.startswith(u'В1') or s2.startswith(u'В1')):
                        continue
                    try:
                        k1_, k2_ = unicode(c.PipeSystemType), unicode(r.PipeSystemType)
                    except Exception:
                        k1_, k2_ = u'?', u'?'
                    kl = (fam(e), k1_, fam(r.Owner), k2_)
                    granicy[kl] += 1
                    primer.setdefault(kl, (e.Id.IntegerValue, s1, s2, c.Origin.X / kvv.M, c.Origin.Y / kvv.M,
                                           c.Origin.Z / kvv.M))
    log(u'систем В1:', len(razmer), u'| соединителей по системам (10 крупнейших):', razmer.most_common(10))
    # из чего состоят системы: размер -> сколько систем; пример состава у нескольких систем каждого размера
    po_razmeru = collections.Counter(razmer.values())
    log(u'размеры систем В1 (соединителей: систем):', sorted(po_razmeru.items(), key=lambda kv: -kv[1])[:12])
    sostav = collections.defaultdict(collections.Counter)
    tochka = {}
    for k in kat:
        for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
            for c in soed(e):
                s1 = imya_sist(c)
                if s1.startswith(u'В1'):
                    sostav[s1][fam(e)] += 1
                    tochka.setdefault(s1, (c.Origin.X / kvv.M, c.Origin.Y / kvv.M, c.Origin.Z / kvv.M))
    vidano = collections.Counter()
    for s1, n in sorted(razmer.items(), key=lambda kv: -kv[1]):
        if vidano[n] >= 2:
            continue
        vidano[n] += 1
        log(u'  %s (%d соед.) у (%.2f, %.2f, %.2f): %s' % ((s1, n) + tochka[s1] + (
            u'; '.join(u'%s %d' % (f_, m) for f_, m in sostav[s1].most_common(6)),)))
    log(u'границы систем В1 (элемент | классификация соединителя | сосед | классификация — число, пример id, системы, точка):')
    for kl, n in granicy.most_common(30):
        pr = primer[kl]
        log(u'  %4d | %s | %s | %s | %s | id %d %s/%s (%.2f, %.2f, %.2f)' % ((n,) + kl + pr))


def proba_sistem(doc, log, s_pravilom=False):
    """Опыт (всё откатывается): в пустом месте по две трубы с отводом для каждого типа системы трубопроводов и
    каждого типа трубы — одна ли получается система. Ответ: сливает ли Revit системы при соединении."""
    M = kvv.M
    lv = sorted(DB.FilteredElementCollector(doc).OfClass(DB.Level), key=lambda l: l.Elevation)[0]
    tipy_sist = [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystemType)
                 if DB.Element.Name.GetValue(t) in (u'ADSK_Водопровод_В1', u'ADSK_Канализация_К1')]
    tipy_sist += [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystemType)
                  if t.SystemClassification == DB.MEPSystemClassification.DomesticColdWater
                  and DB.Element.Name.GetValue(t) != u'ADSK_Водопровод_В1'][:2]
    tipy_tr = [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipeType)
               if DB.Element.Name.GetValue(t) in (u'ADSK_Полипропилен_PN20', u'ADSK_Сталь водогазопроводная_Оцинкованная_ГОСТ 3262-75',
                                                  u'ADSK_Полипропилен раструбный_ГОСТ 32414-2013')]
    pary = []
    glush = kvv.Tranzakciya(doc, u'КВВ: опыт систем (с удалением предупреждений)', log)
    tr = glush.__enter__()
    x0 = -100.0
    for ts in tipy_sist:
        for tt in tipy_tr:
            try:
                a, b, c = kvv.xyz(x0, -100, 0), kvv.xyz(x0 + 1, -100, 0), kvv.xyz(x0 + 1, -99, 0)
                p1 = Plumbing.Pipe.Create(doc, ts.Id, tt.Id, lv.Id, a, b)
                p2 = Plumbing.Pipe.Create(doc, ts.Id, tt.Id, lv.Id, b, c)
                c1 = [q for q in p1.ConnectorManager.Connectors if q.Origin.DistanceTo(b) < 1e-6][0]
                c2 = [q for q in p2.ConnectorManager.Connectors if q.Origin.DistanceTo(b) < 1e-6][0]
                if s_pravilom:
                    # как в kvv_seti._popytka: временное правило в типе трубы, затем удалить
                    gr = DB.RoutingPreferenceRuleGroupType.Elbows
                    rpm = tt.RoutingPreferenceManager
                    rid = rpm.GetRule(gr, 0).MEPPartId
                    rpm.AddRule(gr, DB.RoutingPreferenceRule(rid, u'КВВ'), 0)
                    doc.Regenerate()
                f = doc.Create.NewElbowFitting(c1, c2)
                if s_pravilom:
                    rpm.RemoveRule(gr, 0)
                    doc.Regenerate()
                pary.append((DB.Element.Name.GetValue(ts) + u' + ' + DB.Element.Name.GetValue(tt), p1.Id, p2.Id, f.Id))
            except Exception:
                pass
            x0 += 3.0
    tr.Commit()
    log(u'  (транзакция kvv.Tranzakciya — предупреждения удаляются)')
    ids = []
    for nm, i1, i2, fi in pary:
        s1, s2 = doc.GetElement(i1).MEPSystem, doc.GetElement(i2).MEPSystem
        log(u'  после фиксации %s: систем у пары труб — %s (%s / %s)' % (
            nm, u'ОДНА' if s1 and s2 and s1.Id == s2.Id else u'ДВЕ', s1.Name if s1 else u'-', s2.Name if s2 else u'-'))
        ids += [i1, i2, fi]
    tr = DB.Transaction(doc, u'КВВ: опыт систем — удалить')
    tr.Start()
    doc.Delete(List[DB.ElementId](ids))
    tr.Commit()
    log(u'опыт удалён')


def obedinit_sistemy(doc, log, tip=u'ADSK_Водопровод_В1'):
    """Собрать сеть в одну систему (29.10: В1 была разбита на 1547 систем при физически соединённых элементах).
    Способ 1: удалить все системы этого типа, кроме самой большой, — Revit заново относит соединённые элементы к
    системе сети. Способ 2: тип системы трубы задаётся заново (SetSystemType) для одной трубы каждой оставшейся
    системы. Каждый способ — в подтранзакции, откат, если систем не стало меньше. Транзакция — снаружи."""
    def sist():
        out = []
        for s in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystem):
            t = doc.GetElement(s.GetTypeId())
            if t is not None and DB.Element.Name.GetValue(t) == tip:
                out.append(s)
        return out

    def razmer(s):
        try:
            return s.PipingNetwork.Size
        except Exception:
            return 0
    s0 = sist()
    log(u'систем', tip, u'до:', len(s0))
    if len(s0) <= 1:
        return
    tid = s0[0].GetTypeId()
    # способ 1
    st = DB.SubTransaction(doc)
    st.Start()
    try:
        bolshaya = max(s0, key=razmer)
        doc.Delete(List[DB.ElementId]([s.Id for s in s0 if s.Id != bolshaya.Id]))
        doc.Regenerate()
        n1 = len(sist())
        bez = sum(1 for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)
                  if p.MEPSystem is None and (metka(p) or u'').startswith(u'КВВ-В1'))
        log(u'  способ 1 (удалить лишние системы): систем', n1, u'| труб В1 без системы', bez)
        if n1 < len(s0) and bez == 0:
            st.Commit()
        else:
            st.RollBack()
    except Exception as ex:
        st.RollBack()
        log(u'  способ 1 не удался:', ex)
    # способ 2
    s1 = sist()
    if len(s1) > 1:
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            n_ok = 0
            for s in s1:
                if not s.IsValidObject:
                    continue
                for e in s.PipingNetwork:
                    if isinstance(e, Plumbing.Pipe):
                        e.SetSystemType(tid)
                        n_ok += 1
                        break
            doc.Regenerate()
            n2 = len(sist())
            log(u'  способ 2 (SetSystemType): труб', n_ok, u'| систем', n2)
            if n2 < len(s1):
                st.Commit()
            else:
                st.RollBack()
        except Exception as ex:
            st.RollBack()
            log(u'  способ 2 не удался:', ex)
    # способ 3: новая система по всем приборам и оборудованию (как «Создать систему» в Revit), до и после удаления
    # прежних систем
    def soed_v1():
        cs = DB.ConnectorSet()
        n = 0
        for k in (DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_MechanicalEquipment):
            for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
                mm = getattr(e, 'MEPModel', None)
                if mm is None or mm.ConnectorManager is None:
                    continue
                for c in mm.ConnectorManager.Connectors:
                    if c.Domain == DB.Domain.DomainPiping and c.PipeSystemType == Plumbing.PipeSystemType.DomesticColdWater:
                        cs.Insert(c)
                        n += 1
        return cs, n
    for udalit in (False, True):
        if len(sist()) <= 2:
            break
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            if udalit:
                doc.Delete(List[DB.ElementId]([s.Id for s in sist()]))
                doc.Regenerate()
            cs, n = soed_v1()
            ps = Plumbing.PipingSystem.Create(doc, tid, u'В1')
            ps.Add(cs)
            doc.Regenerate()
            n3 = len(sist())
            bez = sum(1 for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)
                      if p.MEPSystem is None and (metka(p) or u'').startswith(u'КВВ-В1'))
            log(u'  способ 3%s: соединителей приборов %d | систем %d | размер новой %d | труб В1 без системы %d'
                % (u' (после удаления систем)' if udalit else u'', n, n3, razmer(ps), bez))
            if n3 < len(s0) and bez == 0:
                st.Commit()
            else:
                st.RollBack()
        except Exception as ex:
            st.RollBack()
            log(u'  способ 3 не удался:', ex)
    # способ 4: разорвать и заново соединить стыки, где система меняется (если при соединении Revit сливает системы)
    if len(sist()) > 2:
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            def imya(c):
                try:
                    return c.MEPSystem.Name if c.MEPSystem is not None else None
                except Exception:
                    return None
            pary, n_ok, n_osh = [], 0, 0
            kat = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_FlexPipeCurves,
                   DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory)
            for k in kat:
                for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
                    if not (metka(e) or u'').startswith(u'КВВ-В1'):
                        continue
                    cm = e.ConnectorManager if isinstance(e, (Plumbing.Pipe, Plumbing.FlexPipe)) else \
                        (e.MEPModel.ConnectorManager if getattr(e, 'MEPModel', None) else None)
                    if cm is None:
                        continue
                    for c in cm.Connectors:
                        if c.Domain != DB.Domain.DomainPiping or not c.IsConnected:
                            continue
                        for r in c.AllRefs:
                            if r.Owner is None or r.Owner.Id == e.Id or r.Domain != DB.Domain.DomainPiping:
                                continue
                            if r.ConnectorType not in (DB.ConnectorType.End, DB.ConnectorType.Curve):
                                continue
                            if imya(c) != imya(r) and e.Id.IntegerValue < r.Owner.Id.IntegerValue:
                                pary.append((c, r))
            for c, r in pary:
                try:
                    c.DisconnectFrom(r)
                    c.ConnectTo(r)
                    n_ok += 1
                except Exception:
                    n_osh += 1
            doc.Regenerate()
            n4 = len(sist())
            log(u'  способ 4 (переподключить стыки): стыков %d | переподключено %d | ошибок %d | систем %d'
                % (len(pary), n_ok, n_osh, n4))
            if n4 < len(s0) and n_osh == 0:
                st.Commit()
            else:
                st.RollBack()
        except Exception as ex:
            st.RollBack()
            log(u'  способ 4 не удался:', ex)
    s2 = sist()
    log(u'систем', tip, u'после:', len(s2), u'| размеры:', sorted((razmer(s) for s in s2), reverse=True)[:10])


def svobodnye(doc, log):
    """Элементы сетей, которые «висят»: свободные соединители у труб, фитингов и арматуры (кроме верха вытяжной
    части стояков К1), элементы без системы и без метки КВВ. Свободный соединитель делится на «касается» (в той же
    точке ±2 мм есть соединитель другого элемента, но связи нет) и «открытый конец». Журнал — сводка и списки."""
    import collections
    M = kvv.M
    kat_set = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting,
               DB.BuiltInCategory.OST_PipeAccessory)
    kat_vse = kat_set + (DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_MechanicalEquipment)

    def soed(e):
        if isinstance(e, Plumbing.Pipe):
            return list(e.ConnectorManager.Connectors)
        mm = getattr(e, 'MEPModel', None)
        if mm is None or mm.ConnectorManager is None:
            return []
        return [c for c in mm.ConnectorManager.Connectors if c.Domain == DB.Domain.DomainPiping]

    def klyuch(p):
        return (int(round(p.X / M * 500)), int(round(p.Y / M * 500)), int(round(p.Z / M * 500)))   # сетка 2 мм

    tochki = collections.defaultdict(list)
    elementy = []
    for bic in kat_vse:
        for e in DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
            cs = soed(e)
            for c in cs:
                tochki[klyuch(c.Origin)].append(e.Id.IntegerValue)
            if bic in kat_set:
                elementy.append((e, cs))

    def sosed(e, c):
        k = klyuch(c.Origin)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for i in tochki.get((k[0] + dx, k[1] + dy, k[2] + dz), []):
                        if i != e.Id.IntegerValue:
                            return doc.GetElement(DB.ElementId(i))
        return None

    def imya(e):
        if isinstance(e, Plumbing.Pipe):
            return u'Труба ' + DB.Element.Name.GetValue(e.PipeType)
        return u'%s : %s' % (e.Symbol.FamilyName, DB.Element.Name.GetValue(e.Symbol))

    svodka = collections.Counter()
    kasaetsya, otkrytye, chuzhie = [], [], []
    for e, cs in elementy:
        m_ = metka(e)
        bez_sist = False
        try:
            bez_sist = all(c.MEPSystem is None for c in cs)
        except Exception:
            pass
        if not m_.startswith(u'КВВ') or bez_sist:
            sup = getattr(e, 'SuperComponent', None)
            chuzhie.append(u'  id %d | %s | метка %s%s | соединителей %d, свободных %d | %s' % (
                e.Id.IntegerValue, imya(e) + (u' (вложено в %s)' % sup.Symbol.FamilyName if sup is not None else u''),
                m_ or u'-', u' | БЕЗ СИСТЕМЫ' if bez_sist else u'', len(cs),
                len([c for c in cs if not c.IsConnected]),
                u'; '.join(u'(%.3f, %.3f, %.3f)' % (c.Origin.X / M, c.Origin.Y / M, c.Origin.Z / M) for c in cs)))
        for c in cs:
            if c.IsConnected:
                continue
            if isinstance(e, Plumbing.Pipe) and c.Origin.Z / M > 35.0:
                continue                                  # верх вытяжной части стояка
            s_ = sosed(e, c)
            t = u'(%.3f, %.3f, %.3f)' % (c.Origin.X / M, c.Origin.Y / M, c.Origin.Z / M)
            if s_ is not None:
                vid = u'касается'
                kasaetsya.append(u'  id %d %s | %s — касается id %d %s' % (
                    e.Id.IntegerValue, imya(e), t, s_.Id.IntegerValue,
                    imya(s_) if s_.Category.Id.IntegerValue != int(DB.BuiltInCategory.OST_PlumbingFixtures)
                    else u'прибор ' + s_.Symbol.FamilyName))
            else:
                vid = u'открытый конец'
                otkrytye.append(u'  id %d %s | метка %s | %s' % (e.Id.IntegerValue, imya(e), m_ or u'-', t))
            svodka[(vid, imya(e).split(u' : ')[0], m_[:6])] += 1
    log(u'висящие элементы сетей: проверено', len(elementy))
    for (vid, nm, m_), n in sorted(svodka.items(), key=lambda kv: -kv[1]):
        log(u'  %5d | %s | %s | %s' % (n, vid, nm, m_))
    log(u'без метки КВВ или без системы:', len(chuzhie))
    sv = collections.Counter(v.split(u' | ')[1].split(u' : ')[0] + u' | ' + v.split(u' | ')[-2].strip() +
                             (u' | БЕЗ СИСТЕМЫ' if u'БЕЗ СИСТЕМЫ' in v else u'') for v in chuzhie)
    for k_, n_ in sv.most_common(20):
        log(u'  %5d | %s' % (n_, k_))
    for v in chuzhie[:100]:
        log(v)
    log(u'открытые концы:', len(otkrytye))
    for v in otkrytye[:100]:
        log(v)
    log(u'касаются, но не соединены (первые 40 из %d):' % len(kasaetsya))
    for v in kasaetsya[:40]:
        log(v)


def fitingi(doc, log):
    """Фасонные части и арматура сетей: по семейству и типу — сколько, с какой меткой, габарит (мм) и точка первого
    экземпляра; отдельно — что стоит на стояках К1 ниже нуля (переход ПП — чугун)."""
    import collections
    M = kvv.M
    gr = collections.OrderedDict()
    for bic in (DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory):
        for e in DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
            k = (metka(e)[:6], e.Symbol.FamilyName, DB.Element.Name.GetValue(e.Symbol))
            gr.setdefault(k, []).append(e)
    for (m_, fam, tip), es in sorted(gr.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        e = es[0]
        bb = e.get_BoundingBox(None)
        if bb is not None:
            raz = u'%.0f x %.0f x %.0f' % ((bb.Max.X - bb.Min.X) / kvv.MM, (bb.Max.Y - bb.Min.Y) / kvv.MM,
                                          (bb.Max.Z - bb.Min.Z) / kvv.MM)
            c = (bb.Min + bb.Max).Multiply(0.5)
            t = u'(%.3f, %.3f, %.3f)' % (c.X / M, c.Y / M, c.Z / M)
        else:
            raz, t = u'-', u'-'
        try:
            pt = e.MEPModel.PartType
        except Exception:
            pt = u'-'
        n_w, prim = 0, u''
        for x in es:
            pw = x.LookupParameter(u'Warning')
            if pw is not None and pw.AsInteger() == 1:
                n_w += 1
                if not prim:
                    pn = x.LookupParameter(u'ADSK_Наименование')
                    pr_ = x.LookupParameter(u'Размер')
                    prim = u'%s | %s' % (pn.AsString() if pn is not None else u'-', pr_.AsString() if pr_ is not None else u'-')
        log(u'  %4d | %s | %s : %s | PartType %s | габарит %s мм | %s%s' % (
            len(es), m_ or u'-', fam, tip, pt, raz, t, u' | ШАР-ПРЕДУПРЕЖДЕНИЕ у %d: %s' % (n_w, prim) if n_w else u''))
        if False:
            for zag, el in ((u'экз', e), (u'тип', e.Symbol)):
                for pr in sorted(el.Parameters, key=lambda q: q.Definition.Name):
                    try:
                        v = pr.AsValueString() or pr.AsString() or u''
                    except Exception:
                        v = u'?'
                    log(u'       %s | %s = %s%s' % (zag, pr.Definition.Name, v, u' (ч)' if pr.IsReadOnly else u''))
            for c in e.MEPModel.ConnectorManager.Connectors:
                log(u'       соединитель: Ø%.1f мм, (%.3f, %.3f, %.3f)' % (c.Radius * 2 / kvv.MM, c.Origin.X / M,
                                                                       c.Origin.Y / M, c.Origin.Z / M))


def pribory_diag(doc, log):
    """По одному экземпляру каждого семейства сантехприборов: параметры экземпляра и типа (имя = значение), вложенные
    семейства с габаритом по Z относительно уровня — что торчит ниже пола."""
    M = kvv.M
    vidno = set()
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_PlumbingFixtures) \
            .WhereElementIsNotElementType():
        fam = e.Symbol.FamilyName
        if fam in vidno:
            continue
        vidno.add(fam)
        lv = doc.GetElement(e.LevelId)
        z0 = lv.Elevation if lv is not None else 0.0
        log(u'# %s : %s | уровень %s' % (fam, DB.Element.Name.GetValue(e.Symbol), lv.Name if lv else u'-'))
        for zag, el in ((u'экз', e), (u'тип', e.Symbol)):
            for pr in sorted(el.Parameters, key=lambda q: q.Definition.Name):
                try:
                    v = pr.AsValueString() or pr.AsString() or u''
                except Exception:
                    v = u'?'
                log(u'   %s | %s = %s%s' % (zag, pr.Definition.Name, v, u' (только чтение)' if pr.IsReadOnly else u''))
        for sid in e.GetSubComponentIds():
            se = doc.GetElement(sid)
            bb = se.get_BoundingBox(None)
            if bb is None:
                continue
            log(u'   вложенное: %s : %s | Z %.3f…%.3f м от уровня' % (
                se.Symbol.FamilyName, DB.Element.Name.GetValue(se.Symbol), (bb.Min.Z - z0) / M, (bb.Max.Z - z0) / M))


def proba_kombi(doc, log):
    """В откатываемой транзакции: кран VALTEC 1/2" и труба ППР Ø25 к его соединителю; для каждого типа муфт
    комбинированных — PartType, соединители семейства и попытка NewTransitionFitting с правилом этого типа."""
    M = kvv.M
    for sym in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_PipeFitting):
        if u'комбинированная' in sym.FamilyName:
            try:
                pt = sym.Family.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE).AsValueString()
            except Exception:
                pt = u'?'
            log(u'  тип:', sym.FamilyName, u':', DB.Element.Name.GetValue(sym), u'| PartType', pt)
    kran = [s_ for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
            if s_.FamilyName == u'VALTEC_VT.214.N_КранШаровой ВР' and DB.Element.Name.GetValue(s_) == u'1/2"']
    ppr = [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipeType)
           if DB.Element.Name.GetValue(t) == u'ADSK_Полипропилен_PN20']
    sist = [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystemType)]
    lv = [l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if l.Name == u'Подвал'][0]
    if not kran or not ppr:
        log(u'  нет крана или типа ППР')
        return
    sist_v = [t for t in sist if u'В1' in DB.Element.Name.GetValue(t)] or sist
    t = DB.Transaction(doc, u'проба муфты')
    t.Start()
    try:
        if not kran[0].IsActive:
            kran[0].Activate()
        P = kvv.xyz(-20.0, -20.0, lv.Elevation / M + 1.0)
        e = doc.Create.NewFamilyInstance(P, kran[0], lv, DB.Structure.StructuralType.NonStructural)
        doc.Regenerate()
        cs = list(e.MEPModel.ConnectorManager.Connectors)
        c = cs[0]
        log(u'  кран: соединитель Ø%.1f, тип соединения %s' % (c.Radius * 2 / kvv.MM, c.ConnectorType))
        o, z = c.Origin, c.CoordinateSystem.BasisZ
        tr = Plumbing.Pipe.Create(doc, sist_v[0].Id, ppr[0].Id, lv.Id, o + z.Multiply(0.3 * M), o)
        tr.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(25 * kvv.MM)
        doc.Regenerate()
        ct = [q for q in tr.ConnectorManager.Connectors if q.Origin.DistanceTo(o) < 1e-6][0]
        rpm = ppr[0].RoutingPreferenceManager
        gr = DB.RoutingPreferenceRuleGroupType.Transitions
        for sym in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_PipeFitting):
            if u'комбинированная' not in sym.FamilyName or u'25' not in DB.Element.Name.GetValue(sym):
                continue
            st = DB.SubTransaction(doc)
            st.Start()
            try:
                if not sym.IsActive:
                    sym.Activate()
                rpm.AddRule(gr, DB.RoutingPreferenceRule(sym.Id, u'проба'), 0)
                doc.Regenerate()
                f = doc.Create.NewTransitionFitting(ct, c)
                doc.Regenerate()
                pw = f.LookupParameter(u'Warning')
                log(u'  OK:', sym.FamilyName, DB.Element.Name.GetValue(sym), u'-> поставлен', f.Symbol.FamilyName,
                    DB.Element.Name.GetValue(f.Symbol), u'| Warning', pw.AsInteger() if pw else u'-')
            except Exception as ex:
                log(u'  НЕТ:', sym.FamilyName, DB.Element.Name.GetValue(sym), u'->', ex)
            finally:
                st.RollBack()
    finally:
        t.RollBack()


def vid_diag(doc, imya, log):
    """Элементы, видимые на виде imya: счёт по категориям и семействам; элементы сетей не своей системы —
    подробно (система, метка КВВ, точка в м)."""
    v = [x for x in DB.FilteredElementCollector(doc).OfClass(DB.View) if not x.IsTemplate and x.Name == imya]
    if not v:
        log(u'нет вида', imya)
        return
    v = v[0]
    svoya = u'В1' if imya.startswith(u'В1') else u'К1'
    po_kat = {}
    chuzhie = []
    for e in DB.FilteredElementCollector(doc, v.Id).WhereElementIsNotElementType():
        if e.Category is None:
            continue
        fam = getattr(getattr(e, 'Symbol', None), 'FamilyName', None) or e.GetType().Name
        k = (e.Category.Name, fam)
        po_kat[k] = po_kat.get(k, 0) + 1
        ps = e.get_Parameter(DB.BuiltInParameter.RBS_DUCT_PIPE_SYSTEM_ABBREVIATION_PARAM)
        sist = ps.AsString() if ps is not None and ps.HasValue else None
        pn = e.get_Parameter(DB.BuiltInParameter.RBS_SYSTEM_NAME_PARAM)
        imya_s = pn.AsString() if pn is not None and pn.HasValue else None
        mep = e.Category.Id.IntegerValue in (int(DB.BuiltInCategory.OST_PipeCurves),
                                              int(DB.BuiltInCategory.OST_PipeFitting),
                                              int(DB.BuiltInCategory.OST_PipeAccessory),
                                              int(DB.BuiltInCategory.OST_PlumbingFixtures),
                                              int(DB.BuiltInCategory.OST_MechanicalEquipment))
        if mep and svoya not in ((sist or u'') + (imya_s or u'')):
            bb = e.get_BoundingBox(None)
            c = (bb.Min + bb.Max).Multiply(0.5 / kvv.M) if bb is not None else None
            chuzhie.append((e.Category.Name, fam, sist, imya_s, metka(e), e.Id.IntegerValue, c))
    log(u'вид', imya, u'| видимых элементов по категориям и семействам:')
    for (kat, fam), n in sorted(po_kat.items()):
        log(u'  %s | %s : %d' % (kat, fam, n))
    log(u'элементов сетей не системы %s: %d' % (svoya, len(chuzhie)))
    for kat, fam, sist, imya_s, mt, i, c in sorted(chuzhie, key=lambda r: (r[1], r[5])):
        log(u'  ', kat, u'|', fam, u'| сист.', sist, imya_s, u'| метка', mt, u'| id', i,
            u'| (%.2f, %.2f, %.2f)' % (c.X, c.Y, c.Z) if c is not None else u'')


def soed_diag(doc, chasti, log):
    """Соединители семейств, в имени которых есть одна из chasti: для каждого типа — экземпляр в стороне (откат),
    соединители в локальных координатах экземпляра (мм), направление, диаметр, PartType, габарит."""
    import kvv_seti
    M, MM = kvv.M, kvv.MM
    lv = [l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if l.Name == u'Подвал'][0]
    # «часть@25» — после установки задать условный проход 25 мм (параметры с «иаметр»/«DN»/«Ду» в имени)
    dn = dict((ch.split(u'@')[0], float(ch.split(u'@')[1])) for ch in chasti if u'@' in ch)
    chasti = [ch.split(u'@')[0] for ch in chasti]
    simvoly = [s_ for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
               if any(ch in s_.FamilyName for ch in chasti)]
    log(u'типов найдено', len(simvoly), u'по', u' | '.join(chasti))
    t = DB.Transaction(doc, u'соединители')
    t.Start()
    try:
        for sym in sorted(simvoly, key=lambda x: (x.FamilyName, DB.Element.Name.GetValue(x))):
            try:
                pt = sym.Family.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE).AsValueString()
            except Exception:
                pt = u'-'
            try:
                e = kvv_seti.postavit(doc, sym, lv, -30.0, -30.0, lv.Elevation / M + 1.0, 0.0)
                doc.Regenerate()
                d_ = [v for k, v in dn.items() if k in sym.FamilyName]
                pars = []
                for el in (e, sym):
                    for pr in el.Parameters:
                        nm = pr.Definition.Name
                        if pr.StorageType == DB.StorageType.Double and any(w in nm for w in (u'иаметр', u'DN', u'Ду')):
                            if d_ and not pr.IsReadOnly and el is e:
                                try:
                                    pr.Set(d_[0] * MM)
                                except Exception:
                                    pass
                            pars.append(u'%s=%.0f%s' % (nm, pr.AsDouble() / MM, u'' if pr.IsReadOnly else u'*'))
                doc.Regenerate()
                log(u'    параметры:', u', '.join(pars))
                tr = e.GetTransform().Inverse
                cs = []
                for c in kvv_seti.soediniteli(e):
                    if c.Domain != DB.Domain.DomainPiping:
                        continue
                    o = tr.OfPoint(c.Origin)
                    d = tr.OfVector(c.CoordinateSystem.BasisZ)
                    cs.append(u'(%.0f, %.0f, %.0f) dir (%.0f, %.0f, %.0f) D%.1f' % (
                        o.X / MM, o.Y / MM, o.Z / MM, d.X, d.Y, d.Z, c.Radius * 2 / MM))
                bb = e.get_BoundingBox(None)
                gab = u'%.0f x %.0f x %.0f' % ((bb.Max.X - bb.Min.X) / MM, (bb.Max.Y - bb.Min.Y) / MM,
                                              (bb.Max.Z - bb.Min.Z) / MM) if bb else u'-'
                log(u'  %s : %s | %s | %s | %s' % (sym.FamilyName, DB.Element.Name.GetValue(sym), pt, gab,
                                                   u'; '.join(cs)))
            except Exception as ex:
                log(u'  %s : %s | не поставлен: %s' % (sym.FamilyName, DB.Element.Name.GetValue(sym), ex))
    finally:
        t.RollBack()


def vlozhennye(doc, app, imena, log):
    """Вложенные семейства и флаги («Всегда вертикально», «На основе рабочей плоскости») у семейств проекта imena —
    почему экземпляр нельзя повернуть на вертикаль."""
    for fam in [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name in imena]:
        fd = doc.EditFamily(fam)
        try:
            def flagi(f):
                return u', '.join(u'%s=%s' % (q.Definition.Name, q.AsValueString()) for q in f.Parameters
                                 if q.StorageType == DB.StorageType.Integer and (u'ертикал' in q.Definition.Name or
                                                                                 u'плоскост' in q.Definition.Name))
            log(fam.Name, u':', flagi(fd.OwnerFamily))
            for f2 in DB.FilteredElementCollector(fd).OfClass(DB.Family):
                if f2.Id == fd.OwnerFamily.Id:
                    continue
                n = len([e for e in DB.FilteredElementCollector(fd).OfClass(DB.FamilyInstance)
                         if e.Symbol.Family.Id == f2.Id])
                log(u'   вложено:', f2.Name, u'| экз.', n, u'|', flagi(f2), u'| категория',
                    f2.FamilyCategory.Name if f2.FamilyCategory else u'-')
        finally:
            fd.Close(False)


def perepodklyuchit(doc, log, metka_=u'КВВ-В1'):
    """Разорвать и заново соединить все стыки сети в своей транзакции (с фиксацией): Revit сливает системы при
    фиксации транзакции (опыт 29.10), а сборка 05 оставила В1 в 1547 системах."""
    def cm_(e):
        if isinstance(e, (Plumbing.Pipe, Plumbing.FlexPipe)):
            return e.ConnectorManager
        mm = getattr(e, 'MEPModel', None)
        return mm.ConnectorManager if mm is not None else None
    pary = []
    kat = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_FlexPipeCurves,
           DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory)
    for k in kat:
        for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
            if not (metka(e) or u'').startswith(metka_):
                continue
            cm = cm_(e)
            if cm is None:
                continue
            for c in cm.Connectors:
                if c.Domain != DB.Domain.DomainPiping or not c.IsConnected:
                    continue
                for r in c.AllRefs:
                    if r.Owner is None or r.Owner.Id == e.Id or r.Domain != DB.Domain.DomainPiping:
                        continue
                    if r.ConnectorType not in (DB.ConnectorType.End, DB.ConnectorType.Curve):
                        continue
                    if e.Id.IntegerValue < r.Owner.Id.IntegerValue or not (metka(r.Owner) or u'').startswith(metka_):
                        pary.append((c, r))
    tr = DB.Transaction(doc, u'КВВ: переподключить стыки ' + metka_)
    tr.Start()
    n_ok, n_osh = 0, 0
    for c, r in pary:
        try:
            c.DisconnectFrom(r)
            c.ConnectTo(r)
            n_ok += 1
        except Exception:
            n_osh += 1
    tr.Commit()
    log(u'переподключено стыков %d из %d | ошибок %d' % (n_ok, len(pary), n_osh))


def udalit_sistemy(doc, log, tip=u'ADSK_Водопровод_В1'):
    """Удалить все системы типа tip в транзакции с фиксацией: Revit при фиксации заново создаёт системы по связным
    сетям (попытка собрать В1, разбитую на 1547 систем, в одну)."""
    ids = []
    for s_ in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystem):
        t = doc.GetElement(s_.GetTypeId())
        if t is not None and DB.Element.Name.GetValue(t) == tip:
            ids.append(s_.Id)
    tr = DB.Transaction(doc, u'КВВ: удалить системы ' + tip)
    tr.Start()
    doc.Delete(List[DB.ElementId](ids))
    tr.Commit()
    bez = sum(1 for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)
              if p.MEPSystem is None and (metka(p) or u'').startswith(u'КВВ-В1'))
    log(u'удалено систем %d | труб В1 без системы после фиксации %d' % (len(ids), bez))


def naznachit_sistemu(doc, log, tip=u'ADSK_Водопровод_В1', metka_=u'КВВ-В1'):
    """Трубам сети без системы задать тип системы заново (SetSystemType) — по одной трубе на транзакцию, пока есть
    трубы без системы: Revit при фиксации относит к системе всю связную сеть. Пустые системы (опыт) — удалить."""
    t_ = [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystemType)
          if DB.Element.Name.GetValue(t) == tip][0]
    pustye = [s_.Id for s_ in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystem)
              if s_.PipingNetwork is None or s_.PipingNetwork.Size == 0]
    if pustye:
        tr = DB.Transaction(doc, u'КВВ: удалить пустые системы')
        tr.Start()
        doc.Delete(List[DB.ElementId](pustye))
        tr.Commit()
    log(u'удалено пустых систем', len(pustye))
    shag = 0
    while shag < 200:
        bez = [p for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)
               if p.MEPSystem is None and (metka(p) or u'').startswith(metka_)]
        if not bez:
            break
        tr = DB.Transaction(doc, u'КВВ: тип системы ' + tip)
        tr.Start()
        bez[0].SetSystemType(t_.Id)
        tr.Commit()
        shag += 1
    ost = sum(1 for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)
              if p.MEPSystem is None and (metka(p) or u'').startswith(metka_))
    log(u'шагов (труб, которым задан тип) %d | труб без системы осталось %d' % (shag, ost))


def sobrat_sistemu(doc, log, tip=u'ADSK_Водопровод_В1', imya=u'В1'):
    """Одна система сети: (1) удалить все системы типа tip — фиксация; (2) новая система PipingSystem.Create и в неё
    холодные соединители всех приборов и оборудования (как «Создать систему» в Revit) — фиксация. Revit относит к
    системе связную сеть между ними."""
    t_ = [t for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipingSystemType)
          if DB.Element.Name.GetValue(t) == tip][0]
    udalit_sistemy(doc, log, tip)
    cs, n = DB.ConnectorSet(), 0
    for k in (DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_MechanicalEquipment):
        for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
            mm = getattr(e, 'MEPModel', None)
            if mm is None or mm.ConnectorManager is None:
                continue
            for c in mm.ConnectorManager.Connectors:
                if c.Domain == DB.Domain.DomainPiping and c.PipeSystemType == Plumbing.PipeSystemType.DomesticColdWater                         and c.MEPSystem is None:
                    cs.Insert(c)
                    n += 1
    tr = DB.Transaction(doc, u'КВВ: одна система ' + imya)
    tr.Start()
    try:
        ps = Plumbing.PipingSystem.Create(doc, t_.Id, imya)
        ps.Add(cs)
        tr.Commit()
        log(u'система %s создана: соединителей приборов и оборудования %d' % (imya, n))
    except Exception as ex:
        tr.RollBack()
        log(u'система не создана:', ex)
    bez = sum(1 for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)
              if p.MEPSystem is None and (metka(p) or u'').startswith(u'КВВ-В1'))
    log(u'труб В1 без системы после сборки системы %d' % bez)


def modul_semeystva(doc, app, zapros, log):
    """«файл модуля; слово1, слово2» — семейства и типы модуля ADSK из папки «Семейства ВК/Системы трубопроводов»,
    в имени которых есть одно из слов (модуль открывается в фоне и закрывается без сохранения)."""
    import os
    chasti = [x.strip() for x in zapros.split(u';')]
    put = os.path.join(kvv.SEMEYSTVA, u'Системы трубопроводов', chasti[0])
    slova = [w.strip().lower() for w in (chasti[1] if len(chasti) > 1 else u'').split(u',') if w.strip()]
    d2 = app.OpenDocumentFile(put)
    try:
        imena = set()
        for s_ in DB.FilteredElementCollector(d2).OfClass(DB.FamilySymbol):
            nm = s_.FamilyName + u' : ' + DB.Element.Name.GetValue(s_)
            if not slova or any(w in nm.lower() for w in slova):
                imena.add(nm)
        log(u'модуль', chasti[0], u'| найдено', len(imena))
        for nm in sorted(imena):
            log(u'  ' + nm)
    finally:
        d2.Close(False)


def vid_uzla(doc, uidoc, zapros, log):
    """«x y z0 z1 [r [fx fy]]» (м, z — от нуля здания; fx fy — направление взгляда в плане) — 3D-вид «КВВ_3D_Узел» с рамкой вокруг точки (полуширина r, по
    умолчанию 0,5 м), «Высокая» детализация, тонированный, делается активным — для осмотра узла."""
    ch = [float(v.replace(u',', u'.')) for v in zapros.split()]
    x, y, z0, z1 = ch[:4]
    r = ch[4] if len(ch) > 4 else 0.5
    M = kvv.M
    tr = DB.Transaction(doc, u'КВВ: 3D-вид узла')
    tr.Start()
    stare = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D) if v.Name == u'КВВ_3D_Узел']
    vft = [t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
           if t.ViewFamily == DB.ViewFamily.ThreeDimensional][0]
    if stare:
        v = doc.GetElement(stare[0])             # открытый вид удалить нельзя — обновить на месте
    else:
        v = DB.View3D.CreateIsometric(doc, vft.Id)
        v.Name = u'КВВ_3D_Узел'
    try:
        v.ViewTemplateId = DB.ElementId.InvalidElementId
    except Exception:
        pass
    bb = DB.BoundingBoxXYZ()
    bb.Min = DB.XYZ((x - r) * M, (y - r) * M, z0 * M)
    bb.Max = DB.XYZ((x + r) * M, (y + r) * M, z1 * M)
    v.SetSectionBox(bb)
    v.DetailLevel = DB.ViewDetailLevel.Fine
    v.DisplayStyle = DB.DisplayStyle.ShadingWithEdges
    v.Scale = 10
    if len(ch) > 6:
        # взгляд вдоль (fx, fy) чуть сверху — «как на фото»: из помещения на шахту
        fx, fy = ch[5], ch[6]
        c = DB.XYZ(x * M, y * M, (z0 + z1) / 2 * M)
        fw = DB.XYZ(fx, fy, -0.25).Normalize()
        up = DB.XYZ(-fw.X * fw.Z, -fw.Y * fw.Z, 1 - fw.Z * fw.Z).Normalize()
        v.SetOrientation(DB.ViewOrientation3D(c - fw.Multiply(20 * M), up, fw))
    for bic in (DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_Levels,
                DB.BuiltInCategory.OST_Grids, DB.BuiltInCategory.OST_Doors, DB.BuiltInCategory.OST_Windows):
        try:
            v.SetCategoryHidden(DB.ElementId(bic), True)
        except Exception:
            pass
    # окраска сетей — как на «КВВ_3D_Здание и сети»: В1 синим, К1 коричневым
    zaliv = _sploshnaya_zalivka(doc)
    for f, cvet in [(_filtr_sistemy(doc, u'КВВ_3D_В1', u'КВВ-В1'), DB.Color(0, 127, 255)),
                    (_filtr_sistemy(doc, u'КВВ_3D_К1', u'КВВ-К1'), DB.Color(165, 41, 0))]:
        if not v.IsFilterApplied(f.Id):
            v.AddFilter(f.Id)
        o = DB.OverrideGraphicSettings()
        o.SetProjectionLineColor(cvet)
        o.SetSurfaceForegroundPatternColor(cvet)
        if zaliv != DB.ElementId.InvalidElementId:
            o.SetSurfaceForegroundPatternId(zaliv)
        v.SetFilterOverrides(f.Id, o)
    tr.Commit()
    uidoc.ActiveView = v
    log(u'вид КВВ_3D_Узел: x %.2f y %.2f z %.2f…%.2f r %.2f' % (x, y, z0, z1, r))


def proba_flex(doc, log, d_mm=20.0):
    """Опыт (откат): гибкой подводке задать диаметр d_mm — остаётся ли она присоединённой к водорозетке и смесителю
    (их резьба 1/2")."""
    fp = [f for f in DB.FilteredElementCollector(doc).OfClass(Plumbing.FlexPipe)][:3]
    tr = DB.Transaction(doc, u'КВВ: опыт диаметра подводки')
    tr.Start()
    try:
        for f in fp:
            p_ = f.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
            d0 = p_.AsDouble() / kvv.MM
            try:
                p_.Set(d_mm * kvv.MM)
                doc.Regenerate()
                sost = [(c.IsConnected, round(c.Radius * 2 / kvv.MM, 1)) for c in f.ConnectorManager.Connectors]
                sos = [(round(r.Radius * 2 / kvv.MM, 1), r.Owner.Name) for c in f.ConnectorManager.Connectors
                       for r in c.AllRefs if r.Owner.Id != f.Id]
                log(u'  подводка %d: было %.0f мм, стало %.0f | соединители %s | соседи %s'
                    % (f.Id.IntegerValue, d0, p_.AsDouble() / kvv.MM, sost, sos))
            except Exception as ex:
                log(u'  подводка %d: не задаётся %.0f мм: %s' % (f.Id.IntegerValue, d_mm, ex))
    finally:
        tr.RollBack()
        log(u'опыт откатан')


def tochka_sistemy(doc, zapros, log):
    """«x y z r» — элементы сетей в радиусе r (м) от точки: семейство, у каждого соединителя — класс, система,
    соединён ли и с кем (семейство и система соседа). Чтобы найти, где рвётся система."""
    x, y, z, r = [float(v.replace(u',', u'.')) for v in zapros.split()]
    M = kvv.M
    P = DB.XYZ(x * M, y * M, z * M)

    def soed(e):
        if isinstance(e, (Plumbing.Pipe, Plumbing.FlexPipe)):
            return list(e.ConnectorManager.Connectors)
        mm = getattr(e, 'MEPModel', None)
        if mm is None or mm.ConnectorManager is None:
            return []
        return [c for c in mm.ConnectorManager.Connectors if c.Domain == DB.Domain.DomainPiping]

    def sist(c):
        try:
            return c.MEPSystem.Name if c.MEPSystem is not None else u'(нет)'
        except Exception:
            return u'(ош)'
    kat = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_FlexPipeCurves, DB.BuiltInCategory.OST_PipeFitting,
           DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_PlumbingFixtures)
    for k in kat:
        for e in DB.FilteredElementCollector(doc).OfCategory(k).WhereElementIsNotElementType():
            cs = soed(e)
            if not cs or min(c.Origin.DistanceTo(P) for c in cs) > r * M:
                continue
            nm = e.Symbol.FamilyName if isinstance(e, DB.FamilyInstance) else e.GetType().Name
            chasti = []
            for c in cs:
                sos = [(r_.Owner.Symbol.FamilyName if isinstance(r_.Owner, DB.FamilyInstance) else r_.Owner.GetType().Name)
                       + u' ' + sist(r_) for r_ in c.AllRefs if r_.Owner.Id != e.Id and r_.Domain == DB.Domain.DomainPiping]
                try:
                    kl = unicode(c.PipeSystemType)
                except Exception:
                    kl = u'?'
                chasti.append(u'[%s %s z=%.3f -> %s]' % (kl, sist(c), c.Origin.Z / M, u', '.join(sos) or u'-'))
            log(u'%s %d: %s' % (nm, e.Id.IntegerValue, u' '.join(chasti)))


def klassy_soediniteley(doc, imena, log):
    """Классы систем соединителей в семействах (открываются для чтения): почему система не проходит через деталь."""
    for f in DB.FilteredElementCollector(doc).OfClass(DB.Family):
        if f.Name not in imena:
            continue
        fd = doc.EditFamily(f)
        try:
            ce = list(DB.FilteredElementCollector(fd).OfClass(DB.ConnectorElement))
            log(u'семейство %s: категория %s | соединителей %d' % (f.Name, f.FamilyCategory.Name if f.FamilyCategory else u'-', len(ce)))
            for c in ce:
                try:
                    kl = unicode(c.SystemClassification)
                except Exception as ex:
                    kl = u'? ' + unicode(ex)
                log(u'   соединитель %d: класс %s | домен %s' % (c.Id.IntegerValue, kl, c.Domain))
            try:
                pt = fd.OwnerFamily.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE)
                log(u'   PartType:', pt.AsValueString() if pt else u'-')
            except Exception:
                pass
        finally:
            fd.Close(False)


def fasad(doc, log, e_=0.09, b_=12.8):
    """Наружные стены по фасадам: по каждому уровню — стены на линиях фасадов (y = −E, y = B+E, x = −E, x = L+E),
    их длина, низ и верх по габариту (м), привязки; окна и двери на этих стенах; стены, скрытые на 3D-видах."""
    vidy3d = [v for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D) if not v.IsTemplate]
    steny = list(DB.FilteredElementCollector(doc).OfClass(DB.Wall))
    xs = []
    for w in steny:
        lc = getattr(w.Location, 'Curve', None)
        if lc is not None:
            xs += [lc.GetEndPoint(0).X / kvv.M, lc.GetEndPoint(1).X / kvv.M]
    x_max = max(xs)
    linii = {u'А (y=-E)': ('y', -e_), u'Д (y=B+E)': ('y', b_ + e_), u'торец 1 (x=-E)': ('x', -e_),
             u'торец 22 (x=max)': ('x', x_max)}
    log(u'x наибольшая по стенам: %.3f' % x_max)
    po = {}
    for w in steny:
        lc = getattr(w.Location, 'Curve', None)
        if lc is None:
            continue
        a, b = lc.GetEndPoint(0), lc.GetEndPoint(1)
        for nm, (os_, v) in linii.items():
            ka, kb = (a.Y, b.Y) if os_ == 'y' else (a.X, b.X)
            if abs(ka / kvv.M - v) < 0.02 and abs(kb / kvv.M - v) < 0.02:
                try:
                    ur = DB.Element.Name.GetValue(doc.GetElement(w.LevelId))
                except Exception:
                    ur = u'?'
                bb = w.get_BoundingBox(None)
                skr = [v3.Name for v3 in vidy3d if w.IsHidden(v3)]
                po.setdefault((nm, ur), []).append(
                    (w.Id.IntegerValue, DB.Element.Name.GetValue(w.WallType), round(lc.Length / kvv.M, 3),
                     round(bb.Min.Z / kvv.M, 3) if bb else None, round(bb.Max.Z / kvv.M, 3) if bb else None,
                     sorted(set([round(min(a.X, b.X) / kvv.M, 2), round(max(a.X, b.X) / kvv.M, 2)])) if os_ == 'y'
                     else sorted(set([round(min(a.Y, b.Y) / kvv.M, 2), round(max(a.Y, b.Y) / kvv.M, 2)])), skr))
    for (nm, ur), ws in sorted(po.items()):
        log(u'%s | %s | стен %d | длина %.2f' % (nm, ur, len(ws), sum(x[2] for x in ws)))
        for x in ws:
            log(u'   id %d | %s | L %.2f | z %s…%s | %s%s' % (x[0], x[1], x[2], x[3], x[4], x[5],
                                                         (u' | СКРЫТА на ' + u', '.join(x[6])) if x[6] else u''))
    # окна и двери: хост и уровень
    for kat in (DB.BuiltInCategory.OST_Windows, DB.BuiltInCategory.OST_Doors):
        n, bez = 0, []
        for e in DB.FilteredElementCollector(doc).OfCategory(kat).WhereElementIsNotElementType():
            if getattr(e, 'SuperComponent', None) is not None:
                continue                     # вложенные части семейств (створки, подоконники) — основы нет
            n += 1
            if e.Host is None:
                bez.append(e.Id.IntegerValue)
        log(kat, u'всего (без вложенных)', n, u'без основы', len(bez), bez[:20])
    # скрытые на 3D-видах элементы архитектуры
    for v3 in vidy3d:
        skr = {}
        for kat in (DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_Windows, DB.BuiltInCategory.OST_Doors,
                    DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_Roofs):
            for e in DB.FilteredElementCollector(doc).OfCategory(kat).WhereElementIsNotElementType():
                if e.IsHidden(v3):
                    skr[str(kat)] = skr.get(str(kat), 0) + 1
                    if kat == DB.BuiltInCategory.OST_Walls:
                        lc_ = getattr(e.Location, 'Curve', None)
                        try:
                            ur_ = DB.Element.Name.GetValue(doc.GetElement(e.LevelId))
                        except Exception:
                            ur_ = u'?'
                        log(u'   вид', v3.Name, u'| скрыта стена', e.Id.IntegerValue, ur_,
                            DB.Element.Name.GetValue(e.WallType), u'| %.2f,%.2f → %.2f,%.2f' % (
                                lc_.GetEndPoint(0).X / kvv.M, lc_.GetEndPoint(0).Y / kvv.M,
                                lc_.GetEndPoint(1).X / kvv.M, lc_.GetEndPoint(1).Y / kvv.M) if lc_ else u'')
            try:
                if v3.GetCategoryHidden(DB.ElementId(kat)):
                    skr[str(kat) + u' (категория)'] = 1
            except Exception:
                pass
        if skr:
            log(u'вид 3D', v3.Name, u'| скрыто:', skr, u'| разрез. рамка', v3.IsSectionBoxActive)


def snimok(doc, zapros, log):
    """«snimok <имя вида>; <файл .png>; [пикселей]» — картинка вида (ExportImage) для осмотра без экрана."""
    chasti = [x.strip() for x in zapros.split(u';')]
    imya, put = chasti[0], chasti[1]
    px = int(chasti[2]) if len(chasti) > 2 and chasti[2] else 1600
    v = [x for x in DB.FilteredElementCollector(doc).OfClass(DB.View) if not x.IsTemplate and x.Name == imya]
    if not v:
        log(u'нет вида', imya)
        return
    o = DB.ImageExportOptions()
    o.ExportRange = DB.ExportRange.SetOfViews
    o.SetViewsAndSheets(List[DB.ElementId]([v[0].Id]))
    o.FilePath = put
    o.ZoomType = DB.ZoomFitType.FitToPage
    o.FitDirection = DB.FitDirectionType.Horizontal
    o.PixelSize = px
    o.ImageResolution = DB.ImageResolution.DPI_150
    o.HLRandWFViewsFileType = DB.ImageFileType.PNG
    o.ShadowViewsFileType = DB.ImageFileType.PNG
    doc.ExportImage(o)
    log(u'снимок вида', imya, u'->', put)


def topo_tochki(doc, zapros, log):
    """«topo x0 y0 x1 y1» — вершины граней топотела (земли) в прямоугольнике плана, м: где поверхность проседает."""
    x0, y0, x1, y1 = [float(v) for v in zapros.split()]
    kat = getattr(DB.BuiltInCategory, 'OST_Toposolid')
    o = DB.Options()
    o.DetailLevel = DB.ViewDetailLevel.Fine
    for e in DB.FilteredElementCollector(doc).OfCategory(kat).WhereElementIsNotElementType():
        vers = set()
        for g in e.get_Geometry(o):
            if not isinstance(g, DB.Solid):
                continue
            for f in g.Faces:
                n = f.ComputeNormal(DB.UV(0.5, 0.5))
                m = f.Triangulate()
                for i in range(m.Vertices.Count):
                    p = m.Vertices[i]
                    x, y, z = p.X / kvv.M, p.Y / kvv.M, p.Z / kvv.M
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        vers.add((round(x, 2), round(y, 2), round(z, 3), round(n.Z, 2)))
        log(u'топотело', e.Id.IntegerValue, u'| вершин в области', len(vers))
        verh = [v for v in vers if v[3] > 0.01]
        log(u"   верх: z от %.3f до %.3f" % (min(v[2] for v in verh), max(v[2] for v in verh)) if verh else u"   верха нет")
        for v in sorted(vers, key=lambda t: t[2])[:40]:
            log(u'   x %.2f y %.2f z %.3f | нормаль z %.2f' % v)


def seti_na_vidah(doc, log):
    """По 3D-видам: сколько элементов В1 и К1 (по метке) скрыто на виде по одному, скрыты ли категории сетей."""
    po_metke = {}
    for e in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        m = metka(e)
        if m and (m.startswith(u'КВВ-В1') or m.startswith(u'КВВ-К1')):
            po_metke.setdefault(m[:6], []).append(e)
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
        if v.IsTemplate:
            continue
        skr = dict((k, sum(1 for e in es if e.IsHidden(v))) for k, es in po_metke.items())
        vidno = {}
        for e in DB.FilteredElementCollector(doc, v.Id).OfCategory(DB.BuiltInCategory.OST_PipeCurves):
            m = metka(e)[:6]
            vidno[m] = vidno.get(m, 0) + 1
        filtry = []
        for fid in v.GetFilters():
            f = doc.GetElement(fid)
            filtry.append(u'%s%s' % (f.Name, u'' if v.GetFilterVisibility(fid) else u' (СКРЫВАЕТ)'))
        log(u'   %s: видимых труб по меткам %s | фильтры: %s' % (v.Name, u', '.join(
            u'%s %d' % kv for kv in sorted(vidno.items())), u'; '.join(filtry)))
        kat = [doc.Settings.Categories.get_Item(c).Name for c in KAT_SETI
               if v.GetCategoryHidden(DB.ElementId(c))]
        log(u'%s | всего %s | скрыто по одному %s | скрытые категории %s | шаблон %s | рамка %s' % (
            v.Name, u', '.join(u'%s %d' % (k, len(es)) for k, es in sorted(po_metke.items())),
            u', '.join(u'%s %d' % kv for kv in sorted(skr.items())), u', '.join(kat),
            v.ViewTemplateId.IntegerValue, v.IsSectionBoxActive))
