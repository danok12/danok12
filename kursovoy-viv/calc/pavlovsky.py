# Безнапорный поток в круглой трубе по формуле Шези с коэффициентом Павловского
# (на этой основе построены таблицы Лукиных). Проверка: условие незасоряемости V*sqrt(h/d) >= K.
# НЕ СВЕРЕНО с таблицами Лукиных: значения n по материалам ниже — предположение.
# До сверки с несколькими страницами книги в записку цифры отсюда не писать.
import math
def section(d, hd):
    th = 2*math.acos(1-2*hd)               # центральный угол смоченной части
    w = d*d/8*(th-math.sin(th)); chi = d*th/2
    return w, w/chi
def flow(d_mm, i, hd, n):
    d = d_mm/1000; w, R = section(d, hd)
    y = 2.5*math.sqrt(n)-0.13-0.75*math.sqrt(R)*(math.sqrt(n)-0.10)
    C = R**y/n; v = C*math.sqrt(R*i)
    return v, v*w*1000                      # м/с, л/с
if __name__ == "__main__":
    for d, n in [(100, 0.013), (150, 0.014), (200, 0.014)]:
        for i in (0.008, 0.02, 0.03):
            for hd in (0.3, 0.5, 0.6):
                v, q = flow(d, i, hd, n)
                print(f"d={d} n={n} i={i} h/d={hd}: V={round(v,3)} м/с, q={round(q,3)} л/с, V*sqrt(h/d)={round(v*math.sqrt(hd),3)}")
