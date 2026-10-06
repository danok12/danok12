# -*- coding: utf-8 -*-
"""Канализация К1: поэтажные отводы, стояки с вытяжной частью, сборный трубопровод и выпуски;
прочистки в начале горизонтальных участков и ревизии на стояках."""
from pyrevit import HOST_APP
import kvv
import kvv_seti
reload(kvv)
reload(kvv_seti)

doc = HOST_APP.doc


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    try:
        kvv_seti.sml_kosoy_troynik(doc, log, g['tipy_trub'][u'sml'])
    except Exception as ex:
        log(u'косой тройник SML не подготовлен:', ex)
    with kvv.Tranzakciya(doc, u'КВВ: система К1', log):
        kvv_seti.udalit(doc, u'КВВ-К1', log)
        kvv_seti.Stroitel(doc, g, log).sistema_celikom(u'K1')
    # отдельной транзакцией: если прочистки или ревизии не встанут, построенная система К1 остаётся
    try:
        with kvv.Tranzakciya(doc, u'КВВ: прочистки и ревизии К1', log):
            kvv_seti.prochistki_revizii(doc, g, log)
    except Exception as ex:
        log(u'прочистки и ревизии откатены:', ex)


kvv.run('06_k1', main)
