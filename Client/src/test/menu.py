import flet as ft
import sqlite3 as sql 
import json as js
import os
from datetime import datetime

##########################################################################################################################################################################
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ И ЧАТАМИ
##########################################################################################################################################################################

#1
def init_database(db_path):
    """Инициализация базы данных и создание таблиц если их нет"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        
        # Таблица контактов
        cur.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                status TEXT,
                phone TEXT,
                avatar TEXT
            )
        ''')
        
        # Таблица чатов
        cur.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT NOT NULL,
                chat_type TEXT DEFAULT 'private',
                last_message TEXT,
                last_message_time DATETIME,
                unread_count INTEGER DEFAULT 0,
                contact_id INTEGER,
                FOREIGN KEY (contact_id) REFERENCES contacts (user_id)
            )
        ''')
        
        # Проверяем есть ли тестовые контакты
        cur.execute("SELECT COUNT(*) FROM contacts")
        if cur.fetchone()[0] == 0:
            # Добавляем тестовые контакты
            test_contacts = [
                ('Алексей Петров', 'В сети', '+79123456789', None),
                ('Мария Иванова', 'Был(а) недавно', '+79123456780', None),
                ('Иван Сидоров', 'В сети', '+79123456781', None),
                ('Елена Козлова', 'Не беспокоить', '+79123456782', None),
                ('Дмитрий Волков', 'В сети', '+79123456783', None),
            ]
            cur.executemany('INSERT INTO contacts (username, status, phone, avatar) VALUES (?, ?, ?, ?)', test_contacts)
            
            # Добавляем тестовые чаты
            test_chats = [
                ('Алексей Петров', 'Привет! Как дела?', '2024-01-15 14:30:00', 2, 1),
                ('Мария Иванова', 'Договорились на завтра', '2024-01-15 13:15:00', 0, 2),
                ('Иван Сидоров', 'Файл отправлен', '2024-01-14 18:45:00', 1, 3),
                ('Елена Козлова', 'Спасибо за помощь!', '2024-01-14 12:20:00', 0, 4),
            ]
            cur.executemany('''
                INSERT INTO chats (chat_name, last_message, last_message_time, unread_count, contact_id) 
                VALUES (?, ?, ?, ?, ?)
            ''', test_chats)
        
        con.commit()

#2
def load_contacts(db_path):
    """Загрузка списка контактов из базы данных"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id, username, status FROM contacts ORDER BY username")
        contacts_data = cur.fetchall()
        return [{"id": c[0], "username": c[1], "status": c[2]} for c in contacts_data]

#3
def load_chats(db_path):
    """Загрузка списка чатов из базы данных"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('''
            SELECT c.chat_id, c.chat_name, c.last_message, c.last_message_time, c.unread_count 
            FROM chats c 
            ORDER BY c.last_message_time DESC
        ''')
        chats_data = cur.fetchall()
        return [{
            "id": c[0], 
            "name": c[1], 
            "last_message": c[2], 
            "last_time": c[3], 
            "unread": c[4]
        } for c in chats_data]

#30
def delete_chat_from_db(db_path, chat_id):
    """Удаление чата из базы данных"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
        con.commit()
        return cur.rowcount > 0

#4
def format_chat_time(time_string):
    """Форматирование времени для отображения в списке чатов"""
    if not time_string:
        return ""
    
    try:
        if '.' in time_string:
            dt = datetime.strptime(time_string, '%Y-%m-%d %H:%M:%S.%f')
        else:
            dt = datetime.strptime(time_string, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%H:%M')
    except ValueError:
        return ""

#5
def create_new_chat(db_path, contact_id, contact_name):
    """Создает новый чат с контактом и возвращает ID созданного чата"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        
        cur.execute('SELECT chat_id FROM chats WHERE contact_id = ?', (contact_id,))
        existing_chat = cur.fetchone()
        
        if existing_chat:
            return existing_chat[0]
        else:
            cur.execute('''
                INSERT INTO chats (chat_name, chat_type, last_message_time, contact_id) 
                VALUES (?, 'private', ?, ?)
            ''', (contact_name, datetime.now(), contact_id))
            con.commit()
            return cur.lastrowid

#6
def get_user_data(db_path):
    """Получение данных текущего пользователя"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT name, profile FROM users_data")
            result = cur.fetchall()
            return result[0] if result else ['Гость', 'None']
        except sql.OperationalError:
            return ['Гость', 'None']

#7
def get_avatar_letter(name):
    """Преобразует первую букву имени в английскую для аватара"""
    if not name or len(name) == 0:
        return "U"
    
    first_char = name[0].upper()
    cyr_to_lat = {
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'E', 'Ж': 'Z', 'З': 'Z', 'И': 'I',
        'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'C',
        'Ш': 'S', 'Щ': 'S', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'U', 'Я': 'Y',
        'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E',
        'F': 'F', 'G': 'G', 'H': 'H', 'I': 'I', 'J': 'J',
        'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N', 'O': 'O',
        'P': 'P', 'Q': 'Q', 'R': 'R', 'S': 'S', 'T': 'T',
        'U': 'U', 'V': 'V', 'W': 'W', 'X': 'X', 'Y': 'Y', 'Z': 'Z'
    }
    return cyr_to_lat.get(first_char, 'U')

#8
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

#9
def create_chat_item(chat, on_click_handler, on_delete_handler=None):
    """Создает элемент чата с правильным форматированием текста"""
    avatar_letter = get_avatar_letter(chat["name"])
    
    # Создаем кнопки действий для чата
    action_buttons = []
    if on_delete_handler:
        action_buttons = [
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=ft.Colors.RED,
                icon_size=20,
                tooltip="Удалить чат",
                on_click=lambda e, cid=chat["id"]: on_delete_handler(cid),
            ),
            ft.IconButton(
                icon=ft.Icons.ARCHIVE_OUTLINED,
                icon_color=ft.Colors.GREY,
                icon_size=20,
                tooltip="Архивировать",
                on_click=lambda e, cid=chat["id"]: archive_chat(cid),
            ),
            ft.IconButton(
                icon=ft.Icons.NOTIFICATIONS_OFF_OUTLINED,
                icon_color=ft.Colors.GREY,
                icon_size=20,
                tooltip="Отключить уведомления",
                on_click=lambda e, cid=chat["id"]: mute_chat(cid),
            ),
        ]
    
    return ft.Container(
        content=ft.Row(
            controls=[
                # Основной контент чата - используем Container вместо Expanded
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
                        on_click=on_click_handler,
                    )
                ),
                # Кнопки действий (появляются при наведении)
                ft.Container(
                    content=ft.Row(
                        controls=action_buttons,
                        spacing=2,
                        visible=False,  # Изначально скрыты
                    ),
                    padding=ft.padding.symmetric(horizontal=5),
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        on_click=on_click_handler,
        on_hover=lambda e: show_chat_actions(e, chat["id"]),  # Показываем кнопки при наведении
        key=f"chat_{chat['id']}",  # Уникальный ключ для идентификации
    )

##########################################################################################################################################################################
# ОСНОВНАЯ ФУНКЦИЯ ГЛАВНОГО МЕНЮ
##########################################################################################################################################################################

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
                    on_click=lambda e, cid=chat["id"]: on_delete_handler(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.ARCHIVE_OUTLINED,
                    icon_color=ft.Colors.GREY,
                    icon_size=20,
                    tooltip="Архивировать",
                    on_click=lambda e, cid=chat["id"]: archive_chat(cid),
                ),
                ft.IconButton(
                    icon=ft.Icons.NOTIFICATIONS_OFF_OUTLINED,
                    icon_color=ft.Colors.GREY,
                    icon_size=20,
                    tooltip="Отключить уведомления",
                    on_click=lambda e, cid=chat["id"]: mute_chat(cid),
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

#10
def main_menu(page):
    page.title = 'AppChat'
    user_profil = 'None'
    
    # Пути к базам данных
    db_path = "/home/archlinux05/Home/Chat_Test/src/data/user_data.db"
    
    # Инициализация базы данных
    init_database(db_path)
    
    # Загрузка данных
    contacts = load_contacts(db_path)
    chats = load_chats(db_path)
    user_name = get_user_data(db_path)
    
    ##########################################################################################################################################################################
    # ФУНКЦИИ ДЛЯ РАБОТЫ С ИНТЕРФЕЙСОМ
    ##########################################################################################################################################################################
    
    #11
    def get_out(e):
        """Выход из приложения"""
        os.remove(db_path)
        page.go('/login')
        dlg.open = False
        page.update()
    
    #12
    def open_existing_chat(chat_id):
        """Открывает существующий чат"""
        print(f"Открываем чат {chat_id}")
        # page.go(f'/chat/{chat_id}')
    
    #31
    def delete_chat_confirmation(chat_id):
        """Подтверждение удаления чата"""
        # Находим имя чата для сообщения
        chat_name = ""
        for chat in chats:
            if chat["id"] == chat_id:
                chat_name = chat["name"]
                break
        
        confirm_dialog.content = ft.Text(f"Вы уверены, что хотите удалить чат '{chat_name}'?")
        confirm_dialog.actions = [
            ft.TextButton("Удалить", on_click=lambda e: delete_chat(chat_id)),
            ft.TextButton("Отмена", on_click=lambda e: setattr(confirm_dialog, 'open', False) or page.update())
        ]
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()
    
    #32
    def delete_chat(chat_id):
        """Удаление чата"""
        if delete_chat_from_db(db_path, chat_id):
            print(f"Чат {chat_id} удален")
            update_chats_list()
            confirm_dialog.open = False
            page.update()
        else:
            print(f"Ошибка при удалении чата {chat_id}")
    
    #33
    def archive_chat(chat_id):
        """Архивирование чата"""
        print(f"Архивируем чат {chat_id}")
        # Здесь можно добавить логику архивации в БД
        page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(f"Чат перемещен в архив"),
                action="OK"
            )
        )
    
    #34
    def mute_chat(chat_id):
        """Отключение уведомлений для чата"""
        print(f"Отключаем уведомления для чата {chat_id}")
        # Здесь можно добавить логику отключения уведомлений в БД
        page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(f"Уведомления отключены"),
                action="OK"
            )
        )
    
    #35
    def show_chat_actions(e, chat_id):
        """Показывает/скрывает кнопки действий при наведении на чат"""
        chat_container = e.control
        action_buttons = chat_container.content.controls[1].content
        
        if e.data == "true":  # При наведении
            action_buttons.visible = True
        else:  # При уходе мыши
            action_buttons.visible = False
        
        action_buttons.update()
    
    #13
    def update_chats_list():
        """Обновляет список чатов в интерфейсе"""
        nonlocal chats
        chats = load_chats(db_path)
        chats_container.controls.clear()
        
        if not chats:
            # Показываем сообствие если чатов нет
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
                    lambda e, cid=chat["id"]: open_existing_chat(cid),
                    on_delete_handler=delete_chat_confirmation
                )
                chats_container.controls.append(chat_item)
        
        page.update()
    
    #14
    def show_contact_selection(e):
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
                contact_item = create_contact_item(
                    contact,
                    lambda e, cid=contact["id"], cname=contact["username"]: create_chat_with_contact(cid, cname)
                )
                contact_list.controls.append(contact_item)
        
        contact_dialog.open = True
        page.update()
    
    #15
    def create_chat_with_contact(contact_id, contact_name):
        """Создает чат с выбранным контактом и обновляет интерфейс"""
        chat_id = create_new_chat(db_path, contact_id, contact_name)
        
        update_chats_list()
        contact_dialog.open = False
        page.update()
        open_existing_chat(chat_id)
    
    #16
    def new_group(e):
        """Создание новой группы"""
        print("Создание новой группы")
    
    #17
    def chat_ai(e):
        """Чат с ИИ"""
        print("Чат с ИИ")
    
    #18
    def calls(e):
        """Функция для звонков"""
        print("Звонки")
    
    #19
    def close_dialog(e):
        """Закрытие диалога выхода"""
        dlg.open = False
        page.update()
    
    #20
    def open_dialog(e):
        """Открытие диалога выхода"""
        page.dialog = dlg
        dlg.open = True
        page.update()
    
    #21
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
                    lambda e, cid=contact["id"], cname=contact["username"]: create_chat_with_contact(cid, cname)
                )
                contacts_tab_content.controls.append(contact_item)
        
        page.update()

    ##########################################################################################################################################################################
    # ДИАЛОГИ
    ##########################################################################################################################################################################
    
    #22
    dlg = ft.AlertDialog(
        title=ft.Text("Подтверждение выхода"),
        content=ft.Text("Вы уверены, что хотите выйти из приложения?"),
        actions=[
            ft.TextButton("Да", on_click=get_out),
            ft.TextButton("Отмена", on_click=close_dialog),
        ],
    )
    
    #36
    confirm_dialog = ft.AlertDialog(
        title=ft.Text("Удаление чата"),
        content=ft.Text(""),
        actions=[],
    )
    
    # Диалог выбора контакта
    #23
    contact_list = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2
    )
    
    #24
    contact_dialog = ft.AlertDialog(
        title=ft.Text("Выберите контакт для чата"),
        content=ft.Container(
            content=contact_list,
            width=450,
            height=400,
        ),
        actions=[
            ft.TextButton("Отмена", on_click=lambda e: setattr(contact_dialog, 'open', False) or page.update())
        ]
    )
    
    ##########################################################################################################################################################################
    # ЭЛЕМЕНТЫ ИНТЕРФЕЙСА
    ##########################################################################################################################################################################
    
    #25
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
                                        foreground_image_src='/home/archlinux05/ChatApp/TestServerApp/media/images/Z.png',
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
                        on_click=show_contact_selection
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.GROUP_ADD, size=20),
                                ft.Text('Новая группа'),
                            ],
                            spacing=10,
                        ),
                        on_click=new_group,
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SMART_TOY, size=20),
                                ft.Text('Чат с ИИ'),
                            ],
                            spacing=10,
                        ),
                        on_click=chat_ai
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.DATA_SAVER_OFF, size=20),
                                ft.Text("Статус"),
                            ],
                            spacing=10,
                        ),
                        on_click= lambda _: page.go('/status')
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CALL, size=20),
                                ft.Text("Звонки"),
                            ],
                            spacing=10,
                        ),
                        on_click=calls
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=20),
                                ft.Text("Настройки"),
                            ],
                            spacing=10,
                        ),
                        on_click= lambda _: page.go('/settings')
                    ),
                    ft.PopupMenuItem(),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Text("Войти"),
                                ft.Icon(ft.Icons.LOGIN, size=20)
                            ],
                            spacing=10,
                        ),
                        on_click = lambda _: page.go('/login'),
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.LOGOUT, size=20),
                                ft.Text("Выйти"),
                            ],
                            spacing=10,
                        ),
                        on_click = open_dialog,
                    ),
                ]
            )
        ],
    )
    
    ##########################################################################################################################################################################
    # КОНТЕЙНЕРЫ ДЛЯ ДАННЫХ
    ##########################################################################################################################################################################
    
    #26
    chats_container = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2,
        expand=True
    )
    
    #27
    contacts_tab_content = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2,
        expand=True
    )
    
    # Кнопка создания нового чата
    #28
    new_chat_button = ft.FloatingActionButton(
        icon=ft.Icons.CHAT,
        text="Новый чат",
        on_click=show_contact_selection,
        mini=True
    )
    
    ##########################################################################################################################################################################
    # ВКЛАДКИ И ОСНОВНОЙ ИНТЕРФЕЙС
    ##########################################################################################################################################################################
    
    #29
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
                text='Контакты',
                icon=ft.Icons.CONTACTS,
                content=ft.Container(
                    content=contacts_tab_content,
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
                            on_click=new_group,
                            mini=True
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    alignment=ft.alignment.center,
                    padding=50
                ),
            ),
        ],
        expand=True,
    )
    
    # Инициализация данных при загрузке
    update_chats_list()
    update_contacts_tab()
    
    ########################################################################################################################################################################## 
    return ft.View(
        "/",
        [tabs, dlg, contact_dialog, confirm_dialog],
        appbar=appbar,
        padding=0,
    )