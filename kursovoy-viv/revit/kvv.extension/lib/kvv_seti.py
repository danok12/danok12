# -*- coding: utf-8 -*-
"""Построение приборов, арматуры и трубопроводов по geometriya_v3.json (IronPython, pyRevit).

Элементы помечаются в «Комментариях»: КВВ-П<id> — прибор, КВВ-О<id> — оборудование, КВВ-М — муфта,
КВВ-В1 / КВВ-К1 — трубы, фитинги и арматура системы. По меткам повторный запуск удаляет старое.
"""
import math
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

    def truby(self, sys_):
        doc, g = self.doc, self.g
        st = self.sistema(sys_)
        tipy = dict((k, kvv.po_imeni(doc, Plumbing.PipeType, v)) for k, v in g['tipy_trub'].items())
        metka = u'КВВ-' + (u'В1' if sys_ == u'V1' else u'К1')
        n = 0
        for r in g['seti']:
            if r['sys'] != sys_:
                continue
            pts = [kvv.xyz(*p) for p in r['pts']]
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
            try:
                c1.ConnectTo(c2)
            except Exception:
                pass

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
                self.oshibka(u'тройник', ex)
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

    def sistema_celikom(self, sys_):
        metka = self.truby(sys_)
        self.doc.Regenerate()
        self.armatura(sys_, metka)
        self.doc.Regenerate()
        self.svyazi(sys_, metka)
        self.otchet()
