"""Общие инструменты сборки листов: разметка дробей, проверка ответов, версии и PDF.

Разметка в условиях и выкладках:
    [[числитель|знаменатель]]   дробь (вложенность допускается)
    ²³⁴…                        показатель степени, в HTML превращается в <sup>
    {a+2}                       дополнительный множитель «уголком», в проверке не участвует
    ~a~                         зачёркнутое при сокращении, в проверке остаётся

Версии одной страницы:
    <!--T-->…<!--/T-->          только у преподавателя
    <!--S … S-->                только у ученика (у преподавателя закомментировано)
"""
import random
import re
import subprocess
from fractions import Fraction as F
from pathlib import Path

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

SUPCH = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUP = str.maketrans(SUPCH, "0123456789")
FRAC_RE = re.compile(r"\[\[([^\[\]|]*)\|([^\[\]]*)\]\]")


# ---------------------------------------------------------------- разметка → HTML

def html(m):
    """Разметку выражения — в HTML с настоящими дробями."""
    s = m
    while True:
        s2 = FRAC_RE.sub(lambda g: f'<span class="frac"><span class="nu">{g[1]}</span>'
                                   f'<span class="de">{g[2]}</span></span>', s)
        if s2 == s:
            break
        s = s2
    s = re.sub(r"\{([^{}]*)\}", r'<span class="dm">\1</span>', s)
    s = re.sub(r"~([^~]*)~", r'<span class="bad">\1</span>', s)
    s = re.sub(f"[{SUPCH}]+", lambda g: f"<sup>{g[0].translate(SUP)}</sup>", s)
    return s


def html_doc(src):
    """Во всём документе: только дроби и показатели (фигурные скобки CSS не трогаем)."""
    def one(text):
        s = text
        while True:
            s2 = FRAC_RE.sub(lambda g: f'<span class="frac"><span class="nu">{g[1]}</span>'
                                       f'<span class="de">{g[2]}</span></span>', s)
            if s2 == s:
                return s
            s = s2
    out = one(src)
    # показатели — только вне <style>
    parts = re.split(r"(<style>.*?</style>)", out, flags=re.S)
    for i, p in enumerate(parts):
        if not p.startswith("<style>"):
            parts[i] = re.sub(f"[{SUPCH}]+", lambda g: f"<sup>{g[0].translate(SUP)}</sup>", p)
    return "".join(parts)


# ---------------------------------------------------------------- разметка → Python

def to_py(m):
    """Разметку выражения — в код Python на Fraction. Возвращает (код, множество букв)."""
    s = re.sub(r"\{[^{}]*\}", "", m).replace("~", "")
    s = re.sub(r"<[^>]+>", "", s)
    while True:
        s2 = FRAC_RE.sub(lambda g: f"(({g[1]})/({g[2]}))", s)
        if s2 == s:
            break
        s = s2
    for a, b in (("−", "-"), ("·", "*"), (":", "/"), (" ", ""), (" ", ""),
                 (" ", ""), (" ", "")):
        s = s.replace(a, b)
    toks, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch in SUPCH:
            j = i
            while j < len(s) and s[j] in SUPCH:
                j += 1
            toks.append(("pow", s[i:j].translate(SUP)))
            i = j
        elif ch in "0123456789":
            j = i
            while j < len(s) and s[j] in "0123456789,.":
                j += 1
            toks.append(("num", s[i:j].replace(",", ".")))
            i = j
        elif "a" <= ch <= "z":
            toks.append(("var", ch))
            i += 1
        elif ch in "()":
            toks.append((ch, ch))
            i += 1
        elif ch in "+-*/":
            toks.append(("op", ch))
            i += 1
        else:
            raise ValueError(f"непонятный символ {ch!r} в {m!r}")
    out, prev, names = [], None, set()
    for t in toks:
        if prev and prev[0] in ("num", "var", ")", "pow") and t[0] in ("num", "var", "("):
            out.append("*")
        if t[0] == "num":
            out.append(f'F("{t[1]}")')
        elif t[0] == "pow":
            out.append(f"**{t[1]}")
        else:
            out.append(t[1])
            if t[0] == "var":
                names.add(t[1])
        prev = t
    return "".join(out), names


def value(m, env):
    code, _ = to_py(m)
    return eval(code, {"F": F, "__builtins__": {}}, dict(env))


def equal(m1, m2, trials=80, seed=1):
    """Равны ли два выражения при всех допустимых значениях букв (проверка в случайных
    рациональных точках, точная арифметика). Без букв — точное сравнение чисел."""
    _, n1 = to_py(m1)
    _, n2 = to_py(m2)
    names = sorted(n1 | n2)
    if not names:
        return value(m1, {}) == value(m2, {})
    rnd = random.Random(seed)
    ok = 0
    for _ in range(trials * 4):
        env = {v: F(rnd.choice([-1, 1]) * rnd.randint(1, 40), rnd.randint(1, 9)) for v in names}
        try:
            a, b = value(m1, env), value(m2, env)
        except ZeroDivisionError:
            continue
        if a != b:
            return False
        ok += 1
        if ok >= trials:
            return True
    raise RuntimeError(f"мало допустимых точек для {m1!r}")


# ---------------------------------------------------------------- числа по-русски

def fnum(x, group=True):
    """84000 → «84 000», 0.5 → «0,5». Только конечные десятичные дроби."""
    x = F(x)
    sign = "−" if x < 0 else ""
    x = abs(x)
    for k in range(0, 9):
        if (x * 10**k).denominator == 1:
            break
    else:
        raise ValueError(f"{x} не записывается конечной десятичной дробью")
    n = int(x * 10**k)
    ip, fp = divmod(n, 10**k)
    s = str(ip)
    if group and ip >= 10000:
        s = f"{ip:,}".replace(",", " ")
    if k:
        s += "," + str(fp).rjust(k, "0").rstrip("0")
    return sign + s


def fround(x, digits):
    """Округление Fraction до digits знаков после запятой (половину — вверх)."""
    q = F(1, 10**digits)
    return (F(x) / q + F(1, 2)).__floor__() * q


def plain(m):
    """Разметку — в строчную запись для Markdown: [[a|b]] → (a)/(b), теги убираются."""
    s = re.sub(r"\{[^{}]*\}", "", m).replace("~", "")
    s = re.sub(r"<sub>(.*?)</sub>", r"(\1)", s)
    s = re.sub(r"<[^>]+>", "", s)

    def fr(g):
        # числитель без пробелов и знаков оставляем как есть, знаменатель — только число или одну букву
        nu, de = g[1].strip(), g[2].strip()
        nu = nu if re.fullmatch(r"[^ +\-−·:/]+", nu) else f"({nu})"
        de = de if re.fullmatch(r"[\d,\u202f]+|[a-zA-Zа-яА-Я][²³⁴⁵⁶⁷⁸⁹⁰¹]*", de) else f"({de})"
        return f"{nu}/{de}"
    while True:
        s2 = FRAC_RE.sub(fr, s)
        if s2 == s:
            return s
        s = s2


def fsci(x, keep_zero=False):
    """44000000 → «4,4·10⁷»; 50000000 → «5·10⁷» (или «5,0·10⁷» при keep_zero)."""
    x = F(x)
    k = 0
    while x >= 10 * 10**k:
        k += 1
    mant = x / 10**k
    s = fnum(mant)
    if keep_zero and "," not in s:
        s += ",0"
    return f"{s}·10{str(k).translate(str.maketrans('0123456789', SUPCH))}"


# ---------------------------------------------------------------- версии и печать

def variant(src, who):
    if who == "teacher":
        s = re.sub(r"<!--S.*?S-->", "", src, flags=re.S)
        s = s.replace("<!--T-->", "").replace("<!--/T-->", "")
    else:
        s = re.sub(r"<!--T-->.*?<!--/T-->", "", src, flags=re.S)
        s = re.sub(r"<!--S(.*?)S-->", r"\1", s, flags=re.S)
    assert "<!--T" not in s and "<!--S" not in s and "S-->" not in s
    return s


def _cut_block(css, head):
    """Вырезать блок CSS, начинающийся с head, с учётом вложенных скобок."""
    while True:
        i = css.find(head)
        if i < 0:
            return css
        j = css.index("{", i)
        depth = 0
        for k in range(j, len(css)):
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
                if depth == 0:
                    css = css[:i] + css[k + 1:]
                    break


PRINT_CSS = """
@page{margin:14mm 12mm}
@media print{
  body{font-size:14.5px;padding-inline:0;padding-block:0}
  .wrap{max-width:none}
  .masthead{padding-block:0 12px;margin-bottom:18px}
  .toc{display:none}
  .card,.callout,.task,.wrong,.calc,.eq,.fig,tr,.drill li,.plist>li,.dano,.ans,details,.grid2>.card{break-inside:avoid}
  h2,h3,h4,.blockhead{break-after:avoid}
  section.block{margin-block:0 26px}
  a{color:inherit;text-decoration:none}
  summary::before{content:""}
}
"""


def printable(page, title):
    s = re.sub(r'<link[^>]*fonts\.(googleapis|gstatic)\.com[^>]*>\n?', "", page)
    s = _cut_block(s, "@media (prefers-color-scheme:dark)")
    s = _cut_block(s, ':root[data-theme="dark"]')
    s = s.replace("<details>", "<details open>")
    i = s.rindex("</style>")
    s = s[:i] + PRINT_CSS + s[i:]
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"</head><body>\n{s}\n</body></html>")


def pdf(html_path, pdf_path):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    "--virtual-time-budget=8000", f"--print-to-pdf={pdf_path}",
                    f"file://{Path(html_path).resolve()}"],
                   check=True, capture_output=True)


def screenshot(html_path, png_path, width=900, height=16000):
    src = Path(html_path).read_text(encoding="utf-8").replace("@media print{", "@media all{")
    tmp = Path(png_path).with_suffix(".shot.html")
    tmp.write_text(src, encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    f"--window-size={width},{height}", "--virtual-time-budget=4000",
                    f"--screenshot={png_path}", f"file://{tmp.resolve()}"],
                   check=True, capture_output=True)
