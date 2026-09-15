#!/usr/bin/env python3
"""Собирает артборд ResultB.dc.html из реальной выдачи API, без ручных цифр."""
import json, urllib.request

FIELDS = ["09.00.00", "38.00.00", "40.00.00", "31.00.00", "45.00.00"]
SHORT = {"09.00.00": "Информатика и ВТ", "38.00.00": "Экономика и управление",
         "40.00.00": "Юриспруденция", "31.00.00": "Клиническая медицина",
         "45.00.00": "Языкознание"}
COL = {"tech": "Тех", "nat": "Ест", "soc": "Соц", "hum": "Гум", "uni": "Ун"}
ORDER = ["tech", "nat", "soc", "hum", "uni"]

req = urllib.request.Request("http://localhost:8080/api/match",
    data=json.dumps({"class_code": "9A-114", "fields": FIELDS, "extra_subjects": []}).encode(),
    headers={"content-type": "application/json"})
data = json.load(urllib.request.urlopen(req))
prof = {p["profile_id"]: p for p in data["profiles"]}
best = data["profiles"][0]

FULL = '<span style="width: 16px; height: 16px; background: #2e7d6b;"></span>'
PART = '<span style="width: 16px; height: 16px; background: linear-gradient(90deg, #b5792e 50%, #ece6dc 50%);"></span>'
NONE = '<span style="width: 16px; height: 16px; border: 1.5px solid #d6cec1;"></span>'
MARK = {"full": FULL, "partial": PART, "none": NONE}
SEP = '        <div style="grid-column: 1 / -1; height: 1px; background: #e2dcd2;"></div>\n'

rows = []
for code in FIELDS:
    rows.append(SEP)
    rows.append(f'        <div style="font-size: 13px;">{SHORT[code]}</div>\n')
    for pid in ORDER:
        cell = {f["code"]: f for f in prof[pid]["fields"]}[code]["status"]
        rows.append(f'        <div style="display: flex; justify-content: center;">{MARK[cell]}</div>\n')
matrix = "".join(rows)
totals = "".join(
    f'        <div style="font-size: 15px; font-weight: 700; text-align: center;">{prof[p]["available"]}</div>\n'
    for p in ORDER)
heads = "".join(
    f'        <div style="font-size: 12px; font-weight: 700; text-align: center;">{COL[p]}</div>\n'
    for p in ORDER)

advice = best["advice"]
names = {s["id"]: s["name"].lower() for s in data["subjects"]}
add = " и ".join(names[a] for a in advice["add"])
note = (f'Лучший результат — «{best["profile_name"].lower()}». Ему не хватает {add}: '
        f'добрав их элективом, вы вернёте направлений — {advice["gain"]}. '
        f'Клиническая медицина требует сразу химию и биологию, поэтому её сохраняет '
        f'только естественно-научный профиль.')

html = f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&amp;display=swap">
  <style>
    body {{ margin: 0; }}
    a {{ color: #2e7d6b; }} a:hover {{ color: #23604f; }}
  </style>
</helmet>
<div style="width: 390px; height: 844px; position: relative; overflow: hidden; background: #f6f3ee; color: #16211f; font-family: 'Golos Text', 'PT Sans', -apple-system, 'Segoe UI', sans-serif; font-size: 16px; line-height: 1.45;">

  <div style="background: #13262b; color: #f6f3ee; padding: 20px 18px 18px; display: flex; flex-direction: column; gap: 8px;">
    <span style="font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; color: #8fa5a3;">Шаг 2 из 2 · 5 направлений</span>
    <div style="display: flex; align-items: flex-end; gap: 12px;">
      <div style="font-size: 44px; font-weight: 700; line-height: 1; letter-spacing: -0.03em;">{best["available"]}<span style="font-size: 26px; color: #8fa5a3;"> из {best["total"]}</span></div>
      <div style="font-size: 14px; color: #b9c6c3; padding-bottom: 4px;">сохраняет лучший профиль —<br><b style="color: #f6f3ee;">{best["profile_name"].lower()}</b></div>
    </div>
    <div style="font-size: 13px; color: #b9c6c3;">Ни один профиль школы не сохраняет все пять направлений. Ниже видно, что именно теряется.</div>
  </div>

  <div style="padding: 16px 18px 0; display: flex; flex-direction: column; gap: 12px;">

    <div style="background: #ffffff; border: 1px solid #e2dcd2; border-radius: 4px; padding: 14px 12px 12px;">
      <div style="display: grid; grid-template-columns: 148px repeat(5, minmax(0, 1fr)); gap: 6px; align-items: center;">
        <div style="font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; color: #6c736e;">Направление</div>
{heads}{matrix}{SEP}        <div style="font-size: 12px; font-weight: 600; color: #6c736e;">Сохраняет</div>
{totals}      </div>

      <div style="display: flex; flex-wrap: wrap; gap: 12px; padding-top: 12px; font-size: 11px; color: #6c736e;">
        <span style="display: flex; align-items: center; gap: 5px;">{FULL.replace("16px", "11px")}все вузы</span>
        <span style="display: flex; align-items: center; gap: 5px;">{PART.replace("16px", "11px")}часть вузов</span>
        <span style="display: flex; align-items: center; gap: 5px;">{NONE.replace("16px", "11px")}недоступно</span>
      </div>
    </div>

    <div style="background: #ffffff; border-left: 3px solid #b5792e; border-top: 1px solid #e2dcd2; border-right: 1px solid #e2dcd2; border-bottom: 1px solid #e2dcd2; border-radius: 4px; padding: 13px 14px; display: flex; flex-direction: column; gap: 5px;">
      <div style="font-size: 14px; font-weight: 700;">Что вернёт потерянное</div>
      <div style="font-size: 14px;">{note}</div>
    </div>

    <div style="display: flex; align-items: center; justify-content: center; height: 54px; border-radius: 4px; background: #13262b; color: #ffffff; font-size: 16px; font-weight: 600;">Отправить разбор в чат</div>

  </div>
</div>
</x-dc>
</body>
</html>
'''
open("ResultB.dc.html", "w", encoding="utf-8").write(html)
print("ResultB.dc.html собран из живой выдачи API")
print("лидер:", best["profile_name"], best["available"], "/", best["total"])
print("итоги по профилям:", {p: prof[p]["available"] for p in ORDER})
