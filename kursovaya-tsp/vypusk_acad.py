"""Выпуск чертежей средствами AutoCAD: каждый лист - отдельные DWG и PDF в папке «Чертежи».

Работает через accoreconsole.exe (AutoCAD без окна). Для каждого листа из
План_ЛНР_вариант2.dxf делается копия только с этим листом; AutoCAD печатает его
по параметрам печати листа (A3, DWG To PDF, acad.ctb), делает AUDIT и сохраняет
DWG. Проверки: AUDIT без ошибок, в PDF только шрифт GOST type B (AutoCAD молча
печатает Arial, если шрифт не установлен для всех пользователей). PNG для
просмотра рисуются из этих PDF - это вид листов ровно таким, каким его печатает AutoCAD.

    python vypusk_acad.py
"""
import re
import shutil
import subprocess
from pathlib import Path
import ezdxf
import pymupdf

ACAD = Path(r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe")
HERE = Path(__file__).resolve().parent
SRC = HERE / "План_ЛНР_вариант2.dxf"
OUT = HERE / "Чертежи"
WORK = HERE / "_acad"                 # латинский путь: скрипт AutoCAD пишется в ASCII
SHEETS = {
    "Лист 1": "Лист 1. План площадки с рабочими отметками и ЛНР (черновик)",
    "Лист 2": "Лист 2. План площадки с окончательными рабочими отметками и обводами",
    "Лист 3": "Лист 3. Продольный и поперечный разрезы площадки по котловану",
    "Лист 4": "Лист 4. Картограмма перемещения земляных масс",
    "Лист 5": "Лист 5. Схема производства работ по вертикальной планировке",
    "Лист 1 (первый)": "Лист 1 (первый вариант). План площадки с рабочими отметками и ЛНР",
}

if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir()
OUT.mkdir(exist_ok=True)
w = WORK.as_posix()
SCR = [
    '(setvar "FILEDIA" 0)',
    '(setvar "CMDDIA" 0)',
    '(setvar "EXPERT" 5)',
    # единственный лист копии; имя - ключ словаря (код 3), layoutlist в accoreconsole нет
    '(foreach p (dictsearch (namedobjdict) "ACAD_LAYOUT")'
    ' (if (= (car p) 3) (setq nm (cdr p)))'
    ' (if (and (= (car p) 350) (/= nm "Model")) (setq lay nm)))',
    '(setvar "CTAB" lay)',
    f'(command "_.-PLOT" "_N" "" "" "" "{w}/sheet.pdf" "_N" "_Y")',
    "_.AUDIT _N",                     # проверка базы чертежа самим AutoCAD, без исправлений
    f'(command "_.SAVEAS" "2018" "{w}/sheet.dwg")',
    "",
]
(WORK / "vypusk.scr").write_text("\n".join(SCR), encoding="ascii")

for k, (layout, title) in enumerate(SHEETS.items(), start=1):
    doc = ezdxf.readfile(SRC)
    for name in [n for n in doc.layouts.names() if n not in ("Model", layout)]:
        doc.layouts.delete(name)
    doc.saveas(WORK / "sheet.dxf")
    for ext in ("pdf", "dwg"):
        (WORK / f"sheet.{ext}").unlink(missing_ok=True)
    r = subprocess.run([str(ACAD), "/i", str(WORK / "sheet.dxf"), "/s", str(WORK / "vypusk.scr"), "/l", "ru-RU"],
                       capture_output=True, timeout=600)
    log = r.stdout.decode("utf-16-le", errors="replace").replace("\x00", "")
    (WORK / f"accore_{k}.log").write_text(log, encoding="utf-8")
    missing = [p.name for p in (WORK / "sheet.pdf", WORK / "sheet.dwg") if not p.exists()]
    if missing:
        raise SystemExit(f"{layout}: AutoCAD не выпустил {missing}, журнал: {WORK / f'accore_{k}.log'}")
    audit = re.findall(r"найдено ошибок: (\d+)", log)
    if audit != ["0"]:
        raise SystemExit(f"{layout}: AUDIT AutoCAD - ошибок {audit or '?'}, журнал: {WORK / f'accore_{k}.log'}")
    pdf = pymupdf.open(WORK / "sheet.pdf")
    fonts = {fn[3] for page in pdf for fn in page.get_fonts()}
    if not fonts or any("typeb" not in fn.replace(" ", "").replace("-", "").lower() for fn in fonts):
        raise SystemExit(f"{layout}: в PDF не GOST type B, а {sorted(fonts)}: шрифт GOST_B.TTF должен быть "
                         "установлен для всех пользователей (C:\\Windows\\Fonts)")
    pdf[0].get_pixmap(dpi=150).save(HERE / f"preview_list{k}.png")
    pdf.close()
    try:
        shutil.copy(WORK / "sheet.pdf", OUT / f"{title}.pdf")
        shutil.copy(WORK / "sheet.dwg", OUT / f"{title}.dwg")
    except PermissionError:
        raise SystemExit(f"«{title}» открыт в AutoCAD или просмотрщике - закройте и запустите снова")
    print(f"{layout}: DWG и PDF -> Чертежи/{title}")
