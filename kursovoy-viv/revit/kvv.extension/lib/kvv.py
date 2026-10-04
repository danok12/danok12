# -*- coding: utf-8 -*-
"""Общие функции скриптов курсового ВиВ (IronPython 2.7, pyRevit).

Скрипты кнопок пишут журнал в kursovoy-viv/revit/log/<имя>.txt, чтобы результат можно было
прочитать вне Revit, и читают исходные данные из calc/rezultaty_v3.json и revit/geometriya_v3.json.
"""
import io
import json
import os
import traceback

LIB = os.path.dirname(os.path.abspath(__file__))
REVIT = os.path.dirname(os.path.dirname(LIB))          # kursovoy-viv/revit
KURS = os.path.dirname(REVIT)                          # kursovoy-viv
LOG_DIR = os.path.join(REVIT, 'log')
MODEL_DIR = os.path.join(REVIT, 'model')
SEMEYSTVA = os.path.join(os.environ['USERPROFILE'], 'Desktop', u'Семейства ВК')
SHABLON_VK = os.path.join(SEMEYSTVA, u'ADSK_RU_Шаблон_ВК_BIM2B_r2021_v2.1.4.rte')
SHABLON_AR = os.path.join(SEMEYSTVA, u'ADSK_RU_Шаблон_АР_BIM2B_r2021_v2.2.3.rte')
MODEL = os.path.join(MODEL_DIR, u'KR_ViV_v3.rvt')

MM = 1.0 / 304.8       # мм -> футы
M = 1000.0 * MM        # м -> футы


def load_json(*parts):
    with io.open(os.path.join(KURS, *parts), encoding='utf-8') as f:
        return json.load(f)


def _u(x):
    """В IronPython str и unicode — один тип; перекодировать нечего, только привести к строке."""
    if isinstance(x, basestring):
        return x
    try:
        return unicode(x)
    except Exception:
        return repr(x)


class Log(object):
    """Журнал: печатает в окно pyRevit и пишет в файл."""

    def __init__(self, name):
        if not os.path.isdir(LOG_DIR):
            os.makedirs(LOG_DIR)
        self.path = os.path.join(LOG_DIR, name + '.txt')
        self.f = io.open(self.path, 'w', encoding='utf-8')

    def __call__(self, *a):
        s = u' '.join(_u(x) for x in a)
        # без print: иначе pyRevit открывает окно вывода, а оно перехватывает фокус ленты
        self.f.write(s + u'\n')
        self.f.flush()

    def exc(self):
        self(u'ОШИБКА:\n' + _u(traceback.format_exc()))

    def close(self):
        self(u'== конец ==')
        self.f.close()


def run(name, fun):
    """Выполнить fun(log) с журналом и перехватом ошибок."""
    log = Log(name)
    try:
        fun(log)
    except Exception:
        log.exc()
    finally:
        log.close()
