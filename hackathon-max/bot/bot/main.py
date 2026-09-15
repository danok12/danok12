"""Процесс чат-бота: приём обновлений MAX и доставка сообщений из очереди API.

Два независимых цикла в одном процессе:
  * polling  — забирает обновления у MAX и отвечает пользователю;
  * outbox   — забирает готовые сообщения у API (карточка разбора,
               напоминание о сроке) и отправляет их в чат.

Падение одного цикла не останавливает другой: каждый перехватывает свои
ошибки и продолжает работу после паузы.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time

from .api_client import ApiClient, ApiError
from .dialog import Dialog
from .max_api import MaxApiError, MaxClient, button_callback, button_miniapp, parse_update

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("profil10.bot")

STOP = threading.Event()


def outbox_loop(max_client: MaxClient, api: ApiClient, period: float = 2.0) -> None:
    """Доставка отложенных сообщений: карточка разбора и напоминание о сроке."""
    while not STOP.is_set():
        try:
            for item in api.take_outbox():
                text = item["payload"].get("text", "")
                buttons = None
                if item["kind"] == "decision_card":
                    buttons = [[button_callback("Пересчитать с другими направлениями", "menu:open")],
                               [button_callback("Не напоминать о сроке", "reminder:off")]]
                elif item["kind"] == "reminder":
                    buttons = [[button_callback("Открыть подбор", "menu:open")]]
                try:
                    max_client.send_message(item["chat_id"], text, buttons)
                    api.ack_outbox(item["id"], ok=True)
                except MaxApiError as exc:
                    log.warning("Не удалось отправить сообщение %s: %s", item["id"], exc)
                    api.ack_outbox(item["id"], ok=False)
        except ApiError as exc:
            log.warning("Очередь недоступна: %s", exc)
        except Exception:  # noqa: BLE001 - цикл не должен умирать
            log.exception("Ошибка цикла доставки")
        STOP.wait(period)


def polling_loop(max_client: MaxClient, api: ApiClient, dialog: Dialog) -> None:
    """Длинный опрос обновлений MAX."""
    backoff = 1.0
    while not STOP.is_set():
        try:
            updates = max_client.get_updates(timeout=int(os.getenv("POLL_TIMEOUT", "30")))
            backoff = 1.0
        except MaxApiError as exc:
            log.warning("MAX API недоступен (%s), повтор через %.0f с", exc, backoff)
            STOP.wait(backoff)
            backoff = min(backoff * 2, 60)
            continue
        for raw in updates:
            event = parse_update(raw)
            if not event or not event["chat_id"]:
                continue
            try:
                text, buttons = dialog.handle(event)
                if event.get("callback_id"):
                    max_client.answer_callback(event["callback_id"], text, buttons)
                else:
                    max_client.send_message(event["chat_id"], text, buttons)
            except MaxApiError as exc:
                log.warning("Ответ не доставлен: %s", exc)
            except Exception:  # noqa: BLE001 - один сбойный апдейт не роняет бота
                log.exception("Ошибка обработки обновления")
                try:
                    max_client.send_message(
                        event["chat_id"],
                        "⚠️ Не получилось обработать действие. Попробуйте ещё раз или нажмите /start.",
                        [[button_callback("Начать заново", "menu:restart")]],
                    )
                except MaxApiError:
                    pass


def main() -> None:
    token = os.getenv("MAX_BOT_TOKEN", "")
    api = ApiClient()
    max_client = MaxClient(token, base_url=os.getenv("MAX_API_BASE", "https://botapi.max.ru"))

    # Ждём готовности API: контейнеры стартуют одновременно.
    for attempt in range(30):
        try:
            api.class_info(os.getenv("HEALTHCHECK_CLASS", "9A-114"))
            break
        except ApiError as exc:
            log.info("Жду API (%s), попытка %d", exc, attempt + 1)
            time.sleep(2)
    else:
        log.error("API не отвечает — бот запускается, но сценарий будет отдавать ошибку")

    identity: dict = {}
    try:
        me = max_client.get_me()
        identity = {"bot_username": me.get("username"), "bot_id": me.get("user_id")}
        log.info("Бот подключён к MAX: %s (id %s)", me.get("username") or me.get("name"), me.get("user_id"))
    except MaxApiError as exc:
        log.error("Не удалось подтвердить токен в MAX: %s", exc)

    dialog = Dialog(api, bot_identity=identity)

    def stop(*_: object) -> None:
        log.info("Получен сигнал остановки")
        STOP.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    threads = [
        threading.Thread(target=outbox_loop, args=(max_client, api), daemon=True, name="outbox"),
        threading.Thread(target=polling_loop, args=(max_client, api, dialog), daemon=True, name="polling"),
    ]
    for t in threads:
        t.start()
    log.info("Бот запущен")
    while not STOP.is_set():
        STOP.wait(1)
    log.info("Бот остановлен")


if __name__ == "__main__":
    main()
