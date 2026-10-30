# -*- coding: utf-8 -*-
"""Клиент HTTP-моста kvv.extension/startup.py (pyRevit Routes) — вместо нажатия кнопок через computer use.

    python -I kvv_cli.py start            # запустить Revit с рабочей моделью (если не запущен) и дождаться моста
    python -I kvv_cli.py status           # Revit, документ, вид, список кнопок
    python -I kvv_cli.py run 05           # выполнить кнопку «05 Система В1», напечатать её журнал
    python -I kvv_cli.py save             # сохранить модель
    ... run 05 --lyubaya                  # разрешить кнопку не на рабочей модели (по умолчанию — отказ)

Revit должен быть запущен с открытой моделью, в pyRevit включён Routes (pyRevit_config.ini: [routes] enabled = true).
Токен — %USERPROFILE%\\.kvv_routes_token, его создаёт startup.py при загрузке pyRevit.

Запросы идут строго по одному (блокировка %USERPROFILE%\\.kvv_routes.lock): у pyRevit Routes один общий обработчик
на все запросы, и при двух одновременных оба клиента получают ответ первого, а второй запрос выполняется молча позже.
"""
import json
import msvcrt
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

URL = 'http://127.0.0.1:48884/kvv/'
TOKEN_FILE = os.path.join(os.environ['USERPROFILE'], '.kvv_routes_token')
LOCK_FILE = os.path.join(os.environ['USERPROFILE'], '.kvv_routes.lock')
# рабочая модель — копия на рабочем столе (в worktree лежит устаревшая от 05.10)
RABOCHAYA = os.path.join(os.environ['USERPROFILE'], 'Desktop', 'Курсовой ВиВ вариант 3', 'revit', 'model',
                         'KR_ViV_v3.rvt')


REVIT_EXE = r'C:\Program Files\Autodesk\Revit 2025\Revit.exe'


def revit_zapushchen():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Revit.exe', '/NH'], capture_output=True,
                         text=True, encoding='cp866', errors='replace').stdout
    return 'Revit.exe' in out


def start():
    """Запустить Revit с рабочей моделью (второй экземпляр не открывать) и ждать моста до 10 мин."""
    if not revit_zapushchen():
        subprocess.Popen([REVIT_EXE, RABOCHAYA], creationflags=subprocess.DETACHED_PROCESS)
        print('Revit запущен с', RABOCHAYA)
    else:
        print('Revit уже запущен')
    for _ in range(120):
        try:
            with urllib.request.urlopen(URL + 'status/', timeout=30) as r:
                st = json.loads(r.read().decode('utf-8'))
            if st.get('path'):
                return st
        except (urllib.error.URLError, OSError, ValueError):
            pass
        if not revit_zapushchen():
            sys.exit('Revit закрылся при запуске')
        time.sleep(5)
    sys.exit('Мост не ответил за 10 минут (диалог в Revit?)')


def zapros(put, data=None, timeout=1800):
    req = urllib.request.Request(URL + put + '/')
    if data is not None:
        with open(TOKEN_FILE, encoding='utf-8') as f:
            data['token'] = f.read().strip()
        req.data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8') or '{}') | {'http': e.code}
    except urllib.error.URLError as e:
        sys.exit('Нет связи с Revit (%s): запущен ли Revit и включён ли pyRevit Routes?' % e.reason)


def ta_zhe(path):
    """Открыт ли в Revit именно рабочий файл (тот же файл на диске, а не совпадение строк пути)."""
    try:
        return bool(path) and os.path.samefile(path, RABOCHAYA)
    except OSError:
        return False


def zamok():
    """Межпроцессная блокировка: ждать, пока другой клиент не закончит (до 30 мин)."""
    f = open(LOCK_FILE, 'a+')
    for _ in range(1800):
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            return f
        except OSError:
            time.sleep(1)
    sys.exit('Мост занят другим клиентом больше 30 минут')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    lyubaya = '--lyubaya' in sys.argv
    cmd = args[0] if args else 'status'
    if cmd not in ('start', 'status', 'run', 'save') or (cmd == 'run' and len(args) < 2):
        sys.exit(__doc__)
    _z = zamok()
    if cmd == 'start':
        st = start()
        ok = ta_zhe(st.get('path'))
        print(json.dumps(st | {'ok': ok}, ensure_ascii=False, indent=2))
        sys.exit(0 if ok else 'Открыта не рабочая модель: %s' % st.get('path'))
    st = zapros('status')
    if cmd == 'status':
        res = st
        if not ta_zhe(st.get('path')):
            res['preduprezhdenie'] = 'открыта не рабочая модель; рабочая — ' + RABOCHAYA
    else:
        if not lyubaya and not ta_zhe(st.get('path')):
            sys.exit('Открыта не рабочая модель: %s\nРабочая: %s\n(--lyubaya — запустить всё равно)'
                     % (st.get('path'), RABOCHAYA))
        if cmd == 'run':
            res = zapros('run', {'button': args[1]})
            if res.get('button', args[1]) != args[1]:
                res['ok'] = False
                res['error'] = 'пришёл ответ чужого запроса (кнопка %s)' % res.get('button')
            for nm, txt in sorted(res.pop('logs', {}).items()):
                print('=== %s\n%s' % (nm, txt))
                # kvv.run перехватывает исключения кнопки и пишет их в журнал — сервер о них не знает
                if 'ОШИБКА:' in txt:
                    res['ok'] = False
                    res['error'] = res.get('error') or 'ОШИБКА в журнале %s' % nm
        else:
            res = zapros('save', {})
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res.get('ok') else 1)


if __name__ == '__main__':
    main()
