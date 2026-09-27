"""Сборка решения по трёхшарнирной раме-ферме (задание №1, вариант 19, нижняя схема).

Все уравнения узлов строятся из геометрии (rama.py), числа считаются
«вручную» в Decimal с теми округлениями, что записаны в тексте
(cos 45° и sin α, cos α — 5 знаков, результаты — 3 знака), и сверяются
с точным решением всей системы в дробях.
"""
import math
from decimal import Decimal as D, ROUND_HALF_UP
from fractions import Fraction as Fr
from pathlib import Path
from string import Template

from chertezhi import *  # noqa: F403 — Svg, палитра, fig_scheme
import rama
from rama import NODES, MEMBERS, LOADS, P

HERE = Path(__file__).parent


def R(v, n=3):
    if isinstance(v, Fr):
        v = D(v.numerator) / D(v.denominator)
    return D(v).quantize(D(1).scaleb(-n), rounding=ROUND_HALF_UP)


def fmt(v, n=3):
    r = R(v, n)
    if r == 0:
        return "0"
    s = format(r, "f")
    return s.replace("-", "−").replace(".", ",")


def fz(v, n=3):
    """Число для подстановки: отрицательное — в скобках."""
    s = fmt(v, n)
    return f"({s})" if s.startswith("−") else s


# ============================ точный расчёт ============================
VA, HA, VB, HB = rama.reactions()
N_ex, u_ex, R_all = rama.forces()
assert R_all == (VA, HA, VB, HB)
assert (VA, HA, VB, HB) == (Fr(343, 6), Fr(21, 2), Fr(245, 6), Fr(63, 2))

C45 = D("0.70711")
CA, SA = D("0.44721"), D("0.89443")      # наклонные стержни ног: tg α = 2
KSYM = {"1": "", "c45": "·cos 45°", "s45": "·sin 45°", "ca": "·cos α", "sa": "·sin α"}
KVAL = {"1": D(1), "c45": C45, "s45": C45, "ca": CA, "sa": SA}

EXT = {   # внешние силы в узлах: (символ, ось, знак, значение)
    "A": [("H<sub>A</sub>", 0, +1, R(HA)), ("V<sub>A</sub>", 1, +1, R(VA))],
    "B": [("H<sub>B</sub>", 0, -1, R(HB)), ("V<sub>B</sub>", 1, +1, R(VB))],
    "2": [("P", 1, -1, D(14))],
    "1′": [("P", 1, -1, D(14))],
    "4′": [("3P", 1, -1, D(42))],
    "7": [("2P", 1, -1, D(28))],
    "9′": [("P", 0, +1, D(14))],
    "F": [("P/2", 0, +1, D(7))],
}


def msym(m):
    return f"N<sub>{m[0]}–{m[1]}</sub>"


def terms(n):
    """Слагаемые ΣX и ΣY для узла n: (вид, ключ, знак, коэффициент)."""
    tx, ty = [], []
    for m in MEMBERS:
        if n not in m:
            continue
        o = m[1] if m[0] == n else m[0]
        dx = NODES[o][0] - NODES[n][0]
        dy = NODES[o][1] - NODES[n][1]
        sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
        if dy == 0:
            tx.append(("N", m, sx, "1"))
        elif dx == 0:
            ty.append(("N", m, sy, "1"))
        elif abs(dx) == abs(dy):
            tx.append(("N", m, sx, "c45"))
            ty.append(("N", m, sy, "s45"))
        else:
            assert abs(dy) == 2 * abs(dx)
            tx.append(("N", m, sx, "ca"))
            ty.append(("N", m, sy, "sa"))
    for sym, ax, sg, val in EXT.get(n, []):
        (tx if ax == 0 else ty).append(("E", (sym, val), sg, "1"))
    return tx, ty


def tsym(t):
    kind, key, sg, k = t
    s = msym(key) if kind == "N" else key[0]
    return s + KSYM[k]


def tval(t, val):
    kind, key, sg, k = t
    return val[key] if kind == "N" else key[1]


def join(parts):
    """[(знак, текст)] -> «a − b + c»."""
    out = ""
    for i, (sg, s) in enumerate(parts):
        if i == 0:
            out = ("−" if sg < 0 else "") + s
        else:
            out += (" − " if sg < 0 else " + ") + s
    return out or "0"


def eq_line(name, ts):
    return f"{name} = {join([(t[2], tsym(t)) for t in ts])} = 0"


FAM = {"c45": "45", "s45": "45", "ca": "ca", "sa": "sa", "1": "1"}


def num(v):
    return format(v, "f").replace(".", ",")


def solve_one(ts, U, val):
    """Уравнение с одним неизвестным U: возвращает (html, значение).

    U = −Σ(другие)/(коэф. при U). Нулевые слагаемые в подстановке опускаются.
    """
    tu = next(t for t in ts if t[0] == "N" and t[1] == U)
    others = [t for t in ts if t is not tu]
    su, ku = tu[2], tu[3]
    kv_u = KVAL[ku]
    num_sym = join([(-t[2] * su, tsym(t)) for t in others])
    total = D(0)
    sub_parts = []
    for t in others:
        sg = -t[2] * su
        v = tval(t, val)
        kv = KVAL[t[3]]
        total += sg * R(v * kv)
        if v != 0:
            sub_parts.append((sg, fz(v) + ("·" + num(kv) if t[3] != "1" else "")))
    res = R(total / kv_u) if ku != "1" else R(total)
    head = f"⇒ {msym(U)}"
    if not others:
        return f"{head} = <b class='r'>0</b>", D(0)
    wrap = lambda x, n: f"({x})" if n > 1 else x
    # одно слагаемое с тем же коэффициентом, что при U: коэффициенты сокращаются
    if len(others) == 1 and FAM[others[0][3]] == FAM[ku] and ku != "1":
        t = others[0]
        sg = -t[2] * su
        sym = ("−" if sg < 0 else "") + (msym(t[1]) if t[0] == "N" else t[1][0])
        v = tval(t, val)
        res = R(sg * v)
        sub = f" = {'−' if sg < 0 else ''}{fz(v)}"
        if v == 0 or sub[3:] == fmt(res):
            sub = ""
        return f"{head} = {sym}{sub} = <b class='r'>{fmt(res)} кН</b>", res
    sym = num_sym if ku == "1" else f"{wrap(num_sym, len(others))} / {KSYM[ku][1:]}"
    if not sub_parts:
        return f"{head} = {sym} = <b class='r'>0</b>", D(0)
    subst = join(sub_parts)
    single_plain = len(sub_parts) == 1 and ku == "1" and "·" not in subst
    if ku != "1":
        subst = f"{wrap(subst, len(sub_parts))} / {num(kv_u)}"
    mid = "" if single_plain else f" = {subst}"
    return f"{head} = {sym}{mid} = <b class='r'>{fmt(res)} кН</b>", res


def check_line(name, ts, val):
    total = D(0)
    parts = []
    for t in ts:
        v = tval(t, val)
        kv = KVAL[t[3]]
        total += t[2] * R(v * kv)
        if v != 0:
            parts.append((t[2], fz(v) + ("·" + num(kv) if t[3] != "1" else "")))
    ok = abs(total) <= D("0.006")
    return f"{name} = {join(parts)} = {fmt(total)} ≈ 0 <span class='ok'>✓</span>", total, ok


ORDER = ["1′", "1", "2", "A", "D", "E", "2′", "3′", "3", "4", "4′", "C",
         "6", "6′", "9′", "9", "B", "F", "G", "8", "8′", "7′", "7"]

NOTES = {
    "1′": "Конец левой консоли: два стержня под прямым углом и сила P. Начинаем с него — неизвестных два.",
    "A": "Опорный узел: реакции V<sub>A</sub>, H<sub>A</sub> уже известны, неизвестных два.",
    "D": "Горизонтальный стержень D–E — единственный с проекцией на ось x, а внешних сил нет, поэтому N<sub>D–E</sub> = 0.",
    "E": "Оба неизвестных стержня наклонные и входят в оба уравнения — решаем их совместно.",
    "4": "Узел без нагрузки с тремя стержнями, два из которых (3–4 и 4–C) лежат на одной прямой: третий стержень 4–4′ нулевой.",
    "4′": "Неизвестный один — N<sub>4′–C</sub>; второе уравнение узла становится проверкой.",
    "C": "Ключевой шарнир: здесь соединяются левая и правая половины. Усилия левой половины известны — находим два стержня правой.",
    "6": "Как узел 4: без нагрузки, 6–7 и C–6 на одной прямой, поэтому стойка 6–6′ нулевая.",
    "9′": "Конец правой консоли: сила P действует вдоль нижнего пояса, стойка 9–9′ нулевая.",
    "9": "Узел без нагрузки с двумя неколлинеарными неизвестными (9–9′ = 0): оба оставшихся стержня нулевые.",
    "B": "Опорный узел: реакции V<sub>B</sub>, H<sub>B</sub> известны.",
    "G": "Как узел E: два наклонных стержня решаем совместно.",
    "8": "Узел без нагрузки: 8–9 = 0, тогда из ΣX нулевой и 7–8, из ΣY — стойка 8–8′.",
    "7′": "Неизвестный один — N<sub>7–7′</sub>; второе уравнение — проверка.",
    "7": "Все усилия уже найдены: оба уравнения — проверки.",
}


def node_equations():
    val = {}
    blocks = []
    nchecks = 0
    for n in ORDER:
        tx, ty = terms(n)
        unknown_here = {m for m in MEMBERS if n in m and m not in val}
        lines = [eq_line("ΣX", tx), eq_line("ΣY", ty)]
        unk = lambda ts: [t[1] for t in ts if t[0] == "N" and t[1] not in val]
        found = []
        if n in ("E", "G"):
            lines += special_pair(n, val)
            found = [m for m in MEMBERS if n in m and m in val and m not in found]
        else:
            pending = [("ΣX", tx), ("ΣY", ty)]
            while pending:
                pending.sort(key=lambda p: (len(unk(p[1])) == 0, len(unk(p[1]))))
                name, ts = pending.pop(0)
                us = unk(ts)
                if len(us) == 1:
                    line, res = solve_one(ts, us[0], val)
                    val[us[0]] = res
                    lines.append(f"из {name}: {line}")
                elif len(us) == 0:
                    line, total, ok = check_line(name, ts, val)
                    assert ok, (n, name, total)
                    lines.append(f"<b>проверка</b> {line}")
                    nchecks += 1
                else:
                    raise RuntimeError(f"узел {n}: {name} — два неизвестных")
        blocks.append((n, lines, unknown_here))
    assert nchecks == 4, nchecks
    return blocks, val


def special_pair(n, val):
    """Узлы E и G: два наклонных неизвестных, решаем совместно."""
    if n == "E":
        a, dd, u1, u2 = ("E", "A"), ("D", "E"), ("3′", "E"), ("2′", "E")
        rhs1 = R(val[a] + R(val[dd] / CA))                 # N_3′E − N_2′E
        rhs2 = val[a]                                     # N_3′E + N_2′E
        v1 = R((rhs1 + rhs2) / 2)
        v2 = R(rhs2 - v1)
        val[u1], val[u2] = v1, v2
        return [
            f"ΣX : cos α ⇒ {msym(u1)} − {msym(u2)} = {msym(a)} + {msym(dd)} / cos α = {fz(val[a])} + 0 = {fmt(rhs1)}",
            f"ΣY : sin α ⇒ {msym(u1)} + {msym(u2)} = {msym(a)} = {fmt(rhs2)}",
            f"⇒ складываем: {msym(u1)} = ({fmt(rhs1)} + {fz(rhs2)}) / 2 = <b class='r'>{fmt(v1)} кН</b>; "
            f"{msym(u2)} = {fmt(rhs2)} − {fz(v1)} = <b class='r'>{fmt(v2)} кН</b>",
        ]
    gb, fg, u1, u2 = ("G", "B"), ("F", "G"), ("8′", "G"), ("7′", "G")
    rhs1 = R(-val[gb] - R(val[fg] / CA))                   # N_8′G − N_7′G
    rhs2 = val[gb]                                        # N_8′G + N_7′G
    v1 = R((rhs1 + rhs2) / 2)
    v2 = R(rhs2 - v1)
    val[u1], val[u2] = v1, v2
    return [
        f"ΣX : cos α ⇒ {msym(u1)} − {msym(u2)} = −{msym(gb)} − {msym(fg)} / cos α = −{fz(val[gb])} − {fz(val[fg])}/0,44721 = {fmt(rhs1)}",
        f"ΣY : sin α ⇒ {msym(u1)} + {msym(u2)} = {msym(gb)} = {fmt(rhs2)}",
        f"⇒ складываем: {msym(u1)} = ({fmt(rhs1)} + {fz(rhs2)}) / 2 = <b class='r'>{fmt(v1)} кН</b>; "
        f"{msym(u2)} = {fmt(rhs2)} − {fz(v1)} = <b class='r'>{fmt(v2)} кН</b>",
    ]


BLOCKS, HAND = node_equations()
assert set(HAND) == set(MEMBERS)
worst = 0
for m in MEMBERS:
    diff = abs(float(HAND[m]) - N_ex[m])
    worst = max(worst, diff)
    assert diff < 0.006, (m, HAND[m], N_ex[m])
EX2 = {m: R(repr(N_ex[m]) if abs(N_ex[m]) > 1e-12 else "0", 2) for m in MEMBERS}
mism = [m for m in MEMBERS if R(HAND[m], 2) != EX2[m]]


# ============================ проверка сечением (Риттер) ============================
# сечение через панель 3–4: стержни 3–4, 3–4′, 3′–4′; левая часть с опорой A
rit_34 = -2 * VA + 2 * HA + 5 * P          # ΣM(4′)
rit_3p4p = VA - 3 * HA - 3 * P             # ΣM(3)
rit_diag = (VA - 2 * P) * Fr(1)            # ΣY → N·sin45°
assert abs(float(rit_34) - N_ex[("3", "4")]) < 1e-9
assert abs(float(rit_3p4p) - N_ex[("3′", "4′")]) < 1e-9
assert abs(float(rit_diag) / math.sqrt(0.5) - N_ex[("3", "4′")]) < 1e-9


# ============================ сборка HTML ============================
from chertezhi import fig_scheme, fig_numbering, fig_whole, fig_halves, fig_node, fig_ritter, fig_forces  # noqa: E402

EXT_LAB = {"A": [("H", 0, +1, "H_{A} = 10,5"), ("V", 1, +1, "V_{A} = 57,167")],
           "B": [("H", 0, -1, "H_{B} = 31,5"), ("V", 1, +1, "V_{B} = 40,833")],
           "2": [("P", 1, -1, "P = 14")], "1′": [("P", 1, -1, "P = 14")],
           "4′": [("P", 1, -1, "3P = 42")], "7": [("P", 1, -1, "2P = 28")],
           "9′": [("P", 0, +1, "P = 14")], "F": [("P", 0, +1, "P/2 = 7")]}


def uzly_html():
    out = []
    for i, (n, lines, unknown) in enumerate(BLOCKS):
        fig = fig_node(n, unknown, EXT_LAB.get(n, []), f"u{i}")
        note = f'<p class="note">{NOTES[n]}</p>' if n in NOTES else ""
        body = "".join(f"<div>{ln}</div>" for ln in lines)
        out.append(f'<div class="uzel"><div>{fig}</div><div>{note}<div class="f">{body}</div></div></div>')
    return "\n".join(out)


def v2(m):
    v = EX2[m]
    return "0" if v == 0 else fmt(v, 2)


def tablica():
    left = [m for m in MEMBERS if set(m) <= {"1", "2", "3", "4", "C", "1′", "2′", "3′", "4′", "D", "E", "A"}]
    right = [m for m in MEMBERS if m not in left]
    assert len(left) == len(right) == 21

    def table(ms, title):
        rows = []
        for m in ms:
            v = EX2[m]
            cls, kind = ("z", "0") if v == 0 else (("t", "растяжение") if v > 0 else ("cm", "сжатие"))
            rows.append(f'<tr><td class="l">{m[0]}–{m[1]}</td><td class="{cls}">{v2(m)}</td><td>{kind if v != 0 else "нулевой"}</td></tr>')
        return f'<table><tr><th class="l">{title}</th><th>N, кН</th><th>характер</th></tr>' + "".join(rows) + "</table>"
    return table(left, "левая половина") + table(right, "правая половина")


def build():
    zero = [f"{m[0]}–{m[1]}" for m in MEMBERS if EX2[m] == 0]
    V = dict(
        VA=fmt(VA), VB=fmt(VB), HA="10,5", HB="31,5", VA2=fmt(VA, 2), VB2=fmt(VB, 2),
        R34=fmt(rit_34), R3p4p=fmt(rit_3p4p), R34p=fmt(R(R(VA) - 28) / C45),
        H34=fmt(HAND[("3", "4")]), H3p4p=fmt(HAND[("3′", "4′")]), H34p=fmt(HAND[("3", "4′")]),
        R34p2=fmt(EX2[("3", "4′")], 2), GB=v2(("G", "B")), G7=v2(("7′", "G")), S77=v2(("7", "7′")),
        NZ=str(len(zero)), ZLIST=", ".join(zero),
        FIG1=fig_scheme(), FIG2=fig_numbering(), FIG3=fig_whole(False, "r3"), FIG4=fig_halves(),
        FIG5=fig_ritter(), FIG6=fig_forces(N_ex), UZLY=uzly_html(), TABLICA=tablica(),
    )
    html = Template((HERE / "shablon.html").read_text(encoding="utf-8")).substitute(**V)
    (HERE / "reshenie.html").write_text(html, encoding="utf-8")
    return V


if __name__ == "__main__":
    Vb = build()
    print("reshenie.html собран; нулевых стержней:", Vb["NZ"])
    print(f"V_A={VA} H_A={HA} V_B={VB} H_B={HB}")
    print("макс. расхождение ручного счёта с точным:", round(worst, 4))
    print("расхождения при округлении до 0,01:", [(m, HAND[m], EX2[m]) for m in mism])
    for n, lines, _ in BLOCKS:
        print(f"--- узел {n}")
        for s in lines:
            print("   ", s.replace("<sub>", "").replace("</sub>", "").replace("<b class='r'>", "").replace("</b>", ""))
