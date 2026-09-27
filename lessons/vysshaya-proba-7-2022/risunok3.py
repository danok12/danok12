"""Рисунок к задаче 3: A = 18°, B = 70°, C = 92°; M, N, K — точки касания вписанной окружности."""
from math import radians, sin, cos, atan2, degrees, hypot, pi

A_, B_, C_ = 18, 70, 92
c = 1.0                                   # AB
b = c * sin(radians(B_)) / sin(radians(C_))   # AC
a = c * sin(radians(A_)) / sin(radians(C_))   # BC
A = (0.0, 0.0); B = (c, 0.0); C = (b * cos(radians(A_)), b * sin(radians(A_)))
s = (a + b + c) / 2
def along(P, Q, t):
    d = hypot(Q[0] - P[0], Q[1] - P[1]); return (P[0] + (Q[0] - P[0]) * t / d, P[1] + (Q[1] - P[1]) * t / d)
M = along(A, B, s - a); K = along(A, C, s - a); N = along(B, C, s - b)
I = ((a * A[0] + b * B[0] + c * C[0]) / (2 * s), (a * A[1] + b * B[1] + c * C[1]) / (2 * s))
r = (s - a) * (s - b) * (s - c) / s; r = r ** 0.5

def ang(P, Q, R):  # угол QPR
    u = atan2(Q[1] - P[1], Q[0] - P[0]); v = atan2(R[1] - P[1], R[0] - P[0])
    d = (degrees(v - u)) % 360; return min(d, 360 - d)
chk = {'MNK': ang(N, M, K), 'NKM': ang(K, N, M), 'KMN': ang(M, K, N)}
assert abs(chk['MNK'] - 81) < 1e-9 and abs(chk['NKM'] - 55) < 1e-9 and abs(chk['KMN'] - 44) < 1e-9, chk
assert abs(hypot(M[0]-A[0], M[1]-A[1]) - hypot(K[0]-A[0], K[1]-A[1])) < 1e-12

W, H, S, PAD = 1100, 470, 980, 60
def T(P): return (PAD + P[0] * S, H - 60 - P[1] * S)
def line(P, Q, w=2, dash=''):
    (x1, y1), (x2, y2) = T(P), T(Q)
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#000" stroke-width="{w}" {dash}/>'
def label(P, text, dx, dy, size=26, style='italic'):
    x, y = T(P); return f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" font-size="{size}" font-style="{style}">{text}</text>'
def ticks(P, Q, n):
    mx, my = (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2
    (x1, y1), (x2, y2) = T(P), T(Q); L = hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L; nx, ny = -uy, ux
    cx, cy = T((mx, my)); out = []
    for k in range(n):
        off = (k - (n - 1) / 2) * 7
        px, py = cx + ux * off, cy + uy * off
        out.append(f'<line x1="{px-nx*9:.1f}" y1="{py-ny*9:.1f}" x2="{px+nx*9:.1f}" y2="{py+ny*9:.1f}" stroke="#000" stroke-width="2"/>')
    return ''.join(out)
def arc(P, Q, R, rad, text, tdist, size=20):
    """Дуга угла QPR (в экранных координатах) с подписью."""
    (px, py), (qx, qy), (rx, ry) = T(P), T(Q), T(R)
    u = atan2(qy - py, qx - px); v = atan2(ry - py, rx - px)
    d = (v - u) % (2 * pi)
    if d > pi: u, v, d = v, u, 2 * pi - d
    x1, y1 = px + rad * cos(u), py + rad * sin(u); x2, y2 = px + rad * cos(u + d), py + rad * sin(u + d)
    m = u + d / 2; tx, ty = px + tdist * cos(m), py + tdist * sin(m)
    return (f'<path d="M{x1:.1f},{y1:.1f} A{rad},{rad} 0 0 1 {x2:.1f},{y2:.1f}" fill="none" stroke="#000" stroke-width="1.5"/>'
            f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="{size}" text-anchor="middle" dominant-baseline="middle">{text}</text>')

ix, iy = T(I)
parts = [
    f'<circle cx="{ix:.1f}" cy="{iy:.1f}" r="{r*S:.1f}" fill="none" stroke="#888" stroke-width="1.5" stroke-dasharray="6 5"/>',
    line(A, B, 2.5), line(B, C, 2.5), line(C, A, 2.5),
    line(M, N), line(N, K), line(K, M),
    ticks(A, M, 1), ticks(A, K, 1), ticks(B, M, 2), ticks(B, N, 2), ticks(C, N, 3), ticks(C, K, 3),
    arc(A, B, C, 120, '18°', 150),
    arc(B, A, C, 45, '70°', 72),
    arc(C, A, B, 30, '92°', 55),
    arc(N, M, K, 34, '81°', 58),
    arc(K, N, M, 38, '55°', 62),
    arc(M, K, N, 44, '44°', 68),
    label(A, 'A', -32, 10), label(B, 'B', 10, 12), label(C, 'C', -8, -14),
    label(M, 'M', -10, 32), label(N, 'N', 12, -2), label(K, 'K', -14, -14),
]
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Times New Roman, serif"><rect width="100%" height="100%" fill="#fff"/>{"".join(parts)}</svg>'
open('risunok3.svg', 'w').write(svg)
print('ok', {k: round(v, 6) for k, v in chk.items()}, 'C=', T(C))
