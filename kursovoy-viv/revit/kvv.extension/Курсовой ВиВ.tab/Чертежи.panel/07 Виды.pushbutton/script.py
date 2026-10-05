# -*- coding: utf-8 -*-
"""Виды для листов: планы типового этажа и подвала (В1, К1), аксонометрические схемы В1 и К1.

Шаблоны видов — из шаблона ADSK ВК. Повторный запуск пересоздаёт виды (по имени).
"""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from System.Collections.Generic import List
import kvv
reload(kvv)

doc = HOST_APP.doc
M = kvv.M

PLANY = [  # имя вида, уровень, шаблон, тип вида
    (u'В1_План типового этажа', u'Этаж 02', u'О_ПЭ_Водопровод', u'О_ПЭ_Водопровод'),
    (u'В1_План подвала', u'Подвал', u'О_ПЭ_Водопровод', u'О_ПЭ_Водопровод'),
    (u'К1_План типового этажа', u'Этаж 02', u'О_ПЭ_Канализация', u'О_ПЭ_Канализация'),
    (u'К1_План подвала', u'Подвал', u'О_ПЭ_Канализация', u'О_ПЭ_Канализация'),
]
SHEMY = [(u'В1_Аксонометрическая схема', u'О_3D_Система В1', u'ADSK_Водопровод_В1'),
         (u'К1_Аксонометрическая схема', u'О_3D_Система К1', u'ADSK_Канализация_К1')]


def vid_po_imeni(nm):
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if not v.IsTemplate and v.Name == nm:
            return v
    return None


def shablon(nm):
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if v.IsTemplate and v.Name == nm:
            return v
    return None


def tip_vida(nm, semeystvo):
    for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
        if t.ViewFamily == semeystvo and (nm is None or DB.Element.Name.GetValue(t) == nm):
            return t
    return None


def obrezka(v, x0, y0, x1, y1):
    bb = DB.BoundingBoxXYZ()
    bb.Min = DB.XYZ(x0 * M, y0 * M, -100)
    bb.Max = DB.XYZ(x1 * M, y1 * M, 100)
    v.CropBox = bb
    v.CropBoxActive = True
    v.CropBoxVisible = False


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    lv = kvv.urovni(doc)
    xs = [x for w in g['steny'] for x in (w['p1'][0], w['p2'][0])]
    X0, X1 = min(xs), max(xs)
    with kvv.Tranzakciya(doc, u'КВВ: виды'):
        for nm, _, _, _ in PLANY:
            v = vid_po_imeni(nm)
            if v:
                doc.Delete(v.Id)
        for nm, _, _ in SHEMY:
            v = vid_po_imeni(nm)
            if v:
                doc.Delete(v.Id)
        for nm, ur, shab, tip in PLANY:
            vft = tip_vida(tip, DB.ViewFamily.FloorPlan) or tip_vida(None, DB.ViewFamily.FloorPlan)
            v = DB.ViewPlan.Create(doc, vft.Id, lv[ur].Id)
            v.Name = nm
            t = shablon(shab)
            if t:
                v.ViewTemplateId = t.Id
            else:
                log(u'НЕТ шаблона', shab)
            # масштаб и обрезка: шаблон может задавать масштаб — снимаем это свойство с шаблона на виде
            try:
                v.Scale = 100
            except Exception as ex:
                log(u'масштаб задаёт шаблон:', ex)
            obrezka(v, X0 - 4.0, -4.5, X1 + 4.0, 12.8 + 5.0)
            log(u'план', nm, u'| шаблон', shab if t else u'-', u'| тип', DB.Element.Name.GetValue(vft))
        vft3 = tip_vida(None, DB.ViewFamily.ThreeDimensional)
        for nm, shab, sist in SHEMY:
            v = DB.View3D.CreateIsometric(doc, vft3.Id)
            v.Name = nm
            t = shablon(shab)
            if t:
                v.ViewTemplateId = t.Id
            else:
                log(u'НЕТ шаблона', shab)
            # фронтальная изометрия по образцу: взгляд с юго-запада сверху (ось X вправо-вверх, Y — вглубь)
            eye = DB.XYZ(-60 * M, -80 * M, 70 * M)
            fwd = DB.XYZ(1, 1.35, -0.9).Normalize()
            right = fwd.CrossProduct(DB.XYZ.BasisZ).Normalize()
            up = right.CrossProduct(fwd).Normalize()
            v.SetOrientation(DB.ViewOrientation3D(eye, up, fwd))
            try:
                v.Scale = 100
            except Exception:
                pass
            v.SaveOrientationAndLock()
            log(u'схема', nm, u'| шаблон', shab if t else u'-')


kvv.run('07_vidy', main)
