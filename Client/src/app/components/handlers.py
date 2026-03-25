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
from .database import load_chats, delete_chat_from_db, create_new_chat
import flet as ft
import sqlite3 as sql
import requests as http
import threading
import time
from .chat.chat_meneger import set_chat_id, set_status_chat 

def number_search_contact(number):
    if len(number) == 11:
        number = number[1:]  # удаляем первый символ
    elif len(number) == 12:
        number = number[2:]  # удаляем первые два символа
    data = {"number": number}
    response = http.post(f"http://127.0.0.1:5000/search/v2/user/search_contacts/", json=data)
    data_user = response.json()
    print(data_user)

def setup_handlers(page, db_path, contacts, chats, update_chats_list_func, update_contacts_tab_func):

    def get_out(e):
        with sql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE user_settings SET authorization = 'false'")
            cur.execute("DELETE FROM users_data")
            #con.commit()
            cur.close()
        page.go('/login')
        page.update()

    def open_existing_chat(chat_id, status_chat=None):
        if status_chat == None:
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
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    def delete_chat(chat_id, confirm_dialog):
        if delete_chat_from_db(db_path, chat_id):
            update_chats_list_func()
            confirm_dialog.open = False
            page.update()

    def soon_popup(e):
        dlg = ft.AlertDialog(
            title=ft.Text("Скоро"),
            content=ft.Text("Функция находится в разработке"),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def show_contact_selection(e, contact_dialog, contact_list, search_field, contacts, create_chat_with_contact_func):
        def render_contacts(filter_text=""):
            contact_list.controls.clear()
            filtered = [c for c in contacts if filter_text.lower() in c["username"].lower()] if filter_text else contacts
            if not filtered:
                contact_list.controls.append(
                    ft.Container(content=ft.Text("Нет контактов", text_align=ft.TextAlign.CENTER), padding=20)
                )
            else:
                for contact in filtered:
                    from .ui_components import create_contact_item
                    contact_list.controls.append(
                        create_contact_item(
                            contact,
                            lambda e, cid=contact["id"], cname=contact["username"]: create_chat_with_contact_func(cid, cname)
                        )
                    )
            contact_list.update()

        def on_search_submit(e):
                number_search_contact(e.control.value)
                render_contacts(e.control.value)

        search_field.value = ""
        search_field.on_change = lambda e: render_contacts(e.control.value)  # фильтр работает как раньше
        search_field.on_submit = on_search_submit  # печатает только когда нажали Enter
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
        page.dialog = dlg
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
        'open_dialog': open_dialog
    }
