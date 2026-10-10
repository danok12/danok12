"""Общая вёрстка серии: петролевая палитра, Spectral / Source Sans 3 / JetBrains Mono.
Страница собирается из HTML-фрагментов; из одного источника получаются
версия для Artifact (фрагмент без <html>), печатная копия и PDF."""
import os, re, io
import qrcode, qrcode.image.svg
from pdf import print_copy, pdf

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,500;0,700;1,500'
         '&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">')

CSS = r'''
/* Лист занятия: одна колонка ~70 знаков, карточки только у разборов и задач-ловушек */
:root{
  --bg:#f3f7f7; --paper:#ffffff; --ink:#15292c; --muted:#557172; --line:#c8dad9;
  --petrol:#0e5d65; --petrol-soft:#e2efef; --warn:#a4471f; --warn-soft:#f8e9e1;
  --f-head:"Spectral","Liberation Serif",Georgia,serif;
  --f-text:"Source Sans 3","DejaVu Sans","Segoe UI",Arial,sans-serif;
  --f-mono:"JetBrains Mono","DejaVu Sans Mono",Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0c1a1c; --paper:#122427; --ink:#e2eeee; --muted:#95b0b0; --line:#2a4548;
  --petrol:#62bcc3; --petrol-soft:#16383b; --warn:#eba07a; --warn-soft:#3a2219; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0c1a1c; --paper:#122427; --ink:#e2eeee; --muted:#95b0b0; --line:#2a4548;
  --petrol:#62bcc3; --petrol-soft:#16383b; --warn:#eba07a; --warn-soft:#3a2219; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-text);font-size:16.5px;line-height:1.55;margin:0}
.wrap{max-width:820px;margin:0 auto;padding-inline:18px;padding-block:28px 56px}
header.top{border-bottom:2px solid var(--petrol);padding-bottom:14px;margin-bottom:22px}
.eyebrow{font-size:12.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--petrol);font-weight:700;margin:0 0 4px}
h1{font-family:var(--f-head);font-weight:700;font-size:clamp(26px,5vw,36px);line-height:1.15;margin:0 0 8px;text-wrap:balance}
.lead{color:var(--muted);margin:0;max-width:62ch}
h2{font-family:var(--f-head);font-weight:700;font-size:24px;margin:34px 0 10px;color:var(--ink);text-wrap:balance;
   display:flex;gap:10px;align-items:baseline;break-after:avoid}
h2 .n{font-family:var(--f-mono);font-size:14px;color:var(--petrol);font-weight:600}
h3{font-family:var(--f-head);font-weight:700;font-size:19px;color:var(--petrol);margin:22px 0 8px;break-after:avoid}
p{margin:0 0 10px}
.muted{color:var(--muted)}
.m{font-family:var(--f-mono);font-size:.92em;white-space:nowrap}
i{font-family:var(--f-head);font-size:1.05em}
.steps{display:grid;gap:6px;padding:0;margin:0 0 6px;list-style:none;counter-reset:s}
.steps li{counter-increment:s;display:grid;grid-template-columns:28px 1fr;gap:8px}
.steps li::before{content:counter(s);font-family:var(--f-mono);font-weight:600;color:var(--petrol);
  border:1.5px solid var(--petrol);border-radius:50%;width:24px;height:24px;display:grid;place-items:center;font-size:13px}
/* шпаргалка */
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,350px),1fr));gap:12px;margin:8px 0 6px}
.fact{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:12px 14px;display:grid;
  grid-template-columns:auto 1fr;gap:12px;align-items:center;break-inside:avoid;min-width:0}
.fact.nofig{grid-template-columns:1fr}
.fact b{color:var(--petrol)}
.fact p{margin:0 0 4px}.fact p:last-child{margin:0}
.fact svg{width:150px;max-width:100%;height:auto}
/* разбор */
.ex{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:14px 16px;margin:12px 0;break-inside:avoid}
.ex-head{display:flex;gap:10px;align-items:baseline;margin-bottom:6px}
.tag{font-family:var(--f-mono);font-size:12px;font-weight:600;color:var(--petrol);background:var(--petrol-soft);
  padding:2px 8px;border-radius:3px;white-space:nowrap}
.ex-body{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:start}
.ex-body.nopic{grid-template-columns:1fr}
.ex-body>div{min-width:0}
.ex-body svg{width:240px;max-width:100%;height:auto}
details{margin-top:8px;border-top:1px dashed var(--line);padding-top:8px}
summary{cursor:pointer;color:var(--petrol);font-weight:600}
summary:focus-visible{outline:2px solid var(--petrol);outline-offset:2px}
.sol p{margin:6px 0}
.answer{font-weight:700}
.warnbox{background:var(--warn-soft);border-left:3px solid var(--warn);padding:10px 14px;margin:10px 0;border-radius:0 4px 4px 0}
.warnbox b{color:var(--warn)}
/* задачи */
ol.tasks{list-style:none;padding:0;margin:6px 0;display:grid;gap:8px;counter-reset:t}
ol.tasks p{margin:0 0 4px}
ol.tasks>li{display:grid;grid-template-columns:44px 1fr;gap:6px;break-inside:avoid;padding-bottom:8px;border-bottom:1px solid var(--line)}
ol.tasks>li>.num{font-family:var(--f-mono);font-weight:600;color:var(--petrol)}
ol.tasks>li>div{min-width:0}
.ansline{color:var(--muted);margin:2px 0 0!important;font-size:15px}
.key{margin-top:4px;color:var(--petrol);font-weight:600}
/* типовые ошибки */
.tw{overflow-x:auto}
table.err{border-collapse:collapse;width:100%;font-size:15px;min-width:520px}
table.err th{text-align:left;font-weight:700;color:var(--petrol);border-bottom:2px solid var(--petrol);padding:6px 8px}
table.err td{border-bottom:1px solid var(--line);padding:7px 8px;vertical-align:top}
table.err tr{break-inside:avoid}
.wrong{background:var(--paper);border:1px dashed var(--warn);border-radius:6px;padding:10px 14px;margin:6px 0 0}
.wrong .lbl{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--warn);font-weight:700}
/* видео */
.videos{display:grid;gap:10px}
.video{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:12px 14px;display:grid;
  grid-template-columns:1fr auto;gap:12px;align-items:center;break-inside:avoid}
.video>div{min-width:0}
.video a{color:var(--petrol);font-weight:600;text-decoration-thickness:1px;text-underline-offset:3px;word-break:break-word}
.video .meta{font-size:14px;color:var(--muted);margin:2px 0 0}
.video .why{margin:4px 0 0;font-size:15px}
.qr{width:78px;height:78px;color:var(--ink);display:none}
.fig{max-width:100%;height:auto;color:var(--ink)}
.fr{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;line-height:1.1;margin:0 2px}
.fr>span:first-child{border-bottom:1px solid currentColor;padding:0 3px 1px}
.fr>span:last-child{padding:1px 3px 0}
.rt{border-top:1px solid currentColor;padding-top:1px}
.vec{position:relative;font-family:var(--f-head);font-style:italic;display:inline-block}
.vec::after{content:"\2192";position:absolute;left:50%;transform:translateX(-50%);top:-.7em;font-size:.72em;font-style:normal}
.sys{display:inline-flex;align-items:center;vertical-align:middle;margin:2px 4px}
.sys::before{content:"{";font-size:2.4em;line-height:1;font-weight:300;margin-right:3px;font-family:var(--f-text)}
.sys>span{display:flex;flex-direction:column;gap:2px}
.teacher{background:var(--petrol-soft);border-radius:4px;padding:8px 12px;margin:8px 0;font-size:15px}
.teacher::before{content:"Преподавателю. ";font-weight:700;color:var(--petrol)}
footer{margin-top:40px;font-size:13.5px;color:var(--muted);border-top:1px solid var(--line);padding-top:10px}
@media (max-width:560px){.ex-body{grid-template-columns:1fr}.ex-body svg{width:min(100%,260px)}
  .fact{grid-template-columns:1fr}.video{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media print{
  @page{margin:14mm 12mm}
  body{font-size:11.4pt;background:#fff}
  .wrap{max-width:none;padding:0}
  .qr{display:block}
  .ex,.fact,.video,ol.tasks>li,table.err tr,.wrong,.warnbox{break-inside:avoid}
  h2,h3{break-after:avoid}
  .pb{break-before:page}
  details summary{list-style:none}
  details summary::-webkit-details-marker{display:none}
}
'''

def fr(a, b): return f'<span class="fr"><span>{a}</span><span>{b}</span></span>'
def rt(s): return f'√<span class="rt">{s}</span>'
def vec(s): return f'<span class="vec">{s}</span>'
def sys_(*rows): return '<span class="sys"><span>' + ''.join(f'<span>{r}</span>' for r in rows) + '</span></span>'

def qr_svg(url):
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1)
    s = img.to_string(encoding='unicode')
    s = re.sub(r'<\?xml[^>]*>', '', s)
    s = s.replace('<svg ', '<svg class="qr" ', 1)
    s = re.sub(r'fill="#000000"', 'fill="currentColor"', s)
    s = re.sub(r'width="[^"]*mm" height="[^"]*mm" ', '', s)
    return s

TOKENS = {'ACCENT': 'var(--petrol)', 'PAPER': 'var(--paper)', 'GRID': 'var(--line)', 'WARN': 'var(--warn)',
          'SOFT': 'var(--petrol-soft)'}

def themed(svg):
    """Заменяет условные цвета ACCENT/PAPER/GRID/… на CSS-переменные темы (через style, не атрибуты)."""
    def fix(tag):
        t = tag.group(0); style = []
        for attr in ('stroke', 'fill'):
            m = re.search(rf' {attr}="([A-Z]+)"', t)
            if m and m.group(1) in TOKENS:
                style.append(f'{attr}:{TOKENS[m.group(1)]}'); t = t.replace(m.group(0), '')
        if style: t = t[:-1].rstrip('/') + f' style="{";".join(style)}"' + ('/>' if t.endswith('/>') else '>')
        return t
    return re.sub(r'<[a-z]+ [^>]*>', fix, svg)

def video(title, url, meta, why):
    return (f'<div class="video"><div><a href="{url}" target="_blank" rel="noopener">{title}</a>'
            f'<p class="meta">{meta}</p><p class="why">{why}</p></div>{qr_svg(url)}</div>')

def page(title, body):
    return f'<title>{title}</title>\n{FONTS}\n<style>{CSS}</style>\n<div class="wrap">\n{body}\n</div>\n'

def strip_teacher(html):
    """Ученику — без ответов и без заметок преподавателя (CLAUDE.md, п. 5)."""
    html = re.sub(r'<div class="teacher">.*?</div><!--/t-->', '', html, flags=re.S)
    html = re.sub(r'<div class="key">.*?</div><!--/k-->', '', html, flags=re.S)
    return html

def write_all(here, slug, title, body, pdf_names):
    """slug.html — версия ученику для Artifact; печатные копии и PDF: ученику и преподавателю."""
    student = page(title, strip_teacher(body)); teacher = page(title + ' · ответы', body)
    open(os.path.join(here, slug + '.html'), 'w', encoding='utf-8').write(student)
    out = []
    for html, name in ((student, pdf_names[0]), (teacher, pdf_names[1])):
        if not name: continue
        doc = '<!doctype html><html lang="ru"><head><meta charset="utf-8">' + print_copy(html) + '</head><body></body></html>'
        # содержимое страницы — внутрь body
        doc = doc.replace('</head><body></body></html>', '')
        head, rest = doc.split('<div class="wrap">', 1)
        doc = head + '</head><body><div class="wrap">' + rest + '</body></html>'
        tmp = os.path.join(here, f'.print-{slug}-{len(out)}.html')
        open(tmp, 'w', encoding='utf-8').write(doc)
        pdf(tmp, os.path.join(here, name)); out.append(tmp)
    return out
