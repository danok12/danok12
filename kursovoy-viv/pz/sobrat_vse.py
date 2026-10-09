# -*- coding: utf-8 -*-
"""Сборка пояснительной записки целиком: генератор (sobrat_pz.py) -> PDF через Word (pdf_word.ps1) -> номера
страниц заголовков из PDF -> оглавление -> повторная сборка, пока номера не перестанут меняться.

python sobrat_vse.py  ->  pz/«Пояснительная записка — Буев Д.Р. — ВиВ вариант 3.docx» и «….pdf»
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
SB = os.path.join(HERE, "_sborka")
IMYA = "Пояснительная записка — Буев Д.Р. — ВиВ вариант 3"
DOCX, PDF = os.path.join(SB, "osnova.docx"), os.path.join(SB, "zapiska.pdf")


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def sborka():
    for f in glob.glob(os.path.join(SB, "~$*")) + glob.glob(os.path.join(HERE, "~$*")):
        os.remove(f)                    # блокировки Word от прерванных запусков
    subprocess.run([sys.executable, os.path.join(HERE, "sobrat_pz.py")], check=True)
    if os.path.exists(PDF):
        os.remove(PDF)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(HERE, "pdf_word.ps1"), "-Docx", DOCX, "-Pdf", PDF],
                       capture_output=True, text=True, encoding="cp866", errors="replace")
    print(" ".join(r.stdout.split()))
    assert os.path.exists(PDF), "Word не выгрузил PDF"


def stranicy():
    zag = json.load(open(os.path.join(SB, "zagolovki.json"), encoding="utf-8"))
    d = fitz.open(PDF)
    teksty = [norm(p.get_text()) for p in d]
    i_ogl = next(i for i, t in enumerate(teksty) if "ОГЛАВЛЕНИЕ" in t)
    while i_ogl + 1 < len(teksty) and not teksty[i_ogl + 1].lstrip("0123456789 ").startswith("ВВЕДЕНИЕ"):
        i_ogl += 1                      # оглавление на нескольких страницах
    res, start = {}, i_ogl + 1
    for z in zag:
        kl = norm(z)[:30]
        for i in range(start, len(teksty)):
            if kl in teksty[i]:
                res[z] = i + 1
                start = i
                break
        else:
            raise RuntimeError("заголовок не найден в PDF: " + z)
    json.dump(res, open(os.path.join(SB, "stranicy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return res, len(d)


if __name__ == "__main__":
    s_old, n = None, 0
    for prohod in (1, 2, 3):
        sborka()
        s_new, n = stranicy()
        print("проход", prohod, "| страниц", n, "|", ", ".join("%s: %d" % (k[:16], v) for k, v in s_new.items()))
        if s_new == s_old:
            break
        s_old = s_new
    shutil.copyfile(DOCX, os.path.join(HERE, IMYA + ".docx"))
    shutil.copyfile(PDF, os.path.join(HERE, IMYA + ".pdf"))
    print("готово:", IMYA, "| страниц", n)
