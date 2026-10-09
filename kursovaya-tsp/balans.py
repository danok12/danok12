"""Курсовая по ТСП, вариант 2: сводный баланс грунта (п. 2.2.3 методички, табл. 2).

1. Баланс по черновику: выемка = ΣVв.геом (призмы и откосы) + Vк;
   насыпь = ΣVн.геом + засыпка съезда Vс (пазухи засыпаются привозным песком -
   грунт площадки на них не идёт); сравнение - с Vн / kо.р.
2. Расхождение больше 5 % - поправка Δh = Vлиш.(нед.)гр / Fпл; Fпл - площадь
   площадки без площади котлована по верху, если котлован в насыпи. «−» - понижение.
3. Все рабочие отметки сдвигаются на Δh, заново - ЛНР, объёмы планировки, котлован
   (он в насыпи) и баланс.
Δh - с точностью 0,0001 м, как в задании на этап (−0,0604).
"""
from fractions import Fraction as Fr
import raschet as R
import kotlovan as K

K_OR = Fr("1.04")                     # супесь, прил. 2: 1,03-1,05; принято 1,04
F_PL = R.A * R.A * R.NX * R.NY        # площадь площадки, м2


def balance(P, k):
    """Таблица 2 для состояния планировки P и котлована k."""
    b = {"VV_PL": P["VV"], "VN_PL": P["VN"], "V_K": k["V_K"], "V_S": k["V_S"]}
    b["SUM_V"] = float(P["VV"]) + k["V_K"]
    b["SUM_N"] = float(P["VN"] + k["V_S"])
    b["SUM_NK"] = float(P["VN"] / K_OR + k["V_S"] / K_OR)
    b["BALANCE"] = b["SUM_V"] - b["SUM_NK"]                 # «−» - грунта не хватает
    b["PCT"] = abs(b["BALANCE"]) / max(b["SUM_V"], b["SUM_NK"]) * 100
    b["OK"] = b["PCT"] <= 5
    b["F_PL"] = F_PL - (k["F_KV"] if k["IN_FILL"] else 0)
    b["DH_EXACT"] = b["BALANCE"] / float(b["F_PL"])
    b["DH"] = Fr(round(b["DH_EXACT"], 4)).limit_denominator(10 ** 4)
    return b


B0 = balance(R.P0, K.K0)
DH = B0["DH"]
H1 = [hv + DH for hv in R.H]          # окончательные рабочие отметки
P1 = R.compute(H1)
K1 = K.pit(P1)
B1 = balance(P1, K1)


def f(v, n=2):
    return f"{round(float(v), n):,.{n}f}".replace(",", " ").replace(".", ",")


def report(b, title):
    print(title)
    print(f"  В призмах и откосах: Vв = {f(b['VV_PL'])}  Vн = {f(b['VN_PL'])}  Vн/kор = {f(b['VN_PL'] / K_OR)}")
    print(f"  В котловане:         Vк = {f(b['V_K'])}  засыпка съезда Vс = {f(b['V_S'])}  Vс/kор = {f(b['V_S'] / K_OR)}")
    print(f"  Суммарно:            Vв = {f(b['SUM_V'])}  Vн = {f(b['SUM_N'])}  Vн/kор = {f(b['SUM_NK'])}")
    print(f"  Баланс Vв - Vн/kор = {f(b['BALANCE'])} м3 ({f(b['PCT'])} %) -> "
          + ("в пределах 5 %" if b["OK"] else "больше 5 %, нужна поправка"))
    print(f"  Fпл = {f(b['F_PL'])} м2;  Δh = {b['DH_EXACT']:.6f} -> {float(b['DH']):.4f} м")


if __name__ == "__main__":
    report(B0, "Сводный баланс по черновику")
    print(f"Поправка Δh = {float(DH):+.4f} м ко всем рабочим отметкам")
    print("Окончательные отметки:", [f"{float(v):+.4f}" for v in H1])
    print("Точки нулевых работ:", len(P1["ZP"]), " фигур:", len(P1["FIGS"]))
    K.report(K1, "Котлован по окончательным отметкам")
    report(B1, "Сводный баланс по окончательным отметкам")
