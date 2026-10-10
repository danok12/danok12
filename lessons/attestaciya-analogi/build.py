"""Аналоги экзаменационных задач 1–11 (линейная алгебра).

Один источник для всего: условия, ответы, проверка.
  python3 build.py   — пересчитывает каждый ответ (sympy, точная арифметика),
                       падает на первом расхождении с текстом и собирает
                       ZADACHI.md, OTVETY.md, print-uchenik.html, print-prepod.html.
"""
import re
from pathlib import Path
from sympy import (Matrix, Rational as Q, sqrt, symbols, integrate, eye,
                   simplify, expand)

HERE = Path(__file__).parent
MINUS = "−"

# ───────────────────────── мини-разметка формул ─────────────────────────


def num(v):
    s = str(v)
    return s.replace("-", MINUS)


class Node:
    def html(self): ...
    def txt(self): ...


class Mx(Node):
    """Матрица/столбец: CSS-сетка, скобки через ::before/::after."""

    def __init__(self, rows):
        self.rows = [[c if isinstance(c, (str, Node)) else num(c) for c in r] for r in rows]

    def html(self):
        n = len(self.rows[0])
        cells = "".join(f"<span>{R(c)}</span>" for r in self.rows for c in r)
        return f'<span class="mx" style="grid-template-columns:repeat({n},auto)">{cells}</span>'

    def txt(self):
        return "(" + "; ".join(" ".join(T(c) for c in r) for r in self.rows) + ")"


def col(*v):
    return Mx([[c] for c in v])


class Fr(Node):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def html(self):
        return f'<span class="fr"><span>{R(self.a)}</span><span>{R(self.b)}</span></span>'

    def txt(self):
        a, b = T(self.a), T(self.b)
        wrap = lambda s: s if re.fullmatch(r"[\w√.]+|\([^()]*\)", s) else f"({s})"
        return f"{wrap(a)}/{wrap(b)}"


class Sq(Node):
    def __init__(self, a):
        self.a = a

    def html(self):
        return f'<span class="sq">√<span>{R(self.a)}</span></span>'

    def txt(self):
        a = T(self.a)
        return "√" + (a if re.fullmatch(r"\w+", a) else f"({a})")


class Sys(Node):
    """Система: фигурная скобка слева."""

    def __init__(self, *lines):
        self.lines = lines

    def html(self):
        return '<span class="sys">' + "".join(f"<span>{R(l)}</span>" for l in self.lines) + "</span>"

    def txt(self):
        return "{ " + ";  ".join(T(l) for l in self.lines) + " }"


class Int01(Node):
    def html(self):
        return '<span class="int">∫<span class="lim"><span>1</span><span>0</span></span></span>'

    def txt(self):
        return "∫₀¹ "


def ov(s):
    """Вектор с чертой: x̄, ē₁."""
    return f'<span class="ov">{s}</span>'


def R(x):
    if isinstance(x, Node):
        return x.html()
    if isinstance(x, (list, tuple)):
        return "".join(R(p) for p in x)
    return str(x)


SUB = str.maketrans("0123456789ij", "₀₁₂₃₄₅₆₇₈₉ᵢⱼ")
SUP = str.maketrans("0123456789T", "⁰¹²³⁴⁵⁶⁷⁸⁹ᵀ")


def T(x):
    if isinstance(x, Node):
        return x.txt()
    if isinstance(x, (list, tuple)):
        return "".join(T(p) for p in x)
    s = str(x)
    s = re.sub(r'<span class="ov">(.*?)</span>',
               lambda m: re.sub(r"<.*?>", "", m.group(1))[0] + "̄" + re.sub(r"<.*?>", "", m.group(1))[1:], s)
    s = re.sub(r"<sub>(.*?)</sub>", lambda m: re.sub(r"<.*?>", "", m.group(1)).translate(SUB), s)
    s = re.sub(r"<sup>(.*?)</sup>", lambda m: m.group(1).translate(SUP), s)
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s)
    s = re.sub(r"<.*?>", "", s)
    return s.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")


x_ = lambda i: f"<i>x</i><sub>{i}</sub>"
y_ = lambda i: f"<i>y</i><sub>{i}</sub>"
e_ = lambda i: ov(f"<i>e</i><sub>{i}</sub>")
X, Y, A_ = ov("<i>x</i>"), ov("<i>y</i>"), "<i>A</i>"


# ───────────────────────── проверка ответов ─────────────────────────

x = symbols("x")
CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def t1():
    ip = lambda f, g: integrate(f * g, (x, 0, 1))
    # 1А
    f, g = 2 * x + 1, x - 1
    assert ip(f, g) == Q(-5, 6) and ip(f, f) == Q(13, 3) and ip(g, g) == Q(1, 3)
    assert simplify(ip(f, g) / sqrt(ip(f, f) * ip(g, g)) + 5 / (2 * sqrt(13))) == 0
    # 1Б
    f, g = x, 3 * x - 2
    assert ip(f, g) == 0 and ip(f, f) == Q(1, 3) and ip(g, g) == 1


@check
def t2():
    for a, b, c, na, nb, nc in [((2, 1, -2), (1, 2, 2), (2, -2, 1), 3, 3, 3),
                                ((1, 1, 1), (1, -2, 1), (1, 0, -1), sqrt(3), sqrt(6), sqrt(2))]:
        a, b, c = Matrix(a), Matrix(b), Matrix(c)
        assert a.dot(b) == 0 and a.dot(c) == 0 and b.dot(c) == 0
        assert (a.norm(), b.norm(), c.norm()) == (na, nb, nc)
        assert a.cross(b).normalized() == c.normalized()  # правая тройка


Q3 = {
    "А": [[1, 3, 6], [3, 4, 8], [6, 8, 16]],
    "Б": [[1, -2, -1], [-2, 5, 3], [-1, 3, 2]],
    "В": [[1, 2, -3], [2, 4, -6], [-3, -6, 9]],
}


@check
def t3():
    X3 = Matrix(symbols("x1:4"))
    forms = {
        "А": "x1**2+4*x2**2+16*x3**2+6*x1*x2+12*x1*x3+16*x2*x3",
        "Б": "x1**2+5*x2**2+2*x3**2-4*x1*x2-2*x1*x3+6*x2*x3",
        "В": "x1**2+4*x2**2+9*x3**2+4*x1*x2-6*x1*x3-12*x2*x3",
    }
    for k, r in {"А": 2, "Б": 2, "В": 1}.items():
        M = Matrix(Q3[k])
        assert M == M.T and M.rank() == r
        assert expand((X3.T * M * X3)[0] - __import__("sympy").sympify(forms[k])) == 0
    x1, x2, x3 = X3
    assert expand((x1 + 2 * x2 - 3 * x3) ** 2 - __import__("sympy").sympify(forms["В"])) == 0


@check
def t4():
    S = Matrix([[1, -1, 2, 1, -1], [0, 1, 1, -2, 3]])
    basis = [(-3, -1, 1, 0, 0), (1, 2, 0, 1, 0), (-2, -3, 0, 0, 1)]
    assert S.rank() == 2 and all(S * Matrix(v) == Matrix([0, 0]) for v in basis)
    assert Matrix(basis).rank() == 3
    S = Matrix([[1, 2, -1, 1, 3], [2, 5, -1, 4, 4], [1, 3, 0, 3, 1]])
    basis = [(3, -1, 1, 0, 0), (3, -2, 0, 1, 0), (-7, 2, 0, 0, 1)]
    assert S.rank() == 2 and all(S * Matrix(v) == Matrix([0, 0, 0]) for v in basis)
    assert Matrix(basis).rank() == 3


def opmat(F):
    E = [Matrix(2, 2, lambda i, j: int((i, j) == p)) for p in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    return Matrix.hstack(*[Matrix(list(F(e))) for e in E])


A5 = {"А": [[2, 0, 1, 0], [0, 2, 0, 1], [-1, 0, 3, 0], [0, -1, 0, 3]],
      "Б": [[1, 0, 0, 0], [2, -1, 0, 0], [0, 0, 1, 0], [0, 0, 2, -1]]}


@check
def t5():
    B = Matrix([[2, -1], [1, 3]])
    assert opmat(lambda M: B.T * M) == Matrix(A5["А"])
    B = Matrix([[1, 2], [0, -1]])
    assert opmat(lambda M: M * B) == Matrix(A5["Б"])


@check
def t6():
    G, u, v = Matrix([[3, -1], [-1, 2]]), Matrix([2, 1]), Matrix([-1, 3])
    assert G.det() > 0 and G[0, 0] > 0
    assert ((u.T * G * u)[0], (v.T * G * v)[0], (u.T * G * v)[0]) == (10, 27, -5)
    G, u, v = Matrix([[4, 2], [2, 3]]), Matrix([5, -6]), Matrix([1, 1])
    assert G.det() > 0 and G[0, 0] > 0
    assert ((u.T * G * u)[0], (v.T * G * v)[0], (u.T * G * v)[0]) == (88, 11, 0)
    assert u.dot(v) == -1


@check
def t7():
    c = Matrix([[1, 2], [3, 5]]).solve(Matrix([2, 1]))  # столбцы: f1=x+3, f2=2x+5
    assert list(c) == [-8, 5]
    # базис (x²; x; 1): f1=x²+1, f2=x²+x, f3=x+1; p=2x²−x+5
    c = Matrix([[1, 1, 0], [0, 1, 1], [1, 0, 1]]).solve(Matrix([2, -1, 5]))
    assert list(c) == [4, -2, 1]


A8 = {"А": [[2, -1, 4], [1, 0, 3], [-1, 5, -2]], "Б": [[0, 1, -1], [3, 1, 0], [1, -2, 4]]}


@check
def t8():
    assert list(Matrix(A8["А"]) * Matrix([2, -1, 3])) == [17, 11, -13]
    assert list(Matrix(A8["Б"]) * Matrix([1, -2, 3])) == [-5, 1, 17]


A9 = {"А": [[2, 4, 1], [3, 1, -1], [1, 3, 1]], "Б": [[4, -1, 1], [2, 1, 3], [-2, 1, 2]]}


@check
def t9():
    v = Matrix([-1, 1, -1])
    assert Matrix(A9["А"]) * v == -1 * v and list(Matrix(A9["А"]) * v) == [1, -1, 1]
    A = Matrix(A9["Б"])
    u, w = Matrix([1, 2, 0]), Matrix([1, 1, 1])
    assert A * u == 2 * u and list(A * w) == [4, 6, 1]
    assert Matrix.hstack(A * w, w).rank() == 2  # w не собственный


A10 = {"А": [[3, 0, -1], [2, 1, 0], [3, -1, 1]], "Б": [[0, -1, 2], [2, -3, 4], [-1, 1, -3]]}


@check
def t10():
    A = Matrix(A10["А"])
    assert (A - 2 * eye(3)).rank() == 2 and A * Matrix([1, 2, 1]) == 2 * Matrix([1, 2, 1])
    A = Matrix(A10["Б"])
    assert (A + eye(3)).rank() == 1
    for v in [(1, 1, 0), (-2, 0, 1)]:
        assert A * Matrix(v) == -Matrix(v)


@check
def t11():
    for M, lams, P in [
        (Matrix([[1, 2 * sqrt(3)], [2 * sqrt(3), 5]]), (-1, 7),
         Matrix([[sqrt(3) / 2, Q(1, 2)], [-Q(1, 2), sqrt(3) / 2]])),
        (Matrix([[-1, 6], [6, 4]]), (-5, 8),
         Matrix([[3, 2], [-2, 3]]) / sqrt(13)),
    ]:
        assert simplify(P.T * P - eye(2)) == Matrix.zeros(2, 2)
        assert simplify(P.det()) == 1
        assert simplify(P.T * M * P - Matrix([[lams[0], 0], [0, lams[1]]])) == Matrix.zeros(2, 2)


for fn in CHECKS:
    fn()
print(f"проверок пройдено: {len(CHECKS)}")


# ───────────────────────── содержание ─────────────────────────
# Каждая задача: заголовок, напоминание (метод, без ответа), варианты.
# Вариант: (буква, условие, ответ, решение-кратко). Ловушка — для преподавателя.

sq = Sq
TASKS = []

TASKS.append(dict(
    n=1, title="Угол между функциями в C[0;1]",
    hint=["(<i>f</i>,<i>g</i>) = ", Int01(), "<i>f</i>(<i>x</i>)·<i>g</i>(<i>x</i>)<i>dx</i>, &nbsp; ‖<i>f</i>‖ = ", Sq("(<i>f</i>,<i>f</i>)"),
          ", &nbsp; cos<i>φ</i> = ", Fr("(<i>f</i>,<i>g</i>)", "‖<i>f</i>‖·‖<i>g</i>‖"), "."],
    variants=[
        ("А", ["Найдите косинус угла между функциями <i>f</i>, <i>g</i> ∈ <i>C</i>[0;1]: &nbsp; <i>f</i>(<i>x</i>) = 2<i>x</i> + 1 и <i>g</i>(<i>x</i>) = <i>x</i> − 1 "
               "в евклидовом пространстве со скалярным произведением (<i>f</i>,<i>g</i>) = ", Int01(), "<i>f</i>(<i>x</i>)·<i>g</i>(<i>x</i>)<i>dx</i>."],
         ["cos<i>φ</i> = ", Fr("−5", ["2", Sq("13")]), " = ", Fr(["−5", Sq("13")], "26")],
         ["(<i>f</i>,<i>g</i>) = ", Int01(), "(2<i>x</i>² − <i>x</i> − 1)<i>dx</i> = ", Fr(2, 3), " − ", Fr(1, 2), " − 1 = ", Fr("−5", 6),
          "; &nbsp; ‖<i>f</i>‖² = ", Int01(), "(4<i>x</i>² + 4<i>x</i> + 1)<i>dx</i> = ", Fr(13, 3),
          "; &nbsp; ‖<i>g</i>‖² = ", Int01(), "(<i>x</i> − 1)²<i>dx</i> = ", Fr(1, 3), "; &nbsp; ‖<i>f</i>‖·‖<i>g</i>‖ = ", Fr(Sq(13), 3), "."]),
        ("Б", ["Найдите косинус угла и сам угол между функциями <i>f</i>(<i>x</i>) = <i>x</i> и <i>g</i>(<i>x</i>) = 3<i>x</i> − 2 в <i>C</i>[0;1] "
               "с тем же скалярным произведением. Что можно сказать об этих функциях?"],
         ["cos<i>φ</i> = 0, &nbsp;<i>φ</i> = 90°: функции ортогональны"],
         ["(<i>f</i>,<i>g</i>) = ", Int01(), "(3<i>x</i>² − 2<i>x</i>)<i>dx</i> = 1 − 1 = 0; нормы считать уже не нужно "
          "(‖<i>f</i>‖ = ", Fr(1, Sq(3)), ", ‖<i>g</i>‖ = 1)."]),
    ],
    trap="Забывают брать корень: в знаменатель ставят ‖f‖²·‖g‖² вместо ‖f‖·‖g‖. "
         "Второе — ошибки при раскрытии (x − 1)²: пишут x² − 1. Ловить проверкой |cosφ| ≤ 1.",
))

TASKS.append(dict(
    n=2, title="Дополнение до ортонормированного базиса в R³",
    hint=["Третий вектор ортогонален обоим: решить систему из двух уравнений (<i>c</i>,<i>a</i>) = 0, (<i>c</i>,<i>b</i>) = 0 "
          "или взять векторное произведение <i>a</i> × <i>b</i>. Затем каждый вектор разделить на его длину."],
    variants=[
        ("А", ["В пространстве L = <b>R</b>³ в стандартном базисе ", ov("<i>i</i>"), ", ", ov("<i>j</i>"), ", ", ov("<i>k</i>"),
               " заданы два вектора ", ov("<i>a</i>"), " = (2, 1, −2) и ", ov("<i>b</i>"), " = (1, 2, 2). "
               "Убедитесь, что они ортогональны, и дополните их третьим вектором до ортонормированного базиса. В ответе укажите все три вектора."],
         [e_(1), " = ", Fr(1, 3), "(2, 1, −2); &nbsp; ", e_(2), " = ", Fr(1, 3), "(1, 2, 2); &nbsp; ", e_(3), " = ", Fr(1, 3), "(2, −2, 1)"],
         ["(<i>a</i>,<i>b</i>) = 2 + 2 − 4 = 0. &nbsp; <i>a</i> × <i>b</i> = (6, −6, 3) ∥ (2, −2, 1). Все три длины равны 3. "
          "Годится и ", e_(3), " = ", Fr(1, 3), "(−2, 2, −1)."]),
        ("Б", ["То же для ", ov("<i>a</i>"), " = (1, 1, 1) и ", ov("<i>b</i>"), " = (1, −2, 1)."],
         [e_(1), " = ", Fr(1, Sq(3)), "(1, 1, 1); &nbsp; ", e_(2), " = ", Fr(1, Sq(6)), "(1, −2, 1); &nbsp; ", e_(3), " = ", Fr(1, Sq(2)), "(1, 0, −1)"],
         ["(<i>a</i>,<i>b</i>) = 1 − 2 + 1 = 0. &nbsp; <i>a</i> × <i>b</i> = (3, 0, −3) ∥ (1, 0, −1). "
          "Длины: ", Sq(3), ", ", Sq(6), ", ", Sq(2), ". Знак у ", e_(3), " любой."]),
    ],
    trap="Нормируют только третий вектор, а a и b оставляют как есть — базис ортогональный, но не ортонормированный. "
         "Или делят на сумму координат вместо длины.",
))

TASKS.append(dict(
    n=3, title="Ранг квадратичной формы",
    hint=["Ранг формы = ранг её симметричной матрицы. На диагонали — коэффициенты при <i>x</i><sub><i>i</i></sub>², "
          "вне диагонали — <b>половина</b> коэффициента при <i>x</i><sub><i>i</i></sub><i>x</i><sub><i>j</i></sub>. Ранг — элементарными преобразованиями строк."],
    variants=[
        ("А", ["Найдите ранг квадратичной формы <i>f</i>(", x_(1), ", ", x_(2), ", ", x_(3), ") = ", x_(1), "² + 4", x_(2), "² + 16", x_(3), "² + 6", x_(1), x_(2),
               " + 12", x_(1), x_(3), " + 16", x_(2), x_(3), "."],
         ["<i>r</i> = 2"],
         ["Матрица ", Mx(Q3["А"]), ": третья строка = 2 · вторая, а минор ", Mx([[1, 3], [3, 4]]), " = −5 ≠ 0."]),
        ("Б", ["То же для <i>f</i> = ", x_(1), "² + 5", x_(2), "² + 2", x_(3), "² − 4", x_(1), x_(2), " − 2", x_(1), x_(3), " + 6", x_(2), x_(3), "."],
         ["<i>r</i> = 2"],
         ["Матрица ", Mx(Q3["Б"]), ": третья строка = первая + вторая, минор ", Mx([[1, -2], [-2, 5]]), " = 1 ≠ 0."]),
        ("В", ["То же для <i>f</i> = ", x_(1), "² + 4", x_(2), "² + 9", x_(3), "² + 4", x_(1), x_(2), " − 6", x_(1), x_(3), " − 12", x_(2), x_(3), "."],
         ["<i>r</i> = 1"],
         ["Матрица ", Mx(Q3["В"]), ": все строки пропорциональны первой. Действительно, <i>f</i> = (", x_(1), " + 2", x_(2), " − 3", x_(3), ")²."]),
    ],
    trap="Главная ошибка — ставить в матрицу полный коэффициент при xᵢxⱼ (6, 12, 16), а не половину (3, 6, 8). "
         "Ранг при этом может получиться 3. Ловить: матрица обязана быть симметричной, а xᵀAx должен вернуть исходную форму.",
))

TASKS.append(dict(
    n=4, title="Базис и размерность пространства решений однородной системы",
    hint=["Привести к ступенчатому виду, найти ранг <i>r</i>. Тогда dim<i>L</i> = <i>n</i> − <i>r</i> (<i>n</i> — число неизвестных). "
          "Свободным неизвестным по очереди даём значения (1, 0, 0), (0, 1, 0), (0, 0, 1) — получаем фундаментальную систему решений."],
    variants=[
        ("А", ["Найдите какой-нибудь базис и установите размерность пространства решений однородной системы ",
               Sys([x_(1), " − ", x_(2), " + 2", x_(3), " + ", x_(4), " − ", x_(5), " = 0;"],
                   [x_(2), " + ", x_(3), " − 2", x_(4), " + 3", x_(5), " = 0."])],
         ["dim<i>L</i> = 3; &nbsp; <i>e</i><sub>1</sub> = (−3; −1; 1; 0; 0), &nbsp;<i>e</i><sub>2</sub> = (1; 2; 0; 1; 0), &nbsp;<i>e</i><sub>3</sub> = (−2; −3; 0; 0; 1)"],
         ["Свободные ", x_(3), ", ", x_(4), ", ", x_(5), ". &nbsp;", x_(2), " = −", x_(3), " + 2", x_(4), " − 3", x_(5), "; &nbsp;",
          x_(1), " = ", x_(2), " − 2", x_(3), " − ", x_(4), " + ", x_(5), " = −3", x_(3), " + ", x_(4), " − 2", x_(5), "."]),
        ("Б", ["То же для системы ",
               Sys([x_(1), " + 2", x_(2), " − ", x_(3), " + ", x_(4), " + 3", x_(5), " = 0;"],
                   ["2", x_(1), " + 5", x_(2), " − ", x_(3), " + 4", x_(4), " + 4", x_(5), " = 0;"],
                   [x_(1), " + 3", x_(2), " + 3", x_(4), " + ", x_(5), " = 0."])],
         ["dim<i>L</i> = 3; &nbsp; <i>e</i><sub>1</sub> = (3; −1; 1; 0; 0), &nbsp;<i>e</i><sub>2</sub> = (3; −2; 0; 1; 0), &nbsp;<i>e</i><sub>3</sub> = (−7; 2; 0; 0; 1)"],
         ["Третье уравнение = второе − первое, поэтому <i>r</i> = 2, а не 3. После вычитания: ",
          x_(2), " = −", x_(3), " − 2", x_(4), " + 2", x_(5), "; &nbsp;", x_(1), " = 3", x_(3), " + 3", x_(4), " − 7", x_(5), "."]),
    ],
    trap="В варианте Б считают уравнения, а не ранг: «три уравнения — значит dim = 5 − 3 = 2». "
         "Каждый найденный вектор подставить в исходную систему — это 30 секунд и ловит почти всё.",
))

TASKS.append(dict(
    n=5, title="Матрица линейного оператора в пространстве матриц 2×2",
    hint=["Стандартный базис <i>M</i><sub>2×2</sub>: <i>E</i><sub>1</sub> = ", Mx([[1, 0], [0, 0]]), ", <i>E</i><sub>2</sub> = ", Mx([[0, 1], [0, 0]]),
          ", <i>E</i><sub>3</sub> = ", Mx([[0, 0], [1, 0]]), ", <i>E</i><sub>4</sub> = ", Mx([[0, 0], [0, 1]]),
          ". Находим <i>f</i>(<i>E</i><sub><i>k</i></sub>), раскладываем по базису — эти координаты пишем в <b>столбец</b> № <i>k</i>."],
    variants=[
        ("А", ["Пусть <i>L</i> = <i>M</i><sub>2×2</sub>. Найдите матрицу <i>A</i> линейного оператора <i>f</i>(<i>M</i>) = ",
               Mx([[2, -1], [1, 3]]), "<sup><i>T</i></sup>·<i>M</i> в стандартном базисе пространства <i>L</i>."],
         ["<i>A</i> = ", Mx(A5["А"])],
         ["Сначала транспонировать: ", Mx([[2, -1], [1, 3]]), "<sup><i>T</i></sup> = ", Mx([[2, 1], [-1, 3]]),
          ". <i>f</i>(<i>E</i><sub>1</sub>) = ", Mx([[2, 0], [-1, 0]]), " → столбец (2; 0; −1; 0), и т.д."]),
        ("Б", ["То же для оператора <i>f</i>(<i>M</i>) = <i>M</i>·", Mx([[1, 2], [0, -1]]), " (умножение <b>справа</b>)."],
         ["<i>A</i> = ", Mx(A5["Б"])],
         ["<i>f</i>(<i>E</i><sub>1</sub>) = ", Mx([[1, 2], [0, 0]]), " → (1; 2; 0; 0); &nbsp; <i>f</i>(<i>E</i><sub>2</sub>) = ", Mx([[0, -1], [0, 0]]),
          " → (0; −1; 0; 0); <i>E</i><sub>3</sub>, <i>E</i><sub>4</sub> — то же во второй строке."]),
    ],
    trap="Записывают образы базисных матриц в строки, а не в столбцы — получается Aᵀ. "
         "Второе — в варианте А забывают транспонировать матрицу из условия. Проверка: A·(координаты M) должно дать координаты f(M) для любой M, например M = (1 1; 1 1).",
))

TASKS.append(dict(
    n=6, title="Длины и угол по матрице Грама",
    hint=["(", X, ",", Y, ") = <i>X</i><sup><i>T</i></sup>·<i>G</i>·<i>Y</i> (строка × матрица × столбец), &nbsp; ‖", X, "‖ = ", Sq(["(", X, ",", X, ")"]),
     ", &nbsp; cos<i>φ</i> = ", Fr(["(", X, ",", Y, ")"], ["‖", X, "‖·‖", Y, "‖"]), "."],
    variants=[
        ("А", ["В базисе {", e_(1), ", ", e_(2), "} дана матрица Грама скалярного произведения <i>G</i> = ", Mx([[3, -1], [-1, 2]]),
               " и векторы ", X, " = ", col(2, 1), ", ", Y, " = ", col(-1, 3), ". Найдите длины векторов ", X, " и ", Y, ", а также угол между ними."],
         ["‖", X, "‖ = ", Sq(10), ", &nbsp;‖", Y, "‖ = ", Sq(27), " = 3", Sq(3), ", &nbsp;cos<i>φ</i> = ", Fr("−5", [Sq(10), "·", Sq(27)]),
          " = ", Fr("−5", ["3", Sq(30)])],
         ["<i>GY</i> = (−6; 7), (", X, ",", Y, ") = 2·(−6) + 1·7 = −5. &nbsp; <i>GX</i> = (5; 0), (", X, ",", X, ") = 10. &nbsp; <i>GY</i>·<i>Y</i> = 6 + 21 = 27."]),
        ("Б", ["То же для <i>G</i> = ", Mx([[4, 2], [2, 3]]), ", ", X, " = ", col(5, -6), ", ", Y, " = ", col(1, 1),
               ". Отдельно ответьте: ортогональны ли ", X, " и ", Y, " в этом скалярном произведении? А если бы скалярное произведение было обычным?"],
         ["‖", X, "‖ = ", Sq(88), " = 2", Sq(22), ", &nbsp;‖", Y, "‖ = ", Sq(11), ", &nbsp;cos<i>φ</i> = 0 — ортогональны; "
          "в обычном скалярном произведении 5 − 6 = −1 ≠ 0, не ортогональны"],
         ["<i>GY</i> = (6; 5), (", X, ",", Y, ") = 30 − 30 = 0. &nbsp; <i>GX</i> = (8; −8), (", X, ",", X, ") = 40 + 48 = 88."]),
    ],
    trap="Считают обычное скалярное произведение 2·(−1) + 1·3, забывая про G. "
         "Или берут только диагональ G. Ловить: (x,x) по матрице Грама обязано быть > 0.",
))

TASKS.append(dict(
    n=7, title="Координаты многочлена в новом базисе",
    hint=["Записать <i>p</i> = <i>c</i><sub>1</sub><i>f</i><sub>1</sub> + <i>c</i><sub>2</sub><i>f</i><sub>2</sub> (+ …), раскрыть скобки и приравнять "
          "коэффициенты при одинаковых степенях <i>x</i> — получится система для <i>c</i><sub>1</sub>, <i>c</i><sub>2</sub>, …"],
    variants=[
        ("А", ["В линейном пространстве <i>P</i><sub>1</sub> многочленов степени не выше 1 в стандартном базисе (<i>x</i>; 1) заданы три многочлена: "
               "<i>p</i>(<i>x</i>) = 2<i>x</i> + 1; &nbsp;<i>f</i><sub>1</sub>(<i>x</i>) = <i>x</i> + 3; &nbsp;<i>f</i><sub>2</sub>(<i>x</i>) = 2<i>x</i> + 5. "
               "Найдите координаты многочлена <i>p</i>(<i>x</i>) в новом базисе <i>f</i><sub>1</sub>; <i>f</i><sub>2</sub>."],
         ["<i>p</i>(<i>x</i>) = −8<i>f</i><sub>1</sub> + 5<i>f</i><sub>2</sub> = (−8; 5)"],
         [Sys(["<i>x</i>: &nbsp;<i>c</i><sub>1</sub> + 2<i>c</i><sub>2</sub> = 2"], ["1: &nbsp;3<i>c</i><sub>1</sub> + 5<i>c</i><sub>2</sub> = 1"]),
          " &nbsp; Проверка: −8(<i>x</i> + 3) + 5(2<i>x</i> + 5) = 2<i>x</i> + 1 ✓"]),
        ("Б", ["В пространстве <i>P</i><sub>2</sub> многочленов степени не выше 2 в стандартном базисе (<i>x</i>²; <i>x</i>; 1) даны "
               "<i>p</i>(<i>x</i>) = 2<i>x</i>² − <i>x</i> + 5 и <i>f</i><sub>1</sub> = <i>x</i>² + 1, <i>f</i><sub>2</sub> = <i>x</i>² + <i>x</i>, <i>f</i><sub>3</sub> = <i>x</i> + 1. "
               "Найдите координаты <i>p</i>(<i>x</i>) в базисе <i>f</i><sub>1</sub>; <i>f</i><sub>2</sub>; <i>f</i><sub>3</sub>."],
         ["<i>p</i>(<i>x</i>) = 4<i>f</i><sub>1</sub> − 2<i>f</i><sub>2</sub> + <i>f</i><sub>3</sub> = (4; −2; 1)"],
         [Sys(["<i>x</i>²: &nbsp;<i>c</i><sub>1</sub> + <i>c</i><sub>2</sub> = 2"], ["<i>x</i>: &nbsp;<i>c</i><sub>2</sub> + <i>c</i><sub>3</sub> = −1"],
              ["1: &nbsp;<i>c</i><sub>1</sub> + <i>c</i><sub>3</sub> = 5"]),
          " &nbsp; Проверка: 4<i>x</i>² + 4 − 2<i>x</i>² − 2<i>x</i> + <i>x</i> + 1 = 2<i>x</i>² − <i>x</i> + 5 ✓"]),
    ],
    trap="В ответ пишут коэффициенты самого p (2; 1) — это координаты в старом базисе. "
         "Проверка подстановкой c₁f₁ + c₂f₂ обязательна.",
))

TASKS.append(dict(
    n=8, title="Матрица оператора в R³ и образ вектора",
    hint=["Строка № <i>i</i> матрицы <i>A</i> — коэффициенты при ", x_(1), ", ", x_(2), ", ", x_(3), " в <i>i</i>-й координате образа "
          "(если переменной нет — пишем 0). Образ: <i>f</i>(", X, ") = <i>A</i>·<i>X</i>."],
    variants=[
        ("А", ["Найдите матрицу <i>A</i> линейного оператора <i>f</i>((", x_(1), ", ", x_(2), ", ", x_(3), ")) = (2", x_(1), " − ", x_(2), " + 4", x_(3), "; &nbsp;",
               x_(1), " + 3", x_(3), "; &nbsp;−", x_(1), " + 5", x_(2), " − 2", x_(3), ") в стандартном базисе пространства L = <b>R</b>³ и образ вектора ",
               X, " = (2; −1; 3)."],
         ["<i>A</i> = ", Mx(A8["А"]), "; &nbsp; <i>f</i>(", X, ") = (17; 11; −13)"],
         ["Во второй координате нет ", x_(2), " — в матрице 0. &nbsp; 4 + 1 + 12 = 17; &nbsp;2 + 0 + 9 = 11; &nbsp;−2 − 5 − 6 = −13."]),
        ("Б", ["То же для <i>f</i>((", x_(1), ", ", x_(2), ", ", x_(3), ")) = (", x_(2), " − ", x_(3), "; &nbsp;3", x_(1), " + ", x_(2), "; &nbsp;",
               x_(1), " − 2", x_(2), " + 4", x_(3), ") и ", X, " = (1; −2; 3)."],
         ["<i>A</i> = ", Mx(A8["Б"]), "; &nbsp; <i>f</i>(", X, ") = (−5; 1; 17)"],
         ["−2 − 3 = −5; &nbsp;3 − 2 = 1; &nbsp;1 + 4 + 12 = 17."]),
    ],
    trap="Пропущенная переменная: в строку (x₁ + 3x₃) пишут (1, 3) и сдвигают столбцы. Всегда три числа в строке.",
))

TASKS.append(dict(
    n=9, title="К какому собственному значению относится вектор",
    hint=["Умножить <i>A</i> на столбец координат вектора. Если <i>AX</i> = <i>λX</i> — вектор собственный, а <i>λ</i> — искомое значение. "
          "Если результат не пропорционален <i>X</i> — вектор не собственный."],
    variants=[
        ("А", ["Линейный оператор <i>f</i> в базисе ", e_(1), ", ", e_(2), ", ", e_(3), " задан матрицей <i>A</i> = ", Mx(A9["А"]),
               ". Вектор ", X, " = −", e_(1), " + ", e_(2), " − ", e_(3), " является собственным вектором оператора <i>f</i>. "
               "Найдите, к какому собственному значению он относится."],
         ["<i>λ</i> = −1"],
         ["<i>X</i> = (−1; 1; −1), &nbsp;<i>AX</i> = (1; −1; 1) = −1·<i>X</i>."]),
        ("Б", ["Оператор задан матрицей <i>A</i> = ", Mx(A9["Б"]), ". Какой из векторов ", X, " = ", e_(1), " + 2", e_(2), " и ",
               Y, " = ", e_(1), " + ", e_(2), " + ", e_(3), " является собственным? К какому собственному значению он относится?"],
         [X, " — собственный, <i>λ</i> = 2; &nbsp;", Y, " — не собственный"],
         ["<i>AX</i> = (2; 4; 0) = 2·(1; 2; 0). &nbsp; <i>AY</i> = (4; 6; 1) — не пропорционален (1; 1; 1)."]),
    ],
    trap="Координаты вектора −e₁ + e₂ − e₃ пишут без знаков или пропускают нулевую координату (в оригинале −2e₁ + 2e₃ → (−2; 0; 2)). "
         "Ищут λ через характеристический многочлен — долго и не нужно.",
))

TASKS.append(dict(
    n=10, title="Собственный вектор для данного собственного значения",
    hint=["Решить однородную систему (<i>A</i> − <i>λE</i>)<i>X</i> = 0: вычесть <i>λ</i> из диагонали, привести к ступенчатому виду, "
          "взять любое ненулевое решение. Проверка: <i>AX</i> = <i>λX</i>."],
    variants=[
        ("А", ["Для линейного оператора, заданного матрицей <i>A</i> = ", Mx(A10["А"]),
               ", найдите какой-нибудь собственный вектор, соответствующий собственному числу <i>λ</i> = 2."],
         [ov("<i>r</i>"), " = (1; 2; 1) &nbsp;(или любой ненулевой кратный)"],
         ["<i>A</i> − 2<i>E</i> = ", Mx([[1, 0, -1], [2, -1, 0], [3, -1, -1]]), ", ранг 2 (третья строка = первая + вторая): ",
          x_(3), " = ", x_(1), ", ", x_(2), " = 2", x_(1), ". &nbsp; <i>A</i>·(1; 2; 1) = (2; 4; 2) ✓"]),
        ("Б", ["Для матрицы <i>A</i> = ", Mx(A10["Б"]), " найдите какой-нибудь собственный вектор, соответствующий <i>λ</i> = −1. "
               "Сколько линейно независимых собственных векторов отвечает этому значению?"],
         ["например, (1; 1; 0) или (−2; 0; 1); &nbsp;таких независимых векторов два"],
         ["<i>A</i> + <i>E</i> = ", Mx([[1, -1, 2], [2, -2, 4], [-1, 1, -2]]), " — все строки пропорциональны, ранг 1, остаётся одно уравнение ",
          x_(1), " − ", x_(2), " + 2", x_(3), " = 0: две свободные переменные."]),
    ],
    trap="Вычитают λ из всех элементов, а не только из диагонали. Или для λ = −1 вычитают −1 «в ту же сторону» и получают A − E. "
         "Нулевой вектор в ответ — не собственный вектор.",
))

TASKS.append(dict(
    n=11, title="Канонический вид квадратичной формы ортогональным преобразованием",
    hint=["1) Матрица формы (вне диагонали — половина коэффициента при ", x_(1), x_(2), "). 2) Корни |<i>A</i> − <i>λE</i>| = 0 — это коэффициенты канонического вида. "
          "3) Для каждого <i>λ</i> — собственный вектор, нормировать. 4) Из нормированных векторов-столбцов составить матрицу перехода: <i>X</i> = <i>P</i>·<i>Y</i>."],
    variants=[
        ("А", ["Приведите квадратичную форму Φ(", x_(1), ", ", x_(2), ") = ", x_(1), "² + 5", x_(2), "² + 4", Sq(3), x_(1), x_(2),
               " к каноническому виду и укажите соответствующее ортогональное преобразование координат."],
         ["Φ(", y_(1), ", ", y_(2), ") = −", y_(1), "² + 7", y_(2), "², &nbsp;",
          col(x_(1), x_(2)), " = ", Mx([[Fr(Sq(3), 2), Fr(1, 2)], [Fr("−1", 2), Fr(Sq(3), 2)]]), col(y_(1), y_(2))],
         ["<i>A</i> = ", Mx([["1", ["2", Sq(3)]], [["2", Sq(3)], "5"]]), ", &nbsp;<i>λ</i>² − 6<i>λ</i> − 7 = 0, <i>λ</i> = −1; 7. "
          "Для −1: ", x_(1), " = −", Sq(3), x_(2), " → (", Sq(3), "; −1)/2; для 7: ", x_(2), " = ", Sq(3), x_(1), " → (1; ", Sq(3), ")/2. "
          "Это поворот на −30°."]),
        ("Б", ["То же для Φ(", x_(1), ", ", x_(2), ") = −", x_(1), "² + 4", x_(2), "² + 12", x_(1), x_(2), "."],
         ["Φ(", y_(1), ", ", y_(2), ") = −5", y_(1), "² + 8", y_(2), "², &nbsp;",
          col(x_(1), x_(2)), " = ", Mx([[Fr(3, Sq(13)), Fr(2, Sq(13))], [Fr("−2", Sq(13)), Fr(3, Sq(13))]]), col(y_(1), y_(2))],
         ["<i>A</i> = ", Mx([[-1, 6], [6, 4]]), ", &nbsp;<i>λ</i>² − 3<i>λ</i> − 40 = 0, <i>λ</i> = −5; 8. "
          "Для −5: 4", x_(1), " + 6", x_(2), " = 0 → (3; −2)/", Sq(13), "; для 8: −9", x_(1), " + 6", x_(2), " = 0 → (2; 3)/", Sq(13), "."]),
    ],
    trap="Снова «половина коэффициента»: для 12x₁x₂ в матрицу идёт 6, а не 12 (и 2√3, а не 4√3). "
         "Собственные векторы забывают нормировать или ставят их в строки матрицы P. "
         "Проверка: сумма коэффициентов канонического вида = следу матрицы (−1 + 7 = 1 + 5), произведение = её определителю.",
))

# ───────────────────────── вёрстка ─────────────────────────

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#000;font:15px/1.5 "Liberation Serif","Times New Roman","DejaVu Serif",serif}
.wrap{max-width:860px;margin:0 auto;padding:24px 16px 40px}
h1,h2{font-weight:bold;line-height:1.25}
h1{font-size:20px;margin:0 0 4px;text-align:center}
.sub{margin:0 0 14px;text-align:center}
.intro{margin:0 0 16px}
.intro p{margin:3px 0}
.card{margin:0 0 14px}
.card h2{font-size:16px;margin:0 0 4px}
.hint{font-style:italic;margin:0 0 6px}
.hint b.lbl{font-weight:bold}
.var{display:grid;grid-template-columns:28px 1fr;gap:2px 6px;margin:0 0 8px}
.var .lt{font-weight:bold}
.ans{margin:4px 0 0}
.ans .k{font-weight:bold}
.sol{margin:2px 0 0}
.trap{margin:2px 0 6px}
.trap b{font-weight:bold}
.mx{display:inline-grid;position:relative;vertical-align:middle;column-gap:12px;row-gap:1px;padding:2px 10px;margin:2px 3px;text-align:center;line-height:1.35}
.mx::before,.mx::after{content:"";position:absolute;top:1px;bottom:1px;width:6px;border:1.2px solid currentColor}
.mx::before{left:0;border-right:none;border-radius:7px 0 0 7px}
.mx::after{right:0;border-left:none;border-radius:0 7px 7px 0}
.fr{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;margin:0 2px;font-size:.92em;line-height:1.15}
.fr>span:first-child{border-bottom:1px solid currentColor;padding:0 2px}
.fr>span:last-child{padding:0 2px}
.sq{white-space:nowrap}.sq>span{border-top:1px solid currentColor;padding:0 1px;margin-left:1px}
.ov{text-decoration:overline}
.sys{display:inline-flex;flex-direction:column;vertical-align:middle;border-left:1.5px solid currentColor;border-radius:10px 0 0 10px;padding:1px 0 1px 10px;margin:4px 4px}
.int{white-space:nowrap;font-size:1.3em}
.int .lim{display:inline-flex;flex-direction:column;font-size:.5em;vertical-align:middle;line-height:1.05;margin:0 2px 0 -1px}
.foot{font-size:13px;margin-top:18px}
@page{margin:14mm 12mm}
@media print{
  body{font-size:13.5px}
  .wrap{padding:0;max-width:none}
  .card{break-inside:avoid;page-break-inside:avoid}
  .var,.mx,.ans,.sys{break-inside:avoid}
  h1,h2{break-after:avoid}
}
"""


def hint_block(t):
    return f'<div class="hint"><b class="lbl">Как решать.</b> {R(t["hint"])}</div>'


def page(teacher):
    title = "Аттестация: аналоги задач 1–11 — ответы и решения" if teacher else "Аттестация: аналоги задач 1–11"
    parts = [f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
             f'<meta name="viewport" content="width=device-width,initial-scale=1">'
             f"<title>{'Аналоги — ответы' if teacher else 'Аналоги экзаменационных задач'}</title><style>{CSS}</style></head><body><div class=\"wrap\">",
             f"<h1>{title}</h1>",
             '<p class="sub">Линейная алгебра · по образцу «Примерных задач на экзамен», задачи 1–11</p>']
    if teacher:
        parts.append('<div class="intro"><p>Все ответы пересчитаны программой (<code>build.py</code>, точная арифметика sympy). '
                     'Под каждым вариантом — ключевые промежуточные числа, по которым удобно найти, где ученик сбился. '
                     'После вариантов — типичная ошибка в этом типе задач.</p></div>')
    else:
        parts.append('<div class="intro"><p>К каждой задаче экзамена — два варианта того же типа (к задаче 3 — три). '
                     'Решай в тетради с полной записью, как на экзамене.</p>'
                     '<p>Курсивом под заголовком — напоминание, <b>как</b> решать, а не ответ. Сначала попробуй без него.</p>'
                     '<p>Каждый ответ, где это возможно, проверь сам: подставь найденный вектор в систему, умножь матрицу на вектор, '
                     'убедись, что |cos<i>φ</i>| ≤ 1.</p></div>')
    for t in TASKS:
        parts.append(f'<section class="card"><h2>{t["n"]}. {t["title"]}</h2>')
        if not teacher:
            parts.append(hint_block(t))
        for lt, cond, ans, sol in t["variants"]:
            parts.append(f'<div class="var"><div class="lt">{lt})</div><div>{R(cond)}')
            if teacher:
                parts.append(f'<div class="ans"><span class="k">Ответ:</span> {R(ans)}</div>')
                parts.append(f'<div class="sol">{R(sol)}</div>')
            parts.append("</div></div>")
        if teacher:
            parts.append(f'<div class="trap"><b>Типичная ошибка.</b> {t["trap"]}</div>')
        parts.append("</section>")
    parts.append('<p class="foot">Задачи составлены по типам экзаменационного списка, числа свои.</p></div></body></html>')
    return "".join(parts)


def md(teacher):
    out = ["# Аттестация: аналоги задач 1–11" + (" — ответы и решения" if teacher else ""), ""]
    out.append("Сгенерировано `build.py` — править там, а не здесь." if teacher
               else "Для ученика, без ответов. Сгенерировано `build.py`. Ответы — в `OTVETY.md`.")
    out.append("")
    for t in TASKS:
        out += ["---", "", f"## {t['n']}. {t['title']}", ""]
        if not teacher:
            out += [f"*Как решать.* {T(t['hint'])}", ""]
        for lt, cond, ans, sol in t["variants"]:
            out.append(f"**{t['n']}{lt}.** {T(cond)}")
            out.append("")
            if teacher:
                out += [f"**Ответ:** {T(ans)}", "", f"_{T(sol)}_", ""]
        if teacher:
            out += [f"> **Типичная ошибка.** {t['trap']}", ""]
    return "\n".join(out)


(HERE / "print-uchenik.html").write_text(page(False), encoding="utf-8")
(HERE / "print-prepod.html").write_text(page(True), encoding="utf-8")
(HERE / "ZADACHI.md").write_text(md(False), encoding="utf-8")
(HERE / "OTVETY.md").write_text(md(True), encoding="utf-8")
print("собрано: print-uchenik.html, print-prepod.html, ZADACHI.md, OTVETY.md")
