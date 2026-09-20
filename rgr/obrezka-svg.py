# -*- coding: utf-8 -*-
"""Обрезка viewBox у сгенерированных схем по фактическому содержимому.

Зачем. viewBox задаётся при рисовании «на глаз», и снизу почти всегда
остаётся пустое поле. На экране это незаметно, а в PDF рисунок из-за
этого выходит мельче, и под ним зияет пустота.

Как. Настоящие габариты содержимого знает только движок, который
раскладывает текст, поэтому схемы открываются в Chromium, для каждой
берётся svg.getBBox(), и viewBox переписывается по нему с полями.

Запуск:  python3 obrezka-svg.py <папка> [ещё папки...]
"""
import glob
import html
import os
import re
import subprocess
import sys
import tempfile

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
PAD = 14            # поле вокруг содержимого, единицы viewBox


def styles(folder):
    """Стили схем: из _css.html или из блока в shablon.html."""
    css_file = os.path.join(folder, "_css.html")
    if os.path.exists(css_file):
        return open(css_file, encoding="utf-8").read()
    tpl = open(os.path.join(folder, "shablon.html"), encoding="utf-8").read()
    return tpl[tpl.index("<style>"):tpl.index("</style>") + 8]


def measure(folder, files):
    page = ('<!doctype html><html><head><meta charset="utf-8"></head><body>'
            + styles(folder) + '<style>svg{width:600px;display:block}</style>')
    for f in files:
        page += f'<div data-f="{os.path.basename(f)}">' + \
                open(f, encoding="utf-8").read() + "</div>\n"
    page += '''<script>
window.addEventListener('load', function(){
  var out = [];
  document.querySelectorAll('div[data-f]').forEach(function(d){
    var b = d.querySelector('svg').getBBox();
    out.push(d.dataset.f + ' ' + [b.x, b.y, b.width, b.height].join(' '));
  });
  document.body.innerHTML = '<pre id="rep">' + out.join('\\n') + '</pre>';
});
</script></body></html>'''
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(page)
        tmp = fh.name
    dom = subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         "--window-size=900,900", "--virtual-time-budget=6000",
         "--dump-dom", "file://" + tmp],
        capture_output=True, text=True).stdout
    os.unlink(tmp)
    m = re.search(r'<pre id="rep">(.*?)</pre>', dom, re.S)
    if not m:
        raise RuntimeError("не удалось измерить схемы — Chromium не отдал отчёт")
    out = {}
    for line in html.unescape(m.group(1)).strip().split("\n"):
        parts = line.rsplit(" ", 4)
        out[parts[0]] = [float(v) for v in parts[1:]]
    return out


def main(folders):
    for folder in folders:
        files = sorted(glob.glob(os.path.join(folder, "*.svg")))
        if not files:
            continue
        box = measure(folder, files)
        print(f"--- {folder} ---")
        for f in files:
            x, y, w, h = box[os.path.basename(f)]
            nx, ny = max(0.0, x - PAD), max(0.0, y - PAD)
            nw, nh = w + 2 * PAD, h + 2 * PAD
            s = open(f, encoding="utf-8").read()
            old = re.search(r'viewBox="([^"]+)"', s).group(1)
            new = f"{nx:.0f} {ny:.0f} {nw:.0f} {nh:.0f}"
            s = s.replace(f'viewBox="{old}"', f'viewBox="{new}"', 1)
            open(f, "w", encoding="utf-8").write(s)
            print(f"  {os.path.basename(f):24s} {old:>16s}  ->  {new}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["."])
