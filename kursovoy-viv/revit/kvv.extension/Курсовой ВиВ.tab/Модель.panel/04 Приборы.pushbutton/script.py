# -*- coding: utf-8 -*-
"""Санитарные приборы во всех квартирах, насосная установка, противопожарные муфты на стояках К1."""
from pyrevit import HOST_APP
import kvv
import kvv_seti
reload(kvv)
reload(kvv_seti)

doc = HOST_APP.doc


def main(log):
    g = kvv.load_json('revit', 'geometriya_v3.json')
    with kvv.Tranzakciya(doc, u'КВВ: приборы', log):
        for pref in (u'КВВ-П', u'КВВ-О', u'КВВ-М'):
            kvv_seti.udalit(doc, pref, log)
        s = kvv_seti.Stroitel(doc, g, log)
        s.pribory()
        s.otchet()


kvv.run('04_pribory', main)
