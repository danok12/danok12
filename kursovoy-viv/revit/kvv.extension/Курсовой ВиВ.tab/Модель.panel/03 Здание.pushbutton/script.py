# -*- coding: utf-8 -*-
"""Уровни, оси, стены, окна и двери, перекрытия, кровля по revit/geometriya_v3.json.

Повторный запуск удаляет ранее построенное этим скриптом (помечено в «Комментариях» как КВВ-здание) и строит заново.
"""
import clr
from pyrevit import HOST_APP
from Autodesk.Revit import DB
import kvv
reload(kvv)

doc = HOST_APP.doc
M = kvv.M
METKA = u'КВВ-здание'


def pometit(e):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p and not p.IsReadOnly:
        p.Set(METKA)


def udalit_staroe(log):
    ids = []
    for cls in (DB.Wall, DB.Floor, DB.FootPrintRoof, DB.FamilyInstance):
        for e in DB.FilteredElementCollector(doc).OfClass(cls).WhereElementIsNotElementType():
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and p.AsString() == METKA:
                ids.append(e.Id)
    from System.Collections.Generic import List
    if ids:
        doc.Delete(List[DB.ElementId](ids))
    log(u'удалено старых элементов', len(ids))


def urovni_osi(g, log):
    lv = kvv.urovni(doc)
    # уровень шаблона «Этаж 01» оставляем — к нему привязаны виды шаблона
    for u in g['urovni']:
        if u['imya'] in lv:
            lv[u['imya']].Elevation = u['z'] * M
            continue
        l = DB.Level.Create(doc, u['z'] * M)
        l.Name = u['imya']
        lv[u['imya']] = l
    log(u'уровней', len(lv))
    est = set(gr.Name for gr in DB.FilteredElementCollector(doc).OfClass(DB.Grid))
    n = 0
    for o in g['osi']:
        if o['imya'] in est:
            continue
        gr = DB.Grid.Create(doc, DB.Line.CreateBound(kvv.xyz(*o['p1']), kvv.xyz(*o['p2'])))
        gr.Name = o['imya']
        n += 1
    log(u'осей создано', n)
    return lv


def steny(g, lv, log):
    tipy = g['tipy']
    porjadok = sorted(g['urovni'], key=lambda u: u['z'])
    imena = [u['imya'] for u in porjadok]
    etazhi = [u for u in imena if u.startswith(u'Этаж')]
    naruzh = {}            # (уровень, сторона) -> стена, для окон
    n = 0
    korob = kvv.po_imeni(doc, DB.WallType, tipy['korob'])
    if korob is None:
        # обшивка короба ГКЛВ 50 мм — дубликат перегородки ПГП с толщиной 50 мм
        per = kvv.po_imeni(doc, DB.WallType, tipy['per'])
        korob = per.Duplicate(tipy['korob'])
        cs = korob.GetCompoundStructure()
        tot = sum(cs.GetLayerWidth(i) for i in range(cs.LayerCount))
        for i in range(cs.LayerCount):
            cs.SetLayerWidth(i, cs.GetLayerWidth(i) * 50 * kvv.MM / tot)
        korob.SetCompoundStructure(cs)
        log(u'создан тип стены', tipy['korob'])
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
            niz = lv[u]
            verh = lv[imena[imena.index(u) + 1]]
            w = DB.Wall.Create(doc, line, wt.Id, niz.Id, (verh.Elevation - niz.Elevation), 0.0, False, False)
            w.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).Set(verh.Id)
            w.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM).Set(0)     # по оси стены
            pometit(w)
            n += 1
            if s['tip'] == u'nar':
                (x1, y1), (x2, y2) = s['p1'], s['p2']
                if abs(y1 - y2) < 1e-6:
                    naruzh[(u, round(y1, 3))] = w
    log(u'стен создано', n)
    return naruzh


def okna(g, lv, naruzh, log):
    tipy = g['tipy']
    n = 0
    etazhi = [u['imya'] for u in g['urovni'] if u['imya'].startswith(u'Этаж')]
    for o in g['okna']:
        fam, tip = tipy[o['tip']]
        sym = kvv.simvol(doc, fam, tip)
        if sym is None:
            log(u'НЕТ семейства', fam, tip)
            continue
        gde = etazhi if o['gde'] == u'etazhi' else [o['gde']]
        for u in gde:
            w = naruzh.get((u, round(o['y'], 3)))
            if w is None:
                continue
            z = lv[u].Elevation + (g['podokonnik'] * M if o['tip'] == u'okno' else 0.0)
            p = DB.XYZ(o['x'] * M, o['y'] * M, z)
            e = doc.Create.NewFamilyInstance(p, sym, w, lv[u], DB.Structure.StructuralType.NonStructural)
            if o['tip'] == u'okno':
                e.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).Set(g['podokonnik'] * M)
            pometit(e)
            n += 1
    log(u'окон и дверей', n)


def kontur(pts):
    cl = DB.CurveLoop()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        cl.Append(DB.Line.CreateBound(kvv.xyz(*a), kvv.xyz(*b)))
    return cl


def perekrytiya(g, lv, log):
    from System.Collections.Generic import List
    tipy = g['tipy']
    n = 0
    for p in g['perekr']:
        ft = kvv.po_imeni(doc, DB.FloorType, tipy[p['tip']])
        if ft is None:
            log(u'НЕТ типа перекрытия', tipy[p['tip']])
            continue
        f = DB.Floor.Create(doc, List[DB.CurveLoop]([kontur(p['kontur'])]), ft.Id, lv[p['uroven']].Id)
        pometit(f)
        n += 1
    log(u'перекрытий', n)
    k = g['krovlya']
    vse = list(DB.FilteredElementCollector(doc).OfClass(DB.RoofType))
    rt = [t for t in vse if DB.Element.Name.GetValue(t) == tipy[k['tip']]]
    if not rt:
        log(u'НЕТ типа кровли', tipy[k['tip']], u'; есть:', u'; '.join(DB.Element.Name.GetValue(t) for t in vse))
        rt = [t for t in vse if u'Плоская' in DB.Element.Name.GetValue(t)] or vse
    rt = rt[0]
    ca = DB.CurveArray()
    for c in kontur(k['kontur']):
        ca.Append(c)
    try:
        res = doc.Create.NewFootPrintRoof(ca, lv[k['uroven']], rt)
        r = res[0] if isinstance(res, tuple) else res
        pometit(r)
        log(u'кровля', DB.Element.Name.GetValue(rt))
    except Exception as ex:
        log(u'кровля не создалась (%s), ставлю плиту покрытия' % ex)
        ft = kvv.po_imeni(doc, DB.FloorType, tipy['perekr'])
        f = DB.Floor.Create(doc, List[DB.CurveLoop]([kontur(k['kontur'])]), ft.Id, lv[k['uroven']].Id)
        pometit(f)


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    with kvv.Tranzakciya(doc, u'КВВ: здание'):
        udalit_staroe(log)
        lv = urovni_osi(g, log)
        doc.Regenerate()
        naruzh = steny(g, lv, log)
        doc.Regenerate()
        okna(g, lv, naruzh, log)
        perekrytiya(g, lv, log)


kvv.run('03_zdanie', main)
