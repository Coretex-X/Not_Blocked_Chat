import flet as ft
import path
from .components.chat.chat_manager import get_chat_id, get_status_chat
from .components.chat import chat_db as db
from .components.chat import chat_connection as conn
from .components.database import get_contact_id_by_chat, get_contact_display_name
from .components.chat.chat_ui import ChatUI
from .components.utils import format_phone


def chat_view(page: ft.Page) -> ft.View:
    db_path    = f"{path.db_path()}user_data.db"
    chat_id    = get_chat_id()
    status     = get_status_chat()
    contact_id = get_contact_id_by_chat(db_path, chat_id)
    my_id      = db.get_current_user_id()
    contact    = db.get_contact_data(contact_id) if contact_id else None

    if contact is None:
        contact_name  = "Неизвестный"
        contact_phone = "—"
        contact_about = "—"
    else:
        contact_name  = get_contact_display_name(db_path, contact_id)
        contact_phone = format_phone(str(contact[3]))
        contact_about = contact[2]

    contact_user = {
        "id":           contact_id,
        "name":         contact_name,
        "avatar_color": ft.Colors.GREY,
        "phone":        contact_phone,
        "about":        contact_about,
        "last_seen":    "None",
    }
    current_user = {
        "id":           my_id,
        "name":         "None",
        "avatar_color": ft.Colors.GREY,
        "phone":        "None",
        "status":       "None",
        "about":        "None",
    }

    conn.start_connection(my_id, contact_id, status)

    # Передаём chat_id в ChatUI для сохранения/загрузки истории
    ui = ChatUI(page, current_user, contact_user, chat_id=chat_id)

    page.overlay.append(ui.file_picker)
    page.update()

    # Колбэки для входящих сообщений (используются извне при необходимости)
    page.data = {
        "add_incoming_text": lambda text, sid=None: ui.add_message_to_chat(
            ui.create_text_message(text, is_user=(sid == my_id))),
        "add_incoming_image": lambda path, name, sid=None, ot=False: ui.add_message_to_chat(
            ui.create_image_message(path, name, is_user=(sid == my_id), one_time_view=ot)),
        "add_incoming_video": lambda path, name, sid=None: ui.add_message_to_chat(
            ui.create_video_message(path, name, is_user=(sid == my_id))),
        "add_incoming_audio": lambda path, name, sid=None: ui.add_message_to_chat(
            ui.create_audio_message(path, name, is_user=(sid == my_id))),
        "add_incoming_document": lambda path, name, sid=None, ftype="Файл": ui.add_message_to_chat(
            ui.create_document_message(path, name, ftype, is_user=(sid == my_id))),
    }

    ui.poll_queue()

    return ft.View(
        "/chat",
        controls=[ft.Container(
            expand=True,
            content=ft.Column([
                ui.chat_header,
                ft.Container(content=ui.messages_column, expand=True,
                             padding=10),
                ui.voice_panel,
                ui.input_bar,
            ], expand=True),
        )],
        padding=0,
    )