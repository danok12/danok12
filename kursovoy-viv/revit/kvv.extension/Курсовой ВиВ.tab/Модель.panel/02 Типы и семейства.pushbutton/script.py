# -*- coding: utf-8 -*-
"""Перенести типы конструкций из шаблона АР, загрузить семейства и типы труб; выгрузить соединители приборов.

Работает с активным документом (проект на шаблоне ADSK ВК). Повторный запуск безопасен: уже загруженное
пропускается.
"""
import math
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
    # стены по указанию Глушкова: наружные 580, несущие внутренние 250 (прежние 520/420 оставлены для старых моделей)
    DB.WallType: [u'ADSK_Наружная отделка_Кирпич250_Слоистая кладка330_580', u'ADSK_Внутренняя_Кирпич_250',
                  u'ADSK_Наружная_Кирпич380 ут100 мм шт20-шт20_520', u'ADSK_Внутренняя_Кирпич380 шт20-шт20_420',
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
    u'Арматура трубопроводов/Для сети/VALTEC_VT.215.N_КранШаровой ВР-НР.rfa',
    u'Соединительные детали трубопроводов/VALTEC_VTr.582_Ниппель НР.rfa',
    u'Соединительные детали трубопроводов/VALTEC_VTr.340.N_Муфта разъемная латунная.rfa',
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
          (u'ADSK_Модуль ОВ и ВК_Трубы чугунные безраструбные SML_V1.rvt', [u'ADSK_Чугун_Безраструбный SML_DIN EN 877']),
          (u'ADSK_Модуль ОВ и ВК_Трубы ППР под сварку_V1.rvt', [u'ADSK_Полипропилен_PN20'])]   # В1 в квартирах и стояки
# соединительные детали из модулей (все типы семейства): у переходов «по умолчанию» нет нужных размеров — ADSK рисует
# шар-предупреждение (kvv_seti.kandidaty)
DETALI = [(u'ADSK_Модуль ОВ и ВК_Трубы чугунные безраструбные SML_V1.rvt', u'ADSK_ЧугунБезраструбный_Переходная муфта HL'),
          (u'ADSK_Модуль ОВ и ВК_Трубы ППР под сварку_V1.rvt', u'ADSK_Полипропилен_Муфта комбинированная ВР'),
          (u'ADSK_Модуль ОВ и ВК_Трубы ППР под сварку_V1.rvt', u'ADSK_Полипропилен_Муфта комбинированная НР'),
          (u'ADSK_Модуль ОВ и ВК_Трубы ППР под сварку_V1.rvt', u'ADSK_Полипропилен_Муфта комбинированная под ключ НР'),
          # водорозетка (настенный угольник с ушками) — у смесителей мойки, умывальника и ванны (замечание 28.10)
          (u'ADSK_Модуль ОВ и ВК_Трубы ППР под сварку_V1.rvt', u'ADSK_Полипропилен_Водорозетка ВР')]
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


def detali(log):
    """Семейства соединительных деталей из модулей ADSK (все типы), если их ещё нет в проекте."""
    est = set(f.Name for f in DB.FilteredElementCollector(doc).OfClass(DB.Family))
    po_modulyam = {}
    for fn, fam in DETALI:
        if fam in est:
            log(u'деталь уже есть:', fam)
            continue
        po_modulyam.setdefault(fn, []).append(fam)
    for fn, semya in po_modulyam.items():
        m = app.OpenDocumentFile(os.path.join(S, u'Системы трубопроводов', fn))
        try:
            ids = [s_.Id for s_ in DB.FilteredElementCollector(m).OfClass(DB.FamilySymbol)
                   if s_.FamilyName in semya]
            if not ids:
                log(u'НЕТ в модуле', fn, u':', u', '.join(semya))
                continue
            t = DB.Transaction(doc, u'Детали из модуля')
            t.Start()
            kopirovat(m, ids, log, u'типов деталей (%s)' % u', '.join(semya))
            t.Commit()
        finally:
            m.Close(False)


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


MODUL_PPR = u'ADSK_Модуль ОВ и ВК_Трубы ППР под сварку_V1.rvt'


def rezhim_zapuska():
    """revit/02_rezhim.txt: «ppr» — только разведка: трубы ППР из модуля (копируются в проект), крестовины
    канализационные, вертикальная арматура (проба с откатом). Файл после чтения удаляется."""
    import io
    put = os.path.join(kvv.REVIT, u'02_rezhim.txt')
    if not os.path.isfile(put):
        return u''
    with io.open(put, encoding='utf-8') as f:
        r = f.read().strip()
    os.remove(put)
    return r


def opisat_tip_trub(d, pt, log):
    log(u'  тип труб:', name(pt))
    rpm = pt.RoutingPreferenceManager
    for g in (DB.RoutingPreferenceRuleGroupType.Segments, DB.RoutingPreferenceRuleGroupType.Elbows,
              DB.RoutingPreferenceRuleGroupType.Junctions, DB.RoutingPreferenceRuleGroupType.Crosses,
              DB.RoutingPreferenceRuleGroupType.Transitions, DB.RoutingPreferenceRuleGroupType.Unions,
              DB.RoutingPreferenceRuleGroupType.Caps):
        for i in range(rpm.GetNumberOfRules(g)):
            rule = rpm.GetRule(g, i)
            e = d.GetElement(rule.MEPPartId)
            nm = name(e) if e is not None else u'-'
            if isinstance(e, DB.FamilySymbol):
                nm = e.FamilyName + u' : ' + nm
            log(u'    ', g, u'|', nm)
            if g == DB.RoutingPreferenceRuleGroupType.Segments and isinstance(e, Plumbing.PipeSegment):
                razm = [u'%.0f/%.1f/%.1f' % (sz.NominalDiameter * 304.8, sz.OuterDiameter * 304.8,
                                            sz.InnerDiameter * 304.8) for sz in e.GetSizes()]
                log(u'       размеры DN/нар/вн, мм:', u'; '.join(razm))


def razvedka_ppr(log):
    m = app.OpenDocumentFile(os.path.join(S, u'Системы трубопроводов', MODUL_PPR))
    try:
        tipy = list(DB.FilteredElementCollector(m).OfClass(Plumbing.PipeType))
        log(u'модуль', MODUL_PPR, u'| типов труб', len(tipy))
        for pt in tipy:
            opisat_tip_trub(m, pt, log)
        nuzhno = [pt.Id for pt in tipy if po_imeni(doc, Plumbing.PipeType, name(pt)) is None]
        if nuzhno:
            t = DB.Transaction(doc, u'Типы труб ППР из модуля')
            t.Start()
            kopirovat(m, nuzhno, log, u'типов труб ППР')
            t.Commit()
        else:
            log(u'типы труб ППР уже есть в проекте')
    finally:
        m.Close(False)
    for pt in DB.FilteredElementCollector(doc).OfClass(Plumbing.PipeType):
        if u'анализ' in name(pt) or u'Полипропилен' in name(pt):
            opisat_tip_trub(doc, pt, log)
    # крестовины и проба вертикальной арматуры — с откатом
    lvl = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
    t = DB.Transaction(doc, u'Проба: крестовины и вертикальная арматура')
    t.Start()
    try:
        for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(
                DB.BuiltInCategory.OST_PipeFitting):
            if u'Крестовин' not in s.FamilyName:
                continue
            log(u'\n# крестовина', s.FamilyName, u':', name(s))
            try:
                if not s.IsActive:
                    s.Activate()
                    doc.Regenerate()
                e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, 0), s, lvl, DB.Structure.StructuralType.NonStructural)
                doc.Regenerate()
                for cn in e.MEPModel.ConnectorManager.Connectors:
                    o, dr = cn.Origin, cn.CoordinateSystem.BasisZ
                    log(u'   r=%.1fмм o=(%.0f, %.0f, %.0f) dir=(%.2f, %.2f, %.2f)' % (
                        cn.Radius * 304.8, o.X * 304.8, o.Y * 304.8, o.Z * 304.8, dr.X, dr.Y, dr.Z))
            except Exception as ex:
                log(u'   ошибка:', ex)
        for fam in (u'VALTEC_VT.214.N_КранШаровой ВР', u'ADSK_Фильтр механический сетчатый муфтовый ВР',
                    u'Квартирный счетчик воды_Пульсар', u'ADSK_Клапан обратный пружинный_Муфтовый_DN15-50',
                    u'VALTEC_VT.089.N_Редуктор давления мембранный'):
            syms = [s for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol) if s.FamilyName == fam]
            log(u'\n# вертикально:', fam, u'| типы:', u', '.join(name(s) for s in syms[:8]))
            if not syms:
                continue
            s = syms[0]
            try:
                if not s.IsActive:
                    s.Activate()
                    doc.Regenerate()
                e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, 0), s, lvl, DB.Structure.StructuralType.NonStructural)
                doc.Regenerate()
                ax = DB.Line.CreateBound(DB.XYZ(0, 0, 0), DB.XYZ(0, 1, 0))
                DB.ElementTransformUtils.RotateElement(doc, e.Id, ax, math.pi / 2)
                doc.Regenerate()
                for cn in e.MEPModel.ConnectorManager.Connectors:
                    o, dr = cn.Origin, cn.CoordinateSystem.BasisZ
                    log(u'   после поворота: r=%.1fмм o=(%.0f, %.0f, %.0f) dir=(%.2f, %.2f, %.2f)' % (
                        cn.Radius * 304.8, o.X * 304.8, o.Y * 304.8, o.Z * 304.8, dr.X, dr.Y, dr.Z))
            except Exception as ex:
                log(u'   поворот не удался:', ex)
    finally:
        t.RollBack()


def katalog(log):
    """Что есть в модулях труб ADSK и шаблоне ВК: соединительные детали и арматура (семейство : тип, PartType),
    типы труб и правила их маршрутизации. Ищем переход ПП — чугун, комбинированные муфты ППР с резьбой DN15,
    тройники ППР с переходом."""
    moduli = [os.path.join(S, u'Системы трубопроводов', f) for f in sorted(os.listdir(os.path.join(S, u'Системы трубопроводов')))
              if f.lower().endswith(u'.rvt')]
    for put in moduli + [kvv.SHABLON_VK]:
        log(u'######', os.path.basename(put))
        try:
            d = app.NewProjectDocument(put) if put.lower().endswith(u'.rte') else app.OpenDocumentFile(put)
        except Exception as ex:
            log(u'  не открылся:', ex)
            continue
        try:
            for pt in DB.FilteredElementCollector(d).OfClass(Plumbing.PipeType):
                log(u'  тип труб:', name(pt))
                rpm = pt.RoutingPreferenceManager
                for gr in (DB.RoutingPreferenceRuleGroupType.Transitions, DB.RoutingPreferenceRuleGroupType.Unions,
                           DB.RoutingPreferenceRuleGroupType.Junctions):
                    for i in range(rpm.GetNumberOfRules(gr)):
                        r = rpm.GetRule(gr, i)
                        e = d.GetElement(r.MEPPartId)
                        log(u'     %s | %s' % (gr, (e.FamilyName + u' : ' + name(e)) if e is not None else u'-'))
            semya = {}
            for bic in (DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory):
                for sym in DB.FilteredElementCollector(d).OfClass(DB.FamilySymbol).OfCategory(bic):
                    semya.setdefault((bic, sym.FamilyName), []).append(name(sym))
            for (bic, fam), tipy in sorted(semya.items(), key=lambda kv: kv[0][1]):
                log(u'  %s | %s : %s' % (u'деталь' if bic == DB.BuiltInCategory.OST_PipeFitting else u'арматура', fam,
                                         u'; '.join(sorted(tipy))[:300]))
        finally:
            d.Close(False)


def main(log):
    log(u'документ:', doc.Title)
    rezhim = rezhim_zapuska()
    if rezhim == u'ppr':
        razvedka_ppr(log)
        return
    if rezhim == u'katalog':
        katalog(log)
        return
    tipy_ar(log)
    semeystva(log)
    truby(log)
    detali(log)
    soediniteli(log)


kvv.run('02_tipy', main)
