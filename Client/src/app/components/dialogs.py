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
    """
    Диалог выбора/поиска контакта с двумя вкладками.
    При вводе в поиск — вкладки скрываются.
    Возвращает (dialog, contact_list, search_field, loading_container,
                result_container, not_saved_col, saved_col, delete_btn_row)
    """
    saved_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)
    not_saved_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, expand=True)

    delete_btn_row = ft.Row(
        controls=[],
        alignment=ft.MainAxisAlignment.CENTER,
        visible=False,
    )

    inner_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tab_alignment=ft.TabAlignment.FILL,
        tabs=[
            ft.Tab(
                text="Сохранённые",
                content=ft.Container(
                    content=saved_col,
                    padding=ft.padding.only(top=8),
                    expand=True,
                ),
            ),
            ft.Tab(
                text="Не сохранённые",
                content=ft.Container(
                    content=ft.Column(
                        [not_saved_col, delete_btn_row],
                        spacing=6,
                        expand=True,
                    ),
                    padding=ft.padding.only(top=8),
                    expand=True,
                ),
            ),
        ],
    )

    loading_container = ft.Container(
        content=ft.ProgressRing(width=32, height=32, stroke_width=3, visible=False),
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=10),
        visible=False,
    )

    search_result_container = ft.Container(visible=False)

    def on_search_change(e):
        has_text = bool(e.control.value.strip())
        inner_tabs.visible = not has_text
        e.control.page.update()

    search_field = ft.TextField(
        label="Поиск пользователя по номеру",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=20,
        on_change=on_search_change,
    )

    # contact_list для совместимости
    contact_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2, visible=False)

    dialog = ft.AlertDialog(
        title=ft.Text("Выберите контакт для чата"),
        content=ft.Container(
            content=ft.Column(
                [
                    search_field,
                    loading_container,
                    search_result_container,
                    inner_tabs,
                ],
                spacing=8,
                expand=True,
            ),
            width=float("inf"),
            height=460,
            expand=True,
        ),
        actions=[ft.TextButton("Отмена", on_click=None)],
        inset_padding=ft.padding.symmetric(horizontal=16, vertical=24),
    )

    return (dialog, contact_list, search_field, loading_container,
            search_result_container, not_saved_col, saved_col, delete_btn_row)