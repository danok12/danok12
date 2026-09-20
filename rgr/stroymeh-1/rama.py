# -*- coding: utf-8 -*-
"""Расчётное ядро для статически определимых стержневых систем.

Считает опорные реакции и внутренние усилия N, Q, M в любом сечении.
Всё в точной арифметике (Fraction), поэтому проверки сходятся в ноль
без «почти».

Как описывается система:
  nodes    — {имя: (x, y)}, ось x вправо, ось y вверх;
  members  — [(имя, узел1, узел2)], стержень прямой;
  loads    — сосредоточенные силы, моменты и распределённые нагрузки;
  supports — опорные связи: точка + направление реакции;
  hinges   — шарниры: узел + сторона, для которой пишется ΣM = 0.

Знаки:
  момент — против часовой стрелки положителен;
  N      — растяжение положительно;
  Q      — положительна, если стремится повернуть отсечённую часть
           по часовой стрелке (стандартное правило).
"""
from fractions import Fraction as F


def frac(v):
    return v if isinstance(v, F) else F(str(v))


class Sistema:
    def __init__(self, name):
        self.name = name
        self.nodes = {}
        self.members = []          # (имя, у1, у2)
        self.forces = []           # (точка, (Fx, Fy), подпись)
        self.moments = []          # (точка, Mz, подпись)
        self.dists = []            # (стержень, (qx, qy), t0, t1, подпись)
        self.supports = []         # (узел, (dx, dy), имя реакции)
        self.hinges = []           # (узел, [стержни отсечённой части])

    # ---------------------------------------------------------- описание
    def node(self, name, x, y):
        self.nodes[name] = (frac(x), frac(y))
        return self

    def member(self, name, a, b):
        self.members.append((name, a, b))
        return self

    def force(self, node, fx, fy, label=""):
        self.forces.append((node, (frac(fx), frac(fy)), label))
        return self

    def moment(self, node, mz, label=""):
        self.moments.append((node, frac(mz), label))
        return self

    def dist(self, member, qx, qy, t0=0, t1=1, label="q"):
        self.dists.append((member, (frac(qx), frac(qy)), frac(t0), frac(t1), label))
        return self

    def support(self, node, dx, dy, name):
        """Опорная связь — сила по направлению (dx, dy)."""
        self.supports.append((node, (frac(dx), frac(dy)), name))
        return self

    def support_m(self, node, name):
        """Опорная связь — реактивный момент (заделка). Плечо не нужен:
        момент пары одинаков относительно любой точки."""
        self.supports.append((node, None, name))
        return self

    def hinge(self, node, side_members):
        self.hinges.append((node, list(side_members)))
        return self

    # ------------------------------------------------------- геометрия
    def mem(self, name):
        for m in self.members:
            if m[0] == name:
                return m
        raise KeyError(name)

    def mem_pts(self, name):
        _, a, b = self.mem(name)
        return self.nodes[a], self.nodes[b]

    def point_on(self, member, t):
        p, q = self.mem_pts(member)
        return (p[0] + (q[0] - p[0]) * frac(t),
                p[1] + (q[1] - p[1]) * frac(t))

    def length(self, member):
        p, q = self.mem_pts(member)
        dx, dy = q[0] - p[0], q[1] - p[1]
        L2 = dx * dx + dy * dy
        L = F(int(round(float(L2) ** 0.5)))
        assert L * L == L2, "длина стержня не целая — поправь геометрию"
        return L

    def axis(self, member):
        p, q = self.mem_pts(member)
        L = self.length(member)
        return ((q[0] - p[0]) / L, (q[1] - p[1]) / L)

    # ------------------------------------- распределённая -> сила и точка
    def dist_resultant(self, d, t0=None, t1=None):
        """Равнодействующая распределённой нагрузки и точка её приложения."""
        member, (qx, qy), a, b, _ = d
        a = a if t0 is None else max(a, frac(t0))
        b = b if t1 is None else min(b, frac(t1))
        if b <= a:
            return (F(0), F(0)), self.point_on(member, a)
        L = self.length(member)
        s = (b - a) * L                      # длина загруженного участка
        mid = self.point_on(member, (a + b) / 2)
        return (qx * s, qy * s), mid

    # ------------------------------------------------ сбор всех нагрузок
    def load_items(self):
        """Все внешние нагрузки как (точка, (Fx,Fy), Mz, стержень|None)."""
        items = []
        for node, f, lab in self.forces:
            items.append((self.nodes[node], f, F(0), None, lab))
        for node, mz, lab in self.moments:
            items.append((self.nodes[node], (F(0), F(0)), mz, None, lab))
        for d in self.dists:
            R, P = self.dist_resultant(d)
            items.append((P, R, F(0), d[0], d[4]))
        return items

    @staticmethod
    def mom(point, f, mz, about):
        rx, ry = point[0] - about[0], point[1] - about[1]
        return rx * f[1] - ry * f[0] + mz

    # ------------------------------------------------------- связность
    def side_nodes(self, cut_member, keep):
        """Узлы части,连 связанной с узлом keep, если разрезать cut_member."""
        adj = {n: [] for n in self.nodes}
        for name, a, b in self.members:
            if name == cut_member:
                continue
            adj[a].append(b)
            adj[b].append(a)
        seen, stack = {keep}, [keep]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        return seen

    def side_members(self, cut_member, nodes):
        return [m[0] for m in self.members
                if m[0] != cut_member and m[1] in nodes and m[2] in nodes]

    # --------------------------------------------------- решение реакций
    def solve(self):
        n = len(self.supports)
        rows, rhs = [], []

        def load_sum(items):
            sx = sum(i[1][0] for i in items)
            sy = sum(i[1][1] for i in items)
            return sx, sy

        items = self.load_items()

        # ΣX = 0, ΣY = 0
        for k in (0, 1):
            rows.append([(self.supports[j][1][k] if self.supports[j][1] else F(0))
                         for j in range(n)])
            rhs.append(-sum(i[1][k] for i in items))
        # ΣM относительно начала координат
        O = (F(0), F(0))
        rows.append([(self.mom(self.nodes[self.supports[j][0]],
                               self.supports[j][1], F(0), O)
                      if self.supports[j][1] else F(1)) for j in range(n)])
        rhs.append(-sum(self.mom(i[0], i[1], i[2], O) for i in items))

        # условия в шарнирах: ΣM отсечённой части относительно шарнира
        for hn, side in self.hinges:
            H = self.nodes[hn]
            side_node_set = set()
            for mname in side:
                _, a, b = self.mem(mname)
                side_node_set |= {a, b}
            row = []
            for j in range(n):
                sn, sd, _ = self.supports[j]
                if sn not in side_node_set:
                    row.append(F(0))
                elif sd is None:
                    row.append(F(1))
                else:
                    row.append(self.mom(self.nodes[sn], sd, F(0), H))
            rows.append(row)
            tot = F(0)
            for p, f, mz, mem, _ in items:
                belongs = mem in side if mem else \
                    any(p == self.nodes[x] for x in side_node_set if x != hn)
                if belongs:
                    tot += self.mom(p, f, mz, H)
            rhs.append(-tot)

        sol = gauss(rows, rhs)
        self.R = {self.supports[j][2]: sol[j] for j in range(n)}
        return self.R

    # ------------------------------------------- внутренние усилия N,Q,M
    def internal(self, member, t):
        """N, Q, M в сечении стержня member на параметре t (0..1)."""
        _, a, b = self.mem(member)
        P = self.point_on(member, t)
        e = self.axis(member)
        nrm = (-e[1], e[0])
        far_nodes = self.side_nodes(member, b)
        far_mems = self.side_members(member, far_nodes)

        S = [F(0), F(0)]
        Mz = F(0)
        for p, f, mz, mem, _ in self.load_items():
            if mem is not None:
                if mem not in far_mems:
                    continue
            else:
                if not any(p == self.nodes[x] for x in far_nodes):
                    continue
            S[0] += f[0]; S[1] += f[1]
            Mz += self.mom(p, f, mz, P)
        # часть распределённой нагрузки на самом разрезанном стержне (за сечением)
        for d in self.dists:
            if d[0] != member:
                continue
            R, C = self.dist_resultant(d, t0=t)
            S[0] += R[0]; S[1] += R[1]
            Mz += self.mom(C, R, F(0), P)
        # реакции дальней части
        for node, direction, name in self.supports:
            if node not in far_nodes:
                continue
            Rv = self.R[name]
            if direction is None:                 # реактивный момент
                Mz += Rv
                continue
            f = (direction[0] * Rv, direction[1] * Rv)
            S[0] += f[0]; S[1] += f[1]
            Mz += self.mom(self.nodes[node], f, F(0), P)

        N = S[0] * e[0] + S[1] * e[1]
        Q = -(S[0] * nrm[0] + S[1] * nrm[1])
        return N, Q, Mz


    def internal_near(self, member, t):
        """То же сечение, но по ближней части — независимая проверка.

        По равновесию системы в целом результат обязан совпасть
        с internal(): если не совпал, ошибка в реакциях или в модели.
        """
        _, a, b = self.mem(member)
        P = self.point_on(member, t)
        e = self.axis(member)
        nrm = (-e[1], e[0])
        near_nodes = self.side_nodes(member, a)
        near_mems = self.side_members(member, near_nodes)

        S = [F(0), F(0)]
        Mz = F(0)
        for p, f, mz, mem, _ in self.load_items():
            if mem is not None:
                if mem not in near_mems:
                    continue
            else:
                if not any(p == self.nodes[x] for x in near_nodes):
                    continue
            S[0] += f[0]; S[1] += f[1]
            Mz += self.mom(p, f, mz, P)
        for d in self.dists:
            if d[0] != member:
                continue
            R, C = self.dist_resultant(d, t1=t)
            S[0] += R[0]; S[1] += R[1]
            Mz += self.mom(C, R, F(0), P)
        for node, direction, name in self.supports:
            if node not in near_nodes:
                continue
            Rv = self.R[name]
            if direction is None:
                Mz += Rv
                continue
            f = (direction[0] * Rv, direction[1] * Rv)
            S[0] += f[0]; S[1] += f[1]
            Mz += self.mom(self.nodes[node], f, F(0), P)

        N = -(S[0] * e[0] + S[1] * e[1])
        Q = (S[0] * nrm[0] + S[1] * nrm[1])
        return N, Q, -Mz

    def check_section(self, member, t):
        """Сечение по дальней и по ближней части должны совпасть."""
        a = self.internal(member, t)
        b = self.internal_near(member, t)
        assert a == b, (f"{self.name}: сечение {member} t={t} не сходится: "
                        f"дальняя {tuple(map(float, a))} / "
                        f"ближняя {tuple(map(float, b))}")
        return a


def gauss(A, b):
    """Точное решение линейной системы (Fraction), метод Гаусса."""
    n = len(A[0])
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    where = []
    r = 0
    for c in range(n):
        piv = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        f = M[r][c]
        M[r] = [v / f for v in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                k = M[i][c]
                M[i] = [M[i][j] - k * M[r][j] for j in range(n + 1)]
        where.append(c)
        r += 1
        if r == len(M):
            break
    x = [F(0)] * n
    for i, c in enumerate(where):
        x[c] = M[i][n]
    # контроль: все уравнения выполняются
    for i, row in enumerate(A):
        s = sum(row[j] * x[j] for j in range(n))
        assert s == b[i], f"система не решилась, уравнение {i}"
    return x

