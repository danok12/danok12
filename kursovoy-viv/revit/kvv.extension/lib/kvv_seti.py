# -*- coding: utf-8 -*-
"""Построение приборов, арматуры и трубопроводов по geometriya_v3.json (IronPython, pyRevit).

Элементы помечаются в «Комментариях»: КВВ-П<id> — прибор, КВВ-О<id> — оборудование, КВВ-М — муфта,
КВВ-В1 / КВВ-К1 — трубы, фитинги и арматура системы. По меткам повторный запуск удаляет старое.
"""
import math
import os
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Plumbing
from System.Collections.Generic import List
import kvv

M = kvv.M
MM = kvv.MM
GR_PEREHODY = DB.RoutingPreferenceRuleGroupType.Transitions
# запасные семейства переходов (если правило типа трубы не дало переход): оцинкованная сталь на резьбе —
# муфта переходная из ковкого чугуна, затем сварной концентрический переход
PEREHODY = (u'ADSK_ЧугунРезьба_МуфтаПереходная_ГОСТ8957-75', u'ADSK_СтальСварка_Переход_ГОСТ17378-2001')
# переходы из модулей ADSK (кнопка 02 копирует их в проект): у переходов «по умолчанию» нет нужных размеров — семейство
# ADSK рисует вместо детали шар-предупреждение (Warning = Да, «Не найдено: …»)
PEREHOD_PP_SML = u'ADSK_ЧугунБезраструбный_Переходная муфта HL'            # HL 9/1 100-110: ПП Ø110 — SML DN100
KOMBI_NR = u'ADSK_Полипропилен_Муфта комбинированная НР'                  # ППР — арматура с ВР (кран, фильтр…)
KOMBI_VR = u'ADSK_Полипропилен_Муфта комбинированная ВР'                  # ППР — счётчик, прибор
KOMBI_KLYUCH_NR = u'ADSK_Полипропилен_Муфта комбинированная под ключ НР'  # ПЭ 63 — сталь DN50 (ввод)


def multiport(sym):
    """Семейство с видом детали «Мультипорт» — правилами маршрутизации не ставится."""
    try:
        p_ = sym.Family.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE)
        return p_ is not None and p_.AsInteger() == int(DB.PartType.MultiPort)
    except Exception:
        return False


def preduprezhdenie(f):
    """Шар-предупреждение семейства ADSK: размер не найден в таблице (параметр «Warning» = Да)."""
    if f is None:
        return False
    p = f.LookupParameter(u'Warning')
    return p is not None and p.StorageType == DB.StorageType.Integer and p.AsInteger() == 1


DYUYMY = {15: u'1/2"', 20: u'3/4"', 25: u'1"', 32: u'1 1/4"', 40: u'1 1/2"', 50: u'2"'}


def simvoly_semeystva(doc, imya, dn=None):
    """Типы семейства; при dn — только те, в имени которых больше всего размеров соединения («25 х 1/2"»,
    «HL 9/1 100-110»): у муфт ППР тип задаёт размер, перебирать все долго."""
    vse = [s_ for s_ in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(
        DB.BuiltInCategory.OST_PipeFitting) if s_.FamilyName == imya]
    if not dn or len(vse) < 2:
        return vse
    metki = set(u'%d' % int(round(d)) for d in dn) | set(DYUYMY[int(round(d))] for d in dn if int(round(d)) in DYUYMY)

    def ochki(s_):
        nm = DB.Element.Name.GetValue(s_).replace(u'x', u'х')
        return sum(1 for m in metki if m in nm)
    best = max(ochki(s_) for s_ in vse)
    return [s_ for s_ in vse if ochki(s_) == best] if best > 0 else vse


def komment(e, txt):
    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p and not p.IsReadOnly:
        p.Set(txt)


def po_metke(doc, pref):
    out = []
    for e in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        except Exception:
            continue
        if p is not None and p.HasValue:
            s = p.AsString()
            if s and s.startswith(pref):
                out.append(e)
    return out


def udalit(doc, pref, log):
    ids = [e.Id for e in po_metke(doc, pref)]
    if ids:
        doc.Delete(List[DB.ElementId](ids))
    log(u'удалено с меткой', pref, len(ids))
    udalit_siroty(doc, log)


def udalit_siroty(doc, log):
    """Фасонные части и арматура без метки КВВ, у которых все соединители свободны, — «висят в воздухе»: их
    вставлял сам Revit (переходные муфты у приборов и арматуры другого диаметра), трубы при пересборке удаляются по
    метке, а эти детали оставались на старых местах (к 22.10.2026 их накопилось 1800+)."""
    ids = []
    for bic in (DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory):
        for e in DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            m_ = p.AsString() if p is not None and p.HasValue else None
            if m_ and m_.startswith(u'КВВ'):
                continue
            if getattr(e, 'SuperComponent', None) is not None or e.Symbol.FamilyName.startswith(u'Влж'):
                continue                                  # вложенная часть другого семейства
            cs = [c for c in soediniteli(e) if c.Domain == DB.Domain.DomainPiping]
            # все соединители свободны — или их нет совсем (переходные муфты ППР, которые Revit сам вставлял при
            # соединении ППР Ø20/25 с патрубком DN15: размера нет в таблице — шар-предупреждение без соединителей)
            if (cs and all(not c.IsConnected for c in cs)) or                     (not cs and bic == DB.BuiltInCategory.OST_PipeFitting):
                ids.append(e.Id)
    n = 0
    if ids:
        try:
            doc.Delete(List[DB.ElementId](ids))
            n = len(ids)
        except Exception:
            for i in ids:                                 # по одному: что не удаляется — остаётся
                try:
                    doc.Delete(i)
                    n += 1
                except Exception:
                    pass
    log(u'удалено висящих фасонных частей и арматуры без метки', n, u'из', len(ids))


def pometit_avto(doc, log):
    """Фасонные части и арматура без метки КВВ, соединённые с помеченными элементами сети, — их вставил сам Revit
    (переходные муфты при тройнике на магистрали другого диаметра): метка соседа. Без метки схема другой системы
    (07, tolko_sistema) их не скрывает. По цепочке — пока что-то помечается. В транзакции."""
    def m_(e):
        p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        return p.AsString() if p is not None and p.HasValue else None
    bez = []
    for bic in (DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory):
        for e in DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
            mt = m_(e)
            if (mt and mt.startswith(u'КВВ')) or getattr(e, 'SuperComponent', None) is not None:
                continue
            bez.append(e)
    po_sem = {}
    while True:
        ost = []
        for e in bez:
            sosed = None
            for c in soediniteli(e):
                if c.Domain != DB.Domain.DomainPiping or not c.IsConnected:
                    continue
                for r in c.AllRefs:
                    o = r.Owner
                    if o is None or o.Id == e.Id or isinstance(o, Plumbing.PipingSystem):
                        continue
                    mt = m_(o)
                    if mt and (mt.startswith(u'КВВ-В1') or mt.startswith(u'КВВ-К1')):
                        sosed = mt
                        break
                if sosed:
                    break
            if sosed:
                komment(e, sosed)
                k = e.Symbol.FamilyName
                po_sem[k] = po_sem.get(k, 0) + 1
            else:
                ost.append(e)
        if len(ost) == len(bez):
            break
        bez = ost
    for k, n in sorted(po_sem.items()):
        log(u'  помечено по соседу (вставил Revit):', k, n)
    log(u'деталей без метки КВВ осталось', len(bez), u'(вложенные части и детали вне сетей не считаются)')


def soediniteli(e):
    if isinstance(e, Plumbing.Pipe):
        return list(e.ConnectorManager.Connectors)
    mm = getattr(e, 'MEPModel', None)
    if mm is None or mm.ConnectorManager is None:
        return []
    return list(mm.ConnectorManager.Connectors)


def blizhayshiy(e, p, filtr=None):
    best, dbest = None, 1e9
    for c in soediniteli(e):
        if filtr and not filtr(c):
            continue
        d = c.Origin.DistanceTo(p)
        if d < dbest:
            best, dbest = c, d
    return best, dbest


def postavit(doc, sym, lv, x, y, z, th):
    """Экземпляр семейства на уровне, на отметке z (м, абс.), повернуть на th градусов вокруг вертикали."""
    if not sym.IsActive:
        sym.Activate()
    p = kvv.xyz(x, y, lv.Elevation / M)
    e = doc.Create.NewFamilyInstance(p, sym, lv, DB.Structure.StructuralType.NonStructural)
    par = e.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
    if par and not par.IsReadOnly:
        par.Set(z * M - lv.Elevation)
    if abs(th) > 1e-6:
        ax = DB.Line.CreateBound(p, p + DB.XYZ.BasisZ)
        DB.ElementTransformUtils.RotateElement(doc, e.Id, ax, math.radians(th))
    return e


class Stroitel(object):
    def __init__(self, doc, g, log):
        self.doc, self.g, self.log = doc, g, log
        self.lv = kvv.urovni(doc)
        self.oshibki = {}
        # id трубопровода -> ((первая труба, точка начала), (последняя труба, точка конца)); соединитель ищется заново
        # при каждом обращении: после отката подтранзакции (неудачная проба муфты) прежний объект недействителен
        self.koncy = {}
        self.arm = {}             # id арматуры -> экземпляр
        self.otrezki = []         # (труба, id трубопровода, № отрезка, начало, конец) — для проверки после фитингов
        self.perehody = {}        # семейство перехода из модулей -> сколько поставлено
        self.pr = dict((int(e.LookupParameter(u'Комментарии').AsString()[5:]), e)
                       for e in po_metke(doc, u'КВВ-П'))
        self.ob = dict((int(e.LookupParameter(u'Комментарии').AsString()[5:]), e)
                       for e in po_metke(doc, u'КВВ-О'))

    def oshibka(self, chto, ex):
        self.oshibki.setdefault(chto, [0, unicode(ex)])
        self.oshibki[chto][0] += 1

    def otchet(self):
        for k, n in sorted(self.perehody.items()):
            self.log(u'  переходов %s: %d' % (k, n))
        for k, (n, ex) in sorted(self.oshibki.items()):
            self.log(u'  не удалось: %s — %d шт. (%s)' % (k, n, ex))

    # ---------- приборы, оборудование, муфты ----------
    def pribory(self):
        n = 0
        for p in self.g['pribory']:
            sym = kvv.simvol(self.doc, p['fam'], p['tip'])
            if sym is None:
                self.oshibka(u'нет семейства ' + p['fam'], u'')
                continue
            lv = self.lv[p['ur']]
            e = postavit(self.doc, sym, lv, p['x'], p['y'], lv.Elevation / M, p['th'])
            if p.get('mir'):
                # холодная вода слева: отражение относительно оси симметрии прибора
                t = math.radians(p['th'])
                c, s_ = math.cos(t), math.sin(t)
                if p['mir']['os'] == u'x':
                    lo, nv = (p['mir']['c'], 0.0), (1.0, 0.0)
                else:
                    lo, nv = (0.0, p['mir']['c']), (0.0, 1.0)
                ox_ = p['x'] + lo[0] * c - lo[1] * s_
                oy_ = p['y'] + lo[0] * s_ + lo[1] * c
                nrm = DB.XYZ(nv[0] * c - nv[1] * s_, nv[0] * s_ + nv[1] * c, 0)
                pl = DB.Plane.CreateByNormalAndOrigin(nrm, kvv.xyz(ox_, oy_, lv.Elevation / M))
                DB.ElementTransformUtils.MirrorElements(self.doc, List[DB.ElementId]([e.Id]), pl, False)
            komment(e, u'КВВ-П%d' % p['id'])
            self.pr[p['id']] = e
            n += 1
        self.log(u'приборов', n)
        for i, o in enumerate(self.g['oborud']):
            sym = kvv.simvol(self.doc, o['fam'], o['tip'])
            lv = self.lv[o['ur']]
            e = postavit(self.doc, sym, lv, o['x'], o['y'], lv.Elevation / M, o['th'])
            komment(e, u'КВВ-О%d' % i)
            self.ob[i] = e
            self.log(u'оборудование', o['tip'])
        self.mufty()

    def mufty(self):
        """Противопожарные муфты на стояках К1 — под каждым перекрытием (соосно стояку, вплотную к низу плиты)."""
        sym = kvv.simvol(self.doc, u'ADSK_Противопожарная муфта')
        out = []
        for m in self.g['mufty']:
            e = postavit(self.doc, sym, self.lv[m['ur']], m['x'], m['y'], m['z'], 0)
            komment(e, u'КВВ-М')
            out.append(e)
        self.log(u'противопожарных муфт', len(out))
        return out

    # ---------- трубопроводы ----------
    def sistema(self, sys_):
        st = kvv.po_imeni(self.doc, Plumbing.PipingSystemType, self.g['sistemy'][sys_])
        return st

    def k_oborudovaniyu(self, sys_):
        """Концы трубопроводов, присоединяемые к оборудованию: (id, конец) -> фактический соединитель.

        Положение патрубков зависит от типоразмера установки, поэтому берётся из модели, а не из генератора."""
        out = {}
        ids_sys = set(r['id'] for r in self.g['seti'] if r['sys'] == sys_)
        seti = dict((r['id'], r) for r in self.g['seti'])
        for s in self.g['svyazi']:
            b = s['b']
            if s['a'][0] not in ids_sys or not isinstance(b, dict) or 'obor' not in b:
                continue
            e = self.ob.get(b['obor'])
            if e is None:
                continue
            rid, end = s['a']
            p = seti[rid]['pts'][0 if end == 0 else -1]
            c, d = blizhayshiy(e, kvv.xyz(*p))
            if c is not None:
                out[(rid, end)] = c.Origin
                self.log(u'патрубок оборудования для трубопровода %d: смещение от плана %.0f мм' % (rid, d / MM))
        return out

    @staticmethod
    def privyazat(pts, cel):
        """Сдвинуть начало ломаной в точку cel, сохраняя направления отрезков (сдвиг гасится по ходу трассы)."""
        sdv = cel - pts[0]
        pts[0] = cel
        i = 1
        while i < len(pts) and sdv.GetLength() > 1e-9:
            # направление отрезка (i-1, i) до сдвига
            d = (pts[i] - (pts[i - 1] - sdv)).Normalize()
            perp = sdv - d.Multiply(sdv.DotProduct(d))
            if i == len(pts) - 1:
                break                       # последняя точка остаётся: сдвиг вдоль отрезка гасится его длиной
            pts[i] = pts[i] + perp
            sdv = perp
            i += 1
        return pts

    def truby(self, sys_):
        doc, g = self.doc, self.g
        st = self.sistema(sys_)
        tipy = dict((k, kvv.po_imeni(doc, Plumbing.PipeType, v)) for k, v in g['tipy_trub'].items())
        metka = u'КВВ-' + (u'В1' if sys_ == u'V1' else u'К1')
        k_obor = self.k_oborudovaniyu(sys_)
        n = 0
        for r in g['seti']:
            if r['sys'] != sys_:
                continue
            pts = [kvv.xyz(*p) for p in r['pts']]
            if (r['id'], 0) in k_obor:
                pts = self.privyazat(pts, k_obor[(r['id'], 0)])
            if (r['id'], 1) in k_obor:
                pts = self.privyazat(pts[::-1], k_obor[(r['id'], 1)])[::-1]
            lv = self.lv[r['ur']]
            truby = []
            for a, b in zip(pts[:-1], pts[1:]):
                if a.DistanceTo(b) < 2 * MM:
                    continue
                try:
                    t = Plumbing.Pipe.Create(doc, st.Id, tipy[r['pt']].Id, lv.Id, a, b)
                    t.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(r['d'] * MM)
                    komment(t, metka)
                    truby.append(t)
                    self.otrezki.append((t, r['id'], len(truby) - 1, a, b))
                    n += 1
                except Exception as ex:
                    self.oshibka(u'труба', ex)
            for t1, t2 in zip(truby[:-1], truby[1:]):
                p = t1.Location.Curve.GetEndPoint(1)
                c1, _ = blizhayshiy(t1, p)
                c2, _ = blizhayshiy(t2, p)
                self.soedinit(c1, c2, metka)
            if truby:
                self.koncy[r['id']] = ((truby[0], pts[0]), (truby[-1], pts[-1]))
        self.log(u'труб', sys_, n)
        return metka

    def _popytka(self, o1, o2, p, metka, sym=None):
        """Одна попытка соединить o1 и o2 в точке p — в подтранзакции: неудача откатывается целиком (иначе Revit
        оставлял трубы удлинёнными на длину несостоявшегося перехода — у счётчика они заходили друг в друга).
        sym — семейство перехода, временно первое в правилах переходов типа трубы."""
        doc = self.doc
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            tipy = []
            if sym is not None:
                if not sym.IsActive:
                    sym.Activate()
                for o in (o1, o2):
                    if isinstance(o, Plumbing.Pipe) and o.PipeType.Id not in [t.Id for t in tipy]:
                        tipy.append(o.PipeType)
            c1, _ = blizhayshiy(o1, p)
            c2, _ = blizhayshiy(o2, p)
            dot = c1.CoordinateSystem.BasisZ.DotProduct(c2.CoordinateSystem.BasisZ)
            gr = GR_PEREHODY if dot <= -0.999 else DB.RoutingPreferenceRuleGroupType.Elbows
            if sym is not None:
                for t in tipy:
                    t.RoutingPreferenceManager.AddRule(gr, DB.RoutingPreferenceRule(sym.Id, u'КВВ'), 0)
                doc.Regenerate()
            if dot > -0.999:
                f = doc.Create.NewElbowFitting(c1, c2)
            elif abs(c1.Radius - c2.Radius) > 1e-6:
                f = doc.Create.NewTransitionFitting(c1, c2)
            else:
                f = doc.Create.NewUnionFitting(c1, c2)
            komment(f, metka)
            for t in tipy:
                t.RoutingPreferenceManager.RemoveRule(gr, 0)
            doc.Regenerate()
            if preduprezhdenie(f):
                raise Exception(u'шар-предупреждение: ' + f.Symbol.FamilyName)
            st.Commit()
            return f
        except Exception:
            st.RollBack()
            raise

    def kandidaty(self, o1, o2, dn, soosny=True):
        """Семейства переходов, которые пробуются первыми (по типам соединяемых элементов и диаметрам); если
        соединители не соосны — ничего (такие стыки генератор делает соосными)."""
        if abs(dn[0] - dn[1]) < 0.5:
            return []
        tipy = [DB.Element.Name.GetValue(o.PipeType) if isinstance(o, Plumbing.Pipe) else u'' for o in (o1, o2)]
        if min(dn) > 90:
            return [PEREHOD_PP_SML]
        if any(u'Полиэтилен' in t for t in tipy):
            return [KOMBI_KLYUCH_NR]
        if any(u'Полипропилен_PN' in t for t in tipy):
            drugoy = o2 if isinstance(o1, Plumbing.Pipe) else o1
            if isinstance(drugoy, Plumbing.Pipe):
                return []
            kat = drugoy.Category.Id.IntegerValue
            sch = u'четчик' in getattr(getattr(drugoy, 'Symbol', None), 'FamilyName', u'')
            if not soosny:
                return []
            # резьба у арматуры и подводок к смесителям — внутренняя (ВР): муфта НР; присоединители счётчика —
            # наружная резьба: муфта ВР
            # ППР Ø40 у крана 1" (основание стояка в подвале) — муфта «под ключ» 40 х 1"
            return ([KOMBI_VR, KOMBI_NR] if sch else [KOMBI_NR, KOMBI_VR]) + [KOMBI_KLYUCH_NR]
        return []

    def _mufta_mp(self, o1, o2, P0, sym, metka):
        """Муфта-мультипорт между соосными соединителями c1 и c2 (у трубы ППР/ПЭ — тот, что ближе к её диаметру по
        соединителю муфты): резьбой — к неподвижному элементу (арматура, прибор, стальная труба), конец другой трубы
        укорачивается до раструба муфты. В подтранзакции; шар-предупреждение или несовпадение — откат."""
        doc = self.doc
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            if not sym.IsActive:
                sym.Activate()
                doc.Regenerate()
            # подвижный — конец трубы, диаметр которого есть у муфты «ППР»-стороной (больший из двух у переходов
            # ППР 20/25 -> DN15, ПЭ 63 -> сталь 50)
            c1, _ = blizhayshiy(o1, P0)
            c2, _ = blizhayshiy(o2, P0)
            a, b = (c1, c2) if c1.Radius > c2.Radius else (c2, c1)
            if not isinstance(a.Owner, Plumbing.Pipe):
                raise Exception(u'подвижный соединитель — не труба')
            P = b.Origin
            e = doc.Create.NewFamilyInstance(P, sym, DB.Structure.StructuralType.NonStructural)
            doc.Regenerate()

            def svoi():
                cs = [c for c in soediniteli(e) if c.Domain == DB.Domain.DomainPiping]
                if len(cs) != 2:
                    raise Exception(u'у муфты не два соединителя')
                cs.sort(key=lambda c: abs(c.Radius - b.Radius))
                return cs[0], cs[1]                       # резьба (к b), раструб (к трубе a)
            rez, ras = svoi()
            if abs(rez.Radius - b.Radius) > 0.6 * MM or abs(ras.Radius - a.Radius) > 0.6 * MM:
                raise Exception(u'размеры муфты %.0f/%.0f, нужно %.0f/%.0f' % (
                    rez.Radius * 2 / MM, ras.Radius * 2 / MM, b.Radius * 2 / MM, a.Radius * 2 / MM))
            u = rez.CoordinateSystem.BasisZ
            v = b.CoordinateSystem.BasisZ.Negate()        # резьбовой конец муфты смотрит в соединитель b
            os_ = u.CrossProduct(v)
            if os_.GetLength() < 1e-9:
                if u.DotProduct(v) < 0:
                    perp = DB.XYZ.BasisZ if abs(u.Z) < 0.9 else DB.XYZ.BasisX
                    os_ = u.CrossProduct(perp)
                    DB.ElementTransformUtils.RotateElement(doc, e.Id, DB.Line.CreateBound(P, P + os_.Normalize()),
                                                           math.pi)
            else:
                DB.ElementTransformUtils.RotateElement(doc, e.Id, DB.Line.CreateBound(P, P + os_.Normalize()),
                                                       u.AngleTo(v))
            doc.Regenerate()
            rez, ras = svoi()
            DB.ElementTransformUtils.MoveElement(doc, e.Id, P - rez.Origin)
            doc.Regenerate()
            rez, ras = svoi()
            if ras.CoordinateSystem.BasisZ.DotProduct(a.CoordinateSystem.BasisZ) > -0.999:
                raise Exception(u'раструб муфты не навстречу трубе')
            a.Origin = ras.Origin
            doc.Regenerate()
            a.ConnectTo(ras)
            rez.ConnectTo(b)
            komment(e, metka)
            doc.Regenerate()
            if preduprezhdenie(e):
                raise Exception(u'шар-предупреждение: ' + sym.FamilyName)
            st.Commit()
            return e
        except Exception:
            st.RollBack()
            raise

    def soedinit(self, c1, c2, metka):
        """Соединить два соединителя в одной точке: отвод, переход или муфта в зависимости от направлений.
        Не встал переход — повтор с муфтой переходной ГОСТ 8957 (оцинкованная сталь на резьбе), затем со сварным
        переходом ГОСТ 17378."""
        o1, o2, p = c1.Owner, c2.Owner, c1.Origin
        dn = (c1.Radius * 2 / MM, c2.Radius * 2 / MM)
        osh = None
        soosny = c1.CoordinateSystem.BasisZ.DotProduct(c2.CoordinateSystem.BasisZ) <= -0.999       # до проб
        for imya in self.kandidaty(o1, o2, dn, soosny):
            for sym in simvoly_semeystva(self.doc, imya, dn):
                try:
                    if multiport(sym):
                        self._mufta_mp(o1, o2, p, sym, metka)
                    else:
                        self._popytka(o1, o2, p, metka, sym)
                    self.perehody[imya] = self.perehody.get(imya, 0) + 1
                    return
                except Exception as ex:
                    osh = ex
        try:
            self._popytka(o1, o2, p, metka)
            return
        except Exception as ex:
            osh = ex
        if abs(dn[0] - dn[1]) > 0.5:
            for imya in PEREHODY:
                for sym in DB.FilteredElementCollector(self.doc).OfClass(DB.FamilySymbol).OfCategory(
                        DB.BuiltInCategory.OST_PipeFitting):
                    if sym.FamilyName != imya:
                        continue
                    try:
                        self._popytka(o1, o2, p, metka, sym)
                        self.log(u'  переход DN %.0f / %.0f в точке (%.3f, %.3f, %.3f): %s' % (
                            dn[0], dn[1], p.X / M, p.Y / M, p.Z / M, imya))
                        return
                    except Exception as ex:
                        osh = ex
        self.oshibka(u'отвод/переход', osh)
        self.log(u'  отвод/переход не встал в точке (%.3f, %.3f, %.3f): DN %.0f / %.0f' % (
            p.X / M, p.Y / M, p.Z / M, dn[0], dn[1]))
        try:
            c1, _ = blizhayshiy(o1, p)                   # прежние объекты могли стать недействительными после откатов
            c2, _ = blizhayshiy(o2, p)
            c1.ConnectTo(c2)
        except Exception:
            pass

    def kosoy_troynik(self, c):
        """Тройник не под 90° (косой 45° или с уклоном отвода): API ставит тройник только под прямым углом.

        Как в Revit вручную: тройник под 90° по временной ветке в плоскости настоящей, затем параметр «Угол»,
        затем настоящая ветка подрезается к патрубку тройника и присоединяется."""
        doc = self.doc
        o = c[2].Origin
        tr_b = c[2].Owner
        d1 = c[0].CoordinateSystem.BasisZ.Negate()        # от узла вдоль первой магистрали
        d3 = c[2].CoordinateSystem.BasisZ.Negate()        # от узла вдоль ветки
        w = (d3 - d1.Multiply(d3.DotProduct(d1))).Normalize()
        lv = doc.GetElement(tr_b.LevelId)
        vr = Plumbing.Pipe.Create(doc, tr_b.MEPSystem.GetTypeId() if tr_b.MEPSystem else
                                  tr_b.get_Parameter(DB.BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM).AsElementId(),
                                  tr_b.GetTypeId(), lv.Id, o, o + w.Multiply(0.5 * M))
        vr.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(tr_b.Diameter)
        cv, _ = blizhayshiy(vr, o)
        f = doc.Create.NewTeeFitting(c[0], c[1], cv)
        doc.Delete(vr.Id)
        par = None
        for nm in (u'Угол', u'Angle', u'ADSK_Угол'):
            par = f.LookupParameter(nm)
            if par is not None and not par.IsReadOnly:
                break
            par = None
        if par is None:
            raise Exception(u'у тройника нет параметра угла: ' + f.Symbol.FamilyName)
        ugol = d1.AngleTo(d3)
        cb = None
        for u in (ugol, math.pi - ugol):
            par.Set(u)
            doc.Regenerate()
            svob = [x for x in soediniteli(f) if not x.IsConnected]
            if svob and svob[0].CoordinateSystem.BasisZ.AngleTo(d3) < math.radians(0.5):
                cb = svob[0]
                break
        if cb is None:
            raise Exception(u'патрубок ветки не совпал с трассой (%.1f°)' % math.degrees(ugol))
        # подрезать ветку к патрубку тройника, сохранив дальний конец
        lc = tr_b.Location
        a, b = lc.Curve.GetEndPoint(0), lc.Curve.GetEndPoint(1)
        if a.DistanceTo(o) < b.DistanceTo(o):
            lc.Curve = DB.Line.CreateBound(cb.Origin, b)
        else:
            lc.Curve = DB.Line.CreateBound(a, cb.Origin)
        cp, d = blizhayshiy(tr_b, cb.Origin)
        cb.ConnectTo(cp)
        return f

    def konec(self, ref):
        rid, end = ref
        k = self.koncy.get(rid)
        if not k:
            return None
        t, p = k[end]
        if not t.IsValidObject:
            return None
        c, _ = blizhayshiy(t, p)
        return c

    def armatura(self, sys_, metka):
        n = 0
        ids_sys = set(r['id'] for r in self.g['seti'] if r['sys'] == sys_)
        nuzhnye = set()
        for s in self.g['svyazi']:
            if s['a'][0] in ids_sys and isinstance(s['b'], dict) and 'arm' in s['b']:
                nuzhnye.add(s['b']['arm'])
        # середина сборки (регулятор, счётчик) с трубами не связана — по соседям по сборке
        dobavleno = True
        while dobavleno:
            dobavleno = False
            for a1, a2 in self.g.get('arm_svyazi', []):
                for x, y in ((a1, a2), (a2, a1)):
                    if x in nuzhnye and y not in nuzhnye:
                        nuzhnye.add(y)
                        dobavleno = True
        for a in self.g['armatura']:
            if a['id'] not in nuzhnye:
                continue
            sym = kvv.simvol(self.doc, a['fam'], a['tip'])
            if sym is None:
                # «20 х 1/2"» у водорозетки ADSK — русская «х»; в других семействах — латинская
                norm = lambda t: (t or u'').replace(u'\u0445', u'x').replace(u' ', u'')
                for s_ in DB.FilteredElementCollector(self.doc).OfClass(DB.FamilySymbol):
                    if s_.FamilyName == a['fam'] and norm(DB.Element.Name.GetValue(s_)) == norm(a['tip']):
                        sym = s_
                        if not sym.IsActive:
                            sym.Activate()
                        break
            if sym is None:
                self.oshibka(u'нет семейства ' + a['fam'] + u' ' + a['tip'], u'')
                continue
            try:
                if a.get('wp'):
                    e = self.na_ploskost(sym, a)
                    komment(e, metka)
                    self.arm[a['id']] = e
                    n += 1
                    continue
                e = postavit(self.doc, sym, self.lv[a['ur']], a['x'], a['y'], a['z'], a['th'])
                if a.get('dn'):
                    self.razmer_armatury(e, a['dn'])
                if a.get('vert'):
                    # вертикальный узел учёта: локальная X (вход → выход) — вниз (vert = −1) или вверх. Ось поворота —
                    # через точку вставки на её отметке (Location.Point до регенерации ещё на отметке уровня)
                    P = kvv.xyz(a['x'], a['y'], a['z'])
                    ax = DB.Line.CreateBound(P, P + DB.XYZ.BasisY)
                    # обратный клапан (perev): стрелка семейства — против его оси X, поворот в другую сторону
                    ugol = math.pi / 2 * (a['vert'] if a.get('perev') else -a['vert'])
                    DB.ElementTransformUtils.RotateElement(self.doc, e.Id, ax, ugol)
                    # «lico» — куда смотрит циферблат/отвод прибора (после поворота выше — в +X): поворот вокруг
                    # вертикали через точку вставки (замечание 30.10: приборы узла — к помещению)
                    if a.get('lico'):
                        ug2 = math.atan2(a['lico'][1], a['lico'][0])
                        if abs(ug2) > 1e-6:
                            DB.ElementTransformUtils.RotateElement(
                                self.doc, e.Id, DB.Line.CreateBound(P, P + DB.XYZ.BasisZ), ug2)
                else:
                    # детали-мультипорты (водорозетка) могут не иметь «Смещения»: точка вставки — на отметку
                    self.doc.Regenerate()
                    lp = getattr(e.Location, 'Point', None)
                    if lp is not None and abs(a['z'] * M - lp.Z) > 0.5 * MM:
                        DB.ElementTransformUtils.MoveElement(self.doc, e.Id, DB.XYZ(0, 0, a['z'] * M - lp.Z))
                komment(e, metka)
                self.arm[a['id']] = e
                n += 1
            except Exception as ex:
                self.oshibka(u'арматура', ex)
        self.log(u'арматуры', sys_, n)

    def na_ploskost(self, sym, a):
        """Кран на вертикальном опуске: семейство на рабочей плоскости (rabochaya_ploskost), экземпляр — на
        вертикальной плоскости через точку вставки; ось X семейства (вход -> выход) — вниз, нормаль плоскости — norm
        (ручка смотрит вдоль отвода от стояка)."""
        doc = self.doc
        P = kvv.xyz(a['x'], a['y'], a['z'])
        nx, ny = a.get('norm', [1.0, 0.0])
        n_ = DB.XYZ(nx, ny, 0).Normalize()
        if not getattr(self, '_rp_udaleny', False):
            # опорные плоскости прошлой сборки
            self._rp_udaleny = True
            stare = [r.Id for r in DB.FilteredElementCollector(doc).OfClass(DB.ReferencePlane)
                     if (r.Name or u'').startswith(RP_IMYA)]
            if stare:
                doc.Delete(List[DB.ElementId](stare))
        vid = [v for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D) if not v.IsTemplate][0]
        vdol = n_.CrossProduct(DB.XYZ.BasisZ)                # горизонталь в плоскости
        rp = doc.Create.NewReferencePlane(P, P + DB.XYZ.BasisZ, vdol, vid)
        rp.Name = u'%s %d' % (RP_IMYA, a['id'])
        if not sym.IsActive:
            sym.Activate()
        # ось X семейства (вход -> выход): вертикально (опуск) или горизонтально по th (кран пары стояков ручкой вбок)
        if a.get('vert'):
            os_ = DB.XYZ(0, 0, a['vert'])
        else:
            os_ = DB.XYZ(math.cos(math.radians(a['th'])), math.sin(math.radians(a['th'])), 0)
        e = doc.Create.NewFamilyInstance(rp.GetReference(), P, os_, sym)
        doc.Regenerate()
        # плоскость больше не нужна: если кран без неё остаётся на месте — удалить (на видах её не будет)
        st_ = DB.SubTransaction(doc)
        st_.Start()
        doc.Delete(rp.Id)
        doc.Regenerate()
        if e.IsValidObject:
            st_.Commit()
            self.rp_udaleno = getattr(self, 'rp_udaleno', 0) + 1
        else:
            st_.RollBack()
        if not getattr(self, '_wp_v_zhurnale', False):
            self._wp_v_zhurnale = True
            cs = [c for c in soediniteli(e) if c.Domain == DB.Domain.DomainPiping]
            self.log(u'  кран на плоскости:', sym.FamilyName, u'| плоскость удалена:', getattr(self, 'rp_udaleno', 0),
                     u'| соединители:',
                     u'; '.join(u'(%.3f, %.3f, %.3f)' % (c.Origin.X / M, c.Origin.Y / M, c.Origin.Z / M) for c in cs),
                     u'| вставка (%.3f, %.3f, %.3f)' % (a['x'], a['y'], a['z']))
        return e

    def gibkie_podvodki(self, metka):
        """Гибкая подводка (FlexPipe) от резьбы водорозетки к соединителю холодной воды смесителя: умывальник и
        мойка — от стены к смесителю, ванна — сквозь обшивку короба."""
        doc = self.doc
        spisok = self.g.get('gibkie', [])
        if not spisok:
            return
        tipy = list(DB.FilteredElementCollector(doc).OfClass(Plumbing.FlexPipeType))
        if not tipy:
            self.log(u'НЕТ типа гибкой трубы — подводки не построены')
            return
        ft = tipy[0]
        # тип системы — строго В1 (до 30.10 брался первый тип холодной воды в проекте, а в шаблоне ADSK их несколько:
        # подводки получали «В2» и на 3D-виде были не в цвете В1)
        st = [self.sistema(u'V1')]
        n, ne = 0, 0
        for aid, fid, vid_ in spisok:
            e1, e2 = self.arm.get(aid), self.pr.get(fid)
            if e1 is None or e2 is None:
                continue
            try:
                c2s = [c for c in soediniteli(e2) if c.Domain == DB.Domain.DomainPiping and not c.IsConnected
                       and c.PipeSystemType == Plumbing.PipeSystemType.DomesticColdWater]
                c1s = [c for c in soediniteli(e1) if c.Domain == DB.Domain.DomainPiping and not c.IsConnected]
                if not c2s or not c1s:
                    ne += 1
                    continue
                c2 = c2s[0]
                c1 = min(c1s, key=lambda c: c.Origin.DistanceTo(c2.Origin))
                t1 = c1.CoordinateSystem.BasisZ
                t2 = c2.CoordinateSystem.BasisZ.Negate()
                pts = List[DB.XYZ]([c1.Origin, c2.Origin])
                lv = self.lv[a_ur(self.g, aid)]
                fp = Plumbing.FlexPipe.Create(doc, st[0].Id, ft.Id, lv.Id, t1, t2, pts)
                # диаметр подводки — как у трубы под водорозеткой (Ø20/25), а не по резьбе 1/2": иначе на виде
                # подводка резко тоньше трубы (замечание 30.10). Соединение с резьбой 1/2" Revit держит (опыт 30.10)
                d_tr = [c.Radius * 2 for c in soediniteli(e1) if c.Domain == DB.Domain.DomainPiping and c.Id != c1.Id]
                fp.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(max(d_tr + [c1.Radius * 2]))
                doc.Regenerate()
                for c in fp.ConnectorManager.Connectors:
                    cel = c1 if c.Origin.DistanceTo(c1.Origin) < c.Origin.DistanceTo(c2.Origin) else c2
                    try:
                        c.ConnectTo(cel)
                    except Exception as ex:
                        self.oshibka(u'гибкая подводка: присоединение', ex)
                komment(fp, metka)
                n += 1
            except Exception as ex:
                ne += 1
                self.oshibka(u'гибкая подводка', ex)
        self.log(u'гибких подводок', n, u'| не построено', ne, u'| тип', DB.Element.Name.GetValue(ft))

    def razmer_armatury(self, e, dn):
        """Условный проход арматуры (обратный клапан ADSK DN15-50 по умолчанию DN25): параметр экземпляра или
        типа с «диаметр»/«DN»/«Ду» в имени, длина. Что задано — один раз в журнал."""
        zadano = []
        for el in (e, e.Symbol):
            for pr in el.Parameters:
                nm = pr.Definition.Name
                if pr.IsReadOnly or pr.StorageType != DB.StorageType.Double:
                    continue
                if not any(k in nm for k in (u'иаметр', u'DN', u'Ду', u'Условный')):
                    continue
                # условный проход: у обратного клапана по умолчанию DN25, у фильтра DN15
                # «DN» — у фланцевой арматуры ADL (задвижка KR11, фильтр IS40, клапан RD16 — параметр типа)
                if abs(pr.AsDouble() / MM - dn) < 0.5 or (u'иаметр условный' not in nm and nm != u'DN'):
                    continue
                try:
                    pr.Set(dn * MM)
                    zadano.append(nm)
                except Exception:
                    pass
        if not getattr(self, '_dn_v_zhurnale', False):
            self._dn_v_zhurnale = True
            self.doc.Regenerate()
            rad = [c.Radius * 2 / MM for c in soediniteli(e)]
            self.log(u'  DN арматуры', e.Symbol.FamilyName, u': заданы параметры', u', '.join(zadano) or u'-',
                     u'| соединители, мм:', u', '.join(u'%.0f' % r for r in rad))

    def svyazi(self, sys_, metka):
        doc = self.doc
        ids_sys = set(r['id'] for r in self.g['seti'] if r['sys'] == sys_)
        san = Plumbing.PipeSystemType.Sanitary
        cold = Plumbing.PipeSystemType.DomesticColdWater
        for s in self.g['svyazi']:
            if s['a'][0] not in ids_sys:
                continue
            ca = self.konec(s['a'])
            if ca is None:
                continue
            b = s['b']
            try:
                if isinstance(b, list):
                    cb = self.konec(b)
                    if cb is not None:
                        self.soedinit(ca, cb, metka)
                    continue
                if 'fix' in b:
                    e = self.pr.get(b['fix'])
                    vid = san if b['kind'] == u'san' else cold
                    flt = lambda c, vid=vid: c.Domain == DB.Domain.DomainPiping and c.PipeSystemType == vid
                elif 'arm' in b:
                    e = self.arm.get(b['arm'])
                    flt = None
                else:
                    e = self.ob.get(b['obor'])
                    flt = None
                if e is None:
                    continue
                cb, d = blizhayshiy(e, ca.Origin, flt)
                if cb is None:
                    continue
                if d > 5 * MM:
                    self.oshibka(u'соединитель прибора/арматуры далеко от трубы', u'%.0f мм' % (d / MM))
                if abs(ca.Radius - cb.Radius) > 0.3 * MM:
                    # ППР Ø20/25 и арматура или прибор DN15: прямое соединение разных диаметров Revit не держит
                    # (и сам вставлял переходную муфту ППР без размера 20/15 — шар-предупреждение)
                    self.soedinit(ca, cb, metka)
                else:
                    ca.ConnectTo(cb)
            except Exception as ex:
                self.oshibka(u'присоединение к прибору/арматуре', ex)
        # арматура, свинченная с арматурой (узел учёта одной сборкой): соединители встык
        n_sb, raznye = 0, []
        for a1, a2 in self.g.get('arm_svyazi', []):
            e1, e2 = self.arm.get(a1), self.arm.get(a2)
            if e1 is None or e2 is None:
                continue
            try:
                para = None
                for c1 in soediniteli(e1):
                    if c1.Domain != DB.Domain.DomainPiping or c1.IsConnected:
                        continue
                    c2, d = blizhayshiy(e2, c1.Origin)
                    if c2 is not None and (para is None or d < para[2]):
                        para = (c1, c2, d)
                if para is None or para[2] > 5 * MM:
                    self.oshibka(u'арматура сборки не встык', u'%s — %s' % (e1.Symbol.FamilyName, e2.Symbol.FamilyName))
                    continue
                c1, c2, _ = para
                if abs(c1.Radius - c2.Radius) > 0.3 * MM:
                    # разные «диаметры» соединителей у семейств 1/2" — Revit соединение не держит: встык без связи
                    raznye.append(u'%s %.1f / %s %.1f' % (e1.Symbol.FamilyName, c1.Radius * 2 / MM,
                                                          e2.Symbol.FamilyName, c2.Radius * 2 / MM))
                    continue
                c1.ConnectTo(c2)
                n_sb += 1
            except Exception as ex:
                self.oshibka(u'соединение арматуры сборки', ex)
        if self.g.get('arm_svyazi'):
            self.log(u'арматура одной сборкой: соединено', n_sb, u'| встык без связи (разные соединители)',
                     len(raznye))
            for r in sorted(set(raznye)):
                self.log(u'   ', r)
        # арматура встык с прибором: кран ВР-НР у бачка унитаза, водорозетка у смесителя ванны
        n_pr, ne_pr = 0, []
        for aid, fid, vid_ in self.g.get('arm_pribor', []):
            e1, e2 = self.arm.get(aid), self.pr.get(fid)
            if e1 is None or e2 is None:
                continue
            try:
                cs2 = [c for c in soediniteli(e2) if c.Domain == DB.Domain.DomainPiping and not c.IsConnected
                       and c.PipeSystemType == cold]
                para = None
                for c2 in cs2:
                    c1, d = blizhayshiy(e1, c2.Origin)
                    if c1 is not None and not c1.IsConnected and (para is None or d < para[2]):
                        para = (c1, c2, d)
                if para is None or para[2] > 5 * MM or abs(para[0].Radius - para[1].Radius) > 0.3 * MM:
                    ne_pr.append(u'%s — %s %s' % (e1.Symbol.FamilyName, e2.Symbol.FamilyName,
                                                  u'%.0f мм' % (para[2] / MM) if para else u'нет соединителя'))
                    continue
                para[0].ConnectTo(para[1])
                n_pr += 1
            except Exception as ex:
                self.oshibka(u'арматура встык с прибором', ex)
        self.gibkie_podvodki(metka)
        if self.g.get('arm_pribor'):
            self.log(u'арматура встык с прибором: соединено', n_pr, u'| не соединено', len(ne_pr))
            for r in sorted(set(ne_pr))[:10]:
                self.log(u'   ', r)
        # тройники и крестовины
        for t in self.g['troyniki']:
            if t['m1'][0] not in ids_sys:
                continue
            c = [self.konec(t['m1']), self.konec(t['m2']), self.konec(t['b'])]
            if None in c:
                continue
            try:
                f = doc.Create.NewTeeFitting(c[0], c[1], c[2])
                komment(f, metka)
            except Exception as ex:
                try:
                    f = self.kosoy_troynik(c)
                    komment(f, metka)
                except Exception as ex2:
                    self.oshibka(u'тройник', ex2)
                    # точка — из geometriya_v3.json: после неудачного косого тройника труба может быть уже удалена
                    rb = self.g['seti'][t['b'][0]]['pts']
                    o = rb[0] if t['b'][1] == 0 else rb[-1]
                    self.log(u'  тройник не встал в точке (%.3f, %.3f, %.3f): %s' % (o[0], o[1], o[2], ex2))
        for t in self.g['kresty']:
            if t['m1'][0] not in ids_sys:
                continue
            c = [self.konec(t['m1']), self.konec(t['m2']), self.konec(t['b1']), self.konec(t['b2'])]
            if None in c:
                continue
            try:
                f = doc.Create.NewCrossFitting(c[0], c[1], c[2], c[3])
                komment(f, metka)
            except Exception as ex:
                self.oshibka(u'крестовина', ex)
                try:
                    f = doc.Create.NewTeeFitting(c[0], c[1], c[2])
                    komment(f, metka)
                except Exception:
                    pass
        n2 = 0
        for t in self.g.get('kresty2', []):
            if t['m_niz'][0] not in ids_sys:
                continue
            try:
                if self.krestovina2(t, metka) is not None:
                    n2 += 1
            except Exception as ex:
                self.oshibka(u'крестовина двухплоскостная', ex)
        if self.g.get('kresty2'):
            self.log(u'крестовин двухплоскостных', n2)

    def krestovina2(self, t, metka):
        """Крестовина двухплоскостная 110×50 87° (ADSK_ППР_…, левая или правая): ось — по стояку, патрубок Ø110 —
        к унитазу, Ø50 — к отводу от остальных приборов. Концы четырёх труб переносятся в патрубки и соединяются."""
        doc = self.doc
        cc = dict((k, self.konec(t[k])) for k in ('m_niz', 'm_verh', 'b110', 'b50'))
        if None in cc.values():
            self.oshibka(u'крестовина: нет конца трубы', u'')
            return None
        d110 = DB.XYZ(t['d110'][0], t['d110'][1], 0)
        d50 = DB.XYZ(t['d50'][0], t['d50'][1], 0)
        # левая: патрубок Ø50 по Z×(−d110) при оси стояка вверх
        lev = d50.DotProduct(DB.XYZ(d110.Y, -d110.X, 0)) > 0.5
        sym = kvv.simvol(doc, KREST2, KREST2_LEV if lev else KREST2_PRAV)
        if sym is None:
            self.oshibka(u'нет семейства крестовины', KREST2)
            return None
        P = kvv.xyz(t['x'], t['y'], t['z'])
        e = postavit(doc, sym, self.lv[t['ur']], t['x'], t['y'], t['z'], 0)
        DB.ElementTransformUtils.RotateElement(doc, e.Id, DB.Line.CreateBound(P, P + DB.XYZ.BasisY), -math.pi / 2)
        doc.Regenerate()

        def patrubki():
            out = {}
            for c in soediniteli(e):
                z = c.CoordinateSystem.BasisZ
                if z.Z > 0.7:
                    out['m_verh'] = c
                elif z.Z < -0.7:
                    out['m_niz'] = c
                elif abs(c.Radius * 2 / MM - 110) < 1:
                    out['b110'] = c
                else:
                    out['b50'] = c
            return out
        pa = patrubki()
        z0 = pa['b110'].CoordinateSystem.BasisZ
        cur = DB.XYZ(z0.X, z0.Y, 0).Normalize()
        ang = math.atan2(cur.CrossProduct(d110).Z, cur.DotProduct(d110))
        if abs(ang) > 1e-6:
            DB.ElementTransformUtils.RotateElement(doc, e.Id, DB.Line.CreateBound(P, P + DB.XYZ.BasisZ), ang)
            doc.Regenerate()
            pa = patrubki()
        z5 = pa['b50'].CoordinateSystem.BasisZ
        if DB.XYZ(z5.X, z5.Y, 0).Normalize().DotProduct(d50) < 0.9:
            self.oshibka(u'крестовина: патрубок Ø50 не к отводу', u'(%.3f, %.3f, %.3f)' % (t['x'], t['y'], t['z']))
        for k in ('m_niz', 'm_verh', 'b110', 'b50'):
            ct, cf = cc[k], pa[k]
            try:
                ct.Origin = cf.Origin
                ct.ConnectTo(cf)
            except Exception as ex:
                self.oshibka(u'крестовина: присоединение ' + k, ex)
        komment(e, metka)
        return e

    def korotkie(self):
        """Отрезки, которые фитинги «съели» (Revit откажет при фиксации: «Линия слишком короткая»)."""
        plohie = []
        for t, rid, i, a, b in self.otrezki:
            if not t.IsValidObject:
                plohie.append((rid, i, u'удалена', a, b))
                continue
            c = t.Location.Curve
            p0, p1 = c.GetEndPoint(0), c.GetEndPoint(1)
            L = p0.DistanceTo(p1)
            napr = (p1 - p0).DotProduct(b - a)
            if L < 10 * MM or napr <= 0:
                plohie.append((rid, i, u'%.1f мм' % (L / MM), a, b))
        moi = set(t.Id.IntegerValue for t, rid, i, a, b in self.otrezki if t.IsValidObject) | self.do_postroeniya
        for t in DB.FilteredElementCollector(self.doc).OfClass(Plumbing.Pipe):
            if t.Id.IntegerValue in moi:
                continue
            c = t.Location.Curve
            p0, p1 = c.GetEndPoint(0), c.GetEndPoint(1)
            sosedi = []
            for cn in t.ConnectorManager.Connectors:
                for r in cn.AllRefs:
                    if r.Owner.Id != t.Id:
                        sosedi.append(r.Owner.Name)
            self.log(u'  ВСТАВКА REVIT: труба %d, длина %.1f мм, DN %.0f, от (%.3f, %.3f, %.3f) до (%.3f, %.3f, %.3f), '
                     u'соседи: %s' % (t.Id.IntegerValue, p0.DistanceTo(p1) / MM, t.Diameter / MM,
                                      p0.X / M, p0.Y / M, p0.Z / M, p1.X / M, p1.Y / M, p1.Z / M, u'; '.join(sosedi)))
            plohie.append((0, 0, u'вставка', p0, p1))
        for rid, i, chto, a, b in plohie:
            self.log(u'  КОРОТКИЙ ОТРЕЗОК: трубопровод %d, отрезок %d, осталось %s, было %.0f мм, '
                     u'от (%.3f, %.3f, %.3f) до (%.3f, %.3f, %.3f)' % (
                         rid, i, chto, a.DistanceTo(b) / MM, a.X / M, a.Y / M, a.Z / M, b.X / M, b.Y / M, b.Z / M))
        return plohie

    def ugly(self):
        """Любые углы фитингов: уклоны канализации дают 91–92°, косые тройники — 45°."""
        ps = Plumbing.PipeSettings.GetPipeSettings(self.doc)
        self.log(u'углы фитингов в проекте:', ps.FittingAngleUsage)
        if ps.FittingAngleUsage != DB.FittingAngleUsage.UseAnyAngle:
            ps.FittingAngleUsage = DB.FittingAngleUsage.UseAnyAngle
            self.log(u'  установлено: любой угол')

    def prostoy_troynik_pervym(self, sys_):
        """Тройник «Составной» (с вложенным отводом) принимает углы 87–91°, а отвод с уклоном 0,03 к стояку даёт
        до 92°; обычный тройник ADSK принимает 87–92° и 45° — ставим его первым в правилах соединений."""
        gr = DB.RoutingPreferenceRuleGroupType.Junctions
        for k in set(r['pt'] for r in self.g['seti'] if r['sys'] == sys_):
            pt = kvv.po_imeni(self.doc, Plumbing.PipeType, self.g['tipy_trub'][k])
            rpm = pt.RoutingPreferenceManager
            n = rpm.GetNumberOfRules(gr)
            for i in range(n):
                sym = self.doc.GetElement(rpm.GetRule(gr, 0).MEPPartId)
                if sym is None or u'Составной' not in sym.FamilyName:
                    break
                r0 = rpm.GetRule(gr, 0)
                rpm.RemoveRule(gr, 0)
                rpm.AddRule(gr, r0)
                self.log(u'правило соединения', sym.FamilyName, u'перенесено в конец для', pt.get_Parameter(
                    DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString())

    def sistema_celikom(self, sys_):
        self.ugly()
        self.prostoy_troynik_pervym(sys_)
        self.do_postroeniya = set(t.Id.IntegerValue for t in DB.FilteredElementCollector(self.doc).OfClass(Plumbing.Pipe))
        metka = self.truby(sys_)
        self.doc.Regenerate()
        self.armatura(sys_, metka)
        self.doc.Regenerate()
        self.svyazi(sys_, metka)
        pometit_avto(self.doc, self.log)
        self.otchet()
        self.doc.Regenerate()
        plohie = self.korotkie()
        if plohie:
            # откат без диалога ошибок: журнал покажет, какие отрезки исправить в генераторе
            raise Exception(u'короткие отрезки: %d — транзакция отменена' % len(plohie))


def diag_troynik(doc, log, imena_tipov, vse=False):
    """Журнал: правила соединений типов труб и параметры семейств тройников (вне транзакции)."""
    gr = DB.RoutingPreferenceRuleGroupType.Junctions
    vidannye = set()
    for imya in imena_tipov:
        pt = kvv.po_imeni(doc, Plumbing.PipeType, imya)
        if pt is None:
            continue
        rpm = pt.RoutingPreferenceManager
        log(u'тип', imya, u'| тип соединения:', rpm.PreferredJunctionType)
        for i in range(rpm.GetNumberOfRules(gr)):
            r = rpm.GetRule(gr, i)
            sym = doc.GetElement(r.MEPPartId)
            log(u'   правило соединения:', sym.FamilyName if sym else u'-', u':', DB.Element.Name.GetValue(sym) if sym else u'')
            if sym is None or sym.Family.Id in vidannye:
                continue
            vidannye.add(sym.Family.Id)
            try:
                fd = doc.EditFamily(sym.Family)
                fm = fd.FamilyManager
                for p in fm.GetParameters():
                    nm = p.Definition.Name
                    if vse or any(k in nm for k in (u'гол', u'Angle', u'angle')) or (p.Formula and u'гол' in p.Formula):
                        val = u''
                        try:
                            if p.StorageType == DB.StorageType.Double:
                                val = u'%.2f°' % (fm.CurrentType.AsDouble(p) * 180 / math.pi)
                        except Exception:
                            pass
                        log(u'      параметр', nm, u'(экз.)' if p.IsInstance else u'(тип)', val, u'| формула:', p.Formula or u'-')
                if vse:
                    for tp in fm.Types:
                        log(u'      типоразмер:', tp.Name)
                    for c in DB.FilteredElementCollector(fd).OfClass(DB.ConnectorElement):
                        log(u'      соединитель: направление', c.CoordinateSystem.BasisZ, u'начало', c.Origin)
                fd.Close(False)
            except Exception as ex:
                log(u'      не открыть семейство:', ex)


def proba_troynikov(doc, log, imya_tipa, sys_imya, dn):
    """Пробные тройники в откатываемой транзакции: какие углы и порядок правил проходят."""
    pt = kvv.po_imeni(doc, Plumbing.PipeType, imya_tipa)
    st = kvv.po_imeni(doc, Plumbing.PipingSystemType, sys_imya)
    lv = sorted(kvv.urovni(doc).values(), key=lambda l: l.Elevation)[0]
    gr = DB.RoutingPreferenceRuleGroupType.Junctions
    t = DB.Transaction(doc, u'проба тройников')
    t.Start()
    try:
        for perestavit in (False, True):
            rpm = pt.RoutingPreferenceManager
            if perestavit:
                if rpm.GetNumberOfRules(gr) < 2:
                    break
                r0 = rpm.GetRule(gr, 0)
                rpm.RemoveRule(gr, 0)
                rpm.AddRule(gr, r0)
            for k, ugol in enumerate((90.0, 45.0, 135.0, 91.0, 88.0)):
                o = DB.XYZ((200 + 5 * k + (50 if perestavit else 0)) * M, 200 * M, 0)
                a1 = o - DB.XYZ.BasisX.Multiply(1.0 * M)
                a2 = o + DB.XYZ.BasisX.Multiply(1.0 * M)
                u = math.radians(ugol)
                b = o + DB.XYZ(math.cos(u), math.sin(u), 0).Multiply(1.0 * M)
                tr = []
                for p, q in ((a1, o), (o, a2), (o, b)):
                    x = Plumbing.Pipe.Create(doc, st.Id, pt.Id, lv.Id, p, q)
                    x.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(dn * MM)
                    tr.append(x)
                c = [blizhayshiy(x, o)[0] for x in tr]
                try:
                    f = doc.Create.NewTeeFitting(c[0], c[1], c[2])
                    log(u'проба', imya_tipa, u'DN', dn, u'угол', ugol, u'правила переставлены' if perestavit else u'',
                        u'-> OK', f.Symbol.FamilyName)
                except Exception as ex:
                    log(u'проба', imya_tipa, u'DN', dn, u'угол', ugol, u'правила переставлены' if perestavit else u'',
                        u'-> НЕТ:', ex)
    finally:
        t.RollBack()


SML_KOSOY = u'КВВ_Чугун SML_Тройник косой'


class _Perezagruzka(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        source.Value = DB.FamilySource.Family
        overwriteParameterValues.Value = True
        return True


def klass_soediniteley(doc, imena, log, klass=None):
    """Класс системы у соединителей арматуры — «Глобальный» (в семействах ADL из «Старых систем» — SupplyHydronic,
    подача отопления: задвижки и фильтр водомерного узла выпадали из системы В1). Семейство правится и
    загружается обратно с заменой; уже исправленное пропускается."""
    klass = klass or DB.MEPSystemClassification.Global
    for imya in imena:
        # семейство ищется заново: после LoadFamily прежний объект Family недействителен
        f = [x for x in DB.FilteredElementCollector(doc).OfClass(DB.Family) if x.Name == imya]
        if not f:
            continue
        f = f[0]
        fd = doc.EditFamily(f)
        try:
            ce = [c for c in DB.FilteredElementCollector(fd).OfClass(DB.ConnectorElement)
                  if c.Domain == DB.Domain.DomainPiping]
            nado = [c for c in ce if c.SystemClassification != klass]
            if not nado:
                log(u'классы соединителей уже', klass, u':', imya)
                continue
            t = DB.Transaction(fd, u'КВВ: класс соединителей')
            t.Start()
            for c in nado:
                c.SystemClassification = klass
            t.Commit()
            fd.LoadFamily(doc, _Perezagruzka())
            log(u'классы соединителей -> %s: %s (%d шт.)' % (klass, imya, len(nado)))
        except Exception as ex:
            log(u'класс соединителей не изменён:', imya, ex)
        finally:
            fd.Close(False)


RP_IMYA = u'КВВ-В1 узел'     # опорные плоскости кранов на опуске узла учёта


def a_ur(g, aid):
    """Уровень арматуры по её id в geometriya_v3.json."""
    for a in g['armatura']:
        if a['id'] == aid:
            return a['ur']
    return None


def rabochaya_ploskost(doc, imena, log):
    """Краны VALTEC не поворачиваются на вертикаль (вложенная ручка «на рабочей плоскости»): семейство переводится
    на рабочую плоскость, экземпляр ставится на вертикальную плоскость (Stroitel.na_ploskost). Вне транзакции."""
    for fam in [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name in imena]:
        imya = fam.Name
        fd = doc.EditFamily(fam)
        try:
            of = fd.OwnerFamily
            wp = of.get_Parameter(DB.BuiltInParameter.FAMILY_WORK_PLANE_BASED)
            av = of.get_Parameter(DB.BuiltInParameter.FAMILY_ALWAYS_VERTICAL)
            if wp is None or wp.AsInteger() == 1:
                continue
            t = DB.Transaction(fd, u'На рабочей плоскости')
            t.Start()
            if av is not None and av.AsInteger() == 1:
                av.Set(0)
            wp.Set(1)
            t.Commit()
            fd.LoadFamily(doc, _Perezagruzka())
            log(u'семейство', imya, u': на рабочей плоскости, перезагружено')
        finally:
            fd.Close(False)


def ne_vsegda_vertikalno(doc, imena, log):
    """Краны VALTEC VT.214/VT.215: вложенная «Ручка рычаг L» — «Всегда вертикально» и на рабочей плоскости, из-за
    неё Revit не даёт повернуть кран на опуск узла учёта и спуски («Элемент не может быть повернут в эту позицию»).
    Флаг снимается у вложенных семейств, кран перезагружается в проект. Вне транзакции."""
    FLAGI = (DB.BuiltInParameter.FAMILY_ALWAYS_VERTICAL, DB.BuiltInParameter.FAMILY_WORK_PLANE_BASED)

    def flag(f):
        return any((f.get_Parameter(b_) is not None and f.get_Parameter(b_).AsInteger() == 1) for b_ in FLAGI)

    def snyat(fd_):
        if not flag(fd_.OwnerFamily):
            return False
        t = DB.Transaction(fd_, u'Не всегда вертикально')
        t.Start()
        for b_ in FLAGI:
            pv = fd_.OwnerFamily.get_Parameter(b_)
            if pv is not None and pv.AsInteger() == 1 and not pv.IsReadOnly:
                pv.Set(0)
        t.Commit()
        return True
    for fam in [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name in imena]:
        imya = fam.Name
        fd = doc.EditFamily(fam)
        try:
            izm = []
            for f2 in list(DB.FilteredElementCollector(fd).OfClass(DB.Family)):
                if f2.Id == fd.OwnerFamily.Id or not f2.IsEditable:
                    continue
                if not flag(f2):
                    continue
                imya2 = f2.Name                             # после перезагрузки объект недействителен
                nd = fd.EditFamily(f2)
                try:
                    if snyat(nd):
                        nd.LoadFamily(fd, _Perezagruzka())
                        izm.append(imya2)
                finally:
                    nd.Close(False)
            if snyat(fd):
                izm.append(imya)
            if izm:
                fd.LoadFamily(doc, _Perezagruzka())
                log(u'семейство', imya, u': «Всегда вертикально» снято у', u', '.join(izm), u'— перезагружено')
        finally:
            fd.Close(False)


def bez_preduprezhdeniya(doc, fam, log):
    """Косой тройник SML сделан из тройника ППР: в его таблице нет DN100, и ADSK рисует шар-предупреждение
    (Warning = Да), хотя геометрия строится от диаметров соединителей. Формула «Warning» = нет; семейство
    перезагружается в проект. Вне транзакции."""
    imya = fam.Name                                      # после перезагрузки прежний объект семейства недействителен
    fd = doc.EditFamily(fam)
    try:
        fm = fd.FamilyManager
        p = [q for q in fm.GetParameters() if q.Definition.Name == u'Warning']
        if not p or (p[0].Formula or u'').replace(u' ', u'') == u'1<0':
            return
        t = DB.Transaction(fd, u'Без предупреждения')
        t.Start()
        fm.SetFormula(p[0], u'1 < 0')
        t.Commit()
        fd.LoadFamily(doc, _Perezagruzka())
        log(u'семейство', imya, u': предупреждение выключено, перезагружено')
    finally:
        fd.Close(False)


def sml_kosoy_troynik(doc, log, imya_tipa_sml):
    """Косой тройник SML 45° (СП 30, п. 18.4): в библиотеке ADSK только прямой SML-тройник.

    Семейство делается из тройника ADSK_ППР_Тройник канализационный (есть параметр «Угол»), наименование для
    спецификации задаётся формулой. Ставится первым правилом соединений типа трубы SML. Вне транзакции."""
    est = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == SML_KOSOY]
    if not est:
        baza = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family)
                if f.Name == u'ADSK_ППР_Тройник канализационный']
        if not baza:
            log(u'нет базового семейства тройника — косой SML не создан')
            return
        fd = doc.EditFamily(baza[0])
        try:
            fm = fd.FamilyManager
            t = DB.Transaction(fd, u'SML косой')
            t.Start()
            for p in fm.GetParameters():
                if p.Definition.Name == u'ADSK_Наименование':
                    fm.SetFormula(p, u'"Тройник чугунный безраструбный SML 100х100, 45°"')
                elif p.Definition.Name == u'ADSK_Марка':
                    fm.SetFormula(p, u'"DIN EN 877"')
            t.Commit()
            put = os.path.join(kvv.REVIT, u'semeystva')
            if not os.path.isdir(put):
                os.makedirs(put)
            put = os.path.join(put, SML_KOSOY + u'.rfa')
            so = DB.SaveAsOptions()
            so.OverwriteExistingFile = True
            fd.SaveAs(put, so)
        finally:
            fd.Close(False)
        t = DB.Transaction(doc, u'Загрузка: SML косой')
        t.Start()
        ok = doc.LoadFamily(put)
        t.Commit()
        log(u'создано и загружено семейство', SML_KOSOY, ok)
    fam = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == SML_KOSOY][0]
    bez_preduprezhdeniya(doc, fam, log)
    fam = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == SML_KOSOY][0]
    sym = doc.GetElement(list(fam.GetFamilySymbolIds())[0])
    pt = kvv.po_imeni(doc, Plumbing.PipeType, imya_tipa_sml)
    rpm = pt.RoutingPreferenceManager
    gr = DB.RoutingPreferenceRuleGroupType.Junctions
    pervoe = doc.GetElement(rpm.GetRule(gr, 0).MEPPartId) if rpm.GetNumberOfRules(gr) else None
    if pervoe is None or pervoe.Id != sym.Id:
        t = DB.Transaction(doc, u'Правило: SML косой')
        t.Start()
        if not sym.IsActive:
            sym.Activate()
        rpm.AddRule(gr, DB.RoutingPreferenceRule(sym.Id, u'Косой тройник SML'), 0)
        t.Commit()
        log(u'правило соединения', SML_KOSOY, u'— первым для', imya_tipa_sml)


VSTAVKA = u'ADL_Вставка гибкая фланцевая_FC10_DN32-500_PN10_Ф-Ф'


def gibkaya_vstavka(doc, log, x_shov, metka):
    """Компенсирующее устройство на трубопроводе В1 при пересечении деформационного шва (СП 30.13330):
    гибкая фланцевая вставка ADL на участке магистрали, пересекающем шов. Своей подтранзакцией: при неудаче
    откатывается только вставка."""
    sym = None
    for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        if s.FamilyName == VSTAVKA:
            sym = s
            break
    if sym is None:
        log(u'гибкая вставка: нет семейства', VSTAVKA)
        return
    X = x_shov * M
    truba = None
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        p = t.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p is None or p.AsString() != metka:
            continue
        c = t.Location.Curve
        a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        if abs(a.Y - b.Y) < 1e-6 and abs(a.Z - b.Z) < 1e-6 and min(a.X, b.X) < X - 1.0 * M and max(a.X, b.X) > X + 1.0 * M:
            truba = t
            break
    if truba is None:
        log(u'гибкая вставка: не найден участок магистрали, пересекающий шов x =', x_shov)
        return
    st = DB.SubTransaction(doc)
    st.Start()
    try:
        c = truba.Location.Curve
        a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        if a.X > b.X:
            a, b = b, a
        o = DB.XYZ(X, a.Y, a.Z)
        if not sym.IsActive:
            sym.Activate()
        lv = doc.GetElement(truba.ReferenceLevel.Id)
        e = doc.Create.NewFamilyInstance(DB.XYZ(X, a.Y, lv.Elevation), sym, lv, DB.Structure.StructuralType.NonStructural)
        e.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM).Set(a.Z - lv.Elevation)
        # соединители семейства — вдоль локальной Y: повернуть на 90°, чтобы ось вставки шла вдоль магистрали (X)
        DB.ElementTransformUtils.RotateElement(doc, e.Id, DB.Line.CreateBound(o, o + DB.XYZ.BasisZ), -math.pi / 2)
        d = truba.Diameter
        zadano = []
        for par in e.Parameters:
            nm = par.Definition.Name
            if par.StorageType == DB.StorageType.Double and not par.IsReadOnly and \
                    (nm in (u'DN', u'Ду', u'Условный диаметр', u'Диаметр', u'ADSK_Диаметр условный') or nm.startswith(u'DN')):
                par.Set(d)
                zadano.append(nm)
        doc.Regenerate()
        cn = soediniteli(e)
        if len(cn) != 2:
            raise Exception(u'у вставки %d соединителей' % len(cn))
        cn.sort(key=lambda q: q.Origin.X)
        log(u'гибкая вставка: параметры размера', u', '.join(zadano) or u'-', u'| патрубки DN %.0f, длина %.0f мм' % (
            cn[0].Radius * 2 / MM, cn[0].Origin.DistanceTo(cn[1].Origin) / MM))
        if abs(cn[0].Radius - d / 2) > 1e-4:
            raise Exception(u'размер вставки не совпал с трубой (%.0f / %.0f мм)' % (cn[0].Radius * 2 / MM, d / MM))
        # разрезать магистраль: левая часть до левого патрубка, правая — новая труба от правого патрубка
        nov_id = Plumbing.PlumbingUtils.BreakCurve(doc, truba.Id, o)
        nov = doc.GetElement(nov_id)
        for t in (truba, nov):
            cc = t.Location.Curve
            p0, p1 = cc.GetEndPoint(0), cc.GetEndPoint(1)
            if max(p0.X, p1.X) <= X + 1e-6:          # левая часть
                tgt = cn[0].Origin
            else:
                tgt = cn[1].Origin
            if abs(p0.X - X) < abs(p1.X - X):
                t.Location.Curve = DB.Line.CreateBound(tgt, p1)
            else:
                t.Location.Curve = DB.Line.CreateBound(p0, tgt)
            ct, _ = blizhayshiy(t, tgt)
            ce, _ = blizhayshiy(e, tgt)
            ce.ConnectTo(ct)
            komment(t, metka)
        komment(e, metka)
        st.Commit()
        log(u'гибкая вставка у деформационного шва установлена')
    except Exception as ex:
        st.RollBack()
        log(u'гибкая вставка НЕ установлена:', ex)


ZAGLUSHKA = (u'ADSK_ППР_Заглушка канализационная', u'Заглушка канализационная')
KREST2 = u'ADSK_ППР_Крестовина двухплоскостная канализационная'
KREST2_LEV = u'110x50 — 87° левая'
KREST2_PRAV = u'110x50 — 87° правая'
REVIZIYA = (u'ADSK_ППР_Ревизия канализационная', u'Ревизия')
ET_REVIZIY = (1, 4, 7, 10, 11)      # п. 18.26 СП 30: в нижнем и верхнем этажах и не реже чем через три этажа
Z_REVIZII = 1.0                     # над полом


def _metka_trub(t):
    pr = t.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    return (pr.AsString() or u'') if pr is not None and pr.HasValue else u''


def truba_s_koncom(doc, metka, p, dop=0.005):
    """Труба системы, у которой конец в точке p (XYZ)."""
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        if not _metka_trub(t).startswith(metka):
            continue
        c = t.Location.Curve
        for i in (0, 1):
            if c.GetEndPoint(i).DistanceTo(p) < dop * M:
                return t
    return None


def truba_cherez(doc, metka, p, dop=0.005):
    """Вертикальная труба системы, ось которой проходит через p (XYZ) не ближе 0,15 м к концам."""
    for t in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        if not _metka_trub(t).startswith(metka):
            continue
        c = t.Location.Curve
        a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        if abs(a.X - b.X) > 1e-4 or abs(a.Y - b.Y) > 1e-4:
            continue
        if math.hypot(a.X - p.X, a.Y - p.Y) > dop * M:
            continue
        if min(a.Z, b.Z) + 0.15 * M < p.Z < max(a.Z, b.Z) - 0.15 * M:
            return t
    return None


def zaglushka(doc, t, log):
    """Заглушка на свободный конец трубы: сначала семейство ADSK_ППР_Заглушка, иначе — заглушка из правил типа."""
    sym = kvv.simvol(doc, *ZAGLUSHKA)
    oshibki = []
    do = set()
    for c in t.ConnectorManager.Connectors:
        for r in c.AllRefs:
            do.add(r.Owner.Id.IntegerValue)
    for tid in ([sym.Id] if sym is not None else []) + [DB.ElementId.InvalidElementId]:
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            Plumbing.PlumbingUtils.PlaceCapOnOpenEnds(doc, t.Id, tid)
            doc.Regenerate()
            nov = None
            for c in t.ConnectorManager.Connectors:
                for r in c.AllRefs:
                    o = r.Owner
                    if o.Id != t.Id and o.Id.IntegerValue not in do and isinstance(o, DB.FamilyInstance):
                        nov = o
            if nov is None:
                raise Exception(u'заглушка не появилась')
            st.Commit()
            return nov
        except Exception as ex:
            st.RollBack()
            oshibki.append(unicode(ex))
    raise Exception(u'; '.join(oshibki))


PROBKA = (u'ADSK_ЧугунРезьба_Пробка_ГОСТ8963-59', u'Оцинкованные')


def probki(doc, g, log, metka=u'КВВ-В1'):
    """Пробки ГОСТ 8963 на штуцерах спускных кранов 1/2" (точки — g['probki'] из генератора): спуски у оснований
    стояков, на подводках к поливочным кранам, контрольно-спускной кран водомерного узла. На арматуру
    PlaceCapOnOpenEnds не ставит (30.10: «this operation failed»), поэтому за краном — штуцер, пробка — на нём."""
    sym = kvv.simvol(doc, *PROBKA)
    if sym is None:
        log(u'НЕТ семейства пробки', PROBKA[0], u'— запустить 02')
        return
    if not sym.IsActive:
        sym.Activate()
    n, ne, oshibki = 0, 0, []
    for z in g.get('probki', []):
        t = truba_s_koncom(doc, metka, kvv.xyz(z['x'], z['y'], z['z']))
        if t is None:
            ne += 1
            oshibki.append(u'нет штуцера в (%.2f, %.2f, %.2f)' % (z['x'], z['y'], z['z']))
            continue
        st = DB.SubTransaction(doc)
        st.Start()
        try:
            do = set(r.Owner.Id.IntegerValue for c in t.ConnectorManager.Connectors for r in c.AllRefs)
            Plumbing.PlumbingUtils.PlaceCapOnOpenEnds(doc, t.Id, sym.Id)
            doc.Regenerate()
            nov = [r.Owner for c in t.ConnectorManager.Connectors for r in c.AllRefs
                   if r.Owner.Id != t.Id and r.Owner.Id.IntegerValue not in do and isinstance(r.Owner, DB.FamilyInstance)]
            if not nov:
                raise Exception(u'пробка не появилась')
            for o in nov:
                komment(o, metka)
            st.Commit()
            n += 1
        except Exception as ex:
            st.RollBack()
            ne += 1
            oshibki.append(unicode(ex))
    log(u'пробок на спускных кранах', n, u'| не встало', ne, (u'| ' + oshibki[0]) if oshibki else u'')


def revizia(doc, t, P, sym, log):
    """Ревизия в разрыв трубы в точке P: правило муфт типа трубы временно — ревизия, разрыв, муфта."""
    pt = doc.GetElement(t.GetTypeId())
    rpm = pt.RoutingPreferenceManager
    gr = DB.RoutingPreferenceRuleGroupType.Unions
    if not sym.IsActive:
        sym.Activate()
    rpm.AddRule(gr, DB.RoutingPreferenceRule(sym.Id, u'КВВ: ревизия'), 0)
    try:
        nid = Plumbing.PlumbingUtils.BreakCurve(doc, t.Id, P)
        t2 = doc.GetElement(nid)
        c1, _ = blizhayshiy(t, P)
        c2, _ = blizhayshiy(t2, P)
        f = doc.Create.NewUnionFitting(c1, c2)
    finally:
        rpm.RemoveRule(gr, 0)
    if f is None or u'евизи' not in f.Symbol.FamilyName:
        raise Exception(u'встала не ревизия: %s' % (f.Symbol.FamilyName if f is not None else u'-'))
    return f


def prochistki_revizii(doc, g, log, metka=u'КВВ-К1'):
    """Прочистки (заглушки в начале горизонтальных участков у оснований стояков) и ревизии на стояках К1."""
    n_z, n_r, osh = 0, 0, 0
    for z in g.get('zaglushki', []):
        p = kvv.xyz(z['x'], z['y'], z['z'])
        t = truba_s_koncom(doc, metka, p)
        if t is None:
            log(u'  прочистка: нет трубы с концом в (%.3f, %.3f, %.3f)' % (z['x'], z['y'], z['z']))
            continue
        try:
            f = zaglushka(doc, t, log)
            komment(f, metka + u'-Пр')
            n_z += 1
            if n_z == 1:
                log(u'  заглушка:', f.Symbol.FamilyName, u':', DB.Element.Name.GetValue(f.Symbol))
        except Exception as ex:
            osh += 1
            if osh <= 3:
                log(u'  прочистка не встала (%.3f, %.3f):' % (z['x'], z['y']), ex)
    sym = kvv.simvol(doc, *REVIZIYA)
    if sym is None:
        log(u'нет семейства ревизии', REVIZIYA)
    else:
        pt_ = sym.Family.get_Parameter(DB.BuiltInParameter.FAMILY_CONTENT_PART_TYPE)
        log(u'ревизия: тип детали семейства', pt_.AsValueString() if pt_ else u'?')
        urovni = dict((int(u['imya'].split()[-1]), u['z']) for u in g['urovni'] if u['imya'].startswith(u'Этаж'))
        for s_ in g['stoyaki']:
            if s_['sys'] != u'K1':
                continue
            for et in ET_REVIZIY:
                P = kvv.xyz(s_['x'], s_['y'], urovni[et] + Z_REVIZII)
                t = truba_cherez(doc, metka, P)
                if t is None:
                    osh += 1
                    log(u'  ревизия: нет трубы стояка', s_['imya'], u'этаж', et)
                    continue
                st = DB.SubTransaction(doc)
                st.Start()
                try:
                    f = revizia(doc, t, P, sym, log)
                    komment(f, metka + u'-R')
                    st.Commit()
                    n_r += 1
                except Exception as ex:
                    st.RollBack()
                    osh += 1
                    if osh <= 5:
                        log(u'  ревизия не встала:', s_['imya'], u'этаж', et, ex)
    log(u'прочисток', n_z, u'из', len(g.get('zaglushki', [])), u'| ревизий', n_r, u'| не встало', osh)


Z_FUND = 0.27                       # высота фундамента под насосной установкой (как в образце: 1000х1500х270(h))
ZAPAS_FUND = 0.10                   # фундамент шире установки на 100 мм с каждой стороны


def _opora_ustanovki(doc, e, z_osn, log):
    """Габарит в плане (xmin, ymin, xmax, ymax) того, чем установка стоит на фундаменте: тела, нижняя грань которых
    у основания (до 60 мм выше). Габарит семейства COR включает зоны обслуживания и коллекторы (около 2,8 х 2,8 м),
    фундамент по нему вышел бы на всю насосную. Для сверки в журнал — габарит видимого на плане подвала."""
    def tela(opt):
        out = []

        def obhod(geo):
            for g in geo:
                if isinstance(g, DB.GeometryInstance):
                    obhod(g.GetInstanceGeometry())
                elif isinstance(g, DB.Solid) and g.Volume > 1e-9:
                    out.append(g)
        try:
            obhod(e.get_Geometry(opt))
        except Exception:
            pass
        return out

    def gabarit(solids):
        xs, ys, zs = [], [], []
        for s in solids:
            for ed in s.Edges:
                for p in ed.Tessellate():
                    xs.append(p.X)
                    ys.append(p.Y)
                    zs.append(p.Z)
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys), min(zs), max(zs)

    def mm(g):
        return u'%dх%d мм' % (round((g[2] - g[0]) / MM), round((g[3] - g[1]) / MM)) if g else u'—'
    opt = DB.Options()
    opt.DetailLevel = DB.ViewDetailLevel.Fine
    vse = tela(opt)
    niz = [s for s in vse if (gabarit([s]) or (0, 0, 0, 0, 1e9, 0))[4] < z_osn + 0.06 * M]
    g_niz = gabarit(niz)
    g_plan = None
    for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
        if not v.IsTemplate and v.Name == u'В1_План подвала':
            o = DB.Options()
            o.View = v
            g_plan = gabarit(tela(o))
    g_vse = gabarit(vse)
    log(u'фундамент: тел установки', len(vse), u'| опорных', len(niz), u'— в плане', mm(g_niz),
        u'| видимое на плане подвала', mm(g_plan), u'| все тела', mm(g_vse))
    # фундамент — под всей установкой (рама, насосы, коллекторы): габарит её тел, а не семейства
    for g in (g_vse, g_plan, g_niz):
        if g is not None and (g[2] - g[0]) < 2.0 * M and (g[3] - g[1]) < 2.0 * M:
            return g[:4]
    return None


def fundament_nasosa(doc, log):
    """Насосная установка — на бетонном фундаменте (как в образце: «Фундамент ВК …х…х270(h)»): установка
    поднимается на 270 мм, под ней — блок фундамента (DirectShape, «Обобщённые модели», метка КВВ-Ф) по габариту
    установки с запасом 100 мм, размеры кратны 50 мм. Возвращает (длина, ширина) фундамента, мм."""
    nas = po_metke(doc, u'КВВ-О')
    if not nas:
        log(u'фундамент: нет насосной установки')
        return None
    e = nas[0]
    p = e.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
    if p is not None and not p.IsReadOnly and abs(p.AsDouble() - Z_FUND * M) > 1e-6:
        p.Set(Z_FUND * M)
    doc.Regenerate()
    for f in po_metke(doc, u'КВВ-Ф'):
        doc.Delete(f.Id)
    bb = e.get_BoundingBox(None)
    lv = doc.GetElement(e.LevelId)
    z0 = lv.Elevation
    gab = _opora_ustanovki(doc, e, z0 + Z_FUND * M, log)
    if gab is None:
        gab = (bb.Min.X, bb.Min.Y, bb.Max.X, bb.Max.Y)
        log(u'фундамент: опора установки не найдена — по габариту семейства')

    def kr50(v):
        return math.ceil(v / (0.05 * M) - 1e-9) * 0.05 * M
    dx = kr50(gab[2] - gab[0] + 2 * ZAPAS_FUND * M)
    dy = kr50(gab[3] - gab[1] + 2 * ZAPAS_FUND * M)
    cx, cy = (gab[0] + gab[2]) / 2, (gab[1] + gab[3]) / 2
    pts = [DB.XYZ(cx - dx / 2, cy - dy / 2, z0), DB.XYZ(cx + dx / 2, cy - dy / 2, z0),
           DB.XYZ(cx + dx / 2, cy + dy / 2, z0), DB.XYZ(cx - dx / 2, cy + dy / 2, z0)]
    loop = DB.CurveLoop()
    for a, b in zip(pts, pts[1:] + pts[:1]):
        loop.Append(DB.Line.CreateBound(a, b))
    solid = DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop]([loop]), DB.XYZ.BasisZ,
                                                                 Z_FUND * M)
    ds = DB.DirectShape.CreateElement(doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
    ds.SetShape(List[DB.GeometryObject]([solid]))
    ds.SetName(u'Фундамент ВК')
    komment(ds, u'КВВ-Ф')
    razm = (int(round(dx / MM)), int(round(dy / MM)))
    log(u'насосная установка на фундаменте %dх%dх%d(h) мм' % (razm[0], razm[1], int(round(Z_FUND * 1000))))
    return razm


TVM_RVT = u'C:\\Users\\Даниил\\Downloads\\_проект_Revit_2019.rvt'
TVM_FAM = u'КрыльчатыеСчетчикиХолоднойВоды_Стандарт_Тепловодомер'
TVM_TIP = u'DN25_IP54_Металлический_260_Класс_В'       # ВСХН-25, L = 260 мм, метрологический класс В


def tvm_schetchik(doc, app, log, tip=TVM_TIP):
    """Крыльчатый счётчик «Тепловодомер» (TVM) из проекта, присланного пользователем (Revit 2019): семейство
    сохраняется в revit/semeystva (проект открывается фоном и закрывается без сохранения) и загружается в модель.
    В журнал — типы семейства и соединители типа tip относительно точки вставки (для geometriya_v3.ARM).
    Вне транзакции. Возвращает символ или None."""
    # прежняя самодельная заготовка счётчика — из проекта вон
    stare = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == u'КВВ_Счетчик воды крыльчатый']
    if stare:
        t = DB.Transaction(doc, u'Удаление: заготовка счётчика')
        t.Start()
        doc.Delete(stare[0].Id)
        t.Commit()
        log(u'удалено семейство-заготовка КВВ_Счетчик воды крыльчатый')
    papka = os.path.join(kvv.REVIT, u'semeystva', u'tvm')
    put = os.path.join(papka, TVM_FAM + u'.rfa')
    if not [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == TVM_FAM]:
        if not (os.path.isdir(papka) and [fn for fn in os.listdir(papka) if fn.lower().endswith(u'.rfa')]):
            if not os.path.isfile(TVM_RVT):
                log(u'TVM: нет файла', TVM_RVT)
                return None
            # все семейства счётчиков проекта — в revit/semeystva/tvm (проект открывается один раз)
            if not os.path.isdir(papka):
                os.makedirs(papka)
            d2 = app.OpenDocumentFile(TVM_RVT)
            try:
                for f in DB.FilteredElementCollector(d2).OfClass(DB.Family):
                    nm = f.Name
                    low = nm.lower()
                    if not (u'tvm' in low or u'четчик' in low or u'чётчик' in low or u'водомер' in low):
                        continue
                    tipy = [DB.Element.Name.GetValue(d2.GetElement(i)) for i in f.GetFamilySymbolIds()]
                    kat = f.FamilyCategory.Name if f.FamilyCategory else u'?'
                    log(u'TVM: семейство «%s» (%s), типов %d: %s' % (nm, kat, len(tipy), u'; '.join(sorted(tipy))))
                    if not f.IsEditable:
                        continue
                    fd = d2.EditFamily(f)
                    try:
                        so = DB.SaveAsOptions()
                        so.OverwriteExistingFile = True
                        fn = u''.join(u'_' if ch in u'\\/:*?"<>|' else ch for ch in nm)
                        fd.SaveAs(os.path.join(papka, fn + u'.rfa'), so)
                    finally:
                        fd.Close(False)
            finally:
                d2.Close(False)
        for fn in os.listdir(papka):
            if fn.lower().endswith(u'.rfa'):
                log(u'TVM: сохранено', fn)
        if not os.path.isfile(put):
            log(u'TVM: нет файла семейства', TVM_FAM)
            return None
        t = DB.Transaction(doc, u'Загрузка: счётчик TVM')
        t.Start()
        ok = doc.LoadFamily(put)
        t.Commit()
        log(u'TVM: загружено', ok)
    fam = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == TVM_FAM][0]
    simvoly = [doc.GetElement(i) for i in fam.GetFamilySymbolIds()]
    log(u'TVM: типов', len(simvoly), u'—', u'; '.join(sorted(DB.Element.Name.GetValue(s) for s in simvoly)))
    def norm(s):                                  # в именах TVM буквы В, С, Н местами латинские
        return s.replace(u'H', u'Н').replace(u'B', u'В').replace(u'C', u'С').strip()
    sym = [s for s in simvoly if norm(DB.Element.Name.GetValue(s)) == norm(tip)]
    if not sym:
        log(u'TVM: нет типа', tip)
        return None
    sym = sym[0]
    # соединители типа — пробная вставка с откатом
    lvl = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
    t = DB.Transaction(doc, u'Проба: счётчик TVM')
    t.Start()
    try:
        if not sym.IsActive:
            sym.Activate()
            doc.Regenerate()
        tp = sym.Family.FamilyPlacementType
        if tp == DB.FamilyPlacementType.WorkPlaneBased:
            e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, 0), sym, DB.XYZ.BasisX, lvl,
                                             DB.Structure.StructuralType.NonStructural)
        else:
            e = doc.Create.NewFamilyInstance(DB.XYZ(0, 0, 0), sym, lvl, DB.Structure.StructuralType.NonStructural)
        doc.Regenerate()
        p0 = e.Location.Point
        for c in soediniteli(e):
            o, d = c.Origin - p0, c.CoordinateSystem.BasisZ
            log(u'TVM %s: соединитель DN%.0f o=(%.0f, %.0f, %.0f) мм dir=(%.2f, %.2f, %.2f) | размещение %s' % (
                tip, c.Radius * 2 / MM, o.X / MM, o.Y / MM, o.Z / MM, d.X, d.Y, d.Z, tp))
        bb = e.get_BoundingBox(None)
        log(u'TVM %s: габарит (%.0f…%.0f) x (%.0f…%.0f) x (%.0f…%.0f) мм' % (
            tip, (bb.Min.X - p0.X) / MM, (bb.Max.X - p0.X) / MM, (bb.Min.Y - p0.Y) / MM, (bb.Max.Y - p0.Y) / MM,
            (bb.Min.Z - p0.Z) / MM, (bb.Max.Z - p0.Z) / MM))
        for nm in (u'ADSK_Наименование', u'ADSK_Марка', u'Описание', u'Комментарии к типоразмеру'):
            pr = sym.LookupParameter(nm)
            if pr is not None and pr.HasValue:
                log(u'TVM %s: %s = %s' % (tip, nm, pr.AsString() or pr.AsValueString()))
    finally:
        t.RollBack()
    return sym


def podognat_koncy(doc, log, metki=(u'КВВ-В1', u'КВВ-К1'), dopusk=0.0005):
    """Концы труб — точно в соединители, к которым они присоединены. После смены «Угла» у косого тройника его
    соединители сдвигаются (у тройника 135° — на 40 мм), а труба остаётся «присоединённой» с видимым зазором
    (замечание 30.10, сборный К1 в подвале). Конец переносится в точку соединителя и присоединяется заново.
    В транзакции."""
    n, osh = 0, []
    for p in DB.FilteredElementCollector(doc).OfClass(Plumbing.Pipe):
        pm = p.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        mt = (pm.AsString() or u'') if pm is not None and pm.HasValue else u''
        if not any(mt.startswith(m) for m in metki):
            continue
        for c in list(p.ConnectorManager.Connectors):
            if c.ConnectorType != DB.ConnectorType.End or not c.IsConnected:
                continue
            drug = [r for r in c.AllRefs if r.Owner.Id != p.Id and r.ConnectorType == DB.ConnectorType.End]
            if not drug or c.Origin.DistanceTo(drug[0].Origin) < dopusk * M:
                continue
            ref = drug[0]
            lc = p.Location.Curve
            a, b = lc.GetEndPoint(0), lc.GetEndPoint(1)
            d_mm = c.Origin.DistanceTo(ref.Origin) / M * 1000
            try:
                c.DisconnectFrom(ref)
                if c.Origin.DistanceTo(a) < c.Origin.DistanceTo(b):
                    p.Location.Curve = DB.Line.CreateBound(ref.Origin, b)
                else:
                    p.Location.Curve = DB.Line.CreateBound(a, ref.Origin)
                doc.Regenerate()
                nov = min([x for x in p.ConnectorManager.Connectors if x.ConnectorType == DB.ConnectorType.End],
                          key=lambda x: x.Origin.DistanceTo(ref.Origin))
                nov.ConnectTo(ref)
                n += 1
                log(u'  конец трубы %d подтянут к %d на %.0f мм (%.2f, %.2f, %.2f)' % (
                    p.Id.IntegerValue, ref.Owner.Id.IntegerValue, d_mm, ref.Origin.X / M, ref.Origin.Y / M,
                    ref.Origin.Z / M))
            except Exception as ex:
                osh.append((p.Id.IntegerValue, ex))
    log(u'концов труб подтянуто к соединителям', n, u'| не вышло', len(osh))
    for o in osh[:20]:
        log(u'  ОШИБКА подтяжки:', o[0], o[1])


def fitingi_v_dvuh_sistemah(doc, log, metka_=u'КВВ-В1'):
    """Фитинги, у которых соединители в разных системах (30.10: тройник второго контрольного крана водомерного
    узла — участок задвижка–фильтр–тройник выпал в отдельную систему «В1 …» из 18 соединителей): соединители
    отсоединяются и присоединяются заново, Revit сливает системы. В транзакции."""
    n = 0
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_PipeFitting) \
            .WhereElementIsNotElementType():
        pm = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if pm is None or not (pm.AsString() or u'').startswith(metka_):
            continue
        cs = [c for c in e.MEPModel.ConnectorManager.Connectors if c.Domain == DB.Domain.DomainPiping]
        sist = set()
        for c in cs:
            try:
                sist.add(c.MEPSystem.Id.IntegerValue if c.MEPSystem else -1)
            except Exception:
                sist.add(-1)
        if len(sist) < 2:
            continue
        for c in cs:
            refs = [r for r in c.AllRefs if r.Owner.Id != e.Id]
            for r in refs:
                c.DisconnectFrom(r)
                doc.Regenerate()
                c.ConnectTo(r)
        doc.Regenerate()
        n += 1
        log(u'  фитинг %d в системах %s — соединители переподключены' % (e.Id.IntegerValue, sorted(sist)))
    log(u'фитингов в двух системах переподключено', n)
