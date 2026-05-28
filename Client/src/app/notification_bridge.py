# notification_bridge.py
# Посредник между main.py и menu.py — разрывает циклический импорт.
# main.py и menu.py оба импортируют этот модуль, но не друг друга.

_on_notification_callback = None


def set_notification_callback(cb):
    """menu.py регистрирует колбэк для обновления счётчика непрочитанных."""
    global _on_notification_callback
    _on_notification_callback = cb


def fire_notification(chat_id: int):
    """main.py вызывает это при получении нового уведомления."""
    if _on_notification_callback:
        try:
            _on_notification_callback(chat_id)
        except Exception as ex:
            print(f"[УВЕДОМЛЕНИЕ] Ошибка колбэка: {ex}")