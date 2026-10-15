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
        self.koncy = {}           # id трубопровода -> (соединитель начала, соединитель конца)
        self.arm = {}             # id арматуры -> экземпляр
        self.otrezki = []         # (труба, id трубопровода, № отрезка, начало, конец) — для проверки после фитингов
        self.pr = dict((int(e.LookupParameter(u'Комментарии').AsString()[5:]), e)
                       for e in po_metke(doc, u'КВВ-П'))
        self.ob = dict((int(e.LookupParameter(u'Комментарии').AsString()[5:]), e)
                       for e in po_metke(doc, u'КВВ-О'))

    def oshibka(self, chto, ex):
        self.oshibki.setdefault(chto, [0, unicode(ex)])
        self.oshibki[chto][0] += 1

    def otchet(self):
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
                c0, _ = blizhayshiy(truby[0], pts[0])
                c9, _ = blizhayshiy(truby[-1], pts[-1])
                self.koncy[r['id']] = (c0, c9)
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
                for t in tipy:
                    t.RoutingPreferenceManager.AddRule(GR_PEREHODY, DB.RoutingPreferenceRule(sym.Id, u'КВВ'), 0)
                doc.Regenerate()
            c1, _ = blizhayshiy(o1, p)
            c2, _ = blizhayshiy(o2, p)
            dot = c1.CoordinateSystem.BasisZ.DotProduct(c2.CoordinateSystem.BasisZ)
            if dot > -0.999:
                f = doc.Create.NewElbowFitting(c1, c2)
            elif abs(c1.Radius - c2.Radius) > 1e-6:
                f = doc.Create.NewTransitionFitting(c1, c2)
            else:
                f = doc.Create.NewUnionFitting(c1, c2)
            komment(f, metka)
            for t in tipy:
                t.RoutingPreferenceManager.RemoveRule(GR_PEREHODY, 0)
            st.Commit()
            return f
        except Exception:
            st.RollBack()
            raise

    def soedinit(self, c1, c2, metka):
        """Соединить два соединителя в одной точке: отвод, переход или муфта в зависимости от направлений.
        Не встал переход — повтор с муфтой переходной ГОСТ 8957 (оцинкованная сталь на резьбе), затем со сварным
        переходом ГОСТ 17378."""
        o1, o2, p = c1.Owner, c2.Owner, c1.Origin
        dn = (c1.Radius * 2 / MM, c2.Radius * 2 / MM)
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
        return k[end] if k else None

    def armatura(self, sys_, metka):
        n = 0
        ids_sys = set(r['id'] for r in self.g['seti'] if r['sys'] == sys_)
        nuzhnye = set()
        for s in self.g['svyazi']:
            if s['a'][0] in ids_sys and isinstance(s['b'], dict) and 'arm' in s['b']:
                nuzhnye.add(s['b']['arm'])
        for a in self.g['armatura']:
            if a['id'] not in nuzhnye:
                continue
            sym = kvv.simvol(self.doc, a['fam'], a['tip'])
            if sym is None:
                self.oshibka(u'нет семейства ' + a['fam'] + u' ' + a['tip'], u'')
                continue
            try:
                e = postavit(self.doc, sym, self.lv[a['ur']], a['x'], a['y'], a['z'], a['th'])
                komment(e, metka)
                self.arm[a['id']] = e
                n += 1
            except Exception as ex:
                self.oshibka(u'арматура', ex)
        self.log(u'арматуры', sys_, n)

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
                ca.ConnectTo(cb)
            except Exception as ex:
                self.oshibka(u'присоединение к прибору/арматуре', ex)
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
                    o = c[2].Origin
                    self.log(u'  тройник не встал в точке (%.3f, %.3f, %.3f): %s' % (o.X / M, o.Y / M, o.Z / M, ex2))
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
REVIZIYA = (u'ADSK_ППР_Ревизия канализационная', u'Ревизия')
ET_REVIZIY = (1, 4, 7, 10, 11)      # п. 18.28 СП 30: в нижнем и верхнем этажах и не реже чем через три этажа
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
