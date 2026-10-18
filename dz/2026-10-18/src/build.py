"""Сборка: python3 build.py [ключ...]
Пересчитывает все ответы (assert'ы внутри модулей), пишет HTML в _build/ и печатает PDF.
"""
import os
import subprocess
import sys

from common import render, page, header

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                      # dz/2026-10-18
BUILD = os.path.join(OUT, '_build')
KATEX = os.path.join(os.path.dirname(OUT), '_katex')
CHROME = os.environ.get('CHROME', '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')


def docs():
    import anton_stas, varvara, yana, matvey, klim, yulia, timofey
    return [
        ('Антон, 8 кл — ДЗ', anton_stas.build_anton),
        ('Стас, 8 кл — ДЗ', anton_stas.build_stas),
        ('Варвара, 10 кл — ДЗ', varvara.build),
        ('Яна, 11 кл — ДЗ', yana.build),
        ('Матвей, 11 кл — ДЗ', matvey.build),
        ('Клим, 7 кл — ДЗ', klim.build),
        ('Юлия, колледж — ДЗ', yulia.build),
        ('Тимофей, 11 кл — ДЗ', timofey.build),
    ]


def pdf(html_path, pdf_path):
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer',
                    '--virtual-time-budget=10000', '--print-to-pdf=' + pdf_path,
                    'file://' + html_path], check=True, capture_output=True)


def main(only):
    os.makedirs(BUILD, exist_ok=True)
    built = []
    for fname, fn in docs():
        if only and not any(o.lower() in fname.lower() for o in only):
            continue
        doc = fn()
        body = header(doc) + render(doc)
        hp = os.path.join(BUILD, fname + '.html')
        with open(hp, 'w') as f:
            f.write(page(doc.title, body, 'file://' + KATEX))
        pdf(hp, os.path.join(OUT, fname + '.pdf'))
        built.append(doc)
        print('ok', fname, '—', doc.n, 'задач')
    if not only:
        parts = ['<h1>Ответы к домашним заданиям</h1><div class="sub">Для преподавателя. '
                 'Нумерация совпадает с листами учеников.</div>']
        for i, doc in enumerate(built):
            if i:
                parts.append('<div class="br"></div>')
            parts.append('<h1>%s</h1>' % doc.title)
            parts.append('<div class="ans">' + render(doc, answers=True) + '</div>')
        hp = os.path.join(BUILD, 'answers.html')
        with open(hp, 'w') as f:
            f.write(page('Ответы', '\n'.join(parts), 'file://' + KATEX))
        pdf(hp, os.path.join(OUT, 'Ответы — для преподавателя.pdf'))
        print('ok ответы')


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main(sys.argv[1:])
