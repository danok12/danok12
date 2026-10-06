# -*- coding: utf-8 -*-
"""Листы графической части (по образцу преподавателя): листы А3 с основной надписью, по одному виду на лист,
с заголовком вида и масштабом над видом и примечаниями; последний лист — экспликация помещений.
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

# листы А3, каждый вид на своём листе: номер, имя, вид, примечания
LISTY = [
    (u'1', u'План типового этажа. Система В1', u'В1_План типового этажа', PRIM_V1),
    (u'2', u'План подвала. Система В1', u'В1_План подвала', PRIM_V1),
    (u'3', u'Аксонометрическая схема. Система В1', u'В1_Аксонометрическая схема', PRIM_V1),
    (u'4', u'План типового этажа. Система К1', u'К1_План типового этажа', PRIM_K1),
    (u'5', u'План подвала. Система К1', u'К1_План подвала', PRIM_K1),
    (u'6', u'Аксонометрическая схема. Система К1', u'К1_Аксонометрическая схема', PRIM_K1),
    (u'7', u'Экспликация помещений', None, None),
]
LISTOV_VSEGO = len(LISTY) + 1          # лист 8 — генплан (AutoCAD, kursovoy-viv/genplan)
EKSPL = [  # имя таблицы, фильтр номера (от, до) — секция 1; секция 2 зеркальная, номера групп 05-08 / 00.02
    (u'Экспликация помещений типового этажа (секция 1)', u'02.01', u'02.05'),
    (u'Экспликация помещений подвала (секция 1)', u'00.01', u'00.02'),
]


class Zagruzka(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = False
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues.Value = False
        return True


def bez_logotipa(tb, log):
    """Из основной надписи (копия семейства в проекте) убрать логотип шаблона: в графе 9 — кафедра. Вне транзакции."""
    fd = doc.EditFamily(tb.Family)
    try:
        ids = [fi.Id for fi in DB.FilteredElementCollector(fd).OfClass(DB.FamilyInstance)
               if u'Логотип' in fi.Symbol.FamilyName]
        if not ids:
            log(u'логотипа в основной надписи нет')
            return
        t = DB.Transaction(fd, u'без логотипа')
        t.Start()
        fd.Delete(List[DB.ElementId](ids))
        t.Commit()
        fd.LoadFamily(doc, Zagruzka())
        log(u'логотип шаблона убран из основной надписи:', len(ids))
    finally:
        try:
            fd.Close(False)
        except Exception:
            pass


def ekspl(nm, ot, do, log):
    """Спецификация помещений: номер, наименование, площадь; фильтр по номеру [ot, do)."""
    for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule):
        if v.Name == nm:
            doc.Delete(v.Id)
            break
    vs = DB.ViewSchedule.CreateSchedule(doc, DB.ElementId(DB.BuiltInCategory.OST_Rooms))
    vs.Name = nm
    d = vs.Definition
    polya = {}
    for sf in d.GetSchedulableFields():
        polya[sf.GetName(doc)] = sf
    out = {}
    for imya, zag in ((u'Номер', u'Номер'), (u'Имя', u'Наименование'), (u'Площадь', u'Площадь, м²')):
        if imya in polya:
            f = d.AddField(polya[imya])
            f.ColumnHeading = zag
            out[imya] = f
        else:
            log(u'  нет поля', imya)
    fn = out[u'Номер']
    d.AddFilter(DB.ScheduleFilter(fn.FieldId, DB.ScheduleFilterType.GreaterThanOrEqual, ot))
    d.AddFilter(DB.ScheduleFilter(fn.FieldId, DB.ScheduleFilterType.LessThan, do))
    d.AddSortGroupField(DB.ScheduleSortGroupField(fn.FieldId))
    return vs



SHIFR = u'НИУ МГСУ 08.03.01*-КП-2026'
TEMA = u'Системы холодного водоснабжения и водоотведения здания'
ORG = u'НИУ МГСУ ИИЭСМ'
KAFEDRA = u'Кафедра «Водоснабжение и водоотведение»'


def ustanovit(e, imya, znach, log):
    p = e.LookupParameter(imya)
    if p is None or p.IsReadOnly:
        log(u'  нет/только чтение:', imya)
        return
    if p.StorageType == DB.StorageType.Integer:
        p.Set(int(znach))
    elif p.StorageType == DB.StorageType.Double:
        p.Set(float(znach))
    else:
        p.Set(znach)


TIP_VE = u'КВВ_Заголовок вида с масштабом'
TIP_VE_STARYY = u'КВВ_Заголовок с масштабом'      # испорчен прошлой версией скрипта


def tip_vidovogo_ekrana(vp, log, tip_zag=u'Заголовок на листе_Масштаб'):
    """Тип видового экрана с заголовком «ADSK_НаименованиеВида : Заголовок на листе_Масштаб» (как в образце:
    «План типового этажа. Система В1 (1:200)» над видом): готовый тип шаблона с этим заголовком или копия типа,
    в которой задан параметр «Название»."""
    nazv = None
    for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(
            DB.BuiltInCategory.OST_ViewportLabel):
        if s_.FamilyName == u'ADSK_НаименованиеВида' and DB.Element.Name.GetValue(s_) == tip_zag:
            nazv = s_
    if nazv is None:
        log(u'нет семейства заголовка вида ADSK_НаименованиеВида :', tip_zag)
        return None
    baza = doc.GetElement(vp.GetTypeId())
    tipy = [e for e in DB.FilteredElementCollector(doc).OfClass(DB.ElementType) if e.FamilyName == baza.FamilyName]
    opis = []
    for e in tipy:
        try:
            if not e.IsValidObject:
                continue
            p = e.LookupParameter(u'Название') or e.get_Parameter(DB.BuiltInParameter.VIEWPORT_ATTR_LABEL_TAG)
            nid = p.AsElementId() if p is not None else DB.ElementId.InvalidElementId
        except Exception:
            continue
        opis.append(u'%s -> %s' % (DB.Element.Name.GetValue(e), DB.Element.Name.GetValue(doc.GetElement(nid)) if nid.IntegerValue > 0 else u'-'))
        if nid == nazv.Id:
            log(u'тип видового экрана с заголовком', tip_zag, u':', DB.Element.Name.GetValue(e))
            return e
    log(u'типы видовых экранов:', u'; '.join(opis))
    t = baza.Duplicate(TIP_VE + (u'' if tip_zag.endswith(u'Масштаб') else u' (без масштаба)'))
    p = t.LookupParameter(u'Название')
    try:
        p.Set(nazv.Id)
    except Exception as ex:
        log(u'«Название» в копии типа не задано:', ex)
    ps = t.get_Parameter(DB.BuiltInParameter.VIEWPORT_ATTR_SHOW_LABEL)
    if ps is not None and not ps.IsReadOnly:
        ps.Set(1)                                    # «Да»
    return t


def zagolovok(vp, v, imya, log):
    """Заголовок вида над видом: «Заголовок на листе» вида = имя листа, полка — по центру над видом."""
    p = v.get_Parameter(DB.BuiltInParameter.VIEW_DESCRIPTION)
    if p is not None and not p.IsReadOnly:
        p.Set(imya)
    # у 3D-вида масштаб в заголовке пустой «( )» — схемам заголовок без масштаба (как в образце)
    t = tip_vidovogo_ekrana(vp, log, u'Заголовок на листе' if isinstance(v, DB.View3D) else u'Заголовок на листе_Масштаб')
    if t is None:
        return
    vp.ChangeTypeId(t.Id)
    doc.Regenerate()
    try:
        o = vp.GetBoxOutline()
        w = o.MaximumPoint.X - o.MinimumPoint.X
        h = o.MaximumPoint.Y - o.MinimumPoint.Y
        dl = 120 * MM
        vp.LabelLineLength = dl
        vp.LabelOffset = DB.XYZ(max(0.0, (w - dl) / 2), h + 4 * MM, 0)
    except Exception as ex:
        log(u'  положение заголовка не задано:', ex)


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
    try:
        bez_logotipa(tb, log)
    except Exception as ex:
        log(u'логотип не убран:', ex)
    tb = osnovnaya_nadpis()
    with kvv.Tranzakciya(doc, u'КВВ: листы', log):
        # текст организации в графе 9 основной надписи (поверх логотипа шаблона) — непрозрачный фон
        t_org = kvv.po_imeni(doc, DB.TextNoteType, u'КВВ_Штамп_организация')
        if t_org is None and tnt is not None:
            t_org = tnt.Duplicate(u'КВВ_Штамп_организация')
            t_org.get_Parameter(DB.BuiltInParameter.TEXT_BACKGROUND).Set(0)     # 0 — непрозрачный
            t_org.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(2.0 * MM)
        for e in DB.FilteredElementCollector(doc).OfClass(DB.ElementType):
            if e.FamilyName == u'Видовой экран' and DB.Element.Name.GetValue(e) == TIP_VE_STARYY:
                doc.Delete(e.Id)            # вместе с видовыми экранами этого типа — они всё равно ставятся заново
                log(u'удалён испорченный тип видового экрана', TIP_VE_STARYY)
        pi = doc.ProjectInformation
        pi.Number = SHIFR
        pi.Name = TEMA
        pi.OrganizationName = ORG
        pi.OrganizationDescription = KAFEDRA
        pi.Status = u'У'
        # листы с этими номерами переиспользуются (открытый лист удалить нельзя): виды и примечания ставятся заново
        est = dict((s.SheetNumber, s) for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet))
        nomera = set(n for n, _, _, _ in LISTY)
        lishnie = [s.Id for n, s in est.items() if n.isdigit() and n not in nomera and int(n) < 10]
        for sid in lishnie:
            try:
                doc.Delete(sid)
            except Exception:
                pass
        for nom, imya, vn, prim in LISTY:
            sh = est.get(nom)
            if sh is None:
                sh = DB.ViewSheet.Create(doc, tb.Id)
                sh.SheetNumber = nom
            else:
                stare = [e.Id for e in DB.FilteredElementCollector(doc, sh.Id).OfClass(DB.Viewport)] +                         [e.Id for e in DB.FilteredElementCollector(doc, sh.Id).OfClass(DB.TextNote)]
                for eid in stare:
                    doc.Delete(eid)
            sh.Name = imya
            doc.Regenerate()
            rama = [e for e in DB.FilteredElementCollector(doc, sh.Id).OfCategory(
                DB.BuiltInCategory.OST_TitleBlocks)][0]
            ustanovit(rama, u'Формат А', 3, log)
            ustanovit(sh, u'ADSK_Штамп_Наименование объекта', u'Жилой дом. Вариант 3', log)
            ustanovit(sh, u'ADSK_Штамп Раздел проекта', u'ВК', log)
            ustanovit(rama, u'Организация Заказчик', 0, log)
            ustanovit(sh, u'ADSK_Штамп_Количество листов', LISTOV_VSEGO, log)
            ustanovit(rama, u'Количество листов', LISTOV_VSEGO, log)
            ustanovit(sh, u'ADSK_Штамп_1 должность', u'Разраб.', log)
            ustanovit(sh, u'ADSK_Штамп_2 должность', u'Пров.', log)
            doc.Regenerate()
            bb = rama.get_BoundingBox(sh)
            w, h = bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y
            if vn is None:                       # лист экспликации: таблицы помещений
                for k_, (nm_, ot, do) in enumerate(EKSPL):     # две таблицы рядом, сверху
                    vs = ekspl(nm_, ot, do, log)
                    doc.Regenerate()
                    ssi = DB.ScheduleSheetInstance.Create(doc, sh.Id, vs.Id,
                                                          DB.XYZ(bb.Min.X + (30 + 190 * k_) * MM, bb.Max.Y - 12 * MM, 0))
                    doc.Regenerate()
                    b2 = ssi.get_BoundingBox(sh)
                    log(u'лист', nom, u'| таблица', nm_, u'| %d x %d мм' % (round((b2.Max.X - b2.Min.X) / MM),
                                                                         round((b2.Max.Y - b2.Min.Y) / MM)))
                continue
            v = vid_po_imeni(vn)
            if v is None:
                log(u'  НЕТ вида', vn)
                continue
            shema = isinstance(v, DB.View3D)
            if shema:
                # схема высокая — в левой части листа на всю высоту, примечания справа над штампом
                p = DB.XYZ(bb.Min.X + 137 * MM, bb.Min.Y + h / 2, 0)
            else:
                # центр рабочего поля: поле слева 20 мм, над основной надписью (55 мм)
                p = DB.XYZ(bb.Min.X + (20 + (w / MM - 25) / 2) * MM, bb.Min.Y + (60 + (h / MM - 65) / 2) * MM, 0)
            if DB.Viewport.CanAddViewToSheet(doc, sh.Id, v.Id):
                vp = DB.Viewport.Create(doc, sh.Id, v.Id, p)
                doc.Regenerate()
                zagolovok(vp, v, imya, log)
                doc.Regenerate()
                # вид — в рабочее поле: схема прижата к левому верхнему углу (справа примечания и штамп),
                # план — по центру поля над примечаниями; сверху место под заголовок
                o = vp.GetBoxOutline()
                vw, vh = o.MaximumPoint.X - o.MinimumPoint.X, o.MaximumPoint.Y - o.MinimumPoint.Y
                if shema:
                    # габарит 3D-вида на листе Revit берёт больше рамки подрезки (глубина рамки ~200 м после
                    # блокировки вида), лишнее поле — поровну сверху и снизу. Ставим по самой рамке подрезки:
                    # её верх — под заголовком, левый край — в 25 мм от края листа
                    cb = v.CropBox
                    cw = (cb.Max.X - cb.Min.X) / v.Scale + 6 * MM
                    ch = (cb.Max.Y - cb.Min.Y) / v.Scale + 6 * MM
                    cx = bb.Min.X + 25 * MM + cw / 2
                    cy = bb.Max.Y - 24 * MM - ch / 2
                    try:
                        dl = 120 * MM
                        vp.LabelOffset = DB.XYZ(max(0.0, (vw - dl) / 2), (vh + ch) / 2 + 4 * MM, 0)
                    except Exception as ex:
                        log(u'  заголовок схемы не сдвинут:', ex)
                    log(u'  схема: рамка подрезки на листе %.0f x %.0f мм, видовой экран %.0f x %.0f мм' % (
                        cw / MM, ch / MM, vw / MM, vh / MM))
                else:
                    cx = bb.Min.X + (20 + (w / MM - 25) / 2) * MM
                    cy = bb.Min.Y + (60 + (h / MM - 75) / 2) * MM
                vp.SetBoxCenter(DB.XYZ(cx, cy, 0))
                doc.Regenerate()
                try:
                    lo = vp.GetLabelOutline()
                    log(u'  заголовок вида: %.0f..%.0f x %.0f..%.0f мм от угла листа' % (
                        (lo.MinimumPoint.X - bb.Min.X) / MM, (lo.MaximumPoint.X - bb.Min.X) / MM,
                        (lo.MinimumPoint.Y - bb.Min.Y) / MM, (lo.MaximumPoint.Y - bb.Min.Y) / MM),
                        u'| LabelOffset %.0f, %.0f мм' % (vp.LabelOffset.X / MM, vp.LabelOffset.Y / MM))
                except Exception as ex:
                    log(u'  заголовок вида: нет контура', ex)
                o = vp.GetBoxOutline()
                log(u'лист', nom, u'рамка %d x %d мм | вид' % (round(w / MM), round(h / MM)), vn, u'| 1:%d' % v.Scale,
                    u'| габарит вида %d x %d мм' % (round((o.MaximumPoint.X - o.MinimumPoint.X) / MM),
                                                    round((o.MaximumPoint.Y - o.MinimumPoint.Y) / MM)))
            else:
                log(u'  нельзя поставить вид', vn)
            if t_org is not None:
                o2 = DB.TextNoteOptions(t_org.Id)
                o2.HorizontalAlignment = DB.HorizontalTextAlignment.Center
                DB.TextNote.Create(doc, sh.Id, DB.XYZ(bb.Max.X - 30 * MM, bb.Min.Y + 19.5 * MM, 0), 48 * MM,
                                   ORG + unichr(13) + KAFEDRA, o2)
            if prim and tnt:
                opt = DB.TextNoteOptions(tnt.Id)
                opt.HorizontalAlignment = DB.HorizontalTextAlignment.Left
                if shema:
                    # справа от схемы, над основной надписью (схема занимает левые ~265 мм)
                    DB.TextNote.Create(doc, sh.Id, DB.XYZ(bb.Min.X + 293 * MM, bb.Min.Y + 150 * MM, 0), 117 * MM, prim,
                                       opt)
                else:
                    DB.TextNote.Create(doc, sh.Id, DB.XYZ(bb.Min.X + 25 * MM, bb.Min.Y + 52 * MM, 0), 200 * MM, prim,
                                       opt)
    log(u'листов', len(LISTY))
    eksport_png(log)


def eksport_png(log):
    """Листы — в PNG (revit/log/listy/), чтобы проверить вёрстку вне Revit."""
    import os
    papka = os.path.join(kvv.LOG_DIR, u'listy')
    if not os.path.isdir(papka):
        os.makedirs(papka)
    nomera = set(n for n, _, _, _ in LISTY)
    ids = List[DB.ElementId]([s.Id for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet)
                              if s.SheetNumber in nomera])
    o = DB.ImageExportOptions()
    o.ExportRange = DB.ExportRange.SetOfViews
    o.SetViewsAndSheets(ids)
    o.ZoomType = DB.ZoomFitType.FitToPage
    o.PixelSize = 4200
    o.ImageResolution = DB.ImageResolution.DPI_300
    o.HLRandWFViewsFileType = DB.ImageFileType.PNG
    o.ShadowViewsFileType = DB.ImageFileType.PNG
    o.FilePath = os.path.join(papka, u'list')
    try:
        doc.ExportImage(o)
        log(u'листы выгружены в PNG:', papka)
    except Exception as ex:
        log(u'PNG не выгружены:', ex)


kvv.run('09_listy', main)
