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


def _format_phone(number):
    if not number:
        return ""
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return str(number)


def create_contact_item(contact, on_click_handler):
    status = contact.get("status_user_contact", "save_user")
    if status == "not_save_user":
        display_name = _format_phone(contact.get("phone", "")) or contact["username"]
        avatar_letter = "#"
        avatar_bg = ft.Colors.BLUE_GREY
    else:
        display_name = contact["username"]
        avatar_letter = get_avatar_letter(contact["username"])
        avatar_bg = ft.Colors.GREEN

    return ft.Container(
        content=ft.ListTile(
            leading=ft.Container(
                content=ft.Text(avatar_letter, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                width=50, height=50, border_radius=25,
                bgcolor=avatar_bg, alignment=ft.alignment.center,
            ),
            title=ft.Text(display_name, weight=ft.FontWeight.BOLD, size=16,
                          overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            subtitle=ft.Text(contact.get("status", ""), size=14, color=ft.Colors.GREY,
                             overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            trailing=ft.Icon(ft.Icons.CHAT, color=ft.Colors.BLUE),
            on_click=on_click_handler,
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        on_click=on_click_handler,
    )


def create_chat_item(chat, on_click_handler, on_long_press_handler=None):
    avatar_letter = get_avatar_letter(chat["name"])
    is_favorite = chat.get("is_favorite", False)

    trailing_controls = [
        ft.Text(format_chat_time(chat["last_time"]), size=12, color=ft.Colors.GREY),
    ]
    if is_favorite:
        trailing_controls.append(ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER, size=16))
    if chat["unread"] > 0:
        trailing_controls.append(
            ft.Container(
                content=ft.Text(str(chat["unread"]), color=ft.Colors.WHITE, size=12,
                                weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN, border_radius=20, padding=ft.padding.all(6),
            )
        )

    return ft.Container(
        content=ft.ListTile(
            leading=ft.Container(
                content=ft.Text(avatar_letter, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                width=50, height=50, border_radius=25,
                bgcolor=ft.Colors.BLUE, alignment=ft.alignment.center,
            ),
            title=ft.Text(chat["name"], weight=ft.FontWeight.BOLD, size=16,
                          overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            subtitle=ft.Text(chat["last_message"] or "Нет сообщений", size=14, color=ft.Colors.GREY,
                             overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            trailing=ft.Column(
                controls=trailing_controls,
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=4,
            ),
            on_click=lambda e: on_click_handler(chat["id"]),
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        on_long_press=lambda e: on_long_press_handler(chat["id"]) if on_long_press_handler else None,
        ink=True,
    )





'''import flet as ft
from .utils import get_avatar_letter, format_chat_time


def _format_phone(number):
    if not number:
        return ""
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return str(number)


def create_contact_item(contact, on_click_handler):
    status = contact.get("status_user_contact", "save_user")
    if status == "not_save_user":
        display_name = _format_phone(contact.get("phone", "")) or contact["username"]
        avatar_letter = "#"
        avatar_bg = ft.Colors.BLUE_GREY
    else:
        display_name = contact["username"]
        avatar_letter = get_avatar_letter(contact["username"])
        avatar_bg = ft.Colors.GREEN

    return ft.Container(
        content=ft.ListTile(
            leading=ft.Container(
                content=ft.Text(avatar_letter, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                width=50, height=50, border_radius=25,
                bgcolor=avatar_bg, alignment=ft.alignment.center,
            ),
            title=ft.Text(display_name, weight=ft.FontWeight.BOLD, size=16,
                          overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            subtitle=ft.Text(contact.get("status", ""), size=14, color=ft.Colors.GREY,
                             overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            trailing=ft.Icon(ft.Icons.CHAT, color=ft.Colors.BLUE),
            on_click=on_click_handler,
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        on_click=on_click_handler,
    )


def create_chat_item(chat, on_click_handler, on_long_press_handler=None):
    avatar_letter = get_avatar_letter(chat["name"])
    is_favorite = chat.get("is_favorite", False)
    chat_id = chat["id"]

    trailing_controls = [
        ft.Text(format_chat_time(chat["last_time"]), size=12, color=ft.Colors.GREY),
    ]
    if is_favorite:
        trailing_controls.append(ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER, size=16))
    if chat["unread"] > 0:
        trailing_controls.append(
            ft.Container(
                content=ft.Text(str(chat["unread"]), color=ft.Colors.WHITE, size=12,
                                weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN, border_radius=20, padding=ft.padding.all(6),
            )
        )

    inner = ft.Container(
        content=ft.ListTile(
            leading=ft.Container(
                content=ft.Text(avatar_letter, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                width=50, height=50, border_radius=25,
                bgcolor=ft.Colors.BLUE, alignment=ft.alignment.center,
            ),
            title=ft.Text(chat["name"], weight=ft.FontWeight.BOLD, size=16,
                          overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            subtitle=ft.Text(chat["last_message"] or "Нет сообщений", size=14, color=ft.Colors.GREY,
                             overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
            trailing=ft.Column(
                controls=trailing_controls,
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=4,
            ),
            on_click=lambda e: on_click_handler(chat_id),
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        ink=True,
    )

    if on_long_press_handler:
        return ft.GestureDetector(
            content=inner,
            on_long_press_start=lambda e: on_long_press_handler(chat_id),
        )

    return inner'''