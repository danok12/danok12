# -*- coding: utf-8 -*-
"""HTTP-мост для Claude через pyRevit Routes (http://127.0.0.1:48884/kvv/...).

GET  /kvv/status/           — Revit, активный документ и вид, список кнопок;
POST /kvv/run/   {button}   — выполнить кнопку вкладки «Курсовой ВиВ» по номеру («05») и вернуть её журнал;
POST /kvv/save/             — сохранить активный документ.

Произвольный код мост не выполняет — только кнопки вкладки. Все POST требуют JSON-тело с полем token
из %USERPROFILE%\\.kvv_routes_token (создаётся здесь при первом запуске); тело только application/json,
что заодно закрывает запросы со страниц браузера. Клиент — kursovoy-viv/revit/kvv_cli.py.

Сервер Routes пишет журнал каждого запроса (log_message) и ошибки (handle_error) в stderr из своего потока.
pyRevit открывает на это окно вывода, а WPF-окно не из STA-потока в Revit 2025 (.NET 8) роняет весь Revit
(29.10.2026: упал на первом же GET /kvv/status/). Поэтому _tishina() глушит этот вывод у запущенного сервера:
при первом Idling после загрузки и ещё раз в начале каждого обработчика.
"""
import io
import os
import sys
import time
import traceback
import uuid

from pyrevit import routes, HOST_APP
from pyrevit.coreutils import envvars

# скрипты кнопок делают import kvv — при запуске не с ленты папку lib надо добавить самим
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if LIB not in sys.path:
    sys.path.append(LIB)

TAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), u'Курсовой ВиВ.tab')
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log')
TOKEN_FILE = os.path.join(os.environ['USERPROFILE'], '.kvv_routes_token')


def _token():
    if not os.path.isfile(TOKEN_FILE):
        with io.open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(unicode(uuid.uuid4().hex))
    with io.open(TOKEN_FILE, encoding='utf-8') as f:
        return f.read().strip()


TOKEN = _token()


def _molcha(*a, **k):
    pass


def _tishina():
    """Заглушить вывод потока сервера Routes в stderr (см. описание модуля). True — сервер найден."""
    srv = envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    if srv is None:
        return False
    http = srv.server
    cls = http.RequestHandlerClass
    if not getattr(cls, '_kvv_tiho', False):
        cls.log_message = _molcha
        cls._kvv_tiho = True
    http.handle_error = _molcha
    return True


def _pri_prostoe(sender, args):
    # сервер запускается после startup.py — ждём первый Idling, когда он уже есть
    try:
        if _tishina():
            sender.Idling -= _PROSTOE
    except Exception:
        pass


try:
    from System import EventHandler
    from Autodesk.Revit.UI.Events import IdlingEventArgs
    _PROSTOE = EventHandler[IdlingEventArgs](_pri_prostoe)
    HOST_APP.uiapp.Idling += _PROSTOE
except Exception:
    pass

api = routes.API('kvv')


def _otkaz(request):
    """Ответ-отказ, если тело не JSON или токен неверный; иначе None."""
    data = request.data
    if not isinstance(data, dict) or data.get('token') != TOKEN:
        return routes.make_response(data={'ok': False, 'error': u'нет или неверный token'}, status=403)
    return None


def _knopki():
    """{'05': путь к script.py, ...} по папкам *.pushbutton вкладки."""
    res = {}
    for panel in os.listdir(TAB):
        pdir = os.path.join(TAB, panel)
        if not os.path.isdir(pdir):
            continue
        for btn in os.listdir(pdir):
            script = os.path.join(pdir, btn, 'script.py')
            if btn.endswith('.pushbutton') and os.path.isfile(script):
                res[btn.split(' ')[0]] = script
    return res


@api.route('/status/', methods=['GET'])
def status(uiapp):
    _tishina()
    uidoc = uiapp.ActiveUIDocument
    doc = uidoc.Document if uidoc else None
    return {
        'ok': True,
        'revit': uiapp.Application.VersionName,
        'doc': doc.Title if doc else None,
        'path': doc.PathName if doc else None,
        'modified': doc.IsModified if doc else None,
        'view': uidoc.ActiveView.Name if uidoc else None,
        'buttons': sorted(_knopki().keys()),
    }


@api.route('/run/', methods=['POST'])
def run(request, uiapp):
    _tishina()
    otkaz = _otkaz(request)
    if otkaz:
        return otkaz
    nomer = unicode(request.data.get('button', '')).strip()
    knopki = _knopki()
    if nomer not in knopki:
        return routes.make_response(data={'ok': False, 'error': u'нет кнопки ' + nomer,
                                          'buttons': sorted(knopki.keys())}, status=404)
    start = time.time()
    script = knopki[nomer]
    try:
        execfile(script, {'__name__': '__main__', '__file__': script})
        oshibka = None
    except Exception:
        oshibka = traceback.format_exc()
    # журнал кнопки — файлы revit/log, изменённые за время запуска
    zhurnaly = {}
    for nm in os.listdir(LOG_DIR):
        p = os.path.join(LOG_DIR, nm)
        if os.path.isfile(p) and nm.endswith('.txt') and os.path.getmtime(p) >= start - 1:
            with io.open(p, encoding='utf-8') as f:
                zhurnaly[nm] = f.read()
    return {'ok': oshibka is None, 'error': oshibka, 'seconds': round(time.time() - start, 1), 'logs': zhurnaly}


@api.route('/save/', methods=['POST'])
def save(request, uiapp):
    _tishina()
    otkaz = _otkaz(request)
    if otkaz:
        return otkaz
    doc = uiapp.ActiveUIDocument.Document
    doc.Save()
    return {'ok': True, 'doc': doc.Title}
