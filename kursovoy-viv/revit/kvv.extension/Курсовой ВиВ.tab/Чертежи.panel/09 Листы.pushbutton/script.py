# -*- coding: utf-8 -*-
"""Листы графической части (по образцу преподавателя): 4 листа А1 с основной надписью, видами и примечаниями.

Лист 1 — план типового этажа и план подвала, система В1; лист 2 — аксонометрическая схема В1;
лист 3 — планы, система К1; лист 4 — аксонометрическая схема К1. Генплан и профиль — отдельным листом А2 (позже).
Повторный запуск пересоздаёт листы с этими номерами.
"""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from System.Collections.Generic import List
import kvv
reload(kvv)

doc = HOST_APP.doc
MM = kvv.MM

PRIM_V1 = u'''Примечания:
1. Планы и схемы систем рассматривать совместно.
2. Все трубопроводы систем водоснабжения, кроме подводок к санитарным приборам, покрываются теплоизоляцией во избежание теплопотерь и появления конденсата.
3. Трубопроводы прокладывать с уклоном 0,002 в сторону сливной арматуры или смесителей.
4. Монтаж трубопроводов производить с учетом прокладки смежных систем.
5. Отметки трубопроводов даны по оси трубы.
6. Отметки трубопроводов и оборудования даны относительно нуля здания.
7. Привязки и отметки трубопроводов уточнять по месту.'''
PRIM_K1 = u'''Примечания:
1. Планы и схемы систем рассматривать совместно.
2. Монтаж трубопроводов производить с учетом прокладки смежных систем.
3. Отметки трубопроводов даны по лотку трубы.
4. Отметки трубопроводов и оборудования даны относительно нуля здания.
5. Привязки и отметки трубопроводов уточнять по месту.'''

LISTY = [  # номер, имя, [(вид, x доли, y доли)], примечания
    (u'1', u'План типового этажа. План подвала. Система В1',
     [(u'В1_План типового этажа', 0.47, 0.73), (u'В1_План подвала', 0.47, 0.30)], PRIM_V1),
    (u'2', u'Аксонометрическая схема. Система В1', [(u'В1_Аксонометрическая схема', 0.47, 0.52)], PRIM_V1),
    (u'3', u'План типового этажа. План подвала. Система К1',
     [(u'К1_План типового этажа', 0.47, 0.73), (u'К1_План подвала', 0.47, 0.30)], PRIM_K1),
    (u'4', u'Аксонометрическая схема. Система К1', [(u'К1_Аксонометрическая схема', 0.47, 0.52)], PRIM_K1),
]


def vid_po_imeni(nm):
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if not v.IsTemplate and v.Name == nm:
            return v
    return None


def osnovnaya_nadpis():
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(
            DB.BuiltInCategory.OST_TitleBlocks):
        if s.FamilyName == u'ADSK_ОсновнаяНадпись' and DB.Element.Name.GetValue(s) == u'Форма 3':
            return s
    return None


def parametry(e, log, zag):
    vals = []
    for p in e.Parameters:
        try:
            if p.StorageType == DB.StorageType.String:
                v = p.AsString()
            elif p.StorageType == DB.StorageType.Integer:
                v = p.AsInteger()
            elif p.StorageType == DB.StorageType.Double:
                v = round(p.AsDouble() / MM, 1)
            else:
                v = p.AsValueString()
        except Exception:
            v = u'?'
        vals.append(u'%s=%s%s' % (p.Definition.Name, v, u'' if not p.IsReadOnly else u'(ч)'))
    log(zag, u'; '.join(sorted(vals)))


def main(log):
    tb = osnovnaya_nadpis()
    if tb is None:
        log(u'НЕТ основной надписи ADSK_ОсновнаяНадпись : Форма 3')
        return
    tnt = kvv.po_imeni(doc, DB.TextNoteType, u'ADSK_Основной текст_2.5')
    with kvv.Tranzakciya(doc, u'КВВ: листы'):
        nomera = set(n for n, _, _, _ in LISTY)
        for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet):
            if s.SheetNumber in nomera:
                doc.Delete(s.Id)
        doc.Regenerate()
        pervyy = True
        for nom, imya, vidy, prim in LISTY:
            sh = DB.ViewSheet.Create(doc, tb.Id)
            sh.SheetNumber = nom
            sh.Name = imya
            doc.Regenerate()
            rama = [e for e in DB.FilteredElementCollector(doc, sh.Id).OfCategory(
                DB.BuiltInCategory.OST_TitleBlocks)][0]
            if pervyy:
                parametry(rama, log, u'ОСНОВНАЯ НАДПИСЬ (экземпляр):')
                parametry(rama.Symbol, log, u'ОСНОВНАЯ НАДПИСЬ (тип):')
                parametry(sh, log, u'ЛИСТ:')
                pervyy = False
            bb = rama.get_BoundingBox(sh)
            w, h = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
            log(u'лист', nom, u'рамка, мм:', round(w / MM), u'x', round(h / MM))
            for vn, fx, fy in vidy:
                v = vid_po_imeni(vn)
                if v is None:
                    log(u'  НЕТ вида', vn)
                    continue
                p = DB.XYZ(bb.Min.X + w * fx, bb.Min.Y + h * fy, 0)
                if DB.Viewport.CanAddViewToSheet(doc, sh.Id, v.Id):
                    DB.Viewport.Create(doc, sh.Id, v.Id, p)
                    log(u'  вид', vn)
                else:
                    log(u'  нельзя поставить вид', vn)
            if prim and tnt:
                opt = DB.TextNoteOptions(tnt.Id)
                opt.HorizontalAlignment = DB.HorizontalTextAlignment.Left
                p = DB.XYZ(bb.Max.X - 400 * MM, bb.Min.Y + 95 * MM, 0)
                tn = DB.TextNote.Create(doc, sh.Id, p, 205 * MM, prim, opt)
    log(u'листов', len(LISTY))


kvv.run('09_listy', main)
