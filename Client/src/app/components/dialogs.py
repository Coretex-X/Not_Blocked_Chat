import flet as ft


def create_exit_dialog() -> ft.AlertDialog:
    return ft.AlertDialog(
        title=ft.Text("Подтверждение выхода"),
        content=ft.Text("Вы уверены, что хотите выйти?"),
        actions=[
            ft.TextButton("Отмена", on_click=None),
            ft.TextButton("Да", on_click=None),
        ],
    )


def create_contact_dialog():
    """Диалог выбора/поиска контакта. Возвращает (dialog, contact_list, search_field, loading_container, result_container)."""
    search_field = ft.TextField(
        label="Поиск пользователя по номеру",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=20,
    )
    loading_container = ft.Container(
        content=ft.ProgressRing(width=32, height=32, stroke_width=3, visible=False),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=10),
        visible=False,
    )
    search_result_container = ft.Container(visible=False)
    contact_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2)

    dialog = ft.AlertDialog(
        title=ft.Text("Выберите контакт для чата"),
        content=ft.Container(
            content=ft.Column(
                [search_field, loading_container, search_result_container, contact_list],
                spacing=10,
            ),
            width=float("inf"),
            height=400,
            expand=True,
        ),
        actions=[ft.TextButton("Отмена", on_click=None)],
        inset_padding=ft.padding.symmetric(horizontal=16, vertical=24),
    )
    return dialog, contact_list, search_field, loading_container, search_result_container
