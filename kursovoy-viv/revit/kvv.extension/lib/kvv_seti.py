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
        sym = kvv.simvol(self.doc, u'ADSK_Противопожарная муфта')
        for m in self.g['mufty']:
            e = postavit(self.doc, sym, self.lv[m['ur']], m['x'], m['y'], m['z'], 0)
            komment(e, u'КВВ-М')
        self.log(u'противопожарных муфт', len(self.g['mufty']))

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

    def soedinit(self, c1, c2, metka):
        """Соединить два соединителя в одной точке: отвод, переход или муфта в зависимости от направлений."""
        try:
            z1, z2 = c1.CoordinateSystem.BasisZ, c2.CoordinateSystem.BasisZ
            dot = z1.DotProduct(z2)
            if dot > -0.999:
                f = self.doc.Create.NewElbowFitting(c1, c2)
            elif abs(c1.Radius - c2.Radius) > 1e-6:
                f = self.doc.Create.NewTransitionFitting(c1, c2)
            else:
                f = self.doc.Create.NewUnionFitting(c1, c2)
            komment(f, metka)
        except Exception as ex:
            self.oshibka(u'отвод/переход', ex)
            o = c1.Origin
            self.log(u'  отвод/переход не встал в точке (%.3f, %.3f, %.3f): DN %.0f / %.0f' % (
                o.X / M, o.Y / M, o.Z / M, c1.Radius * 2 / MM, c2.Radius * 2 / MM))
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
