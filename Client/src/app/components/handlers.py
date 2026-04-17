import threading
import time
import requests as http
import flet as ft

from .database import (
    load_chats, delete_chat, create_new_chat,
    save_contact_if_not_exists, toggle_chat_favorite, delete_user_and_contacts,
)
from .ui_components import create_contact_item
from .utils import format_phone
from .chat.chat_manager import set_chat_id, set_status_chat


def search_user_by_phone(number: str) -> dict | None:
    """Поиск пользователя по номеру через сервер."""
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 11:
        digits = digits[1:]
    try:
        response = http.post(
            "http://127.0.0.1:5000/search/v2/user/search_contacts/",
            json={"number": digits}
        )
        return response.json()
    except Exception as ex:
        print(f"Ошибка поиска: {ex}")
        return None


def _soon_dialog(page: ft.Page) -> None:
    dlg = ft.AlertDialog(
        title=ft.Text("Скоро"),
        content=ft.Text("Функция находится в разработке"),
        actions=[ft.TextButton("OK", on_click=lambda e: (setattr(dlg, 'open', False), page.update()))],
    )
    page.dialog = dlg
    dlg.open = True
    page.update()


def _wip_dialog(page: ft.Page, title: str, text: str) -> None:
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(text),
        actions=[ft.TextButton("OK", on_click=lambda e: (setattr(dlg, 'open', False), page.update()))],
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def setup_handlers(page, db_path, contacts, chats,
                   update_chats_list_func, update_contacts_tab_func):

    def get_out(e):
        delete_user_and_contacts(db_path)
        page.go('/login')
        page.update()

    def open_existing_chat(chat_id, status_chat='existing_chat'):
        set_status_chat(status_chat)
        set_chat_id(chat_id)
        page.go('/chat')

    def handle_chat_menu(chat_id, action, update_fn):
        if action == "delete":
            def _do_delete(e):
                dlg.open = False
                page.update()
                if delete_chat(db_path, chat_id):
                    update_fn()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Удаление чата"),
                content=ft.Text("Вы уверены, что хотите удалить этот чат?"),
                actions=[
                    ft.TextButton("Удалить", style=ft.ButtonStyle(color=ft.Colors.RED),
                                  on_click=_do_delete),
                    ft.TextButton("Отмена",
                                  on_click=lambda e: (setattr(dlg, 'open', False), page.update())),
                ],
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        elif action == "favorite":
            toggle_chat_favorite(db_path, chat_id)
            update_fn()

        elif action == "save_contact":
            _wip_dialog(page, "В разработке", "Сохранение контакта будет добавлено позже")

        elif action == "edit_contact":
            _wip_dialog(page, "В разработке", "Редактирование контакта будет добавлено позже")

    def show_contact_selection(e, contact_dialog, contact_list, search_field,
                               contacts, create_chat_func,
                               loading_container=None, search_result_container=None):

        def render_contacts(filter_text=""):
            contact_list.controls.clear()
            saved    = [c for c in contacts if c.get("status_user_contact") != "not_save_user"]
            not_saved = [c for c in contacts if c.get("status_user_contact") == "not_save_user"]

            if filter_text:
                f = filter_text.lower()
                saved     = [c for c in saved if f in c["username"].lower()]
                not_saved = [c for c in not_saved
                             if f in c["username"].lower() or f in format_phone(c.get("phone", ""))]

            if not saved and not not_saved:
                contact_list.controls.append(
                    ft.Container(content=ft.Text("Нет контактов", text_align=ft.TextAlign.CENTER),
                                 padding=20)
                )
            else:
                if saved:
                    contact_list.controls.append(
                        ft.Container(
                            content=ft.Text("Сохранённые", size=13, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_600),
                            padding=ft.padding.only(left=10, top=8, bottom=4),
                        )
                    )
                    for c in saved:
                        contact_list.controls.append(
                            create_contact_item(
                                c,
                                lambda e, cid=c["id"], cname=c["username"]: create_chat_func(cid, cname)
                            )
                        )
                if not_saved:
                    contact_list.controls.append(
                        ft.Container(
                            content=ft.Text("Не сохранённые", size=13, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_600),
                            padding=ft.padding.only(left=10, top=12, bottom=4),
                        )
                    )
                    for c in not_saved:
                        c_copy = dict(c)
                        c_copy["username"] = format_phone(c.get("phone", "")) or c["username"]
                        contact_list.controls.append(
                            create_contact_item(
                                c_copy,
                                lambda e, cid=c["id"], cname=c["username"]: create_chat_func(cid, cname)
                            )
                        )

            if search_result_container:
                search_result_container.content = None
                search_result_container.visible = False
            page.update()

        def show_search_result(data_user):
            if data_user and data_user.get("post") == 200:
                def open_found_chat(e):
                    save_contact_if_not_exists(
                        db_path,
                        contact_id=data_user.get("id"),
                        username=data_user.get("login"),
                        phone=data_user.get("number", ""),
                    )
                    create_chat_func(data_user.get("id"), data_user.get("login"))

                card = ft.Container(
                    content=ft.ListTile(
                        leading=ft.Container(
                            content=ft.Icon(ft.Icons.PERSON, size=22, color=ft.Colors.WHITE),
                            width=50, height=50, border_radius=25,
                            bgcolor=ft.Colors.GREEN, alignment=ft.alignment.center,
                        ),
                        title=ft.Text(data_user.get("login", ""), weight=ft.FontWeight.BOLD,
                                      size=16, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                        subtitle=ft.Text(format_phone(data_user.get("number", "")),
                                         size=14, color=ft.Colors.GREY,
                                         overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
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
                        [ft.Icon(ft.Icons.PERSON_OFF, color=ft.Colors.GREY_500, size=22),
                         ft.Text("Пользователь не найден :(", color=ft.Colors.GREY_500, size=14)],
                        spacing=8,
                    ),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )
            search_result_container.visible = True
            page.update()

        def on_search_change(e):
            render_contacts(e.control.value.strip())

        def on_search_submit(e):
            value = e.control.value.strip()
            if not value:
                return
            contact_list.controls.clear()
            if search_result_container:
                search_result_container.content = None
                search_result_container.visible = False
            if loading_container:
                loading_container.visible = True
                loading_container.content.visible = True
            page.update()

            def do_search():
                time.sleep(1)
                result = search_user_by_phone(value)
                if loading_container:
                    loading_container.visible = False
                show_search_result(result)

            threading.Thread(target=do_search, daemon=True).start()

        search_field.value = ""
        search_field.on_change = on_search_change
        search_field.on_submit = on_search_submit
        render_contacts()

        contact_dialog.actions = [
            ft.TextButton("Отмена",
                          on_click=lambda e: (setattr(contact_dialog, 'open', False), page.update()))
        ]
        contact_dialog.open = True
        page.update()

    def create_chat_with_contact(contact_id, contact_name,
                                 update_chats_list_func, open_existing_chat_func, contact_dialog):
        chat_id = create_new_chat(db_path, contact_id, contact_name)
        update_chats_list_func()
        contact_dialog.open = False
        page.update()
        open_existing_chat_func(chat_id, 'new_chat')

    def close_dialog(e, dlg):
        dlg.open = False
        page.update()

    def open_dialog(e, dlg):
        page.dialog = dlg
        dlg.open = True
        page.update()

    return {
        'get_out':                   get_out,
        'open_existing_chat':        open_existing_chat,
        'handle_chat_menu':          handle_chat_menu,
        'show_contact_selection':    show_contact_selection,
        'create_chat_with_contact':  create_chat_with_contact,
        'close_dialog':              close_dialog,
        'open_dialog':               open_dialog,
        'soon_popup':                lambda e: _soon_dialog(page),
    }
