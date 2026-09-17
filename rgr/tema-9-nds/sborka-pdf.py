# -*- coding: utf-8 -*-
"""Сборка печатной версии: index.html -> print.html -> PDF (Chromium).

Правила подготовки печатной копии — из CLAUDE.md:
убрать Google Fonts (сети нет), вырезать тёмную тему, раскрыть <details>,
добавить print-CSS с запретом разрывов внутри карточек и рисунков.
"""
import re
import subprocess
import os

SRC, DST = "index.html", "print.html"
OUT = "Тема 9 — задача 1 (пп. 7-8) и задача 2 (пп. 1-3).pdf"

h = open(SRC, encoding="utf-8").read()

# 1. Google Fonts -> локальные фолбэки
h = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', "", h)

# 2. вырезать тёмную тему
h = re.sub(r'@media \(prefers-color-scheme:dark\)\{.*?\n\}\n', "", h, flags=re.S)
h = re.sub(r':root\[data-theme="dark"\]\{.*?\n\}\n', "", h, flags=re.S)

# 3. раскрыть свёрнутые блоки (в этом документе их нет, но правило общее)
h = h.replace("<details>", "<details open>")

PRINT_CSS = """
<style>
@page{margin:14mm 12mm}
body{background:#fff; font-size:11.4pt; line-height:1.5}
.wrap{max-width:none; padding-block:0; padding-inline:0}
h1{font-size:22pt} h2{font-size:15pt; margin-top:22pt} h3{font-size:12.6pt; margin-top:15pt}
h2,h3,h4,caption{break-after:avoid}
h2{break-before:auto}
.f,.out,.note,.mx,figure,.sum section{break-inside:avoid}
.tw,table,tr,.matrix{break-inside:avoid}
figure svg{max-height:104mm}
.f{font-size:9.6pt; line-height:1.7}
table{font-size:9.8pt} td.mono,th.mono,.kv{font-size:9.2pt}
.sum{grid-template-columns:1fr 1fr}
footer{break-inside:avoid}
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
