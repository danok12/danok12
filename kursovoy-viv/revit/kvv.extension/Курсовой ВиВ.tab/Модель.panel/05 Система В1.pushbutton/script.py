# -*- coding: utf-8 -*-
"""Водопровод В1: ввод, водомерный узел, насосная установка, магистраль, стояки, квартирные узлы и разводка."""
from pyrevit import HOST_APP
import kvv
import kvv_seti
reload(kvv)
reload(kvv_seti)

doc = HOST_APP.doc


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    with kvv.Tranzakciya(doc, u'КВВ: система В1', log):
        kvv_seti.udalit(doc, u'КВВ-В1', log)
        kvv_seti.Stroitel(doc, g, log).sistema_celikom(u'V1')


kvv.run('05_v1', main)
