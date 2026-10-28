# -*- coding: utf-8 -*-
"""Водопровод В1: ввод, водомерный узел, насосная установка на фундаменте, магистраль, стояки, квартирные узлы
и разводка."""
from pyrevit import HOST_APP
import kvv
import kvv_seti
reload(kvv)
reload(kvv_seti)

doc = HOST_APP.doc


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    # общедомовой счётчик ВСХН-25 «Тепловодомер» (вне транзакции: загрузка семейства)
    if kvv_seti.tvm_schetchik(doc, HOST_APP.app, log) is None:
        log(u'ВНИМАНИЕ: счётчик TVM не загружен — водомерный узел встанет без счётчика')
    # кран на опуске узла учёта — семейство на рабочей плоскости (вне транзакции: правка семейства)
    kvv_seti.rabochaya_ploskost(doc, (u'VALTEC_VT.215.N_КранШаровой ВР-НР',), log)
    with kvv.Tranzakciya(doc, u'КВВ: система В1', log):
        kvv_seti.udalit(doc, u'КВВ-В1', log)
        # установка на фундамент до трубопроводов: патрубки берутся из модели (поднятые на 270 мм)
        kvv_seti.fundament_nasosa(doc, log)
        kvv_seti.Stroitel(doc, g, log).sistema_celikom(u'V1')
        tr = kvv.load_json('calc', 'trassa_v3.json')
        if 'x_shov' in tr:
            kvv_seti.gibkaya_vstavka(doc, log, tr['x_shov'], u'КВВ-В1')


kvv.run('05_v1', main)
