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

# 0. вклеить схемы в шаблон -> index.html
h = open(TPL, encoding="utf-8").read()
for a, b in ((1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (2, 1), (2, 2), (2, 3)):
    h = h.replace(f"__FIG_{a}_{b}__",
                  open(f"fig-{a}-{b}.svg", encoding="utf-8").read().strip())
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
figure svg{width:100%; height:auto}
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
