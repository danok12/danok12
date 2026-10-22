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
