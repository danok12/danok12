# -*- coding: utf-8 -*-
"""Создать рабочий проект на шаблоне ADSK ВК и открыть его.

Если файл модели уже есть — просто открыть. Сохранение дальше выполняет пользователь.
"""
import os
from pyrevit import HOST_APP
from Autodesk.Revit import DB
import kvv
reload(kvv)

app = HOST_APP.app
uiapp = HOST_APP.uiapp


def main(log):
    if not os.path.isdir(kvv.MODEL_DIR):
        os.makedirs(kvv.MODEL_DIR)
    if not os.path.exists(kvv.MODEL):
        log(u'создаю проект по шаблону', kvv.SHABLON_VK)
        doc = app.NewProjectDocument(kvv.SHABLON_VK)
        opt = DB.SaveAsOptions()
        opt.OverwriteExistingFile = False
        doc.SaveAs(kvv.MODEL, opt)
        doc.Close(False)
        log(u'сохранён', kvv.MODEL)
    uiapp.OpenAndActivateDocument(kvv.MODEL)
    log(u'открыт', kvv.MODEL)


kvv.run('01_proekt', main)
