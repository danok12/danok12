# -*- coding: utf-8 -*-
"""Виды для листов: планы типового этажа и подвала (В1, К1), аксонометрические схемы В1 и К1, разрез 1-1 по шахте
кв. А (лист 4).

Шаблоны видов — из шаблона ADSK ВК. Повторный запуск пересоздаёт виды (по имени).
"""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
from System.Collections.Generic import List
import kvv
import kvv_oform
reload(kvv)
reload(kvv_oform)

doc = HOST_APP.doc
M = kvv.M

MASSHTAB = 100      # как в образце; каждый вид на своём листе: планы (46 м) — А2, схемы — А1 (на А2 не входят)
PLANY = [  # имя вида, уровень, шаблон, тип вида
    (u'В1_План типового этажа', u'Этаж 02', u'О_ПЭ_Водопровод', u'О_ПЭ_Водопровод'),
    (u'В1_План подвала', u'Подвал', u'О_ПЭ_Водопровод', u'О_ПЭ_Водопровод'),
    (u'К1_План типового этажа', u'Этаж 02', u'О_ПЭ_Канализация', u'О_ПЭ_Канализация'),
    (u'К1_План подвала', u'Подвал', u'О_ПЭ_Канализация', u'О_ПЭ_Канализация'),
]
SHEMY = [(u'В1_Аксонометрическая схема', u'О_3D_Система В1', u'ADSK_Водопровод_В1'),
         (u'К1_Аксонометрическая схема', u'О_3D_Система К1', u'ADSK_Канализация_К1')]

RAZREZ = u'1-1'               # разрез по шахте кв. А секции 1: имя вида — то, что пишется у секущей линии на планах
MASSHTAB_RAZREZA = 50


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


VIDNO_NA_SHEME = (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting,
                  DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_MechanicalEquipment,
                  DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel)   # + фундамент установки


def tolko_sistema(v, metka_svoya, log):
    """Аксонометрия: видны трубы, фитинги, арматура, оборудование и сантехприборы (полутоном, как в образце
    преподавателя); трубы другой системы скрыты."""
    v.ViewTemplateId = DB.ElementId.InvalidElementId
    pol = DB.OverrideGraphicSettings()
    pol.SetHalftone(True)
    v.SetCategoryOverrides(DB.ElementId(DB.BuiltInCategory.OST_PlumbingFixtures), pol)
    vidno = set(int(c) for c in VIDNO_NA_SHEME)
    n = 0
    for c in doc.Settings.Categories:
        if c.CategoryType != DB.CategoryType.Model:
            continue
        if c.Id.IntegerValue in vidno:
            if v.CanCategoryBeHidden(c.Id) and v.GetCategoryHidden(c.Id):
                v.SetCategoryHidden(c.Id, False)          # могла остаться скрытой с прошлого запуска
            continue
        try:
            if v.CanCategoryBeHidden(c.Id):
                v.SetCategoryHidden(c.Id, True)
                n += 1
        except Exception:
            pass
    chuzhie = []
    for e in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        except Exception:
            continue
        if p is None or not p.HasValue:
            continue
        s_ = p.AsString() or u''
        chuzhoe = (s_.startswith(u'КВВ-В1') or s_.startswith(u'КВВ-К1')) and not s_.startswith(metka_svoya)
        if metka_svoya == u'КВВ-К1' and (s_.startswith(u'КВВ-О') or s_.startswith(u'КВВ-Ф')):   # установка — только на В1
            chuzhoe = True
        if metka_svoya == u'КВВ-В1' and s_.startswith(u'КВВ-М'):       # противопожарные муфты — на стояках К1
            chuzhoe = True
        if chuzhoe and e.CanBeHidden(v):
            chuzhie.append(e.Id)
    if chuzhie:
        v.HideElements(List[DB.ElementId](chuzhie))
    # опорные плоскости кранов узла учёта (kvv_seti.na_ploskost) на листах не нужны
    for bic in (DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_Grids, DB.BuiltInCategory.OST_CLines):
        c = doc.Settings.Categories.get_Item(bic)
        if v.CanCategoryBeHidden(c.Id):
            v.SetCategoryHidden(c.Id, True)
    log(u'   скрыто категорий', n, u'| элементов другой системы', len(chuzhie))
    if metka_svoya == u'КВВ-К1':
        kvv.armatura_detalno(doc, v, log)             # противопожарные муфты на стояках видны объёмом


def gruppirovka_kak_u(v, obrazec, log):
    """Параметры группировки диспетчера проекта («Назначение вида», «Раздел» и т. п.) — как у плана той же системы."""
    for p in obrazec.Parameters:
        nm = p.Definition.Name
        if p.StorageType != DB.StorageType.String or not (u'Назначение' in nm or u'Раздел' in nm):
            continue
        q = v.LookupParameter(nm)
        if q is not None and not q.IsReadOnly and p.AsString():
            q.Set(p.AsString())
            log(u'   ', nm, u'=', p.AsString())


def marki_osey(v, log):
    """Марки осей не налезают: у близких пар (< 1,2 м) марка второй оси — сверху; у остальных — снизу (буквенные
    оси — слева)."""
    osi = [gr for gr in DB.FilteredElementCollector(doc).OfClass(DB.Grid)]
    ver = sorted([gr for gr in osi if abs(gr.Curve.Direction.Y) > 0.9], key=lambda gr: gr.Curve.GetEndPoint(0).X)
    verh = set()
    for a, b in zip(ver[:-1], ver[1:]):
        if b.Curve.GetEndPoint(0).X - a.Curve.GetEndPoint(0).X < 1.3 * M and a.Id not in verh:
            verh.add(b.Id)
    for gr in osi:
        niz = gr.Curve.GetEndPoint(0).Y < gr.Curve.GetEndPoint(1).Y          # End0 — нижний (левый) конец
        # по проверке на листе: DatumEnds.End1 — нижний конец цифровых осей и левый — буквенных
        k0, k1 = (DB.DatumEnds.End1, DB.DatumEnds.End0) if niz or abs(gr.Curve.Direction.Y) < 0.9 else             (DB.DatumEnds.End0, DB.DatumEnds.End1)
        if gr.Id in verh:
            k0, k1 = k1, k0
        try:
            gr.ShowBubbleInView(k0, v)
            gr.HideBubbleInView(k1, v)
        except Exception as ex:
            log(u'  марка оси', gr.Name, ex)


def marka_osi_8mm(log):
    """Марки осей — кружок Ø8 мм (Ø10 на А3 в 1:200 налезают)."""
    sym = None
    for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_GridHeads):
        if u'Ø8' in DB.Element.Name.GetValue(s_):
            sym = s_
    if sym is None:
        log(u'нет марки оси Ø8')
        return
    tipy = set(gr.GetTypeId() for gr in DB.FilteredElementCollector(doc).OfClass(DB.Grid))
    for tid in tipy:
        t = doc.GetElement(tid)
        p = t.get_Parameter(DB.BuiltInParameter.GRID_HEAD_TAG)
        if p and not p.IsReadOnly:
            p.Set(sym.Id)
    log(u'марка осей:', sym.FamilyName, DB.Element.Name.GetValue(sym))


def obrezka_3d(v, pref, log, zx=5.0, zy=2.5, zx_lev=7.0):
    """Схема: подрезка по габариту своей системы (+ приборы, + насосная установка у В1) с запасом под отметки и
    выноски; аннотации за подрезкой не раздувают вид на листе."""
    tr = v.CropBox.Transform
    inv = tr.Inverse
    mn, mx = [1e18] * 3, [-1e18] * 3
    n = 0
    for e in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        except Exception:
            continue
        s_ = (p.AsString() or u'') if p is not None and p.HasValue else u''
        if not (s_.startswith(pref) or s_.startswith(u'КВВ-П') or (pref == u'КВВ-В1' and s_.startswith(u'КВВ-О'))):
            continue
        bb = e.get_BoundingBox(None)
        if bb is None:
            continue
        n += 1
        for x in (bb.Min.X, bb.Max.X):
            for y in (bb.Min.Y, bb.Max.Y):
                for z in (bb.Min.Z, bb.Max.Z):
                    q = inv.OfPoint(DB.XYZ(x, y, z))
                    for i, c in enumerate((q.X, q.Y, q.Z)):
                        mn[i] = min(mn[i], c)
                        mx[i] = max(mx[i], c)
    if n == 0:
        log(u'   подрезка схемы: нет элементов', pref)
        return
    # запас: по горизонтали — под полки отметок у крайних стояков, по вертикали — под верхние отметки
    nb = DB.BoundingBoxXYZ()
    nb.Transform = tr
    nb.Min = DB.XYZ(mn[0] - zx_lev * M, mn[1] - zy * M, mn[2] - 1 * M)       # слева — выноски у ввода и крана
    nb.Max = DB.XYZ(mx[0] + zx * M, mx[1] + zy * M, mx[2] + 1 * M)
    v.CropBox = nb
    v.CropBoxActive = True
    v.CropBoxVisible = False
    p = v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    if p is not None and not p.IsReadOnly:
        p.Set(1)
    try:
        crsm = v.GetCropRegionShapeManager()
        for a in ('LeftAnnotationCropOffset', 'RightAnnotationCropOffset', 'TopAnnotationCropOffset',
                  'BottomAnnotationCropOffset'):
            setattr(crsm, a, 3 * kvv.MM)
    except Exception as ex:
        log(u'   отступы подрезки аннотаций не заданы:', ex)
    log(u'   подрезка схемы: элементов', n, u'| %.1f x %.1f м' % ((mx[0] - mn[0]) / M + zx + zx_lev,
                                                             (mx[1] - mn[1]) / M + 2 * zy))


def sploshnye_steny(v, log):
    """Стены на плане — сплошным телом, как в образце: детализация «Грубая» (без слоёв штукатурки и утеплителя)
    и «Отображение соединения стен» = очищать все соединения (линия стыка пропадает и между разными типами).
    Задаётся и в шаблоне вида (если он управляет этими свойствами), и в самом виде."""
    obekty = [v]
    if v.ViewTemplateId != DB.ElementId.InvalidElementId:
        obekty.insert(0, doc.GetElement(v.ViewTemplateId))
    for o in obekty:
        p = o.get_Parameter(DB.BuiltInParameter.VIEW_DETAIL_LEVEL)
        if p is not None and not p.IsReadOnly:
            p.Set(int(DB.ViewDetailLevel.Coarse))
    doc.Regenerate()
    for o in obekty:
        for q in o.Parameters:
            nm = q.Definition.Name.lower()
            if not (u'соединен' in nm and u'стен' in nm) or q.IsReadOnly or q.StorageType != DB.StorageType.Integer:
                continue
            bylo = q.AsValueString()
            for znach in (0, 1, 2):
                try:
                    q.Set(znach)
                except Exception:
                    continue
                if u'все' in (q.AsValueString() or u'').lower() or u'all' in (q.AsValueString() or u'').lower():
                    break
            log(u'   %s: «%s» %s → %s' % (DB.Element.Name.GetValue(o), q.Definition.Name, bylo, q.AsValueString()))
    log(u'   детализация', DB.Element.Name.GetValue(v), v.DetailLevel)


def obrezka(v, x0, y0, x1, y1):
    bb = DB.BoundingBoxXYZ()
    bb.Min = DB.XYZ(x0 * M, y0 * M, -100)
    bb.Max = DB.XYZ(x1 * M, y1 * M, 100)
    v.CropBox = bb
    v.CropBoxActive = True
    v.CropBoxVisible = False


def razrez_shahty(g, log):
    """Разрез 1-1 по шахте кв. А секции 1 — показать, что крестовина К1 и отводы над плитой перекрытия, а не в ней
    (преподаватель считал, что канализация «в полу»). Плоскость поперёк здания на 0,1 м за осью стояков (через
    унитаз), взгляд на юг: наружная стена, прослойка и перегородка шахты, стояки В1 и К1, крестовина 110×50 над
    полом, отвод от унитаза, опуск узла учёта В1 с арматурой; внизу — сборный К1 под потолком подвала."""
    st = dict((s_['sys'], s_) for s_ in g['stoyaki'] if s_['x'] < 5.0)
    xk, yk, xv = st['K1']['x'], st['K1']['y'], st['V1']['x']
    yc, xo, zo = yk + 0.10, 0.85, 0.3
    t = DB.Transform.Identity
    t.Origin = kvv.xyz(xo, yc, zo)
    # Revit смотрит вдоль +BasisZ рамки, секущая плоскость — на Min.Z, вправо на листе — −BasisX (проверено:
    # при BasisZ = +y разрез смотрел на север и резал кухню). Взгляд на юг: BasisZ = −y, вправо — на запад
    t.BasisX = DB.XYZ(1, 0, 0)
    t.BasisY = DB.XYZ.BasisZ
    t.BasisZ = DB.XYZ(0, -1, 0)
    box = DB.BoundingBoxXYZ()
    box.Transform = t
    # по x от −0,7 (наружная стена) до 2,4 (ванна), по z от −1,1 (сборный К1 под потолком подвала) до +1,75 (тройник
    # узла учёта на +1,5), вглубь на юг — 2,7 м (умывальник, мойка)
    box.Min = DB.XYZ((-0.7 - xo) * M, (-1.1 - zo) * M, 0.0)
    box.Max = DB.XYZ((2.4 - xo) * M, (1.75 - zo) * M, 2.7 * M)
    # направление разреза рамкой подрезки не меняется — прежний вид удаляется (с листа его снимает и ставит 09)
    v = vid_po_imeni(RAZREZ)
    if v is not None:
        doc.Delete(v.Id)
        doc.Regenerate()
    vft = tip_vida(None, DB.ViewFamily.Section)
    v = DB.ViewSection.CreateSection(doc, vft.Id, box)
    v.Name = RAZREZ
    v.ViewTemplateId = DB.ElementId.InvalidElementId
    v.Scale = MASSHTAB_RAZREZA
    v.DetailLevel = DB.ViewDetailLevel.Fine
    v.CropBoxActive = True
    v.CropBoxVisible = False
    for nm, zn in ((u'ADSK_Назначение вида', u'Оформленные виды'), (u'ADSK_Штамп Раздел проекта', u'Канализация')):
        p = v.LookupParameter(nm)
        if p is not None and not p.IsReadOnly:
            p.Set(zn)
    # видны обе системы: фильтры вида (из типа вида) сняты; уровни и оси скрыты — отметки даны в выносках
    filtry = list(v.GetFilters())
    for fid in filtry:
        v.RemoveFilter(fid)
    for bic in (DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting,
                DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_PlumbingFixtures):
        cid = DB.ElementId(bic)
        if v.CanCategoryBeHidden(cid):
            v.SetCategoryHidden(cid, False)
    v.SetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_Levels), True)
    v.SetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_Grids), True)      # ось 1 тянулась через весь лист
    log(u'разрез: снято фильтров вида', len(filtry))
    doc.Regenerate()
    z_kr = min(k['z'] for k in g['kresty2'] if abs(k['x'] - xk) < 1e-3 and abs(k['y'] - yk) < 1e-3)
    n = 0          # выноски ставит 08 (kvv_oform.podpisi_razreza): его очистка удаляет тексты этого типа в проекте
    cb = v.CropBox
    log(u'разрез', RAZREZ, u'| 1:%d' % v.Scale, u'| %.1f x %.1f м, глубина %.1f м' % (
        (cb.Max.X - cb.Min.X) / M, (cb.Max.Y - cb.Min.Y) / M, (cb.Max.Z - cb.Min.Z) / M),
        u'| взгляд', v.ViewDirection, u'| крестовина на %.3f' % z_kr)


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    lv = kvv.urovni(doc)
    xs = [x for w in g['steny'] for x in (w['p1'][0], w['p2'][0])]
    X0, X1 = min(xs), max(xs)
    with kvv.Tranzakciya(doc, u'КВВ: виды', log):
        marka_osi_8mm(log)
        # существующие виды переиспользуются (открытый вид удалить нельзя)
        for nm, ur, shab, tip in PLANY:
            vft = tip_vida(tip, DB.ViewFamily.FloorPlan) or tip_vida(None, DB.ViewFamily.FloorPlan)
            v = vid_po_imeni(nm)
            if v is None:
                v = DB.ViewPlan.Create(doc, vft.Id, lv[ur].Id)
                v.Name = nm
            t = shablon(shab)
            if t:
                v.ViewTemplateId = t.Id
            else:
                log(u'НЕТ шаблона', shab)
            # масштаб и обрезка: шаблон может задавать масштаб — снимаем это свойство с шаблона на виде
            try:
                v.Scale = MASSHTAB
            except Exception as ex:
                log(u'масштаб задаёт шаблон:', ex)
            # подвал — ниже концов осей место под выноски «Водомерный узел», «Насосная установка» и марку ввода
            obrezka(v, X0 - 4.0, -6.0 if ur == u'Подвал' else -4.5, X1 + 4.0, 12.8 + 5.0)
            doc.Regenerate()
            marki_osey(v, log)
            try:
                sploshnye_steny(v, log)
            except Exception as ex:
                log(u'   стыки стен на плане не настроены:', ex)
            log(u'план', nm, u'| шаблон', shab if t else u'-', u'| тип', DB.Element.Name.GetValue(vft))
        try:
            razrez_shahty(g, log)
        except Exception:
            import traceback
            log(u'ОШИБКА разреза:', traceback.format_exc())
        vft3 = tip_vida(None, DB.ViewFamily.ThreeDimensional)
        for nm, shab, sist in SHEMY:
            v = vid_po_imeni(nm)
            if v is None:
                v = DB.View3D.CreateIsometric(doc, vft3.Id)
                v.Name = nm
            elif v.IsLocked:
                v.Unlock()
            tolko_sistema(v, u'КВВ-В1' if nm.startswith(u'В1') else u'КВВ-К1', log)
            plan = vid_po_imeni(u'В1_План типового этажа' if nm.startswith(u'В1') else u'К1_План типового этажа')
            if plan is not None:
                gruppirovka_kak_u(v, plan, log)
            # фронтальная изометрия по образцу: взгляд с юго-запада сверху (ось X вправо-вверх, Y — вглубь)
            eye = DB.XYZ(-60 * M, -80 * M, 70 * M)
            fwd = DB.XYZ(1, 1.35, -0.9).Normalize()
            right = fwd.CrossProduct(DB.XYZ.BasisZ).Normalize()
            up = right.CrossProduct(fwd).Normalize()
            v.SetOrientation(DB.ViewOrientation3D(eye, up, fwd))
            try:
                v.Scale = MASSHTAB
            except Exception:
                pass
            doc.Regenerate()
            obrezka_3d(v, u'КВВ-В1' if nm.startswith(u'В1') else u'КВВ-К1', log)
            v.SaveOrientationAndLock()
            doc.Regenerate()
            # блокировка растягивает глубину рамки подрезки (~200 м) — на листе вид становится выше; задать снова
            try:
                obrezka_3d(v, u'КВВ-В1' if nm.startswith(u'В1') else u'КВВ-К1', log)
                doc.Regenerate()
            except Exception as ex:
                log(u'   подрезка после блокировки не задана:', ex)
            try:
                pf = v.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_ACTIVE_FAR)
                if pf is not None and not pf.IsReadOnly:
                    pf.Set(0)
            except Exception:
                pass
            cb = v.CropBox
            pa = v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
            log(u'   после блокировки: подрезка', v.CropBoxActive, u'| %.1f x %.1f x %.1f м' % (
                (cb.Max.X - cb.Min.X) / M, (cb.Max.Y - cb.Min.Y) / M, (cb.Max.Z - cb.Min.Z) / M),
                u'| подрезка аннотаций', pa.AsInteger() if pa else u'-')
            try:
                crsm = v.GetCropRegionShapeManager()
                log(u'   отступы подрезки аннотаций, мм: л %.0f п %.0f в %.0f н %.0f' % tuple(
                    getattr(crsm, a) / kvv.MM for a in ('LeftAnnotationCropOffset', 'RightAnnotationCropOffset',
                                                         'TopAnnotationCropOffset', 'BottomAnnotationCropOffset')))
                log(u'   контур подрезки:', [u'(%.1f, %.1f, %.1f)' % (c.GetEndPoint(0).X / M, c.GetEndPoint(0).Y / M,
                                                                   c.GetEndPoint(0).Z / M)
                                            for c in crsm.GetCropShape()[0]])
            except Exception as ex:
                log(u'   отступы подрезки: нет', ex)
            tr_ = cb.Transform
            log(u'   оси подрезки: X', tr_.BasisX, u'Y', tr_.BasisY, u'Z', tr_.BasisZ, u'| вид: вправо', v.RightDirection,
                u'вверх', v.UpDirection, u'взгляд', v.ViewDirection)
            try:
                ol = v.Outline
                log(u'   вид на листе (Outline), мм: %.0f x %.0f' % ((ol.Max.U - ol.Min.U) / kvv.MM,
                                                                  (ol.Max.V - ol.Min.V) / kvv.MM))
            except Exception as ex:
                log(u'   Outline:', ex)
            log(u'схема', nm, u'| трубы, фитинги, арматура своей системы и сантехприборы (полутон)')


kvv.run('07_vidy', main)
