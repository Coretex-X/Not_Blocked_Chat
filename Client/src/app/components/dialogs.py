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

def create_exit_dialog():
    return ft.AlertDialog(
        title=ft.Text("Подтверждение выхода"),
        content=ft.Text("Вы уверены, что хотите выйти?"),
        actions=[
            ft.TextButton("Отмена", on_click=None),
            ft.TextButton("Да", on_click=None),
        ],
    )

def create_delete_chat_dialog():
    return ft.AlertDialog(
        title=ft.Text("Удаление чата"),
        content=ft.Text(""),
        actions=[],
    )

def create_contact_dialog():
    """Диалог выбора контакта с полем поиска"""
    search_field = ft.TextField(
        label="Поиск пользователя",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=20,
    )

    contact_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=2)

    dialog = ft.AlertDialog(
        title=ft.Text("Выберите контакт для чата"),
        content=ft.Container(
            content=ft.Column(
                controls=[search_field, contact_list],
                spacing=10,
            ),
            width=450,
            height=450,
        ),
        actions=[ft.TextButton("Отмена", on_click=None)]
    )

    return dialog, contact_list, search_field