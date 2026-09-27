// Сборка презентации «Космополитизм» (pptxgenjs).
// Запуск: node build.js  → ../kosmopolitizm.pptx и ../TEKST.md
// Размеры — в дюймах, холст 13.333 × 7.5 (16:9).

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const TEKST = require("./tekst.js");

const OUT_DIR = path.resolve(__dirname, "..");
const IMG = (f) => path.join(__dirname, "img", f);

// ---------- палитра и шрифты ----------
const C = {
  bg: "F1EDE6",        // светлый тёплый фон
  card: "E5DED3",      // бежево-серые плашки
  cardLight: "EBE5DB",
  paper: "F8F5F0",     // карточки поверх графики
  blue: "2B4C8C",      // акцентный синий
  blueDark: "1F3868",
  blueMid: "7F97C4",
  blueSoft: "A9BAD9",
  bluePale: "DCE3EF",
  blueOnDark: "C9D4E8",
  brown: "3B2A20",     // основной текст — тёмно-коричневый
  brownSoft: "75645A",
  brownFill: "4A362A",
  watermark: "E2DACE",
};
const F = { head: "Arial Narrow", body: "Calibri", quote: "Georgia" };
const W = 13.333, H = 7.5, M = 0.6;          // холст и поле
const CW = W - 2 * M;                          // ширина контента
const TOTAL = TEKST.length;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Космополитизм";
pres.subject = "Гражданин мира: от Диогена до наших дней";

// ---------- помощники ----------
const T = (slide, text, o) => slide.addText(text, { isTextBox: true, margin: 0, color: C.brown, fontFace: F.body, ...o });
const rect = (slide, x, y, w, h, color, extra = {}) =>
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color }, line: { color, width: 0 }, ...extra });

function line(slide, x1, y1, x2, y2, color, width = 1) {
  slide.addShape(pres.shapes.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: (x2 - x1) * (y2 - y1) < 0, line: { color, width },
  });
}

function base(slide, n, { dark = false } = {}) {
  slide.background = { color: dark ? C.blue : C.bg };
  const col = dark ? C.blueOnDark : C.brownSoft;
  T(slide, "КОСМОПОЛИТИЗМ", { x: M, y: 0.3, w: 4, h: 0.3, fontFace: F.head, fontSize: 11, charSpacing: 3, color: col });
  T(slide, `${String(n).padStart(2, "0")} / ${TOTAL}`, { x: W - M - 2, y: 0.3, w: 2, h: 0.3, fontFace: F.head, fontSize: 11, charSpacing: 2, color: col, align: "right" });
}

function title(slide, text, w = CW) {
  T(slide, text, { x: M, y: 0.72, w, h: 0.75, fontFace: F.head, fontSize: 34, bold: true, color: C.blue, charSpacing: 1, valign: "middle" });
}

// строка «//01 заголовок + пояснение» на бежевой плашке — мотив из референса
function numRow(slide, x, y, w, h, num, head, text, { fill = C.card, size = 14.5 } = {}) {
  rect(slide, x, y, w, h, fill);
  T(slide, "//" + num, { x: x + 0.18, y, w: 0.8, h, fontFace: F.head, fontSize: 22, bold: true, color: C.blue, valign: "middle" });
  T(slide, [
    { text: head, options: { bold: true, breakLine: true } },
    { text },
  ], { x: x + 1.0, y, w: w - 1.2, h, fontSize: size, valign: "middle", paraSpaceAfter: 2 });
}

// плашка-метка (как «МЕХАНИКА:» в референсе)
function tag(slide, text, x, y, w, { fill = C.card, color = C.blue, h = 0.36, size = 12.5 } = {}) {
  rect(slide, x, y, w, h, fill);
  T(slide, text, { x: x + 0.14, y, w: w - 0.2, h, fontFace: F.head, fontSize: size, bold: true, charSpacing: 2, color, valign: "middle" });
}

// каркасный глобус: контур, меридианы-эллипсы, параллели-хорды
function globe(slide, cx, cy, r, { color = C.blueMid, width = 1, fill = null } = {}) {
  const base = { line: { color, width } };
  if (fill) slide.addShape(pres.shapes.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: fill }, line: { color: fill, width: 0 } });
  slide.addShape(pres.shapes.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, ...base });
  for (const lon of [30, 60]) {
    const a = r * Math.sin((lon * Math.PI) / 180);
    slide.addShape(pres.shapes.OVAL, { x: cx - a, y: cy - r, w: 2 * a, h: 2 * r, line: { color, width } });
  }
  line(slide, cx, cy - r, cx, cy + r, color, width);
  for (const lat of [-60, -30, 0, 30, 60]) {
    const yy = cy + r * Math.sin((lat * Math.PI) / 180);
    const half = r * Math.cos((lat * Math.PI) / 180);
    line(slide, cx - half, yy, cx + half, yy, color, width);
  }
}

// двойная тонкая вертикаль — «колонна», как линии у фото в референсе
function doubleV(slide, x, y1, y2, color = C.blue) {
  line(slide, x, y1, x, y2, color, 1);
  line(slide, x + 0.09, y1, x + 0.09, y2, color, 1);
}

// картинка со смещённой рамкой-линией
function framedImage(slide, file, x, y, w, h, dx = 0.16, dy = 0.16) {
  slide.addShape(pres.shapes.RECTANGLE, { x: x + dx, y: y + dy, w, h, line: { color: C.blue, width: 1 } });
  slide.addImage({ path: IMG(file), x, y, w, h });
}

const slides = [];
const add = (opts) => { const s = pres.addSlide(); slides.push(s); return s; };

// ================= 1. Титул =================
{
  const s = add();
  s.background = { color: C.bg };
  T(s, "ΚΟΣΜΟΠΟΛΙΤΗΣ", { x: 0.45, y: 0.55, w: 8, h: 1.1, fontFace: F.head, fontSize: 66, color: C.watermark, charSpacing: 4 });
  T(s, "КОСМОПОЛИТИЗМ", { x: M, y: 2.2, w: 8.2, h: 1.2, fontFace: F.head, fontSize: 64, bold: true, color: C.blue, charSpacing: 2, valign: "middle" });
  T(s, "Гражданин мира: от Диогена до наших дней", { x: M, y: 3.5, w: 7.6, h: 0.55, fontSize: 24, valign: "middle" });
  T(s, [
    { text: "κόσμος", options: { italic: true, color: C.blue } },
    { text: " — мир   ·   ", options: {} },
    { text: "πολίτης", options: { italic: true, color: C.blue } },
    { text: " — гражданин", options: {} },
  ], { x: M, y: 4.15, w: 7.6, h: 0.45, fontFace: F.quote, fontSize: 17, color: C.brownSoft, valign: "middle" });
  // ступенчатые полосы, как на титуле референса
  rect(s, 0, 5.45, 5.9, 0.15, C.blue);
  rect(s, 1.0, 5.85, 5.3, 0.15, C.blue);
  rect(s, 0, 6.25, 3.7, 0.15, C.blueMid);
  // глобус за статуей
  globe(s, 10.25, 3.05, 2.3, { color: C.blueMid, width: 1, fill: C.bluePale });
  const sh = 6.55, sw = sh * (487 / 962);
  s.addImage({ path: IMG("statue_cutout.png"), x: 9.05, y: H - sh, w: sw, h: sh });
}

// ================= 2. Определение =================
{
  const s = add(); base(s, 2);
  title(s, "ЧТО ТАКОЕ КОСМОПОЛИТИЗМ");
  const y = 1.75, h = 1.55;
  const box = (x, w, gr, tr, ru, dark) => {
    rect(s, x, y, w, h, dark ? C.blue : C.card);
    T(s, [
      { text: gr, options: { fontFace: F.quote, italic: true, fontSize: 30, color: dark ? "FFFFFF" : C.blue, breakLine: true } },
      { text: tr, options: { fontSize: 13, color: dark ? C.blueOnDark : C.brownSoft, breakLine: true } },
      { text: ru, options: { fontSize: 16, bold: true, color: dark ? "FFFFFF" : C.brown } },
    ], { x, y, w, h, align: "center", valign: "middle", paraSpaceAfter: 3 });
  };
  box(M, 3.3, "κόσμος", "kósmos", "мир, вселенная, порядок");
  T(s, "+", { x: 3.95, y, w: 0.55, h, fontFace: F.head, fontSize: 40, color: C.blue, align: "center", valign: "middle" });
  box(4.5, 3.3, "πολίτης", "polítēs", "гражданин");
  T(s, "=", { x: 7.85, y, w: 0.55, h, fontFace: F.head, fontSize: 40, color: C.blue, align: "center", valign: "middle" });
  box(8.4, W - M - 8.4, "κοσμοπολίτης", "kosmopolítēs", "гражданин мира", true);

  tag(s, "ОПРЕДЕЛЕНИЕ", M, 3.75, 2.1);
  T(s, "Космополитизм — убеждение, что все люди принадлежат к единому мировому сообществу и эта принадлежность не менее важна, чем связь со своей страной, городом или народом.",
    { x: M, y: 4.25, w: 5.5, h: 1.75, fontSize: 19, valign: "top", lineSpacingMultiple: 1.05 });
  T(s, "Космополитизм — не отказ от родины. Главный вопрос — как совместить «своё» и «общее».",
    { x: M, y: 6.15, w: 5.5, h: 0.7, fontSize: 14, italic: true, color: C.brownSoft, valign: "top" });

  const rx = 6.55, rw = W - M - rx, rh = 0.92, gap = 0.16;
  numRow(s, rx, 3.75, rw, rh, "01", "Равное достоинство", "все люди равны, где бы они ни родились");
  numRow(s, rx, 3.75 + rh + gap, rw, rh, "02", "Обязанности без границ", "моральный долг не заканчивается на границе государства");
  numRow(s, rx, 3.75 + 2 * (rh + gap), rw, rh, "03", "Общий дом", "у человечества общие проблемы и общее будущее");
}

// ================= 3. Мир полиса =================
{
  const s = add(); base(s, 3);
  title(s, "ДО КОСМОПОЛИТИЗМА: МИР ПОЛИСА");
  const iw = 5.7, ih = iw * (1149 / 1563);
  framedImage(s, "athens_gray.jpg", M, 1.72, iw, ih);
  T(s, "Рафаэль. «Афинская школа», 1509–1511. В центре — Платон и Аристотель",
    { x: M, y: 1.72 + ih + 0.28, w: iw + 0.2, h: 0.3, fontSize: 11.5, italic: true, color: C.brownSoft });

  const rx = 6.85, rw = W - M - rx;
  const item = (y, head, text) => T(s, [
    { text: head, options: { bold: true, color: C.blue, breakLine: true } },
    { text },
  ], { x: rx, y, w: rw, h: 0.95, fontSize: 15, valign: "top", paraSpaceAfter: 2 });
  item(1.72, "Полис — это всё", "Человек существует как гражданин своего города-государства: Афин, Спарты, Коринфа.");
  item(2.72, "Аристотель", "«Человек по природе — существо политическое». Живущий вне полиса — «либо зверь, либо бог».");
  item(3.72, "Эллины и варвары", "Варвары — все, кто не говорит по-гречески: их речь звучала для греков как «бар-бар».");

  rect(s, rx, 4.95, rw, 1.9, C.blue);
  T(s, "ПОВОРОТ", { x: rx + 0.3, y: 5.12, w: 3, h: 0.3, fontFace: F.head, fontSize: 13, bold: true, charSpacing: 3, color: C.blueOnDark });
  T(s, "Ученик Аристотеля — Александр Македонский. Его походы (334–323 до н. э.) разрушили мир независимых полисов, и человеку понадобилась новая опора: не «я — афинянин», а «я — человек».",
    { x: rx + 0.3, y: 5.45, w: rw - 0.6, h: 1.3, fontSize: 15, color: "FFFFFF", valign: "top" });
}

// ================= 4. Парадокс Сократа =================
{
  const s = add(); base(s, 4);
  title(s, "ПАРАДОКС СОКРАТА");
  const iw = 5.95, ih = iw * (1116 / 1764), ix = W - M - iw - 0.16;
  framedImage(s, "socrates_gray.jpg", ix, 1.72, iw, ih);
  T(s, "Жак-Луи Давид. «Смерть Сократа», 1787", { x: ix, y: 1.72 + ih + 0.26, w: iw, h: 0.3, fontSize: 11.5, italic: true, color: C.brownSoft });

  const lw = ix - M - 0.45;
  tag(s, "СЛОВА", M, 1.72, 1.5);
  T(s, "«Я не афинянин и не эллин, а гражданин мира»", { x: M, y: 2.2, w: lw, h: 0.95, fontFace: F.quote, italic: true, fontSize: 21, color: C.blue, valign: "top" });
  T(s, "— так, по Цицерону и Плутарху, Сократ отвечал на вопрос, откуда он родом", { x: M, y: 3.15, w: lw, h: 0.55, fontSize: 13, color: C.brownSoft, valign: "top" });
  tag(s, "ПОСТУПОК", M, 3.85, 1.5);
  T(s, [
    { text: "399 г. до н. э. ", options: { bold: true } },
    { text: "Афинский суд приговорил Сократа к смерти. Друзья готовили побег, но он отказался: нарушить законы родного города — значит предать его. И выпил цикуту." },
  ], { x: M, y: 4.33, w: lw, h: 1.45, fontSize: 15, valign: "top" });

  rect(s, M, 6.05, CW, 0.85, C.blue);
  T(s, "?", { x: M + 0.25, y: 6.05, w: 0.5, h: 0.85, fontFace: F.quote, fontSize: 36, bold: true, color: C.blueOnDark, valign: "middle" });
  T(s, "Можно ли быть гражданином мира — и оставаться верным своему городу?",
    { x: M + 0.85, y: 6.05, w: CW - 1.1, h: 0.85, fontFace: F.quote, italic: true, fontSize: 20, color: "FFFFFF", valign: "middle" });
}

// ================= 5. Диоген =================
{
  const s = add(); base(s, 5);
  title(s, "ДИОГЕН: ПЕРВЫЙ КОСМОПОЛИТ", 8);
  // солнце, которое «заслоняет» карточка с диалогом
  const sx = 11.35, sy = 2.35, r = 0.9;
  s.addShape(pres.shapes.OVAL, { x: sx - r, y: sy - r, w: 2 * r, h: 2 * r, fill: { color: C.bluePale }, line: { color: C.blueMid, width: 1.25 } });
  for (let i = 0; i < 16; i++) {
    const a = (i * 2 * Math.PI) / 16 + Math.PI / 16;
    line(s, sx + (r + 0.18) * Math.cos(a), sy + (r + 0.18) * Math.sin(a), sx + (r + 0.5) * Math.cos(a), sy + (r + 0.5) * Math.sin(a), C.blueMid, 1.5);
  }

  const lw = 6.3;
  T(s, "«Я — гражданин мира»", { x: M, y: 1.7, w: lw, h: 0.85, fontFace: F.quote, italic: true, fontSize: 38, color: C.blue, valign: "middle" });
  T(s, "Диоген Синопский (IV в. до н. э.) — первый, о ком известно, что он называл себя κοσμοπολίτης",
    { x: M, y: 2.6, w: lw, h: 0.6, fontSize: 14, color: C.brownSoft, valign: "top" });
  const rh = 0.95, g = 0.14, y0 = 3.4;
  numRow(s, M, y0, lw, rh, "01", "Изгнанник", "его выслали из родной Синопы на Чёрном море", { size: 14 });
  numRow(s, M, y0 + rh + g, lw, rh, "02", "«Бочка» — это пифос", "огромный глиняный сосуд для зерна, в нём Диоген и жил", { size: 14 });
  numRow(s, M, y0 + 2 * (rh + g), lw, rh, "03", "Вызов обществу", "для киников законы, границы и обычаи условны; важны природа и разум", { size: 14 });

  const cx = 7.45, cw = W - M - cx - 0.35, cy = 2.95, ch = 3.0;
  rect(s, cx, cy, cw, ch, C.blue);
  T(s, "КОРИНФ, IV В. ДО Н. Э.", { x: cx + 0.3, y: cy + 0.22, w: cw - 0.6, h: 0.3, fontFace: F.head, fontSize: 12.5, bold: true, charSpacing: 3, color: C.blueOnDark });
  const who = (t) => ({ text: t, options: { bold: true, color: C.blueOnDark } });
  T(s, [
    who("Александр: "), { text: "«Проси у меня чего хочешь».", options: { breakLine: true } },
    who("Диоген: "), { text: "«Отойди, не заслоняй мне солнце».", options: { breakLine: true } },
    who("Александр: "), { text: "«Если бы я не был Александром, я хотел бы быть Диогеном»." },
  ], { x: cx + 0.3, y: cy + 0.62, w: cw - 0.6, h: ch - 0.8, fontSize: 17, color: "FFFFFF", valign: "top", paraSpaceAfter: 10 });
  T(s, "По преданию, оба умерли в один день — в 323 г. до н. э.",
    { x: cx, y: cy + ch + 0.2, w: cw + 0.35, h: 0.55, fontSize: 13, italic: true, color: C.brownSoft, valign: "top" });
}

// ================= 6. Стоики =================
{
  const s = add(); base(s, 6);
  title(s, "СТОИКИ: ДВА ГОСУДАРСТВА");
  T(s, "Стоики превратили вызов Диогена в стройную философию: каждый человек — гражданин двух государств",
    { x: M, y: 1.45, w: CW, h: 0.45, fontSize: 16, color: C.brownSoft, valign: "middle" });
  const cy = 2.1, ch = 3.65, gap = 0.4, cw = (CW - 2 * gap) / 3;
  const col = (i, name, dates, quote, src) => {
    const x = M + i * (cw + gap);
    rect(s, x, cy, cw, ch, C.card);
    T(s, name, { x: x + 0.3, y: cy + 0.25, w: cw - 0.6, h: 0.4, fontFace: F.head, fontSize: 20, bold: true, charSpacing: 1, color: C.blue });
    T(s, dates, { x: x + 0.3, y: cy + 0.65, w: cw - 0.6, h: 0.3, fontSize: 12, color: C.brownSoft });
    T(s, quote, { x: x + 0.3, y: cy + 1.1, w: cw - 0.6, h: 2.0, fontFace: F.quote, italic: true, fontSize: 17, valign: "top", lineSpacingMultiple: 1.05 });
    T(s, src, { x: x + 0.3, y: cy + ch - 0.5, w: cw - 0.6, h: 0.3, fontSize: 11.5, color: C.brownSoft });
    if (i > 0) doubleV(s, x - gap / 2 - 0.045, cy + 0.2, cy + ch - 0.2);
  };
  col(0, "ЗЕНОН КИТИЙСКИЙ", "ок. 334–262 до н. э. · основатель школы",
    "Люди должны жить не отдельными городами, каждый со своими законами, а одним сообществом под общим законом", "— в пересказе Плутарха");
  col(1, "СЕНЕКА", "ок. 4 до н. э. – 65 н. э. · римский философ",
    "«Есть два государства: одно — великое и поистине общее, его границы мы измеряем путём солнца; другое — то, к которому нас приписал случай рождения»", "— «О досуге»");
  col(2, "МАРК АВРЕЛИЙ", "121–180 · римский император",
    "«Мой город и отечество, поскольку я Антонин, — Рим, а поскольку я человек — мир»", "— «Размышления», VI, 44");

  const fy = 6.05, fh = 0.82, fw = (CW - gap) / 2;
  const fact = (x, text) => {
    rect(s, x, fy, fw, fh, C.cardLight);
    T(s, "ФАКТ", { x: x + 0.2, y: fy, w: 0.8, h: fh, fontFace: F.head, fontSize: 13, bold: true, charSpacing: 2, color: C.blue, valign: "middle" });
    T(s, text, { x: x + 1.0, y: fy, w: fw - 1.2, h: fh, fontSize: 13.5, valign: "middle" });
  };
  fact(M, "«Стоики» — от Стоа Пойкиле, Расписного портика в Афинах, где учил Зенон.");
  fact(M + fw + gap, "Марк Аврелий писал «Размышления» по-гречески, в военных лагерях на Дунае.");
}

// ================= 7. Круги Иерокла =================
{
  const s = add(); base(s, 7);
  title(s, "КРУГИ ИЕРОКЛА");
  const cx = 3.75, cy = 4.42, R = [2.72, 2.28, 1.84, 1.4, 0.96, 0.5];
  const fills = ["E4E9F2", "CCD6E8", "A9BAD9", "7F97C4", "4F6DA8", C.blue];
  const labels = ["ЧЕЛОВЕЧЕСТВО", "СОГРАЖДАНЕ", "СОСЕДИ", "РОДНЯ", "СЕМЬЯ"];
  R.forEach((r, i) => s.addShape(pres.shapes.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: fills[i] }, line: { color: C.bg, width: 1.5 } }));
  labels.forEach((t, i) => {
    const ly = cy - (R[i] + R[i + 1]) / 2;
    T(s, t, { x: cx - 1.4, y: ly - 0.16, w: 2.8, h: 0.32, fontFace: F.head, fontSize: 12.5, bold: true, charSpacing: 1, align: "center", valign: "middle", color: i < 3 ? C.brown : "FFFFFF" });
  });
  T(s, "Я", { x: cx - 0.5, y: cy - 0.3, w: 1, h: 0.6, fontFace: F.head, fontSize: 24, bold: true, align: "center", valign: "middle", color: "FFFFFF" });

  const rx = 7.35, rw = W - M - rx;
  T(s, "Стоик Иерокл, II в. н. э.", { x: rx, y: 1.75, w: rw, h: 0.4, fontFace: F.head, fontSize: 20, bold: true, color: C.blue });
  T(s, "Каждый человек стоит в центре кругов: семья, родня, соседи, сограждане — и, наконец, всё человечество.",
    { x: rx, y: 2.25, w: rw, h: 1.0, fontSize: 16, valign: "top" });
  rect(s, rx, 3.4, rw, 1.35, C.card);
  T(s, [
    { text: "«Стягивать круги к центру»", options: { fontFace: F.quote, italic: true, fontSize: 20, color: C.blue, breakLine: true } },
    { text: "относиться к дальним как к ближним", options: { fontSize: 15 } },
  ], { x: rx + 0.3, y: 3.4, w: rw - 0.6, h: 1.35, valign: "middle", paraSpaceAfter: 4 });
  rect(s, rx, 4.95, rw, 1.2, C.blue);
  T(s, "Космополит не стирает внутренние круги — он не даёт внешним стать чужими.",
    { x: rx + 0.3, y: 4.95, w: rw - 0.6, h: 1.2, fontSize: 16.5, bold: true, color: "FFFFFF", valign: "middle" });
  T(s, "Эту схему использует философ Марта Нуссбаум в споре о патриотизме и космополитизме",
    { x: rx, y: 6.3, w: rw, h: 0.6, fontSize: 12.5, italic: true, color: C.brownSoft, valign: "top" });
}

// ================= 8. Кант =================
{
  const s = add(); base(s, 8);
  title(s, "КАНТ: «К ВЕЧНОМУ МИРУ»");
  const lw = 4.35;
  T(s, "1795", { x: M - 0.05, y: 1.5, w: lw, h: 1.55, fontFace: F.head, fontSize: 110, bold: true, color: C.blue, valign: "middle" });
  T(s, "Иммануил Кант (1724–1804) публикует трактат «К вечному миру»", { x: M, y: 3.1, w: lw, h: 0.75, fontSize: 16, valign: "top" });
  rect(s, M, 4.1, lw, 2.8, C.card);
  T(s, "ИНТЕРЕСНЫЙ ФАКТ", { x: M + 0.3, y: 4.3, w: lw - 0.6, h: 0.3, fontFace: F.head, fontSize: 12.5, bold: true, charSpacing: 2, color: C.blue });
  T(s, "Главный теоретик «гражданина мира» почти всю жизнь провёл в Кёнигсберге (ныне Калининград) и считал, что в портовом городе мир и людей можно узнать без путешествий.",
    { x: M + 0.3, y: 4.72, w: lw - 0.6, h: 2.05, fontSize: 16.5, valign: "top" });

  const rx = 5.4, rw = W - M - rx;
  numRow(s, rx, 1.72, rw, 0.95, "01", "Союз государств вместо войн", "споры между народами решает право, а не сила");
  numRow(s, rx, 2.82, rw, 1.15, "02", "Космополитическое право", "право каждого на гостеприимство: прибыв в чужую страну, не встретить вражды");
  T(s, "«Нарушение права в одном месте Земли ощущается во всех других»",
    { x: rx, y: 4.15, w: rw, h: 0.95, fontFace: F.quote, italic: true, fontSize: 21, color: C.blue, valign: "top" });
  T(s, "Трактат считают одним из идейных истоков Лиги Наций и ООН", { x: rx, y: 5.1, w: rw, h: 0.35, fontSize: 13, color: C.brownSoft });
  rect(s, rx, 5.7, rw, 1.2, C.bluePale);
  T(s, [
    { text: "А в России: ", options: { bold: true, color: C.blue } },
    { text: "«Главное дело быть людьми, а не славянами»", options: { fontFace: F.quote, italic: true, breakLine: true } },
    { text: "Н. М. Карамзин, «Письма русского путешественника»", options: { fontSize: 12, color: C.brownSoft } },
  ], { x: rx + 0.3, y: 5.7, w: rw - 0.6, h: 1.2, fontSize: 16, valign: "middle", paraSpaceAfter: 3 });
}

// ================= 9. На практике =================
{
  const s = add(); base(s, 9);
  title(s, "ГРАЖДАНИН МИРА НА ПРАКТИКЕ");
  T(s, "XIX–XX века: от идеи — к попыткам жить по ней", { x: M, y: 1.45, w: CW, h: 0.45, fontSize: 16, color: C.brownSoft, valign: "middle" });
  const cy = 2.1, ch = 4.0, gap = 0.3, cw = (CW - 2 * gap) / 3;
  const card = (i, year, head, text, dark) => {
    const x = M + i * (cw + gap);
    rect(s, x, cy, cw, ch, dark ? C.blue : C.card);
    T(s, year, { x: x + 0.3, y: cy + 0.2, w: cw - 0.6, h: 0.85, fontFace: F.head, fontSize: 50, bold: true, color: dark ? "FFFFFF" : C.blue, valign: "middle" });
    T(s, head, { x: x + 0.3, y: cy + 1.1, w: cw - 0.6, h: 0.4, fontFace: F.head, fontSize: 17, bold: true, charSpacing: 1.5, color: dark ? C.blueOnDark : C.blue });
    T(s, text, { x: x + 0.3, y: cy + 1.6, w: cw - 0.6, h: ch - 1.75, fontSize: 15.5, color: dark ? "FFFFFF" : C.brown, valign: "top" });
  };
  card(0, "1887", "ЭСПЕРАНТО", "Окулист Людвик Заменгоф вырос в Белостоке, где соседи говорили на разных языках и не доверяли друг другу. Он создал язык «для всего человечества» и подписался «Доктор Эсперанто» — «надеющийся».");
  card(1, "1948", "ГАРРИ ДЭВИС", "Бывший лётчик ВВС США отказался от американского гражданства и объявил себя «гражданином мира». Разбил палатку у дворца Шайо в Париже, где заседала ООН, позже выпускал «мировые паспорта». Жил без гражданства до 2013 г.", true);
  card(2, "1948", "ДЕКЛАРАЦИЯ ПРАВ", "10 декабря в том же дворце Шайо ООН приняла Всеобщую декларацию прав человека: «Все люди рождаются свободными и равными в своём достоинстве и правах».");
  T(s, "Права человека не зависят от паспорта — в этом космополитическая суть Декларации.",
    { x: M, y: 6.3, w: CW, h: 0.5, fontSize: 15, italic: true, color: C.brownSoft, valign: "middle" });
}

// ================= 10. «Безродные космополиты» =================
{
  const s = add(); base(s, 10);
  title(s, "КАК «КОСМОПОЛИТ» СТАЛ РУГАТЕЛЬСТВОМ");
  const lw = 5.95;
  T(s, "28.01.1949", { x: M, y: 1.6, w: lw, h: 0.95, fontFace: F.head, fontSize: 56, bold: true, color: C.blue, valign: "middle" });
  T(s, "Газета «Правда»: статья «Об одной антипатриотической группе театральных критиков»",
    { x: M, y: 2.6, w: lw, h: 0.75, fontSize: 15.5, valign: "top" });
  T(s, [
    { text: "1948–1953 — кампания «борьбы с космополитизмом» в СССР", options: { bullet: { indent: 16 }, breakLine: true } },
    { text: "Клеймо «безродный космополит» — обвинение в «низкопоклонстве перед Западом»: увольнения, исключения из союзов и институтов", options: { bullet: { indent: 16 }, breakLine: true } },
    { text: "Кампания имела явную антисемитскую направленность", options: { bullet: { indent: 16 } } },
  ], { x: M, y: 3.55, w: lw, h: 2.3, fontSize: 15, valign: "top", paraSpaceAfter: 8 });

  const rx = 7.1, rw = W - M - rx;
  // «штамп»
  s.addText("БЕЗРОДНЫЙ КОСМОПОЛИТ", {
    isTextBox: true, x: rx + 0.45, y: 1.72, w: rw - 0.9, h: 0.72, margin: 0, rotate: -3,
    fontFace: F.head, fontSize: 24, bold: true, charSpacing: 3, color: C.brownFill, align: "center", valign: "middle",
    line: { color: C.brownFill, width: 2.5 },
  });
  const dy = 2.85, dh = 1.2;
  rect(s, rx, dy, rw, dh, C.card);
  T(s, [
    { text: "ГРЕЧЕСКИЙ СМЫСЛ", options: { fontFace: F.head, fontSize: 12.5, bold: true, charSpacing: 2, color: C.blue, breakLine: true } },
    { text: "«гражданин мира»", options: { fontFace: F.quote, italic: true, fontSize: 22 } },
  ], { x: rx + 0.3, y: dy, w: rw - 0.6, h: dh, valign: "middle", paraSpaceAfter: 4 });
  T(s, "↓", { x: rx, y: dy + dh, w: rw, h: 0.42, fontSize: 22, bold: true, color: C.brownSoft, align: "center", valign: "middle" });
  const d2 = dy + dh + 0.42;
  rect(s, rx, d2, rw, dh, C.brownFill);
  T(s, [
    { text: "СОВЕТСКИЕ СЛОВАРИ 1950-Х", options: { fontFace: F.head, fontSize: 12.5, bold: true, charSpacing: 2, color: "D9CBBE", breakLine: true } },
    { text: "«реакционная буржуазная идеология»", options: { fontFace: F.quote, italic: true, fontSize: 21, color: "FFFFFF" } },
  ], { x: rx + 0.3, y: d2, w: rw - 0.6, h: dh, valign: "middle", paraSpaceAfter: 4 });
  rect(s, M, 6.0, CW, 0.9, C.bluePale);
  T(s, [
    { text: "Парадокс: ", options: { bold: true, color: C.blue } },
    { text: "лозунгом страны оставалось «Пролетарии всех стран, соединяйтесь!» — интернационализм считался добродетелью, космополитизм — пороком." },
  ], { x: M + 0.3, y: 6.0, w: CW - 0.6, h: 0.9, fontSize: 15, valign: "middle" });
}

// ================= 11. Сегодня =================
{
  const s = add(); base(s, 11);
  title(s, "КОСМОПОЛИТИЗМ СЕГОДНЯ");
  // Земля по текстуре NASA Blue Marble (см. zemlya.py); фон картинки совпадает с фоном слайда
  const er = 2.25, ecx = 10.3, ecy = 3.85, box = 2 * er * 1.035;
  s.addImage({ path: IMG("earth.jpg"), x: ecx - box / 2, y: ecy - box / 2, w: box, h: box });
  s.addShape(pres.shapes.OVAL, { x: ecx - er - 0.22, y: ecy - er - 0.22, w: 2 * er + 0.44, h: 2 * er + 0.44, line: { color: C.blueMid, width: 1 } });
  const stat = (y, big, text) => {
    T(s, big, { x: M, y, w: 2.3, h: 1.05, fontFace: F.head, fontSize: 42, bold: true, color: C.blue, valign: "middle" });
    T(s, text, { x: M + 2.45, y, w: 4.0, h: 1.05, fontSize: 15.5, valign: "middle" });
  };
  stat(1.85, "1992", "Гражданство Евросоюза: гражданин любой страны ЕС может жить и работать в любой другой");
  stat(3.3, "≈1 млн", "«детей Эразмуса» — у пар, познакомившихся по студенческому обмену (оценка Еврокомиссии, 2014)");
  stat(4.75, "0", "границ у климата, пандемий и интернета — такие проблемы решают только вместе");

  const qx = 7.35, qw = W - M - qx, qy = 5.0, qh = 1.9;
  rect(s, qx, qy, qw, qh, C.paper, { shadow: { type: "outer", color: "000000", opacity: 0.12, blur: 8, offset: 2, angle: 90 } });
  T(s, [
    { text: "«ЭФФЕКТ ОБЗОРА»", options: { fontFace: F.head, fontSize: 12, bold: true, charSpacing: 2, color: C.blue, breakLine: true } },
    { text: "«В первый день мы показывали на свои страны. На третий-четвёртый — на континенты. К пятому дню мы видели только одну Землю»", options: { fontFace: F.quote, italic: true, fontSize: 14, breakLine: true } },
    { text: "Султан бин Салман, первый араб в космосе, 1985", options: { fontSize: 11.5, color: C.brownSoft } },
  ], { x: qx + 0.25, y: qy, w: qw - 0.5, h: qh, valign: "middle", paraSpaceAfter: 4 });
}

// ================= 12. За и против =================
{
  const s = add(); base(s, 12);
  title(s, "ЗА И ПРОТИВ");
  const gap = 0.4, cw = (CW - gap) / 2;
  const column = (x, head, fill, items, quote, who) => {
    rect(s, x, 1.7, cw, 0.62, fill);
    T(s, head, { x: x + 0.3, y: 1.7, w: cw - 0.6, h: 0.62, fontFace: F.head, fontSize: 22, bold: true, charSpacing: 3, color: "FFFFFF", valign: "middle" });
    T(s, items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1 } })),
      { x: x + 0.1, y: 2.5, w: cw - 0.2, h: 2.05, fontSize: 15, valign: "top", paraSpaceAfter: 7 });
    rect(s, x, 4.4, cw, 1.4, C.card);
    T(s, [
      { text: quote, options: { fontFace: F.quote, italic: true, fontSize: 15.5, breakLine: true } },
      { text: who, options: { fontSize: 11.5, color: C.brownSoft } },
    ], { x: x + 0.3, y: 4.4, w: cw - 0.6, h: 1.4, valign: "middle", paraSpaceAfter: 4 });
  };
  column(M, "ЗА", C.blue, [
    "Равное достоинство людей — основа прав человека",
    "Климат, пандемии, бедность требуют общих решений",
    "Открытость делает общества терпимее и богаче идеями",
  ], "«Я человек, и ничто человеческое мне не чуждо»", "Теренций, римский драматург, II в. до н. э.");
  column(M + cw + gap, "ПРОТИВ", C.brownFill, [
    "Любовь «ко всему человечеству» может подменить заботу о ближних",
    "Риск размыть культуру, язык и традиции",
    "Гражданство — права и обязанности в конкретном государстве, а мирового государства нет",
  ], "«Иной философ любит татар, чтобы иметь право не любить своих соседей»", "Ж.-Ж. Руссо, «Эмиль», 1762");
  T(s, [
    { text: "Спор продолжается: ", options: { bold: true, color: C.blue } },
    { text: "«Если вы считаете себя гражданином мира, вы гражданин ниоткуда»", options: { fontFace: F.quote, italic: true, breakLine: true } },
    { text: "Тереза Мэй, премьер-министр Великобритании, 2016", options: { color: C.brownSoft, fontSize: 12 } },
  ], { x: M, y: 6.0, w: CW, h: 0.9, fontSize: 16, valign: "middle", paraSpaceAfter: 3 });
}

// ================= 13. Вывод =================
{
  const s = add(); base(s, 13);
  title(s, "ВЫВОД: УКОРЕНЁННЫЙ КОСМОПОЛИТИЗМ");
  const lw = 5.6, ly = 1.72, lh = 3.66;
  rect(s, M, ly, lw, lh, C.blue);
  T(s, "ЗАВЕТ ОТЦА ФИЛОСОФА К. Э. АППИА", { x: M + 0.35, y: ly + 0.28, w: lw - 0.7, h: 0.3, fontFace: F.head, fontSize: 12.5, bold: true, charSpacing: 2, color: C.blueOnDark });
  T(s, "«Помните, что вы граждане мира. Где бы вы ни жили, оставьте это место лучше, чем нашли его»",
    { x: M + 0.35, y: ly + 0.72, w: lw - 0.7, h: 1.75, fontFace: F.quote, italic: true, fontSize: 22, color: "FFFFFF", valign: "top" });
  T(s, "Кваме Энтони Аппиа — сын ганского политика и англичанки, вырос в Гане, преподаёт в США. Автор идеи «укоренённого космополитизма».",
    { x: M + 0.35, y: ly + 2.55, w: lw - 0.7, h: 0.95, fontSize: 13, color: C.blueOnDark, valign: "top" });

  const rx = M + lw + 0.45, rw = W - M - rx, rh = 1.1, g = 0.18;
  numRow(s, rx, ly, rw, rh, "01", "Не «или — или»", "любить свой дом и уважать весь мир — не противоречие");
  numRow(s, rx, ly + rh + g, rw, rh, "02", "Круги Иерокла", "внутренние круги остаются, внешние перестают быть чужими");
  numRow(s, rx, ly + 2 * (rh + g), rw, rh, "03", "Корни и широта", "космополитизм — не отсутствие корней, а широта взгляда");
  T(s, "Ответ Сократу: можно быть верным Афинам — и думать о человеке вообще.",
    { x: M, y: 5.85, w: CW, h: 0.8, fontFace: F.quote, italic: true, fontSize: 22, color: C.blue, valign: "middle" });
}

// ================= 14. Источники =================
{
  const s = add(); base(s, 14);
  title(s, "ИСТОЧНИКИ");
  const list = (x, w, head, items, start) => {
    tag(s, head, x, 1.7, w);
    T(s, items.map((t, i) => ({ text: `${start + i}. ${t}`, options: { breakLine: i < items.length - 1 } })),
      { x, y: 2.25, w, h: 4.7, fontSize: 14, valign: "top", paraSpaceAfter: 6 });
  };
  const gap = 0.45, cw = (CW - gap) / 2;
  list(M, cw, "ПЕРВОИСТОЧНИКИ", [
    "Диоген Лаэртский. О жизни, учениях и изречениях знаменитых философов. Кн. VI",
    "Плутарх. Об изгнании; Александр; О судьбе и доблести Александра",
    "Цицерон. Тускуланские беседы. Кн. V",
    "Платон. Критон",
    "Аристотель. Политика. Кн. I",
    "Сенека. О досуге",
    "Марк Аврелий. Размышления. Кн. VI",
    "Иерокл. Фрагменты (в передаче Стобея)",
    "И. Кант. К вечному миру (1795)",
    "Ж.-Ж. Руссо. Эмиль, или О воспитании (1762)",
    "Н. М. Карамзин. Письма русского путешественника",
  ], 1);
  list(M + cw + gap, cw, "ИССЛЕДОВАНИЯ, ДОКУМЕНТЫ, ИЛЛЮСТРАЦИИ", [
    "Всеобщая декларация прав человека (ООН, 1948)",
    "Г. В. Костырченко. Кампания по борьбе с космополитизмом в СССР",
    "M. Nussbaum. Patriotism and Cosmopolitanism (1994)",
    "K. A. Appiah. Cosmopolitanism: Ethics in a World of Strangers (2006)",
    "G. Davis. My Country Is the World (1961)",
    "European Commission. The Erasmus Impact Study (2014)",
    "Рафаэль. Афинская школа (1509–1511), Ватикан",
    "Ж.-Л. Давид. Смерть Сократа (1787), Метрополитен-музей",
    "NASA. Blue Marble — снимки Земли (слайд 11)",
  ], 12);
}

// ================= 15. Спасибо =================
{
  const s = add(); base(s, 15, { dark: true });
  globe(s, 10.6, 3.85, 2.3, { color: "5874AE", width: 1 });
  T(s, "СПАСИБО\nЗА ВНИМАНИЕ", { x: M, y: 1.55, w: 7.8, h: 2.3, fontFace: F.head, fontSize: 64, bold: true, charSpacing: 2, color: "FFFFFF", valign: "middle", lineSpacingMultiple: 0.95 });
  T(s, "ВОПРОС ДЛЯ ОБСУЖДЕНИЯ", { x: M, y: 4.2, w: 6, h: 0.3, fontFace: F.head, fontSize: 13, bold: true, charSpacing: 3, color: C.blueOnDark });
  T(s, "А вы считаете себя гражданином мира?", { x: M, y: 4.55, w: 7.6, h: 0.7, fontFace: F.quote, italic: true, fontSize: 28, color: "FFFFFF", valign: "middle" });
  rect(s, 0, 5.95, 5.4, 0.15, C.bg);
  rect(s, 0.9, 6.35, 4.8, 0.15, C.blueOnDark);
  rect(s, 0, 6.75, 3.3, 0.15, "5874AE");
}

// ---------- заметки докладчика ----------
if (slides.length !== TEKST.length) throw new Error(`слайдов ${slides.length}, а текстов ${TEKST.length}`);
slides.forEach((s, i) => s.addNotes(TEKST[i].text));

// ---------- TEKST.md ----------
const words = (t) => t.split(/\s+/).filter((w) => /[А-Яа-яЁёA-Za-z0-9]/.test(w)).length;
const total = TEKST.reduce((a, s) => a + words(s.text), 0);
let md = `# Космополитизм — текст выступления\n\n`;
md += `Текст к каждому слайду (он же лежит в заметках докладчика в \`kosmopolitizm.pptx\`).\n`;
md += `Всего ≈ ${total} слов — это ${Math.round(total / 125)}–${Math.round(total / 115)} минут спокойной речи.\n\n`;
md += `Если время поджимает, первым можно сократить: факты о «детях Эразмуса» (слайд 11), Карамзина (слайд 8), эпизод про Нуссбаум (слайд 7).\n`;
TEKST.forEach((s, i) => {
  const n = words(s.text);
  md += `\n## Слайд ${i + 1}. ${s.title}\n\n_≈ ${Math.max(5, Math.round((n / 125) * 60 / 5) * 5)} сек_\n\n${s.text.split("\n").join("\n\n")}\n`;
});
fs.writeFileSync(path.join(OUT_DIR, "TEKST.md"), md);

const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
let html = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Космополитизм — текст выступления</title><style>
@page{margin:16mm 16mm}
body{font-family:Calibri,Carlito,"Segoe UI",sans-serif;color:#${C.brown};background:#fff;font-size:12.5pt;line-height:1.5;max-width:170mm;margin:0 auto}
h1{font-family:"Arial Narrow","Liberation Sans Narrow",sans-serif;color:#${C.blue};font-size:26pt;letter-spacing:.02em;margin:0 0 4pt}
.lead{color:#${C.brownSoft};margin:0 0 14pt}
section{break-inside:avoid;padding:10pt 0 4pt;border-top:1px solid #${C.card}}
h2{font-family:"Arial Narrow","Liberation Sans Narrow",sans-serif;color:#${C.blue};font-size:14pt;margin:0 0 4pt;break-after:avoid}
h2 span{color:#${C.brownSoft};font-weight:normal;font-size:11pt;margin-left:8pt}
p{margin:0 0 6pt}
</style></head><body>
<h1>КОСМОПОЛИТИЗМ — ТЕКСТ ВЫСТУПЛЕНИЯ</h1>
<p class="lead">≈ ${total} слов, ${Math.round(total / 125)}–${Math.round(total / 115)} минут. Если время поджимает, первым можно сократить «детей Эразмуса» (слайд 11), Карамзина (слайд 8) и Нуссбаум (слайд 7).</p>
`;
TEKST.forEach((s, i) => {
  const n = words(s.text);
  html += `<section><h2>Слайд ${i + 1}. ${esc(s.title)}<span>≈ ${Math.max(5, Math.round((n / 125) * 60 / 5) * 5)} сек</span></h2>${s.text.split("\n").map((p) => `<p>${esc(p)}</p>`).join("")}</section>\n`;
});
fs.writeFileSync(path.join(__dirname, "tekst-print.html"), html + "</body></html>\n");

pres.writeFile({ fileName: path.join(OUT_DIR, "kosmopolitizm.pptx") }).then((f) => console.log("готово:", f, "| слов:", total));
