##############################################################################
# ФАЙЛ: dialogs.py
# НАЗНАЧЕНИЕ: Создание и настройка диалоговых окон (модальных окон)
# 
# СОДЕРЖАНИЕ:
# 1. Предопределенные диалоги (выход, удаление, выбор контакта)
# 2. Базовая структура диалогов
# 3. Возврат ссылок на элементы диалогов для настройки
# 
# ОСНОВНЫЕ ФУНКЦИИ:
# - create_exit_dialog()      - диалог подтверждения выхода
# - create_delete_chat_dialog()- диалог подтверждения удаления чата
# - create_contact_dialog()   - диалог выбора контакта (возвращает диалог и список)
# 
# ОСОБЕННОСТИ:
# - Обработчики кнопок настраиваются в menu.py
# - Диалоги создаются заранее, но отображаются по необходимости
# - Можно легко добавлять новые диалоги
# 
# ПРИМЕР ИСПОЛЬЗОВАНИЯ:
# from dialogs import create_exit_dialog
# exit_dialog = create_exit_dialog()
# exit_dialog.actions[0].on_click = lambda e: print("Отмена")
# 
# ДЛЯ РАСШИРЕНИЯ:
# - Добавьте диалоги для настроек профиля
# - Реализуйте диалог создания группы
# - Добавьте диалог поиска контактов
##############################################################################

import flet as ft


def number(e):
    return e.value


def create_exit_dialog():
    return ft.AlertDialog(
        title=ft.Text("Подтверждение выхода"),
        content=ft.Text("Вы уверены, что хотите выйти?"),
        actions=[
            ft.TextButton("Отмена", on_click=None),
            ft.TextButton("Да", on_click=None),
        ],
        inset_padding=ft.padding.symmetric(horizontal=20, vertical=24),
    )


def create_delete_chat_dialog():
    return ft.AlertDialog(
        title=ft.Text("Удаление чата"),
        content=ft.Text(""),
        actions=[],
        inset_padding=ft.padding.symmetric(horizontal=20, vertical=24),
    )


def create_contact_dialog():
    """Диалог выбора контакта — ширина задаётся динамически при открытии"""
    search_field = ft.TextField(
        label="Поиск пользователя по номеру",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=20,
    )

    loading_ring = ft.ProgressRing(width=32, height=32, stroke_width=3, visible=False)
    loading_container = ft.Container(
        content=loading_ring,
        alignment=ft.alignment.center,
        padding=ft.padding.symmetric(vertical=10),
        visible=False,
    )

    search_result_container = ft.Container(visible=False)
    contact_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2)

    # content_width будет установлен динамически перед открытием
    content_container = ft.Container(
        content=ft.Column(
            controls=[
                search_field,
                loading_container,
                search_result_container,
                contact_list,
            ],
            spacing=10,
        ),
        height=400,
    )

    dialog = ft.AlertDialog(
        title=ft.Text("Выберите контакт для чата"),
        content=content_container,
        actions=[ft.TextButton("Отмена", on_click=None)],
        inset_padding=ft.padding.symmetric(horizontal=16, vertical=24),
    )

    return dialog, contact_list, search_field, loading_container, search_result_container, content_container