"""Сборка PDF и контрольных скриншотов через установленный Chromium (см. CLAUDE.md)."""
import os, re, subprocess, tempfile

CH = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

def print_copy(html):
    """Печатная копия: без Google Fonts, без тёмной темы, все <details> раскрыты."""
    html = re.sub(r'<link[^>]+fonts\.(googleapis|gstatic)[^>]*>\s*', '', html)
    html = cut_blocks(html, '@media (prefers-color-scheme:dark)')
    html = cut_blocks(html, ':root[data-theme="dark"]')
    html = html.replace('<details>', '<details open>')
    return html

def cut_blocks(css, head):
    while True:
        i = css.find(head)
        if i < 0: return css
        j = css.index('{', i); depth = 0
        for k in range(j, len(css)):
            if css[k] == '{': depth += 1
            elif css[k] == '}':
                depth -= 1
                if depth == 0: break
        css = css[:i] + css[k + 1:]

def pdf(html_path, pdf_path):
    subprocess.run([CH, '--headless', '--disable-gpu', '--no-sandbox', '--no-pdf-header-footer',
                    '--virtual-time-budget=8000', f'--print-to-pdf={pdf_path}', 'file://' + os.path.abspath(html_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def screenshot(html_path, png_path, width=900, height=3000):
    src = open(html_path, encoding='utf-8').read().replace('@media print{', '@media all{')
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8',
                                     dir=os.path.dirname(os.path.abspath(html_path))) as f:
        f.write(src); tmp = f.name
    try:
        subprocess.run([CH, '--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
                        f'--window-size={width},{height}', f'--screenshot={png_path}', 'file://' + tmp],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(tmp)
