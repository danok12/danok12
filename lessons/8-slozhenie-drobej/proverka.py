"""Проверка ответов: исходное выражение и ответ сравниваются в 400 случайных
рациональных точках точной арифметикой (Fraction). Точки, где знаменатель
обращается в ноль, пропускаются."""
from fractions import Fraction as F
import random

random.seed(1)

def pts(n):
    for _ in range(400):
        yield [F(random.randint(-60, 60), random.randint(1, 9)) for _ in range(n)]

def same(name, lhs, rhs, n=1):
    ok = 0
    for p in pts(n):
        try:
            a, b = lhs(*p), rhs(*p)
        except ZeroDivisionError:
            continue
        assert a == b, (name, p, a, b)
        ok += 1
    assert ok > 300, (name, ok)
    print(f"ok  {name:10} ({ok} точек)")

# ---------- домашнее задание: № 86 ----------
same("86а", lambda b, c: (b-c)/b + b/(b+c),          lambda b, c: (2*b*b - c*c)/(b*(b+c)), 2)
same("86б", lambda x: (x+1)/(x-2) - (x+3)/x,         lambda x: F(6)/(x*(x-2)))
same("86в", lambda m, n: m/(m-n) - n/(m+n),          lambda m, n: (m*m + n*n)/(m*m - n*n), 2)
same("86г", lambda a: 2*a/(2*a-1) - 1/(2*a+1),       lambda a: (4*a*a+1)/(4*a*a-1))
same("86д", lambda a: a/(a+2) - a/(a-2),             lambda a: -4*a/(a*a-4))
same("86е", lambda p: p/(3*p-1) - p/(1+3*p),         lambda p: 2*p/(9*p*p-1))
# ---------- домашнее задание: № 96 ----------
same("96а", lambda a: (a+4)/(a*a-2*a) - a/(a*a-4),   lambda a: (6*a+8)/(a*(a-2)*(a+2)))
same("96б", lambda x: (4-x*x)/(16-x*x) - (x+1)/(x+4), lambda x: 3*x/(x*x-16))
same("96в", lambda a, b: (a+b)**2/(a*a+a*b) + (a-b)**2/(a*a-a*b), lambda a, b: F(2) + 0*a/(a*a-b*b), 2)
same("96г", lambda x: (x*x-4)/(5*x-10) - (x*x+4*x+4)/(5*x+10), lambda x: F(0) + 0/(x*x-4))

# ---------- аналоги ----------
A = [
 ("А1",  lambda a: (a+2)/a - a/(a+3),                 lambda a: (5*a+6)/(a*(a+3))),
 ("А2",  lambda y: (y-1)/(y+3) - (y-4)/y,             lambda y: F(12)/(y*(y+3))),
 ("А3",  lambda c: 3*c/(3*c-2) - 2/(3*c+2),           lambda c: (9*c*c+4)/(9*c*c-4)),
 ("А4",  lambda b: b/(b-5) - b/(b+5),                 lambda b: 10*b/(b*b-25)),
 ("А5",  lambda q: q/(2*q-3) - q/(3+2*q),             lambda q: 6*q/(4*q*q-9)),
 ("А6",  lambda k: k/(2*k-1) + k/(1-2*k),             lambda k: F(0) + 0/(2*k-1)),
 ("А7",  lambda b: (b+3)/(b*b-3*b) - b/(b*b-9),       lambda b: (6*b+9)/(b*(b*b-9))),
 ("А8",  lambda y: (9-y*y)/(25-y*y) - (y+2)/(y+5),    lambda y: (3*y+1)/(y*y-25)),
 ("А10", lambda c: (c*c-1)/(3*c+3) + (c*c-2*c+1)/(3*c-3), lambda c: 2*(c-1)/3 + 0/(c*c-1)),
 ("А11", lambda m: 2*m/(m*m-4) - 1/(m-2),             lambda m: 1/(m+2) + 0/(m-2)),
 ("А12", lambda x: (x+5)/(x*x-5*x) - (x-5)/(x*x+5*x), lambda x: 20/(x*x-25) + 0/x),
]
for name, l, r in A:
    same(name, l, r)
same("А9", lambda x, y: (x+y)**2/(x*x+x*y) - (x-y)**2/(x*x-x*y), lambda x, y: 2*y/x + 0/(x*x-y*y), 2)
same("А13", lambda a, b: 1/(a*a-a*b) + 1/(a*b-b*b), lambda a, b: (a+b)/(a*b*(a-b)), 2)

# ---------- «найди ошибку»: неверные ответы действительно неверны ----------
def differs(name, lhs, wrong, n=1):
    for p in pts(n):
        try:
            if lhs(*p) != wrong(*p):
                print(f"ok  {name:10} неверный ответ отличается, например в {[str(v) for v in p]}")
                return
        except ZeroDivisionError:
            continue
    raise AssertionError(name)

differs("Ош1", lambda y: (y-1)/(y+3) - (y-4)/y, lambda y: (-2*y-12)/(y*(y+3)))
differs("Ош2", lambda b: b/(b-5) - b/(b+5),     lambda b: F(0) + 0/(b*b-25))
differs("Ош3", lambda k: k/(2*k-1) + k/(1-2*k), lambda k: 2*k/(2*k-1))
differs("Ош4", lambda a: (5*a+6)/(a*(a+3)),     lambda a: F(11)/(a+3))
differs("Ош5", lambda x, y: (x+y)**2/(x*x+x*y), lambda x, y: (x*x+y*y)/(x*(x+y)), 2)

# числа для «проверки подстановкой» в тексте страницы
v = lambda a: (a+4)/(a*a-2*a) - a/(a*a-4)
print("96а при a=3:", v(F(3)), " ответ:", (6*3+8)/F(3*1*5))
v = lambda x: (x+1)/(x-2) - (x+3)/x
print("86б при x=3:", v(F(3)), " ответ:", F(6)/(3*1))
