##############################################################################
# ФАЙЛ: handlers.py
# НАЗНАЧЕНИЕ: Все обработчики событий интерфейса (клики, нажатия)
# 
# СОДЕРЖАНИЕ:
# 1. Обработчики для кнопок и меню
# 2. Логика работы с диалогами
# 3. Функции навигации между окнами
# 
# ОСНОВНЫЕ ФУНКЦИИ:
# - setup_handlers()           - настраивает все обработчики
# - get_out()                  - выход из приложения
# - delete_chat_confirmation() - подтверждение удаления чата
# - soon_popup()               - показывает "Скоро" для недоступных функций
# - show_contact_selection()   - показывает выбор контакта для нового чата
# 
# КЛЮЧЕВЫЕ МОМЕНТЫ:
# - Все функции принимают параметр 'e' (событие)
# - Используют callback-функции для обновления UI
# - Работают с диалогами через page.dialog
# 
# ПРИМЕР ИСПОЛЬЗОВАНИЯ:
# from handlers import setup_handlers
# handlers = setup_handlers(page, db_path, contacts, chats, update_funcs)
# button.on_click = handlers['soon_popup']
# 
# ДЛЯ РАСШИРЕНИЯ:
# - Добавьте обработчики для отправки сообщений
# - Реализуйте обработку клавиатурных сочетаний
# - Добавьте обработчики drag & drop
##############################################################################
import os
import threading
import time
from .database import (
    load_chats, delete_chat_from_db, create_new_chat, save_contact_if_not_exists,
    toggle_chat_favorite, is_chat_favorite, delete_user_and_contacts
)
import flet as ft
import sqlite3 as sql
import requests as http
from .chat.chat_meneger import set_chat_id, set_status_chat


def number_search_contact(number):
    if len(number) == 11:
        number = number[1:]
    elif len(number) == 12:
        number = number[2:]
    data = {"number": number}
    try:
        response = http.post(f"http://127.0.0.1:5000/search/v2/user/search_contacts/", json=data)
        data_user = response.json()
        return data_user
    except Exception as ex:
        print(f"Ошибка поиска: {ex}")
        return None


def _format_phone(number):
    """Форматирует номер в вид +7 (XXX) XXX-XX-XX"""
    if not number:
        return ""
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return str(number)


def setup_handlers(page, db_path, contacts, chats, update_chats_list_func, update_contacts_tab_func):

    # ─── ВЫХОД: удаляем пользователя + все контакты ───────────────────────────
    def get_out(e):
        delete_user_and_contacts(db_path)
        page.go('/login')
        page.update()

    def open_existing_chat(chat_id, status_chat=None):
        if status_chat is None:
            status_chat = 'existing_chat'
        set_status_chat(status_chat)
        set_chat_id(chat_id)
        page.go('/chat')

    def delete_chat_confirmation(chat_id, confirm_dialog):
        chat_name = next((c["name"] for c in chats if c["id"] == chat_id), "")
        confirm_dialog.content = ft.Text(f"Удалить чат '{chat_name}'?")
        confirm_dialog.actions = [
            ft.TextButton("Удалить", on_click=lambda e: delete_chat(chat_id, confirm_dialog)),
            ft.TextButton("Отмена", on_click=lambda e: setattr(confirm_dialog, 'open', False) or page.update())
        ]
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def delete_chat(chat_id, confirm_dialog):
        if delete_chat_from_db(db_path, chat_id):
            update_chats_list_func()
            confirm_dialog.open = False
            page.update()

    # ─── МЕНЮ ТРЁХ ТОЧЕК У ЧАТА ───────────────────────────────────────────────
    def handle_chat_menu(chat_id, action, update_fn):
        if action == "delete":
            confirm_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Удаление чата"),
                content=ft.Text("Вы уверены, что хотите удалить этот чат?"),
                actions=[],
            )

            def _do_delete(e):
                confirm_dlg.open = False
                page.update()
                if delete_chat_from_db(db_path, chat_id):
                    update_fn()

            def _cancel(e):
                confirm_dlg.open = False
                page.update()

            confirm_dlg.actions = [
                ft.TextButton("Удалить", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=_do_delete),
                ft.TextButton("Отмена", on_click=_cancel),
            ]
            page.overlay.append(confirm_dlg)
            confirm_dlg.open = True
            page.update()

        elif action == "favorite":
            toggle_chat_favorite(db_path, chat_id)
            update_fn()
            page.update()

        elif action == "save_contact":
            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("В разработке"),
                content=ft.Text("Сохранение контакта в БД будет добавлено позже"),
                actions=[],
            )
            def _close_save(e):
                dlg.open = False
                page.update()
            dlg.actions = [ft.TextButton("OK", on_click=_close_save)]
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        elif action == "edit_contact":
            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("В разработке"),
                content=ft.Text("Редактирование контакта в БД будет добавлено позже"),
                actions=[],
            )
            def _close_edit(e):
                dlg.open = False
                page.update()
            dlg.actions = [ft.TextButton("OK", on_click=_close_edit)]
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

    def soon_popup(e):
        dlg = ft.AlertDialog(
            title=ft.Text("Скоро"),
            content=ft.Text("Функция находится в разработке"),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def show_contact_selection(e, contact_dialog, contact_list, search_field, contacts,
                               create_chat_with_contact_func,
                               loading_container=None, search_result_container=None):

        def render_contacts(filter_text=""):
            contact_list.controls.clear()

            # ─── Разделяем контакты на сохранённые и несохранённые ────────────
            saved = [c for c in contacts if c.get("status_user_contact") == "save_user"]
            not_saved = [c for c in contacts if c.get("status_user_contact") == "not_save_user"]
            # Контакты без явного статуса считаем сохранёнными
            unknown = [c for c in contacts if c.get("status_user_contact") not in ("save_user", "not_save_user")]
            saved = saved + unknown

            if filter_text:
                saved = [c for c in saved if filter_text.lower() in c["username"].lower()]
                not_saved_filtered = []
                for c in not_saved:
                    phone_fmt = _format_phone(c.get("phone", ""))
                    if filter_text.lower() in c["username"].lower() or filter_text in phone_fmt:
                        not_saved_filtered.append(c)
                not_saved = not_saved_filtered

            if not saved and not not_saved:
                contact_list.controls.append(
                    ft.Container(
                        content=ft.Text("Нет контактов", text_align=ft.TextAlign.CENTER),
                        padding=20
                    )
                )
            else:
                # ── Раздел «Сохранённые» ──
                if saved:
                    contact_list.controls.append(
                        ft.Container(
                            content=ft.Text("Сохранённые", size=13, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_600),
                            padding=ft.padding.only(left=10, top=8, bottom=4),
                        )
                    )
                    for contact in saved:
                        from .ui_components import create_contact_item
                        contact_list.controls.append(
                            create_contact_item(
                                contact,
                                lambda e, cid=contact["id"], cname=contact["username"]:
                                    create_chat_with_contact_func(cid, cname)
                            )
                        )

                # ── Раздел «Не сохранённые» ──
                if not_saved:
                    contact_list.controls.append(
                        ft.Container(
                            content=ft.Text("Не сохранённые", size=13, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_600),
                            padding=ft.padding.only(left=10, top=12, bottom=4),
                        )
                    )
                    for contact in not_saved:
                        display_name = _format_phone(contact.get("phone", "")) or contact["username"]
                        contact_copy = dict(contact)
                        contact_copy["username"] = display_name
                        from .ui_components import create_contact_item
                        contact_list.controls.append(
                            create_contact_item(
                                contact_copy,
                                lambda e, cid=contact["id"], cname=contact["username"]:
                                    create_chat_with_contact_func(cid, cname)
                            )
                        )

            search_result_container.content = None
            search_result_container.visible = False
            page.update()

        def format_number(number):
            return _format_phone(number)

        def show_search_result(data_user):
            if data_user and data_user.get("post") == 200:

                def open_found_chat(e):
                    save_contact_if_not_exists(
                        db_path,
                        contact_id=data_user.get("id"),
                        username=data_user.get("login"),
                        phone=data_user.get("number", "")
                    )
                    create_chat_with_contact_func(
                        data_user.get("id"),
                        data_user.get("login")
                    )

                card = ft.Container(
                    content=ft.ListTile(
                        leading=ft.Container(
                            content=ft.Icon(ft.Icons.PERSON, size=22, color=ft.Colors.WHITE),
                            width=50, height=50, border_radius=25,
                            bgcolor=ft.Colors.GREEN, alignment=ft.alignment.center,
                        ),
                        title=ft.Text(
                            data_user.get("login", ""),
                            weight=ft.FontWeight.BOLD,
                            size=16,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        subtitle=ft.Text(
                            format_number(data_user.get("number", "")),
                            size=14,
                            color=ft.Colors.GREY,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        trailing=ft.Icon(ft.Icons.CHAT, color=ft.Colors.BLUE),
                        on_click=open_found_chat,
                    ),
                    padding=ft.padding.symmetric(horizontal=5, vertical=2),
                    border_radius=10,
                    on_click=open_found_chat,
                )

                search_result_container.content = card

            else:
                search_result_container.content = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PERSON_OFF, color=ft.Colors.GREY_500, size=22),
                            ft.Text("Пользователь не найден :(", color=ft.Colors.GREY_500, size=14),
                        ],
                        spacing=8,
                    ),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )

            search_result_container.visible = True
            page.update()

        def on_search_change(e):
            value = e.control.value.strip()
            render_contacts(value)

        def on_search_submit(e):
            value = e.control.value.strip()
            if not value:
                return

            contact_list.controls.clear()
            search_result_container.content = None
            search_result_container.visible = False

            loading_container.visible = True
            loading_container.content.visible = True
            page.update()

            def do_search():
                time.sleep(1)
                result = number_search_contact(value)
                loading_container.visible = False
                show_search_result(result)

            threading.Thread(target=do_search, daemon=True).start()

        search_field.value = ""
        search_field.on_change = on_search_change
        search_field.on_submit = on_search_submit
        render_contacts()

        contact_dialog.actions = [
            ft.TextButton("Отмена", on_click=lambda e: setattr(contact_dialog, 'open', False) or page.update())
        ]
        contact_dialog.open = True
        page.update()

    def create_chat_with_contact(contact_id, contact_name, update_chats_list_func, open_existing_chat_func, contact_dialog):
        chat_id = create_new_chat(db_path, contact_id, contact_name)
        update_chats_list_func()
        contact_dialog.open = False
        status_chat = 'new_chat'
        page.update()
        open_existing_chat_func(chat_id, status_chat)

    def close_dialog(e, dlg):
        dlg.open = False
        page.update()

    def open_dialog(e, dlg):
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    return {
        'get_out': get_out,
        'open_existing_chat': open_existing_chat,
        'delete_chat_confirmation': delete_chat_confirmation,
        'delete_chat': delete_chat,
        'soon_popup': soon_popup,
        'show_contact_selection': show_contact_selection,
        'create_chat_with_contact': create_chat_with_contact,
        'close_dialog': close_dialog,
        'open_dialog': open_dialog,
        'show_chat_context_menu': None,
        'toggle_favorite': None,
        'handle_chat_menu': handle_chat_menu,
    }