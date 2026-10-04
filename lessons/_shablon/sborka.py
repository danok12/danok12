"""Сборка занятия из istochnik.html.

    python3 lessons/_shablon/sborka.py lessons/<тема> "<имя PDF без расширения>"

Разметка исходника:
  [[числитель||знаменатель]]   — дробь
  {{a+2}}                      — дополнительный множитель («уголок» над дробью)
  <!--T--> … <!--/T-->         — только для преподавателя (вырезается из версии ученику)
  <!--S … S-->                 — только для ученика (в остальных версиях это комментарий)
  <details> … </details>       — ответы (вырезаются из версии ученику, в PDF преподавателю раскрываются)

Выход:
  <scratch>/<тема>/stranica.html          — страница для Artifact
  <тема>/<имя> — преподавателю.pdf
  <тема>/<имя> — рабочий лист ученика.pdf
"""
import re, subprocess, sys, pathlib, os

ROOT = pathlib.Path(__file__).resolve().parent
CH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,500;0,600;1,500'
         '&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap">')
PRINT_CSS = """
@page{margin:14mm 12mm}
body{background:#fff;padding:0;font-size:14.5px}
.masthead{padding-top:0}
.card,.callout,.task,.wrong,.calc,.fig,.eq,.proof tr,table.plain tr,.drill li,.cond{break-inside:avoid}
h2,h3,h4,.blockhead{break-after:avoid}
.toc{display:none}
.calc,.card,.callout,.wrong,.eq{box-shadow:none}
summary::before{content:""}
"""

def macros(s):
    s = re.sub(r"\[\[(.+?)\|\|(.+?)\]\]", r'<span class="frac"><span class="nu">\1</span><span class="de">\2</span></span>', s)
    s = re.sub(r"\{\{(.+?)\}\}", r'<span class="dm">\1</span>', s)
    return s

def to_print(s):
    s = s.replace(FONTS, "")
    s = re.sub(r"@media \(prefers-color-scheme:dark\)\{\s*:root:not\(\[data-theme=\"light\"\]\)\{.*?\}\s*\}", "", s, flags=re.S)
    s = re.sub(r":root\[data-theme=\"dark\"\]\{.*?\}", "", s, flags=re.S)
    s = s.replace("<details>", "<details open>")
    s = s.replace("</style>", PRINT_CSS + "</style>", 1)
    return "<!doctype html><html lang=ru><head><meta charset=utf-8>" + s + "</body></html>"

def student(s):
    s = re.sub(r"<!--S(.*?)S-->", r"\1", s, flags=re.S)
    s = re.sub(r"<!--T-->.*?<!--/T-->", "", s, flags=re.S)
    s = re.sub(r"<details>.*?</details>", "", s, flags=re.S)
    return s

def pdf(html, out):
    tmp = pathlib.Path(out).with_suffix(".print.html")
    tmp.write_text(html, encoding="utf-8")
    subprocess.run([CH, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    "--virtual-time-budget=8000", f"--print-to-pdf={out}", f"file://{tmp}"],
                   check=True, capture_output=True)
    tmp.unlink()

def main(folder, name, scratch):
    folder = pathlib.Path(folder).resolve()
    src = (folder / "istochnik.html").read_text(encoding="utf-8")
    css = (ROOT / "serija.css").read_text(encoding="utf-8")
    page = macros(src).replace("<!--FONTS-->", FONTS).replace("/*CSS*/", css)
    out = pathlib.Path(scratch) / folder.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "stranica.html").write_text(page, encoding="utf-8")
    for n, v in (("student", student(page)), ("teacher", page)):
        (out / f"{n}.print.html").write_text(to_print(v), encoding="utf-8")
    pdf(to_print(page), folder / f"{name} — преподавателю.pdf")
    st = student(page)
    pdf(to_print(st), folder / f"{name} — рабочий лист ученика.pdf")
    left = [w for w in ("<details", "<summary", "<!--T-->", "Ответ:") if w in st]
    print("страница:", out / "stranica.html")
    print("в версии ученика осталось:", left or "ничего лишнего")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], os.environ.get("SCRATCH", "/tmp/sborka"))
