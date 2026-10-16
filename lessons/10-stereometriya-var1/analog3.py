"""Аналог задачи 3 варианта I: своя задача того же типа, два PDF — ученику и преподавателю.

    python3 analog3.py          проверить ответ, собрать оба PDF
    python3 analog3.py --check  только проверка

Отличия от задачи 3: диагональ BD вместо AC, треугольник при вершине A, нужная сторона AB
дана через равную ей CD (как в задаче 3 сторона AD — через BC). Ответ BD = 21 проверяется
точной арифметикой на явных координатах, по ним же строится чертёж.
"""
import subprocess
import sys

from build import CHROME, CSS, F, Fig, HERE, cross, dot, fonts, inside, m, on_line, vadd, vsub

PDF_STUDENT = "Аналог задачи 3 — ученику.pdf"
PDF_TEACHER = "Аналог задачи 3 — с решением.pdf"

# параллелограмм ABCD: AB = CD = 14, BD = 21; A впереди, BD — фронтальная прямая
P = {"A": (F(42, 5), F(-56, 5), F(0)), "B": (F(0), F(0), F(0)), "D": (F(21), F(0), F(0))}
P["C"] = vadd(P["B"], vsub(P["D"], P["A"]))
AK, CD, KM = 4, 14, 6


def dist2(p, q):
    return dot(vsub(p, q), vsub(p, q))


def check():
    A, B, C, D = P["A"], P["B"], P["C"], P["D"]
    assert vadd(A, vsub(C, B)) == D                         # ABCD — параллелограмм
    assert dist2(C, D) == CD ** 2 and dist2(A, B) == CD ** 2
    K = on_line(F(AK, CD), A, B)                            # K ∈ AB, AK = 4
    assert dist2(A, K) == AK ** 2
    n = cross(vsub(D, B), (0, 0, 1))                        # β ∥ BD, вертикальная, через K
    assert dot(n, vsub(D, B)) == 0 and dot(n, vsub(B, K)) != 0
    s = dot(n, vsub(K, A)) / dot(n, vsub(D, A))
    M = on_line(s, A, D)                                    # M = β ∩ AD
    assert 0 < s < 1                                        # M на стороне AD
    assert cross(vsub(M, K), vsub(D, B)) == (0, 0, 0)       # KM ∥ BD
    assert dist2(K, M) == KM ** 2                           # KM = 6
    k = F(AK, CD)
    bd = KM / k
    assert bd == 21 and dist2(B, D) == bd ** 2              # BD = KM / k = 21
    wrong = KM / F(AK, CD - AK)                             # ловушка AK : KB = 4 : 10
    assert wrong == 15 and wrong != bd
    P.update(K=K, M=M)
    print(f"✓ аналог задачи 3: KM ∥ BD, k = {k}, BD = {bd}; ловушка AK:KB даёт {wrong}")


def figure(width=420):
    A, B, C, D, K, M = (P[x] for x in "ABCDKM")
    d = vsub(M, K)
    Q1, Q2 = vadd(K, d, F(-2, 5)), vadd(M, d, F(2, 5))
    up = (0, 0, F(9, 2))
    f = Fig(s=20, kx=0.4, ky=0.45)
    wall = [Q1, Q2, vadd(Q2, up), vadd(Q1, up)]
    f.poly([A, B, D], "fb")
    f.poly([A, K, M], "fa")
    f.poly(wall, "pl")
    w2 = [f.p(q) for q in wall]
    behind = lambda q: q[1] > K[1] and inside(f.p(q), w2)
    for a, b in [(A, B), (B, C), (C, D), (D, A)]:
        f.seg_vis(a, b, behind, "e", "eb")
    f.seg_vis(B, D, behind, "mid", "midb")
    f.seg(Q1, Q2, "lnr"); f.seg(K, M, "hl")
    f.dot(K); f.dot(M)
    for q, t, dx, dy in [(A, "A", 0, 18), (B, "B", -12, 5), (C, "C", 0, -8), (D, "D", 12, 5),
                         (K, "K", -13, 4), (M, "M", 13, 4)]:
        f.name(q, t, dx, dy)
    f.name(vadd(Q2, up), "β", -12, 20, "lb al")
    f.name(vadd(A, vsub(K, A), F(1, 2)), "4", -12, 8, "lb num")
    f.name(vadd(K, d, F(1, 2)), "6", 0, -6, "lb num")
    f.name(vadd(C, vsub(D, C), F(1, 2)), "14", 13, -2, "lb num")
    return f.svg(width, label="параллелограмм ABCD и плоскость β")


COND = f"""
  <p><strong>Дано:</strong> {m("ABCD")} — параллелограмм, {m("BD")} — диагональ; {m("K ∈ AB")}, {m("AK = 4")};
     плоскость {m("β ∥ BD")}, {m("K ∈ β")}, {m("β ∩ AD = M")}.</p>
  <p><strong>Доказать:</strong> {m("ΔAKM ∼ ΔABD")}.</p>
  <p><strong>Найти:</strong> {m("BD")}, если {m("CD = 14")}, {m("KM = 6")}.</p>"""


def head(title, sub):
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{fonts()}{CSS}
.cmp td{{font-family:var(--body);white-space:normal}}
.cmp td:first-child{{color:var(--ink-soft)}}
.space{{border:1px dashed var(--rule);border-radius:2px;height:150mm;margin-top:12px;display:flex;align-items:flex-start;justify-content:flex-end;padding:6px 10px;font-size:11px;color:var(--muted)}}
</style></head>
<body><div class="wrap">
<header class="masthead">
  <p class="eyebrow">Геометрия · 10 класс · к варианту I</p>
  <h1>{title}</h1>
  <p class="standfirst">{sub}</p>
</header>
"""


def page_student():
    return head("Аналог задачи 3", "Плоскость, параллельная диагонали параллелограмма") + f"""
<section class="task">
  <div class="head"><span class="badge">задача</span><h2>Плоскость, параллельная диагонали</h2></div>
  <div class="cond solo"><div>{COND}
  <p>Сделайте рисунок. Каждый шаг обоснуйте: на какую аксиому, теорему или свойство он опирается.</p></div></div>
  <div class="space">место для рисунка и решения</div>
</section>
</div></body></html>
"""


def page_teacher():
    return head("Аналог задачи 3: решение", "Та же конструкция, что в задаче 3, но другая диагональ, другая вершина и свои числа. Ответ: BD = 21.") + f"""
<section class="task">
  <div class="head"><span class="badge">задача</span><h2>Плоскость, параллельная диагонали</h2></div>
  <div class="cond">
    <div>{COND}</div>
    <figure>{figure(380)}<figcaption>Плоскость β пересекает плоскость параллелограмма по прямой KM</figcaption></figure>
  </div>

  <h3>Чем отличается от задачи 3</h3>
  <table class="cmp">
    <tr><th></th><th>Задача 3</th><th>Аналог</th></tr>
    <tr><td>диагональ</td><td>{m("AC")}</td><td>{m("BD")}</td></tr>
    <tr><td>подобные треугольники</td><td>{m("ΔC1DA1 ∼ ΔCDA")}, вершина D</td><td>{m("ΔAKM ∼ ΔABD")}, вершина A</td></tr>
    <tr><td>сторона через равную</td><td>{m("AD = BC = 10")}</td><td>{m("AB = CD = 14")}</td></tr>
    <tr><td>коэффициент</td><td>{m("k = 4/10 = 2/5")}</td><td>{m("k = 4/14 = 2/7")}</td></tr>
    <tr><td>ответ</td><td>{m("AC = 15")}</td><td>{m("BD = 21")}</td></tr>
  </table>

  <h3>Решение</h3>
  <ol class="steps">
    <li><strong>Линия пересечения.</strong> {m("K ∈ β")} и {m("K ∈ AB ⊂ (ABC)")}; {m("M ∈ β")} и {m("M ∈ AD ⊂ (ABC)")}. Плоскости β и {m("(ABC)")} различны: BD лежит в {m("(ABC)")}, а с β у BD нет общих точек. Две общие точки ⇒ {m("β ∩ (ABC) = KM")} (аксиомы 3 и 2).</li>
    <li><strong>{m("KM ∥ BD")}.</strong> Плоскость {m("(ABC)")} проходит через прямую BD, параллельную β, и пересекает β по KM. Линия пересечения параллельна этой прямой: {m("KM ∥ BD")}.</li>
    <li><strong>Подобие.</strong> В треугольниках AKM и ABD угол A общий; {m("∠AKM = ∠ABD")} как соответственные при {m("KM ∥ BD")} и секущей AB. По двум углам {m("ΔAKM ∼ ΔABD")}, соответствие {m("A↔A, K↔B, M↔D")}. ∎</li>
    <li><strong>Вычисление.</strong> {m("AB = CD = 14")} (противоположные стороны параллелограмма). Коэффициент подобия {m("k = AK / AB = 4/14 = 2/7")}. Сходственные стороны: {m("KM / BD = k")}, откуда {m("BD = KM / k = 6 · 14/4 = 21")}.</li>
  </ol>

  <div class="answer"><p class="t">Ответ</p><p>{m("ΔAKM ∼ ΔABD")} (по двум углам, так как {m("KM ∥ BD")}); {m("BD = 21")}.</p></div>

  <div class="warn"><p class="t">На что смотреть при проверке</p><ul>
    <li>{m("KM ∥ BD")} должно быть доказано через {m("BD ∥ β")}, а не «видно по рисунку». Это главный шаг.</li>
    <li>Отношение {m("AK : KB = 4 : 10")} вместо {m("AK : AB = 4 : 14")} даёт неверное {m("BD = 15")}.</li>
    <li>CD подставлено как сторона треугольника ABD без слов «{m("AB = CD")} как противоположные стороны».</li>
    <li>Треугольник при вершине D, как в задаче 3, вместо треугольника при A: признак, что задача 3 решена по образцу, а не понята.</li>
  </ul></div>

  <div class="note"><p class="t">Вариант с ловушкой</p>
    <p>Если вместо {m("AK = 4")} дать {m("KB = 10")}, ответ останется {m("BD = 21")}, но ученику придётся самому найти {m("AK = AB − KB = 14 − 10 = 4")}. Этот вариант ловит ошибку с отношением {m("AK : KB")}.</p>
  </div>
</section>
</div></body></html>
"""


def render(html, name, out):
    src = HERE / name
    src.write_text(html)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    "--virtual-time-budget=8000", f"--print-to-pdf={HERE / out}", f"file://{src}"],
                   check=True, capture_output=True)
    print("→", out)


if __name__ == "__main__":
    check()
    if "--check" not in sys.argv:
        render(page_student(), "print-analog-uchenik.html", PDF_STUDENT)
        render(page_teacher(), "print-analog-prepod.html", PDF_TEACHER)
