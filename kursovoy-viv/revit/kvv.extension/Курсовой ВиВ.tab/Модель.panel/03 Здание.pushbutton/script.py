# -*- coding: utf-8 -*-
"""Уровни, оси, стены, двери, окна, перекрытия с отверстиями, покрытие и лестницы по revit/geometriya_v3.json.

Перед перестройкой удаляются сети и приборы (метки КВВ-П/О/М/В1/К1) — после 03 запускать 04, 05, 06.

Повторный запуск удаляет построенное этим скриптом (метка «КВВ-здание» в «Комментариях») и строит заново.
"""
import io
import os
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Architecture as A
import System
from System.Collections.Generic import List
import kvv
reload(kvv)

doc = HOST_APP.doc
M = kvv.M
METKA = u'КВВ-здание'
METKA_Z = u'КВВ-земля'          # земля, крыльца, приямки (режим zemlya)
TOLSH = {u'nar': 0.58, u'fund': 0.316, u'nes': 0.25, u'per': 0.10, u'beton': 0.20, u'korob': 0.05}   # как в geometriya_v3.py


def pometit(e):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p and not p.IsReadOnly:
        p.Set(METKA)


def udalit_seti(log):
    """Перед перестройкой здания убрать сети и приборы (кнопки 04–06 строят их заново): иначе Revit не может
    сохранить присоединение приборов к трубам при удалении перекрытий."""
    ids = []
    for e in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        except Exception:
            continue
        if p is not None and p.HasValue:
            s_ = p.AsString() or u''
            if s_.startswith(u'КВВ-') and s_ not in (METKA, METKA_Z):
                ids.append(e.Id)
    if ids:
        doc.Delete(List[DB.ElementId](ids))
    log(u'удалено сетей и приборов (перестроить кнопками 04–06)', len(ids))


def udalit_staroe(log):
    ids = []
    for cls in (DB.Wall, DB.Floor, DB.FootPrintRoof, DB.FamilyInstance, A.Stairs, A.Railing):
        for e in DB.FilteredElementCollector(doc).OfClass(cls).WhereElementIsNotElementType():
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and p.AsString() == METKA:
                ids.append(e.Id)
    if ids:
        doc.Delete(List[DB.ElementId](ids))
    log(u'удалено старых элементов', len(ids))


def urovni_osi(g, log):
    lv = kvv.urovni(doc)
    for u in g['urovni']:
        if u['imya'] in lv:
            lv[u['imya']].Elevation = u['z'] * M
            continue
        l = DB.Level.Create(doc, u['z'] * M)
        l.Name = u['imya']
        lv[u['imya']] = l
    log(u'уровней', len(lv))
    est = dict((gr.Name, gr) for gr in DB.FilteredElementCollector(doc).OfClass(DB.Grid))
    n = 0
    for o in g['osi']:
        line = DB.Line.CreateBound(kvv.xyz(*o['p1']), kvv.xyz(*o['p2']))
        if o['imya'] in est:
            gr = est[o['imya']]
            if gr.Curve.Distance(line.GetEndPoint(0)) < 1e-6 and gr.Curve.Distance(line.GetEndPoint(1)) < 1e-6:
                continue
            doc.Delete(gr.Id)
        gr = DB.Grid.Create(doc, line)
        gr.Name = o['imya']
        n += 1
    log(u'осей создано/обновлено', n)
    return lv


def tip_korob(tipy, log):
    korob = kvv.po_imeni(doc, DB.WallType, tipy['korob'])
    if korob is None:
        per = kvv.po_imeni(doc, DB.WallType, tipy['per'])
        korob = per.Duplicate(tipy['korob'])
        cs = korob.GetCompoundStructure()
        tot = sum(cs.GetLayerWidth(i) for i in range(cs.LayerCount))
        for i in range(cs.LayerCount):
            cs.SetLayerWidth(i, cs.GetLayerWidth(i) * 50 * kvv.MM / tot)
        korob.SetCompoundStructure(cs)
        log(u'создан тип стены', tipy['korob'])


def steny(g, lv, log, tolko=None):
    tipy = g['tipy']
    tip_korob(tipy, log)
    imena = [u['imya'] for u in sorted(g['urovni'], key=lambda u: u['z'])]
    etazhi = [u for u in imena if u.startswith(u'Этаж')]
    sozd = []            # (уровень, стена, p1, p2, толщина)
    for s in g['steny']:
        if tolko is not None and s['gde'] not in (u'podval', u'vse', tolko):
            continue
        wt = kvv.po_imeni(doc, DB.WallType, tipy[s['tip']])
        if wt is None:
            log(u'НЕТ типа стены', tipy[s['tip']])
            continue
        gde = []
        if s['gde'] in (u'etazhi', u'vse'):
            gde += etazhi
        if s['gde'] in (u'podval', u'vse'):
            gde.append(u'Подвал')
        if s['gde'] in imena:                 # стена только на одном уровне (например, «Этаж 01»)
            gde.append(s['gde'])
        if tolko is not None:
            gde = [u for u in gde if u == tolko]
        line = DB.Line.CreateBound(kvv.xyz(*s['p1']), kvv.xyz(*s['p2']))
        for u in gde:
            niz, verh = lv[u], lv[imena[imena.index(u) + 1]]
            w = DB.Wall.Create(doc, line, wt.Id, niz.Id, verh.Elevation - niz.Elevation, 0.0, False, False)
            w.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).Set(verh.Id)
            w.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM).Set(0)
            pometit(w)
            sozd.append((u, w, s['p1'], s['p2'], TOLSH[s['tip']]))
    log(u'стен создано', len(sozd))
    return sozd


def najti_stenu(sozd, u, x, y):
    best = None
    for (uu, w, p1, p2, t) in sozd:
        if uu != u:
            continue
        (x1, y1), (x2, y2) = p1, p2
        if abs(y1 - y2) < 1e-9:
            if min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and abs(y - y1) <= t / 2 + 1e-3:
                best = w
        elif min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6 and abs(x - x1) <= t / 2 + 1e-3:
            best = w
    return best


def proemy(g, lv, sozd, log, tolko=None):
    etazhi = [u['imya'] for u in g['urovni'] if u['imya'].startswith(u'Этаж')]
    n, net = 0, 0
    razvorot = []                 # (дверь, куда открывается)
    for o, is_okno in [(o, True) for o in g['okna']] + [(d, False) for d in g['dveri']]:
        if tolko is not None and o['gde'] != tolko:
            continue
        fam, tip = o['tip']
        sym = kvv.simvol(doc, fam, tip)
        if sym is None:
            log(u'НЕТ семейства', fam, tip)
            continue
        if o['gde'] == u'etazhi':
            gde = etazhi
        elif o['gde'] == u'verh':
            gde = etazhi[1:]
        else:
            gde = [o['gde']]
        for u in gde:
            w = najti_stenu(sozd, u, o['x'], o['y'])
            if w is None:
                net += 1
                continue
            pod = o.get('podokonnik', 0.0) if is_okno else 0.0
            ot = o.get('otkr') if (not is_okno and fam.startswith(u'AC_')) else None
            sdv = (ot[0] * 0.03, ot[1] * 0.03) if ot else (0.0, 0.0)   # точка со стороны открывания — дверь лицом туда
            p = DB.XYZ((o['x'] + sdv[0]) * M, (o['y'] + sdv[1]) * M, lv[u].Elevation + pod * M)
            e = doc.Create.NewFamilyInstance(p, sym, w, lv[u], DB.Structure.StructuralType.NonStructural)
            if is_okno:
                par = e.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if par and not par.IsReadOnly:
                    par.Set(pod * M)
            pometit(e)
            if o.get('otkr') and fam.startswith(u'AC_'):     # балконные B2B ориентируются по наружной грани сами
                razvorot.append((e, o['otkr']))
            n += 1
    log(u'окон и дверей', n, u'| без стены-основы:', net)



def kontur(pts):
    cl = DB.CurveLoop()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        cl.Append(DB.Line.CreateBound(kvv.xyz(*a), kvv.xyz(*b)))
    return cl


def perekrytiya(g, lv, log):
    tipy = g['tipy']
    n = 0
    for p in g['perekr']:
        ft = kvv.po_imeni(doc, DB.FloorType, tipy[p['tip']])
        loops = [kontur(p['kontur'])]
        for poly in p.get('otverstiya', []):
            loops.append(kontur(poly))
        f = DB.Floor.Create(doc, List[DB.CurveLoop](loops), ft.Id, lv[p['uroven']].Id)
        pometit(f)
        n += 1
    log(u'перекрытий', n)
    ft = kvv.po_imeni(doc, DB.FloorType, tipy['perekr'])
    kr = g['krovlya'] if isinstance(g['krovlya'], list) else [g['krovlya']]     # по секциям (деформационный шов)
    for k in kr:
        f = DB.Floor.Create(doc, List[DB.CurveLoop]([kontur(k['kontur'])]), ft.Id, lv[k['uroven']].Id)
        pometit(f)
    log(u'плит покрытия на уровне', kr[0]['uroven'], len(kr))


class Glush(DB.IFailuresPreprocessor):
    def PreprocessFailures(self, fa):
        for f in fa.GetFailureMessages():
            if f.GetSeverity() == DB.FailureSeverity.Warning:
                fa.DeleteWarning(f)
        return DB.FailureProcessingResult.Continue


def lestnicy(g, lv, log):
    etazhi = sorted([u for u in g['urovni'] if u['imya'].startswith(u'Этаж')], key=lambda u: u['z'])
    rail_t = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.StairsRailingType)
    n, oshibki = 0, []
    for L in g['lestnicy']:
        for i in range(len(etazhi) - 1):
            niz, verh = lv[etazhi[i]['imya']], lv[etazhi[i + 1]['imya']]
            scope = DB.StairsEditScope(doc, u'КВВ: лестница')
            try:
                sid = scope.Start(niz.Id, verh.Id)
                t = DB.Transaction(doc, u'КВВ: марши')
                t.Start()
                st = doc.GetElement(sid)
                par = st.get_Parameter(DB.BuiltInParameter.STAIRS_DESIRED_NUMBER_OF_RISERS)
                if par and not par.IsReadOnly:
                    par.Set(18)
                z0 = niz.Elevation
                m1, m2 = L['m1'], L['m2']
                l1 = DB.Line.CreateBound(DB.XYZ(m1['p1'][0] * M, m1['p1'][1] * M, z0),
                                         DB.XYZ(m1['p2'][0] * M, m1['p2'][1] * M, z0))
                r1 = A.StairsRun.CreateStraightRun(doc, sid, l1, A.StairsRunJustification.Center)
                r1.ActualRunWidth = m1['shir'] * M
                z1 = z0 + r1.TopElevation
                l2 = DB.Line.CreateBound(DB.XYZ(m2['p1'][0] * M, m2['p1'][1] * M, z1),
                                         DB.XYZ(m2['p2'][0] * M, m2['p2'][1] * M, z1))
                r2 = A.StairsRun.CreateStraightRun(doc, sid, l2, A.StairsRunJustification.Center)
                r2.ActualRunWidth = m2['shir'] * M
                A.StairsLanding.CreateAutomaticLanding(doc, r1.Id, r2.Id)
                pometit(st)
                t.Commit()
                scope.Commit(Glush())
                n += 1
                try:
                    tr = DB.Transaction(doc, u'КВВ: ограждение')
                    tr.Start()
                    for rid in A.Railing.Create(doc, sid, rail_t, A.RailingPlacementPosition.Treads):
                        pometit(doc.GetElement(rid))
                    tr.Commit()
                except Exception as ex:
                    if tr.HasStarted() and not tr.HasEnded():
                        tr.RollBack()
                    oshibki.append(u'ограждение: %s' % ex)
            except Exception as ex:
                oshibki.append(unicode(ex))
                try:
                    scope.Cancel()
                except Exception:
                    pass
    log(u'лестниц (поэтажных) создано', n)
    for o in sorted(set(oshibki)):
        log(u'  ошибка лестницы:', o)


def obyom(w):
    p = w.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED)
    return p.AsDouble() if p else 0.0


class ZagruzkaSemeystva(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True


def strelki_razvorota(g, log):
    """В семействах дверей AC нет стрелки разворота (CanFlipFacing = False) — добавить двойную вертикальную стрелку
    в плане семейства (как вручную в редакторе) и перезагрузить семейство. Вне транзакции."""
    imena = set(o['tip'][0] for o in g['dveri'] if o['tip'][0].startswith(u'AC_'))
    log(u'формы стрелок:', u', '.join(System.Enum.GetNames(DB.ControlShape)))
    semeystva = [(f.Name, f.Id) for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name in imena]
    for imya, fid in semeystva:
        fam = doc.GetElement(fid)
        fd = doc.EditFamily(fam)
        try:
            est = [c for c in DB.FilteredElementCollector(fd).OfClass(DB.Control)]
            formy = [c.Shape for c in est]
            if DB.ControlShape.DoubleVerticalArrow in formy:
                log(u'стрелка разворота уже есть:', imya)
                continue
            vid = [v for v in DB.FilteredElementCollector(fd).OfClass(DB.ViewPlan) if not v.IsTemplate][0]
            t = DB.Transaction(fd, u'стрелка разворота')
            t.Start()
            try:
                fd.FamilyCreate.NewControl(DB.ControlShape.DoubleVerticalArrow, vid, DB.XYZ(0, 0.6 / 0.3048, 0))
                t.Commit()
            except Exception:
                t.RollBack()
                raise
            fd.LoadFamily(doc, ZagruzkaSemeystva())
            log(u'добавлена стрелка разворота и семейство перезагружено:', imya)
        finally:
            try:
                fd.Close(False)
            except Exception:
                pass


def razvernut_dveri(g, log):
    """Полотно открывается в сторону FacingOrientation (проверено по габариту семейств AC_Дверь). Отдельной
    транзакцией после фиксации проёмов."""
    nado = [(o['x'], o['y'], o['otkr']) for o in g['dveri'] if o.get('otkr') and o['tip'][0].startswith(u'AC_')]
    n, nf, nelzya = 0, 0, 0
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType():
        p = e.Location.Point
        ot = None
        for x, y, o in nado:
            if abs(p.X / M - x) < 0.05 and abs(p.Y / M - y) < 0.05:
                ot = o
                break
        if ot is None:
            continue
        n += 1
        f = e.FacingOrientation
        if f.X * ot[0] + f.Y * ot[1] >= 0:
            continue
        if e.CanFlipFacing:
            e.flipFacing()
            nf += 1
        else:
            nelzya += 1
    log(u'открывание дверей: всего', n, u'| развёрнуто', nf, u'| нельзя развернуть', nelzya)


def proverka_proemov(log, n_prob=30):
    """Выборочно (откат): удалить проём — объём стены должен вырасти, значит проём был вырезан."""
    vse = []
    for bic in (DB.BuiltInCategory.OST_Doors, DB.BuiltInCategory.OST_Windows):
        for e in DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and p.AsString() == METKA and isinstance(e.Host, DB.Wall):
                vse.append(e)
    shag = max(1, len(vse) // n_prob)
    proba = vse[::shag]
    t = DB.Transaction(doc, u'проверка проёмов')
    t.Start()
    ne_vyrezany = []
    try:
        for e in proba:
            w = e.Host
            v0 = obyom(w)
            opis = u'%s %s (%.2f, %.2f) %s' % (e.Symbol.FamilyName, e.Name, e.Location.Point.X / M,
                                               e.Location.Point.Y / M, doc.GetElement(e.LevelId).Name)
            doc.Delete(e.Id)
            doc.Regenerate()
            if obyom(w) - v0 < 1e-6:
                ne_vyrezany.append(opis)
    finally:
        t.RollBack()
    log(u'проверка проёмов: из', len(proba), u'проверенных не вырезано', len(ne_vyrezany))
    for o in ne_vyrezany:
        log(u'  проём НЕ вырезан:', o)


def udalit_uroven(lv, uroven, log):
    """Стены, двери и окна здания (метка КВВ-здание) одного уровня — для перестройки только подвала."""
    lid = lv[uroven].Id
    ids = []
    for cls in (DB.Wall, DB.FamilyInstance):
        for e in DB.FilteredElementCollector(doc).OfClass(cls).WhereElementIsNotElementType():
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and p.AsString() == METKA and e.LevelId == lid:
                ids.append(e.Id)
    if ids:
        doc.Delete(List[DB.ElementId](ids))
    log(u'удалено стен, дверей и окон уровня', uroven, len(ids))


def soedinit_steny(log):
    """Стыки стен — сплошным телом: касающиеся стены одного уровня соединяются (JoinGeometry); у стен одного
    материала линия стыка на плане пропадает, у разных материалов остаётся граница (как положено)."""
    po_ur = {}
    for w in DB.FilteredElementCollector(doc).OfClass(DB.Wall).WhereElementIsNotElementType():
        p = w.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p and p.AsString() == METKA:
            bb = w.get_BoundingBox(None)
            if bb is not None:
                po_ur.setdefault(w.LevelId.IntegerValue, []).append((w, bb))
    d = 0.02 * M
    n, osh = 0, 0
    for spisok in po_ur.values():
        for i in range(len(spisok)):
            a, ba = spisok[i]
            for j in range(i + 1, len(spisok)):
                b, bb = spisok[j]
                if ba.Max.X + d < bb.Min.X or bb.Max.X + d < ba.Min.X or ba.Max.Y + d < bb.Min.Y \
                        or bb.Max.Y + d < ba.Min.Y:
                    continue
                if DB.JoinGeometryUtils.AreElementsJoined(doc, a, b):
                    continue
                try:
                    DB.JoinGeometryUtils.JoinGeometry(doc, a, b)
                    n += 1
                except Exception:
                    osh += 1
    log(u'стыки стен: соединено пар', n, u'| не соединилось', osh)


# ---------------- земля, крыльца, приямки (режим zemlya) ----------------
# 30.10, замечание «почему двери на втором этаже»: без земли подвал стоял над землёй целиком. Земля — по рельефу
# генплана (genplan/genplan_v3.json, блок zemlya: сетка отметок, отверстие под здание и приямки, крыльца, приямки).
VID_FASAD = u'КВВ_3D_Фасад'
VID_VHOD = u'КВВ_3D_Вход'                 # вход в подъезд и приямок секции 1 крупно


def pometit_z(e):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p and not p.IsReadOnly:
        p.Set(METKA_Z)


def udalit_zemlyu(log):
    ids = []
    for e in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        except Exception:
            continue
        if p is not None and p.HasValue and p.AsString() == METKA_Z:
            ids.append(e.Id)
    if ids:
        doc.Delete(List[DB.ElementId](ids))
    log(u'удалено элементов земли, крылец и приямков', len(ids))


def tip_grunta(log, tolsh=1.0):
    """Тип земли толщиной 1,0 м: низ топотела — на 1,0 м ниже уровня «Этаж 01» (−1,000), ниже самой низкой
    отметки рельефа (−0,67) и выше секущей плоскости плана подвала (−1,8) — на планах земли нет."""
    imya = u'КВВ_Грунт_1000'
    tipy = list(DB.FilteredElementCollector(doc).OfClass(DB.ToposolidType))
    for t in tipy:
        if DB.Element.Name.GetValue(t) == imya:
            return t
    t = tipy[0].Duplicate(imya)
    cs = t.GetCompoundStructure()            # слои типа — пропорционально до 1,0 м (новая структура не подходит:
    vse = sum(cs.GetLayerWidth(i) for i in range(cs.LayerCount))       # у земли своё условие торцов)
    for i in range(cs.LayerCount):
        cs.SetLayerWidth(i, cs.GetLayerWidth(i) * tolsh * M / vse)
    t.SetCompoundStructure(cs)
    log(u'создан тип земли', imya, u'толщиной', tolsh)
    return t


def pryamoug(x0, y0, x1, y1):
    return kontur([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def plita(ft, lv_, x0, y0, x1, y1, verh):
    """Плита (крыльцо, ступень, дно приямка): верх на verh (м) от уровня lv_."""
    f = DB.Floor.Create(doc, List[DB.CurveLoop]([pryamoug(x0, y0, x1, y1)]), ft.Id, lv_.Id)
    f.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).Set(verh * M)
    pometit_z(f)
    return f


def zemlya(g, gp, lv, log):
    z = gp['zemlya']
    l1, lp = lv[u'Этаж 01'], lv[u'Подвал']
    tt = tip_grunta(log)
    x0, y0, x1, y1 = z['granica']
    loops = List[DB.CurveLoop]([pryamoug(x0, y0, x1, y1), kontur(z['otverstie'])])
    pts = List[DB.XYZ]([DB.XYZ(x * M, y * M, h * M) for x, y, h in z['tochki']])
    ts = DB.Toposolid.Create(doc, loops, pts, tt.Id, l1.Id)
    pometit_z(ts)
    log(u'земля: точек', len(z['tochki']), u'| отметки %.2f…%.2f' % (z['zeml_min'], z['zeml_max']))
    ft = kvv.po_imeni(doc, DB.FloorType, g['tipy']['pol_podv'])
    for k in z['kryltsa']:
        plita(ft, l1, k['x0'], k['y0'], k['x1'], k['y1'], k['verh'])
        for s_ in k['stupeni']:
            plita(ft, l1, k['x0'], s_['y0'], k['x1'], s_['y1'], s_['verh'])
        log(u'крыльцо x %.2f…%.2f: верх %.3f, земля %.3f, подступенков %d по %.3f' % (
            k['x0'], k['x1'], k['verh'], k['zeml'], k['n_podst'], k['h_podst']))
    wt = kvv.po_imeni(doc, DB.WallType, g['tipy']['beton'])
    for p in z['priyamki']:
        xa, xb = p['x'] - p['shir'] / 2, p['x'] + p['shir'] / 2
        plita(ft, lp, xa, p['y_kon'], xb, p['y_stena'], 0.0)
        for xs in (xa - p['t_st'] / 2, xb + p['t_st'] / 2):
            line = DB.Line.CreateBound(kvv.xyz(xs, p['y_stena']), kvv.xyz(xs, p['y_kon']))
            w = DB.Wall.Create(doc, line, wt.Id, lp.Id, (p['verh_sten'] - p['z_niz']) * M, 0.0, False, False)
            w.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM).Set(0)
            pometit_z(w)
        log(u'приямок x %.2f: земля %.3f, подступенков %d по %.3f, марш %.2f м' % (
            p['x'], p['zeml'], p['n_podst'], p['h_podst'], p['y_marsh0'] - p['y_marsh1']))


def marshi_priyamkov(gp, lv, log):
    """Марш в приямке: от уровня подвала до земли (верх лестницы — смещение от «Этаж 01»)."""
    l1, lp = lv[u'Этаж 01'], lv[u'Подвал']
    for p in gp['zemlya']['priyamki']:
        scope = DB.StairsEditScope(doc, u'КВВ: марш приямка')
        try:
            sid = scope.Start(lp.Id, l1.Id)
            t = DB.Transaction(doc, u'КВВ: марш приямка')
            t.Start()
            st = doc.GetElement(sid)
            st.get_Parameter(DB.BuiltInParameter.STAIRS_TOP_OFFSET).Set(p['zeml'] * M)
            for bip, v in ((DB.BuiltInParameter.STAIRS_DESIRED_NUMBER_OF_RISERS, p['n_podst']),
                           (DB.BuiltInParameter.STAIRS_ACTUAL_TREAD_DEPTH, p['stupen'] * M)):
                par = st.get_Parameter(bip)
                if par is not None and not par.IsReadOnly:
                    par.Set(v)
            z0 = lp.Elevation
            line = DB.Line.CreateBound(DB.XYZ(p['x'] * M, p['y_marsh0'] * M, z0),
                                       DB.XYZ(p['x'] * M, p['y_marsh1'] * M, z0))
            r = A.StairsRun.CreateStraightRun(doc, sid, line, A.StairsRunJustification.Center)
            r.ActualRunWidth = (p['shir'] - 0.10) * M        # косоуры (по 50 мм) — внутри приямка
            pometit_z(st)
            t.Commit()
            scope.Commit(Glush())
            st = doc.GetElement(sid)
            log(u'марш приямка x %.2f: подступенков %s, высота %.3f, проступь %.3f' % (
                p['x'], st.ActualRisersNumber, st.Height / M, st.ActualTreadDepth / M))
            bb = st.get_BoundingBox(None)
            log(u'   габарит марша: x %.2f…%.2f, y %.2f…%.2f, z %.2f…%.2f' % (
                bb.Min.X / M, bb.Max.X / M, bb.Min.Y / M, bb.Max.Y / M, bb.Min.Z / M, bb.Max.Z / M))
            for rid in st.GetAssociatedRailings():
                rl = doc.GetElement(rid)
                rb = rl.get_BoundingBox(None)
                log(u'   ограждение %d: x %.2f…%.2f, y %.2f…%.2f, z %.2f…%.2f' % (
                    rid.IntegerValue, rb.Min.X / M, rb.Max.X / M, rb.Min.Y / M, rb.Max.Y / M, rb.Min.Z / M,
                    rb.Max.Z / M))
        except Exception as ex:
            log(u'ОШИБКА марша приямка:', ex)
            try:
                scope.Cancel()
            except Exception:
                pass


def vid_fasada(log, imya=VID_FASAD, ramka=None, glaz=(70, -45, 30), cel=(22.6, 6.4, 8)):
    """3D-вид фасада по оси А с юго-востока: здание с землёй, крыльцами и приямками (для осмотра). ramka —
    (x0, y0, z0, x1, y1, z1) секущего параллелепипеда, м (вид входа крупно)."""
    v = None
    for e in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
        if not e.IsTemplate and e.Name == imya:
            v = e
    if v is None:
        vft = [t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
               if t.ViewFamily == DB.ViewFamily.ThreeDimensional][0]
        v = DB.View3D.CreateIsometric(doc, vft.Id)
        v.Name = imya
    v.ViewTemplateId = DB.ElementId.InvalidElementId
    if v.IsLocked:
        v.Unlock()
    v.IsSectionBoxActive = False
    if ramka is not None:
        sb = DB.BoundingBoxXYZ()
        sb.Min = DB.XYZ(ramka[0] * M, ramka[1] * M, ramka[2] * M)
        sb.Max = DB.XYZ(ramka[3] * M, ramka[4] * M, ramka[5] * M)
        v.IsSectionBoxActive = True
        v.SetSectionBox(sb)
    for bic in (DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_Grids, DB.BuiltInCategory.OST_SectionBox):
        cid = DB.ElementId(bic)
        if v.CanCategoryBeHidden(cid):
            v.SetCategoryHidden(cid, True)
    v.DisplayStyle = DB.DisplayStyle.ShadingWithEdges
    v.DetailLevel = DB.ViewDetailLevel.Medium
    glaz = DB.XYZ(glaz[0] * M, glaz[1] * M, glaz[2] * M)
    cel = DB.XYZ(cel[0] * M, cel[1] * M, cel[2] * M)
    vpered = (cel - glaz).Normalize()
    vverh = vpered.CrossProduct(DB.XYZ.BasisZ).CrossProduct(vpered).Normalize()
    v.SetOrientation(DB.ViewOrientation3D(glaz, vverh, vpered))
    for p in v.Parameters:
        nm = p.Definition.Name
        if p.StorageType == DB.StorageType.String and not p.IsReadOnly:
            if u'Назначение' in nm:
                p.Set(u'Вспомогательные виды')
            elif u'Раздел' in nm:
                p.Set(u'3D для осмотра')
    log(u'вид', imya)
    return v


def rezhim_zemlya(g, log):
    gp = kvv.load_json('genplan', 'genplan_v3.json')
    lv = kvv.urovni(doc)
    with kvv.Tranzakciya(doc, u'КВВ: земля, крыльца, приямки', log):
        udalit_zemlyu(log)
        zemlya(g, gp, lv, log)
    marshi_priyamkov(gp, lv, log)
    with kvv.Tranzakciya(doc, u'КВВ: вид фасада', log):
        v = vid_fasada(log)
        k = gp['zemlya']['kryltsa'][0]
        xc = (k['x0'] + k['x1']) / 2 + 1.5
        vid_fasada(log, VID_VHOD, (k['x0'] - 1.5, -8.0, -3.6, k['x1'] + 4.5, 2.0, 4.0),
                   glaz=(xc + 9.0, -16.0, 10.0), cel=(xc, -2.0, -1.0))
    try:
        HOST_APP.uidoc.ActiveView = v
    except Exception as ex:
        log(u'вид фасада не открыт:', ex)


def rezhim_zapuska():
    """revit/03_rezhim.txt: «podval» — перестроить только подвал (стены и двери) и соединить стыки стен;
    «styki» — только соединить стыки; «zemlya» — только земля, крыльца и приямки (сети не трогаются);
    иначе — всё здание. Файл после чтения удаляется."""
    put = os.path.join(kvv.REVIT, u'03_rezhim.txt')
    if not os.path.isfile(put):
        return u''
    with io.open(put, encoding='utf-8') as f:
        r = f.read().strip()
    os.remove(put)
    return r


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    rezhim = rezhim_zapuska()
    if rezhim == u'zemlya':
        rezhim_zemlya(g, log)
        return
    if rezhim in (u'podval', u'styki'):
        log(u'режим:', rezhim)
        lv = kvv.urovni(doc)
        if rezhim == u'podval':
            with kvv.Tranzakciya(doc, u'КВВ: подвал', log):
                udalit_uroven(lv, u'Подвал', log)
                doc.Regenerate()
                sozd = steny(g, lv, log, tolko=u'Подвал')
            sozd = [(u, doc.GetElement(w.Id), p1, p2, t) for (u, w, p1, p2, t) in sozd]
            with kvv.Tranzakciya(doc, u'КВВ: проёмы подвала', log):
                proemy(g, lv, sozd, log, tolko=u'Подвал')
            with kvv.Tranzakciya(doc, u'КВВ: открывание дверей', log):
                razvernut_dveri(g, log)
            with kvv.Tranzakciya(doc, u'КВВ: проверка открывания', log):
                razvernut_dveri(g, log)
            proverka_proemov(log)
        with kvv.Tranzakciya(doc, u'КВВ: стыки стен', log):
            soedinit_steny(log)
        return
    try:
        strelki_razvorota(g, log)
    except Exception as ex:
        log(u'стрелки разворота не добавлены:', ex)
    # стены и перекрытия фиксируются отдельно: проёмы, созданные в той же транзакции, Revit не врезает
    with kvv.Tranzakciya(doc, u'КВВ: удаление сетей', log):
        udalit_seti(log)
    with kvv.Tranzakciya(doc, u'КВВ: здание', log):
        udalit_staroe(log)
        lv = urovni_osi(g, log)
        doc.Regenerate()
        sozd = steny(g, lv, log)
        perekrytiya(g, lv, log)
    lv = kvv.urovni(doc)
    sozd = [(u, doc.GetElement(w.Id), p1, p2, t) for (u, w, p1, p2, t) in sozd]
    with kvv.Tranzakciya(doc, u'КВВ: проёмы', log):
        proemy(g, lv, sozd, log)
    with kvv.Tranzakciya(doc, u'КВВ: открывание дверей', log):
        razvernut_dveri(g, log)
    with kvv.Tranzakciya(doc, u'КВВ: проверка открывания', log):
        razvernut_dveri(g, log)          # повторно: должно быть «исправлено 0, не исправлено 0»
    proverka_proemov(log)
    lestnicy(g, lv, log)
    with kvv.Tranzakciya(doc, u'КВВ: стыки стен', log):
        soedinit_steny(log)
    rezhim_zemlya(g, log)


kvv.run('03_zdanie', main)
