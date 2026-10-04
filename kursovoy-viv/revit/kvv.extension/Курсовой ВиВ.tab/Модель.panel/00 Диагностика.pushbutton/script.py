# -*- coding: utf-8 -*-
"""Проверка активной модели: количество элементов по категориям, параметры и габариты окон.

(Выгрузка шаблонов ВК/АР и модулей труб, которую делала эта кнопка раньше, сохранена в revit/log/00_diagnostika_*.txt.)
"""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
import kvv
reload(kvv)

doc = HOST_APP.doc


def mm(v):
    return u'%.0f' % (v / kvv.MM)


def main(log):
    log(u'документ:', doc.Title)
    for bic, nm in ((DB.BuiltInCategory.OST_Walls, u'стены'), (DB.BuiltInCategory.OST_Windows, u'окна'),
                    (DB.BuiltInCategory.OST_Doors, u'двери'), (DB.BuiltInCategory.OST_Floors, u'перекрытия'),
                    (DB.BuiltInCategory.OST_PlumbingFixtures, u'приборы'),
                    (DB.BuiltInCategory.OST_PipeCurves, u'трубы'), (DB.BuiltInCategory.OST_PipeFitting, u'фитинги'),
                    (DB.BuiltInCategory.OST_PipeAccessory, u'арматура')):
        n = DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().GetElementCount()
        log(u'  %s: %d' % (nm, n))
    okna = list(DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Windows)
                .WhereElementIsNotElementType())
    log(u'\nокна, первые 3:')
    for e in okna[:3]:
        s = e.Symbol
        log(u'#', e.Id, s.FamilyName, u':', DB.Element.Name.GetValue(s))
        log(u'  основа:', e.Host.Id if e.Host else None, type(e.Host).__name__ if e.Host else u'-',
            u'уровень:', doc.GetElement(e.LevelId).Name if e.LevelId != DB.ElementId.InvalidElementId else u'-')
        p = e.Location.Point
        log(u'  точка, мм:', mm(p.X), mm(p.Y), mm(p.Z), u'| ориентация:', e.FacingOrientation, e.HandOrientation,
            u'| отражено:', e.Mirrored)
        bb = e.get_BoundingBox(None)
        if bb:
            log(u'  габарит, мм:', mm(bb.Max.X - bb.Min.X), mm(bb.Max.Y - bb.Min.Y), mm(bb.Max.Z - bb.Min.Z))
        for src, nm in ((e, u'экземпляр'), (s, u'тип')):
            vals = []
            for par in src.Parameters:
                if par.StorageType == DB.StorageType.Double and par.HasValue:
                    vals.append(u'%s=%s' % (par.Definition.Name, mm(par.AsDouble())))
            log(u'  параметры (%s), мм:' % nm, u'; '.join(sorted(vals)))
        if e.Host:
            w = e.Host
            log(u'  стена:', DB.Element.Name.GetValue(w.WallType), u'толщина', mm(w.Width),
                u'ориентация', w.Orientation)


def gabarity(log):
    """Габариты семейств приборов, арматуры и оборудования относительно точки вставки (th = 0), мм."""
    import json
    import os
    lvl = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
    out = {}
    cats = [DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_PipeAccessory,
            DB.BuiltInCategory.OST_MechanicalEquipment]
    t = DB.Transaction(doc, u'Проба габаритов')
    t.Start()
    for c in cats:
        for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(c):
            if s.Family.FamilyPlacementType != DB.FamilyPlacementType.OneLevelBased:
                continue
            try:
                if not s.IsActive:
                    s.Activate()
                    doc.Regenerate()
                e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, lvl.Elevation), s, lvl,
                                                 DB.Structure.StructuralType.NonStructural)
                doc.Regenerate()
                bb = e.get_BoundingBox(None)
                k = s.FamilyName + u' : ' + DB.Element.Name.GetValue(s)
                out[k] = [round(bb.Min.X / kvv.MM), round(bb.Min.Y / kvv.MM), round((bb.Min.Z - lvl.Elevation) / kvv.MM),
                          round(bb.Max.X / kvv.MM), round(bb.Max.Y / kvv.MM), round((bb.Max.Z - lvl.Elevation) / kvv.MM)]
                log(u'  %s: %s' % (k, out[k]))
            except Exception as ex:
                log(u'  ошибка', s.FamilyName, ex)
    t.RollBack()
    path = os.path.join(kvv.REVIT, 'gabarity_semeystv.json')
    import io
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))
    log(u'записано', path)


def vse(log):
    main(log)
    log(u'\nгабариты семейств (min x, y, z, max x, y, z), мм:')
    gabarity(log)


kvv.run('00_proverka', vse)
