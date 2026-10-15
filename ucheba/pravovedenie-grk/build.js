// Сборка двух .pptx из content.js.
// Запуск: NODE_PATH=<папка с node_modules> node build.js [папка-вывода]
// Нужны пакеты: pptxgenjs react react-dom react-icons sharp.

const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");
const { decks } = require("./content");

const OUT = process.argv[2] || __dirname;

// Палитра «генплан»: тёмная хвоя доминирует, терракота — единственный акцент.
const C = {
  spruce: "163A33",
  spruce2: "1F4D44",
  sage: "8FB9A8",
  sageText: "D3E3DB",
  tint: "EEF3F0",
  tint2: "E2EBE6",
  accent: "D9692E",
  accentTint: "FBEADF",
  text: "1B2421",
  muted: "5B6966",
  white: "FFFFFF",
  line: "C9D8D1",
};
const HEAD = "Cambria";
const BODY = "Calibri";
const W = 13.333;
const M = 0.6; // поля
const CW = W - 2 * M; // ширина контентной области

// Неразрывные пробелы: «ст. 39», «№ 96», «7 дней» не должны рваться.
const nb = (s) =>
  s
    .replace(/(^|[\s(«])(ст|ч|п|гл|№)\.? (?=[\d«А-Я])/g, (m, a, b) => `${a}${b}${m.includes(".") ? "." : ""} `)
    .replace(/(\d) (?=(дн|дня|дней|раб|мес|%|этаж|года|г\.|ГрК|КоАП))/g, "$1 ")
    .replace(/ — /g, " — ");

const iconCache = {};
async function icon(name, color) {
  const key = name + color;
  if (!iconCache[key]) {
    const svg = renderToStaticMarkup(React.createElement(fa[name], { size: 256, color: "#" + color }));
    const buf = await sharp(Buffer.from(svg)).png().toBuffer();
    iconCache[key] = "image/png;base64," + buf.toString("base64");
  }
  return iconCache[key];
}

// Плитка-участок с иконкой — сквозной мотив всех слайдов.
async function tile(slide, pres, x, y, s, iconName, fill, iconColor = C.white) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w: s, h: s, fill: { color: fill }, line: { color: fill }, rectRadius: s * 0.18 });
  const p = s * 0.24;
  slide.addImage({ data: await icon(iconName, iconColor), x: x + p, y: y + p, w: s - 2 * p, h: s - 2 * p });
}

function numTile(slide, pres, x, y, s, label, fill, color = C.white, size = 22) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w: s, h: s, fill: { color: fill }, line: { color: fill }, rectRadius: s * 0.18 });
  slide.addText(label, { x, y, w: s, h: s, fontFace: HEAD, fontSize: size, bold: true, color, align: "center", valign: "middle", margin: 0, isTextBox: true });
}

function card(slide, pres, x, y, w, h, fill = C.tint) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.12 });
}

function text(slide, t, o) {
  slide.addText(typeof t === "string" ? nb(t) : t, {
    fontFace: BODY, fontSize: 15, color: C.text, valign: "top", margin: 0, isTextBox: true, ...o,
  });
}

function header(slide, pres, kicker, title, dark = false) {
  slide.addShape(pres.ShapeType.rect, { x: M, y: 0.5, w: 0.15, h: 0.15, fill: { color: C.accent }, line: { color: C.accent } });
  text(slide, kicker, { x: M + 0.28, y: 0.4, w: 10, h: 0.34, fontSize: 12, bold: true, color: dark ? C.sage : C.accent, charSpacing: 2, valign: "middle" });
  text(slide, title, { x: M, y: 0.78, w: CW, h: 0.75, fontFace: HEAD, fontSize: 30, bold: true, color: dark ? C.white : C.spruce, valign: "middle" });
}

// Мотив титульного слайда: кварталы зонирования, один участок выделен.
async function parcels(slide, pres, iconName, deviation) {
  const rows = [
    { y: 0.55, h: 1.35, cells: [[8.75, 1.6], [10.45, 1.05], [11.6, 1.15]] },
    { y: 2.05, h: 1.0, cells: [[8.75, 0.95], [9.8, 1.45], [11.35, 1.4]] },
    { y: 3.2, h: 1.6, cells: [[8.75, 1.3], [10.15, 1.25, "hl"], [11.5, 1.25]] },
    { y: 4.95, h: 0.9, cells: [[8.75, 2.0], [10.85, 1.9]] },
    { y: 6.0, h: 0.9, cells: [[8.75, 1.15], [10.0, 1.3], [11.4, 1.35]] },
  ];
  const fills = ["1F4D44", "245A4F", "2B6457", "1C4740", null];
  let i = 0;
  for (const r of rows) {
    for (const [x, w, hl] of r.cells) {
      if (hl) {
        if (deviation) {
          slide.addShape(pres.ShapeType.roundRect, { x: x - 0.14, y: r.y - 0.3, w: w + 0.28, h: r.h + 0.44, fill: { type: "none" }, line: { color: C.accent, width: 1.5, dashType: "dash" }, rectRadius: 0.12 });
        }
        slide.addShape(pres.ShapeType.roundRect, { x, y: r.y, w, h: r.h, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.1 });
        const s = 0.62;
        slide.addImage({ data: await icon(iconName, C.white), x: x + (w - s) / 2, y: r.y + (r.h - s) / 2, w: s, h: s });
      } else {
        const f = fills[i++ % fills.length];
        slide.addShape(pres.ShapeType.roundRect, {
          x, y: r.y, w, h: r.h, rectRadius: 0.1,
          fill: f ? { color: f } : { type: "none" },
          line: { color: f || "3F7A6B", width: f ? 0 : 1.25 },
        });
      }
    }
  }
}

async function buildDeck(d) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Буев Даниил";
  pres.title = d.title.title;
  pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

  const footer = (color) => [
    { text: { text: d.footer, options: { x: M, y: 6.98, w: 9, h: 0.3, fontFace: BODY, fontSize: 10, color, margin: 0 } } },
  ];
  pres.defineSlideMaster({ title: "TITLE", background: { color: C.spruce }, objects: [] });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: C.white }, objects: footer(C.muted),
    slideNumber: { x: W - M - 0.6, y: 6.98, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: C.muted, align: "right" },
  });
  pres.defineSlideMaster({
    title: "DARK", background: { color: C.spruce }, objects: footer(C.sage),
    slideNumber: { x: W - M - 0.6, y: 6.98, w: 0.6, h: 0.3, fontFace: BODY, fontSize: 10, color: C.sage, align: "right" },
  });

  // 1. Титул
  {
    const t = d.title;
    const s = pres.addSlide({ masterName: "TITLE" });
    await parcels(s, pres, d.titleIcon, d.titleIcon === "FaBuilding");
    text(s, t.course, { x: 0.75, y: 1.0, w: 7.6, h: 0.35, fontSize: 13, bold: true, color: C.sage, charSpacing: 3 });
    text(s, t.title, { x: 0.75, y: 1.45, w: 7.6, h: 1.2, fontFace: HEAD, fontSize: 54, bold: true, color: C.white, valign: "middle" });
    text(s, t.subtitle, { x: 0.75, y: 2.75, w: 7.4, h: 1.25, fontSize: 21, color: C.sageText });
    await tile(s, pres, 0.75, 4.35, 0.62, "FaCompassDrafting", C.accent);
    text(s, t.tagline, { x: 1.55, y: 4.3, w: 6.6, h: 0.75, fontSize: 14, color: C.sageText, valign: "middle" });
    text(s, t.author, { x: 0.75, y: 6.15, w: 7.6, h: 0.35, fontSize: 13, bold: true, color: C.sage, charSpacing: 2 });
    s.addNotes(t.notes);
  }

  // 2. План доклада
  {
    const p = d.plan;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, "ПЛАН ДОКЛАДА", "Три вопроса, на которые отвечает доклад");
    const y0 = 1.85, h = 1.4, gap = 0.28;
    for (const [i, it] of p.items.entries()) {
      const y = y0 + i * (h + gap);
      card(s, pres, M, y, CW, h);
      numTile(s, pres, M + 0.3, y + 0.25, 0.9, String(i + 1), i === 2 ? C.accent : C.spruce, C.white, 30);
      text(s, it.t.replace(/^\d\.\s*/, ""), { x: M + 1.5, y: y + 0.22, w: 9.4, h: 0.5, fontSize: 21, bold: true, color: C.spruce, valign: "middle" });
      text(s, it.d, { x: M + 1.5, y: y + 0.72, w: 9.4, h: 0.5, fontSize: 15, color: C.muted, valign: "middle" });
      s.addImage({ data: await icon(it.icon, C.sage), x: M + CW - 1.05, y: y + 0.4, w: 0.6, h: 0.6 });
    }
    s.addNotes(p.notes);
  }

  // 3. Место статьи: дерево + цифры
  {
    const p = d.place;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    const bx = M, by = 1.8, bh = 0.68, step = 0.38, gap = 0.2, bw = 6.9;
    for (const [i, t] of p.tree.entries()) {
      const x = bx + i * step, y = by + i * (bh + gap), last = i === p.tree.length - 1;
      if (i > 0) {
        const px = bx + (i - 1) * step + 0.2;
        s.addShape(pres.ShapeType.line, { x: px, y: y - gap, w: 0, h: gap + bh / 2, line: { color: C.line, width: 1.5 } });
        s.addShape(pres.ShapeType.line, { x: px, y: y + bh / 2, w: x - px, h: 0, line: { color: C.line, width: 1.5 } });
      }
      card(s, pres, x, y, bw - i * step, bh, last ? C.spruce : C.tint);
      text(s, t, { x: x + 0.25, y, w: bw - i * step - 0.4, h: bh, fontSize: 15, bold: last, color: last ? C.white : C.spruce, valign: "middle" });
    }
    const ny = by + p.tree.length * (bh + gap) + 0.1;
    card(s, pres, M, ny, bw + 0.25, 6.75 - ny, C.accentTint);
    text(s, p.note, { x: M + 0.25, y: ny + 0.12, w: bw - 0.25, h: 6.75 - ny - 0.24, fontSize: 15, color: C.text, valign: "middle" });

    const sx = 8.15, sw = W - M - sx, sh = 1.5, sg = 0.22;
    for (const [i, st] of p.stats.entries()) {
      const y = 1.8 + i * (sh + sg);
      card(s, pres, sx, y, sw, sh);
      text(s, st.num, { x: sx + 0.2, y: y + 0.18, w: 1.65, h: 0.75, fontFace: HEAD, fontSize: 36, bold: true, color: C.accent, align: "center", valign: "middle" });
      text(s, st.unit, { x: sx + 0.2, y: y + 0.92, w: 1.65, h: 0.36, fontSize: 13, bold: true, color: C.spruce, align: "center", valign: "middle" });
      text(s, st.label, { x: sx + 2.0, y: y + 0.15, w: sw - 2.2, h: sh - 0.3, fontSize: 15, color: C.text, valign: "middle" });
    }
    s.addNotes(p.notes);
  }

  // 4. Части статьи — таблица
  {
    const p = d.parts;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    const hdr = (t) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.spruce }, fontSize: 14 } });
    const rows = [[hdr("Часть"), hdr("Что установлено")]];
    for (const [i, [n, t]] of p.rows.entries()) {
      const fill = { color: i % 2 ? C.white : C.tint };
      rows.push([
        { text: nb(n), options: { bold: true, color: C.accent, fill, align: "center" } },
        { text: nb(t), options: { color: C.text, fill } },
      ]);
    }
    s.addTable(rows, {
      x: M, y: 1.75, w: CW, colW: [1.25, CW - 1.25], fontFace: BODY, fontSize: 14, valign: "middle",
      margin: [0.05, 0.14, 0.05, 0.14], border: { type: "solid", pt: 0.75, color: C.line },
      rowH: [0.42, ...p.rows.map(() => 0.64)],
    });
    s.addNotes(p.notes);
  }

  // 5. Участники и путь решения
  {
    const p = d.flow;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    const n = p.steps.length, ag = 0.38, bw = (CW - (n - 1) * ag) / n, by = 1.85, bh = 3.05;
    for (const [i, st] of p.steps.entries()) {
      const x = M + i * (bw + ag);
      const dark = !!st.key;
      card(s, pres, x, by, bw, bh, dark ? C.spruce : C.tint);
      await tile(s, pres, x + 0.22, by + 0.25, 0.7, st.icon, dark ? C.accent : C.spruce);
      text(s, `ШАГ ${i + 1}`, { x: x + 1.05, y: by + 0.25, w: bw - 1.15, h: 0.7, fontSize: 12, bold: true, color: dark ? C.sage : C.accent, charSpacing: 2, valign: "middle" });
      text(s, st.who, { x: x + 0.22, y: by + 1.1, w: bw - 0.4, h: 0.6, fontSize: 17, bold: true, color: dark ? C.white : C.spruce, valign: "middle" });
      text(s, st.what, { x: x + 0.22, y: by + 1.75, w: bw - 0.4, h: 1.2, fontSize: 14, color: dark ? C.sageText : C.text });
      if (i < n - 1) {
        s.addShape(pres.ShapeType.rightArrow, { x: x + bw + 0.07, y: by + bh / 2 - 0.14, w: ag - 0.14, h: 0.28, fill: { color: C.accent }, line: { color: C.accent } });
      }
    }
    card(s, pres, M, 5.2, CW, 1.4, C.accentTint);
    await tile(s, pres, M + 0.3, 5.5, 0.8, "FaTriangleExclamation", C.accent);
    text(s, p.callout, { x: M + 1.35, y: 5.3, w: CW - 1.6, h: 1.2, fontSize: 17, bold: true, color: C.spruce, valign: "middle" });
    s.addNotes(p.notes);
  }

  // 6. Почему выбрана — три карточки
  {
    const p = d.why;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    const g = 0.35, cw = (CW - 2 * g) / 3, cy = 1.9, ch = 4.3;
    for (const [i, c] of p.cards.entries()) {
      const x = M + i * (cw + g);
      card(s, pres, x, cy, cw, ch, c.accent ? C.accentTint : C.tint);
      await tile(s, pres, x + 0.35, cy + 0.38, 0.95, c.icon, c.accent ? C.accent : C.spruce);
      text(s, c.t, { x: x + 0.35, y: cy + 1.6, w: cw - 0.7, h: 0.95, fontSize: 20, bold: true, color: C.spruce, valign: "top" });
      text(s, c.d, { x: x + 0.35, y: cy + 2.6, w: cw - 0.7, h: ch - 2.75, fontSize: 16, color: C.text });
    }
    s.addNotes(p.notes);
  }

  // 7. Сложность 1 — цитата + три тезиса
  {
    const p = d.hard1;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    card(s, pres, M, 1.8, CW, 1.62, C.spruce);
    text(s, "“", { x: M + 0.3, y: 1.78, w: 0.8, h: 1.0, fontFace: HEAD, fontSize: 72, bold: true, color: C.accent });
    text(s, `«${p.quote}»`, { x: M + 1.15, y: 1.95, w: CW - 1.5, h: 0.95, fontFace: HEAD, fontSize: 18, italic: true, color: C.white, valign: "middle" });
    text(s, `— ${p.source}`, { x: M + 1.15, y: 2.92, w: CW - 1.5, h: 0.36, fontSize: 13, bold: true, color: C.sage, valign: "middle" });
    const ry = 3.7, rh = 0.98;
    for (const [i, t] of p.points.entries()) {
      const y = ry + i * rh;
      numTile(s, pres, M, y + 0.12, 0.58, String(i + 1), C.accent, C.white, 18);
      text(s, t, { x: M + 0.85, y, w: CW - 0.9, h: rh - 0.08, fontSize: 15, color: C.text, valign: "middle" });
    }
    s.addNotes(p.notes);
  }

  // 8. Сложность 2 — сравнение или хронология
  {
    const p = d.hard2;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    if (p.kind === "compare") {
      const g = 0.35, cw = (CW - g) / 2, cy = 1.85, ch = 3.65;
      for (const [i, col] of [p.left, p.right].entries()) {
        const x = M + i * (cw + g);
        card(s, pres, x, cy, cw, ch);
        await tile(s, pres, x + 0.3, cy + 0.28, 0.75, col.icon, i ? C.spruce2 : C.spruce);
        text(s, col.t, { x: x + 1.25, y: cy + 0.28, w: cw - 1.5, h: 0.75, fontSize: 20, bold: true, color: C.spruce, valign: "middle" });
        for (const [j, it] of col.items.entries()) {
          const y = cy + 1.3 + j * 0.76;
          s.addShape(pres.ShapeType.rect, { x: x + 0.35, y: y + 0.13, w: 0.13, h: 0.13, fill: { color: C.accent }, line: { color: C.accent } });
          text(s, it, { x: x + 0.65, y, w: cw - 0.95, h: 0.72, fontSize: 15, color: C.text });
        }
      }
      card(s, pres, M, 5.75, CW, 0.95, C.accentTint);
      text(s, p.banner, { x: M + 0.35, y: 5.75, w: CW - 0.7, h: 0.95, fontSize: 17, bold: true, color: C.spruce, valign: "middle" });
    } else {
      const n = p.points.length, ly = 2.55, x0 = M + 0.2, span = CW - 0.4, cw = 2.75;
      const cx = (i) => x0 + cw / 2 + (i * (span - cw)) / (n - 1);
      s.addShape(pres.ShapeType.line, { x: cx(0), y: ly, w: cx(n - 1) - cx(0), h: 0, line: { color: C.line, width: 3 } });
      for (const [i, pt] of p.points.entries()) {
        const c = cx(i), hl = !!pt.key;
        s.addShape(pres.ShapeType.roundRect, { x: c - 0.2, y: ly - 0.2, w: 0.4, h: 0.4, fill: { color: hl ? C.accent : C.spruce }, line: { color: C.white, width: 2 }, rectRadius: 0.08 });
        text(s, pt.y, { x: c - cw / 2, y: 1.75, w: cw, h: 0.5, fontFace: HEAD, fontSize: 24, bold: true, color: hl ? C.accent : C.spruce, align: "center", valign: "middle" });
        card(s, pres, c - cw / 2, 3.0, cw, 2.45, hl ? C.accentTint : C.tint);
        text(s, pt.d, { x: c - cw / 2 + 0.25, y: 3.2, w: cw - 0.5, h: 2.1, fontSize: 16, color: C.text });
      }
      card(s, pres, M, 5.75, CW, 0.95, C.spruce);
      text(s, p.banner, { x: M + 0.35, y: 5.75, w: CW - 0.7, h: 0.95, fontSize: 17, bold: true, color: C.white, valign: "middle" });
    }
    s.addNotes(p.notes);
  }

  // 9. Сложность 3 — три строки
  {
    const p = d.hard3;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    const y0 = 1.8, h = 1.5, gap = 0.2;
    for (const [i, r] of p.rows.entries()) {
      const y = y0 + i * (h + gap);
      card(s, pres, M, y, CW, h);
      await tile(s, pres, M + 0.3, y + 0.33, 0.84, r.icon, C.spruce);
      text(s, r.t, { x: M + 1.45, y: y + 0.14, w: CW - 1.75, h: 0.45, fontSize: 18, bold: true, color: C.spruce, valign: "middle" });
      text(s, r.d, { x: M + 1.45, y: y + 0.6, w: CW - 1.75, h: h - 0.7, fontSize: 15, color: C.text });
    }
    s.addNotes(p.notes);
  }

  // 10. Кейс 1 — три колонки
  {
    const p = d.case1;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    card(s, pres, M, 1.75, CW, 0.95, C.tint);
    await tile(s, pres, M + 0.22, 1.9, 0.65, "FaBuildingColumns", C.spruce);
    text(s, p.lead, { x: M + 1.1, y: 1.75, w: CW - 1.35, h: 0.95, fontSize: 16, color: C.spruce, valign: "middle" });
    const g = 0.3, cw = (CW - 2 * g) / 3, cy = 2.95, ch = 3.75;
    for (const [i, c] of p.cols.entries()) {
      const x = M + i * (cw + g), hl = !!c.key;
      card(s, pres, x, cy, cw, ch, hl ? C.accentTint : C.tint);
      s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: cy + 0.3, w: cw - 0.6, h: 0.48, fill: { color: hl ? C.accent : C.spruce }, line: { color: hl ? C.accent : C.spruce }, rectRadius: 0.08 });
      text(s, c.t.toUpperCase(), { x: x + 0.3, y: cy + 0.3, w: cw - 0.6, h: 0.48, fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle", charSpacing: 2 });
      text(s, c.d, { x: x + 0.3, y: cy + 0.98, w: cw - 0.6, h: ch - 1.15, fontSize: 16, color: C.text });
    }
    s.addNotes(p.notes);
  }

  // 11. Кейс 2 — путь дела со стрелками
  {
    const p = d.case2;
    const s = pres.addSlide({ masterName: "CONTENT" });
    header(s, pres, p.kicker, p.title);
    card(s, pres, M, 1.75, CW, 0.95, C.tint);
    await tile(s, pres, M + 0.22, 1.9, 0.65, "FaGavel", C.spruce);
    text(s, p.lead, { x: M + 1.1, y: 1.75, w: CW - 1.35, h: 0.95, fontSize: 16, color: C.spruce, valign: "middle" });
    const ag = 0.45, cw = (CW - 2 * ag) / 3, cy = 2.95, ch = 3.75;
    for (const [i, st] of p.stages.entries()) {
      const x = M + i * (cw + ag), dark = !!st.key;
      card(s, pres, x, cy, cw, ch, dark ? C.spruce : C.tint);
      numTile(s, pres, x + 0.3, cy + 0.3, 0.55, String(i + 1), dark ? C.accent : C.spruce, C.white, 18);
      text(s, st.t, { x: x + 1.0, y: cy + 0.3, w: cw - 1.2, h: 0.55, fontSize: 18, bold: true, color: dark ? C.white : C.spruce, valign: "middle" });
      text(s, st.d, { x: x + 0.3, y: cy + 1.05, w: cw - 0.6, h: ch - 1.2, fontSize: 15, color: dark ? C.sageText : C.text });
      if (i < 2) {
        s.addShape(pres.ShapeType.rightArrow, { x: x + cw + 0.08, y: cy + ch / 2 - 0.16, w: ag - 0.16, h: 0.32, fill: { color: C.accent }, line: { color: C.accent } });
      }
    }
    s.addNotes(p.notes);
  }

  // 12. Выводы — тёмный слайд
  {
    const p = d.outro;
    const s = pres.addSlide({ masterName: "DARK" });
    header(s, pres, "ВЫВОДЫ", p.title, true);
    const y0 = 1.85, h = 1.45, gap = 0.22;
    for (const [i, it] of p.items.entries()) {
      const y = y0 + i * (h + gap), hl = !!it.key;
      card(s, pres, M, y, CW, h, hl ? C.accent : C.spruce2);
      numTile(s, pres, M + 0.3, y + 0.3, 0.85, String(i + 1), hl ? C.white : C.accent, hl ? C.accent : C.white, 26);
      text(s, it.t, { x: M + 1.45, y: y + 0.16, w: CW - 1.75, h: 0.48, fontSize: 19, bold: true, color: C.white, valign: "middle" });
      text(s, it.d, { x: M + 1.45, y: y + 0.64, w: CW - 1.75, h: h - 0.74, fontSize: 15, color: hl ? C.white : C.sageText });
    }
    s.addNotes(p.notes);
  }

  const file = path.join(OUT, d.file + ".pptx");
  await pres.writeFile({ fileName: file });
  console.log("written", file);
}

(async () => {
  for (const d of decks) await buildDeck(d);
})();
