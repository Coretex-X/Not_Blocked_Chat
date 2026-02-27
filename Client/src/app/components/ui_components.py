##############################################################################
# ФАЙЛ: ui_components.py
# НАЗНАЧЕНИЕ: Визуальные компоненты интерфейса (виджеты Flet)
# 
# СОДЕРЖАНИЕ:
# 1. Создание элементов списка (контакты, чаты)
# 2. Обработка событий наведения/кликов
# 3. Форматирование внешнего вида элементов
# 
# ОСНОВНЫЕ ФУНКЦИИ:
# - create_contact_item() - создает элемент контакта для списка
# - create_chat_item()    - создает элемент чата с кнопками действий
# - on_hover_chat()       - обработка наведения мыши на чат
# 
# ОСОБЕННОСТИ:
# - Элементы чатов имеют скрытые кнопки действий при наведении
# - Аватары генерируются из первой буквы имени
# - Поддержка непрочитанных сообщений (badge с числом)
# 
# ПРИМЕР ИСПОЛЬЗОВАНИЯ:
# from ui_components import create_chat_item
# chat_element = create_chat_item(chat_data, on_click_handler, on_delete_handler)
# 
# ДЛЯ РАСШИРЕНИЯ:
# - Добавьте новые типы элементов (сообщения, группы)
# - Реализуйте разные стили для разных типов чатов
# - Добавьте анимации для элементов
##############################################################################

import flet as ft
from .utils import get_avatar_letter, format_chat_time

def create_contact_item(contact, on_click_handler):
    """Создает элемент контакта с правильным форматированием текста"""
    avatar_letter = get_avatar_letter(contact["username"])
    
    return ft.Container(
        content=ft.ListTile(
            leading=ft.Container(
                content=ft.Text(
                    avatar_letter,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                width=50,
                height=50,
                border_radius=25,
                bgcolor=ft.Colors.GREEN,
                alignment=ft.alignment.center,
            ),
            title=ft.Text(
                contact["username"],
                weight=ft.FontWeight.BOLD,
                size=16,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
            subtitle=ft.Text(
                contact["status"],
                size=14,
                color=ft.Colors.GREY,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1,
            ),
            trailing=ft.Icon(ft.Icons.CHAT, color=ft.Colors.BLUE),
            on_click=on_click_handler,
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        on_click=on_click_handler,
    )

def create_chat_item(chat, on_click_handler, on_delete_handler=None):
    """Создает элемент чата с правильным форматированием текста"""
    avatar_letter = get_avatar_letter(chat["name"])
    
    # Создаем контейнер для кнопок действий
    action_buttons_container = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED,
                    icon_size=20,
                    tooltip="Удалить чат",
                    on_click=lambda e, cid=chat["id"]: on_delete_handler(cid) if on_delete_handler else None,
                ),
            ],
            spacing=2,
        ),
        padding=ft.padding.symmetric(horizontal=5),
        opacity=0,  # Изначально прозрачные
        animate_opacity=300,  # Анимация появления
    )
    
    # Основной контейнер чата
    chat_container = ft.Container(
        content=ft.Row(
            controls=[
                # Основной контент чата
                ft.Container(
                    expand=True,
                    content=ft.ListTile(
                        leading=ft.Container(
                            content=ft.Text(
                                avatar_letter,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                            ),
                            width=50,
                            height=50,
                            border_radius=25,
                            bgcolor=ft.Colors.BLUE,
                            alignment=ft.alignment.center,
                        ),
                        title=ft.Text(
                            chat["name"],
                            weight=ft.FontWeight.BOLD,
                            size=16,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        subtitle=ft.Text(
                            chat["last_message"] or "Нет сообщений",
                            size=14,
                            color=ft.Colors.GREY,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        trailing=ft.Column(
                            controls=[
                                ft.Text(
                                    format_chat_time(chat["last_time"]),
                                    size=12,
                                    color=ft.Colors.GREY,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        str(chat["unread"]), 
                                        color=ft.Colors.WHITE, 
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    bgcolor=ft.Colors.GREEN,
                                    border_radius=20,
                                    padding=ft.padding.all(6),
                                    visible=chat["unread"] > 0
                                ) if chat["unread"] > 0 else ft.Container(width=0, height=0)
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=5,
                        ),
                    )
                ),
                # Кнопки действий
                action_buttons_container
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        key=f"chat_{chat['id']}",
        on_click=lambda e: on_click_handler(chat["id"]),
        on_hover=lambda e: on_hover_chat(e, action_buttons_container),
    )
    
    return chat_container

def on_hover_chat(e, action_buttons):
    """Обработчик наведения на чат"""
    if e.data == "true":
        action_buttons.opacity = 1  # Показываем кнопки
    else:
        action_buttons.opacity = 0  # Скрываем кнопки
    action_buttons.update()