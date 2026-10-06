"""Рисунок 1.1: официальная характеристика Grundfos CR 10-7 (3x400 В, 50 Гц,
Grundfos Product Center, pz/cr10-7_grundfos.png) с нанесённой рабочей точкой.

Кривая H(Q) оцифровывается по синим пикселям; калибровка осей по линиям сетки:
Q = 0 при x = 41, 46 px на 1 м³/ч; H = 0 при y = 392, 85 м на 361,5 px.
Печатает напор, КПД, мощность и NPSH при расчётной подаче, пишет nasos.json
и рисунок nasos_cr10-7.png (верхний график: H(Q) и КПД).
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "..", "calc", "rezultaty_v3.json")))
Q = round(R["rasx"]["q_tot"] * 3.6, 6)      # м³/ч
H_NAS = R["H_nas"]

im = Image.open(os.path.join(HERE, "cr10-7_grundfos.png")).convert("RGB")
a = np.asarray(im).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
X0, PXQ = 41, 46.0
Y0, PXH = 392.0, (392 - 30.5) / 85
YP0, PXP = 612.5, 58.0                        # нижний график: P = 0 при y = 612,5; 58 px на 1 кВт
qx = lambda x: (x - X0) / PXQ
hy = lambda y: (Y0 - y) / PXH
xq = lambda q: X0 + q * PXQ
yh = lambda h: Y0 - h * PXH

blue = (b > r + 40) & (b > g + 20)
dark = (r < 100) & (g < 100) & (b < 100)
pts = []
for x in range(42, 650):                      # до 13,2 м³/ч, без подписей
    ys = np.where(blue[20:235, x])[0] + 20
    if len(ys):
        pts.append((qx(x), hy(ys.mean())))
pts = np.array(pts)
H_Q = float(np.interp(Q, pts[:, 0], pts[:, 1]))

x = int(round(xq(Q)))
eta = sorted(hy(y) * 2 for y in np.where(dark[200:390, x])[0] + 200)   # шкала eta = 2·H
p_bl = sorted((YP0 - y) / PXP for y in np.where(blue[400:623, x])[0] + 400)
npsh = [(YP0 - y) / PXP * 4 for y in np.where(dark[400:623, x])[0] + 400]  # шкала NPSH = 4·P
N_gidr = 1000 * 9.81 * Q / 3600 * H_Q / 1000
res = {
    "Q": round(Q, 2), "H_Q": round(H_Q, 1), "H_nas": round(H_NAS, 2),
    "zapas_proc": round((H_Q / H_NAS - 1) * 100, 1),
    "eta_nasos": round(eta[-1]), "eta_obsh": round(eta[0]),
    "P1": round(float(p_bl[-1]), 2), "P2": round(float(p_bl[0]), 2),
    "NPSH": round(float(np.mean(npsh)), 1),
    "eta_proverka": round(N_gidr / p_bl[0] * 100),   # N_гидр / P2 ≈ η насоса
}
print(res)
json.dump(res, open(os.path.join(HERE, "nasos.json"), "w"), ensure_ascii=False, indent=1)

# рисунок: увеличение ×2 для печати, рабочая точка и требуемый напор
K = 2
big = im.resize((im.width * K, im.height * K), Image.LANCZOS)
d = ImageDraw.Draw(big)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
RED = (200, 30, 30)
X = xq(Q) * K
for y in range(int(yh(0) * K), int(yh(H_Q) * K), -14):          # пунктир Q = const
    d.line([(X, y), (X, y - 7)], fill=RED, width=2)
for xx in range(int(xq(0) * K), int(X), 14):                     # пунктир H = H_нас
    d.line([(xx, yh(H_NAS) * K), (xx + 7, yh(H_NAS) * K)], fill=RED, width=2)
for h, lab in [(H_Q, "1"), (H_NAS, "2")]:
    y = yh(h) * K
    d.ellipse([X - 7, y - 7, X + 7, y + 7], outline=RED, fill=(255, 255, 255) if lab == "2" else RED, width=3)
    d.text((X + 12, y - 30 if lab == "1" else y + 2), lab, fill=RED, font=font)
big = big.crop((0, 0, big.width, int(406 * K)))          # только H(Q) и КПД; P и NPSH — в cr10-7_grundfos.png
big.save(os.path.join(HERE, "nasos_cr10-7.png"))
print("size", big.size)
