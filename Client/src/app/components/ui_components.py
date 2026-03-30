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


def create_chat_item(chat, on_click_handler, on_menu_handler=None, contact_status="save_user"):
    """
    Создаёт элемент чата с кнопкой ⋮ в конце.
    contact_status: 'save_user' или 'not_save_user' — влияет на пункты меню.
    on_menu_handler(chat_id, action) где action: 'delete' | 'favorite' | 'save_contact' | 'edit_contact'
    """
    avatar_letter = get_avatar_letter(chat["name"])
    is_favorite = chat.get("is_favorite", False)
    chat_id = chat["id"]

    # Время + бейдж непрочитанных
    time_badge = ft.Column(
        controls=[
            ft.Text(format_chat_time(chat["last_time"]), size=12, color=ft.Colors.GREY),
            *([ ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER, size=14) ] if is_favorite else []),
            *([ ft.Container(
                content=ft.Text(str(chat["unread"]), color=ft.Colors.WHITE, size=12,
                                weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN, border_radius=20, padding=ft.padding.all(5),
            ) ] if chat["unread"] > 0 else []),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.END,
        spacing=3,
    )

    # Пункты меню зависят от статуса контакта
    favorite_label = "Убрать из избранного" if is_favorite else "Добавить в избранное"
    favorite_icon = ft.Icons.STAR_OUTLINE if is_favorite else ft.Icons.STAR

    if contact_status == "not_save_user":
        contact_menu_item = ft.PopupMenuItem(
            content=ft.Row([ft.Icon(ft.Icons.PERSON_ADD, size=18), ft.Text("Сохранить контакт")], spacing=8),
            on_click=lambda e: on_menu_handler(chat_id, "save_contact") if on_menu_handler else None,
        )
    else:
        contact_menu_item = ft.PopupMenuItem(
            content=ft.Row([ft.Icon(ft.Icons.EDIT, size=18), ft.Text("Изменить контакт")], spacing=8),
            on_click=lambda e: on_menu_handler(chat_id, "edit_contact") if on_menu_handler else None,
        )

    menu_button = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        items=[
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(favorite_icon, size=18, color=ft.Colors.AMBER), ft.Text(favorite_label)], spacing=8),
                on_click=lambda e: on_menu_handler(chat_id, "favorite") if on_menu_handler else None,
            ),
            contact_menu_item,
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=18, color=ft.Colors.RED), ft.Text("Удалить чат", color=ft.Colors.RED)], spacing=8),
                on_click=lambda e: on_menu_handler(chat_id, "delete") if on_menu_handler else None,
            ),
        ],
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.ListTile(
                    leading=ft.Container(
                        content=ft.Text(avatar_letter, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        width=50, height=50, border_radius=25,
                        bgcolor=ft.Colors.BLUE, alignment=ft.alignment.center,
                    ),
                    title=ft.Text(chat["name"], weight=ft.FontWeight.BOLD, size=16,
                                  overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    subtitle=ft.Text(chat["last_message"] or "Нет сообщений", size=14, color=ft.Colors.GREY,
                                     overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    trailing=time_badge,
                    on_click=lambda e: on_click_handler(chat_id),
                    expand=True,
                ),
                menu_button,
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=5, right=0, top=2, bottom=2),
        border_radius=10,
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