##############################################################################
# ФАЙЛ: menu.py
# НАЗНАЧЕНИЕ: Главная точка сборки интерфейса приложения
# 
# СОДЕРЖАНИЕ:
# 1. Импорт всех модулей и их сборка
# 2. Создание основного интерфейса (AppBar, Tabs, контейнеры)
# 3. Настройка связей между компонентами и обработчиками
# 4. Инициализация начального состояния
# 
# СТРУКТУРА:
# 1. Инициализация данных (БД, контакты, чаты)
# 2. Создание UI компонентов (контейнеры, кнопки)
# 3. Функции обновления интерфейса
# 4. Настройка обработчиков через setup_handlers()
# 5. Создание AppBar с меню
# 6. Создание вкладок (Чаты, Контакты, Группы)
# 7. Сборка итогового View
# 
# КЛЮЧЕВЫЕ МОМЕНТЫ:
# - Точка входа для Flet (возвращает ft.View)
# - Связывает все модули в единое целое
# - Управляет состоянием приложения
# - Обрабатывает навигацию между экранами
# 
# ПРИМЕР ИСПОЛЬЗОВАНИЯ:
# В основном файле приложения:
# from app.menu import main_menu
# def main(page):
#     return main_menu(page)
# 
# ДЛЯ РАСШИРЕНИЯ:
# - Добавьте новые вкладки в Tabs
# - Реализуйте разные темы оформления
# - Добавьте поддержку разных языков
##############################################################################

import flet as ft
import path
from .components.database import init_database, load_contacts, load_chats, create_new_chat, get_user_data
from .components.ui_components import create_contact_item, create_chat_item
from .components.dialogs import create_exit_dialog, create_delete_chat_dialog, create_contact_dialog
from .components.handlers import setup_handlers

def main_menu(page):
    page.title = 'Not Blocked Chat'

    db_path = f"{path.db_path()}user_data.db"
    init_database(db_path)

    contacts = load_contacts(db_path)
    chats = load_chats(db_path)
    user_data = get_user_data(db_path)  # (name, profile)

    dlg = create_exit_dialog()
    confirm_dialog = create_delete_chat_dialog()
    contact_dialog, contact_list, search_field = create_contact_dialog()

    chats_container = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)
    contacts_tab_content = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)
    new_chat_button = ft.FloatingActionButton(icon=ft.Icons.CHAT, text="Новый чат", on_click=None, mini=True)

    def update_chats_list():
        nonlocal chats
        chats = load_chats(db_path)
        chats_container.controls.clear()
        if not chats:
            chats_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CHAT, size=50, color=ft.Colors.GREY),
                        ft.Text("Нет чатов", size=16, color=ft.Colors.GREY),
                        ft.Text("Начните новый чат, нажав кнопку ниже", size=14, color=ft.Colors.GREY_400),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=ft.padding.all(50), alignment=ft.alignment.center,
                )
            )
        else:
            for chat in chats:
                chats_container.controls.append(
                    create_chat_item(
                        chat,
                        lambda cid=chat["id"]: handlers['open_existing_chat'](cid),
                        on_delete_handler=lambda cid: handlers['delete_chat_confirmation'](cid, confirm_dialog)
                    )
                )
        page.update()

    def update_contacts_tab():
        contacts_tab_content.controls.clear()
        if not contacts:
            contacts_tab_content.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CONTACTS, size=50, color=ft.Colors.GREY),
                        ft.Text("Нет контактов", size=16, color=ft.Colors.GREY),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=ft.padding.all(50), alignment=ft.alignment.center,
                )
            )
        else:
            for contact in contacts:
                contacts_tab_content.controls.append(
                    create_contact_item(
                        contact,
                        lambda e, cid=contact["id"], cname=contact["username"]: handlers['create_chat_with_contact'](
                            cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
                        )
                    )
                )
        page.update()

    handlers = setup_handlers(
        page=page, db_path=db_path, contacts=contacts, chats=chats,
        update_chats_list_func=update_chats_list,
        update_contacts_tab_func=update_contacts_tab
    )

    dlg.actions[0].on_click = lambda e: handlers['close_dialog'](e, dlg)
    dlg.actions[1].on_click = handlers['get_out']

    new_chat_button.on_click = lambda e: handlers['show_contact_selection'](
        e, contact_dialog, contact_list, search_field, contacts,
        lambda cid, cname: handlers['create_chat_with_contact'](
            cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
        )
    )

    appbar = ft.AppBar(
        leading=ft.Image(src="image/not_blocked_chat.ico", width=10, height=10, fit=ft.ImageFit.CONTAIN),
        leading_width=40,
        title=ft.Text("Not Blocked Chat", weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.PopupMenuButton(items=[
                ft.PopupMenuItem(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.CircleAvatar(foreground_image_src='image/user.png', radius=40),
                                ft.Text(user_data[0], weight=ft.FontWeight.BOLD, size=20,
                                        text_align=ft.TextAlign.CENTER, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                                ft.Text(user_data[1], size=12, color=ft.Colors.GREY,
                                        text_align=ft.TextAlign.CENTER, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
                        ),
                        padding=ft.padding.symmetric(vertical=10), alignment=ft.alignment.center, width=250,
                    )
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.CHAT, size=20), ft.Text('Новый чат')], spacing=10),
                    on_click=lambda e: handlers['show_contact_selection'](
                        e, contact_dialog, contact_list, search_field, contacts,
                        lambda cid, cname: handlers['create_chat_with_contact'](
                            cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
                        )
                    )
                ),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.GROUP_ADD, size=20), ft.Text('Новая группа')], spacing=10),
                    on_click=handlers['soon_popup'],
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=20), ft.Text("Настройки")], spacing=10),
                    on_click=lambda _: page.go('/settings')
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.LOGOUT, size=20), ft.Text("Выйти")], spacing=10),
                    on_click=lambda _: handlers['open_dialog'](_, dlg),
                ),
            ])
        ],
    )

    tabs = ft.Tabs(
        adaptive=True, selected_index=0, animation_duration=300,
        tabs=[
            ft.Tab(
                text="Чаты", icon=ft.Icons.CHAT,
                content=ft.Container(
                    content=ft.Column([chats_container, new_chat_button],
                                      scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                ),
            ),
            ft.Tab(
                text="Группы", icon=ft.Icons.GROUP,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.GROUP, size=50, color=ft.Colors.GREY),
                        ft.Text("Группы появятся здесь", size=16, color=ft.Colors.GREY),
                        ft.FloatingActionButton(icon=ft.Icons.GROUP_ADD, text="Создать группу",
                                                on_click=handlers['soon_popup'], mini=True)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center, padding=50
                ),
            ),
            ft.Tab(
                text="Избранное", icon=ft.Icons.STAR,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.STAR, size=50, color=ft.Colors.GREY),
                        ft.Text("Избранные чаты", size=16, color=ft.Colors.GREY),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center, padding=50
                ),
            ),
            ft.Tab(
                text='Контакты', icon=ft.Icons.CONTACTS,
                content=ft.Container(
                    content=contacts_tab_content,
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                ),
            ),
        ],
        expand=True,
    )

    update_chats_list()
    update_contacts_tab()

    return ft.View("/", [tabs, dlg, contact_dialog, confirm_dialog], appbar=appbar, padding=0)