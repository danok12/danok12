# -*- coding: utf-8 -*-
"""Уровни, оси, стены, двери, окна, перекрытия с отверстиями, покрытие и лестницы по revit/geometriya_v3.json.

Повторный запуск удаляет построенное этим скриптом (метка «КВВ-здание» в «Комментариях») и строит заново.
"""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Architecture as A
from System.Collections.Generic import List
import kvv
reload(kvv)

doc = HOST_APP.doc
M = kvv.M
METKA = u'КВВ-здание'
TOLSH = {u'nar': 0.52, u'fund': 0.316, u'nes': 0.42, u'per': 0.10, u'beton': 0.20, u'korob': 0.05}


def pometit(e):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p and not p.IsReadOnly:
        p.Set(METKA)


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


def steny(g, lv, log):
    tipy = g['tipy']
    tip_korob(tipy, log)
    imena = [u['imya'] for u in sorted(g['urovni'], key=lambda u: u['z'])]
    etazhi = [u for u in imena if u.startswith(u'Этаж')]
    sozd = []            # (уровень, стена, p1, p2, толщина)
    for s in g['steny']:
        wt = kvv.po_imeni(doc, DB.WallType, tipy[s['tip']])
        if wt is None:
            log(u'НЕТ типа стены', tipy[s['tip']])
            continue
        gde = []
        if s['gde'] in (u'etazhi', u'vse'):
            gde += etazhi
        if s['gde'] in (u'podval', u'vse'):
            gde.append(u'Подвал')
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


def proemy(g, lv, sozd, log):
    etazhi = [u['imya'] for u in g['urovni'] if u['imya'].startswith(u'Этаж')]
    n, net = 0, 0
    for o, is_okno in [(o, True) for o in g['okna']] + [(d, False) for d in g['dveri']]:
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
            p = DB.XYZ(o['x'] * M, o['y'] * M, lv[u].Elevation + pod * M)
            e = doc.Create.NewFamilyInstance(p, sym, w, lv[u], DB.Structure.StructuralType.NonStructural)
            if is_okno:
                par = e.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if par and not par.IsReadOnly:
                    par.Set(pod * M)
            pometit(e)
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
    k = g['krovlya']
    ft = kvv.po_imeni(doc, DB.FloorType, tipy['perekr'])
    f = DB.Floor.Create(doc, List[DB.CurveLoop]([kontur(k['kontur'])]), ft.Id, lv[k['uroven']].Id)
    pometit(f)
    log(u'плита покрытия на уровне', k['uroven'])


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


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    with kvv.Tranzakciya(doc, u'КВВ: здание'):
        udalit_staroe(log)
        lv = urovni_osi(g, log)
        doc.Regenerate()
        sozd = steny(g, lv, log)
        doc.Regenerate()
        proemy(g, lv, sozd, log)
        perekrytiya(g, lv, log)
    lv = kvv.urovni(doc)
    lestnicy(g, lv, log)


kvv.run('03_zdanie', main)
