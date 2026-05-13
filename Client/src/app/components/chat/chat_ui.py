import flet as ft
import datetime
import os
import shutil
import json
import time
import base64
import threading
import queue
 
from . import chat_connection as conn
from .chat_connection import FILE_SEPARATOR
 
# ── Константы ─────────────────────────────────────────────────────────────────
 
INCOMING_FOLDER = "assets/data.media/incoming_files"
ASSETS_FOLDER   = "assets/data.media/assets"
VOICE_FOLDER    = "assets/data.media/voice_recordings"
SETTINGS_FILE   = "chat_settings.json"
MAX_FILE_SIZE   = 50 * 1024 * 1024  # 50 МБ
 
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a"}
 
for _folder in (INCOMING_FOLDER, ASSETS_FOLDER, VOICE_FOLDER):
    os.makedirs(_folder, exist_ok=True)
 
 
# ── Утилиты ───────────────────────────────────────────────────────────────────
 
def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()
 
 
def _file_type(filename: str) -> str:
    e = _ext(filename)
    if e in IMAGE_EXTS: return "image"
    if e in VIDEO_EXTS: return "video"
    if e in AUDIO_EXTS: return "audio"
    return "document"
 
 
def _file_size_str(path: str) -> str:
    try:
        size = os.path.getsize(path)
        if size < 1024:            return f"{size} Б"
        if size < 1024 * 1024:    return f"{size / 1024:.1f} КБ"
        return f"{size / (1024 * 1024):.1f} МБ"
    except Exception:
        return "?"
 
 
def _fmt_seconds(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"
 
 
def _now_hm() -> str:
    return datetime.datetime.now().strftime("%H:%M")
 
 
# ── Класс ChatUI ──────────────────────────────────────────────────────────────
 
class ChatUI:
    """Весь UI и логика экрана чата."""
 
    def __init__(self, page: ft.Page, current_user: dict, contact_user: dict):
        self.page         = page
        self.CURRENT_USER = current_user
        self.CONTACT_USER = contact_user
 
        self.messages_column  = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
        self.all_messages:     list = []
        self.sent_media_files: list = []
        self.viewed_once_ids:  list = []
 
        self.reply_to         = [None]
        self.is_blocked       = [False]
        self.auto_save_folder = [None]
        self.recording_start  = [None]
 
        self._load_settings()
        self._build_reply_bar()
        self._build_voice_panel()
        self._build_input_bar()
        self._build_header()
 
    # ── Настройки ─────────────────────────────────────────────────────────────
 
    def _load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self.auto_save_folder[0] = json.load(f).get("auto_download_folder")
        except Exception:
            pass
 
    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"auto_download_folder": self.auto_save_folder[0]}, f, ensure_ascii=False)
        except Exception:
            pass
 
    # ── Общие утилиты ─────────────────────────────────────────────────────────
 
    def make_avatar(self, user: dict, size: int = 40) -> ft.CircleAvatar:
        letter = (user.get("name") or "?")[0].upper()
        return ft.CircleAvatar(
            content=ft.Text(letter, size=size // 2),
            bgcolor=user.get("avatar_color", ft.Colors.GREY),
            radius=size // 2,
        )
 
    def show_snack(self, text: str):
        self.page.open(ft.SnackBar(content=ft.Text(text), duration=2000))
        self.page.update()
 
    def scroll_to_bottom(self):
        self.messages_column.scroll_to(offset=-1, duration=300)
 
    def add_message_to_chat(self, widget):
        self.messages_column.controls.append(widget)
        self.all_messages.append(widget)
        self.scroll_to_bottom()
        self.page.update()
 
    # ── Панель ответа ─────────────────────────────────────────────────────────
 
    def _build_reply_bar(self):
        self.reply_preview_text = ft.Text(
            "", size=12, color=ft.Colors.GREY_700,
            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.reply_bar = ft.Container(
            visible=False,
            content=ft.Row([
                ft.Icon(ft.Icons.REPLY, color=ft.Colors.BLUE, size=18),
                ft.Column([
                    ft.Text("Ответ на:", size=11, color=ft.Colors.BLUE,
                            weight=ft.FontWeight.BOLD),
                    self.reply_preview_text,
                ], spacing=0, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16,
                              icon_color=ft.Colors.GREY, tooltip="Отменить ответ",
                              on_click=lambda e: self.cancel_reply()),
            ], spacing=8),
            bgcolor=ft.Colors.BLUE_50,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.BLUE)),
        )
 
    def cancel_reply(self):
        self.reply_to[0] = None
        self.reply_bar.visible = False
        self.reply_bar.update()
 
    def set_reply(self, text: str):
        self.reply_to[0] = text
        self.reply_preview_text.value = text if len(text) <= 60 else text[:57] + "..."
        self.reply_bar.visible = True
        self.reply_bar.update()
        self.message_input.focus()
        self.message_input.update()
 
    def _apply_block_state(self):
        pass  # Поле ввода остаётся активным
 
    # ── Файловые операции ─────────────────────────────────────────────────────
 
    def auto_save_file(self, src: str, filename: str) -> str:
        folder = self.auto_save_folder[0]
        if not folder or not os.path.exists(folder):
            return src
        dest, counter = os.path.join(folder, filename), 1
        while os.path.exists(dest):
            name, ext = os.path.splitext(filename)
            dest = os.path.join(folder, f"{name}_{counter}{ext}")
            counter += 1
        try:
            shutil.copy2(src, dest)
            return dest
        except Exception as e:
            print(f"❌ Автосохранение: {e}")
            return src
 
    def download_file(self, file_path: str, file_name: str):
        def on_save(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    shutil.copy2(file_path, e.path)
                    self.show_snack(f"Файл сохранён: {e.path}")
                except Exception as ex:
                    self.show_snack(f"Ошибка сохранения: {ex}")
 
        picker = ft.FilePicker(on_result=on_save)
        self.page.overlay.append(picker)
        self.page.update()
        picker.save_file(file_name=file_name, dialog_title="Сохранить файл как")
 
    def select_auto_save_folder(self, e):
        def on_picked(e: ft.FilePickerResultEvent):
            if e.path:
                self.auto_save_folder[0] = e.path
                self._save_settings()
                self.show_snack(f"Папка для сохранения: {e.path}")
 
        picker = ft.FilePicker(on_result=on_picked)
        self.page.overlay.append(picker)
        self.page.update()
        picker.get_directory_path(dialog_title="Выберите папку для автосохранения")
 
    # ── Диалоги просмотра ─────────────────────────────────────────────────────
 
    def open_image_fullscreen(self, image_path: str, file_name: str):
        def close(e): self.page.close(dlg)
        dlg = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column([
                    ft.Image(src=image_path, fit=ft.ImageFit.CONTAIN),
                    ft.Text(file_name, size=14, weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=600, height=650,
            ),
            actions=[
                ft.TextButton("📥 Скачать",
                              on_click=lambda e: self.download_file(image_path, file_name)),
                ft.TextButton("Закрыть", on_click=close),
            ],
        )
        self.page.open(dlg)
 
    def open_video_viewer(self, video_path: str, file_name: str):
        def close(e): self.page.close(dlg)
        dlg = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column([
                    ft.Video(playlist=[ft.VideoMedia(video_path)],
                             width=600, height=400, show_controls=True),
                    ft.Text(file_name, size=14, weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=600,
            ),
            actions=[
                ft.TextButton("📥 Скачать",
                              on_click=lambda e: self.download_file(video_path, file_name)),
                ft.TextButton("Закрыть", on_click=close),
            ],
        )
        self.page.open(dlg)
 
    # ── Контекстное меню сообщения ────────────────────────────────────────────
 
    def show_message_menu(self, msg_widget, text: str, is_user: bool,
                          msg_text_ref=None, edited_tag=None, current_text=None):
        def close(e): self.page.close(dlg)
 
        def copy(e):
            self.page.set_clipboard(text)
            self.show_snack("📋 Скопировано!")
            self.page.close(dlg)
 
        def reply(e):
            self.set_reply(text)
            self.page.close(dlg)
 
        def delete(e):
            self.delete_message(msg_widget, text)
            self.page.close(dlg)
 
        def edit(e):
            self.page.close(dlg)
            field = ft.TextField(value=current_text[0], multiline=True,
                                 min_lines=1, max_lines=5, expand=True, autofocus=True)
 
            def confirm_edit(e):
                new_text = field.value.strip()
                if not new_text or new_text == current_text[0]:
                    self.page.close(edit_dlg)
                    return
                current_text[0]            = new_text
                msg_text_ref.current.value = new_text
                edited_tag.value           = "изменено"
                msg_text_ref.current.update()
                edited_tag.update()
                try:
                    conn.send_text({
                        "type":      "edit",
                        "message":   new_text,
                        "sender_id": self.CURRENT_USER["id"],
                        "timestamp": datetime.datetime.now().timestamp(),
                    })
                except Exception as ex:
                    print(f"❌ Ошибка отправки правки: {ex}")
                self.page.close(edit_dlg)
                self.show_snack("✏️ Сообщение изменено")
 
            edit_dlg = ft.AlertDialog(
                title=ft.Text("Редактировать сообщение"),
                content=ft.Container(content=field, width=320),
                actions=[
                    ft.TextButton("Отмена",    on_click=lambda e: self.page.close(edit_dlg)),
                    ft.TextButton("Сохранить", on_click=confirm_edit,
                                  style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                ],
            )
            self.page.open(edit_dlg)
 
        items = [ft.TextButton("↩ Ответить", on_click=reply),
                 ft.TextButton("📋 Копировать", on_click=copy)]
        if is_user:
            items += [ft.TextButton("✏️ Редактировать", on_click=edit),
                      ft.TextButton("🗑️ Удалить", on_click=delete)]
 
        dlg = ft.AlertDialog(
            title=ft.Text("Действия"),
            content=ft.Column(items, tight=True),
            actions=[ft.TextButton("Закрыть", on_click=close)],
        )
        self.page.open(dlg)
 
    def delete_message(self, widget, text: str = ""):
        if widget not in self.messages_column.controls:
            return
        try:
            conn.send_text({
                "type":         "delete",
                "message_id":   f"msg_{datetime.datetime.now().timestamp()}_{hash(text)}",
                "message_text": text,
                "sender_id":    self.CURRENT_USER["id"],
                "timestamp":    datetime.datetime.now().timestamp(),
            })
            self.messages_column.controls.remove(widget)
            if widget in self.all_messages:
                self.all_messages.remove(widget)
            self.messages_column.update()
            self.show_snack("✅ Сообщение удалено у всех")
        except Exception as e:
            print(f"❌ Ошибка удаления: {e}")
 
    # ── Стили пузырей ─────────────────────────────────────────────────────────
 
    def _bubble_color(self, is_user: bool):
        return ft.Colors.BLUE if is_user else ft.Colors.GREY
 
    def _bubble_color_dark(self, is_user: bool):
        return ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700
 
    def _bubble_margin(self, is_user: bool):
        return ft.margin.only(right=10) if is_user else ft.margin.only(left=10)
 
    def _make_row(self, bubble, is_user: bool, user_data: dict) -> ft.Row:
        avatar = self.make_avatar(user_data)
        spacer = ft.Container(expand=True)
        return (ft.Row([spacer, bubble, avatar], vertical_alignment=ft.CrossAxisAlignment.START)
                if is_user else
                ft.Row([avatar, bubble, spacer], vertical_alignment=ft.CrossAxisAlignment.START))
 
    # ── Создание пузырей ──────────────────────────────────────────────────────
 
    def create_text_message(self, text: str, is_user: bool = True,
                            quote: str | None = None) -> ft.GestureDetector:
        user_data     = self.CURRENT_USER if is_user else self.CONTACT_USER
        children      = []
 
        if quote:
            short = quote if len(quote) <= 60 else quote[:57] + "..."
            children.append(ft.Container(
                content=ft.Column([
                    ft.Text("↩ Ответ на:", size=10, color=ft.Colors.WHITE70,
                            weight=ft.FontWeight.BOLD),
                    ft.Text(short, size=12, color=ft.Colors.WHITE70, italic=True,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ], tight=True, spacing=1),
                bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=8,
                border=ft.border.only(left=ft.border.BorderSide(3, ft.Colors.WHITE70)),
            ))
 
        msg_ref      = ft.Ref[ft.Text]()
        edited_tag   = ft.Text("", size=10, color=ft.Colors.WHITE54, italic=True)
        current_text = [text]
 
        children += [
            ft.Text(text, color=ft.Colors.WHITE, ref=msg_ref),
            ft.Row([edited_tag, ft.Container(expand=True),
                    ft.Text(_now_hm(), size=12, color=ft.Colors.WHITE54)], spacing=0),
        ]
 
        bubble = ft.Container(
            content=ft.Column(children, tight=True, spacing=4),
            bgcolor=self._bubble_color(is_user),
            padding=10, border_radius=15,
            margin=self._bubble_margin(is_user),
        )
        row    = self._make_row(bubble, is_user, user_data)
        widget = None
 
        def open_menu(e):
            self.show_message_menu(widget, current_text[0], is_user,
                                   msg_text_ref=msg_ref,
                                   edited_tag=edited_tag,
                                   current_text=current_text)
 
        widget = ft.GestureDetector(content=row, on_tap=open_menu,
                                    on_long_press_start=open_menu)
        return widget
 
    def create_image_message(self, image_path: str, file_name: str,
                             is_user: bool = True,
                             one_time_view: bool = False) -> ft.GestureDetector:
        user_data  = self.CURRENT_USER if is_user else self.CONTACT_USER
        message_id = f"img_{datetime.datetime.now().timestamp()}"
        is_viewed  = [message_id in self.viewed_once_ids]
 
        def viewed_placeholder():
            return ft.Column([
                ft.Icon(ft.Icons.VISIBILITY_OFF, size=80, color=ft.Colors.WHITE54),
                ft.Text("Просмотрено", size=16, color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD),
                ft.Text(_now_hm(), size=12, color=ft.Colors.WHITE54),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
 
        def on_tap(e):
            if one_time_view:
                if is_viewed[0]:
                    self.show_snack("❌ Сообщение уже было просмотрено")
                    return
                self.viewed_once_ids.append(message_id)
                is_viewed[0] = True
 
                def close_and_replace(e):
                    self.page.close(dlg)
                    image_container.content = viewed_placeholder()
                    image_container.update()
 
                dlg = ft.AlertDialog(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Image(src=image_path, fit=ft.ImageFit.CONTAIN),
                            ft.Text("⚠️ Одноразовый просмотр", size=14,
                                    weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        width=600, height=650,
                    ),
                    actions=[ft.TextButton("Закрыть", on_click=close_and_replace)],
                )
                self.page.open(dlg)
            else:
                self.open_image_fullscreen(image_path, file_name)
 
        if one_time_view and is_viewed[0]:
            bubble_content = viewed_placeholder()
        else:
            eye_overlay = (ft.Container(
                content=ft.Icon(ft.Icons.VISIBILITY, color=ft.Colors.WHITE, size=30),
                alignment=ft.alignment.center, width=200, height=200,
            ) if one_time_view else ft.Container())
 
            bubble_content = ft.Column([
                ft.Stack([
                    ft.Image(src=image_path, width=200, height=200,
                             fit=ft.ImageFit.COVER, border_radius=10),
                    eye_overlay,
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.TIMER_OUTLINED, color=ft.Colors.WHITE, size=16)
                    if one_time_view else ft.Container(),
                    ft.Text("Одноразовое фото" if one_time_view else file_name,
                            size=12, color=ft.Colors.WHITE,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ft.IconButton(icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                  icon_size=16, tooltip="Скачать",
                                  on_click=lambda e: self.download_file(image_path, file_name),
                                  ) if not one_time_view else ft.Container(),
                ], spacing=5),
                ft.Text(_now_hm(), size=12, color=ft.Colors.WHITE54),
            ], tight=True, spacing=5)
 
        image_container = ft.Container(
            content=bubble_content,
            bgcolor=self._bubble_color_dark(is_user),
            padding=10, border_radius=15,
            margin=self._bubble_margin(is_user),
        )
        row    = self._make_row(image_container, is_user, user_data)
        widget = ft.GestureDetector(
            content=row, on_tap=on_tap,
            on_long_press_start=lambda e: self.show_message_menu(widget, "📷 Фото", is_user),
        )
        return widget
 
    def create_video_message(self, video_path: str, file_name: str,
                             is_user: bool = True) -> ft.GestureDetector:
        user_data = self.CURRENT_USER if is_user else self.CONTACT_USER
        bubble = ft.Container(
            content=ft.Column([
                ft.Stack([
                    ft.Container(width=200, height=150,
                                 bgcolor=ft.Colors.BLACK54, border_radius=10),
                    ft.Container(
                        content=ft.Icon(ft.Icons.PLAY_CIRCLE_FILLED,
                                        color=ft.Colors.WHITE, size=60),
                        alignment=ft.alignment.center, width=200, height=150,
                    ),
                ]),
                ft.Row([
                    ft.Text("Видео", size=12, color=ft.Colors.WHITE,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ft.IconButton(icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                  icon_size=16, tooltip="Скачать",
                                  on_click=lambda e: self.download_file(video_path, file_name)),
                ], spacing=5),
                ft.Text(_now_hm(), size=12, color=ft.Colors.WHITE54),
            ], tight=True, spacing=5),
            bgcolor=self._bubble_color_dark(is_user),
            padding=10, border_radius=15,
            margin=self._bubble_margin(is_user),
        )
        row    = self._make_row(bubble, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_tap=lambda e: self.open_video_viewer(video_path, file_name),
            on_long_press_start=lambda e: self.show_message_menu(widget, "Видео", is_user),
        )
        return widget
 
    def create_audio_message(self, audio_path: str, file_name: str,
                             is_user: bool = True,
                             one_time_view: bool = False):
        user_data = self.CURRENT_USER if is_user else self.CONTACT_USER
        abs_path  = os.path.abspath(audio_path)
 
        if not os.path.exists(abs_path):
            return self.create_document_message(abs_path, f"❌ {file_name}",
                                                "Файл не найден", is_user)
 
        size_text = _file_size_str(abs_path)
        try:
            fsize    = os.path.getsize(abs_path)
            duration = [max(30, min(600, int(fsize / (1024 * 1024) * 60)))]
        except Exception:
            duration = [180]
 
        is_playing       = [False]
        current_pos      = [0.0]
        timer_ref        = [None]
        audio_elem       = [None]
        play_btn         = [None]
        slider_ref       = [None]
        time_text        = [None]
 
        audio = ft.Audio(src=abs_path, autoplay=False, volume=1)
        audio_elem[0] = audio
        self.page.overlay.append(audio)
 
        def on_slider_change(e):
            current_pos[0] = e.control.value
            time_text[0].value = f"{_fmt_seconds(current_pos[0])} / {_fmt_seconds(duration[0])}"
            time_text[0].update()
 
        def on_slider_release(e):
            current_pos[0] = e.control.value
            try:
                audio_elem[0].seek(int(current_pos[0] * 1000))
            except Exception as ex:
                print(f"❌ Ошибка перемотки: {ex}")
            on_slider_change(e)
 
        def tick():
            if not is_playing[0]:
                return
            current_pos[0] = min(current_pos[0] + 0.5, duration[0])
            slider_ref[0].value = current_pos[0]
            time_text[0].value  = f"{_fmt_seconds(current_pos[0])} / {_fmt_seconds(duration[0])}"
            slider_ref[0].update()
            time_text[0].update()
            if current_pos[0] >= duration[0]:
                is_playing[0]       = False
                play_btn[0].icon    = ft.Icons.PLAY_ARROW
                play_btn[0].tooltip = "Воспроизвести"
                play_btn[0].update()
                return
            timer_ref[0] = threading.Timer(0.5, tick)
            timer_ref[0].start()
 
        def toggle_play(e):
            try:
                if is_playing[0]:
                    is_playing[0]       = False
                    play_btn[0].icon    = ft.Icons.PLAY_ARROW
                    play_btn[0].tooltip = "Воспроизвести"
                    if timer_ref[0]:
                        timer_ref[0].cancel()
                    audio_elem[0].pause()
                else:
                    is_playing[0]       = True
                    play_btn[0].icon    = ft.Icons.PAUSE
                    play_btn[0].tooltip = "Пауза"
                    if current_pos[0] == 0:
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
 
        tm = ft.Text(f"0:00 / {_fmt_seconds(duration[0])}",
                     color=ft.Colors.WHITE70, size=11, weight=ft.FontWeight.BOLD)
        time_text[0] = tm
 
        download_btn = (ft.IconButton(icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                      icon_size=20, tooltip="Скачать",
                                      on_click=lambda e: self.download_file(abs_path, file_name))
                        if not one_time_view else ft.Container())
 
        bubble = ft.Container(
            content=ft.Column([
                ft.Row([
                    btn,
                    ft.Column([
                        ft.Text("🔊 Голосовое сообщение" if one_time_view else file_name,
                                color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"🎵 {size_text}", color=ft.Colors.WHITE70, size=11),
                    ], spacing=2, expand=True),
                    download_btn,
                ], spacing=5),
                sld,
                ft.Row([tm, ft.Container(expand=True),
                        ft.Text(_now_hm(), size=12, color=ft.Colors.WHITE54)]),
            ], tight=True, spacing=2),
            bgcolor=self._bubble_color_dark(is_user),
            padding=10, border_radius=15,
            margin=self._bubble_margin(is_user),
            width=350,
        )
        row    = self._make_row(bubble, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_long_press_start=lambda e: self.show_message_menu(
                widget, f"🎵 Аудио: {file_name}", is_user),
        )
        return widget
 
    def create_document_message(self, file_path: str, file_name: str,
                                file_type: str,
                                is_user: bool = True) -> ft.GestureDetector:
        user_data  = self.CURRENT_USER if is_user else self.CONTACT_USER
        size_text  = _file_size_str(file_path)
        clean_name = file_name
        for prefix in ("📄 ", "📝 ", "📊 ", "📃 ", "🗜️ ", "📎 "):
            clean_name = clean_name.replace(prefix, "")
 
        bubble = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color=ft.Colors.WHITE, size=40),
                    ft.Column([
                        ft.Text(file_name, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD,
                                size=13, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{file_type} • {size_text}", color=ft.Colors.WHITE70, size=11),
                    ], spacing=2, expand=True),
                    ft.IconButton(icon=ft.Icons.DOWNLOAD, icon_color=ft.Colors.WHITE,
                                  icon_size=20, tooltip="Скачать",
                                  on_click=lambda e: self.download_file(file_path, clean_name)),
                ], spacing=10),
                ft.Text(_now_hm(), size=12, color=ft.Colors.WHITE54),
            ], tight=True, spacing=5),
            bgcolor=self._bubble_color_dark(is_user),
            padding=10, border_radius=15,
            margin=self._bubble_margin(is_user),
            width=280,
        )
        row    = self._make_row(bubble, is_user, user_data)
        widget = ft.GestureDetector(
            content=row,
            on_long_press_start=lambda e: self.show_message_menu(widget, file_name, is_user),
        )
        return widget
 
    # ── Отправка ──────────────────────────────────────────────────────────────
 
    def send_text_message(self, e):
        text = self.message_input.value.strip()
        if not text:
            return
        quote = self.reply_to[0]
        self.add_message_to_chat(self.create_text_message(text, is_user=True, quote=quote))
        payload = {"message": text, "sender_id": self.CURRENT_USER["id"]}
        if quote:
            payload["reply_to"] = quote
        try:
            conn.send_text(payload)
        except Exception as ex:
            self.show_snack(f"❌ Ошибка отправки: {ex}")
        self.cancel_reply()
        self.message_input.value = ""
        self.message_input.update()
        self.reset_input_buttons()
 
    def send_file_via_ws(self, file_path: str, file_name: str,
                         file_type: str, one_time_view: bool = False) -> bool:
        try:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                self.show_snack("❌ Файл слишком большой! Максимум 50 МБ")
                return False
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            meta = json.dumps({"file_name": file_name, "file_type": file_type,
                               "file_size": file_size})
            conn.send_binary(meta.encode("utf-8") + FILE_SEPARATOR + file_bytes)
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки файла: {e}")
            return False
 
    # ── Файловый диалог ───────────────────────────────────────────────────────
 
    def on_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files:
                self.show_rename_dialog({"path": f.path, "name": f.name,
                                         "display_name": f.name})
 
    def show_rename_dialog(self, file_info: dict):
        name_no_ext, ext = os.path.splitext(file_info["name"])
        is_media         = ext.lower() in IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS
        rename_field = ft.TextField(value=name_no_ext, label="Название",
                                    expand=True, text_size=13)
        one_time_cb  = ft.Checkbox(label="Одноразовый", value=False)
 
        def confirm(e):
            new_name = rename_field.value.strip() + ext
            file_info["display_name"]  = new_name or file_info["name"]
            file_info["one_time_view"] = one_time_cb.value if is_media else False
            self.page.close(dlg)
            self.add_file_to_chat(file_info)
 
        def skip(e):
            file_info["display_name"]  = file_info["name"]
            file_info["one_time_view"] = one_time_cb.value if is_media else False
            self.page.close(dlg)
            self.add_file_to_chat(file_info)
 
        short = file_info["name"][:35] + ("..." if len(file_info["name"]) > 35 else "")
        items = [ft.Text(short, size=11, weight=ft.FontWeight.BOLD), rename_field]
        if is_media:
            items.append(one_time_cb)
 
        dlg = ft.AlertDialog(
            title=ft.Text("Отправка файла", size=15),
            content=ft.Container(content=ft.Column(items, tight=True, spacing=10), width=280),
            actions=[
                ft.TextButton("Отмена",    on_click=lambda e: self.page.close(dlg)),
                ft.TextButton("Отправить", on_click=confirm),
            ],
        )
        self.page.open(dlg)
 
    def add_file_to_chat(self, file_info: dict):
        p           = file_info["path"]
        name        = file_info["display_name"]
        one_time    = file_info.get("one_time_view", False)
        ftype       = _file_type(name)
        saved_path  = self.auto_save_file(p, name)
 
        self.send_file_via_ws(saved_path, name, ftype, one_time)
 
        e = _ext(name)
        if e in IMAGE_EXTS:
            widget = self.create_image_message(saved_path, name, is_user=True,
                                               one_time_view=one_time)
        elif e in VIDEO_EXTS:
            widget = self.create_video_message(saved_path, name, is_user=True)
        elif e in AUDIO_EXTS:
            widget = self.create_audio_message(saved_path, name, is_user=True,
                                               one_time_view=one_time)
        else:
            widget = self.create_document_message(saved_path, f"📎 {name}",
                                                  "Файл", is_user=True)
 
        self.messages_column.controls.append(widget)
        self.all_messages.append(widget)
        self.sent_media_files.append({"name": name, "type": e, "path": saved_path})
        self.scroll_to_bottom()
        self.page.update()
 
    # ── Входящие сообщения ────────────────────────────────────────────────────
 
    def handle_incoming_file(self, msg: dict):
        try:
            file_name = msg["file_name"]
            if msg.get("sender_id") != self.CONTACT_USER["id"]:
                return
            file_bytes = base64.b64decode(msg["file_data"])
            ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path  = os.path.join(INCOMING_FOLDER, f"{ts}_{file_name}")
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            shutil.copy2(save_path, os.path.join(ASSETS_FOLDER, os.path.basename(save_path)))
 
            e = _ext(file_name)
            if e in IMAGE_EXTS:
                widget = self.create_image_message(save_path, file_name, is_user=False)
            elif e in VIDEO_EXTS:
                widget = self.create_video_message(save_path, file_name, is_user=False)
            elif e in AUDIO_EXTS:
                widget = self.create_audio_message(save_path, file_name, is_user=False)
            else:
                widget = self.create_document_message(save_path, f"📎 {file_name}",
                                                      "Файл", is_user=False)
            self.add_message_to_chat(widget)
        except Exception as e:
            print(f"❌ Ошибка получения файла: {e}")
 
    def poll_queue(self):
        """Опрашивает очередь входящих сообщений каждые 0.5 с."""
        try:
            while not conn.message_queue.empty():
                msg       = conn.message_queue.get_nowait()
                sender_id = msg.get("sender_id")
                if msg.get("type") == "file":
                    if not self.is_blocked[0]:
                        self.handle_incoming_file(msg)
                else:
                    text     = msg.get("message")
                    in_quote = msg.get("reply_to")
                    if (text and sender_id == self.CONTACT_USER["id"]
                            and not self.is_blocked[0]):
                        self.add_message_to_chat(
                            self.create_text_message(text, is_user=False, quote=in_quote))
        except queue.Empty:
            pass
        threading.Timer(0.5, self.poll_queue).start()
 
    # ── Голосовые сообщения ───────────────────────────────────────────────────
 
    def _build_voice_panel(self):
        self.recording_label   = ft.Text("Запись... 0:00", size=14)
        self.voice_one_time_cb = ft.Checkbox(label="Одноразовый", value=False)
 
        def cancel_voice(e):
            self.voice_panel.visible     = False
            self.recording_start[0]      = None
            self.voice_one_time_cb.value = False
            self.voice_panel.update()
 
        def send_voice(e):
            ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"voice_{ts}.mp3"
            file_path = os.path.join(VOICE_FOLDER, file_name)
            try:
                open(file_path, "w").close()
                self._send_voice_message(file_path, file_name,
                                         one_time=self.voice_one_time_cb.value)
                self.show_snack("⚠️ Демо-версия. В реальном — настоящая запись.")
            except Exception as ex:
                print(f"❌ Ошибка создания файла: {ex}")
            self.voice_panel.visible     = False
            self.recording_start[0]      = None
            self.voice_one_time_cb.value = False
            self.voice_panel.update()
 
        self.voice_panel = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Text("Запись голосового", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([ft.Icon(ft.Icons.MIC, color=ft.Colors.RED, size=30),
                        self.recording_label],
                       alignment=ft.MainAxisAlignment.CENTER),
                self.voice_one_time_cb,
                ft.Row([
                    ft.ElevatedButton("Отмена",    on_click=cancel_voice,
                                      bgcolor=ft.Colors.GREY_300),
                    ft.ElevatedButton("Отправить", on_click=send_voice,
                                      bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            bgcolor=ft.Colors.WHITE, border_radius=10, padding=15,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15,
                                color=ft.Colors.BLACK54, offset=ft.Offset(0, 0)),
        )
 
    def _send_voice_message(self, audio_path: str, file_name: str, one_time: bool = False):
        saved = self.auto_save_file(audio_path, file_name)
        self.add_message_to_chat(
            self.create_audio_message(saved, "Голосовое сообщение",
                                      is_user=True, one_time_view=one_time))
        if self.auto_save_folder[0] and saved != audio_path:
            self.show_snack("✅ Голосовое сообщение сохранено")
 
    def _start_recording_timer(self):
        self.recording_start[0] = time.time()
        self._tick_recording()
 
    def _tick_recording(self):
        if self.recording_start[0] and self.voice_panel.visible:
            elapsed = int(time.time() - self.recording_start[0])
            self.recording_label.value = f"Запись... {elapsed // 60}:{elapsed % 60:02d}"
            self.recording_label.update()
            threading.Timer(1.0, self._tick_recording).start()
 
    def toggle_voice(self, e):
        self.voice_panel.visible = not self.voice_panel.visible
        if self.voice_panel.visible:
            self._start_recording_timer()
        self.voice_panel.update()
 
    # ── Кнопки ввода ──────────────────────────────────────────────────────────
 
    def reset_input_buttons(self):
        self.mic_btn.visible    = True
        self.attach_btn.visible = True
        self.send_btn.visible   = False
        for b in (self.mic_btn, self.attach_btn, self.send_btn):
            b.update()
 
    def on_text_change(self, e):
        has_text            = bool(self.message_input.value.strip())
        self.mic_btn.visible    = not has_text
        self.attach_btn.visible = not has_text
        self.send_btn.visible   = has_text
        for b in (self.mic_btn, self.attach_btn, self.send_btn):
            b.update()
 
    def _build_input_bar(self):
        self.message_input = ft.TextField(
            hint_text="Введите сообщение...",
            expand=True, multiline=True, min_lines=1, max_lines=3,
            on_change=self.on_text_change,
        )
        self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
        self.mic_btn = ft.IconButton(icon=ft.Icons.KEYBOARD_VOICE,
                                     on_click=self.toggle_voice,
                                     icon_color=ft.Colors.BLUE, visible=True)
        self.attach_btn = ft.IconButton(
            icon=ft.Icons.ATTACH_FILE, icon_color=ft.Colors.BLUE,
            tooltip="Прикрепить файл", visible=True,
            on_click=lambda e: self.file_picker.pick_files(
                allow_multiple=True, dialog_title="Выберите файлы"),
        )
        self.send_btn = ft.IconButton(icon=ft.Icons.SEND,
                                      on_click=self.send_text_message,
                                      icon_color=ft.Colors.BLUE, visible=False)
        self.input_bar = ft.Container(
            content=ft.Column([
                self.reply_bar,
                ft.Row([self.attach_btn, self.message_input,
                        self.mic_btn, self.send_btn],
                       vertical_alignment=ft.CrossAxisAlignment.END),
            ], spacing=0),
            padding=10,
            bgcolor=ft.Colors.SURFACE,
        )
 
    # ── Шапка чата ────────────────────────────────────────────────────────────
 
    def _build_header(self):
        self.chat_header = ft.Container(
            content=ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK,
                              on_click=lambda e: self.page.go('/'),
                              icon_color=ft.Colors.BLUE),
                ft.Row([
                    self.make_avatar(self.CONTACT_USER),
                    ft.Column([
                        ft.Text(self.CONTACT_USER["name"],
                                weight=ft.FontWeight.BOLD, size=16),
                        ft.Text(self.CONTACT_USER["last_seen"],
                                size=12, color=ft.Colors.GREY),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Container(expand=True),
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    items=[
                        ft.PopupMenuItem(
                            text="Редактировать чат",
                            icon=ft.Icons.EDIT,
                            on_click=lambda e: self.edit_chat(),
                        ),
                        ft.PopupMenuItem(
                            text="Удалить чат",
                            icon=ft.Icons.DELETE,
                            on_click=lambda e: self.clear_all_chat(),
                        ),
                        ft.PopupMenuItem(
                            text="Заблокировать пользователя",
                            icon=ft.Icons.BLOCK,
                            on_click=lambda e: self._toggle_block_from_menu(),
                        ),
                    ],
                ),
            ], alignment=ft.MainAxisAlignment.START),
            padding=15, bgcolor=ft.Colors.SURFACE,
            border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_300)),
        )
 
    # ── Профиль контакта ──────────────────────────────────────────────────────
 
    def _info_row(self, icon, title, value):
        return ft.Row([
            ft.Icon(icon, size=20, color=ft.Colors.GREY),
            ft.Column([ft.Text(title, size=12, color=ft.Colors.GREY),
                       ft.Text(value, size=14)], spacing=2),
        ], spacing=10)
 
    def show_user_profile(self, e):
        def close(e): self.page.close(dlg)
        big_avatar     = self.make_avatar(self.CONTACT_USER, size=160)
        block_icon_ref = ft.Ref[ft.Icon]()
        block_text_ref = ft.Ref[ft.Text]()
 
        def _update_block_btn():
            blocked = self.is_blocked[0]
            block_icon_ref.current.name  = ft.Icons.LOCK_OPEN if blocked else ft.Icons.BLOCK
            block_icon_ref.current.color = ft.Colors.ORANGE   if blocked else ft.Colors.RED
            block_text_ref.current.value = "Разблокировать"   if blocked else "Заблокировать"
            block_text_ref.current.color = ft.Colors.ORANGE   if blocked else ft.Colors.RED
            block_icon_ref.current.update()
            block_text_ref.current.update()
 
        def toggle_block(e):
            self.is_blocked[0] = not self.is_blocked[0]
            _update_block_btn()
            self._apply_block_state()
            self.show_snack("🚫 Пользователь заблокирован"
                            if self.is_blocked[0] else "✅ Пользователь разблокирован")
 
        blocked = self.is_blocked[0]
        block_btn = ft.TextButton(
            content=ft.Row([
                ft.Icon(ft.Icons.LOCK_OPEN if blocked else ft.Icons.BLOCK,
                        color=ft.Colors.ORANGE if blocked else ft.Colors.RED,
                        ref=block_icon_ref),
                ft.Text("Разблокировать" if blocked else "Заблокировать", size=14,
                        color=ft.Colors.ORANGE if blocked else ft.Colors.RED,
                        ref=block_text_ref),
            ], spacing=10),
            on_click=toggle_block,
        )
 
        dlg = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column([
                    ft.Container(content=big_avatar,
                                 alignment=ft.alignment.center, padding=20),
                    ft.Text(self.CONTACT_USER["name"], size=24,
                            weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(self.CONTACT_USER["phone"], size=16,
                            color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER),
                    ft.Container(alignment=ft.alignment.center, padding=10),
                    ft.Divider(),
                    ft.Container(content=ft.Column([
                        self._info_row(ft.Icons.INFO_OUTLINE, "О себе",
                                       self.CONTACT_USER["about"]),
                        ft.Divider(height=20),
                        self._info_row(ft.Icons.PHOTO_LIBRARY, "Отправленные файлы",
                                       f"{len(self.sent_media_files)} файлов"),
                        ft.Divider(height=20),
                        self._info_row(ft.Icons.CHAT_BUBBLE_OUTLINE, "Сообщений",
                                       f"{len(self.all_messages)} сообщений"),
                    ], spacing=10), padding=10),
                    ft.Divider(),
                    ft.Column([
                        ft.TextButton(
                            content=ft.Row([ft.Icon(ft.Icons.NOTIFICATIONS_OFF,
                                                    color=ft.Colors.GREY),
                                            ft.Text("Отключить уведомления", size=14)],
                                          spacing=10),
                            on_click=lambda e: self.show_snack("🔕 Уведомления отключены"),
                        ),
                        block_btn,
                    ], spacing=5),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=10, scroll=ft.ScrollMode.AUTO),
                width=400, height=700,
            ),
            actions=[ft.TextButton("Закрыть", on_click=close)],
        )
        self.page.open(dlg)
 
    # ── Методы меню (три точки) ───────────────────────────────────────────────
 
    def edit_chat(self):
        field = ft.TextField(
            value=self.CONTACT_USER["name"],
            label="Название чата",
            expand=True,
            autofocus=True,
        )
 
        def confirm(e):
            new_name = field.value.strip()
            if new_name:
                self.CONTACT_USER["name"] = new_name
                self.page.close(dlg)
                self.show_snack("✏️ Название чата изменено")
 
        dlg = ft.AlertDialog(
            title=ft.Text("Редактировать чат"),
            content=ft.Container(content=field, width=320),
            actions=[
                ft.TextButton("Отмена",    on_click=lambda e: self.page.close(dlg)),
                ft.TextButton("Сохранить", on_click=confirm,
                              style=ft.ButtonStyle(color=ft.Colors.BLUE)),
            ],
        )
        self.page.open(dlg)
 
    def _toggle_block_from_menu(self):
        self.is_blocked[0] = not self.is_blocked[0]
        self._apply_block_state()
        self.show_snack(
            "🚫 Пользователь заблокирован"
            if self.is_blocked[0] else "✅ Пользователь разблокирован"
        )
 
    # ── Очистка чата ──────────────────────────────────────────────────────────
 
    def clear_all_chat(self):
        def confirm(e):
            self.messages_column.controls.clear()
            self.all_messages.clear()
            self.sent_media_files.clear()
            self.messages_column.update()
            self.page.close(dlg)
            for folder in (ASSETS_FOLDER, INCOMING_FOLDER, VOICE_FOLDER):
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        fp = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(fp):
                                os.remove(fp)
                        except Exception as ex:
                            print(f"❌ Ошибка удаления {fp}: {ex}")
            self.show_snack("🗑️ Чат очищен")
 
        dlg = ft.AlertDialog(
            title=ft.Text("Очистить чат?"),
            content=ft.Text("Все сообщения будут удалены"),
            actions=[
                ft.TextButton("Отмена",   on_click=lambda e: self.page.close(dlg)),
                ft.TextButton("Очистить", on_click=confirm,
                              style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        self.page.open(dlg)
 
 
