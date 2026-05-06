import threading
import time
import requests as http
import flet as ft

from .database import (
    load_chats, delete_chat, create_new_chat,
    save_contact_if_not_exists, toggle_chat_favorite, delete_user_and_contacts,
    save_contact_name, get_contact_id_by_chat, delete_not_saved_contacts,
)
from .ui_components import create_contact_item
from .utils import format_phone
from .chat.chat_manager import set_chat_id, set_status_chat


def search_user_by_phone(number: str) -> dict | None:
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
            contact_id = get_contact_id_by_chat(db_path, chat_id)
            if not contact_id:
                return

            name_field = ft.TextField(label="Имя контакта", autofocus=True, border_radius=10)

            def _do_save(e):
                name = name_field.value.strip()
                if not name:
                    name_field.error_text = "Введите имя"
                    page.update()
                    return
                save_contact_name(db_path, contact_id, name)
                save_dlg.open = False
                page.update()
                update_fn()

            save_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Сохранить контакт"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Введите имя для этого контакта:", size=14, color=ft.Colors.GREY),
                        name_field,
                    ], spacing=10, tight=True),
                    width=300,
                ),
                actions=[
                    ft.TextButton("Сохранить", style=ft.ButtonStyle(color=ft.Colors.GREEN),
                                  on_click=_do_save),
                    ft.TextButton("Отмена",
                                  on_click=lambda e: (setattr(save_dlg, 'open', False), page.update())),
                ],
            )
            page.overlay.append(save_dlg)
            save_dlg.open = True
            page.update()

        elif action == "edit_contact":
            contact_id = get_contact_id_by_chat(db_path, chat_id)
            if not contact_id:
                return

            name_field = ft.TextField(label="Новое имя контакта", autofocus=True, border_radius=10)

            def _do_edit(e):
                name = name_field.value.strip()
                if not name:
                    name_field.error_text = "Введите имя"
                    page.update()
                    return
                save_contact_name(db_path, contact_id, name)
                edit_dlg.open = False
                page.update()
                update_fn()

            edit_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Изменить контакт"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Введите новое имя для контакта:", size=14, color=ft.Colors.GREY),
                        name_field,
                    ], spacing=10, tight=True),
                    width=300,
                ),
                actions=[
                    ft.TextButton("Сохранить", style=ft.ButtonStyle(color=ft.Colors.GREEN),
                                  on_click=_do_edit),
                    ft.TextButton("Отмена",
                                  on_click=lambda e: (setattr(edit_dlg, 'open', False), page.update())),
                ],
            )
            page.overlay.append(edit_dlg)
            edit_dlg.open = True
            page.update()

    # ── Диалог выбора контакта ────────────────────────────────────────────────

    def show_contact_selection(e, contact_dialog, contact_list, search_field,
                               contacts, create_chat_func,
                               loading_container=None, search_result_container=None,
                               not_saved_col=None, saved_col=None, delete_btn_row=None):

        def _refresh_columns(filter_text=""):
            all_contacts = contacts
            saved     = [c for c in all_contacts if c.get("status_user_contact") != "not_save_user"]
            not_saved = [c for c in all_contacts if c.get("status_user_contact") == "not_save_user"]

            if filter_text:
                f = filter_text.lower()
                saved     = [c for c in saved if f in (c["username"] or "").lower()]
                not_saved = [c for c in not_saved
                             if f in (c["username"] or "").lower()
                             or f in format_phone(c.get("phone", ""))]

            # Колонка "Сохранённые"
            if saved_col is not None:
                saved_col.controls.clear()
                if saved:
                    for c in saved:
                        saved_col.controls.append(
                            create_contact_item(
                                c,
                                lambda e, cid=c["id"], cname=c["username"]: create_chat_func(cid, cname)
                            )
                        )
                else:
                    saved_col.controls.append(
                        ft.Container(
                            content=ft.Text("Нет сохранённых контактов", size=13,
                                            color=ft.Colors.GREY_400,
                                            text_align=ft.TextAlign.CENTER),
                            padding=ft.padding.symmetric(vertical=30),
                            alignment=ft.alignment.center,
                        )
                    )

            # Колонка "Не сохранённые"
            if not_saved_col is not None:
                not_saved_col.controls.clear()
                if not_saved:
                    for c in not_saved:
                        c_copy = dict(c)
                        c_copy["username"] = format_phone(c.get("phone", "")) or c["username"]
                        not_saved_col.controls.append(
                            create_contact_item(
                                c_copy,
                                lambda e, cid=c["id"], cname=c["username"]: create_chat_func(cid, cname)
                            )
                        )
                else:
                    not_saved_col.controls.append(
                        ft.Container(
                            content=ft.Text("Нет несохранённых контактов", size=13,
                                            color=ft.Colors.GREY_400,
                                            text_align=ft.TextAlign.CENTER),
                            padding=ft.padding.symmetric(vertical=30),
                            alignment=ft.alignment.center,
                        )
                    )

            # Кнопка удаления
            if delete_btn_row is not None:
                delete_btn_row.controls.clear()
                if not_saved:
                    delete_btn_row.visible = True
                    delete_btn_row.controls.append(
                        ft.ElevatedButton(
                            text=f"Удалить несохранённых ({len(not_saved)})",
                            icon=ft.Icons.DELETE_SWEEP,
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.RED_600,
                            on_click=_delete_not_saved,
                        )
                    )
                else:
                    delete_btn_row.visible = False

            if search_result_container:
                search_result_container.content = None
                search_result_container.visible = False

            page.update()

        def _delete_not_saved(e):
            def _confirm(e):
                confirm_dlg.open = False
                page.update()
                deleted = delete_not_saved_contacts(db_path)
                if deleted > 0:
                    update_chats_list_func()
                    # Обновляем список внутри диалога
                    nonlocal contacts
                    from .database import load_contacts
                    contacts = load_contacts(db_path)
                    _refresh_columns()

            confirm_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Удалить несохранённые контакты?"),
                content=ft.Text("Все несохранённые контакты и их чаты будут удалены безвозвратно.",
                                size=14),
                actions=[
                    ft.TextButton("Удалить", style=ft.ButtonStyle(color=ft.Colors.RED),
                                  on_click=_confirm),
                    ft.TextButton("Отмена",
                                  on_click=lambda e: (setattr(confirm_dlg, 'open', False), page.update())),
                ],
            )
            page.overlay.append(confirm_dlg)
            confirm_dlg.open = True
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
                    content=ft.Row([
                        ft.Icon(ft.Icons.PERSON_OFF, color=ft.Colors.GREY_500, size=22),
                        ft.Text("Пользователь не найден :(", color=ft.Colors.GREY_500, size=14),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                )
            search_result_container.visible = True
            page.update()

        def _find_tabs():
            try:
                col = contact_dialog.content.content
                for ctrl in col.controls:
                    if isinstance(ctrl, ft.Tabs):
                        return ctrl
            except Exception:
                pass
            return None

        local_results_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, visible=False)

        # Вставляем local_results_col в диалог после search_result_container
        try:
            col = contact_dialog.content.content
            if local_results_col not in col.controls:
                # Вставляем после search_result_container (индекс 2)
                col.controls.insert(3, local_results_col)
        except Exception:
            pass

        def _show_local_results(text):
            """Ищет по имени и номеру в локальных контактах и рисует результаты."""
            f = text.lower()
            matched = [
                c for c in contacts
                if f in (c.get("username") or "").lower()
                or f in format_phone(c.get("phone", "")).lower()
                or f in (c.get("phone", "") or "").lower()
            ]
            local_results_col.controls.clear()
            if matched:
                local_results_col.controls.append(
                    ft.Container(
                        content=ft.Text("Найдено в контактах", size=12,
                                        color=ft.Colors.GREY_500,
                                        weight=ft.FontWeight.BOLD),
                        padding=ft.padding.only(left=4, top=4, bottom=2),
                    )
                )
                for c in matched:
                    display = dict(c)
                    if c.get("status_user_contact") == "not_save_user":
                        display["username"] = format_phone(c.get("phone", "")) or c["username"]
                    local_results_col.controls.append(
                        create_contact_item(
                            display,
                            lambda e, cid=c["id"], cname=c["username"]: create_chat_func(cid, cname)
                        )
                    )
            else:
                local_results_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SEARCH_OFF, color=ft.Colors.GREY_400, size=18),
                            ft.Text("Не найдено в контактах", color=ft.Colors.GREY_400, size=13),
                        ], spacing=6),
                        padding=ft.padding.symmetric(horizontal=4, vertical=10),
                    )
                )
            local_results_col.visible = True

        def on_search_change(e):
            text = e.control.value.strip()
            tabs = _find_tabs()
            if text:
                if tabs:
                    tabs.visible = False
                if search_result_container:
                    search_result_container.visible = False
                _show_local_results(text)
            else:
                if tabs:
                    tabs.visible = True
                local_results_col.visible = False
                local_results_col.controls.clear()
            page.update()

        def on_search_submit(e):
            value = e.control.value.strip()
            if not value:
                return
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
        # Сбрасываем состояние при открытии
        local_results_col.controls.clear()
        local_results_col.visible = False
        tabs = _find_tabs()
        if tabs:
            tabs.visible = True
        _refresh_columns()

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