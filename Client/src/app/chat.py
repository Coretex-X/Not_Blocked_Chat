"""
chat.py — главный файл: собирает всё вместе и отдаёт ft.View пользователю.

Структура проекта:
    chat_db.py         — работа с базой данных SQLite
    chat_connection.py — WebSocket-соединение и очередь сообщений
    chat_ui.py         — все UI-компоненты, диалоги, пузыри, файлы, голос
    chat.py            — точка входа, маршрут /chat
"""

import flet as ft
from .components.chat.chat_meneger import get_chat_id, get_status_chat
from .components.chat import chat_db as db
from .components.chat import chat_connection as conn
from .components.database import get_contact_id_by_chat
from .components.chat.chat_ui import ChatUI
import path
# ─────────────────────────── Идентификаторы ───────────────────────────────────

# ─────────────────────────── Главная функция ──────────────────────────────────

def chat_view(page: ft.Page) -> ft.View:
    """Возвращает ft.View для маршрута /chat."""

    # Получаем данные собеседника из БД
    chat_id = get_chat_id()
    status_chat = get_status_chat()
    #result  = db.db_user_data(chat_id)

    db_path = f"{path.db_path()}user_data.db"
    contact_id = get_contact_id_by_chat(db_path, chat_id)  # получаем contact_id из chats
    my_id = db.db_user()  # получаем my_id из users_data
    my_id = my_id[0]
    result = db.db_user_data(contact_id) if contact_id else None

    # Защита от None
    if result is None:
        contact_name  = "Неизвестный"
        contact_phone = "—"
        contact_about = "—"
    else:
        contact_name  = result[1]
        contact_phone = result[3]
        contact_about = result[2]

    contact_user = {
        "id":           contact_id,
        "name":         contact_name,
        "avatar_color": ft.Colors.GREY,
        "phone":        contact_phone,
        "about":        contact_about,
        "last_seen":    "None",
    }

    CURRENT_USER = {
        "id":           my_id,
        "name":         "None",
        "avatar_color": ft.Colors.GREY,
        "phone":        "None",
        "status":       "None",
        "about":        "None",
    }
    
    # Запускаем WebSocket-соединение при загрузке модуля
    conn.start_connection(my_id, contact_id, status_chat)

    # Создаём объект UI (строит все виджеты внутри)
    ui = ChatUI(page, CURRENT_USER, contact_user)

    # Регистрируем FilePicker в overlay страницы
    page.overlay.append(ui.file_picker)
    page.update()

    # Публикуем хуки для входящих сообщений (используются снаружи при необходимости)
    page.data = {
        "add_incoming_text": lambda text, sid=None: ui.add_message_to_chat(
            ui.create_text_message(text, is_user=(sid == CURRENT_USER["id"]))),

        "add_incoming_image": lambda path, name, sid=None, ot=False: ui.add_message_to_chat(
            ui.create_image_message(path, name,
                                    is_user=(sid == CURRENT_USER["id"]),
                                    one_time_view=ot)),

        "add_incoming_video": lambda path, name, sid=None: ui.add_message_to_chat(
            ui.create_video_message(path, name,
                                    is_user=(sid == CURRENT_USER["id"]))),

        "add_incoming_audio": lambda path, name, sid=None: ui.add_message_to_chat(
            ui.create_audio_message(path, name,
                                    is_user=(sid == CURRENT_USER["id"]))),

        "add_incoming_document": lambda path, name, sid=None, ftype="Файл": ui.add_message_to_chat(
            ui.create_document_message(path, name, ftype,
                                       is_user=(sid == CURRENT_USER["id"]))),
    }

    # Запускаем опрос очереди входящих сообщений
    ui.poll_queue()

    # ── Сборка страницы ────────────────────────────────────────────────────────
    return ft.View(
        "/chat",
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        ui.chat_header,
                        ft.Container(
                            content=ui.messages_column,
                            expand=True,
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                        ),
                        ui.voice_panel,
                        ui.input_bar,
                    ],
                    expand=True,
                ),
            )
        ],
        padding=0,
        bgcolor=ft.Colors.WHITE,
    )
