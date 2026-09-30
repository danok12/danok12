# -*- coding: utf-8 -*-
"""Сборка печатной версии: index.html -> print.html -> PDF (Chromium).

Правила подготовки печатной копии — из CLAUDE.md:
убрать Google Fonts (сети нет), вырезать тёмную тему, раскрыть <details>,
добавить print-CSS с запретом разрывов внутри карточек и рисунков.
"""
import re
import subprocess
import os

TPL, SRC, DST = "shablon.html", "index.html", "print.html"
OUT = "Тема 9 — НДС в окрестности точки тела.pdf"

# Единый масштаб черчения на весь документ.
# Без него каждая схема растягивалась на всю ширину полосы, и подписи на
# ней выходили крупнее основного текста, а линии — грубее. Теперь ширина
# задаётся не полосой, а содержимым: одна единица viewBox = MM_NA_ED мм,
# поэтому шрифт .lbl (17 ед.) печатается около 9 пт на всех схемах сразу.
MM_NA_ED = 0.187
MAX_MM = 175.0      # ширина полосы набора; шире — только тогда ужимать


def po_masshtabu(svg):
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    mm = min(vb[2] * MM_NA_ED, MAX_MM)
    return svg.replace("<svg ", f'<svg style="width:{mm:.2f}mm" ', 1)


# 0. вклеить схемы в шаблон -> index.html
h = open(TPL, encoding="utf-8").read()
for n in range(1, 8):
    h = h.replace(f"__FIG_{n}__",
                  po_masshtabu(open(f"fig-{n}.svg", encoding="utf-8").read().strip()))
assert "__FIG" not in h, "не все схемы вклеены"
open(SRC, "w", encoding="utf-8").write(h)

# 1. Google Fonts -> локальные фолбэки
h = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', "", h)

# 2. вырезать тёмную тему
h = re.sub(r'@media \(prefers-color-scheme:dark\)\{.*?\n\}\n', "", h, flags=re.S)
h = re.sub(r':root\[data-theme="dark"\]\{.*?\n\}\n', "", h, flags=re.S)

# 3. раскрыть свёрнутые блоки (в этом документе их нет, но правило общее)
h = h.replace("<details>", "<details open>")

PRINT_CSS = """
<style>
@page{size:A4; margin:18mm 16mm 16mm}
body{background:#fff; color:#000; font-size:11.5pt; line-height:1.45;
  hyphens:auto; -webkit-hyphens:auto}
.wrap{max-width:none; padding-block:0; padding-inline:0}
h1{font-size:14pt; margin-bottom:10pt}
h2{font-size:13pt; margin:18pt 0 8pt}
h3{font-size:11.5pt; margin:13pt 0 5pt}
h4{margin:9pt 0 4pt}
h1,h2,h3,h4,caption{break-after:avoid}
p,.f,.res,.rem,.mx,figure,.tw,table,tr,.matrix,footer{break-inside:avoid}
.f{line-height:1.6; margin-bottom:7pt}
table{font-size:10.5pt}
figure{margin:9pt 0 11pt}
figure svg{height:auto; max-width:100%}
figcaption{font-size:10.5pt}
</style>
"""
h = h.replace("</style>", "</style>" + PRINT_CSS, 1)
open(DST, "w", encoding="utf-8").write(
    '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "</head><body>" + h + "</body></html>")

CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([CH, "--headless", "--disable-gpu", "--no-sandbox",
                "--no-pdf-header-footer", "--virtual-time-budget=8000",
                f"--print-to-pdf={OUT}", "file://" + os.path.abspath(DST)],
               check=True)
print("собрано:", OUT, os.path.getsize(OUT), "байт")

# 4. отдельный лист — только круг Мора (рис. 7) в натуральном масштабе
OUT7 = "Рис. 7 — круг Мора.pdf"
tpl = open(TPL, encoding="utf-8").read()
fig7 = tpl[tpl.index("<figure>__FIG_7__"):tpl.index("</figure>", tpl.index("<figure>__FIG_7__")) + 9]
fig7 = fig7.replace("__FIG_7__", po_masshtabu(open("fig-7.svg", encoding="utf-8").read().strip()))
css = tpl[tpl.index("<style>"):tpl.index("</style>") + 8]
css = re.sub(r'@media \(prefers-color-scheme:dark\)\{.*?\n\}\n', "", css, flags=re.S)
css = re.sub(r':root\[data-theme="dark"\]\{.*?\n\}\n', "", css, flags=re.S)
list7 = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">' + css + PRINT_CSS +
         '</head><body><div class="wrap">' + fig7 + '</div></body></html>')
open("print-7.html", "w", encoding="utf-8").write(list7)
subprocess.run([CH, "--headless", "--disable-gpu", "--no-sandbox",
                "--no-pdf-header-footer", "--virtual-time-budget=8000",
                f"--print-to-pdf={OUT7}", "file://" + os.path.abspath("print-7.html")],
               check=True)
os.remove("print-7.html")
print("собрано:", OUT7, os.path.getsize(OUT7), "байт")
