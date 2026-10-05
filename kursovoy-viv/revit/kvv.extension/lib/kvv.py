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


def xyz(x, y, z=0.0):
    """Точка из метров."""
    from Autodesk.Revit.DB import XYZ
    return XYZ(x * M, y * M, z * M)


def po_imeni(doc, cls, nm):
    from Autodesk.Revit.DB import FilteredElementCollector, Element
    for e in FilteredElementCollector(doc).OfClass(cls):
        if Element.Name.GetValue(e) == nm:
            return e
    return None


def simvol(doc, fam, tip=None):
    from Autodesk.Revit.DB import FilteredElementCollector, FamilySymbol, Element
    for s in FilteredElementCollector(doc).OfClass(FamilySymbol):
        if s.FamilyName == fam and (tip is None or Element.Name.GetValue(s) == tip):
            if not s.IsActive:
                s.Activate()
            return s
    return None


def urovni(doc):
    from Autodesk.Revit.DB import FilteredElementCollector, Level
    return dict((l.Name, l) for l in FilteredElementCollector(doc).OfClass(Level))


class Tranzakciya(object):
    """with Tranzakciya(doc, 'имя'): ... — предупреждения Revit удаляются, чтобы не всплывали окна."""

    def __init__(self, doc, name, log=None):
        from Autodesk.Revit import DB
        self.t = DB.Transaction(doc, name)
        self.doc, self.log = doc, log
        self.oshibki = 0

    def __enter__(self):
        from Autodesk.Revit import DB
        tr = self

        class Glush(DB.IFailuresPreprocessor):
            def PreprocessFailures(self, fa):
                est_oshibki = False
                for f in fa.GetFailureMessages():
                    if f.GetSeverity() == DB.FailureSeverity.Warning:
                        fa.DeleteWarning(f)
                        continue
                    est_oshibki = True
                    tr.oshibki += 1
                    if tr.log is not None:
                        tr.opisat(f)
                if est_oshibki and tr.log is not None:
                    # ошибки — в журнал, транзакция откатывается без диалога
                    return DB.FailureProcessingResult.ProceedWithRollBack
                return DB.FailureProcessingResult.Continue

        self.t.Start()
        opt = self.t.GetFailureHandlingOptions()
        opt.SetFailuresPreprocessor(Glush())
        opt.SetClearAfterRollback(True)
        self.t.SetFailureHandlingOptions(opt)
        return self.t

    def opisat(self, f):
        """Ошибка Revit в журнал: текст, элементы, их положение и комментарий."""
        from Autodesk.Revit import DB
        chasti = [f.GetDescriptionText()]
        for eid in list(f.GetFailingElementIds()) + list(f.GetAdditionalElementIds()):
            e = self.doc.GetElement(eid)
            if e is None:
                chasti.append(u'id %d (нет)' % eid.IntegerValue)
                continue
            loc = getattr(e, 'Location', None)
            gde = u''
            if isinstance(loc, DB.LocationCurve):
                a, b = loc.Curve.GetEndPoint(0), loc.Curve.GetEndPoint(1)
                gde = u'(%.3f, %.3f, %.3f)-(%.3f, %.3f, %.3f) L=%.1f мм' % (
                    a.X / M, a.Y / M, a.Z / M, b.X / M, b.Y / M, b.Z / M, a.DistanceTo(b) / MM)
            elif isinstance(loc, DB.LocationPoint):
                a = loc.Point
                gde = u'(%.3f, %.3f, %.3f)' % (a.X / M, a.Y / M, a.Z / M)
            chasti.append(u'id %d %s %s' % (eid.IntegerValue, e.Name, gde))
        self.log(u'  ОШИБКА REVIT: ' + u' | '.join(chasti))

    def __exit__(self, et, ev, tb):
        from Autodesk.Revit import DB
        if et is None:
            st = self.t.Commit()
            if st != DB.TransactionStatus.Committed:
                msg = u'транзакция «%s» НЕ зафиксирована (%s), ошибок Revit: %d' % (self.t.GetName(), st, self.oshibki)
                if self.log is not None:
                    self.log(msg)
                raise Exception(msg)
        else:
            self.t.RollBack()
        return False


def run(name, fun):
    """Выполнить fun(log) с журналом и перехватом ошибок."""
    log = Log(name)
    try:
        fun(log)
    except Exception:
        log.exc()
    finally:
        log.close()
