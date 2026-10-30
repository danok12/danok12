# -*- coding: utf-8 -*-
"""Проверка модели перед выдачей: шрифт ГОСТ («GOST Common», как на листах преподавателя) во всех типах текста,
размеров, отметок, таблиц и в семействах аннотаций; коллизии сетей (В1 с К1, трубы с приборами, трубы вдоль стен,
приборы в стенах). Журнал — revit/log/00_proverka.txt.

(Прежняя выгрузка шаблонов ВК/АР и габаритов семейств сохранена в revit/log/00_diagnostika_*.txt.)
"""
from pyrevit import HOST_APP
from Autodesk.Revit import DB
import kvv
import kvv_proverka
reload(kvv)
reload(kvv_proverka)

doc = HOST_APP.doc

KATEGORII_ANNOTACIY = [DB.BuiltInCategory.OST_PipeTags, DB.BuiltInCategory.OST_RoomTags,
                       DB.BuiltInCategory.OST_TitleBlocks, DB.BuiltInCategory.OST_ViewportLabel,
                       DB.BuiltInCategory.OST_GenericAnnotation, DB.BuiltInCategory.OST_PipeFittingTags,
                       DB.BuiltInCategory.OST_PipeAccessoryTags, DB.BuiltInCategory.OST_PlumbingFixtureTags,
                       DB.BuiltInCategory.OST_MechanicalEquipmentTags, DB.BuiltInCategory.OST_GridHeads,
                       DB.BuiltInCategory.OST_LevelHeads, DB.BuiltInCategory.OST_SpotElevSymbols]


def rezhim_zapuska():
    """revit/00_rezhim.txt: «svobodnye» — только проверка висящих элементов сетей; «siroty» — удалить висящие
    фасонные части и арматуру без метки КВВ и проверить. Файл после чтения удаляется."""
    import io
    import os
    put = os.path.join(kvv.REVIT, u'00_rezhim.txt')
    if not os.path.isfile(put):
        return u''
    with io.open(put, encoding='utf-8') as f:
        r = f.read().strip()
    os.remove(put)
    return r


def main(log):
    log(u'документ:', doc.Title)
    rezhim = rezhim_zapuska()
    if rezhim == u'svobodnye':
        kvv_proverka.svobodnye(doc, log)
        return
    if rezhim.startswith(u'vid '):
        kvv_proverka.vid_diag(doc, rezhim[4:].strip(), log)
        return
    if rezhim == u'metki':
        import kvv_seti
        reload(kvv_seti)
        with kvv.Tranzakciya(doc, u'КВВ: метки деталей', log):
            kvv_seti.pometit_avto(doc, log)
        return
    if rezhim.startswith(u'soed '):
        kvv_proverka.soed_diag(doc, [x.strip() for x in rezhim[5:].split(u';') if x.strip()], log)
        return
    if rezhim.startswith(u'vlozh '):
        kvv_proverka.vlozhennye(doc, HOST_APP.app, [x.strip() for x in rezhim[6:].split(u';')], log)
        return
    if rezhim == u'klass_adl':
        import kvv_seti
        reload(kvv_seti)
        kvv_seti.klass_soediniteley(doc, [u'ADL_Задвижка_KR11', u'ADL_Фильтр сетчатый фланцевый_IS40',
                                          u'ADL_Клапан обратный фланцевый_RD16',
                                          u'ADL_Вставка гибкая фланцевая_FC10_DN32-500_PN10_Ф-Ф'], log)
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim.startswith(u'topo '):
        kvv_proverka.topo_tochki(doc, rezhim[5:], log)
        return
    if rezhim.startswith(u'snimok '):
        kvv_proverka.snimok(doc, rezhim[7:], log)
        return
    if rezhim == u'seti_vidy':
        kvv_proverka.seti_na_vidah(doc, log)
        return
    if rezhim == u'fasad':
        kvv_proverka.fasad(doc, log)
        return
    if rezhim == u'sistemy':
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim.startswith(u'klassy '):
        kvv_proverka.klassy_soediniteley(doc, [x.strip() for x in rezhim[7:].split(u';')], log)
        return
    if rezhim.startswith(u'tochka '):
        kvv_proverka.tochka_sistemy(doc, rezhim[7:], log)
        return
    if rezhim == u'proba_flex':
        kvv_proverka.proba_flex(doc, log)
        return
    if rezhim.startswith(u'uzel '):
        kvv_proverka.vid_uzla(doc, HOST_APP.uidoc, rezhim[5:], log)
        return
    if rezhim.startswith(u'modul '):
        kvv_proverka.modul_semeystva(doc, HOST_APP.app, rezhim[6:], log)
        return
    if rezhim == u'sobrat':
        kvv_proverka.sobrat_sistemu(doc, log)
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim == u'naznachit':
        kvv_proverka.naznachit_sistemu(doc, log)
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim == u'udalit_sist':
        kvv_proverka.udalit_sistemy(doc, log)
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim == u'perepodkl':
        kvv_proverka.perepodklyuchit(doc, log)
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim == u'proba_sist2':
        kvv_proverka.proba_sistem(doc, log, s_pravilom=True)
        return
    if rezhim == u'proba_sist':
        kvv_proverka.proba_sistem(doc, log)
        return
    if rezhim == u'obedinit':
        with kvv.Tranzakciya(doc, u'КВВ: одна система В1', log):
            kvv_proverka.obedinit_sistemy(doc, log)
        kvv_proverka.sistemy(doc, log)
        return
    if rezhim == u'proba':
        kvv_proverka.proba_kombi(doc, log)
        return
    if rezhim == u'pribory':
        kvv_proverka.pribory_diag(doc, log)
        return
    if rezhim == u'fitingi':
        kvv_proverka.fitingi(doc, log)
        return
    if rezhim == u'siroty':
        import kvv_seti
        reload(kvv_seti)
        with kvv.Tranzakciya(doc, u'КВВ: висящие детали', log):
            kvv_seti.udalit_siroty(doc, log)
        kvv_proverka.svobodnye(doc, log)
        return
    kvv_proverka.shrift_v_semeystvah(doc, log, KATEGORII_ANNOTACIY)
    with kvv.Tranzakciya(doc, u'КВВ: шрифт ГОСТ', log):
        kvv_proverka.shrift_v_proekte(doc, log)
    kvv_proverka.kollizii(doc, log)
    # рабочие 3D-виды для осмотра модели (не на листах) — после проверки открывается вид здания
    vidy = []
    with kvv.Tranzakciya(doc, u'КВВ: 3D-виды для осмотра', log):
        vidy = kvv_proverka.vidy_3d(doc, log)
    if vidy:
        try:
            HOST_APP.uidoc.ActiveView = vidy[0]
        except Exception as ex:
            log(u'3D-вид не открыт:', ex)


kvv.run('00_proverka', main)
