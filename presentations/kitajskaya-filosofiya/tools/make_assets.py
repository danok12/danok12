"""Генерация фоновых текстур и подготовка иллюстраций для презентации.

Все фоны рисуются процедурно (рисовая бумага + тушевая размывка),
чтобы не зависеть от скриншотов с водяными знаками и держать любой размер.
"""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

random.seed(20260913)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "assets", "raw")
BG = os.path.join(ROOT, "assets", "bg")
IMG = os.path.join(ROOT, "assets", "img")
os.makedirs(BG, exist_ok=True)
os.makedirs(IMG, exist_ok=True)

W, H = 2560, 1440

PAPER = (237, 233, 224)
PAPER_WARM = (231, 226, 214)
GREEN = (41, 53, 45)
INK = (43, 43, 40)


def paper_texture(size, base, grain=9, fibers=900, seed=0):
    """Тёплая фактура рисовой бумаги: мелкое зерно + редкие волокна."""
    rnd = random.Random(seed)
    w, h = size
    im = Image.new("RGB", size, base)
    noise = Image.effect_noise((w, h), grain).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    im = Image.composite(
        Image.new("RGB", size, tuple(min(255, c + 8) for c in base)),
        im,
        noise.point(lambda v: 255 if v > 150 else 0),
    )
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(fibers):
        x, y = rnd.randrange(w), rnd.randrange(h)
        ln = rnd.randint(6, 46)
        dark = rnd.random() < 0.5
        col = (0, 0, 0, rnd.randint(4, 12)) if dark else (255, 255, 255, rnd.randint(6, 18))
        if rnd.random() < 0.5:
            d.line([(x, y), (x + ln, y + rnd.randint(-2, 2))], fill=col, width=1)
        else:
            d.line([(x, y), (x + rnd.randint(-2, 2), y + ln)], fill=col, width=1)
    # мягкая виньетка, чтобы бумага «дышала»
    vign = Image.new("L", size, 0)
    ImageDraw.Draw(vign).ellipse(
        [-w * 0.25, -h * 0.35, w * 1.25, h * 1.35], fill=255
    )
    vign = vign.filter(ImageFilter.GaussianBlur(w // 8))
    im = Image.composite(im, ImageEnhance.Brightness(im).enhance(0.94), vign)
    return im


def mountain_layer(size, y_base, amp, seed, color, alpha, blur):
    """Один слой гор тушью — ломаный силуэт с размывкой."""
    rnd = random.Random(seed)
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [(0, y_base)]
    x = 0
    y = y_base
    while x < w:
        step = rnd.randint(int(w * 0.04), int(w * 0.12))
        x += step
        y += rnd.randint(-amp, amp)
        y = max(y_base - amp * 3, min(y_base + amp, y))
        pts.append((x, y))
    pts += [(w, h), (0, h)]
    d.polygon(pts, fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def mist(size, y, thickness, seed, strength=200):
    rnd = random.Random(seed)
    w, h = size
    m = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    for i in range(14):
        yy = y + rnd.randint(-thickness, thickness)
        hh = rnd.randint(thickness // 3, thickness)
        d.ellipse(
            [rnd.randint(-w // 4, w // 2), yy, rnd.randint(w // 2, int(w * 1.25)), yy + hh],
            fill=(246, 243, 236, strength),
        )
    return m.filter(ImageFilter.GaussianBlur(thickness // 2))


def birds(size, cx, cy, n, seed, scale=1.0):
    rnd = random.Random(seed)
    b = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    for _ in range(n):
        x = cx + rnd.randint(-int(320 * scale), int(320 * scale))
        y = cy + rnd.randint(-int(120 * scale), int(120 * scale))
        s = rnd.randint(4, 9) * scale
        d.line([(x - s, y), (x, y - s * 0.45)], fill=(40, 40, 38, 190), width=max(1, int(s / 3)))
        d.line([(x, y - s * 0.45), (x + s, y)], fill=(40, 40, 38, 190), width=max(1, int(s / 3)))
    return b


def ink_landscape(size=(W, H), seed=7, paper_base=PAPER):
    """Горный пейзаж тушью на бумаге — фон обложки и разделов."""
    im = paper_texture(size, paper_base, seed=seed).convert("RGBA")
    w, h = size
    # дальние горы
    im.alpha_composite(mountain_layer(size, int(h * 0.62), int(h * 0.09), seed + 1, (120, 124, 118), 70, 26))
    im.alpha_composite(mist(size, int(h * 0.58), int(h * 0.13), seed + 2, 190))
    # средние
    im.alpha_composite(mountain_layer(size, int(h * 0.74), int(h * 0.11), seed + 3, (86, 90, 85), 95, 16))
    im.alpha_composite(mist(size, int(h * 0.70), int(h * 0.11), seed + 4, 165))
    # ближние
    im.alpha_composite(mountain_layer(size, int(h * 0.88), int(h * 0.08), seed + 5, (52, 55, 50), 135, 5))
    im.alpha_composite(mist(size, int(h * 0.85), int(h * 0.09), seed + 6, 130))
    im.alpha_composite(birds(size, int(w * 0.34), int(h * 0.52), 16, seed + 7))
    return im.convert("RGB")


def pine_branch(size, seed=3, color=(46, 48, 44), origin="left", scale=1.0):
    """Ветка сосны тушью: тёмные сучья + плотные веера хвои."""
    import math
    rnd = random.Random(seed)
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def needle_fan(x, y, ang, length, n=None):
        """Пучок хвои — веер из коротких игл."""
        n = n or rnd.randint(22, 34)
        spread = rnd.uniform(0.75, 1.15)
        for i in range(n):
            a = ang + rnd.uniform(-spread, spread)
            ln = length * rnd.uniform(0.55, 1.0)
            x2, y2 = x + math.cos(a) * ln, y + math.sin(a) * ln
            d.line([(x, y), (x2, y2)],
                   fill=color + (rnd.randint(130, 225),),
                   width=1)

    def limb(x, y, ang, length, width, depth):
        # сук рисуем сегментами с сужением — получается кисть, а не линейка
        seg = 6
        px, py = x, y
        for i in range(seg):
            a = ang + rnd.uniform(-0.09, 0.09)
            sl = length / seg
            nx, ny = px + math.cos(a) * sl, py + math.sin(a) * sl
            wd = max(1, int(width * (1 - i / (seg + 2))))
            d.line([(px, py), (nx, ny)], fill=color + (235,), width=wd)
            px, py = nx, ny
            # хвоя вдоль сука
            if depth <= 2 and rnd.random() < 0.55:
                needle_fan(px, py, ang + rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.5),
                           rnd.uniform(26, 52) * scale)
        if depth <= 2:
            needle_fan(px, py, ang, rnd.uniform(32, 60) * scale)
        if depth == 0:
            return
        for _ in range(rnd.randint(2, 3)):
            limb(px, py,
                 ang + rnd.uniform(-0.8, 0.8),
                 length * rnd.uniform(0.5, 0.72),
                 width * 0.6,
                 depth - 1)

    if origin == "left":
        limb(-30, int(h * 0.16), math.radians(20), w * 0.26 * scale, 13 * scale, 3)
    else:
        limb(w + 30, int(h * 0.15), math.radians(160), w * 0.26 * scale, 13 * scale, 3)
    return layer


DUO_DARK = (0x32, 0x39, 0x31)   # тушь с зеленцой
DUO_LIGHT = (0xEC, 0xE8, 0xDF)  # бумага


def duotone(im, keep_color=0.12, gamma=1.0, dark=DUO_DARK, light=DUO_LIGHT):
    """Тушевый дуотон: белое уходит в бумагу, тёмное — в тушь.

    Приводит фотографии, гравюры и рисунки к одной выдержанной гамме;
    заодно убирает белые «коробки» вокруг штриховых рисунков.
    """
    alpha = im.getchannel("A") if "A" in im.getbands() else None
    rgb = im.convert("RGB")
    grey = rgb.convert("L")
    if gamma != 1.0:
        grey = grey.point(lambda v: int(255 * (v / 255.0) ** gamma))
    lut = []
    for ch in range(3):
        lut += [int(dark[ch] + (light[ch] - dark[ch]) * (v / 255.0)) for v in range(256)]
    toned = Image.merge("RGB", [grey, grey, grey]).point(lut)
    if keep_color:
        toned = Image.blend(toned, rgb, keep_color)
    if alpha is not None:
        toned = toned.convert("RGBA")
        toned.putalpha(alpha)
    return toned


def mute(im, wash=0.16, color=0.42, contrast=1.05):
    return duotone(im)


def prep(name, out, crop=None, keep=0.12, gamma=1.0, max_side=1600):
    """Подготовка иллюстрации: обрезка вотермарки + приглушение цвета."""
    im = Image.open(os.path.join(RAW, name))
    im = im.convert("RGBA") if "A" in im.getbands() else im.convert("RGB")
    if crop:
        l, t, r, b = crop
        w, h = im.size
        im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
    if max(im.size) > max_side:
        k = max_side / max(im.size)
        im = im.resize((int(im.size[0] * k), int(im.size[1] * k)), Image.LANCZOS)
    im = duotone(im, keep_color=keep, gamma=gamma)
    path = os.path.join(IMG, out)
    if out.lower().endswith((".jpg", ".jpeg")):
        im.convert("RGB").save(path, quality=92)
    else:
        im.save(path)
    return im.size


ILLUSTRATIONS = [
    # исходник,                   результат,                  кроп,                     цвет, гамма
    ("laozi-ox.jpg",            "laozi-ox.jpg",              None,                     0.10, 1.0),
    ("laozi-ox-color.png",      "laozi-ox-color.png",        None,                     0.10, 1.0),
    ("laozi-statue.jpg",        "laozi-statue.jpg",          None,                     0.08, 1.05),
    ("confucius-ink.png",       "confucius-ink.png",         (0.0, 0.10, 1.0, 1.0),    0.06, 1.0),
    ("confucius-portrait.png",  "confucius-portrait.png",    None,                     0.12, 1.0),
    ("confucius-scene.png",     "confucius-scene.png",       (0.0, 0.0, 0.90, 0.93),   0.10, 1.0),
    ("confucius-disciples.png", "confucius-disciples.png",   (0.0, 0.0, 0.955, 0.95),  0.10, 1.0),
    ("two-sages.png",           "two-sages.png",             None,                     0.10, 1.0),
    ("taiji.png",               "taiji.png",                 None,                     0.06, 1.0),
    ("pagoda.jpg",              "pagoda.jpg",                None,                     0.08, 1.05),
    ("cranes-pine.png",         "cranes-pine.png",           (0.0, 0.0, 1.0, 0.93),    0.08, 1.0),
    ("ink-landscape-frame.png", "ink-landscape.png",         (0.05, 0.05, 0.95, 0.95), 0.06, 1.0),
]


def cover_scene(size=(W, H)):
    """Обложка: гряды гор в верхней половине + ветка сосны."""
    w, h = size
    im = paper_texture(size, PAPER, seed=7).convert("RGBA")
    im.alpha_composite(mountain_layer(size, int(h * 0.30), int(h * 0.10), 21, (130, 134, 128), 85, 22))
    im.alpha_composite(mist(size, int(h * 0.27), int(h * 0.10), 22, 165))
    im.alpha_composite(mountain_layer(size, int(h * 0.39), int(h * 0.09), 23, (92, 96, 90), 110, 12))
    im.alpha_composite(mist(size, int(h * 0.36), int(h * 0.09), 24, 145))
    im.alpha_composite(mountain_layer(size, int(h * 0.47), int(h * 0.07), 25, (56, 60, 55), 135, 6))
    im.alpha_composite(mist(size, int(h * 0.45), int(h * 0.07), 26, 115))
    im.alpha_composite(birds(size, int(w * 0.31), int(h * 0.21), 18, 27))
    # ветки свешиваются из верхних углов, центр остаётся пустым
    ls = (int(w * 0.40), int(h * 0.52))
    im.alpha_composite(pine_branch(ls, seed=41, origin="left", scale=0.95), (0, 0))
    # правый верхний угол оставлен пустым — там каллиграфическая метка
    return im.convert("RGB")


def corner_branch(base, seed, origin, alpha, scale, shift=0.0):
    """Бумага с веткой, прижатой к углу, — фон текстовых слайдов."""
    im = base.convert("RGBA")
    w, h = im.size
    layer = Image.new("RGBA", (int(w * 0.46), int(h * 0.55)), (0, 0, 0, 0))
    br = pine_branch(layer.size, seed=seed, origin=origin, scale=scale)
    br.putalpha(br.getchannel("A").point(lambda v: int(v * alpha)))
    x = int(w * 0.54) if origin == "right" else 0
    y = int(h * shift)
    im.alpha_composite(br, (x, y))
    return im.convert("RGB")


def main():
    # --- фоны ---
    cover_scene().save(os.path.join(BG, "cover.png"))
    print("bg/cover.png")

    sect = ink_landscape(seed=31, paper_base=PAPER_WARM)
    sect = Image.blend(sect, Image.new("RGB", sect.size, PAPER_WARM), 0.45)
    sect.save(os.path.join(BG, "section.png"))
    print("bg/section.png")

    base = paper_texture((W, H), PAPER, seed=11)
    corner_branch(base, 5, "right", 0.30, 0.72).save(os.path.join(BG, "paper.png"))
    print("bg/paper.png")

    corner_branch(paper_texture((W, H), PAPER, seed=19), 23, "left", 0.20, 0.55,
                  shift=0.66).save(os.path.join(BG, "paper-quote.png"))
    print("bg/paper-quote.png")

    paper_texture((W, H), PAPER, seed=12).save(os.path.join(BG, "paper-clean.png"))
    print("bg/paper-clean.png")

    gpan = paper_texture((760, H), GREEN, grain=6, fibers=400, seed=13).convert("RGBA")
    gbr = pine_branch((760, H), seed=29, color=(150, 162, 148), origin="right", scale=0.75)
    gbr.putalpha(gbr.getchannel("A").point(lambda v: int(v * 0.26)))
    gpan.alpha_composite(gbr, (0, int(H * 0.42)))
    gpan.convert("RGB").save(os.path.join(BG, "green-panel.png"))
    print("bg/green-panel.png")

    gp = paper_texture((W, H), GREEN, grain=6, fibers=900, seed=17).convert("RGBA")
    gb = pine_branch((W, H), seed=9, color=(150, 160, 148), origin="left")
    gb.putalpha(gb.getchannel("A").point(lambda v: int(v * 0.30)))
    gp.alpha_composite(gb)
    gp.convert("RGB").save(os.path.join(BG, "green-full.png"))
    print("bg/green-full.png")

    # --- иллюстрации ---
    for src, out, crop, keep, gamma in ILLUSTRATIONS:
        if not os.path.exists(os.path.join(RAW, src)):
            print("  ! нет исходника:", src)
            continue
        print("img/%s" % out, prep(src, out, crop=crop, keep=keep, gamma=gamma))


if __name__ == "__main__":
    main()
