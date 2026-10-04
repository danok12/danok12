# -*- coding: utf-8 -*-
"""Выгрузить в журнал содержимое шаблонов ВК и АР и модулей труб: типы, уровни, виды, семейства."""
import os
from pyrevit import HOST_APP
from Autodesk.Revit import DB
import kvv
reload(kvv)

app = HOST_APP.app


def name(e):
    try:
        return DB.Element.Name.GetValue(e)
    except Exception:
        return u'?'


def dump(log, doc, titul):
    log(u'\n########', titul, u'########')
    def kls(cls, zag):
        items = sorted(set(name(e) for e in DB.FilteredElementCollector(doc).OfClass(cls)))
        log(u'--', zag, len(items))
        for s in items:
            log(u'   ', s)
    kls(DB.WallType, u'Типы стен')
    kls(DB.FloorType, u'Типы перекрытий')
    kls(DB.RoofType, u'Типы кровли')
    kls(DB.CeilingType, u'Типы потолков')
    kls(DB.Level, u'Уровни')
    kls(DB.Plumbing.PipeType, u'Типы труб')
    kls(DB.Plumbing.PipingSystemType, u'Типы систем трубопроводов')
    kls(DB.Plumbing.PipeInsulationType, u'Типы изоляции')
    kls(DB.Plumbing.FlexPipeType, u'Типы гибких труб')
    kls(DB.Plumbing.PipeSegment, u'Сегменты труб')
    kls(DB.ViewFamilyType, u'Типы видов')
    kls(DB.TextNoteType, u'Типы текста')
    kls(DB.DimensionType, u'Типы размеров')
    kls(DB.Mechanical.DuctType, u'Типы воздуховодов')
    views = DB.FilteredElementCollector(doc).OfClass(DB.View)
    tpl = sorted(name(v) for v in views if v.IsTemplate)
    log(u'-- Шаблоны видов', len(tpl))
    for s in tpl:
        log(u'   ', s)
    vv = sorted(u'%s | %s' % (v.ViewType, name(v)) for v in DB.FilteredElementCollector(doc).OfClass(DB.View)
                if not v.IsTemplate)
    log(u'-- Виды', len(vv))
    for s in vv:
        log(u'   ', s)
    fams = {}
    for fs in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        cat = fs.Category.Name if fs.Category else u'-'
        fams.setdefault(cat, set()).add(u'%s : %s' % (fs.FamilyName, name(fs)))
    log(u'-- Семейства по категориям')
    for cat in sorted(fams):
        log(u' [%s] %d' % (cat, len(fams[cat])))
        for s in sorted(fams[cat])[:60]:
            log(u'    ', s)
    pp = sorted(set(p.GetDefinition().Name for p in DB.FilteredElementCollector(doc).OfClass(DB.ParameterElement)))
    log(u'-- Параметры проекта/общие (ParameterElement)', len(pp))
    log(u'   ' + u'; '.join(pp))
    filt = sorted(name(e) for e in DB.FilteredElementCollector(doc).OfClass(DB.ParameterFilterElement))
    log(u'-- Фильтры видов', len(filt))
    log(u'   ' + u'; '.join(filt))
    sch = sorted(name(e) for e in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule))
    log(u'-- Спецификации', len(sch))
    for s in sch:
        log(u'   ', s)


def main(log):
    log(u'Revit', app.VersionNumber, app.VersionBuild, u'язык', app.Language)
    for titul, path in []:
        log(u'открываю', path)
        doc = app.NewProjectDocument(path)
        try:
            dump(log, doc, titul)
        finally:
            doc.Close(False)
    papka = os.path.join(kvv.SEMEYSTVA, u'Системы трубопроводов')
    for fn in sorted(os.listdir(papka)):
        if fn.lower().endswith('.rvt'):
            log(u'открываю', fn)
            doc = app.OpenDocumentFile(os.path.join(papka, fn))
            try:
                log(u'\n######## МОДУЛЬ', fn)
                for cls, zag in [(DB.Plumbing.PipeType, u'Типы труб'),
                                 (DB.Plumbing.PipingSystemType, u'Системы'),
                                 (DB.Plumbing.PipeSegment, u'Сегменты')]:
                    log(u'--', zag, u'; '.join(sorted(name(e) for e in
                                                     DB.FilteredElementCollector(doc).OfClass(cls))))
            finally:
                doc.Close(False)


kvv.run('00_diagnostika', main)
