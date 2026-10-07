#!/usr/bin/env python3
"""Собирает публичную версию страницы проверки для GitHub Pages.

    python3 proverka-dz/build_site.py site/proverka

Исходник один — proverka-dz/index.html, он же публикуется как артефакт claude.ai.
Здесь он оборачивается в полноценный HTML-документ с политикой безопасности (CSP)
и меткой proverka-site: по ней страница переключается на работу через ключ Anthropic API
и хранение в браузере. Рядом кладутся библиотеки из vendor/.
"""
import argparse
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent


def build(out: pathlib.Path, api_base: str) -> None:
    src = (HERE / "index.html").read_text(encoding="utf-8")
    cut = src.index('<div class="wrap">')
    head, body = src[:cut], src[cut:]
    csp = "; ".join([
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data: blob:",
        "connect-src " + api_base,
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ])
    doc = "\n".join([
        "<!doctype html>",
        '<html lang="ru">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
        '<meta http-equiv="Content-Security-Policy" content="' + csp + '">',
        '<meta name="referrer" content="no-referrer">',
        '<link rel="icon" href="data:,">',
        '<meta name="proverka-site" content="1">',
        '<meta name="proverka-api-base" content="' + api_base + '">',
        head.rstrip(),
        '<script src="vendor/anthropic-sdk.min.js"></script>',
        "</head>",
        "<body>",
        body.rstrip(),
        "</body>",
        "</html>",
        "",
    ])
    (out / "vendor").mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(doc, encoding="utf-8")
    for f in (HERE / "vendor").iterdir():
        if f.is_file():
            shutil.copy2(f, out / "vendor" / f.name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", help="куда положить сайт, например site/proverka")
    ap.add_argument("--api-base", default="https://api.anthropic.com",
                    help="адрес API; меняется только для локального теста с заглушкой")
    a = ap.parse_args()
    build(pathlib.Path(a.out), a.api_base.rstrip("/"))
    print("собрано:", a.out)
