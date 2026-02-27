##############################################################################
# ФАЙЛ: handlers.py
# НАЗНАЧЕНИЕ: Все обработчики событий интерфейса (клики, нажатия)
# 
# СОДЕРЖАНИЕ:
# 1. Обработчики для кнопок и меню
# 2. Логика работы с диалогами
# 3. Функции навигации между окнами
# 
# ОСНОВНЫЕ ФУНКЦИИ:
# - setup_handlers()           - настраивает все обработчики
# - get_out()                  - выход из приложения
# - delete_chat_confirmation() - подтверждение удаления чата
# - soon_popup()               - показывает "Скоро" для недоступных функций
# - show_contact_selection()   - показывает выбор контакта для нового чата
# 
# КЛЮЧЕВЫЕ МОМЕНТЫ:
# - Все функции принимают параметр 'e' (событие)
# - Используют callback-функции для обновления UI
# - Работают с диалогами через page.dialog
# 
# ПРИМЕР ИСПОЛЬЗОВАНИЯ:
# from handlers import setup_handlers
# handlers = setup_handlers(page, db_path, contacts, chats, update_funcs)
# button.on_click = handlers['soon_popup']
# 
# ДЛЯ РАСШИРЕНИЯ:
# - Добавьте обработчики для отправки сообщений
# - Реализуйте обработку клавиатурных сочетаний
# - Добавьте обработчики drag & drop
##############################################################################

import os
from .database import load_chats, delete_chat_from_db, create_new_chat
import flet as ft

def setup_handlers(page, db_path, contacts, chats, update_chats_list_func, update_contacts_tab_func):
    """Настройка всех обработчиков событий"""
    
    def get_out(e):
        """Выход из приложения"""
        os.remove(db_path)
        page.go('/login')
        # Найдем диалог в page.controls если нужно
        page.update()
    
    def open_existing_chat(chat_id):
        """Открывает существующий чат"""
        print(f"Открываем чат {chat_id}")
        #page.go(f'/chat/{chat_id}')
        page.go('/chat')
    
    def delete_chat_confirmation(chat_id, confirm_dialog):
        """Подтверждение удаления чата"""
        chat_name = ""
        for chat in chats:
            if chat["id"] == chat_id:
                chat_name = chat["name"]
                break
        
        confirm_dialog.content = ft.Text(f"Вы уверены, что хотите удалить чат '{chat_name}'?")
        confirm_dialog.actions = [
            ft.TextButton("Удалить", on_click=lambda e: delete_chat(chat_id, confirm_dialog)),
            ft.TextButton("Отмена", on_click=lambda e: setattr(confirm_dialog, 'open', False) or page.update())
        ]
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()
    
    def delete_chat(chat_id, confirm_dialog):
        """Удаление чата"""
        if delete_chat_from_db(db_path, chat_id):
            print(f"Чат {chat_id} удален")
            update_chats_list_func()
            confirm_dialog.open = False
            page.update()
        else:
            print(f"Ошибка при удалении чата {chat_id}")
    
    def soon_popup(e):
        """Показывает всплывающее окно 'Скоро'"""
        # Простой AlertDialog вместо snack_bar
        dlg = ft.AlertDialog(
            title=ft.Text("Скоро"),
            content=ft.Text("Функция находится в разработке"),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()
    
    def show_contact_selection(e, contact_dialog, contact_list, contacts, create_chat_with_contact_func):
        """Показывает диалог выбора контакта для нового чата"""
        contact_list.controls.clear()
        
        if not contacts:
            contact_list.controls.append(
                ft.Container(
                    content=ft.Text("Нет контактов", text_align=ft.TextAlign.CENTER),
                    padding=20
                )
            )
        else:
            for contact in contacts:
                from .ui_components import create_contact_item
                contact_item = create_contact_item(
                    contact,
                    lambda e, cid=contact["id"], cname=contact["username"]: create_chat_with_contact_func(cid, cname)
                )
                contact_list.controls.append(contact_item)
        
        # Обновляем обработчики кнопок диалога
        contact_dialog.actions = [
            ft.TextButton("Отмена", on_click=lambda e: setattr(contact_dialog, 'open', False) or page.update())
        ]
        
        contact_dialog.open = True
        page.update()
    
    def create_chat_with_contact(contact_id, contact_name, update_chats_list_func, open_existing_chat_func, contact_dialog):
        """Создает чат с выбранным контактом и обновляет интерфейс"""
        chat_id = create_new_chat(db_path, contact_id, contact_name)
        
        update_chats_list_func()
        contact_dialog.open = False
        page.update()
        open_existing_chat_func(chat_id)
    
    def close_dialog(e, dlg):
        """Закрытие диалога выхода"""
        dlg.open = False
        page.update()
    
    def open_dialog(e, dlg):
        """Открытие диалога выхода"""
        page.dialog = dlg
        dlg.open = True
        page.update()
    
    # Возвращаем все функции
    return {
        'get_out': get_out,
        'open_existing_chat': open_existing_chat,
        'delete_chat_confirmation': delete_chat_confirmation,
        'delete_chat': delete_chat,
        'soon_popup': soon_popup,
        'show_contact_selection': show_contact_selection,
        'create_chat_with_contact': create_chat_with_contact,
        'close_dialog': close_dialog,
        'open_dialog': open_dialog
    }