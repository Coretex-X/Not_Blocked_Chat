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
from .components.database import init_database, load_contacts, load_chats, create_new_chat, get_user_data, delete_chat_from_db
from .components.ui_components import create_contact_item, create_chat_item, on_hover_chat
from .components.dialogs import create_exit_dialog, create_delete_chat_dialog, create_contact_dialog
from .components.handlers import setup_handlers

def main_menu(page):
    #page.title = 'AppChat'
    user_profil = 'None'
    
    # Пути к базам данных
    db_path = f"{path.db_path()}user_data.db"
    
    # Инициализация базы данных
    init_database(db_path)
    
    # Загрузка данных
    contacts = load_contacts(db_path)
    chats = load_chats(db_path)
    user_name = get_user_data(db_path)
    
    # Диалоги
    dlg = create_exit_dialog()
    confirm_dialog = create_delete_chat_dialog()
    contact_dialog, contact_list = create_contact_dialog()
    
    ########################################################################
    # UI КОМПОНЕНТЫ
    ########################################################################
    
    chats_container = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2,
        expand=True
    )
    
    contacts_tab_content = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2,
        expand=True
    )
    
    new_chat_button = ft.FloatingActionButton(
        icon=ft.Icons.CHAT,
        text="Новый чат",
        on_click=None,  # Будет установлено ниже
        mini=True
    )
    
    ########################################################################
    # ФУНКЦИИ ДЛЯ ОБНОВЛЕНИЯ ИНТЕРФЕЙСА
    ########################################################################
    
    def update_chats_list():
        """Обновляет список чатов в интерфейсе"""
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
                    padding=ft.padding.all(50),
                    alignment=ft.alignment.center,
                )
            )
        else:
            for chat in chats:
                chat_item = create_chat_item(
                    chat, 
                    lambda e, cid=chat["id"]: handlers['open_existing_chat'](cid),
                    on_delete_handler=lambda cid: handlers['delete_chat_confirmation'](cid, confirm_dialog)
                )
                chats_container.controls.append(chat_item)
        
        page.update()
    
    def update_contacts_tab():
        """Обновляет вкладку контактов"""
        contacts_tab_content.controls.clear()
        
        if not contacts:
            contacts_tab_content.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CONTACTS, size=50, color=ft.Colors.GREY),
                        ft.Text("Нет контактов", size=16, color=ft.Colors.GREY),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=ft.padding.all(50),
                    alignment=ft.alignment.center,
                )
            )
        else:
            for contact in contacts:
                contact_item = create_contact_item(
                    contact,
                    lambda e, cid=contact["id"], cname=contact["username"]: handlers['create_chat_with_contact'](
                        cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
                    )
                )
                contacts_tab_content.controls.append(contact_item)
        
        page.update()
    
    ########################################################################
    # НАСТРОЙКА ОБРАБОТЧИКОВ
    ########################################################################
    
    handlers = setup_handlers(
        page=page,
        db_path=db_path,
        contacts=contacts,
        chats=chats,
        update_chats_list_func=update_chats_list,
        update_contacts_tab_func=update_contacts_tab
    )
    
    # Настройка обработчиков для диалогов
    dlg.actions[0].on_click = lambda e: handlers['close_dialog'](e, dlg)
    dlg.actions[1].on_click = handlers['get_out']
    
    # Настройка кнопки нового чата
    new_chat_button.on_click = lambda e: handlers['show_contact_selection'](
        e, contact_dialog, contact_list, contacts,
        lambda cid, cname: handlers['create_chat_with_contact'](
            cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
        )
    )
    
    ########################################################################
    # APP BAR
    ########################################################################
    
    appbar = ft.AppBar(
        adaptive=True,
        leading=ft.Icon(ft.Icons.CHAT, color=ft.Colors.BLUE),
        leading_width=40,
        title=ft.Text("AppChat", weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.CircleAvatar(
                                        foreground_image_src='/home/archlinux05/Home/Photo/Z.png',
                                        radius=40,
                                    ),
                                    ft.Text(
                                        user_name[0], 
                                        weight=ft.FontWeight.BOLD, 
                                        size=20,
                                        text_align=ft.TextAlign.CENTER,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        max_lines=1,
                                    ),
                                    ft.Text(
                                        user_profil,
                                        size=12,
                                        color=ft.Colors.GREY,
                                        text_align=ft.TextAlign.CENTER,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        max_lines=1,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10,
                            ),
                            padding=ft.padding.symmetric(vertical=10),
                            alignment=ft.alignment.center,
                            width=250,
                        )
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHAT, size=20),
                                ft.Text('Новый чат'),
                            ],
                            spacing=10,
                        ),
                        on_click=lambda e: handlers['show_contact_selection'](
                            e, contact_dialog, contact_list, contacts,
                            lambda cid, cname: handlers['create_chat_with_contact'](
                                cid, cname, update_chats_list, handlers['open_existing_chat'], contact_dialog
                            )
                        )
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.GROUP_ADD, size=20),
                                ft.Text('Новая группа'),
                            ],
                            spacing=10,
                        ),
                        on_click=handlers['soon_popup'],
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=20),
                                ft.Text("Настройки"),
                            ],
                            spacing=10,
                        ),
                        on_click=lambda _: page.go('/settings')
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.LOGOUT, size=20),
                                ft.Text("Выйти"),
                            ],
                            spacing=10,
                        ),
                        on_click=lambda _: handlers['open_dialog'](_, dlg),
                    ),
                ]
            )
        ],
    )
    
    ########################################################################
    # ВКЛАДКИ
    ########################################################################
    
    tabs = ft.Tabs(
        adaptive=True,
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="Чаты",
                icon=ft.Icons.CHAT,
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            chats_container,
                            new_chat_button
                        ],
                        scroll=ft.ScrollMode.ADAPTIVE,
                        expand=True
                    ), 
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                ),
            ),
            ft.Tab(
                text="Группы",
                icon=ft.Icons.GROUP,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.GROUP, size=50, color=ft.Colors.GREY),
                        ft.Text("Группы появятся здесь", size=16, color=ft.Colors.GREY),
                        ft.FloatingActionButton(
                            icon=ft.Icons.GROUP_ADD,
                            text="Создать группу",
                            on_click=handlers['soon_popup'],
                            mini=True
                        )
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center,
                    padding=50
                ),
            ),
            ft.Tab(
                text="Избранное",
                icon=ft.Icons.STAR,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.GROUP, size=50, color=ft.Colors.GREY),
                        ft.Text("Избранные чаты", size=16, color=ft.Colors.GREY),
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    padding=50
                ),
            ),
            ft.Tab(
                text='Контакты',
                icon=ft.Icons.CONTACTS,
                content=ft.Container(
                    content=contacts_tab_content,
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                ),
            ),
        ],
        expand=True,
    )
    
    # Инициализация данных при загрузке
    update_chats_list()
    update_contacts_tab()
    
    return ft.View(
        "/",
        [tabs, dlg, contact_dialog, confirm_dialog],
        appbar=appbar,
        padding=0,
    )