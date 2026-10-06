# -*- coding: utf-8 -*-
"""Аннотации по образцу преподавателя (ГОСТ 21.601-2011): марки стояков «Ст.В1-N Ø» на планах и аксонометриях,
помещения с номерами, размеры по осям, марки диаметров, ввода и выпусков, выноски «Водомерный узел» и
«Насосная установка», высотные отметки на схемах. Повторный запуск удаляет свои аннотации и ставит заново."""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
from System.Collections.Generic import List
import math
import kvv
import kvv_oform
reload(kvv)
reload(kvv_oform)

doc = HOST_APP.doc
M = kvv.M
MARKA_STOYAKA = (u'ADSK_M_Трубы_Сокращение для системы', u'Сокращение_Номер стояка_Диаметр')
PLANY = [u'В1_План типового этажа', u'В1_План подвала', u'К1_План типового этажа', u'К1_План подвала']
SHEMY = [u'В1_Аксонометрическая схема', u'К1_Аксонометрическая схема']


def vid(nm):
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if not v.IsTemplate and v.Name == nm:
            return v
    return None


def tip_marki(fam, tip):
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_PipeTags):
        if s.FamilyName == fam and DB.Element.Name.GetValue(s) == tip:
            return s
    return None


def metka(e):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    return (p.AsString() or u'') if p is not None and p.HasValue else u''


def truby_stoyakov(g, log):
    """Вертикальные трубы стояков: (имя стояка, система) -> [трубы снизу вверх]."""
    st = {}
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        c = t.Location.Curve
        a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        if abs(a.X - b.X) > 1e-4 or abs(a.Y - b.Y) > 1e-4 or abs(a.Z - b.Z) < 0.5 * M:
            continue
        for s in g['stoyaki']:
            if abs(a.X / M - s['x']) < 0.01 and abs(a.Y / M - s['y']) < 0.01:
                st.setdefault(s['imya'], []).append(t)
    for k in st:
        st[k].sort(key=lambda t: min(t.Location.Curve.GetEndPoint(0).Z, t.Location.Curve.GetEndPoint(1).Z))
    log(u'стояков найдено', len(st), u'| труб', sum(len(v) for v in st.values()))
    return st


def storona(x, g):
    """Куда вынести марку стояка, чтобы марки соседних стояков (кв. Б и В у оси 8) не налезали:
    кв. Б — влево, кв. В — вправо, кв. А — в сторону комнаты (в локальных координатах секции)."""
    tr = kvv.load_json('calc', 'trassa_v3.json')
    zerk = tr.get('zerkalo', 45.0)
    sek2 = x > zerk / 2
    xl = zerk - x if sek2 else x
    s_ = -1 if 10.0 < xl < 15.7 else 1
    return -s_ if sek2 else s_


METKA_POM = u'КВВ-помещение'
PLANY_UR = {u'Этаж 02': [u'В1_План типового этажа', u'К1_План типового этажа'],
            u'Подвал': [u'В1_План подвала', u'К1_План подвала']}


def pomescheniya(g, log):
    """Помещения с номерами «этаж.группа.номер» и наименованиями на типовом этаже (Этаж 02) и в подвале,
    линии разделения кухня — прихожая, марки помещений на планах. Повторный запуск пересоздаёт."""
    lv = kvv.urovni(doc)
    stare = []
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        stare.append(e.Id)
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_RoomSeparationLines)             .WhereElementIsNotElementType():
        if metka(e) == METKA_POM:
            stare.append(e.Id)
    if stare:
        doc.Delete(List[DB.ElementId](stare))
    log(u'удалено старых помещений и линий', len(stare))
    marka_pom = None
    for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_RoomTags):
        if s_.FamilyName == u'ADSK_Марка_Помещение_ОдноЗначение' and DB.Element.Name.GetValue(s_) == u'Номер':
            marka_pom = s_
    log(u'марка помещения:', u'только номер' if marka_pom else u'по умолчанию (нет «Номер» — запустить 02)')
    if marka_pom is not None:
        # номер в окружности (как просил пользователь): тип «Номер» с параметром «Окружность» = Да; шрифт в семействе
        # уменьшен вдвое (umenshit_shrift_marki), окружность — под него
        p = marka_pom.LookupParameter(u'Окружность')
        if p is not None and not p.IsReadOnly:
            p.Set(1)
        p = marka_pom.LookupParameter(u'Радиус окружности')
        if p is not None and not p.IsReadOnly:
            p.Set(R_OKR_POM * kvv.MM)
    for r in g.get('razdeliteli', []):
        u = lv[r['uroven']]
        v = vid(PLANY_UR[r['uroven']][0])
        sp = DB.SketchPlane.Create(doc, DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisZ, DB.XYZ(0, 0, u.Elevation)))
        ca = DB.CurveArray()
        ca.Append(DB.Line.CreateBound(DB.XYZ(r['p1'][0] * M, r['p1'][1] * M, u.Elevation),
                                      DB.XYZ(r['p2'][0] * M, r['p2'][1] * M, u.Elevation)))
        for mc in doc.Create.NewRoomBoundaryLines(sp, ca, v):
            p = mc.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and not p.IsReadOnly:
                p.Set(METKA_POM)
    doc.Regenerate()
    n, nz, nt = 0, 0, 0
    for r in g.get('pomescheniya', []):
        u = lv[r['uroven']]
        uv = DB.UV(r['x'] * M, r['y'] * M)
        rm = doc.Create.NewRoom(u, uv)
        rm.Name = r['imya']
        rm.Number = r['nomer']
        p = rm.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p and not p.IsReadOnly:
            p.Set(METKA_POM)
        doc.Regenerate()
        if rm.Area <= 1e-6:
            nz += 1
            log(u'  помещение не замкнуто:', r['nomer'], r['imya'], u'(%.2f, %.2f)' % (r['x'], r['y']))
        n += 1
        for vn in PLANY_UR[r['uroven']]:
            v = vid(vn)
            if v is None:
                continue
            try:
                tg = doc.Create.NewRoomTag(DB.LinkElementId(rm.Id), uv, v.Id)
                if marka_pom is not None:
                    tg.ChangeTypeId(marka_pom.Id)
                tg.HasLeader = False
                nt += 1
            except Exception as ex:
                log(u'  марка помещения не встала:', vn, r['nomer'], ex)
    log(u'помещений', n, u'| не замкнуто', nz, u'| марок помещений', nt)


R_OKR_POM = 2.6          # радиус окружности номера помещения, мм (номер «02.03.06» шрифтом 1,25 мм — около 4,5 мм)


class Zagruzka(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = False
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues.Value = False
        return True


def umenshit_shrift_marki(log):
    """Шрифт номеров помещений — вдвое меньше (по просьбе пользователя: марки занимали слишком много места).
    Размер текста задан в семействе марки, поэтому семейство правится и перезагружается; повторный запуск не
    уменьшает ещё раз (уменьшаются только тексты не мельче 2 мм)."""
    fam = None
    for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_RoomTags):
        if s_.FamilyName == u'ADSK_Марка_Помещение_ОдноЗначение':
            fam = s_.Family
            break
    if fam is None:
        log(u'шрифт марок помещений: нет семейства')
        return
    fd = doc.EditFamily(fam)
    try:
        bylo, stalo = [], []
        t = DB.Transaction(fd, u'КВВ: шрифт марки помещения')
        t.Start()
        for tt in DB.FilteredElementCollector(fd).OfClass(DB.TextElementType):
            p = tt.get_Parameter(DB.BuiltInParameter.TEXT_SIZE)
            if p is None or p.IsReadOnly:
                continue
            h = p.AsDouble() / kvv.MM
            bylo.append(round(h, 2))
            if h >= 2.0 - 1e-6:
                p.Set(h / 2.0 * kvv.MM)
                stalo.append(round(h / 2.0, 2))
        t.Commit()
        if stalo:
            fd.LoadFamily(doc, Zagruzka())
            log(u'шрифт марок помещений уменьшен вдвое:', bylo, u'->', stalo)
        else:
            log(u'шрифт марок помещений уже уменьшен:', bylo)
    finally:
        try:
            fd.Close(False)
        except Exception:
            pass


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    try:
        umenshit_shrift_marki(log)
    except Exception as ex:
        log(u'шрифт марок помещений не изменён:', ex)
    sym = tip_marki(*MARKA_STOYAKA)
    if sym is None:
        log(u'НЕТ типа марки', MARKA_STOYAKA)
        return
    with kvv.Tranzakciya(doc, u'КВВ: единицы размера труб', log):
        # размер трубы в марках — целыми миллиметрами («Ø25», а не «Ø25.00»)
        u = doc.GetUnits()
        fo = DB.FormatOptions(DB.UnitTypeId.Millimeters)
        fo.Accuracy = 1.0
        u.SetFormatOptions(DB.SpecTypeId.PipeSize, fo)
        doc.SetUnits(u)
    with kvv.Tranzakciya(doc, u'КВВ: марки стояков', log):
        # свои марки прошлого запуска
        ids = [m.Id for m in DB.FilteredElementCollector(doc).OfClass(DB.IndependentTag)
               if m.GetTypeId() == sym.Id]
        if ids:
            doc.Delete(List[DB.ElementId](ids))
        log(u'удалено старых марок стояков', len(ids))
        st = truby_stoyakov(g, log)
        for imya, truby in st.items():
            nomer = imya.split(u'-')[-1]
            for t in truby:
                p = t.LookupParameter(u'ADSK_Номер стояка')
                if p is not None and not p.IsReadOnly:
                    p.Set(nomer)
        n = 0
        po_vidam = {}
        for nm in PLANY + SHEMY:
            v = vid(nm)
            if v is None:
                log(u'нет вида', nm)
                continue
            sist = u'В1' if nm.startswith(u'В1') else u'К1'
            for imya, truby in sorted(st.items()):
                if (u'.%s-' % sist) not in imya:
                    continue
                if isinstance(v, DB.View3D):
                    t = truby[-2] if len(truby) > 1 else truby[-1]      # верхний этаж (без вытяжной части)
                else:
                    # середина этажа (не отметка тройника — на ней стык двух участков); в подвале — под перекрытием
                    z = v.GenLevel.Elevation + 1.6 * M if v.GenLevel.Elevation >= -1e-6 else -0.2 * M
                    t, d_min = None, None
                    for tt in truby:
                        c = tt.Location.Curve
                        z0, z1 = sorted((c.GetEndPoint(0).Z, c.GetEndPoint(1).Z))
                        if z0 <= z <= z1:
                            t, d_min = tt, 0.0
                            break
                        # в подвале у стояка К1 на -0,20 может оказаться фитинг — ближайший участок ниже нуля
                        if v.GenLevel.Elevation < -1e-6 and z1 <= 1e-6:
                            d = min(abs(z - z0), abs(z - z1))
                            if d_min is None or d < d_min:
                                t, d_min = tt, d
                    if t is None:
                        continue
                c = t.Location.Curve
                p = c.Evaluate(0.5, True)
                k = v.Scale / 100.0                    # вынос полки — в размерах листа, не модели
                golova = p + DB.XYZ(storona(p.X / M, g) * 1.4 * k * M, 0.9 * k * M, 0)
                try:
                    m = DB.IndependentTag.Create(doc, sym.Id, v.Id, DB.Reference(t), True,
                                                 DB.TagOrientation.Horizontal, golova)
                    m.TagHeadPosition = golova          # Revit иногда сбрасывает полку в начало координат
                    doc.Regenerate()
                    gp = m.TagHeadPosition
                    if math.hypot(gp.X - golova.X, gp.Y - golova.Y) > 0.5 * M:
                        log(u'  ПОЛКА МАРКИ НЕ НА МЕСТЕ:', nm, imya, u'(%.2f, %.2f)' % (gp.X / M, gp.Y / M))
                    n += 1
                    po_vidam.setdefault(nm, []).append(imya)
                except Exception as ex:
                    log(u'  марка не встала:', nm, imya, ex)
        log(u'марок стояков поставлено', n)
        doc.Regenerate()
        for nm, sp in po_vidam.items():
            log(u'  ', nm, u':', u', '.join(sp))
        for m in DB.FilteredElementCollector(doc).OfClass(DB.IndependentTag):
            if m.GetTypeId() == sym.Id:
                log(u'  пример текста марки:', m.TagText, u'| вид', doc.GetElement(m.OwnerViewId).Name)
                break
    with kvv.Tranzakciya(doc, u'КВВ: помещения', log):
        pomescheniya(g, log)
    tr = kvv.load_json('calc', 'trassa_v3.json')
    with kvv.Tranzakciya(doc, u'КВВ: оформление планов и схем', log):
        kvv_oform.oformit_vse(doc, g, tr, dict((nm, vid(nm)) for nm in PLANY),
                              dict((nm, vid(nm)) for nm in SHEMY), sym, log)


kvv.run("08_annotacii", main)
