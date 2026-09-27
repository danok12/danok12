# Вид Земли из космоса для слайда 11.
# Текстуры: NASA Blue Marble и облака из npm-пакета three-globe (example/img/earth-blue-marble.jpg,
# example/clouds/clouds.png): npm pack three-globe && tar xzf three-globe-*.tgz
# Ортографическая проекция с центром над Средиземноморьем, мягкий свет и дымка атмосферы.
# Результат затем приглушён (насыщенность 0.9), уменьшен до 1200 px и положен на фон слайда → img/earth.jpg
import numpy as np, cv2
from PIL import Image

N = 1600                                  # размер итоговой картинки
lat0, lon0 = np.radians(28), np.radians(32)  # центр: Средиземноморье, Чёрное море, Африка
tex = cv2.imread('package/example/img/earth-blue-marble.jpg')[:, :, ::-1].astype(np.float32) / 255
cl = np.array(Image.open('package/example/clouds/clouds.png').convert('RGBA')).astype(np.float32) / 255
H, W = tex.shape[:2]

pad = 0.035                                # поле под свечение атмосферы
s = np.linspace(-1 - pad, 1 + pad, N)
x, y = np.meshgrid(s, -s)
r2 = x**2 + y**2
inside = r2 <= 1
z = np.sqrt(np.clip(1 - r2, 0, 1))
lat = np.arcsin(np.clip(y * np.cos(lat0) + z * np.sin(lat0), -1, 1))
lon = lon0 + np.arctan2(x, z * np.cos(lat0) - y * np.sin(lat0))
u = ((np.degrees(lon) + 180) % 360) / 360 * (W - 1)
v = (90 - np.degrees(lat)) / 180 * (H - 1)
mapx, mapy = u.astype(np.float32), v.astype(np.float32)
earth = cv2.remap(tex, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
clouds = cv2.remap(cl, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
ca = np.clip(clouds[..., 3:4] * clouds[..., :3].mean(axis=2, keepdims=True) * 1.15, 0, 1) * 0.85
img = earth * (1 - ca) + ca * 0.97

# мягкое освещение слева-сверху и затемнение к краю диска
L = np.array([-0.45, 0.35, 0.82]); L /= np.linalg.norm(L)
lam = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)
shade = 0.35 + 0.75 * lam ** 0.8
img = img * shade[..., None] * (0.85 + 0.15 * z[..., None])
# голубая дымка атмосферы у края
haze = (1 - z) ** 2.2
img = img * (1 - 0.45 * haze[..., None]) + np.array([0.55, 0.72, 1.0]) * 0.45 * haze[..., None]
img = np.clip(img, 0, 1)

# альфа: диск + тонкое свечение снаружи
rr = np.sqrt(r2)
alpha = np.where(inside, 1.0, np.clip(1 - (rr - 1) / pad, 0, 1) ** 3 * 0.55)
glow = np.array([0.62, 0.76, 1.0])
out = np.where(inside[..., None], img, glow)
aa = np.clip((1 - rr) * N / 2, 0, 1)        # сглаживание края диска
alpha = np.where(inside, np.maximum(aa, alpha * 0 + aa), alpha)
alpha = np.where(inside, 1.0, alpha)
rgba = np.dstack([out, alpha])
Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA').save('earth.png', optimize=True)
print('ok')
