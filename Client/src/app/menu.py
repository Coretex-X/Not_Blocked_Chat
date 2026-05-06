import flet as ft
import path
from .components.database import (
    init_database, load_contacts, load_chats,
    get_user_data, load_favorite_chats, get_contact_display_name,
)
from .components.ui_components import create_contact_item, create_chat_item
from .components.dialogs import create_exit_dialog, create_contact_dialog
from .components.handlers import setup_handlers


def main_menu(page: ft.Page) -> ft.View:
    db = f"{path.db_path()}user_data.db"
    init_database(db)

    page.title = "Not Blocked Chat"

    contacts  = load_contacts(db)
    chats     = load_chats(db)
    user_data = get_user_data(db)

    exit_dlg = create_exit_dialog()

    (contact_dialog, contact_list, search_field,
     loading_container, search_result_container,
     not_saved_col, saved_col, delete_btn_row) = create_contact_dialog()

    chats_col     = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)
    favorites_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)
    contacts_col  = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)

    new_chat_fab = ft.FloatingActionButton(
        icon=ft.Icons.CHAT, tooltip="Новый чат", mini=True, on_click=None)
    new_group_fab = ft.FloatingActionButton(
        icon=ft.Icons.GROUP_ADD, tooltip="Новая группа", mini=True, on_click=None)

    # ── Вспомогательная: статус контакта по chat ──────────────────────────────

    def _contact_status_map():
        fresh_contacts = load_contacts(db)
        return {c["id"]: c.get("status_user_contact", "save_user") for c in fresh_contacts}

    def _make_chat_item(chat, status_map):
        display = dict(chat)
        cid = chat.get("contact_id")
        if cid:
            display["name"] = get_contact_display_name(db, cid)
        c_status = status_map.get(cid, "save_user")
        return create_chat_item(
            display,
            lambda cid=chat["id"]: handlers['open_existing_chat'](cid),
            on_menu_handler=lambda cid=chat["id"], action=None:
                handlers['handle_chat_menu'](cid, action, update_chats_list),
            contact_status=c_status,
        )

    # ── Обновление вкладок ────────────────────────────────────────────────────

    def _empty(icon, text, hint=""):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=50, color=ft.Colors.GREY),
                ft.Text(text, size=16, color=ft.Colors.GREY),
                *([ ft.Text(hint, size=14, color=ft.Colors.GREY_400,
                            text_align=ft.TextAlign.CENTER) ] if hint else []),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=ft.padding.all(50), alignment=ft.alignment.center,
        )

    def update_chats_list():
        nonlocal chats, contacts
        chats    = load_chats(db)
        contacts = load_contacts(db)
        chats_col.controls.clear()
        smap = _contact_status_map()
        if chats:
            for chat in chats:
                chats_col.controls.append(_make_chat_item(chat, smap))
        else:
            chats_col.controls.append(
                _empty(ft.Icons.CHAT, "Нет чатов",
                       "Начните новый чат, нажав кнопку ниже"))
        update_favorites_list()
        page.update()

    def update_favorites_list():
        favs = load_favorite_chats(db)
        favorites_col.controls.clear()
        smap = _contact_status_map()
        if favs:
            for chat in favs:
                favorites_col.controls.append(_make_chat_item(chat, smap))
        else:
            favorites_col.controls.append(
                _empty(ft.Icons.STAR_OUTLINE, "Нет избранных чатов",
                       "Удерживайте чат, чтобы добавить в избранное"))
        page.update()

    def update_contacts_tab():
        nonlocal contacts
        contacts = load_contacts(db)
        contacts_col.controls.clear()
        if not contacts:
            contacts_col.controls.append(
                _empty(ft.Icons.CONTACTS, "Нет контактов"))
        else:
            for c in contacts:
                contacts_col.controls.append(
                    create_contact_item(
                        c,
                        lambda e, cid=c["id"], cname=c["username"]:
                            handlers['create_chat_with_contact'](
                                cid, cname, update_chats_list,
                                handlers['open_existing_chat'], contact_dialog
                            )
                    )
                )
        page.update()

    # ── Обработчики ───────────────────────────────────────────────────────────

    handlers = setup_handlers(
        page=page, db_path=db, contacts=contacts, chats=chats,
        update_chats_list_func=update_chats_list,
        update_contacts_tab_func=update_contacts_tab,
    )

    exit_dlg.actions[0].on_click = lambda e: handlers['close_dialog'](e, exit_dlg)
    exit_dlg.actions[1].on_click = handlers['get_out']

    def open_new_chat_dialog(e):
        handlers['show_contact_selection'](
            e, contact_dialog, contact_list, search_field, contacts,
            lambda cid, cname: handlers['create_chat_with_contact'](
                cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
            ),
            loading_container, search_result_container,
            not_saved_col=not_saved_col,
            saved_col=saved_col,
            delete_btn_row=delete_btn_row,
        )

    new_chat_fab.on_click  = open_new_chat_dialog
    new_group_fab.on_click = handlers['soon_popup']

    # ── AppBar ────────────────────────────────────────────────────────────────

    appbar = ft.AppBar(
        leading=ft.Image(src="image/not_blocked_chat.ico",
                         width=10, height=10, fit=ft.ImageFit.CONTAIN),
        leading_width=40,
        title=ft.Text("Not Blocked Chat", weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[ft.PopupMenuButton(items=[
            ft.PopupMenuItem(content=ft.Container(
                content=ft.Column([
                    ft.CircleAvatar(foreground_image_src='image/user.png', radius=40),
                    ft.Text(user_data[0], weight=ft.FontWeight.BOLD, size=20,
                            text_align=ft.TextAlign.CENTER,
                            overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    ft.Text(user_data[1], size=12, color=ft.Colors.GREY,
                            text_align=ft.TextAlign.CENTER,
                            overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=ft.padding.symmetric(vertical=10),
                alignment=ft.alignment.center, width=250,
            )),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.CHAT, size=20), ft.Text('Новый чат')], spacing=10),
                on_click=open_new_chat_dialog,
            ),
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.GROUP_ADD, size=20), ft.Text('Новая группа')], spacing=10),
                on_click=handlers['soon_popup'],
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=20),
                                ft.Text("Настройки")], spacing=10),
                on_click=lambda _: page.go('/settings'),
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.LOGOUT, size=20), ft.Text("Выйти")], spacing=10),
                on_click=lambda _: handlers['open_dialog'](_, exit_dlg),
            ),
        ])],
    )

    # ── Вкладки ───────────────────────────────────────────────────────────────

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        expand=True,
        tab_alignment=ft.TabAlignment.FILL,
        tabs=[
            ft.Tab(
                text="Чаты", icon=ft.Icons.CHAT,
                content=ft.Container(
                    content=ft.Column([
                        chats_col,
                        ft.Row([new_chat_fab], alignment=ft.MainAxisAlignment.END),
                    ], expand=True, spacing=4),
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                    expand=True,
                ),
            ),
            ft.Tab(
                text="Группы", icon=ft.Icons.GROUP,
                content=ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.GROUP, size=50, color=ft.Colors.GREY),
                                ft.Text("Группы появятся здесь", size=16,
                                        color=ft.Colors.GREY),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                            alignment=ft.alignment.center, expand=True,
                        ),
                        ft.Row([new_group_fab], alignment=ft.MainAxisAlignment.END),
                    ], expand=True, spacing=4),
                    padding=ft.padding.all(10), expand=True,
                ),
            ),
            ft.Tab(
                text="Избранное", icon=ft.Icons.STAR,
                content=ft.Container(
                    content=favorites_col,
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                    expand=True,
                ),
            ),
        ],
    )

    update_chats_list()

    return ft.View(
        "/",
        [tabs, exit_dlg, contact_dialog],
        appbar=appbar,
        padding=0,
    )