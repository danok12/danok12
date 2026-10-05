# -*- coding: utf-8 -*-
"""Рабочий файл модели: сохранить активный несохранённый проект в revit/model/KR_ViV_v3.rvt
(если файла ещё нет) или сохранить уже открытый файл модели."""
import os
from pyrevit import HOST_APP
from Autodesk.Revit import DB
import kvv
reload(kvv)

doc = HOST_APP.doc


def main(log):
    if not os.path.isdir(kvv.MODEL_DIR):
        os.makedirs(kvv.MODEL_DIR)
    if doc.PathName:
        doc.Save()
        log(u'сохранён', doc.PathName)
        return
    opt = DB.SaveAsOptions()
    opt.OverwriteExistingFile = False
    doc.SaveAs(kvv.MODEL, opt)
    log(u'сохранён как', kvv.MODEL)


kvv.run('01_proekt', main)
