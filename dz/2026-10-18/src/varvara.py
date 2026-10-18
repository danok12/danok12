"""Варвара, 10 класс: задание 7 (простейшие уравнения) — много и с самого простого,
векторы (задание 2) всех типов понемногу, видео: задание 3 и вероятность 4–6."""
import sympy as sp

from common import Doc, Task, ege_task, fmt_num
from vectors import vec_tasks_varvara

# (уравнение, правило выбора корня)
LINEAR = [
    (r'3x-7=11', None),
    (r'5-2x=17', None),
    (r'\frac{x-3}{4}=5', None),
    (r'7(x-2)=3x+6', None),
    (r'\frac{3}{5}x=-12', None),
    (r'0{,}2x+1{,}6=0{,}6x', None),
    (r'\frac{2x+1}{3}=\frac{x-4}{2}', None),
]
QUADRATIC = [
    (r'x^2-9x+20=0', 'min'),
    (r'x^2+3x-10=0', 'max'),
    (r'x^2=6x', 'max'),
    (r'2x^2-7x+3=0', 'min'),
    (r'3x^2+5x-2=0', 'min'),
    (r'(x+2)(x-5)=8', 'max'),
    (r'(x-4)^2=(x+6)^2', None),
]
RATIONAL = [
    (r'\frac{5}{x-3}=2', None),
    (r'\frac{1}{2x+1}=\frac{1}{5}', None),
    (r'\frac{x+4}{x-2}=3', None),
    (r'\frac{6}{x+1}=\frac{4}{x-1}', None),
    (r'\frac{x+2}{x-1}=\frac{x-3}{x-4}', None),
    (r'\frac{x^2-4}{x+2}=5', None),
    (r'x=\frac{3x+10}{x}', 'min'),
]
IRRATIONAL = [
    (r'\sqrt{x+3}=5', None),
    (r'\sqrt{2x-1}=3', None),
    (r'\sqrt{15-2x}=3', None),
    (r'\sqrt{\frac{1}{3x+4}}=\frac{1}{5}', None),
    (r'\sqrt[3]{x-4}=3', None),
    (r'\sqrt{2x+15}=x', None),
    (r'\sqrt{x+10}=x-2', None),
    (r'\sqrt{6-x}=-x', None),
]
EXPONENTIAL = [
    (r'2^{x}=32', None),
    (r'3^{x-2}=27', None),
    (r'5^{x+1}=\frac{1}{25}', None),
    (r'\left(\frac{1}{2}\right)^{x}=8', None),
    (r'4^{x}=8', None),
    (r'7^{2x-5}=49', None),
    (r'\left(\frac{1}{3}\right)^{x-1}=9', None),
    (r'16^{x-9}=\frac{1}{2}', None),
    (r'2^{3-x}=4^{x}', None),
    (r'9^{x+1}=27^{x}', None),
]
LOGARITHMIC = [
    (r'\log_{2}x=5', None),
    (r'\log_{3}(x+4)=2', None),
    (r'\log_{5}(2x-1)=2', None),
    (r'\log_{4}(x-3)=0{,}5', None),
    (r'\log_{\frac{1}{2}}(4-x)=-3', None),
    (r'\log_{2}(x+7)=\log_{2}(3x-5)', None),
    (r'\log_{3}(x^2+2x)=\log_{3}(x+6)', 'min'),
    (r'\log_{x-1}9=2', None),
]
TRIG = [
    (r'\sin\frac{\pi x}{4}=\frac{\sqrt{2}}{2}', 'minpos'),
    (r'\cos\frac{\pi(x-1)}{3}=\frac{1}{2}', 'maxneg'),
    (r'\tg\frac{\pi x}{4}=-1', 'maxneg'),
    (r'\sin\frac{\pi(2x-3)}{6}=0{,}5', 'minpos'),
    (r'\cos\frac{\pi(4x+1)}{6}=\frac{\sqrt{3}}{2}', 'minpos'),
]

VIDEOS = [
    ('Задание 3 (стереометрия) — теория и практика',
     '3 задание ЕГЭ профиль 2025. Стереометрия: всё, что ты должен знать. Формулы, теория и практика',
     'https://www.youtube.com/watch?v=D6oOO19tGmU'),
    ('Задание 3 — все формулы в одном месте', 'Все формулы стереометрии',
     'https://www.youtube.com/watch?v=UNs80kG5ihg'),
    ('Задание 4 (простая вероятность) — с нуля', 'Как научиться решать задачи на вероятность',
     'https://www.youtube.com/watch?v=uQipw8zMjgI'),
    ('Задание 4 — все типы из банка ФИПИ', 'Вероятности. Задание 4. Все прототипы банка ФИПИ',
     'https://www.youtube.com/watch?v=gkdGPV9FzHI'),
    ('Задание 5 (сложные события)',
     'Сложная вероятность. 5 задание ЕГЭ 2024 по профильной математике. Разбор всех типов',
     'https://www.youtube.com/watch?v=84dlZS81h2U'),
    ('Задание 6 (новое: случайная величина)', 'Математическое ожидание, дисперсия, стандартное отклонение за 5 минут',
     'https://www.youtube.com/watch?v=06TFGVkQDGg'),
    ('Задание 6 — как оно выглядит в демоверсии 2027', 'Демоверсия ЕГЭ 2027 | Математика Профиль (смотрите задание 6)',
     'https://www.youtube.com/watch?v=GkQzLwl-SL4'),
]


def block(doc, title, items, intro=None, cols=2):
    doc.h(title, 3)
    if intro:
        doc.p(intro)
    doc.tasks([ege_task(t, r, prefix='', short=True) for t, r in items], cols=cols, answer_cols=6)


def build():
    doc = Doc('varvara', 'Варвара, 10 класс', 'Домашнее задание · профильная математика')
    doc.h('Задание 7. Простейшие уравнения')
    doc.p('В каждом номере найдите корень уравнения. Если корней несколько, а в номере не сказано, '
          'какой выбрать, — значит, корень один, а лишние отсекает проверка. '
          'Делайте проверку подстановкой: в ЕГЭ это спасает от посторонних корней.')
    block(doc, 'Линейные', LINEAR)
    block(doc, 'Квадратные', QUADRATIC)
    block(doc, 'Дробные', RATIONAL, 'Помните: знаменатель не равен нулю.')
    block(doc, 'С корнем', IRRATIONAL, 'Возводим в квадрат, потом обязательно проверяем корни.')
    block(doc, 'Показательные', EXPONENTIAL, 'Приводим обе части к одному основанию.')
    block(doc, 'Логарифмические', LOGARITHMIC, 'Выражение под логарифмом должно быть положительным.')
    block(doc, 'Тригонометрические', TRIG,
          'Запишите все серии корней, потом подставляйте $n = 0, \\pm1, \\pm2, \\ldots$ и выбирайте нужный.',
          cols=1)
    doc.h('Задание 2. Векторы')
    doc.p('Понемногу каждого типа: координаты, длина, скалярное произведение, угол, '
          'коллинеарность и перпендикулярность, векторы в фигурах и в пространстве.')
    doc.tasks(vec_tasks_varvara(), cols=1, answer_cols=6)
    doc.h('Видео')
    doc.p('Смотрите по порядку, останавливайте видео и решайте вместе с автором. '
          'Видео прошлых лет: вероятность там — задания 4 и 5. Задание 6 о случайной величине '
          'появилось в 2027 году.')
    doc.videos(VIDEOS)
    return doc
