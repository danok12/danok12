"""Курсовая по ТСП, вариант 2: баланс земляных работ по котловану (п. 2.2.4, табл. 3 -
в форме с доски), распределение
земляных масс и картограмма (п. 2.2.5, табл. 4), средняя дальность (п. 2.2.6, табл. 5, 6).

По окончательным рабочим отметкам (после Δh). На картограмме объёмы фигур выемки -
в плотном теле (табл. 1, ст. 3), фигур насыпи - с учётом kо.р (ст. 6: Vн / kо.р).
Распределение - «с учётом наименьших моментов перемещений» (с. 19): минимум суммы
V·l, l - расстояние между центрами тяжести фигур (с. 18). Порядок - как в методичке:
сначала грунт выемок в насыпь (землеройно-транспортные машины), затем недостача
восполняется грунтом из котлована (самосвалы, от центра котлована, с. 19); остаток -
недостача, подвоз из карьера (с. 15). Машина по дальности (с. 22): до 70 м - бульдозер,
дальше - скрепер.
Объёмы восстанавливаются точно (Fraction) по опорным перевозкам решения ЛП.

Грунт котлована (с. 16 и лекция): пазухи засыпаются привозным песком (супесь - не песок),
в отвал у котлована идёт только грунт для засыпки съезда; остальное - в насыпь планировки,
а если её не хватает - на вывоз.
"""
from fractions import Fraction as Fr
from math import hypot
from scipy.optimize import linprog
import balans as B
import kotlovan as K

K_P = Fr("1.15")                 # kр, супесь: 1,12-1,17 (прил. 2); принято 1,15 (решение пользователя)
K_OR = B.K_OR
L_BULL = 70                      # бульдозер - до 70 м (с. 22), дальше - скрепер
P, KT = B.P1, B.K1

CUT = [g for g in P["FIGS"] if g["sign"] < 0]
FILL = [g for g in P["FIGS"] if g["sign"] > 0]
C = lambda g: (float(g["c"][0]), float(g["c"][1]))
PIT_C = (float(K.CENTER[0]), float(K.CENTER[1]))
dist = lambda a, b: hypot(a[0] - b[0], a[1] - b[1])

# ---------- грунт котлована ----------
V_K = Fr(KT["V_K"])                                  # котлован со съездом, плотное тело
V_OSN = Fr(KT["V_OSN"])                              # котлован без съезда
V_S = Fr(KT["V_S"])                                  # съезд (разработка = засыпка, местный грунт)
V_PAZ = Fr(KT["V_PAZ"])                              # пазухи - привозной песок
V_PODS = Fr(KT["V_PODS"])                            # подсыпка - привозной щебень
V_OTVAL = V_S / K_OR                                 # в отвал: на засыпку съезда (ΣVн местного грунта)
V_AVAIL = V_K - V_OTVAL                              # остальной грунт котлована - в транспортные средства


def transport(sup, dem, cost):
    """Минимум Σ x·cost при Σ_j x_ij = sup_i, Σ_i x_ij <= dem_j. -> {(i, j): x} точно."""
    n, m = len(sup), len(dem)
    c = [cost[i][j] for i in range(n) for j in range(m)]
    A_eq = [[1 if k // m == i else 0 for k in range(n * m)] for i in range(n)]
    A_ub = [[1 if k % m == j else 0 for k in range(n * m)] for j in range(m)]
    r = linprog(c, A_ub=A_ub, b_ub=[float(d) for d in dem], A_eq=A_eq, b_eq=[float(s) for s in sup],
                bounds=(0, None), method="highs-ds")
    assert r.status == 0, r.message
    arcs = [(k // m, k % m) for k in range(n * m) if r.x[k] > 1e-7]
    used = [sum(r.x[k] for k in range(n * m) if k % m == j) for j in range(m)]
    tight = [j for j in range(m) if abs(used[j] - float(dem[j])) < 1e-6]
    # точное решение: поставки - все равенства, плотные спросы - равенства (опорный план - лес)
    rows = [([1 if a[0] == i else 0 for a in arcs], Fr(sup[i])) for i in range(n)] + \
           [([1 if a[1] == j else 0 for a in arcs], Fr(dem[j])) for j in tight]
    x = solve_exact(rows, len(arcs))
    for (a, v), f in zip(zip(arcs, x), (r.x[i * m + j] for i, j in arcs)):
        assert abs(float(v) - f) < 1e-6, (a, v, f)
    return dict(zip(arcs, x))


def solve_exact(rows, nvar):
    """Гаусс в Fraction для переопределённой совместной системы ранга nvar."""
    M = [list(map(Fr, a)) + [Fr(b)] for a, b in rows]
    piv, r = [], 0
    for c in range(nvar):
        p = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        M[r] = [v / M[r][c] for v in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                M[i] = [a - M[i][c] * b for a, b in zip(M[i], M[r])]
        piv.append(c); r += 1
    assert len(piv) == nvar, "решение не единственное"
    assert all(all(v == 0 for v in row) for row in M[r:]), "система несовместна"
    x = [Fr(0)] * nvar
    for i, c in enumerate(piv):
        x[c] = M[i][-1]
    return x


# ---------- табл. 4: распределение ----------
DEM = [g["V"] / K_OR for g in FILL]                  # насыпь - грунт в плотном теле (ст. 6)
SUP = [g["V"] for g in CUT]                          # выемка - плотное тело (ст. 3)
ZTM = transport(SUP, DEM, [[dist(C(a), C(b)) for b in FILL] for a in CUT])
rest = [DEM[j] - sum(v for (i, jj), v in ZTM.items() if jj == j) for j in range(len(FILL))]
V_PIT_FILL = min(V_AVAIL, sum(rest))                 # из котлована в насыпь планировки
V_LISH = V_AVAIL - V_PIT_FILL                        # лишний грунт - вывоз (при положительном балансе)
PIT = transport([V_PIT_FILL], rest, [[dist(PIT_C, C(b)) for b in FILL]])
SHORT = {j: rest[j] - sum(v for (i, jj), v in PIT.items() if jj == j) for j in range(len(FILL))}
SHORT = {j: v for j, v in SHORT.items() if v > 0}    # недостача по фигурам - подвоз из карьера

# ---------- табл. 3: баланс земляных работ по котловану (форма с доски) ----------
T3_V = [("Котлован", V_OSN), ("Съезд", V_S)]                          # выемка, плотное тело
T3_N = [("Пазухи сооружения - песок из карьера", V_PAZ, V_PAZ / K_OR),  # насыпь: геом., потребный V/kо.р
        ("Съезд - грунт котлована из отвала", V_S, V_S / K_OR)]
T3_SUM_V = V_OSN + V_S
T3_SUM_N = V_S / K_OR                                                   # ΣVн местного грунта
T3_OTVAL = T3_SUM_N * K_P                                               # в отвал, с kр
T3_TRANSPORT = (T3_SUM_V - T3_SUM_N) * K_P                              # в транспортные средства, с kр
T3_PRIVOZ = [("Песок для засыпки пазух", V_PAZ / K_OR), ("Щебень для подсыпки", V_PODS / K_OR)]

MOVES = []                                           # (откуда, куда, V, l, машина)
for (i, j), v in sorted(ZTM.items()):
    l = dist(C(CUT[i]), C(FILL[j]))
    MOVES.append((CUT[i]["name"], FILL[j]["name"], v, l, "бульдозер" if l <= L_BULL else "скрепер"))
for (_, j), v in sorted(PIT.items()):
    MOVES.append(("котлован", FILL[j]["name"], v, dist(PIT_C, C(FILL[j])), "самосвал"))


def crossings():
    """Пары пересекающихся стрелок землеройно-транспортных машин (с. 18: не допускается)."""
    segs = [(C(CUT[i]), C(FILL[j]), (CUT[i]["name"], FILL[j]["name"])) for (i, j) in ZTM]

    def inter(p1, p2, p3, p4):
        d = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if p1 in (p3, p4) or p2 in (p3, p4):
            return False
        return d(p1, p2, p3) * d(p1, p2, p4) < 0 and d(p3, p4, p1) * d(p3, p4, p2) < 0

    return [(a[2], b[2]) for k, a in enumerate(segs) for b in segs[k + 1:] if inter(a[0], a[1], b[0], b[1])]


# ---------- табл. 5, 6: средняя дальность методом статических моментов ----------
def moments(parts):
    """parts: [(имя, V, (x, y))] -> строки (имя, V, x, y, Mx = x·V, My = y·V) и центр тяжести."""
    rows = [(nm, v, x, y, x * float(v), y * float(v)) for nm, v, (x, y) in parts]
    V = sum(float(r[1]) for r in rows)
    return rows, (sum(r[4] for r in rows) / V, sum(r[5] for r in rows) / V)


def mean_distance(src, dst):
    rs, (xs, ys) = moments(src)
    rd, (xd, yd) = moments(dst)
    return rs, rd, (xs, ys), (xd, yd), hypot(xs - xd, ys - yd)


got = lambda fig, pairs: sum(v for (i, j), v in pairs.items() if FILL[j]["name"] == fig)
T5 = mean_distance([(g["name"], g["V"], C(g)) for g in CUT],
                   [(g["name"], got(g["name"], ZTM), C(g)) for g in FILL if got(g["name"], ZTM)])
T6 = mean_distance([("котлован", V_PIT_FILL, PIT_C)],
                   [(g["name"], got(g["name"], PIT), C(g)) for g in FILL if got(g["name"], PIT)])
L_ANALYT = {t: sum(float(v) * l for _, _, v, l, m in MOVES if (m == "самосвал") == (t == "самосвал"))
            / sum(float(v) for _, _, v, l, m in MOVES if (m == "самосвал") == (t == "самосвал"))
            for t in ("ЗТМ", "самосвал")}

if __name__ == "__main__":
    f2 = lambda v: f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
    print("Табл. 3: баланс земляных работ по котловану")
    for nm, v in T3_V:
        print(f"   выемка  {nm:<38} {f2(v):>10}")
    for nm, g, v in T3_N:
        print(f"   насыпь  {nm:<38} {f2(g):>10}  потребный {f2(v)}")
    print(f"   ΣVв = {f2(T3_SUM_V)};  ΣVн местного грунта = {f2(T3_SUM_N)};  в отвал {f2(T3_OTVAL)} (с kр);"
          f"  в транспорт {f2(T3_TRANSPORT)} (с kр)")
    print(f"Из котлована в насыпь: {f2(V_PIT_FILL)} м3; вывоз: {f2(V_LISH)} м3; в отвал: {f2(V_OTVAL)} м3")
    print("Привозное:", {nm: f2(v) for nm, v in T3_PRIVOZ})
    print("Перемещения (табл. 4):")
    for a, b, v, l, m in MOVES:
        print(f"   {a:>9} -> {b:<4} {f2(v):>10} м3  {l:7.1f} м  {m}")
    print("Недостача:", {FILL[j]["name"]: f2(v) for j, v in SHORT.items()}, " всего", f2(sum(SHORT.values())))
    print("Пересечения стрелок ЗТМ:", crossings() or "нет")
    for t, (rs, rd, cs, cd, L) in (("5 (ЗТМ)", T5), ("6 (самосвалы)", T6)):
        print(f"Табл. {t}: центр выемки ({cs[0]:.2f}; {cs[1]:.2f}), насыпи ({cd[0]:.2f}; {cd[1]:.2f}),"
              f" Lср = {L:.2f} м")
    print("Аналитически: Lср ЗТМ =", round(L_ANALYT["ЗТМ"], 2), "м; самосвалы =", round(L_ANALYT["самосвал"], 2), "м")
