"""Дроби и степени, 8 класс — банк задач, проверка ответов и сборка страницы и PDF.

    python3 build.py            проверить все ответы и выкладки, собрать index.html, MD и PDF
    python3 build.py --check    только проверка

Каждое условие, ответ и строка разбора записаны разметкой из ../sborka.py; одна и та же
строка идёт и в HTML, и в проверку, поэтому текст на листе совпадает с проверенным.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from sborka import F, equal, html, html_doc, plain, value, variant, printable, pdf, screenshot, fnum  # noqa: E402

ARTIFACT = "https://claude.ai/artifact/KvUX6F38Wv4Ao6y2LSktmh"  # страница занятия (версия преподавателя)
TITLE = "Дроби и степени"

# ------------------------------------------------------------------ банк задач
# c — условие, a — ответ, alt — та же величина в другой записи, star — по желанию,
# at — значения букв для «найдите значение», hint — пояснение преподавателю

BLOCKS = [
    dict(id="b0", n="0", title="Разминка: обычные дроби",
         lead="Вычислите. Правила те же, что и с буквами, только проще. Ответ — несократимая дробь.",
         tasks=[
             dict(c="[[5|6]] − [[3|8]]", a="[[11|24]]"),
             dict(c="[[7|12]] + [[5|18]]", a="[[31|36]]"),
             dict(c="[[3|4]] · [[8|15]]", a="[[2|5]]"),
             dict(c="[[9|14]] : [[15|28]]", a="[[6|5]]", hint="это 1 [[1|5]]; не забыть перевернуть вторую дробь"),
             dict(c="([[1|4]] + [[1|6]]) · [[12|5]]", a="1"),
             dict(c="([[5|6]] − [[1|4]]) : [[7|8]]", a="[[2|3]]"),
             dict(c="(−[[2|3]])³", a="−[[8|27]]", hint="нечётная степень сохраняет минус"),
         ]),
    dict(id="b1", n="1", title="Степени",
         lead="Упростите. Числа считай отдельно, каждую букву — отдельно, по правилам степеней.",
         tasks=[
             dict(c="a⁵ · a³ : a⁶", a="a²"),
             dict(c="(x³)⁴ : x⁹", a="x³", hint="ловушка (x³)⁴ = x⁷"),
             dict(c="(2a³)⁴", a="16a¹²", hint="ловушка 2a¹²: коэффициент тоже в степень"),
             dict(c="(−3x²y)³", a="−27x⁶y³"),
             dict(c="5a²b · (−2ab³)²", a="20a⁴b⁷"),
             dict(c="[[(x²y³)⁴|x⁵y¹⁰]]", a="x³y²"),
             dict(c="([[a³|2b²]])⁴", a="[[a¹²|16b⁸]]"),
             dict(c="(−[[2x|y³]])⁵", a="−[[32x⁵|y¹⁵]]"),
             dict(c="[[4⁵ · 8²|2¹⁴]]", a="4", hint="всё к основанию 2: 2¹⁰ · 2⁶ : 2¹⁴"),
             dict(c="[[3⁵ · 2⁴|6⁴]]", a="3", hint="2⁴ · 3⁴ = 6⁴"),
             dict(c="[[6¹⁰|2⁹ · 3⁸]]", a="18", star=True, hint="6¹⁰ = 2¹⁰ · 3¹⁰, остаётся 2 · 3²"),
         ]),
    dict(id="b2", n="2", title="Сокращение дробей",
         lead="Сократите дроби. Сначала разложи числитель и знаменатель на множители, потом сокращай.",
         tasks=[
             dict(c="[[15a³b²|25ab⁵]]", a="[[3a²|5b³]]"),
             dict(c="[[x² − 16|3x + 12]]", a="[[x − 4|3]]"),
             dict(c="[[a² − 6a + 9|a² − 9]]", a="[[a − 3|a + 3]]"),
             dict(c="[[5x − 5y|y² − x²]]", a="−[[5|x + y]]", hint="y − x = −(x − y), отсюда минус"),
             dict(c="[[ab + 2b|a² + 4a + 4]]", a="[[b|a + 2]]"),
             dict(c="[[m³ − m|m² + m]]", a="m − 1"),
         ]),
    dict(id="b3", n="3", title="Сложение и вычитание: разные знаменатели",
         lead="Выполните действия. В задачах 1–5 знаменатели раскладывать не нужно, в 6–11 — нужно. "
              "Ответ должен быть несократимым.",
         tasks=[
             dict(c="[[3|4a]] + [[5|6a]]", a="[[19|12a]]"),
             dict(c="[[x − 2|3x]] + [[x + 1|6x]]", a="[[x − 1|2x]]", hint="в конце сокращается на 3"),
             dict(c="[[5|6x²y]] − [[1|4xy²]]", a="[[10y − 3x|12x²y²]]"),
             dict(c="[[a + b|ab]] − [[b + c|bc]]", a="[[c − a|ac]]", hint="числитель bc − ab = b(c − a), b сокращается"),
             dict(c="[[2|x − 3]] − [[1|x + 3]]", a="[[x + 9|x² − 9]]"),
             dict(c="x + 1 − [[x²|x − 1]]", a="[[1|1 − x]]", alt=["−[[1|x − 1]]"],
                  hint="x + 1 записать как дробь со знаменателем x − 1"),
             dict(c="[[3|2a − 6]] − [[1|a − 3]]", a="[[1|2a − 6]]"),
             dict(c="[[b|b² − 25]] − [[1|b + 5]]", a="[[5|b² − 25]]"),
             dict(c="[[4|x² − 2x]] + [[2|4 − x²]]", a="[[2(x + 4)|x(x² − 4)]]",
                  hint="4 − x² = −(x − 2)(x + 2): плюс перед второй дробью становится минусом"),
             dict(c="[[1|a² − 6a + 9]] − [[1|a² − 9]]", a="[[6|(a − 3)²(a + 3)]]"),
             dict(c="[[1|x(x + 1)]] + [[1|(x + 1)(x + 2)]] + [[1|(x + 2)(x + 3)]]",
                  a="[[3|x(x + 3)]]", star=True,
                  hint="можно складывать по очереди; или заметить [[1|x(x + 1)]] = [[1|x]] − [[1|x + 1]]"),
         ]),
    dict(id="b4", n="4", title="Умножение, деление, возведение в степень",
         lead="Выполните действия. Ничего не перемножай раньше времени: разложи, запиши одной дробью, сократи.",
         tasks=[
             dict(c="[[6a²|5b]] · [[10b³|9a]]", a="[[4ab²|3]]"),
             dict(c="[[14x³|y²]] : [[21x|y⁵]]", a="[[2x²y³|3]]"),
             dict(c="([[2a|b²]])³ · [[b⁵|4a²]]", a="[[2a|b]]"),
             dict(c="(−[[3m|2n²]])² : [[9m³|4n]]", a="[[1|mn³]]"),
             dict(c="[[x² − 25|4x]] · [[8x²|x + 5]]", a="2x(x − 5)"),
             dict(c="[[a² − ab|b²]] : [[a² − b²|b]]", a="[[a|b(a + b)]]"),
             dict(c="[[3y − 3|y + 2]] : [[y² − 1|y² + 2y]]", a="[[3y|y + 1]]"),
             dict(c="[[c² + 6c + 9|c² − 4]] · [[c − 2|c + 3]]", a="[[c + 3|c + 2]]"),
             dict(c="([[x²|x − 1]])² · ([[x − 1|x]])³", a="x(x − 1)"),
             dict(c="[[a + b|a − b]] · [[a² − 2ab + b²|a² − b²]]", a="1"),
         ]),
    dict(id="b5", n="5", title="Посложнее: несколько действий",
         lead="Упростите. Сначала скобки, потом умножение и деление; решай по действиям, как в разборе 4.",
         tasks=[
             dict(c="([[1|a]] − [[1|b]]) · [[ab|b − a]]", a="1"),
             dict(c="([[x|x − 2]] − 1) : [[4|x² − 4]]", a="[[x + 2|2]]"),
             dict(c="([[a|a + 3]] + [[a|a − 3]]) · [[a² − 9|4a]]", a="[[a|2]]"),
             dict(c="([[3|m − n]] + [[3|m + n]]) · [[m² − n²|m²]]", a="[[6|m]]"),
             dict(c="([[x²y|3z]])³ : [[x⁵y²|9z²]]", a="[[xy|3z]]"),
             dict(c="([[a + 2|a − 2]] − [[a − 2|a + 2]]) · [[a² − 4|4a]]", a="2",
                  hint="(a + 2)² − (a − 2)² = 8a"),
             dict(c="([[1|a − 3]] + [[1|a + 3]]) · [[a² − 9|a²]]", a="[[2|a]]",
                  at={"a": F("-0.4")}, at_text="a = −0,4"),
             dict(c="([[x|x − 1]] − [[x + 1|x]]) : [[1|x² − x]]", a="1", star=True, prove=True),
             dict(c="([[2b|b + 1]])² : ([[4b|b² − 1]] · [[b − 1|b + 1]])", a="b", star=True),
         ]),
]

# ------------------------------------------------------------------ разборы
# строка: (выражения через «=», пояснение); всё в одном разборе равно первому выражению

RAZBORY = {
    "r1": dict(steps=[
        (["[[(2x³y)³ · (3xy²)²|12x⁸y⁶]]", "[[8x⁹y³ · 9x²y⁴|12x⁸y⁶]]"],
         "каждый множитель скобки — в степень: 2³ = 8, (x³)³ = x⁹; 3² = 9, (y²)² = y⁴"),
        (["[[72x¹¹y⁷|12x⁸y⁶]]"], "числа перемножаем, у одинаковых букв складываем показатели"),
        (["6x³y"], "делим: 72 : 12 = 6, x¹¹ : x⁸ = x³, y⁷ : y⁶ = y"),
    ]),
    "r2": dict(steps=[
        (["[[5|x² − 4]] − [[1|x² + 2x]]", "{x}[[5|(x − 2)(x + 2)]] − {x − 2}[[1|x(x + 2)]]"],
         "знаменатели разложены, над дробями — дополнительные множители"),
        (["[[5x − (x − 2)|x(x − 2)(x + 2)]]"], "числитель вычитаемой дроби — в скобках"),
        (["[[5x − x + 2|x(x − 2)(x + 2)]]", "[[4x + 2|x(x − 2)(x + 2)]]", "[[2(2x + 1)|x(x² − 4)]]"],
         "минус перед скобкой поменял знак у обоих слагаемых"),
    ]),
    "r3a": dict(steps=[
        (["[[x² − 4|3x + 9]] · [[x + 3|x² − 2x]]", "[[(x − 2)(x + 2)|3(x + 3)]] · [[x + 3|x(x − 2)]]"],
         "разложили всё, что раскладывается"),
        (["[[~(x − 2)~(x + 2)~(x + 3)~|3~(x + 3)~ · x~(x − 2)~]]", "[[x + 2|3x]]"],
         "одна дробь, одинаковые скобки сокращаем, ничего не перемножая"),
    ]),
    "r3b": dict(steps=[
        (["[[a² − 1|a²]] : [[a + 1|a]]", "[[(a − 1)(a + 1)|a²]] · [[a|a + 1]]"],
         "деление — умножение на перевёрнутую вторую дробь"),
        (["[[(a − 1)(a + 1) · a|a² · (a + 1)]]", "[[a − 1|a]]"], "сократили a + 1 и одно a"),
    ]),
    "r4a": dict(steps=[
        (["{x + 3}[[x|x − 3]] − {x − 3}[[x|x + 3]]", "[[x(x + 3) − x(x − 3)|(x − 3)(x + 3)]]"],
         "общий знаменатель (x − 3)(x + 3)"),
        (["[[x² + 3x − x² + 3x|x² − 9]]", "[[6x|x² − 9]]"], "раскрыли скобки, x² взаимно уничтожились"),
    ]),
    "r4b": dict(steps=[
        (["[[6x|x² − 9]] · [[x² − 9|2x²]]", "[[6x · (x² − 9)|(x² − 9) · 2x²]]", "[[3|x]]"],
         "сократили x² − 9, 6 и 2, x и x²"),
    ]),
}
# связки между частями разборов: исходное выражение = итог
RAZBOR_LINKS = [
    ("([[x|x − 3]] − [[x|x + 3]]) · [[x² − 9|2x²]]", "[[3|x]]"),
]

# формулы и примеры из теории
THEORY = [
    ("[[x² − 9|2x + 6]]", "[[(x − 3)(x + 3)|2(x + 3)]]"), ("[[x² − 9|2x + 6]]", "[[x − 3|2]]"),
    ("x³ · x⁴", "x⁷"), ("x⁹ : x⁴", "x⁵"), ("(x³)⁴", "x¹²"), ("(2x³)⁴", "16x¹²"),
    ("([[x²|3]])³", "[[x⁶|27]]"), ("(−2)⁴", "16"), ("(−2)³", "−8"),
    ("[[x|x − 5]] + [[5|5 − x]]", "1"), ("[[x|x − 5]] − [[5|x − 5]]", "1"), ("(−3x²)²", "9x⁴"),
    ("(−x)⁵", "−x⁵"), ("3x + 12", "3(x + 4)"), ("a² − 2a", "a(a − 2)"), ("m³ − m", "m(m − 1)(m + 1)"),
    ("5 − x", "−(x − 5)"), ("4 − x²", "−(x² − 4)"), ("[[x + 6|x + 3]]", "[[x + 6|x + 3]]"),
]
THEORY_FALSE = [("[[x + 6|x + 3]]", "2"), ("(x³)⁴", "x⁷"), ("(2x)³", "2x³"), ("x³ + x⁴", "x⁷")]
# числа, которые стоят в тексте теории: (выражение, буквы, значение)
THEORY_VALUES = [
    ("[[x + 6|x + 3]]", {"x": 1}, F(7, 4)),
    ("[[5|x² − 4]] − [[1|x² + 2x]]", {"x": 3}, F(14, 15)),
    ("[[2(2x + 1)|x(x² − 4)]]", {"x": 3}, F(14, 15)),
    ("[[x² − 4|x² − 2x]]", {"x": 1}, F(3)),
]

# ------------------------------------------------------------------ найди ошибку
# chain — неверное решение, bad — номер неверного перехода (0 — между 1-м и 2-м), fix — верный ответ

OSHIBKI = [
    dict(chain=["a³ · (a²)⁴ : a⁵", "a³ · a⁶ : a⁵", "a⁹ : a⁵", "a⁴"], bad=0, fix="a⁶",
         why="Степень в степень — показатели <strong>перемножают</strong>: (a²)⁴ = a⁸, а не a⁶. "
             "Верно: a³ · a⁸ : a⁵ = a⁶."),
    dict(chain=["(−2x³y)⁴", "−2x¹²y⁴"], bad=0, fix="16x¹²y⁴",
         why="Две ошибки сразу: в степень не возвели число и не убрали минус. (−2)⁴ = 16 — "
             "чётная степень делает результат положительным."),
    dict(chain=["[[4a|b²]] : [[2a²|b]]", "[[b²|4a]] · [[2a²|b]]", "[[2a²b²|4ab]]", "[[ab|2]]"], bad=0,
         fix="[[2|ab]]",
         why="Перевернули первую дробь, а переворачивают <strong>вторую</strong> (делитель): "
             "[[4a|b²]] · [[b|2a²]] = [[2|ab]]. Проверка на числах: 1 : [[1|2]] = 2, а не [[1|2]]."),
    dict(chain=["[[x² − 4|x² − 2x]]", "[[−4|−2x]]", "[[2|x]]"], bad=0, fix="[[x + 2|x]]",
         why="Сократили x² — а это слагаемое, не множитель. Сначала разложить: "
             "[[(x − 2)(x + 2)|x(x − 2)]] = [[x + 2|x]]. Подстановка x = 1: условие даёт 3, «ответ» — 2."),
    dict(chain=["{x + 2}[[1|x − 2]] − [[x + 1|x² − 4]]", "[[x + 2 − x + 1|x² − 4]]", "[[3|x² − 4]]"], bad=0,
         fix="[[1|x² − 4]]",
         why="Минус перед дробью относится ко всему числителю x + 1. Верно: x + 2 − (x + 1) = 1, "
             "ответ [[1|x² − 4]]."),
]

# ------------------------------------------------------------------ заметки преподавателю

NOTES = [
    ("Порядок.", "Блоки идут от простого к сложному и опираются друг на друга: блок 2 (сокращение) нужен "
     "для блоков 3–5, блок 1 (степени) — для блока 4, № 3, 4, 9 и блока 5, № 5. Если на неделю это много, "
     "минимум — по 3–4 первых задачи каждого блока и блок 5, № 1–4: около 25 задач."),
    ("Квадратные уравнения не нужны.", "Все знаменатели раскладываются вынесением общего множителя и "
     "тремя формулами 7 класса; трёхчленов вида x² + 5x + 6 в листе нет."),
    ("Где ждать ошибок.", "Блок 1, № 2 и 3: (x³)⁴ = x⁷ и (2a³)⁴ = 2a¹². Блок 2, № 4 и блок 3, № 9 — "
     "знак у b − a. Блок 3, № 5 и 8 — скобки у вычитаемой дроби. Блок 4, № 2, 4, 6, 7 — при делении "
     "переворачивают не ту дробь."),
    ("Другая запись ответа засчитывается:", "−[[1|x − 1]] = [[1|1 − x]], 2x(x − 5) = 2x² − 10x; "
     "скобки в знаменателе ответа раскрывать не обязательно."),
    ("Проверка подстановкой.", "Просите делать её хотя бы в блоках 3 и 5. Брать 2, 3 или «некруглое» "
     "число: 0 и 1 часто маскируют ошибку."),
    ("«Найди ошибку»", "лучше разобрать вместе, если ученик не нашёл ошибку сам: каждая из пяти — самая "
     "частая в своей теме."),
]

# ------------------------------------------------------------------ проверка


def check():
    n = 0
    for b in BLOCKS:
        for i, t in enumerate(b["tasks"], 1):
            tag = f"блок {b['n']}, № {i}"
            assert equal(t["c"], t["a"]), f"{tag}: ответ не совпал"
            for alt in t.get("alt", []):
                assert equal(t["a"], alt), f"{tag}: другая запись ответа не совпала"
            if "at" in t:
                v = value(t["c"], t["at"])
                t["at_value"] = v
                assert v == value(t["a"], t["at"])
            n += 1
    for key, r in RAZBORY.items():
        first = r["steps"][0][0][0]
        for exprs, _ in r["steps"]:
            for e in exprs:
                assert equal(first, e), f"разбор {key}: {e!r} не равно {first!r}"
    for a, b in RAZBOR_LINKS + THEORY:
        assert equal(a, b), f"{a!r} ≠ {b!r}"
    for a, b in THEORY_FALSE:
        assert not equal(a, b), f"ловушка {a!r} = {b!r} оказалась верной"
    for e, env, v in THEORY_VALUES:
        assert value(e, {k: F(x) for k, x in env.items()}) == v, f"{e!r} при {env} ≠ {v}"
    for k, o in enumerate(OSHIBKI, 1):
        ch = o["chain"]
        for j in range(len(ch) - 1):
            same = equal(ch[j], ch[j + 1])
            assert same == (j != o["bad"]), f"ошибка {k}: переход {j} {'верен' if same else 'неверен'}"
        assert equal(ch[0], o["fix"]), f"ошибка {k}: исправленный ответ неверен"
        assert not equal(ch[0], ch[-1]), f"ошибка {k}: неверный ответ случайно верен"
    print(f"проверено: {n} задач, {len(RAZBORY)} разборов, {len(THEORY) + len(THEORY_FALSE)} формул теории, "
          f"{len(OSHIBKI)} неверных решений — всё сходится")
    return n


# ------------------------------------------------------------------ HTML


def ln(exprs, comment, first):
    body = " = ".join(html(e) for e in exprs)
    if not first:
        body = "= " + body
    c = f'<span class="c">{html(comment)}</span>' if comment else ""
    return f'<div class="ln">{body}{c}</div>'


def razbor_html(key):
    lines = [ln(e, c, i == 0) for i, (e, c) in enumerate(RAZBORY[key]["steps"])]
    return '<div class="calc">\n' + "\n".join(lines) + "\n</div>"


def block_html(b):
    items = []
    for i, t in enumerate(b["tasks"], 1):
        star = "★" if t.get("star") else ""
        extra = ""
        if t.get("prove"):
            extra = '<span class="q">Докажите, что при всех допустимых x значение одно и то же, и найдите его:</span>'
        if t.get("at"):
            extra = f'<span class="q">Упростите и найдите значение при {t["at_text"]}:</span>'
        cls = ' class="wide"' if extra or len(t["c"]) > 52 else ""
        items.append(f'<li{cls}><span class="no">{i}.{star}</span>{extra}<span class="ex">{html(t["c"])}</span></li>')
    ans = []
    notes = []
    for i, t in enumerate(b["tasks"], 1):
        a = html(t["a"])
        if t.get("alt"):
            a += " = " + " = ".join(html(x) for x in t["alt"])
        if "at" in t:
            a += f"; при {t['at_text']} получается {fnum(t['at_value'])}"
        ans.append(f'<li><span class="no">{i}.</span><span class="ex">{a}</span></li>')
        if t.get("hint"):
            notes.append(f"<li><strong>№ {i}:</strong> {html(t['hint'])}</li>")
    note_html = f'<ul class="hints">{"".join(notes)}</ul>' if notes else ""
    return (f'<h3 id="{b["id"]}"><span class="lvl">Блок {b["n"]}</span>{b["title"]}</h3>\n'
            f'<p>{b["lead"]}</p>\n<ol class="drill">\n' + "\n".join(items) + "\n</ol>\n"
            f'<!--T--><details><summary>Ответ · блок {b["n"]}</summary>\n<ol class="anslist">'
            + "".join(ans) + f"</ol>{note_html}</details><!--/T-->")


def oshibki_html():
    out = []
    for k, o in enumerate(OSHIBKI, 1):
        chain = " = ".join(html(e) for e in o["chain"])
        out.append(
            f'<div class="wrong"><span class="tag">Решение {k} <span class="stamp">неверно</span></span>\n'
            f'<div class="calc"><div class="ln">{chain}</div></div>\n'
            f'<!--T--><details><summary>Где ошибка</summary><p>{html(o["why"])}</p>'
            f'<p class="ans"><b>Верный ответ:</b> {html(o["fix"])}</p></details><!--/T-->\n</div>')
    return "\n".join(out)


def build_page(total):
    src = (HERE / "src.html").read_text(encoding="utf-8")
    stars = sum(1 for b in BLOCKS for t in b["tasks"] if t.get("star"))
    repl = {"@@N@@": str(total), "@@NSTAR@@": str(stars), "@@NOBL@@": str(total - stars),
            "@@CSS@@": (HERE.parent / "seriya.css").read_text(encoding="utf-8").strip(),
            "@@OSHIBKI@@": oshibki_html(),
            "@@NOTES@@": "\n".join(f"<li><strong>{b}</strong> {html(t)}</li>" for b, t in NOTES)}
    for key in RAZBORY:
        repl[f"@@R:{key}@@"] = razbor_html(key)
    for b in BLOCKS:
        repl[f"@@B:{b['id']}@@"] = block_html(b)
    for k, v in repl.items():
        assert k in src, f"в src.html нет {k}"
        src = src.replace(k, v)
    assert "@@" not in src
    return html_doc(src)


# ------------------------------------------------------------------ Markdown


def build_md(total):
    z = [f"# {TITLE} — задачи для ученика", "",
         f"{total} задач. Задачи со ★ — по желанию. Теория и разборы — в PDF и на странице занятия.",
         "Дробь в строчку: `(x + 1)/(x − 2)` — это дробь с числителем x + 1 и знаменателем x − 2.", ""]
    o = [f"# {TITLE} — ответы", "", f"Страница занятия с теорией и разборами: <{ARTIFACT}>", "",
         "Все ответы сверены программой: `python3 build.py --check` сравнивает "
         "условие и ответ в 80 случайных рациональных точках точной арифметикой (`fractions.Fraction`).", ""]
    for b in BLOCKS:
        z += [f"## Блок {b['n']}. {b['title']}", "", b["lead"], "", "```"]
        o += [f"## Блок {b['n']}. {b['title']}", ""]
        for i, t in enumerate(b["tasks"], 1):
            pre = ""
            if t.get("prove"):
                pre = "докажите, что значение не зависит от x: "
            if t.get("at"):
                pre = f"упростите и найдите значение при {t['at_text']}: "
            z.append(f"{i:>2}.{'★' if t.get('star') else ' '} {pre}{plain(t['c'])}")
            a = plain(t["a"])
            if t.get("alt"):
                a += " = " + " = ".join(plain(x) for x in t["alt"])
            if "at" in t:
                a += f"; при {t['at_text']} значение {fnum(t['at_value'])}"
            hint = f" — {plain(t['hint'])}" if t.get("hint") else ""
            o.append(f"{i}) `{a}`{hint}  ")
        z += ["```", ""]
        o += [""]
    z += ["## Найди ошибку", "", "В каждом решении есть ошибка. Найдите неверный переход, объясните и решите правильно.", ""]
    o += ["## Найди ошибку", ""]
    for k, e in enumerate(OSHIBKI, 1):
        chain = " = ".join(plain(x) for x in e["chain"])
        z.append(f"{k}. `{chain}`  ")
        why = plain(e["why"])
        o.append(f"{k}. `{chain}` — {why} **Верно:** `{plain(e['fix'])}`  ")
    (HERE / "ZADACHI.md").write_text("\n".join(z) + "\n", encoding="utf-8")
    o += ["", "## Заметки преподавателю", ""] + [f"- **{b}** {plain(t)}" for b, t in NOTES]
    (HERE / "OTVETY.md").write_text("\n".join(o) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ сборка


def main():
    total = check()
    if "--check" in sys.argv:
        return
    page = build_page(total)
    teacher = variant(page, "teacher")
    student = variant(page, "student")
    (HERE / "index.html").write_text(teacher, encoding="utf-8")
    build_md(total)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "_print"
    out.mkdir(exist_ok=True)
    for who, body, name in (("teacher", teacher, f"{TITLE} — ответы преподавателя.pdf"),
                            ("student", student, f"{TITLE} — ДЗ ученика.pdf")):
        p = out / f"print-{who}.html"
        p.write_text(printable(body, TITLE), encoding="utf-8")
        pdf(p, HERE / name)
        if "--shot" in sys.argv:
            screenshot(p, out / f"shot-{who}.png")
    print("собрано:", ", ".join(x.name for x in sorted(HERE.glob("*.pdf"))))


if __name__ == "__main__":
    main()
