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


# ---------------- переходы у водомерного узла ----------------
def _truby_v_tochke(doc, p, metka_=u'КВВ-В1'):
    out = []
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        if not metka(t).startswith(metka_):
            continue
        for c in t.ConnectorManager.Connectors:
            if c.Origin.DistanceTo(p) < 0.03 * M:
                out.append((t, c))
    return out


def _imya(s):
    return u'%s : %s' % (s.FamilyName, DB.Element.Name.GetValue(s))


def proba_perehodov(doc, log, tochki=((4.0, 2.35, -2.0), (4.0, 2.85, -2.0))):
    """Почему не встаёт переход 50/25 у счётчика: правила переходов в типе трубы и проба каждого семейства
    перехода проекта (в транзакции с откатом — модель не меняется)."""
    gr = DB.RoutingPreferenceRuleGroupType.Transitions
    kand = []
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(
            DB.BuiltInCategory.OST_PipeFitting):
        try:
            pt = s.Family.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE).AsInteger()
        except Exception:
            continue
        if pt == int(DB.PartType.Transition):
            kand.append(s)
    log(u'семейств переходов в проекте:', len(kand), u'—', u'; '.join(_imya(s) for s in kand))
    # всё В1 у водомерного узла: соединители (точка, DN, с кем соединён)
    ol = DB.Outline(DB.XYZ(3.5 * M, 1.5 * M, -2.5 * M), DB.XYZ(4.5 * M, 3.5 * M, -1.5 * M))
    for e in DB.FilteredElementCollector(doc).WherePasses(DB.BoundingBoxIntersectsFilter(ol)) \
            .WhereElementIsNotElementType():
        if not metka(e).startswith(u'КВВ-В1'):
            continue
        cm = e.ConnectorManager if isinstance(e, Plumbing.Pipe) else getattr(getattr(e, 'MEPModel', None),
                                                                              'ConnectorManager', None)
        if cm is None:
            continue
        opis = []
        for c in cm.Connectors:
            o = c.Origin
            sv = [r.Owner.Id.IntegerValue for r in c.AllRefs if r.Owner.Id != e.Id]
            opis.append(u'(%.3f, %.3f, %.3f) DN%.0f -> %s' % (o.X / M, o.Y / M, o.Z / M, c.Radius * 2 / MM,
                                                             sv or u'—'))
        log(u'  %d %s %s: %s' % (e.Id.IntegerValue, e.Category.Name, e.Name, u' | '.join(opis)))
    # проба на месте счётчика: трубе DN25 вернуть длину 2,35…2,85, соседней DN50 — конец 2,35, и пробовать переход
    d25 = [t for t in DB.FilteredElementCollector(doc, ).OfClass(Plumbing.Pipe)
           if metka(t).startswith(u'КВВ-В1') and abs(t.Diameter / MM - 25) < 1
           and t.get_BoundingBox(None) is not None and ol.Contains(t.get_BoundingBox(None).Min, 0)]
    for t25 in d25:
        for s in kand:
            t = DB.Transaction(doc, u'КВВ: проба перехода')
            t.Start()
            try:
                if not s.IsActive:
                    s.Activate()
                sosedi = []
                for c in t25.ConnectorManager.Connectors:
                    for r in list(c.AllRefs):
                        if r.Owner.Id != t25.Id:
                            sosedi.append(r.Owner)
                            c.DisconnectFrom(r)
                a = t25.Location.Curve.GetEndPoint(0)
                y0 = 2.35 * M
                t25.Location.Curve = DB.Line.CreateBound(DB.XYZ(a.X, y0, a.Z), DB.XYZ(a.X, 2.85 * M, a.Z))
                t50 = [q for q in sosedi if isinstance(q, Plumbing.Pipe) and q.Location.Curve.GetEndPoint(0).Y < y0]
                for q in t50:
                    c0 = q.Location.Curve.GetEndPoint(0)
                    q.Location.Curve = DB.Line.CreateBound(c0, DB.XYZ(c0.X, y0, c0.Z))
                m = t25.PipeType.RoutingPreferenceManager
                m.AddRule(gr, DB.RoutingPreferenceRule(s.Id, u'проба'), 0)
                doc.Regenerate()
                c1 = [c for c in t25.ConnectorManager.Connectors if abs(c.Origin.Y - y0) < 0.01 * M][0]
                c2 = [c for c in t50[0].ConnectorManager.Connectors if abs(c.Origin.Y - y0) < 0.01 * M][0]
                f = doc.Create.NewTransitionFitting(c2, c1)
                log(u'   переход 50/25 ВСТАЁТ:', _imya(s), u'| id', f.Id.IntegerValue)
            except Exception as ex:
                log(u'   переход 50/25 нет:', _imya(s), u'—', unicode(ex).split(u'\n')[0][:150])
            finally:
                t.RollBack()
    for x, y, z in tochki:
        p = DB.XYZ(x * M, y * M, z * M)
        tr = _truby_v_tochke(doc, p)
        log(u'точка (%.2f, %.2f, %.2f): труб %d —' % (x, y, z, len(tr)),
            u'; '.join(u'%s DN%.0f' % (DB.Element.Name.GetValue(t.PipeType), c.Radius * 2 / MM) for t, c in tr))
        if len(tr) != 2:
            continue
        rpm = tr[0][0].PipeType.RoutingPreferenceManager
        for i in range(rpm.GetNumberOfRules(gr)):
            r = rpm.GetRule(gr, i)
            s = doc.GetElement(r.MEPPartId)
            kr = []
            for j in range(r.NumberOfCriteria):
                c = r.GetCriterion(j)
                try:
                    kr.append(u'DN %.0f…%.0f' % (c.MinimumSize / MM, c.MaximumSize / MM))
                except Exception:
                    pass
            log(u'   правило перехода %d: %s %s' % (i, _imya(s) if s else u'?', u', '.join(kr)))
        for s in kand:
            t = DB.Transaction(doc, u'КВВ: проба перехода')
            t.Start()
            try:
                if not s.IsActive:
                    s.Activate()
                    doc.Regenerate()
                for tt in set(q[0].PipeType.Id.IntegerValue for q in tr):
                    m = doc.GetElement(DB.ElementId(tt)).RoutingPreferenceManager
                    m.AddRule(gr, DB.RoutingPreferenceRule(s.Id, u'проба'), 0)
                doc.Regenerate()
                (t1, c1), (t2, c2) = _truby_v_tochke(doc, p)
                if c1.IsConnectedTo(c2):
                    c1.DisconnectFrom(c2)
                f = doc.Create.NewTransitionFitting(c1, c2)
                log(u'   ВСТАЁТ:', _imya(s), u'| id', f.Id.IntegerValue)
            except Exception as ex:
                log(u'   нет:', _imya(s), u'—', unicode(ex).split(u'\n')[0][:120])
            finally:
                t.RollBack()
