"""Выпуск чертежа средствами AutoCAD: DXF -> DWG и PDF (оба листа), PNG для проверки.

Работает через accoreconsole.exe (AutoCAD без окна): открывает DXF, печатает
каждый лист по его параметрам печати (A3, DWG To PDF, acad.ctb), сохраняет DWG.
Листы склеиваются в один PDF; PNG рисуются из этого PDF, то есть это
вид листов ровно таким, каким его печатает AutoCAD.

    python vypusk_acad.py
"""
import re
import shutil
import subprocess
from pathlib import Path
import pymupdf

ACAD = Path(r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe")
HERE = Path(__file__).resolve().parent
STEM = "План_ЛНР_вариант2"
WORK = HERE / "_acad"                 # латинский путь: скрипт AutoCAD пишется в ASCII
SHEETS = 2

if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir()
shutil.copy(HERE / f"{STEM}.dxf", WORK / "plan.dxf")
w = WORK.as_posix()
scr = [
    '(setvar "FILEDIA" 0)',
    '(setvar "CMDDIA" 0)',
    '(setvar "EXPERT" 5)',
    # листы по порядку вкладок (код 71); имя - ключ словаря (код 3); layoutlist в accoreconsole нет
    "(setq lays nil)",
    '(foreach p (dictsearch (namedobjdict) "ACAD_LAYOUT")'
    " (if (= (car p) 3) (setq nm (cdr p)))"
    ' (if (and (= (car p) 350) (/= nm "Model"))'
    " (setq lays (cons (cons (cdr (assoc 71 (entget (cdr p)))) nm) lays))))",
    "(setq k 0 o 0)",
    "(repeat 64 (setq o (1+ o)) (if (setq nm (cdr (assoc o lays)))"
    ' (progn (setq k (1+ k)) (setvar "CTAB" nm)'
    f' (command "_.-PLOT" "_N" "" "" "" (strcat "{w}/list" (itoa k) ".pdf") "_N" "_Y"))))',
    "_.AUDIT _N",                     # проверка базы чертежа самим AutoCAD, без исправлений
    f'(command "_.SAVEAS" "2018" "{w}/plan.dwg")',
    "",
]
(WORK / "vypusk.scr").write_text("\n".join(scr), encoding="ascii")
r = subprocess.run([str(ACAD), "/i", str(WORK / "plan.dxf"), "/s", str(WORK / "vypusk.scr"), "/l", "ru-RU"],
                   capture_output=True, timeout=600)
log = r.stdout.decode("utf-16-le", errors="replace").replace("\x00", "")
(WORK / "accore.log").write_text(log, encoding="utf-8")

pdfs = [WORK / f"list{k}.pdf" for k in range(1, SHEETS + 1)]
missing = [p.name for p in pdfs + [WORK / "plan.dwg"] if not p.exists()]
if missing:
    raise SystemExit(f"AutoCAD не выпустил {missing}, журнал: {WORK / 'accore.log'}")
audit = re.findall(r"найдено ошибок: (\d+)", log)
if audit != ["0"]:
    raise SystemExit(f"AUDIT AutoCAD: ошибок {audit or '?'}, журнал: {WORK / 'accore.log'}")
if re.search(r"[Шш]рифт.*(не найден|замен)", log):
    raise SystemExit(f"AutoCAD подменил шрифт, журнал: {WORK / 'accore.log'}")

out = pymupdf.open()
for p in pdfs:
    out.insert_pdf(pymupdf.open(p))
# AutoCAD молча подставляет Arial, если шрифта нет в C:\Windows\Fonts
# (установленные только для пользователя он не видит) - проверяем сам PDF
fonts = {fn[3] for page in out for fn in page.get_fonts()}
if not fonts or any("typeb" not in fn.replace(" ", "").replace("-", "").lower() for fn in fonts):
    raise SystemExit(f"в PDF не GOST type B, а {sorted(fonts)}: шрифт GOST_B.TTF должен быть "
                     "установлен для всех пользователей (C:\\Windows\\Fonts)")
out.save(HERE / f"{STEM}.pdf")
for k, page in enumerate(pymupdf.open(HERE / f"{STEM}.pdf"), start=1):
    png = HERE / (f"{STEM}_preview.png" if k == 1 else f"{STEM}_list{k}_preview.png")
    page.get_pixmap(dpi=150).save(png)
try:
    shutil.copy(WORK / "plan.dwg", HERE / f"{STEM}.dwg")
except PermissionError:
    raise SystemExit(f"{STEM}.dwg открыт в AutoCAD - закройте его и запустите снова (PDF и PNG уже обновлены)")
print("AutoCAD:", f"{STEM}.dwg,", f"{STEM}.pdf ({len(pdfs)} листа), PNG по листам")
