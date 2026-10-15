# -*- coding: utf-8 -*-
"""Санитарные приборы во всех квартирах, насосная установка, противопожарные муфты на стояках К1.

revit/04_rezhim.txt = «mufty» — только переставить противопожарные муфты по geometriya_v3.json (приборы и трубы
не трогаются) и проверить модель: муфты на стояках, уклоны горизонтальных труб К1, верх стояков над кровлей,
квартирные счётчики В1, видимость семейства муфты на схеме.
"""
import io
import math
import os
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
from System.Collections.Generic import List
import kvv
import kvv_seti
reload(kvv)
reload(kvv_seti)

doc = HOST_APP.doc
M = kvv.M
MM = kvv.MM
SHEMA_V1, SHEMA_K1 = u'В1_Аксонометрическая схема', u'К1_Аксонометрическая схема'


def rezhim_zapuska():
    """revit/04_rezhim.txt: «mufty» — только муфты и проверки. Файл после чтения удаляется."""
    put = os.path.join(kvv.REVIT, u'04_rezhim.txt')
    if not os.path.isfile(put):
        return u''
    with io.open(put, encoding='utf-8') as f:
        r = f.read().strip()
    os.remove(put)
    return r


def komment(e):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    return (p.AsString() or u'') if p is not None and p.HasValue else u''


def vid(nm):
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if not v.IsTemplate and v.Name == nm:
            return v
    return None


def vidimost_semeystva(log):
    """Что из геометрии семейства муфты видно при грубой / средней / высокой детализации."""
    sym = kvv.simvol(doc, u'ADSK_Противопожарная муфта')
    fam = sym.Family
    log(u'семейство', fam.Name, u'| категория', fam.FamilyCategory.Name if fam.FamilyCategory else u'-')
    fdoc = doc.EditFamily(fam)
    try:
        for cls in (DB.GenericForm, DB.CurveElement, DB.FamilyInstance, DB.ImportInstance):
            for e in DB.FilteredElementCollector(fdoc).OfClass(cls):
                try:
                    vis = e.GetVisibility()
                    s = u'груб %s сред %s выс %s' % (vis.IsShownInCoarse, vis.IsShownInMedium, vis.IsShownInFine)
                except Exception as ex:
                    s = u'видимость: %s' % ex
                bb = e.get_BoundingBox(None)
                r = u''
                if bb is not None:
                    r = u'габарит, мм: x %.0f…%.0f y %.0f…%.0f z %.0f…%.0f' % (
                        bb.Min.X / MM, bb.Max.X / MM, bb.Min.Y / MM, bb.Max.Y / MM, bb.Min.Z / MM, bb.Max.Z / MM)
                log(u'   ', e.GetType().Name, s, r)
    finally:
        fdoc.Close(False)


def proverka(log, mufty):
    truby = [e for e in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe) if komment(e).startswith(u'КВВ-К1')]
    vert, gor = [], []
    for t in truby:
        c = t.Location.Curve
        a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        d = t.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).AsDouble() / MM
        h = math.hypot(b.X - a.X, b.Y - a.Y) / M
        if h < 0.001:
            vert.append((a.X / M, a.Y / M, min(a.Z, b.Z) / M, max(a.Z, b.Z) / M, d))
        else:
            gor.append((abs(b.Z - a.Z) / M / h, h, d, t.ReferenceLevel.Name, a, b))
    log(u'труб К1: вертикальных', len(vert), u'| горизонтальных и наклонных', len(gor))
    # муфты на стояках
    ok, plohie = 0, []
    for e in mufty:
        bb = e.get_BoundingBox(None)
        p = e.Location.Point
        st = [v for v in vert if math.hypot(v[0] - p.X / M, v[1] - p.Y / M) < 0.002
              and v[2] - 1e-4 <= bb.Min.Z / M and bb.Max.Z / M <= v[3] + 1e-4]
        if st:
            ok += 1
        else:
            plohie.append(u'(%.3f, %.3f, %.3f…%.3f)' % (p.X / M, p.Y / M, bb.Min.Z / M, bb.Max.Z / M))
    if mufty:
        bb = mufty[0].get_BoundingBox(None)
        log(u'муфта: габарит %.0f x %.0f x %.0f мм, низ %.3f верх %.3f (первая)' % (
            (bb.Max.X - bb.Min.X) / MM, (bb.Max.Y - bb.Min.Y) / MM, (bb.Max.Z - bb.Min.Z) / MM, bb.Min.Z / M,
            bb.Max.Z / M))
    log(u'муфт на стояках', ok, u'из', len(mufty), u'| мимо стояка:', u' '.join(plohie[:10]))
    # уклоны
    po_d = {}
    for s, h, d, ur, a, b in gor:
        k = (int(round(d)), u'подвал' if ur == u'Подвал' else u'этажи')
        po_d.setdefault(k, []).append(s)
    for k in sorted(po_d):
        v = po_d[k]
        log(u'уклоны К1 d %d (%s): %d труб, i от %.4f до %.4f' % (k[0], k[1], len(v), min(v), max(v)))
    plosk = [g for g in gor if g[0] < 0.005 and g[1] > 0.02]
    log(u'горизонтальных труб К1 без уклона (i < 0,005, L > 20 мм):', len(plosk))
    for s, h, d, ur, a, b in plosk[:15]:
        log(u'   d %d L %.3f i %.4f (%.3f, %.3f, %.3f)-(%.3f, %.3f, %.3f) %s' % (
            d, h, s, a.X / M, a.Y / M, a.Z / M, b.X / M, b.Y / M, b.Z / M, ur))
    # верх стояков и кровля
    lv = kvv.urovni(doc)
    z_kr = lv[u'Кровля'].Elevation / M
    pokr = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Floor) if f.LevelId == lv[u'Кровля'].Id]
    verh_pl = [f.get_BoundingBox(None).Max.Z / M for f in pokr]
    log(u'уровень «Кровля» %.3f | плит покрытия %d, верх плит: %s' % (
        z_kr, len(pokr), u', '.join(u'%.3f' % z for z in verh_pl)))
    verh = {}
    for x, y, z0, z1, d in vert:
        k = (round(x, 3), round(y, 3))
        if d > 100 and z1 > verh.get(k, -1e9):
            verh[k] = z1
    for k in sorted(verh):
        log(u'   стояк К1 (%.3f, %.3f): верх %.3f, над кровлей %.3f м' % (k[0], k[1], verh[k],
                                                                         verh[k] - max(verh_pl or [z_kr])))
    # квартирные узлы учёта В1
    arm = [e for e in DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance)
           if komment(e).startswith(u'КВВ-В1') and e.Symbol is not None]
    sch = [e for e in arm if e.Symbol.FamilyName == u'Квартирный счетчик воды_Пульсар']
    reg = [e for e in arm if u'Редуктор' in e.Symbol.FamilyName]
    log(u'квартирных счётчиков В1', len(sch), u'| регуляторов давления', len(reg))
    for nm in (SHEMA_V1, SHEMA_K1):
        v = vid(nm)
        if v is not None:
            log(u'вид', nm, u'| детализация', v.DetailLevel, u'| арматура скрыта:',
                v.GetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_PipeAccessory)))
            vidno = set(e.Id.IntegerValue for e in DB.FilteredElementCollector(doc, v.Id)
                        .OfCategory(DB.BuiltInCategory.OST_PipeAccessory).WhereElementIsNotElementType())
            log(u'   муфт в выборке вида:', sum(1 for e in mufty if e.Id.IntegerValue in vidno),
                u'| скрыта ли первая:', mufty[0].IsHidden(v) if mufty else u'-')
            for fid in v.GetFilters():
                f = doc.GetElement(fid)
                log(u'   фильтр', f.Name, u'| виден', v.GetFilterVisibility(fid), u'| включён',
                    v.GetIsFilterEnabled(fid) if hasattr(v, 'GetIsFilterEnabled') else u'-')


def tolko_mufty(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    vidimost_semeystva(log)
    with kvv.Tranzakciya(doc, u'КВВ: противопожарные муфты', log):
        kvv_seti.udalit(doc, u'КВВ-М', log)
        s = kvv_seti.Stroitel(doc, g, log)
        mufty = s.mufty()
        v = vid(SHEMA_V1)
        if v is not None and mufty:
            v.HideElements(List[DB.ElementId]([e.Id for e in mufty if e.CanBeHidden(v)]))
            log(u'муфты скрыты на виде', SHEMA_V1)
        v = vid(SHEMA_K1)
        if v is not None:
            kvv.armatura_detalno(doc, v, log)
    proverka(log, mufty)


def main(log):
    if rezhim_zapuska() == u'mufty':
        tolko_mufty(log)
        return
    g = kvv.load_json('revit', 'geometriya_v3.json')
    with kvv.Tranzakciya(doc, u'КВВ: приборы', log):
        for pref in (u'КВВ-П', u'КВВ-О', u'КВВ-М'):
            kvv_seti.udalit(doc, pref, log)
        s = kvv_seti.Stroitel(doc, g, log)
        s.pribory()
        s.otchet()


kvv.run('04_pribory', main)
