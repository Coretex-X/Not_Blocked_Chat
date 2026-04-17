import flet as ft
from .utils import get_avatar_letter, format_chat_time, format_phone


def create_contact_item(contact: dict, on_click_handler) -> ft.Container:
    status = contact.get("status_user_contact", "save_user")
    if status == "not_save_user":
        display_name = format_phone(contact.get("phone", "")) or contact["username"]
        avatar_letter, avatar_bg = "#", ft.Colors.BLUE_GREY
    else:
        display_name = contact["username"]
        avatar_letter = get_avatar_letter(contact["username"])
        avatar_bg = ft.Colors.GREEN

    return ft.Container(
        content=ft.ListTile(
            leading=ft.Container(
                content=ft.Text(avatar_letter, size=16, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE),
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


def create_chat_item(chat: dict, on_click_handler, on_menu_handler=None,
                     contact_status="save_user") -> ft.Container:
    """Элемент чата с меню ⋮."""
    chat_id    = chat["id"]
    is_fav     = chat.get("is_favorite", False)
    fav_label  = "Убрать из избранного" if is_fav else "Добавить в избранное"
    fav_icon   = ft.Icons.STAR_OUTLINE if is_fav else ft.Icons.STAR

    time_badge = ft.Column(
        controls=[
            ft.Text(format_chat_time(chat["last_time"]), size=12, color=ft.Colors.GREY),
            *([ ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER, size=14) ] if is_fav else []),
            *([ ft.Container(
                content=ft.Text(str(chat["unread"]), color=ft.Colors.WHITE, size=12,
                                weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.GREEN, border_radius=20,
                padding=ft.padding.all(5),
            ) ] if chat["unread"] > 0 else []),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.END,
        spacing=3,
    )

    contact_item = (
        ft.PopupMenuItem(
            content=ft.Row([ft.Icon(ft.Icons.PERSON_ADD, size=18), ft.Text("Сохранить контакт")], spacing=8),
            on_click=lambda e: on_menu_handler(chat_id, "save_contact") if on_menu_handler else None,
        ) if contact_status == "not_save_user" else
        ft.PopupMenuItem(
            content=ft.Row([ft.Icon(ft.Icons.EDIT, size=18), ft.Text("Изменить контакт")], spacing=8),
            on_click=lambda e: on_menu_handler(chat_id, "edit_contact") if on_menu_handler else None,
        )
    )

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        icon_color=ft.Colors.ON_SURFACE,
        items=[
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(fav_icon, size=18, color=ft.Colors.AMBER),
                                ft.Text(fav_label)], spacing=8),
                on_click=lambda e: on_menu_handler(chat_id, "favorite") if on_menu_handler else None,
            ),
            contact_item,
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINE, size=18, color=ft.Colors.RED),
                                ft.Text("Удалить чат", color=ft.Colors.RED)], spacing=8),
                on_click=lambda e: on_menu_handler(chat_id, "delete") if on_menu_handler else None,
            ),
        ],
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.ListTile(
                    leading=ft.Container(
                        content=ft.Text(get_avatar_letter(chat["name"]), size=16,
                                        weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        width=50, height=50, border_radius=25,
                        bgcolor=ft.Colors.BLUE, alignment=ft.alignment.center,
                    ),
                    title=ft.Text(chat["name"], weight=ft.FontWeight.BOLD, size=16,
                                  overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    subtitle=ft.Text(chat["last_message"] or "Нет сообщений",
                                     size=14, color=ft.Colors.GREY,
                                     overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                    trailing=time_badge,
                    on_click=lambda e: on_click_handler(chat_id),
                    expand=True,
                ),
                menu,
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=5, right=0, top=2, bottom=2),
        border_radius=10,
        ink=True,
    )
