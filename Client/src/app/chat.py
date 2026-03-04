"""
Chat Messenger — чистая и читаемая версия
"""

import flet as ft
import datetime
import os
import shutil
import json
import time
import base64
import websocket
import threading
import queue
import sqlite3
import path  # ваш модуль с путями


db_path = f"{path.db_path()}user_data.db"

# ─────────────────────────── Константы ────────────────────────────────────────

INCOMING_FOLDER = "assets/data.media/incoming_files"
ASSETS_FOLDER   = "assets/data.media/assets"
VOICE_FOLDER    = "assets/data.media/voice_recordings"
SETTINGS_FILE   = "chat_settings.json"
WS_URL_DATA     = "ws://127.0.0.1:5000/ws/data/"
WS_URL_CHAT     = "ws://127.0.0.1:5000/ws/chat_user/api87/"
FILE_SEPARATOR  = b"|||BINARY_DATA|||"
MAX_FILE_SIZE   = 50 * 1024 * 1024  # 50 МБ

IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS  = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
AUDIO_EXTS  = {".mp3", ".wav", ".ogg", ".m4a"}

for folder in (INCOMING_FOLDER, ASSETS_FOLDER, VOICE_FOLDER):
    os.makedirs(folder, exist_ok=True)

# ─────────────────────────── Данные пользователей ─────────────────────────────

MY_ID      = "None"
CONTACT_ID = "None"

CURRENT_USER = {
    "id": MY_ID,
    "name": "None",
    "avatar_color": ft.Colors.GREY,
    "phone": "None",
    "status": "None",
    "about": "None",
}

CONTACT_USER = {
    "id": CONTACT_ID,
    "name": "None",
    "avatar_color": ft.Colors.GREY,
    "phone": "None",
    "status": "None",
    "about": "None",
    "last_seen": "None",
}

# ─────────────────────────── WebSocket ────────────────────────────────────────

message_queue: queue.Queue = queue.Queue()
ws: websocket.WebSocket | None = None
running = True


def authenticate():
    """Регистрирует чат-комнату на сервере."""
    conn = websocket.WebSocket()
    conn.connect(WS_URL_DATA)
    conn.send(json.dumps({
        "room": "None",
        "user_id": MY_ID,
        "guest_id": CONTACT_ID,
        "status_chat": "existing_chat",
        "token": "api87",
    }))
    conn.close()


def receive_messages():
    """Фоновый поток: читает сообщения из WebSocket и кладёт в очередь."""
    global running
    while running:
        try:
            raw = ws.recv()

            # Если данные текстовые — это JSON-сообщение
            if isinstance(raw, str):
                message_queue.put(json.loads(raw))

            # Если данные бинарные — это файл: метаданные + разделитель + байты файла
            elif isinstance(raw, bytes):
                sep_pos = raw.find(FILE_SEPARATOR)
                if sep_pos == -1:
                    print("❌ Не найден разделитель в бинарных данных")
                    continue
                metadata   = json.loads(raw[:sep_pos].decode("utf-8"))
                file_bytes = raw[sep_pos + len(FILE_SEPARATOR):]
                message_queue.put({
                    "type":      "file",
                    "file_name": metadata.get("file_name", "unknown"),
                    "file_type": metadata.get("file_type", "unknown"),
                    "file_size": metadata.get("file_size", len(file_bytes)),
                    "file_data": base64.b64encode(file_bytes).decode("utf-8"),
                    "sender_id": metadata.get("sender_id"),
                })
        except websocket.WebSocketConnectionClosedException:
            print("❌ WebSocket соединение закрыто")
            break
        except Exception as e:
            import traceback
            print(f"❌ Ошибка получения сообщения: {e}")
            traceback.print_exc()
            break


# Запускаем соединение и фоновый поток
authenticate()
ws = websocket.WebSocket()
ws.connect(WS_URL_CHAT)
threading.Thread(target=receive_messages, daemon=True).start()


# ─────────────────────────── Вспомогательные функции ──────────────────────────

def get_file_ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def get_file_type(filename: str) -> str:
    ext = get_file_ext(filename)
    if ext in IMAGE_EXTS:  return "image"
    if ext in VIDEO_EXTS:  return "video"
    if ext in AUDIO_EXTS:  return "audio"
    return "document"


def format_file_size(path: str) -> str:
    try:
        size = os.path.getsize(path)
        if size < 1024:             return f"{size} Б"
        if size < 1024 * 1024:      return f"{size / 1024:.1f} КБ"
        return f"{size / (1024 * 1024):.1f} МБ"
    except Exception:
        return "?"


def format_time_seconds(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def now_hm() -> str:
    return datetime.datetime.now().strftime("%H:%M")


# ─────────────────────────── Главная функция ──────────────────────────────────

def chat_view(page: ft.Page) -> ft.View:
    """Возвращает ft.View для маршрута /chat."""

    # Списки сообщений
    messages_column   = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    all_messages:      list = []
    sent_media_files:  list = []
    viewed_once_ids:   list = []

    # Состояние ответа на сообщение
    reply_to: list[str | None] = [None]  # текст цитируемого сообщения

    # Состояние блокировки пользователя
    is_blocked: list[bool] = [False]

    # Настройки автосохранения
    auto_save_folder: list[str | None] = [None]  # обёртка в list для изменения в closure

    # ── Настройки ──────────────────────────────────────────────────────────────

    def load_settings():
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    auto_save_folder[0] = data.get("auto_download_folder")
        except Exception:
            pass

    def save_settings():
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"auto_download_folder": auto_save_folder[0]}, f, ensure_ascii=False)
        except Exception:
            pass

    load_settings()

    # ── Панель ответа на сообщение ─────────────────────────────────────────────

    reply_preview_text = ft.Text("", size=12, color=ft.Colors.GREY_700,
                                  max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    reply_bar = ft.Container(
        visible=False,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.REPLY, color=ft.Colors.BLUE, size=18),
                ft.Column(
                    [ft.Text("Ответ на:", size=11, color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD),
                     reply_preview_text],
                    spacing=0, expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE, icon_size=16, icon_color=ft.Colors.GREY,
                    tooltip="Отменить ответ",
                    on_click=lambda e: cancel_reply(),
                ),
            ],
            spacing=8,
        ),
        bgcolor=ft.Colors.BLUE_50,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.BLUE)),
    )

    def cancel_reply():
        reply_to[0] = None
        reply_bar.visible = False
        reply_bar.update()

    def _apply_block_state():
        pass  # Блокировка только входящих — поле ввода остаётся активным

    def set_reply(text: str):
        reply_to[0] = text
        short = text if len(text) <= 60 else text[:57] + "..."
        reply_preview_text.value = short
        reply_bar.visible = True
        reply_bar.update()
        message_input.focus()
        message_input.update()

    # ── Утилиты UI ─────────────────────────────────────────────────────────────

    def make_avatar(user_data: dict, size: int = 40) -> ft.CircleAvatar:
        """Создаёт круглый аватар с первой буквой имени."""
        letter = (user_data.get("name") or "?")[0].upper()
        return ft.CircleAvatar(
            content=ft.Text(letter, size=size // 2),
            bgcolor=user_data.get("avatar_color", ft.Colors.GREY),
            radius=size // 2,
        )

    def show_snack(text: str):
        page.open(ft.SnackBar(content=ft.Text(text), duration=2000))
        page.update()

    def scroll_to_bottom():
        messages_column.scroll_to(offset=-1, duration=300)

    def add_message_to_chat(widget):
        messages_column.controls.append(widget)
        all_messages.append(widget)
        scroll_to_bottom()
        page.update()

    # ── Файловые операции ──────────────────────────────────────────────────────

    def auto_save_file(src: str, filename: str) -> str:
        """Копирует файл в папку автосохранения, если она задана."""
        folder = auto_save_folder[0]
        if not folder or not os.path.exists(folder):
            return src
        dest = os.path.join(folder, filename)
        counter = 1
        while os.path.exists(dest):
            name, ext = os.path.splitext(filename)
            dest = os.path.join(folder, f"{name}_{counter}{ext}")
            counter += 1
        try:
            shutil.copy2(src, dest)
            return dest
        except Exception as e:
            print(f"❌ Ошибка автосохранения: {e}")
            return src

    def download_file(file_path: str, file_name: str):
        """Диалог сохранения файла через FilePicker."""
        def on_save(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    shutil.copy2(file_path, e.path)
                    show_snack(f"Файл сохранён: {e.path}")
                except Exception as ex:
                    show_snack(f"Ошибка сохранения: {ex}")

        picker = ft.FilePicker(on_result=on_save)
        page.overlay.append(picker)
        page.update()
        picker.save_file(file_name=file_name, dialog_title="Сохранить файл как")

    def select_auto_save_folder(e):
        """Диалог выбора папки для автосохранения."""
        def on_folder_picked(e: ft.FilePickerResultEvent):
            if e.path:
                auto_save_folder[0] = e.path
                save_settings()
                show_snack(f"Папка для сохранения: {e.path}")

        picker = ft.FilePicker(on_result=on_folder_picked)
        page.overlay.append(picker)
        page.update()
        picker.get_directory_path(dialog_title="Выберите папку для автосохранения")

    # ── Диалоговые окна просмотра ──────────────────────────────────────────────

    def open_image_fullscreen(image_path: str, file_name: str):
        def close(e): page.close(dlg)

        dlg = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Image(src=image_path, fit=ft.ImageFit.CONTAIN),
                        ft.Text(file_name, size=14, weight=ft.FontWeight.BOLD),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=600, height=650,
            ),
            actions=[
                ft.TextButton("📥 Скачать", on_click=lambda e: download_file(image_path, file_name)),
                ft.TextButton("Закрыть", on_click=close),
            ],
        )
        page.open(dlg)

    def open_video_viewer(video_path: str, file_name: str):
        def close(e): page.close(dlg)

        dlg = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Video(
                            playlist=[ft.VideoMedia(video_path)],
                            width=600, height=400, show_controls=True,
                        ),
                        ft.Text(file_name, size=14, weight=ft.FontWeight.BOLD),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                width=600,
            ),
            actions=[
                ft.TextButton("📥 Скачать", on_click=lambda e: download_file(video_path, file_name)),
                ft.TextButton("Закрыть", on_click=close),
            ],
        )
        page.open(dlg)

    # ── Контекстное меню сообщения ─────────────────────────────────────────────

    def show_message_menu(msg_widget, text: str, is_user: bool,
                          msg_text_ref=None, edited_tag=None, current_text=None):
        def close(e): page.close(dlg)

        def copy(e):
            page.set_clipboard(text)
            show_snack("📋 Скопировано!")
            page.close(dlg)

        def delete(e):
            delete_message(msg_widget, text)
            page.close(dlg)

        def reply(e):
            set_reply(text)
            page.close(dlg)

        def edit(e):
            page.close(dlg)
            edit_field = ft.TextField(
                value=current_text[0],
                multiline=True, min_lines=1, max_lines=5,
                expand=True, autofocus=True,
            )

            def confirm_edit(e):
                new_text = edit_field.value.strip()
                if not new_text or new_text == current_text[0]:
                    page.close(edit_dlg)
                    return
                # Обновляем текст прямо в пузыре
                current_text[0]            = new_text
                msg_text_ref.current.value = new_text
                edited_tag.value           = "изменено"
                msg_text_ref.current.update()
                edited_tag.update()
                # Отправляем на сервер
                try:
                    ws.send(json.dumps({
                        "type":       "edit",
                        "message":    new_text,
                        "sender_id":  CURRENT_USER["id"],
                        "timestamp":  datetime.datetime.now().timestamp(),
                    }))
                except Exception as ex:
                    print(f"❌ Ошибка отправки правки: {ex}")
                page.close(edit_dlg)
                show_snack("✏️ Сообщение изменено")

            edit_dlg = ft.AlertDialog(
                title=ft.Text("Редактировать сообщение"),
                content=ft.Container(
                    content=edit_field,
                    width=320,
                ),
                actions=[
                    ft.TextButton("Отмена",   on_click=lambda e: page.close(edit_dlg)),
                    ft.TextButton("Сохранить", on_click=confirm_edit,
                                  style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                ],
            )
            page.open(edit_dlg)

        items = [
            ft.TextButton("↩ Ответить", on_click=reply),
            ft.TextButton("📋 Копировать", on_click=copy),
        ]
        if is_user:
            items.append(ft.TextButton("✏️ Редактировать", on_click=edit))
            items.append(ft.TextButton("🗑️ Удалить", on_click=delete))

        dlg = ft.AlertDialog(
            title=ft.Text("Действия"),
            content=ft.Column(items, tight=True),
            actions=[ft.TextButton("Закрыть", on_click=close)],
        )
        page.open(dlg)

    def delete_message(widget, text: str = ""):
        if widget not in messages_column.controls:
            return
        try:
            msg_id = f"msg_{datetime.datetime.now().timestamp()}_{hash(text)}"
            send_delete_command(msg_id, text)
            messages_column.controls.remove(widget)
            if widget in all_messages:
                all_messages.remove(widget)
            messages_column.update()
            show_snack("✅ Сообщение удалено у всех")
        except Exception as e:
            print(f"❌ Ошибка удаления: {e}")

    # ── Создание пузырей сообщений ─────────────────────────────────────────────

    def make_message_row(bubble, is_user: bool, user_data: dict) -> ft.Row:
        """Оборачивает пузырь с аватаром — справа для себя, слева для собеседника."""
        avatar = make_avatar(user_data)
        spacer = ft.Container(expand=True)
        if is_user:
            return ft.Row([spacer, bubble, avatar], vertical_alignment=ft.CrossAxisAlignment.START)
        else:
            return ft.Row([avatar, bubble, spacer], vertical_alignment=ft.CrossAxisAlignment.START)

    def make_bubble_colors(is_user: bool):
        return ft.Colors.BLUE if is_user else ft.Colors.GREY

    def make_bubble_colors_dark(is_user: bool):
        return ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700

    def make_bubble_margin(is_user: bool):
        return ft.margin.only(right=10) if is_user else ft.margin.only(left=10)

    def create_text_message(text: str, is_user: bool = True, quote: str | None = None) -> ft.GestureDetector:
        user_data = CURRENT_USER if is_user else CONTACT_USER
        bubble_children = []

        # Цитата (ответ на сообщение)
        if quote:
            short_quote = quote if len(quote) <= 60 else quote[:57] + "..."
            bubble_children.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Text("↩ Ответ на:", size=10, color=ft.Colors.WHITE70,
                                  weight=ft.FontWeight.BOLD),
                         ft.Text(short_quote, size=12, color=ft.Colors.WHITE70,
                                  italic=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)],
                        tight=True, spacing=1,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.WHITE70)),
                )
            )

        # Ref для редактирования текста
        msg_text_ref  = ft.Ref[ft.Text]()
        edited_tag    = ft.Text("", size=10, color=ft.Colors.WHITE54, italic=True)
        current_text  = [text]  # mutable хранилище актуального текста

        bubble_children += [
            ft.Text(text, color=ft.Colors.WHITE, ref=msg_text_ref),
            ft.Row(
                [
                    edited_tag,
                    ft.Container(expand=True),
                    ft.Text(now_hm(), size=12, color=ft.Colors.WHITE54),
                ],
                spacing=0,
            ),
        ]

        bubble = ft.Container(
            content=ft.Column(bubble_children, tight=True, spacing=4),
            bgcolor=make_bubble_colors(is_user),
            padding=10,
            border_radius=15,
            margin=make_bubble_margin(is_user),
        )
        row = make_message_row(bubble, is_user, user_data)

        def open_menu(e):
            show_message_menu(widget, current_text[0], is_user,
                              msg_text_ref=msg_text_ref,
                              edited_tag=edited_tag,
                              current_text=current_text)

        widget = ft.GestureDetector(
            content=row,
            on_tap=open_menu,
            on_long_press_start=open_menu,
        )
        return widget

    def create_image_message(
        image_path: str, file_name: str,
        is_user: bool = True, one_time_view: bool = False
    ) -> ft.GestureDetector:
        user_data  = CURRENT_USER if is_user else CONTACT_USER
        message_id = f"img_{datetime.datetime.now().timestamp()}"
        is_viewed  = [message_id in viewed_once_ids]

        def build_viewed_placeholder():
            return ft.Column(
                [
                    ft.Icon(ft.Icons.VISIBILITY_OFF, size=80, color=ft.Colors.WHITE54),
                    ft.Text("Просмотрено", size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    ft.Text(now_hm(), size=12, color=ft.Colors.WHITE54),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            )

        def on_tap(e):
            if one_time_view:
                if is_viewed[0]:
                    show_snack("❌ Сообщение уже было просмотрено")
                    return
                viewed_once_ids.append(message_id)
                is_viewed[0] = True

                def close_and_replace(e):
                    page.close(dlg)
                    image_container.content = build_viewed_placeholder()
                    image_container.update()

                dlg = ft.AlertDialog(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Image(src=image_path, fit=ft.ImageFit.CONTAIN),
                                ft.Text("⚠️ Одноразовый просмотр", size=14,
                                        weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        width=600, height=650,
                    ),
                    actions=[ft.TextButton("Закрыть", on_click=close_and_replace)],
                )
                page.open(dlg)
            else:
                open_image_fullscreen(image_path, file_name)

        # Контент пузыря — либо «просмотрено», либо картинка
        if one_time_view and is_viewed[0]:
            bubble_content = build_viewed_placeholder()
        else:
            eye_overlay = ft.Container(
                content=ft.Icon(ft.Icons.VISIBILITY, color=ft.Colors.WHITE, size=30),
                alignment=ft.alignment.center,
                width=200, height=200,
            ) if one_time_view else ft.Container()

            bubble_content = ft.Column(
                [
                    ft.Stack([
                        ft.Image(src=image_path, width=200, height=200,
                                 fit=ft.ImageFit.COVER, border_radius=10),
                        eye_overlay,
                    ]),
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.TIMER_OUTLINED, color=ft.Colors.WHITE, size=16)
                            if one_time_view else ft.Container(),
                            ft.Text(
                                "Одноразовое фото" if one_time_view else file_name,
                                size=12, color=ft.Colors.WHITE,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                icon_size=16, tooltip="Скачать",
                                on_click=lambda e: download_file(image_path, file_name),
                            ) if not one_time_view else ft.Container(),
                        ],
                        spacing=5,
                    ),
                    ft.Text(now_hm(), size=12, color=ft.Colors.WHITE54),
                ],
                tight=True, spacing=5,
            )

        image_container = ft.Container(
            content=bubble_content,
            bgcolor=make_bubble_colors_dark(is_user),
            padding=10,
            border_radius=15,
            margin=make_bubble_margin(is_user),
        )
        row    = make_message_row(image_container, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_tap=on_tap,
            on_long_press_start=lambda e: show_message_menu(widget, "📷 Фото", is_user),
        )
        return widget

    def create_video_message(video_path: str, file_name: str, is_user: bool = True) -> ft.GestureDetector:
        user_data = CURRENT_USER if is_user else CONTACT_USER
        bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Stack([
                        ft.Container(width=200, height=150, bgcolor=ft.Colors.BLACK54, border_radius=10),
                        ft.Container(
                            content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED, color=ft.Colors.WHITE, size=60),
                            alignment=ft.alignment.center,
                            width=200, height=150,
                        ),
                    ]),
                    ft.Row(
                        [
                            ft.Text("Видео", size=12, color=ft.Colors.WHITE,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                icon_size=16, tooltip="Скачать",
                                on_click=lambda e: download_file(video_path, file_name),
                            ),
                        ],
                        spacing=5,
                    ),
                    ft.Text(now_hm(), size=12, color=ft.Colors.WHITE54),
                ],
                tight=True, spacing=5,
            ),
            bgcolor=make_bubble_colors_dark(is_user),
            padding=10,
            border_radius=15,
            margin=make_bubble_margin(is_user),
        )
        row    = make_message_row(bubble, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_tap=lambda e: open_video_viewer(video_path, file_name),
            on_long_press_start=lambda e: show_message_menu(widget, "Видео", is_user),
        )
        return widget

    def create_audio_message(
        audio_path: str, file_name: str,
        is_user: bool = True, one_time_view: bool = False
    ) -> ft.GestureDetector | ft.Container:
        user_data = CURRENT_USER if is_user else CONTACT_USER
        abs_path  = os.path.abspath(audio_path)

        if not os.path.exists(abs_path):
            print(f"❌ Аудио не найдено: {abs_path}")
            return create_document_message(abs_path, f"❌ {file_name}", "Файл не найден", is_user)

        size_text = format_file_size(abs_path)

        # Оценка длительности по размеру файла
        try:
            file_size = os.path.getsize(abs_path)
            duration  = [max(30, min(600, int(file_size / (1024 * 1024) * 60)))]
        except Exception:
            duration = [180]

        is_playing       = [False]
        current_position = [0.0]
        timer_ref        = [None]
        audio_elem       = [None]
        play_btn         = [None]
        slider_ref       = [None]
        time_text        = [None]

        audio = ft.Audio(src=abs_path, autoplay=False, volume=1)
        audio_elem[0] = audio
        page.overlay.append(audio)

        def on_slider_change(e):
            current_position[0] = e.control.value
            time_text[0].value = f"{format_time_seconds(current_position[0])} / {format_time_seconds(duration[0])}"
            time_text[0].update()

        def on_slider_release(e):
            current_position[0] = e.control.value
            try:
                audio_elem[0].seek(int(current_position[0] * 1000))
            except Exception as ex:
                print(f"❌ Ошибка перемотки: {ex}")
            on_slider_change(e)

        def tick():
            """Обновляет прогресс каждые 0.5 секунды."""
            if not is_playing[0]:
                return
            current_position[0] = min(current_position[0] + 0.5, duration[0])
            slider_ref[0].value = current_position[0]
            time_text[0].value  = f"{format_time_seconds(current_position[0])} / {format_time_seconds(duration[0])}"
            slider_ref[0].update()
            time_text[0].update()

            if current_position[0] >= duration[0]:
                is_playing[0] = False
                play_btn[0].icon    = ft.Icons.PLAY_ARROW
                play_btn[0].tooltip = "Воспроизвести"
                play_btn[0].update()
                return

            timer_ref[0] = threading.Timer(0.5, tick)
            timer_ref[0].start()

        def toggle_play(e):
            try:
                if is_playing[0]:
                    is_playing[0] = False
                    play_btn[0].icon    = ft.Icons.PLAY_ARROW
                    play_btn[0].tooltip = "Воспроизвести"
                    if timer_ref[0]:
                        timer_ref[0].cancel()
                    audio_elem[0].pause()
                else:
                    is_playing[0] = True
                    play_btn[0].icon    = ft.Icons.PAUSE
                    play_btn[0].tooltip = "Пауза"
                    if current_position[0] == 0:
                        audio_elem[0].play()
                    else:
                        audio_elem[0].resume()
                    tick()
                play_btn[0].update()
            except Exception as ex:
                print(f"❌ Ошибка воспроизведения: {ex}")

        btn = ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_color=ft.Colors.WHITE,
                            icon_size=30, tooltip="Воспроизвести", on_click=toggle_play)
        play_btn[0] = btn

        sld = ft.Slider(min=0, max=duration[0], value=0, divisions=100,
                        active_color=ft.Colors.WHITE, inactive_color=ft.Colors.WHITE38,
                        thumb_color=ft.Colors.WHITE,
                        on_change=on_slider_change, on_change_end=on_slider_release)
        slider_ref[0] = sld

        tm = ft.Text(f"0:00 / {format_time_seconds(duration[0])}",
                     color=ft.Colors.WHITE70, size=11, weight=ft.FontWeight.BOLD)
        time_text[0] = tm

        download_btn = ft.IconButton(
            icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
            icon_size=20, tooltip="Скачать",
            on_click=lambda e: download_file(abs_path, file_name),
        ) if not one_time_view else ft.Container()

        bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            btn,
                            ft.Column(
                                [
                                    ft.Text(
                                        "🔊 Голосовое сообщение" if one_time_view else file_name,
                                        color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(f"🎵 {size_text}", color=ft.Colors.WHITE70, size=11),
                                ],
                                spacing=2, expand=True,
                            ),
                            download_btn,
                        ],
                        spacing=5,
                    ),
                    sld,
                    ft.Row([
                        tm,
                        ft.Container(expand=True),
                        ft.Text(now_hm(), size=12, color=ft.Colors.WHITE54),
                    ]),
                ],
                tight=True, spacing=2,
            ),
            bgcolor=make_bubble_colors_dark(is_user),
            padding=10, border_radius=15,
            margin=make_bubble_margin(is_user),
            width=350,
        )
        row    = make_message_row(bubble, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_long_press_start=lambda e: show_message_menu(widget, f"🎵 Аудио: {file_name}", is_user),
        )
        return widget

    def create_document_message(
        file_path: str, file_name: str, file_type: str, is_user: bool = True
    ) -> ft.GestureDetector:
        user_data = CURRENT_USER if is_user else CONTACT_USER
        size_text = format_file_size(file_path)
        clean_name = file_name
        for prefix in ("📄 ", "📝 ", "📊 ", "📃 ", "🗜️ ", "📎 "):
            clean_name = clean_name.replace(prefix, "")

        bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color=ft.Colors.WHITE, size=40),
                            ft.Column(
                                [
                                    ft.Text(file_name, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD,
                                            size=13, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(f"{file_type} • {size_text}", color=ft.Colors.WHITE70, size=11),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                icon_size=20, tooltip="Скачать",
                                on_click=lambda e: download_file(file_path, clean_name),
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Text(now_hm(), size=12, color=ft.Colors.WHITE54),
                ],
                tight=True, spacing=5,
            ),
            bgcolor=make_bubble_colors_dark(is_user),
            padding=10, border_radius=15,
            margin=make_bubble_margin(is_user),
            width=280,
        )
        row    = make_message_row(bubble, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_long_press_start=lambda e: show_message_menu(widget, file_name, is_user),
        )
        return widget

    # ── Отправка ───────────────────────────────────────────────────────────────

    def send_text_message(e):
        text = message_input.value.strip()
        if not text:
            return

        quote = reply_to[0]
        add_message_to_chat(create_text_message(text, is_user=True, quote=quote))

        payload: dict = {"message": text, "sender_id": CURRENT_USER["id"]}
        if quote:
            payload["reply_to"] = quote
        try:
            ws.send(json.dumps(payload))
        except Exception as ex:
            show_snack(f"❌ Ошибка отправки: {ex}")

        # Сбросить ответ
        cancel_reply()
        message_input.value = ""
        message_input.update()
        reset_input_buttons()

    def send_file_via_ws(file_path: str, file_name: str, file_type: str, one_time_view: bool = False) -> bool:
        """Отправляет бинарный файл с метаданными через WebSocket."""
        try:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                show_snack(f"❌ Файл слишком большой! Максимум 50 МБ")
                return False

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            metadata = json.dumps({"file_name": file_name, "file_type": file_type, "file_size": file_size})
            ws.send_binary(metadata.encode("utf-8") + FILE_SEPARATOR + file_bytes)
            return True
        except Exception as e:
            import traceback
            print(f"❌ Ошибка отправки файла: {e}")
            traceback.print_exc()
            return False

    def send_delete_command(msg_id: str, text: str) -> bool:
        try:
            ws.send(json.dumps({
                "type": "delete",
                "message_id": msg_id,
                "message_text": text,
                "sender_id": CURRENT_USER["id"],
                "timestamp": datetime.datetime.now().timestamp(),
            }))
            return True
        except Exception as e:
            print(f"❌ Ошибка команды удаления: {e}")
            return False

    # ── Работа с файлами ───────────────────────────────────────────────────────

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files:
                show_rename_dialog({"path": f.path, "name": f.name, "display_name": f.name})

    def show_rename_dialog(file_info: dict):
        name_no_ext, ext = os.path.splitext(file_info["name"])
        is_media = ext.lower() in IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

        rename_field     = ft.TextField(value=name_no_ext, label="Название", expand=True, text_size=13)
        one_time_cb      = ft.Checkbox(label="Одноразовый", value=False)

        def confirm(e):
            new_name = rename_field.value.strip() + ext
            file_info["display_name"] = new_name or file_info["name"]
            file_info["one_time_view"] = one_time_cb.value if is_media else False
            page.close(dlg)
            add_file_to_chat(file_info)

        def skip(e):
            file_info["display_name"] = file_info["name"]
            file_info["one_time_view"] = one_time_cb.value if is_media else False
            page.close(dlg)
            add_file_to_chat(file_info)

        short_name = file_info["name"][:35] + "..." if len(file_info["name"]) > 35 else file_info["name"]
        items = [ft.Text(short_name, size=11, weight=ft.FontWeight.BOLD), rename_field]
        if is_media:
            items.append(one_time_cb)

        dlg = ft.AlertDialog(
            title=ft.Text("Отправка файла", size=15),
            content=ft.Container(content=ft.Column(items, tight=True, spacing=10), width=280),
            actions=[
                ft.TextButton("Отмена",    on_click=lambda e: page.close(dlg)),
                ft.TextButton("Отправить", on_click=confirm),
            ],
        )
        page.open(dlg)

    def add_file_to_chat(file_info: dict):
        path         = file_info["path"]
        display_name = file_info["display_name"]
        one_time     = file_info.get("one_time_view", False)
        ftype        = get_file_type(display_name)
        saved_path   = auto_save_file(path, display_name)

        send_file_via_ws(saved_path, display_name, ftype, one_time)

        ext = get_file_ext(display_name)
        if ext in IMAGE_EXTS:
            widget = create_image_message(saved_path, display_name, is_user=True, one_time_view=one_time)
        elif ext in VIDEO_EXTS:
            widget = create_video_message(saved_path, display_name, is_user=True)
        elif ext in AUDIO_EXTS:
            widget = create_audio_message(saved_path, display_name, is_user=True, one_time_view=one_time)
        else:
            widget = create_document_message(saved_path, f"📎 {display_name}", "Файл", is_user=True)

        messages_column.controls.append(widget)
        all_messages.append(widget)
        sent_media_files.append({"name": display_name, "type": ext, "path": saved_path})
        scroll_to_bottom()
        page.update()

    # ── Обработка входящих сообщений ──────────────────────────────────────────

    def handle_incoming_file(msg: dict):
        try:
            file_name = msg["file_name"]
            file_type = msg["file_type"]
            sender_id = msg.get("sender_id")

            if sender_id != CONTACT_USER["id"]:
                return

            file_bytes = base64.b64decode(msg["file_data"])
            timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name  = f"{timestamp}_{file_name}"
            save_path  = os.path.join(INCOMING_FOLDER, save_name)

            with open(save_path, "wb") as f:
                f.write(file_bytes)

            # Копия в assets для отображения через Flet
            shutil.copy2(save_path, os.path.join(ASSETS_FOLDER, os.path.basename(save_path)))

            ext = get_file_ext(file_name)
            if ext in IMAGE_EXTS:
                widget = create_image_message(save_path, file_name, is_user=False)
            elif ext in VIDEO_EXTS:
                widget = create_video_message(save_path, file_name, is_user=False)
            elif ext in AUDIO_EXTS:
                widget = create_audio_message(save_path, file_name, is_user=False)
            else:
                widget = create_document_message(save_path, f"📎 {file_name}", "Файл", is_user=False)

            add_message_to_chat(widget)
        except Exception as e:
            import traceback
            print(f"❌ Ошибка получения файла: {e}")
            traceback.print_exc()

    def poll_queue():
        """Опрашивает очередь сообщений каждые 0.5 секунды."""
        try:
            while not message_queue.empty():
                msg = message_queue.get_nowait()
                if msg.get("type") == "file":
                    # Не показываем файлы от заблокированного пользователя
                    if not is_blocked[0]:
                        handle_incoming_file(msg)
                else:
                    sender_id = msg.get("sender_id")
                    text      = msg.get("message")
                    in_quote  = msg.get("reply_to")
                    # Не показываем сообщения от заблокированного пользователя
                    if text and sender_id == CONTACT_USER["id"] and not is_blocked[0]:
                        add_message_to_chat(create_text_message(text, is_user=False, quote=in_quote))
        except queue.Empty:
            pass
        threading.Timer(0.5, poll_queue).start()

    # ── Голосовые сообщения ────────────────────────────────────────────────────

    recording_start = [None]
    recording_label = ft.Text("Запись... 0:00", size=14)

    def start_recording_timer():
        recording_start[0] = time.time()
        tick_recording()

    def tick_recording():
        if recording_start[0] and voice_panel.visible:
            elapsed = int(time.time() - recording_start[0])
            recording_label.value = f"Запись... {elapsed // 60}:{elapsed % 60:02d}"
            recording_label.update()
            threading.Timer(1.0, tick_recording).start()

    def send_voice_message(audio_path: str, file_name: str, one_time: bool = False):
        saved = auto_save_file(audio_path, file_name)
        add_message_to_chat(create_audio_message(saved, "Голосовое сообщение", is_user=True, one_time_view=one_time))
        if auto_save_folder[0] and saved != audio_path:
            show_snack("✅ Голосовое сообщение сохранено")

    # Строим панель записи
    voice_one_time_cb = ft.Checkbox(label="Одноразовый", value=False)

    def cancel_voice(e):
        voice_panel.visible = False
        recording_start[0]  = None
        voice_one_time_cb.value = False
        voice_panel.update()

    def send_voice(e):
        ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"voice_{ts}.mp3"
        file_path = os.path.join(VOICE_FOLDER, file_name)
        try:
            open(file_path, "w").close()  # заглушка для демо
            send_voice_message(file_path, file_name, one_time=voice_one_time_cb.value)
            show_snack("⚠️ Демо-версия. В реальном приложении — настоящая запись.")
        except Exception as ex:
            print(f"❌ Ошибка создания файла: {ex}")
        voice_panel.visible = False
        recording_start[0]  = None
        voice_one_time_cb.value = False
        voice_panel.update()

    voice_panel = ft.Container(
        visible=False,
        content=ft.Column(
            [
                ft.Text("Запись голосового", size=14, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [ft.Icon(ft.Icons.MIC, color=ft.Colors.RED, size=30), recording_label],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                voice_one_time_cb,
                ft.Row(
                    [
                        ft.ElevatedButton("Отмена",    on_click=cancel_voice, bgcolor=ft.Colors.GREY_300),
                        ft.ElevatedButton("Отправить", on_click=send_voice,
                                          bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        bgcolor=ft.Colors.WHITE,
        border_radius=10, padding=15,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.BLACK54, offset=ft.Offset(0, 0)),
    )

    def toggle_voice(e):
        voice_panel.visible = not voice_panel.visible
        if voice_panel.visible:
            start_recording_timer()
        voice_panel.update()

    # ── Кнопки ввода ──────────────────────────────────────────────────────────

    def reset_input_buttons():
        mic_btn.visible    = True
        attach_btn.visible = True
        send_btn.visible   = False
        for b in (mic_btn, attach_btn, send_btn):
            b.update()

    def on_text_change(e):
        has_text = bool(message_input.value.strip())
        mic_btn.visible    = not has_text
        attach_btn.visible = not has_text
        send_btn.visible   = has_text
        for b in (mic_btn, attach_btn, send_btn):
            b.update()

    message_input = ft.TextField(
        hint_text="Введите сообщение...",
        expand=True, multiline=True, min_lines=1, max_lines=3,
        on_change=on_text_change,
    )

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    mic_btn    = ft.IconButton(icon=ft.Icons.KEYBOARD_VOICE, on_click=toggle_voice,
                               icon_color=ft.Colors.BLUE, visible=True)
    attach_btn = ft.IconButton(icon=ft.Icons.ATTACH_FILE, icon_color=ft.Colors.BLUE,
                               tooltip="Прикрепить файл", visible=True,
                               on_click=lambda e: file_picker.pick_files(
                                   allow_multiple=True, dialog_title="Выберите файлы"))
    send_btn   = ft.IconButton(icon=ft.Icons.SEND, on_click=send_text_message,
                               icon_color=ft.Colors.BLUE, visible=False)

    # ── Шапка чата ────────────────────────────────────────────────────────────

    def show_user_profile(e):
        def close(e): page.close(dlg)

        big_avatar = make_avatar(CONTACT_USER, size=160)

        # Динамическая кнопка блокировки
        block_icon_ref  = ft.Ref[ft.Icon]()
        block_text_ref  = ft.Ref[ft.Text]()

        def _update_block_btn():
            if is_blocked[0]:
                block_icon_ref.current.name  = ft.Icons.LOCK_OPEN
                block_icon_ref.current.color = ft.Colors.ORANGE
                block_text_ref.current.value = "Разблокировать"
                block_text_ref.current.color = ft.Colors.ORANGE
            else:
                block_icon_ref.current.name  = ft.Icons.BLOCK
                block_icon_ref.current.color = ft.Colors.RED
                block_text_ref.current.value = "Заблокировать"
                block_text_ref.current.color = ft.Colors.RED
            block_icon_ref.current.update()
            block_text_ref.current.update()

        def toggle_block(e):
            is_blocked[0] = not is_blocked[0]
            _update_block_btn()
            _apply_block_state()
            if is_blocked[0]:
                show_snack("🚫 Пользователь заблокирован")
            else:
                show_snack("✅ Пользователь разблокирован")

        block_btn = ft.TextButton(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.BLOCK if not is_blocked[0] else ft.Icons.LOCK_OPEN,
                        color=ft.Colors.RED if not is_blocked[0] else ft.Colors.ORANGE,
                        ref=block_icon_ref,
                    ),
                    ft.Text(
                        "Заблокировать" if not is_blocked[0] else "Разблокировать",
                        size=14,
                        color=ft.Colors.RED if not is_blocked[0] else ft.Colors.ORANGE,
                        ref=block_text_ref,
                    ),
                ],
                spacing=10,
            ),
            on_click=toggle_block,
        )

        dlg = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(content=big_avatar, alignment=ft.alignment.center, padding=20),
                        ft.Text(CONTACT_USER["name"], size=24, weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(CONTACT_USER["phone"], size=16, color=ft.Colors.GREY,
                                text_align=ft.TextAlign.CENTER),
                        ft.Container(
                            content=ft.Text(CONTACT_USER["status"], size=14, color=ft.Colors.GREEN),
                            alignment=ft.alignment.center, padding=10,
                        ),
                        ft.Divider(),
                        ft.Container(
                            content=ft.Column(
                                [
                                    _info_row(ft.Icons.INFO_OUTLINE,       "О себе",
                                              CONTACT_USER["about"]),
                                    ft.Divider(height=20),
                                    _info_row(ft.Icons.PHOTO_LIBRARY,      "Отправленные файлы",
                                              f"{len(sent_media_files)} файлов"),
                                    ft.Divider(height=20),
                                    _info_row(ft.Icons.CHAT_BUBBLE_OUTLINE, "Сообщений",
                                              f"{len(all_messages)} сообщений"),
                                ],
                                spacing=10,
                            ),
                            padding=10,
                        ),
                        ft.Divider(),
                        ft.Column(
                            [
                                ft.TextButton(
                                    content=ft.Row([ft.Icon(ft.Icons.NOTIFICATIONS_OFF, color=ft.Colors.GREY),
                                                    ft.Text("Отключить уведомления", size=14)], spacing=10),
                                    on_click=lambda e: show_snack("🔕 Уведомления отключены"),
                                ),
                                block_btn,
                            ],
                            spacing=5,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10, scroll=ft.ScrollMode.AUTO,
                ),
                width=400, height=700,
            ),
            actions=[ft.TextButton("Закрыть", on_click=close)],
        )
        page.open(dlg)

    def _profile_action(icon, label, color, handler):
        return ft.Column(
            [
                ft.IconButton(icon=icon, icon_color=color, icon_size=30, on_click=handler, tooltip=label),
                ft.Text(label, size=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
        )

    def _info_row(icon, title, value):
        return ft.Row(
            [
                ft.Icon(icon, size=20, color=ft.Colors.GREY),
                ft.Column(
                    [ft.Text(title, size=12, color=ft.Colors.GREY), ft.Text(value, size=14)],
                    spacing=2,
                ),
            ],
            spacing=10,
        )

    def clear_all_chat():
        def confirm(e):
            messages_column.controls.clear()
            all_messages.clear()
            sent_media_files.clear()
            messages_column.update()
            page.close(dlg)

            # Удаляем все файлы из папок чата
            for folder in (ASSETS_FOLDER, INCOMING_FOLDER, VOICE_FOLDER):
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        except Exception as ex:
                            print(f"❌ Ошибка удаления файла {file_path}: {ex}")

            show_snack("🗑️ Чат очищен")

        dlg = ft.AlertDialog(
            title=ft.Text("Очистить чат?"),
            content=ft.Text("Все сообщения будут удалены"),
            actions=[
                ft.TextButton("Отмена",   on_click=lambda e: page.close(dlg)),
                ft.TextButton("Очистить", on_click=confirm,
                              style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        page.open(dlg)

    chat_header = ft.Container(
        content=ft.Row(
            [
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: page.go('/'),
                              icon_color=ft.Colors.BLUE),
                ft.GestureDetector(
                    content=ft.Row(
                        [
                            make_avatar(CONTACT_USER),
                            ft.Column(
                                [
                                    ft.Text(CONTACT_USER["name"], weight=ft.FontWeight.BOLD, size=16),
                                    ft.Text(CONTACT_USER["last_seen"], size=12, color=ft.Colors.GREY),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    on_tap=show_user_profile,
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_SWEEP, icon_color=ft.Colors.RED,
                    tooltip="Очистить весь чат",
                    on_click=lambda e: clear_all_chat(),
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=15,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_300)),
    )

    # ── Сборка страницы ────────────────────────────────────────────────────────

    input_bar = ft.Container(
        content=ft.Column(
            [
                reply_bar,
                ft.Row(
                    [attach_btn, message_input, mic_btn, send_btn],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=0,
        ),
        padding=10,
        bgcolor=ft.Colors.WHITE,
    )

    page.data = {
        "add_incoming_text":     lambda text, sid=None: add_message_to_chat(
            create_text_message(text, is_user=(sid == CURRENT_USER["id"]))),
        "add_incoming_image":    lambda path, name, sid=None, ot=False: add_message_to_chat(
            create_image_message(path, name, is_user=(sid == CURRENT_USER["id"]), one_time_view=ot)),
        "add_incoming_video":    lambda path, name, sid=None: add_message_to_chat(
            create_video_message(path, name, is_user=(sid == CURRENT_USER["id"]))),
        "add_incoming_audio":    lambda path, name, sid=None: add_message_to_chat(
            create_audio_message(path, name, is_user=(sid == CURRENT_USER["id"]))),
        "add_incoming_document": lambda path, name, sid=None, ftype="Файл": add_message_to_chat(
            create_document_message(path, name, ftype, is_user=(sid == CURRENT_USER["id"]))),
    }

    poll_queue()

    return ft.View(
        "/chat",
        controls=[
            ft.Container(
                expand=True,
                content=ft.Column(
                    [
                        chat_header,
                        ft.Container(content=messages_column, expand=True, padding=10, bgcolor=ft.Colors.GREY_100),
                        voice_panel,
                        input_bar,
                    ],
                    expand=True,
                ),
            )
        ],
        padding=0,
        bgcolor=ft.Colors.WHITE,
    )
