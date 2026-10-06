# -*- coding: utf-8 -*-
"""Перенести типы конструкций из шаблона АР, загрузить семейства и типы труб; выгрузить соединители приборов.

Работает с активным документом (проект на шаблоне ADSK ВК). Повторный запуск безопасен: уже загруженное
пропускается.
"""
import os
import clr
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
import kvv
reload(kvv)

app = HOST_APP.app
doc = HOST_APP.doc
S = kvv.SEMEYSTVA

AR_TIPY = {
    DB.WallType: [u'ADSK_Наружная_Кирпич380 ут100 мм шт20-шт20_520', u'ADSK_Внутренняя_Кирпич380 шт20-шт20_420',
                  u'ADSK_Внутренняя_Кирпич120 шт20-шт20_160', u'ADSK_Перегородка_ПГП_100',
                  u'ADSK_Внутренняя_Бетон_200', u'ADSK_Фундамент_Бетон300_Гидроизоляция16_316'],
    DB.FloorType: [u'ADSK_Перекрытие_Плита с полом_Бетон200 стяжка80 плитка20_300',
                   u'ADSK_Фундамент_Бетон200_Двухслойная Гидроизоляция249_449'],
    DB.RoofType: [u'ADSK_Плоская кровля по бетонному основанию_290'],
}
AR_SIMVOLY = [(u'B2B_Окно_2створки', u'1470(870)х1320h'), (u'AC_Дверь_Однопольная_Деревянная', u'860х2080h М Л'),
              (u'AC_Дверь_Однопольная_Деревянная', u'760х2080h М Л'), (u'AC_Дверь_Двупольная_Стальная', u'1360х2080h Н'),
              (u'B2B_Окно_1створка', u'870х1460h'), (u'B2B_БДверь_1створка', u'870х2060h Л'),
              (u'ADSK_Марка_Помещение_ОдноЗначение', u'Номер')]       # марка помещения — только номер (план А3 1:200)

SEMEYSTVA = [
    u'Сантехника/ADSK_Ванна стальная эмалированная_ГОСТ23695-2016.rfa',
    u'Сантехника/ADSK_Унитаз напольный_ГОСТ 30493-2017.rfa',
    u'Сантехника/ADSK_Умывальник со смесителем.rfa',
    u'Сантехника/ADSK_Мойка кухонная со смесителем.rfa',
    u'Арматура трубопроводов/Для сети/VALTEC_VT.214.N_КранШаровой ВР.rfa',
    u'Арматура трубопроводов/Для сети/VALTEC_VT.089.N_Редуктор давления мембранный.rfa',
    u'Арматура трубопроводов/Для сети/VALTEC_VT.051.N_Кран поливочный.rfa',
    u'Арматура трубопроводов/Для сети/ADSK_Фильтр механический сетчатый муфтовый ВР.rfa',
    u'Арматура трубопроводов/Для сети/ADSK_Клапан обратный пружинный_Муфтовый_DN15-50.rfa',
    u'Арматура трубопроводов/Для сети/ADSK_АвтоматическийВоздухоудалитель.rfa',
    u'Арматура трубопроводов/Для сети/ADSK_Противопожарная муфта.rfa',
    u'Арматура трубопроводов/Счетчики/Квартирный счетчик воды_Пульсар.rfa',
    u'Арматура трубопроводов/Счетчики/Многоструйный счетчик воды_Пульсар.rfa',
    u'Арматура трубопроводов/Для водомерного узла и насосной станции/ADL_Задвижка клиновая_Гранар_KR11.02.DN040-600.PN10-16.Ф-Ф.rfa',
    u'Арматура трубопроводов/Для водомерного узла и насосной станции/ADL_Фильтр_сетчатый_IS15.01.0600.DN15-50.PN16.Р-Р.rfa',
    u'Арматура трубопроводов/Для водомерного узла и насосной станции/ADL_Клапан обратный муфтовый_CVT16.04.DN15-80.PN16.Р-Р.rfa',
    u'Арматура трубопроводов/Для водомерного узла и насосной станции/Манометр_стандартное исполнение_Росма.rfa',
    u'Арматура трубопроводов/Для водомерного узла и насосной станции/ADL_Вставка гибкая фланцевая_FC10_DN32-500_PN10_Ф-Ф.rfa',
    u'Системы трубопроводов/ADSK_ППР_Переход_канализационный_с_фиксацией_R22.rfa',
]
NASOS_RFA = u'Оборудование/COR-MVL_2-32_BIM/COR-MVL_2_32_Revit2019(08.25).rfa'
MODULI = [(u'ADSK_Модуль ОВ и ВК_Трубы водогазопроводные ГОСТ 3262-75 на резьбе и сварке_V1.1.rvt',
           [u'ADSK_Сталь водогазопроводная_Оцинкованная_ГОСТ 3262-75']),
          (u'ADSK_Модуль ОВ и ВК_Трубы чугунные безраструбные SML_V1.rvt', [u'ADSK_Чугун_Безраструбный SML_DIN EN 877'])]
TIP_PE = u'ADSK_Полиэтилен ПЭ100 SDR17_ГОСТ 18599-2001'
SEGMENT_PE = u'Полиэтилен ПЭ100 - SDR17'


def name(e):
    return DB.Element.Name.GetValue(e)


def po_imeni(d, cls, nm):
    for e in DB.FilteredElementCollector(d).OfClass(cls):
        if name(e) == nm:
            return e
    return None


class TipyProekta(DB.IDuplicateTypeNamesHandler):
    """При совпадении имён типов брать типы проекта — без диалога."""
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


def versiya(path):
    try:
        return int(DB.BasicFileInfo.Extract(path).Format)
    except Exception:
        return 0


def kopirovat(src, ids, log, chto):
    if not ids:
        return
    opt = DB.CopyPasteOptions()
    opt.SetDuplicateTypeNamesHandler(TipyProekta())
    from System.Collections.Generic import List
    res = DB.ElementTransformUtils.CopyElements(src, List[DB.ElementId](ids), doc, DB.Transform.Identity, opt)
    log(u'скопировано', chto, res.Count)


def tipy_ar(log):
    log(u'открываю шаблон АР (обновление 2021 -> 2025, около минуты)')
    ar = app.NewProjectDocument(kvv.SHABLON_AR)
    try:
        ids = []
        for cls, names in AR_TIPY.items():
            for nm in names:
                if po_imeni(doc, cls, nm):
                    log(u'уже есть', nm)
                    continue
                e = po_imeni(ar, cls, nm)
                if e is None:
                    log(u'НЕТ в шаблоне АР:', nm)
                else:
                    ids.append(e.Id)
        for fam, tip in AR_SIMVOLY:
            uzhe = [s for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
                    if s.FamilyName == fam and name(s) == tip]
            if uzhe:
                log(u'уже есть', fam, tip)
                continue
            src = [s for s in DB.FilteredElementCollector(ar).OfClass(DB.FamilySymbol)
                   if s.FamilyName == fam and name(s) == tip]
            if src:
                ids.append(src[0].Id)
            else:
                log(u'НЕТ в шаблоне АР:', fam, tip)
        t = DB.Transaction(doc, u'Типы из шаблона АР')
        t.Start()
        kopirovat(ar, ids, log, u'типов АР')
        t.Commit()
    finally:
        ar.Close(False)


def semeystva(log):
    t = DB.Transaction(doc, u'Загрузка семейств')
    t.Start()
    for rel in SEMEYSTVA:
        path = os.path.join(S, *rel.split(u'/'))
        if versiya(path) > int(app.VersionNumber):
            log(u'ПРОПУСК: семейство из Revit', versiya(path), os.path.basename(path))
            continue
        fam = clr.Reference[DB.Family]()
        ok = doc.LoadFamily(path, fam)
        log(u'семейство', u'загружено' if ok else u'уже было/ошибка', os.path.basename(path))
    nas = kvv.load_json('calc', 'nasos_v3.json')
    sym = clr.Reference[DB.FamilySymbol]()
    ok = doc.LoadFamilySymbol(os.path.join(S, *NASOS_RFA.split(u'/')), nas['tip'], sym)
    log(u'насосная установка', nas['tip'], u'загружена' if ok else u'уже была/ошибка')
    t.Commit()


def truby(log):
    for fn, tipy in MODULI:
        nuzhno = [tp for tp in tipy if not po_imeni(doc, Plumbing.PipeType, tp)]
        if not nuzhno:
            log(u'типы труб уже есть:', u', '.join(tipy))
            continue
        m = app.OpenDocumentFile(os.path.join(S, u'Системы трубопроводов', fn))
        try:
            ids = [po_imeni(m, Plumbing.PipeType, tp).Id for tp in nuzhno]
            t = DB.Transaction(doc, u'Типы труб из модуля')
            t.Start()
            kopirovat(m, ids, log, u'типов труб из ' + fn)
            t.Commit()
        finally:
            m.Close(False)
    if po_imeni(doc, Plumbing.PipeType, TIP_PE):
        log(u'тип ПЭ уже есть')
        return
    t = DB.Transaction(doc, u'Тип трубы ПЭ100 для ввода')
    t.Start()
    st = po_imeni(doc, Plumbing.PipeType, u'ADSK_Сталь водогазопроводная_Оцинкованная_ГОСТ 3262-75')
    pe = st.Duplicate(TIP_PE)
    seg = po_imeni(doc, Plumbing.PipeSegment, SEGMENT_PE)
    rpm = pe.RoutingPreferenceManager
    g = DB.RoutingPreferenceRuleGroupType.Segments
    while rpm.GetNumberOfRules(g) > 0:
        rpm.RemoveRule(g, 0)
    rpm.AddRule(g, DB.RoutingPreferenceRule(seg.Id, u'ПЭ100 SDR17'))
    t.Commit()
    log(u'создан тип', TIP_PE)


def soediniteli(log):
    """Поставить по экземпляру каждого прибора/арматуры, выписать соединители и откатить."""
    lvl = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
    cats = [DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_PipeAccessory,
            DB.BuiltInCategory.OST_MechanicalEquipment]
    t = DB.Transaction(doc, u'Проба соединителей')
    t.Start()
    for c in cats:
        for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(c):
            fam = s.Family
            log(u'\n#', s.FamilyName, u':', name(s), u'| размещение', fam.FamilyPlacementType)
            try:
                if not s.IsActive:
                    s.Activate()
                    doc.Regenerate()
                if fam.FamilyPlacementType == DB.FamilyPlacementType.OneLevelBased:
                    e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, 0), s, lvl,
                                                     DB.Structure.StructuralType.NonStructural)
                elif fam.FamilyPlacementType == DB.FamilyPlacementType.WorkPlaneBased:
                    e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, 0), s, DB.XYZ.BasisX, lvl,
                                                     DB.Structure.StructuralType.NonStructural)
                else:
                    log(u'   пропуск: тип размещения не проверяю')
                    continue
                doc.Regenerate()
                cm = e.MEPModel.ConnectorManager if e.MEPModel else None
                if cm is None:
                    log(u'   нет соединителей')
                    continue
                for cn in cm.Connectors:
                    o = cn.Origin
                    dr = cn.CoordinateSystem.BasisZ
                    st = u''
                    try:
                        st = unicode(cn.PipeSystemType)
                    except Exception:
                        pass
                    log(u'   %s %s r=%.1fмм o=(%.0f, %.0f, %.0f)мм dir=(%.2f, %.2f, %.2f)' % (
                        cn.Domain, st, cn.Radius * 304.8, o.X * 304.8, o.Y * 304.8, o.Z * 304.8,
                        dr.X, dr.Y, dr.Z))
                for p in (u'ADSK_Наименование', u'ADSK_Марка', u'Комментарии к типоразмеру'):
                    pr = e.Symbol.LookupParameter(p) or e.LookupParameter(p)
                    if pr and pr.HasValue:
                        log(u'   ', p, u'=', pr.AsString() or pr.AsValueString())
            except Exception as ex:
                log(u'   ошибка пробы:', ex)
    t.RollBack()


def main(log):
    log(u'документ:', doc.Title)
    tipy_ar(log)
    semeystva(log)
    truby(log)
    soediniteli(log)


kvv.run('02_tipy', main)
