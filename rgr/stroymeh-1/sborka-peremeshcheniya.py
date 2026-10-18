# -*- coding: utf-8 -*-
"""Сборка второго файла: все схемы и эпюры с точками K и расчёт перемещений.

shablon-peremeshcheniya.html -> peremeshcheniya.html -> print-peremeshcheniya.html -> PDF.
Правила печатной копии — те же, что в sborka-pdf.py (CLAUDE.md).
"""
import re
import subprocess
import os
import glob

TPL, SRC, DST = ("shablon-peremeshcheniya.html", "peremeshcheniya.html",
                 "print-peremeshcheniya.html")
OUT = "Строймех, задание 1 — эпюры и перемещения.pdf"
W_MM, H_MM = 136, 78


def po_meste(svg, w_mm=W_MM, h_mm=H_MM):
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    w = min(w_mm, h_mm * vb[2] / vb[3])
    return svg.replace("<svg ", f'<svg style="width:{w:.0f}mm;max-width:{w:.0f}mm" ', 1)


def rd(f):
    return open(f, encoding="utf-8").read().strip()


# подписи «что ищем в K» — по заданию к каждой схеме
PODPISI = {
    1: ("Δ<tspan class='sub'>kp</tspan> — ?", "Δ<tspan class='sub'>KP</tspan> — ?"),
    3: ("φ<tspan class='sub'>kp</tspan> — ?", "φ<tspan class='sub'>Kt</tspan> — ?"),
    4: ("<tspan class='sub'>K</tspan> — ?", "<tspan class='sub'>Kc</tspan> — ?"),
}

h = rd(TPL).replace("__CSS__", rd("_css.html"))
for i in range(1, 6):
    svg = rd(f"shema-{i}.svg")
    if i in PODPISI:
        a, b = PODPISI[i]
        assert a in svg, f"подпись схемы {i}"
        svg = svg.replace(a, b)
    h = h.replace(f"__SH_{i}__", po_meste(svg, 120, 105))
    for k in "MQN":
        key = f"__EP_{i}_{k}__"
        if key in h:
            h = h.replace(key, po_meste(rd(f"epury-{i}-{k.lower()}.svg")))
for key, f, size in (("__ED_1G__", "ed-1-g-m.svg", (136, 78)),
                     ("__SH_1E__", "shema-1-ed.svg", (100, 80)), ("__ED_1PARAB__", "ed-1-parab.svg", (150, 45)),
                     ("__ED_1PERE__", "ed-1-pere.svg", (150, 170)), ("__ED_1PEREV__", "ed-1-pere-v.svg", (140, 60)), ("__SH_3T__", "shema-3-temp.svg", (110, 95)),
                     ("__SH_4O__", "shema-4-osadka.svg", (140, 70)),
                     ("__ED_3M__", "ed-3-m.svg", (136, 78)), ("__ED_3N__", "ed-3-n.svg", (136, 78)),
                     ("__SH_3E__", "shema-3-ed.svg", (110, 100)), ("__SH_4E__", "shema-4-ed.svg", (130, 80))):
    h = h.replace(key, po_meste(rd(f), *size))
assert not re.search(r"__[A-Z_0-9]+__", h), "не всё вклеено"
open(SRC, "w", encoding="utf-8").write(h)

h = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', "", h)
h = re.sub(r'@media \(prefers-color-scheme:dark\)\{.*?\n\}\n', "", h, flags=re.S)
h = re.sub(r':root\[data-theme="dark"\]\{.*?\n\}\n', "", h, flags=re.S)
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
h1,h2,h3,h4,caption{break-after:avoid}
p,.f,.res,.rem,.mx,figure,.tw,table,tr,.matrix,footer{break-inside:avoid}
.f{line-height:1.6; margin-bottom:7pt}
table{font-size:10.5pt}
figure{margin:9pt 0 11pt}
figure svg{width:100%; max-width:136mm; height:auto}
figcaption{font-size:10.5pt}
</style>
"""
h = h.replace("</style>", "</style>" + PRINT_CSS, 1)
open(DST, "w", encoding="utf-8").write(
    '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "</head><body>" + h + "</body></html>")
CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
if not os.path.exists(CH):
    CH = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")[0]
subprocess.run([CH, "--headless", "--disable-gpu", "--no-sandbox",
                "--no-pdf-header-footer", "--virtual-time-budget=8000",
                f"--print-to-pdf={OUT}", "file://" + os.path.abspath(DST)],
               check=True, capture_output=True)
print("собрано:", OUT, os.path.getsize(OUT), "байт")
