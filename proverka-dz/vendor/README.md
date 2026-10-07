# Сторонние библиотеки для сайта

Лежат здесь, а не грузятся с CDN: на сайте в браузере хранится ключ API, и чужие скрипты на странице ему ни к чему.
Политика безопасности страницы (CSP) разрешает скрипты только со своего адреса и сетевые запросы только к api.anthropic.com.

| Файл | Что это | Версия | Лицензия |
|---|---|---|---|
| `anthropic-sdk.min.js` | официальный SDK `@anthropic-ai/sdk`, собран в один файл для браузера (глобальная переменная `AnthropicSDK`) | 0.132.0 | MIT, `LICENSE-anthropic-sdk.txt` |
| `pdf.min.js`, `pdf.worker.min.js` | `pdfjs-dist`, открывает PDF с решениями | 3.11.174 | Apache-2.0, `LICENSE-pdfjs.txt` |

Как пересобрать SDK:

```bash
npm install @anthropic-ai/sdk@0.132.0 esbuild
printf 'import Anthropic from "@anthropic-ai/sdk";\nexport { Anthropic };\n' > entry.mjs
npx esbuild entry.mjs --bundle --minify --format=iife --global-name=AnthropicSDK \
  --platform=browser --target=es2020 --legal-comments=none --outfile=anthropic-sdk.min.js
```
