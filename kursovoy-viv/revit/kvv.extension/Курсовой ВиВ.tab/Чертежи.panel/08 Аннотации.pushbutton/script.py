# -*- coding: utf-8 -*-
"""Марки, размеры, отметки. Пока — разведка: параметры трубы и типы марок."""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
import kvv
reload(kvv)

doc = HOST_APP.doc


def main(log):
    t = [p for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe)][0]
    for p in t.Parameters:
        log(u'параметр трубы:', p.Definition.Name, u'| только чтение' if p.IsReadOnly else u'',
            u'| общий' if p.IsShared else u'', p.StorageType)
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_PipeTags):
        log(u'марка трубы:', s.FamilyName, u':', DB.Element.Name.GetValue(s), u'| id', s.Id.IntegerValue)
    for s in DB.FilteredElementCollector(doc).OfClass(DB.SpotDimensionType):
        log(u'тип отметки:', DB.Element.Name.GetValue(s), s.StyleType)
    for s in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType):
        log(u'тип текста:', DB.Element.Name.GetValue(s))


kvv.run("08_annotacii", main)
