"""Квадратные уравнения, 8 класс — простой лист заданий без оформления + лист ответов.

    python3 build.py            проверить все ответы, собрать MD и два PDF
    python3 build.py --check    только проверка

По просьбе преподавателя лист — просто задания на белой странице: без теории, разборов и
оформления серии. Уравнения записаны разметкой из ../sborka.py; скрипт сам находит коэффициенты
(значения левой минус правой части в точках 0, 1, 2, проверка ещё в трёх), считает
дискриминант и корни точно (Fraction; корни с √ — в виде (p ± q√s) : r) и сверяет с ответом
из банка.
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from sborka import F, equal, html, plain, value, pdf, fnum  # noqa: E402

TITLE = "Квадратные уравнения"

# ------------------------------------------------------------------ алгебра уравнения


def coeffs(eq, var="x"):
    """a, b, c уравнения «левая = правая», перенесённого в левую часть."""
    left, right = eq.split("=")
    f = lambda t: value(left, {var: F(t)}) - value(right, {var: F(t)})
    c = f(0)
    a = (f(2) - 2 * f(1) + f(0)) / 2
    b = f(1) - f(0) - a
    for t in (3, 4, F(-5, 3)):
        assert f(t) == a * t * t + b * t + c, f"{eq}: не квадратное"
    return a, b, c


def normal(a, b, c):
    """Целые коэффициенты без общего множителя, a > 0."""
    den = math.lcm(a.denominator, b.denominator, c.denominator)
    k = [int(x * den) for x in (a, b, c)]
    g = math.gcd(*k) or 1
    k = [x // g for x in k]
    return [-x for x in k] if k[0] < 0 else k


def sqfree(m):
    """m = k²·s, s без квадратов."""
    k, s, d = 1, m, 2
    while d * d <= s:
        while s % (d * d) == 0:
            s //= d * d
            k *= d
        d += 1
    return k, s


def fmt_q(q):
    q = F(q)
    if q.denominator == 1:
        return fnum(q)
    return f"{'−' if q < 0 else ''}[[{abs(q.numerator)}|{q.denominator}]]"


def solve_eq(eq, var="x"):
    """Корни разметкой по возрастанию."""
    a, b, c = coeffs(eq, var)
    assert a != 0, f"{eq}: не квадратное"
    D = b * b - 4 * a * c
    if D < 0:
        return dict(a=a, b=b, c=c, roots=[], text="корней нет")
    n, d = D.numerator, D.denominator
    sn, sd = math.isqrt(n), math.isqrt(d)
    if sn * sn == n and sd * sd == d:
        s = F(sn, sd)
        rs = sorted({(-b - s) / (2 * a), (-b + s) / (2 * a)})
        return dict(a=a, b=b, c=c, roots=rs, text="; ".join(fmt_q(r) for r in rs))
    k, s = sqfree(n * d)                     # √D = k√s : d
    P, Q = -b / (2 * a), abs(F(k) / (2 * a * d))
    r = math.lcm(P.denominator, Q.denominator)
    p, q = int(P * r), int(Q * r)
    sur = f"{'' if q == 1 else q}√{s}"
    body = f"±{sur}" if p == 0 else f"{fnum(p)} ± {sur}"
    return dict(a=a, b=b, c=c, roots=None, text=body if r == 1 else f"[[{body}|{r}]]")


def poly(k, var="x"):
    out = []
    for coef, mon in zip(k, (f"{var}²", var, "")):
        if coef:
            v = abs(coef)
            out.append(("−" if coef < 0 else "+", (str(v) if v != 1 or not mon else "") + mon))
    s = ("−" if out[0][0] == "−" else "") + out[0][1]
    return s + "".join(f" {sg} {body}" for sg, body in out[1:])


def same_answer(stated, sol):
    stated = stated.strip()
    if stated == "нет":
        return sol["roots"] == []
    if "√" in stated:
        return stated.replace(" ", "") == sol["text"].replace(" ", "")
    if sol["roots"] is None:
        return False
    return sorted({value(x, {}) for x in stated.split(";")}) == sol["roots"]


def std_and_D(eq, sol, var="x"):
    """Стандартный вид и дискриминант — для листа ответов."""
    a, b, c = normal(sol["a"], sol["b"], sol["c"])
    std = f"{poly([a, b, c], var)} = 0"
    parts = [] if eq.replace(" ", "") == std.replace(" ", "") else [std]
    if b and c:
        parts.append(f"D = {fnum(b * b - 4 * a * c)}")
    return "; ".join(parts)


# ------------------------------------------------------------------ задания

BLOCKS = [
    dict(n="1", kind="simp", title="Раскройте скобки и приведите подобные", tasks=[
        dict(c="(x + 4)(x − 3)", a="x² + x − 12"),
        dict(c="(2x − 5)²", a="4x² − 20x + 25"),
        dict(c="(x − 2)² − (x + 1)(x − 4)", a="−x + 8"),
        dict(c="(x + [[1|2]])²", a="x² + x + [[1|4]]"),
    ]),
    dict(n="2", kind="eq", title="Решите неполные квадратные уравнения", tasks=[
        dict(e="x² − 16 = 0", a="−4; 4"),
        dict(e="3x² − 27 = 0", a="−3; 3"),
        dict(e="x² + 9 = 0", a="нет"),
        dict(e="2x² + 7x = 0", a="−[[7|2]]; 0"),
        dict(e="x² = 3x", a="0; 3"),
        dict(e="4x² − 1 = 0", a="−[[1|2]]; [[1|2]]"),
    ]),
    dict(n="3", kind="eq", title="Решите уравнения через дискриминант", tasks=[
        dict(e="x² − 5x + 6 = 0", a="2; 3"),
        dict(e="x² + 2x − 15 = 0", a="−5; 3"),
        dict(e="2x² − 3x − 2 = 0", a="−[[1|2]]; 2"),
        dict(e="x² − 6x + 9 = 0", a="3"),
        dict(e="x² + x + 5 = 0", a="нет"),
        dict(e="3x² + 5x − 2 = 0", a="−2; [[1|3]]"),
        dict(e="−x² + 4x + 5 = 0", a="−1; 5"),
        dict(e="x² − 4x + 1 = 0", a="2 ± √3"),
    ]),
    dict(n="4", kind="eq", title="Раскройте скобки и решите уравнения", tasks=[
        dict(e="(x − 3)(x + 2) = 14", a="−4; 5"),
        dict(e="(x + 4)² = 3x + 22", a="−6; 1"),
        dict(e="(2x − 1)² = (x + 1)²", a="0; 2"),
        dict(e="(2x + 3)(x − 1) = (x + 1)² + 2", a="−2; 3"),
        dict(e="(x − 2)² + (x + 3)² = 25", a="−3; 2"),
    ]),
    dict(n="5", kind="eq", title="Решите уравнения с дробными коэффициентами", tasks=[
        dict(e="[[x²|2]] − x − 4 = 0", a="−2; 4"),
        dict(e="[[x²|6]] − [[x|3]] = [[1|2]]", a="−1; 3"),
        dict(e="[[x² − 1|4]] = [[x + 1|2]]", a="−1; 3"),
        dict(e="0,5x² − 1,5x + 1 = 0", a="1; 2"),
        dict(e="[[2x² − 3|5]] − [[x|2]] = 2", a="−2; [[13|4]]"),
    ]),
]

TEXT = [
    dict(t="Одно натуральное число на 5 больше другого, а их произведение равно 84. Найдите эти числа.",
         e="x(x + 5) = 84", a="−12; 7", ans="7 и 12"),
    dict(t="Длина прямоугольника на 3 см больше ширины, площадь равна 54 см². Найдите стороны прямоугольника.",
         e="x(x + 3) = 54", a="−9; 6", ans="6 см и 9 см"),
    dict(t="Произведение двух последовательных натуральных чисел равно 156. Найдите эти числа.",
         e="x(x + 1) = 156", a="−13; 12", ans="12 и 13"),
    dict(t="Сторону квадрата увеличили на 3 см, и его площадь стала 64 см². Какой была сторона квадрата?",
         e="(x + 3)² = 64", a="−11; 5", ans="5 см"),
    dict(t="Мяч подбросили вверх. Его высота над землёй через t секунд равна h = 20t − 5t² метров. "
           "Через сколько секунд мяч будет на высоте 15 м?",
         e="20t − 5t² = 15", var="t", a="1; 3", ans="через 1 с и через 3 с (на подъёме и на спуске)"),
]

OSHIBKI = [
    dict(e="x² = 6x", wrong="делим обе части на x: x = 6", bad="6", fix="0; 6",
         why="делить на x нельзя — теряется корень 0; x(x − 6) = 0"),
    dict(e="2x² − 5x − 3 = 0", wrong="D = 25 − 24 = 1, x = (5 ± 1) : 4, x = 1,5 или x = 1", bad="1; [[3|2]]",
         fix="−[[1|2]]; 3", why="c = −3, поэтому D = 25 + 24 = 49"),
    dict(e="(x − 2)² = 3x − 2", wrong="x² − 4 = 3x − 2, x² − 3x − 2 = 0, D = 17", bad="[[3 ± √17|2]]",
         fix="1; 6", why="(x − 2)² = x² − 4x + 4, а не x² − 4; дальше x² − 7x + 6 = 0"),
]


def check():
    n = 0
    for b in BLOCKS:
        for i, t in enumerate(b["tasks"], 1):
            tag = f"задание {b['n']}.{i}"
            if b["kind"] == "simp":
                assert equal(t["c"], t["a"]), f"{tag}: раскрытие скобок не совпало"
                t["ans"], t["sol"] = t["a"], ""
            else:
                sol = solve_eq(t["e"])
                assert same_answer(t["a"], sol), f"{tag}: в банке «{t['a']}», посчитано «{sol['text']}»"
                t["ans"] = sol["text"] if sol["text"] == "корней нет" else "x = " + sol["text"]
                t["sol"] = std_and_D(t["e"], sol)
            n += 1
    for i, t in enumerate(TEXT, 1):
        sol = solve_eq(t["e"], t.get("var", "x"))
        assert same_answer(t["a"], sol), f"текстовая {i}: в банке «{t['a']}», посчитано «{sol['text']}»"
        t["roots"] = sol["text"]
        n += 1
    for k, o in enumerate(OSHIBKI, 1):
        sol = solve_eq(o["e"])
        assert same_answer(o["fix"], sol), f"ошибка {k}: верный ответ не совпал ({sol['text']})"
        assert not same_answer(o["bad"], sol), f"ошибка {k}: «неверный» ответ оказался верным"
        n += 1
    print(f"проверено: {n} заданий — все ответы сходятся")
    return n


# ------------------------------------------------------------------ простой лист

CSS = """
@page{size:A4;margin:16mm 15mm}
body{margin:0;background:#fff;color:#000;font-family:"Times New Roman","Liberation Serif",serif;font-size:13pt;line-height:1.45}
h1{font-size:15pt;margin:0 0 2pt}
.sub{margin:0 0 10pt}
h2{font-size:13pt;margin:14pt 0 6pt;break-after:avoid}
ol{margin:0;padding-left:22pt}
ol.cols{columns:2;column-gap:24pt}
li{margin:0 0 9pt;break-inside:avoid}
.frac{display:inline-flex;flex-direction:column;align-items:stretch;text-align:center;vertical-align:middle;line-height:1.15;margin:0 2px}
.frac>.nu{border-bottom:1px solid #000;padding:0 3px}
.frac>.de{padding:0 3px}
sup{font-size:.7em;line-height:0;vertical-align:.5em}
.w{display:block;margin-top:2pt}
.sol{display:block;font-size:11pt}
"""


def page(body):
    return (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>{TITLE}</title>'
            f"<style>{CSS}</style></head><body>\n{body}\n</body></html>")


def student():
    out = [f"<h1>{TITLE}</h1>", '<p class="sub">Домашнее задание</p>']
    for b in BLOCKS:
        cls = ' class="cols"'
        items = "".join(f"<li>{html(t['c'] if b['kind'] == 'simp' else t['e'])}</li>" for t in b["tasks"])
        out.append(f"<h2>{b['n']}. {b['title']}</h2><ol{cls}>{items}</ol>")
    items = "".join(f"<li>{t['t']}</li>" for t in TEXT)
    out.append(f"<h2>6. Решите задачи с помощью уравнения</h2><ol>{items}</ol>")
    items = "".join(f"<li>Решите уравнение {html(o['e'])}.<span class=\"w\">Решение: {html(o['wrong'])}</span></li>"
                    for o in OSHIBKI)
    out.append(f"<h2>7. Найдите ошибку в решении и решите правильно</h2><ol>{items}</ol>")
    return page("\n".join(out))


def answers():
    out = [f"<h1>{TITLE} — ответы</h1>", '<p class="sub">Для преподавателя</p>']
    for b in BLOCKS:
        items = "".join(f"<li>{html(t['ans'])}" + (f"<span class=\"sol\">{html(t['sol'])}</span>" if t["sol"] else "")
                        + "</li>" for t in b["tasks"])
        out.append(f"<h2>{b['n']}. {b['title']}</h2><ol class=\"cols\">{items}</ol>")
    items = "".join(f"<li>{t['ans']}<span class=\"sol\">{html(t['e'])}; корни {html(t['roots'])}</span></li>"
                    for t in TEXT)
    out.append(f"<h2>6. Задачи</h2><ol>{items}</ol>")
    items = "".join(f"<li>x = {html(o['fix'])}<span class=\"sol\">{html(o['why'])}</span></li>" for o in OSHIBKI)
    out.append(f"<h2>7. Найдите ошибку</h2><ol>{items}</ol>")
    return page("\n".join(out))


def build_md():
    z = [f"# {TITLE} — домашнее задание", ""]
    o = [f"# {TITLE} — ответы", "", "Все ответы посчитаны программой: `python3 build.py --check`.", ""]
    for b in BLOCKS:
        z += [f"## {b['n']}. {b['title']}", ""]
        o += [f"## {b['n']}. {b['title']}", ""]
        for i, t in enumerate(b["tasks"], 1):
            z.append(f"{i}. `{plain(t['c'] if b['kind'] == 'simp' else t['e'])}`")
            o.append(f"{i}. `{plain(t['ans'])}`" + (f" — {plain(t['sol'])}" if t["sol"] else ""))
        z.append("")
        o.append("")
    z += ["## 6. Решите задачи с помощью уравнения", ""] + [f"{i}. {t['t']}" for i, t in enumerate(TEXT, 1)]
    o += ["## 6. Задачи", ""] + [f"{i}. **{t['ans']}** — {plain(t['e'])}; корни {plain(t['roots'])}"
                                 for i, t in enumerate(TEXT, 1)]
    z += ["", "## 7. Найдите ошибку в решении и решите правильно", ""]
    z += [f"{i}. Решите уравнение `{plain(x['e'])}`. Решение: «{plain(x['wrong'])}»" for i, x in enumerate(OSHIBKI, 1)]
    o += ["", "## 7. Найдите ошибку", ""]
    o += [f"{i}. x = {plain(x['fix'])} — {plain(x['why'])}" for i, x in enumerate(OSHIBKI, 1)]
    (HERE / "ZADACHI.md").write_text("\n".join(z) + "\n", encoding="utf-8")
    (HERE / "OTVETY.md").write_text("\n".join(o) + "\n", encoding="utf-8")


def main():
    check()
    if "--check" in sys.argv:
        return
    build_md()
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "_print"
    out.mkdir(exist_ok=True)
    for name, body in ((f"{TITLE} — ДЗ ученика.pdf", student()), (f"{TITLE} — ответы.pdf", answers())):
        p = out / (name.replace(" ", "_") + ".html")
        p.write_text(body, encoding="utf-8")
        pdf(p, HERE / name)
    print("собрано:", ", ".join(x.name for x in sorted(HERE.glob("*.pdf"))))


if __name__ == "__main__":
    main()
