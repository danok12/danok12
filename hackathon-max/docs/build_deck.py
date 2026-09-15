#!/usr/bin/env python3
"""Собирает презентацию решения: docs/presentation.html (готов к печати в PDF).

Скриншоты встраиваются в base64, внешних шрифтов нет — файл самодостаточен
и печатается Chromium без сети (см. раздел «Сборка PDF» в CLAUDE.md).
"""
import base64
from pathlib import Path

DOCS = Path(__file__).resolve().parent


def img(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((DOCS / "img" / name).read_bytes()).decode()


CSS = """
:root{
  --ink:#12242b; --paper:#fbfaf8; --surface:#ffffff; --line:#e2dcd2;
  --text:#16211f; --muted:#69726f; --teal:#2e7d6b; --amber:#b5792e; --red:#a4462f;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#3a4246;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
  color:var(--text);-webkit-font-smoothing:antialiased}
.slide{position:relative;width:1280px;height:720px;margin:0 auto 24px;background:var(--paper);
  overflow:hidden;padding:50px 64px 56px;display:flex;flex-direction:column;gap:16px}
.slide.dark{background:var(--ink);color:#f2efe9}
.kicker{font-size:14px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:600}
.dark .kicker{color:#8fa5a3}
h1{font-size:54px;line-height:1.08;letter-spacing:-.025em;margin:0;font-weight:700}
h2{font-size:34px;line-height:1.15;letter-spacing:-.02em;margin:0;font-weight:700}
h3{font-size:19px;margin:0 0 6px;font-weight:700}
p,li{font-size:18px;line-height:1.45;margin:0}
.lead{font-size:22px;line-height:1.4;color:var(--muted);max-width:62ch}
.dark .lead{color:#b9c6c3}
ul{margin:0;padding-left:22px;display:flex;flex-direction:column;gap:9px}
ul.tight li{font-size:17px}
.cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;flex:1;min-height:0}
.cols3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;flex:1;min-height:0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:20px 22px;
  display:flex;flex-direction:column;gap:9px}
.card.accent{border-left:4px solid var(--teal)}
.card.warn{border-left:4px solid var(--amber)}
.card.muted{background:#f2eee8}
.dark .card{background:#1b3239;border-color:#2c454c;color:#f2efe9}
.tag{display:inline-block;font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--teal);margin-bottom:2px}
.tag.amber{color:var(--amber)}
.big{font-size:46px;font-weight:700;letter-spacing:-.03em;line-height:1}
.num{font-size:34px;font-weight:700;letter-spacing:-.02em;color:var(--teal)}
.muted{color:var(--muted)}
.dark .muted{color:#b9c6c3}
.small{font-size:15px;line-height:1.4}
.xsmall{font-size:13px;line-height:1.4;color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:16px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
td.c{text-align:center;font-size:18px}
.phone{height:100%;width:auto;border:1px solid var(--line);border-radius:10px;display:block}
.shots{display:flex;gap:18px;align-items:stretch;flex:1;min-height:0}
.foot{position:absolute;left:64px;right:64px;bottom:22px;display:flex;justify-content:space-between;
  font-size:12px;color:var(--muted)}
.dark .foot{color:#7e9391}
.flow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.step{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:11px 14px;font-size:15px}
.arrow{color:var(--muted);font-size:17px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:16px}
.kv b{white-space:nowrap}
.legend{display:flex;gap:16px;font-size:14px;color:var(--muted);flex-wrap:wrap}
.sq{display:inline-block;width:12px;height:12px;vertical-align:-1px;margin-right:5px}
.sq.f{background:var(--teal)}
.sq.p{background:linear-gradient(90deg,var(--amber) 50%,#e8e2d8 50%)}
.sq.n{border:1.5px solid #d6cec1}
@page{size:13.333in 7.5in;margin:0}
@media print{
  html,body{background:#fff}
  .slide{margin:0;break-after:page;break-inside:avoid;box-shadow:none}
  .slide:last-child{break-after:auto}
  .card,tr,li{break-inside:avoid}
  h1,h2,h3{break-after:avoid}
}
"""


def slide(n, total, body, dark=False, title="Профиль 10"):
    cls = "slide dark" if dark else "slide"
    return (f'<section class="{cls}">{body}'
            f'<div class="foot"><span>{title}</span><span>{n} / {total}</span></div></section>')


SLIDES = []

# 1 — служебный
SLIDES.append("""
<div class="kicker">Служебный слайд · не оценивается</div>
<h2>Техническая информация для проверки</h2>
<div class="cols" style="gap:20px">
  <div class="card">
    <h3>Доступ к решению</h3>
    <div class="kv small">
      <b>Чат-бот в MAX</b><span>[ССЫЛКА НА БОТА] — ник выдаётся вместе с токеном</span>
      <b>Мини-приложение</b><span>[PUBLIC_BASE_URL]/app/ — открывается кнопкой из бота</span>
      <b>Роль школы</b><span>[PUBLIC_BASE_URL]/app/?role=curator</span>
      <b>API</b><span>[PUBLIC_BASE_URL]/api · Swagger: /docs</span>
      <b>Репозиторий</b><span>[ССЫЛКА НА РЕПОЗИТОРИЙ], commit [COMMIT HASH]</span>
    </div>
    <p class="xsmall">Значения MAX_BOT_TOKEN, APP_SECRET и INTERNAL_KEY передаются отдельно: рабочие секреты в репозиторий не коммитятся.</p>
    <p class="xsmall">Команда TeamRoulette № 870. Контакт по вопросам проверки: [ИМЯ, ТЕЛЕФОН ИЛИ ПОЧТА].</p>
  </div>
  <div class="card">
    <h3>Тестовые данные (персональных данных нет)</h3>
    <div class="kv small">
      <b>Коды классов</b><span>9A-114, 9B-114 (Лицей № 114, Казань); 9A-ALM7 (СОШ № 7, Альметьевск)</span>
      <b>Коды кураторов</b><span>KUR-114-9A, KUR-114-9B, KUR-ALM7-9A</span>
    </div>
    <h3 style="margin-top:6px">Порядок проверки основного сценария</h3>
    <ul class="tight">
      <li>Открыть бота → «Начать» → отправить <b>9A-114</b>.</li>
      <li>Выбрать исходный профиль → «Открыть подбор».</li>
      <li>Отметить 09.00.00, 38.00.00, 40.00.00, 31.00.00, 45.00.00 → «Сравнить профили».</li>
      <li>Нажать чип «+ Обществознание» — покрытие пересчитывается.</li>
      <li>Выбрать профиль → карточка разбора приходит в чат.</li>
    </ul>
  </div>
</div>
""")

# 2 — титул
SLIDES.append("""
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:22px">
  <div class="kicker" style="color:#8fa5a3">Трек «Образовательные решения» · чат-бот и мини-приложение в MAX</div>
  <h1>Профиль 10</h1>
  <p class="lead" style="max-width:56ch">Показывает девятикласснику, какие направления в вузах останутся ему
  доступны при каждом профиле его школы — и какой один предмет вернёт то, что закрывается.</p>
  <div style="display:flex;gap:56px;margin-top:10px">
    <div><div class="kicker" style="color:#8fa5a3">Команда</div>
      <p style="color:#f2efe9">TeamRoulette · №&thinsp;870</p></div>
    <div><div class="kicker" style="color:#8fa5a3">Состав</div>
      <p style="color:#f2efe9">Константин Антуганов · Даниил Буев · Трофим Горский · Борислав Бондарев</p></div>
  </div>
</div>
""", )

# 3 — executive summary
SLIDES.append("""
<div class="kicker">Резюме проекта</div>
<h2>Решение в одном экране</h2>
<div class="cols3" style="gap:16px">
  <div class="card accent">
    <span class="tag">Кто</span>
    <h3>Ученик 9 класса</h3>
    <p class="small">Школа с индивидуальным отбором в профильные 10-е классы. Период — с февраля до срока подачи заявления.</p>
  </div>
  <div class="card accent">
    <span class="tag">Что не так</span>
    <h3>Цепочка не собрана</h3>
    <p class="small">Профиль → углублённые предметы → ЕГЭ → перечень испытаний → направление. Каждое звено доступно, вся цепочка — нигде.</p>
  </div>
  <div class="card accent">
    <span class="tag">Что делаем</span>
    <h3>Считаем цену выбора</h3>
    <p class="small">За 3–5 минут в чате MAX: сколько интересных направлений сохраняет каждый профиль, что закрывается и что добрать элективом.</p>
  </div>
</div>
<div class="cols" style="flex:none">
  <div class="card muted" style="padding:14px 18px">
    <p class="small"><b>Результат для ученика.</b> Карточка разбора в чате: что закрывается, почему и что спросить в школе — плюс напоминание о сроке.</p>
  </div>
  <div class="card muted" style="padding:14px 18px">
    <p class="small"><b>Результат для школы.</b> Обезличенный агрегат: какие запросы класса не закрывает ни один профиль и какой электив вернёт больше всего.</p>
  </div>
</div>
""")

# 4 — аудитория и проблема
SLIDES.append("""
<div class="kicker">Целевая аудитория и проблема</div>
<h2>Кто именно и в какой момент</h2>
<div class="cols">
  <div style="display:flex;flex-direction:column;gap:14px">
    <div class="card">
      <span class="tag">Приоритетный сегмент</span>
      <p>Ученики <b>9 класса</b> школ, где в 10-е классы идёт индивидуальный отбор по профилям,
      и их родители. Пилотный контур — школы Республики Татарстан.</p>
      <p class="small muted">Не «школьники вообще»: сценарий существует только там, где у школы есть
      несколько профилей и заявление подаётся к конкретному сроку.</p>
    </div>
    <div class="card muted">
      <p class="small"><b>Почему не 11 класс.</b> В 11 классе набор предметов уже определён профилем.
      Решение, которое можно изменить, принимается в 9-м — там и точка воздействия.</p>
    </div>
  </div>
  <div class="card warn" style="justify-content:center">
    <span class="tag amber">Формулировка проблемы</span>
    <p style="font-size:21px;line-height:1.4">Ученик 9 класса <span class="muted">в ситуации</span>
    записи в профильный 10 класс <span class="muted">хочет</span> выбрать профиль, не потеряв интересные
    ему специальности, <span class="muted">но сталкивается с тем, что</span> связь «профиль → ЕГЭ →
    направление подготовки» нигде не собрана вместе, <span class="muted">из-за чего</span> выбирает по
    сверстникам и нагрузке, а цену решения узнаёт в 11 классе, когда менять поздно.</p>
  </div>
</div>
""")

# 5 — актуальность
SLIDES.append("""
<div class="kicker">Актуальность</div>
<h2>Что подтверждено, а что мы предполагаем</h2>
<div class="cols">
  <div class="card accent">
    <span class="tag">Подтверждённые факты</span>
    <ul class="tight">
      <li><b>18 млн школьников</b> в 38 тыс. школ в 2026/27 учебном году — каждый проходит развилку после 9 класса. <span class="muted">Минпросвещения России</span></li>
      <li>Единая модель профориентации в 2025/26 охватила <b>8,5 млн школьников</b>, 36 тыс. школ, 900 вузов. <span class="muted">Минпросвещения России</span></li>
      <li>Индивидуальный отбор в классы профильного обучения предусмотрен <b>Федеральным законом № 273-ФЗ</b>; порядок устанавливает субъект Российской Федерации.</li>
      <li>Профили и углублённые предметы задаёт <b>ФГОС среднего общего образования</b>; перечень вступительных испытаний — приказ Минобрнауки России.</li>
      <li>Коммуникация школы, родителей и учеников уже живёт в MAX: <b>около 35 млн пользователей</b> «Сферума», сервис интегрирован с MAX. <span class="muted">Минпросвещения России, VK</span></li>
    </ul>
  </div>
  <div class="card warn">
    <span class="tag amber">Наши допущения — проверяются в пилоте</span>
    <ul class="tight">
      <li>Значимая доля девятиклассников не связывает профиль с перечнем вступительных испытаний. <span class="muted">Проверка: опрос класса до расчёта.</span></li>
      <li>Увидев потери, часть учеников меняет первоначальный выбор. <span class="muted">Проверка: доля изменивших выбор — метрика продукта.</span></li>
      <li>Школе полезен агрегат по классу для решения об элективе. <span class="muted">Проверка: число решений, принятых на данных за пилот.</span></li>
      <li>Нормативные ссылки и перечень испытаний сверяются с действующей редакцией до запуска.</li>
    </ul>
    <p class="xsmall">Мы сознательно не приводим точных цифр «сколько учеников ошибается с профилем»:
    открытого источника такой статистики нет, а выдумывать её нельзя.</p>
  </div>
</div>
""")

# 6 — As Is / To Be
SLIDES.append("""
<div class="kicker">Текущий и будущий процесс</div>
<h2>As&nbsp;Is → To&nbsp;Be</h2>
<div class="cols">
  <div class="card">
    <span class="tag amber">Как происходит сейчас</span>
    <ul class="tight">
      <li>Школа объявляет список профилей и условия отбора в чате или на сайте.</li>
      <li>Ученик сопоставляет профиль с будущей специальностью сам: сайты вузов, перечни испытаний, форумы.</li>
      <li>Чаще сопоставление не происходит вовсе — решение принимается по сверстникам и нагрузке.</li>
      <li>Родитель узнаёт о последствиях, когда в 11 классе выясняется, что нужного ЕГЭ нет.</li>
      <li>Школа не видит, какие запросы класса её набор профилей не закрывает.</li>
    </ul>
    <p class="small muted">Время: часы разрозненного поиска или ноль. Результат: решение без информации.</p>
  </div>
  <div class="card accent">
    <span class="tag">Как будет</span>
    <ul class="tight">
      <li>Ученик открывает бота в MAX по коду класса — профили его школы подтягиваются автоматически.</li>
      <li>Отмечает интересные направления и получает сравнение всех профилей с объяснением потерь.</li>
      <li>Видит минимальное дополнение: какой предмет вернёт закрывшиеся направления.</li>
      <li>Карточка разбора уходит в чат — её видит родитель; к сроку приходит напоминание.</li>
      <li>Школа получает обезличенный агрегат и основание для решения об элективе.</li>
    </ul>
    <p class="small muted">Время: 3–5 минут. Результат: решение, которое ученик может объяснить.</p>
  </div>
</div>
""")

# 7 — решение, экраны
SLIDES.append(f"""
<div class="kicker">Решение и основной сценарий</div>
<h2>Что видит ученик</h2>
<div class="shots">
  <img class="phone" src="{img('screen-pick.png')}" alt="Экран выбора направлений">
  <img class="phone" src="{img('screen-result.png')}" alt="Экран сравнения профилей">
  <div style="display:flex;flex-direction:column;gap:12px;flex:1;min-width:0">
    <div class="card" style="padding:14px 16px">
      <h3>Что в чате, а что в мини-приложении</h3>
      <p class="small"><b>Чат-бот:</b> вход, код класса, исходное намерение, карточка разбора, напоминание о сроке.
      Короткие шаги и уведомления — там, где пользователь уже находится.</p>
      <p class="small"><b>Мини-приложение:</b> каталог из 32 направлений с поиском, сравнение пяти профилей,
      пересчёт по добранным предметам. Список и сравнение требуют отдельного экрана.</p>
    </div>
    <div class="card warn" style="padding:14px 16px">
      <h3>Ключевая механика</h3>
      <p class="small">Продукт отвечает не «куда тебе пойти», а <b>«что ты теряешь и что это вернёт»</b>.
      Каждое закрытое направление показано с причиной: какого именно предмета не хватает.</p>
    </div>
  </div>
</div>
""")

# 8 — как считает движок
SLIDES.append("""
<div class="kicker">Что внутри расчёта</div>
<h2>Пример: класс 9А, пять направлений</h2>
<div class="cols" style="gap:24px">
  <div class="card" style="padding:18px 20px;align-self:start">
    <table>
      <tr><th>Направление</th><th style="text-align:center">Тех</th><th style="text-align:center">Ест</th>
          <th style="text-align:center">Соц</th><th style="text-align:center">Гум</th><th style="text-align:center">Ун</th></tr>
      <tr><td>Информатика и ВТ</td><td class="c"><i class="sq p"></i></td><td class="c"><i class="sq p"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td></tr>
      <tr><td>Экономика и управление</td><td class="c"><i class="sq p"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq p"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td></tr>
      <tr><td>Юриспруденция</td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq p"></i></td><td class="c"><i class="sq n"></i></td></tr>
      <tr><td>Клиническая медицина</td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq f"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td></tr>
      <tr><td>Языкознание</td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq n"></i></td><td class="c"><i class="sq f"></i></td><td class="c"><i class="sq n"></i></td></tr>
      <tr><td><b>Сохраняет</b></td><td class="c"><b>2</b></td><td class="c"><b>2</b></td><td class="c"><b>1</b></td><td class="c"><b>2</b></td><td class="c"><b>0</b></td></tr>
    </table>
    <div class="legend" style="margin-top:10px">
      <span><i class="sq f"></i>доступны все вузы направления</span>
      <span><i class="sq p"></i>часть вузов</span>
      <span><i class="sq n"></i>недоступно</span>
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:14px">
    <div class="card accent">
      <h3>Как считается</h3>
      <p class="small">Направление доступно, если профиль закрывает все обязательные предметы испытаний
      и хотя бы один предмет из списка, который выбирает вуз. Отсюда три состояния, а не «да/нет»:
      вуз вправе выбрать предмет, которого у ученика нет.</p>
    </div>
    <div class="card warn">
      <h3>Минимальное дополнение</h3>
      <p class="small">Перебором наборов из одного и двух предметов находим самый дешёвый способ вернуть
      закрывшиеся направления. Для технологического профиля это обществознание и иностранный язык —
      они возвращают юриспруденцию и языкознание.</p>
    </div>
    <div class="card muted">
      <p class="small">Доли считаются точной арифметикой (обыкновенные дроби), проценты округляются,
      а не усекаются. Ядро расчёта не зависит от веба и покрыто тестами.</p>
    </div>
  </div>
</div>
""")

# 9 — эффект и метрики
SLIDES.append("""
<div class="kicker">Ожидаемый эффект</div>
<h2>Какую часть процесса меняем и чем это измерить</h2>
<div class="cols3" style="flex:none">
  <div class="card"><span class="num">3–5 мин</span><p class="small">вместо часов разрозненного поиска или его отсутствия — время получения сравнения. <span class="muted">Замеряется в продукте.</span></p></div>
  <div class="card"><span class="num">1 экран</span><p class="small">вместо обхода сайтов вузов и перечней испытаний — число источников, которые нужно свести вручную.</p></div>
  <div class="card"><span class="num">≥ 1 решение</span><p class="small">школы об элективе или группе, принятое на данных агрегата за пилот.</p></div>
</div>
<div class="card" style="flex:1">
  <h3>Метрики пилота</h3>
  <div class="cols" style="gap:24px">
    <ul class="tight">
      <li><b>Доля завершивших сценарий</b> от числа девятиклассников класса — целевое значение ≥ 60 %.</li>
      <li><b>Доля изменивших первоначальный выбор</b> профиля после расчёта — прокси-метрика осведомлённости; фиксируется до и после.</li>
      <li><b>Среднее число закрывающихся направлений</b> при первоначальном и при итоговом выборе.</li>
    </ul>
    <ul class="tight">
      <li><b>Доля дошедших до карточки в чате</b> — показатель того, что разбор доходит до родителя.</li>
      <li><b>Доля подавших заявление в срок</b> среди получивших напоминание.</li>
      <li><b>Число «непокрытых» запросов</b> класса — вход для управленческого решения школы.</li>
    </ul>
  </div>
  <p class="xsmall">Все метрики считаются по обезличенным событиям продукта. Гипотеза: если ученик увидит
  цену выбора до подачи заявления, доля решений, принятых без информации, снизится.</p>
</div>
""")

# 10 — архитектура
SLIDES.append("""
<div class="kicker">Архитектура</div>
<h2>Два сервиса, одна точка правды</h2>
<div class="cols" style="gap:24px">
  <div style="display:flex;flex-direction:column;gap:12px">
    <div class="card" style="padding:16px 18px">
      <h3>api — FastAPI, Python 3.11</h3>
      <p class="small">Справочники, расчётное ядро, анкеты, обезличенный агрегат, очередь исходящих сообщений,
      раздача мини-приложения. Хранилище — SQLite на томе.</p>
    </div>
    <div class="card" style="padding:16px 18px">
      <h3>bot — Python 3.11</h3>
      <p class="small">Диалог в MAX через Bot API (длинный опрос), запуск мини-приложения, доставка карточек
      и напоминаний. Своего состояния не хранит и слушающих портов не открывает.</p>
    </div>
    <div class="card" style="padding:16px 18px">
      <h3>мини-приложение — React 18 + Vite</h3>
      <p class="small">Каталог направлений, сравнение профилей, экран классного руководителя.
      Собирается в образ api и раздаётся по HTTPS.</p>
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:12px">
    <div class="card accent">
      <h3>Решения, которые держат систему</h3>
      <ul class="tight">
        <li><b>Очередь вместо входящего порта.</b> Мини-приложение просит API отправить карточку, API кладёт её в очередь, бот забирает и подтверждает доставку. Перезапуск бота не теряет сообщений, напоминание переживает рестарт.</li>
        <li><b>Бот без состояния.</b> Владелец данных — API, поэтому начатый сценарий продолжается после перезапуска контейнера.</li>
        <li><b>Платформенные детали MAX изолированы</b> в одном модуле-адаптере: изменения в API платформы правятся в одном файле.</li>
        <li><b>Тексты сообщений живут в API</b> — одна точка правды для формулировок.</li>
      </ul>
    </div>
    <div class="card muted">
      <p class="small">Запуск всех локальных компонентов — одной командой <b>docker compose up --build</b>.
      Отдельный профиль поднимает стенд-эмулятор Bot API MAX: сквозной сценарий проходится без доступа к платформе.</p>
    </div>
  </div>
</div>
""")

# 11 — данные и интеграции
SLIDES.append("""
<div class="kicker">Данные и интеграции</div>
<h2>Что реально, что модельно, что с персональными данными</h2>
<div class="cols">
  <div class="card">
    <h3>Интеграции</h3>
    <table>
      <tr><th>Что</th><th>Статус в MVP</th></tr>
      <tr><td>Bot API MAX и мини-приложение</td><td><b>реальная интеграция</b>, единственная внешняя зависимость</td></tr>
      <tr><td>Перечень вступительных испытаний</td><td><b>модельный справочник</b>: структура приказа, не официальная выгрузка</td></tr>
      <tr><td>Профили, классы и сроки школы</td><td><b>демонстрационные данные</b>; в пилоте вводит куратор или загрузка из региональной системы</td></tr>
    </table>
    <p class="xsmall">Пометка о происхождении данных отдаётся в каждом ответе API и видна пользователю
    в интерфейсе и в карточке. Мы не имитируем интеграции, которых нет.</p>
  </div>
  <div style="display:flex;flex-direction:column;gap:12px">
    <div class="card accent">
      <h3>Персональные данные</h3>
      <p class="small">Пользователи — несовершеннолетние, поэтому MVP не собирает ФИО, контакты, оценки и возраст.
      Хранятся идентификатор пользователя MAX, код класса, отмеченные направления и выбранный профиль.</p>
      <p class="small">Доступ ученика к своей анкете — по подписанному токену с ограниченным сроком;
      доступ школы — по отдельному коду куратора, токен привязан к конкретному классу.</p>
    </div>
    <div class="card warn">
      <h3>Агрегат для школы обезличен</h3>
      <p class="small">Разрезы открываются только начиная с пяти заполненных анкет в классе: по агрегату
      нельзя восстановить ответ конкретного ученика. Порог настраивается.</p>
    </div>
    <div class="card muted">
      <p class="small">Генеративные модели не используются: расчёт детерминированный, объяснимый
      и воспроизводимый — это принципиально для сценария, влияющего на решение семьи.</p>
    </div>
  </div>
</div>
""")

# 12 — масштабирование
SLIDES.append("""
<div class="kicker">Потенциал масштабирования</div>
<h2>Что переносится без изменений, а что придётся адаптировать</h2>
<div class="cols" style="flex:none">
  <div class="card accent">
    <span class="tag">Ядро продукта — не меняется</span>
    <ul class="tight">
      <li>Модель «набор углублённых предметов → допустимые испытания → множество направлений».</li>
      <li>Движок покрытия и минимального дополнения, три состояния доступности.</li>
      <li>Сценарий: код класса → выбор → сравнение → карточка в чат.</li>
    </ul>
  </div>
  <div class="card warn">
    <span class="tag amber">Переменная часть — адаптируется</span>
    <ul class="tight">
      <li>Справочник профилей и сроков конкретной школы.</li>
      <li>Региональный порядок индивидуального отбора.</li>
      <li>Перечень вступительных испытаний — обновляется ежегодно.</li>
    </ul>
  </div>
</div>
<div class="card" style="flex:1;padding:16px 20px">
  <h3>Порядок тиражирования</h3>
  <div class="flow">
    <span class="step"><b>1.</b> Один класс пилотной школы</span><span class="arrow">→</span>
    <span class="step"><b>2.</b> Все девятые классы школы</span><span class="arrow">→</span>
    <span class="step"><b>3.</b> Муниципалитет: школы с индивидуальным отбором</span><span class="arrow">→</span>
    <span class="step"><b>4.</b> Регион — через институт развития образования</span>
  </div>
  <div class="cols" style="gap:24px;margin-top:6px">
    <p class="small"><b>Куда в первую очередь.</b> В школы того же региона: меняется только справочник
    профилей и сроков, код не трогается. Канал — классные руководители в MAX, где чат класса уже есть.</p>
    <p class="small"><b>Смежный контекст — та же задача, другой справочник.</b> Выбор специальности
    в колледже, предпрофильная подготовка в 8 классе. Меняется справочник, не логика.</p>
  </div>
  <p class="xsmall"><b>Риски масштабирования:</b> ежегодное изменение перечня испытаний (нужен владелец
  обновления), разнородность региональных порядков отбора, зависимость наполнения от школы — поэтому
  куратор школы обязателен в модели внедрения.</p>
</div>
""")

# 13 — пилот
SLIDES.append("""
<div class="kicker">Сценарий пилотного запуска</div>
<h2>Первый запуск: одна школа, одна параллель</h2>
<div class="cols3" style="flex:none">
  <div class="card"><span class="tag">Где</span><p class="small">Одна школа Республики Татарстан с несколькими профилями в 10 классе. Две параллели 9 класса, около 50 учеников.</p></div>
  <div class="card"><span class="tag">Когда</span><p class="small">С февраля, за 8–10 недель до срока подачи заявления на индивидуальный отбор.</p></div>
  <div class="card"><span class="tag">Кто владеет процессом</span><p class="small">Заместитель директора по учебной работе — вводит профили и срок. Классные руководители — раздают коды классов.</p></div>
</div>
<div class="cols">
  <div class="card accent">
    <h3>Как встраивается в существующий процесс</h3>
    <ul class="tight">
      <li>Точка входа — родительское собрание и чат класса в MAX: там же, где школа уже объявляет профили.</li>
      <li>Классный руководитель отправляет код класса в чат; ученик открывает бота.</li>
      <li>Перед собранием завуч смотрит агрегат и приносит на него разговор с родителями.</li>
      <li>Ничего не требуется устанавливать: MAX уже установлен у участников процесса.</li>
    </ul>
  </div>
  <div class="card warn">
    <h3>Что нужно для старта и что дальше</h3>
    <ul class="tight">
      <li><b>Данные:</b> профили школы, сроки, коды классов; выгрузка перечня вступительных испытаний.</li>
      <li><b>Ресурсы:</b> сервер с HTTPS, токен чат-бота, 1–2 часа куратора школы на ввод данных.</li>
      <li><b>Согласования:</b> информирование родителей о том, какие данные собираются.</li>
      <li><b>После пилота:</b> при доле завершивших ≥ 60 % и хотя бы одном решении школы на данных — тиражирование на муниципалитет и автоматизация ввода профилей.</li>
    </ul>
  </div>
</div>
""")

# 14 — ограничения
SLIDES.append("""
<div class="kicker">Ограничения, риски и допущения</div>
<h2>Что мы знаем о границах решения</h2>
<div class="cols3">
  <div class="card warn">
    <h3>Допущения</h3>
    <ul class="tight">
      <li>Формально ЕГЭ можно сдавать по любому предмету. Модель считает предмет закрытым, если он не изучается углублённо и не добран.</li>
      <li>Допущение показано пользователю, и его можно снять: чипы «готов добрать предмет» пересчитывают все профили.</li>
    </ul>
  </div>
  <div class="card warn">
    <h3>Ограничения MVP</h3>
    <ul class="tight">
      <li>Справочник испытаний модельный; данные школ демонстрационные.</li>
      <li>Валидация параметров запуска мини-приложения MAX не реализована — доступ по подписанному токену из бота.</li>
      <li>Тип кнопки запуска мини-приложения вынесен в настройку и сверяется с документацией платформы.</li>
      <li>SQLite рассчитан на класс и школу; для региона — перенос на PostgreSQL без смены логики.</li>
    </ul>
  </div>
  <div class="card warn">
    <h3>Риски и что делаем</h3>
    <ul class="tight">
      <li><b>Устаревание справочника.</b> Версия и дата актуальности видны пользователю; владелец обновления назначается на этапе пилота.</li>
      <li><b>Школа не введёт данные.</b> Куратор — обязательная роль модели внедрения, без неё запуск не начинается.</li>
      <li><b>Ложная точность.</b> Продукт отделяет факт, расчёт и рекомендацию и прямо пишет, что не заменяет правила приёма вуза и решение школы.</li>
      <li><b>Чувствительные ситуации</b> адресуются классному руководителю: продукт не даёт психологических заключений.</li>
    </ul>
  </div>
</div>
""")

# 15 — источники
SLIDES.append("""
<div class="kicker">Источники</div>
<h2>На чём основано</h2>
<div class="cols">
  <div class="card">
    <h3>Нормативные и официальные источники</h3>
    <ul class="tight">
      <li>Федеральный закон от 29.12.2012 № 273-ФЗ «Об образовании в Российской Федерации» — индивидуальный отбор при приёме в классы профильного обучения.</li>
      <li>Федеральный государственный образовательный стандарт среднего общего образования — профили обучения и углублённое изучение предметов.</li>
      <li>Приказ Минобрнауки России об утверждении перечня вступительных испытаний при приёме на обучение по программам бакалавриата и специалитета.</li>
      <li>Федеральный закон от 27.07.2006 № 152-ФЗ «О персональных данных».</li>
      <li>Минпросвещения России — статистика системы образования и Единой модели профориентации.</li>
      <li>Росстат, раздел «Образование» — численность обучающихся по регионам.</li>
    </ul>
  </div>
  <div style="display:flex;flex-direction:column;gap:12px">
    <div class="card accent">
      <h3>Что и как мы проверяли</h3>
      <ul class="tight">
        <li>Расчётное ядро и API покрыты тестами; ожидаемые значения посчитаны вручную и зафиксированы.</li>
        <li>Обязательные проверки API описаны в DATA-API.yaml и исполняются скриптом.</li>
        <li>Сквозной сценарий чат-бота прогоняется автоматически на стенде-эмуляторе Bot API MAX.</li>
      </ul>
    </div>
    <div class="card muted">
      <p class="small"><b>Честная оговорка.</b> Справочник вступительных испытаний в демо-версии
      построен по структуре официального перечня, но не является его выгрузкой. Перед пилотом он
      заменяется официальными данными и сверяется с правилами приёма вузов региона.</p>
    </div>
  </div>
</div>
""")

total = len(SLIDES)
body = "\n".join(
    slide(i + 1, total, s, dark=(i == 1)) for i, s in enumerate(SLIDES)
)
html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Профиль 10 — презентация решения</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""
(DOCS / "presentation.html").write_text(html, encoding="utf-8")
print(f"docs/presentation.html: {total} слайдов, {len(html) // 1024} КБ")
