from fractions import Fraction as F
from math import isqrt
def solve_lin(f):
    # f linear in x: f(x)=0 ; solve via two points
    a=f(F(1))-f(F(0)); b=f(F(0)); return -b/a
def quad(a,b,c):
    D=b*b-4*a*c
    if D<0: return D,[]
    r=isqrt(int(D)) if F(D).denominator==1 else None
    assert r is not None and r*r==D, ("D not square",D)
    return D,sorted({F(-b+r,2*a),F(-b-r,2*a)})
R={}
# 1 три числа
x=solve_lin(lambda x: x+(x+5)+2*x-61); R[1]=(x,x+5,2*x)
# 2 возраст
x=solve_lin(lambda x: (x+26+4)-3*(x+4)); R[2]=x; assert x+30==3*(x+4)
# 3 тетради и ручки
x=solve_lin(lambda x: 3*x+2*(x+15)-230); R[3]=(x,x+15)
# 4 навстречу
x=solve_lin(lambda x: 2*(x+x+4)-72); R[4]=(x,x+4)
# 5 догонялки, часы -> минуты
t=solve_lin(lambda t: 5*(t+F(3,2))-14*t); R[5]=(t,t*60)
# 6 река
x=solve_lin(lambda x: 3*(x+2)+4*(x-2)-152); R[6]=x
# 7 бригады
t=solve_lin(lambda t: t/10+t/15-1); R[7]=t
# 8 проценты
x=solve_lin(lambda x: x*F(12,10)*F(8,10)-960); R[8]=x
# 9 разбавление
x=solve_lin(lambda x: F(6,100)*(30+x)-3); R[9]=x
# 10 сплавы
x=solve_lin(lambda x: F(2,10)*x+F(5,10)*(30-x)-F(4,10)*30); R[10]=(x,30-x)
# 11 средняя скорость
S=F(1); R[11]=2*S/(S/60+S/90)
# 12 два рабочих
t=solve_lin(lambda t: F(3,12)+t*(F(1,12)+F(1,24))-1); R[12]=t
# 13 поезд
x=solve_lin(lambda x: x/15-(x+450)/F(45)); R[13]=(x,x/15,x/15*F(36,10))
for k,v in R.items(): print(k,v)
# ошибки
print("err A wrong:", solve_lin(lambda t: 5*(t+30)-14*t), "right(h):", solve_lin(lambda t: 5*(t+F(1,2))-14*t)*60,"min")
print("err B:", solve_lin(lambda x: F(8,10)*x-800), "wrong", 800*F(12,10))
print("err C:", solve_lin(lambda x: 3*(x+x+6)-102))
# квадратные
print("demo", quad(1,-5,-14))
for e in [(1,-8,15),(2,1,-6),(1,-6,9)]: print("warm",e,quad(*e))
# разбор: 72 км, +6, на 1 ч меньше -> x^2+6x-432=0
D,r=quad(1,6,-432); print("razbor",D,r); x=max(r); assert F(72)/x-F(72)/(x+6)==1; print(72/x,72/(x+6))
# попробуй: 180 км, +15, на 1 ч раньше -> x^2+15x-2700=0
D,r=quad(1,15,-2700); print("try",D,r); x=max(r); assert F(180)/x-F(180)/(x+15)==1; print(x+15,180/x,180/(x+15))
