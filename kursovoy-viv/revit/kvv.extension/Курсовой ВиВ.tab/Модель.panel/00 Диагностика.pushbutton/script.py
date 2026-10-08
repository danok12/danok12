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


def main(log):
    log(u'документ:', doc.Title)
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
