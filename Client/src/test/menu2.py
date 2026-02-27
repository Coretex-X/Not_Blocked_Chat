import flet as ft
import sqlite3 as sql 
import json as js
import os
from datetime import datetime

##########################################################################################################################################################################
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ И ЧАТАМИ
##########################################################################################################################################################################

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

def load_contacts(db_path):
    """Загрузка списка контактов из базы данных"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id, username, status FROM contacts ORDER BY username")
        contacts_data = cur.fetchall()
        return [{"id": c[0], "username": c[1], "status": c[2]} for c in contacts_data]

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

def create_chat_item(chat, on_click_handler):
    """Создает элемент чата с правильным форматированием текста"""
    avatar_letter = get_avatar_letter(chat["name"])
    
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
        ),
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
        border_radius=10,
        on_click=on_click_handler,
    )

##########################################################################################################################################################################
# ОСНОВНАЯ ФУНКЦИЯ ГЛАВНОГО МЕНЮ
##########################################################################################################################################################################

def main_menu(page):
    page.title = 'AppChat'
    user_profil = 'None'
    
    # Пути к базам данных
    db_path = "/home/username/Test/Test_Chat/Chat_Test/src/data/user_data.db"
    
    # Инициализация базы данных
    init_database(db_path)
    
    # Загрузка данных
    contacts = load_contacts(db_path)
    chats = load_chats(db_path)
    user_name = get_user_data(db_path)
    
    ##########################################################################################################################################################################
    # ФУНКЦИИ ДЛЯ РАБОТЫ С ИНТЕРФЕЙСОМ
    ##########################################################################################################################################################################
    
    def get_out(e):
        """Выход из приложения"""
        os.remove(db_path)
        page.go('/login')
        dlg.open = False
        page.update()
    
    def open_existing_chat(chat_id):
        """Открывает существующий чат"""
        print(f"Открываем чат {chat_id}")
        # page.go(f'/chat/{chat_id}')
    
    def update_chats_list():
        """Обновляет список чатов в интерфейсе"""
        nonlocal chats
        chats = load_chats(db_path)
        chats_container.controls.clear()
        
        if not chats:
            # Показываем сообщение если чатов нет
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
                    lambda e, cid=chat["id"]: open_existing_chat(cid)
                )
                chats_container.controls.append(chat_item)
        
        page.update()
    
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
    
    def create_chat_with_contact(contact_id, contact_name):
        """Создает чат с выбранным контактом и обновляет интерфейс"""
        chat_id = create_new_chat(db_path, contact_id, contact_name)
        
        update_chats_list()
        contact_dialog.open = False
        page.update()
        open_existing_chat(chat_id)
    
    def new_group(e):
        """Создание новой группы"""
        print("Создание новой группы")
    
    def chat_ai(e):
        """Чат с ИИ"""
        print("Чат с ИИ")
    
    def calls(e):
        """Функция для звонков"""
        print("Звонки")
    
    def close_dialog(e):
        """Закрытие диалога выхода"""
        dlg.open = False
        page.update()
    
    def open_dialog(e):
        """Открытие диалога выхода"""
        page.dialog = dlg
        dlg.open = True
        page.update()
    
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
    
    dlg = ft.AlertDialog(
        title=ft.Text("Подтверждение выхода"),
        content=ft.Text("Вы уверены, что хотите выйти из приложения?"),
        actions=[
            ft.TextButton("Да", on_click=get_out),
            ft.TextButton("Отмена", on_click=close_dialog),
        ],
    )
    
    # Диалог выбора контакта
    contact_list = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2
    )
    
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
    
    chats_container = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2,
        expand=True
    )
    
    contacts_tab_content = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        spacing=2,
        expand=True
    )
    
    # Кнопка создания нового чата
    new_chat_button = ft.FloatingActionButton(
        icon=ft.Icons.CHAT,
        text="Новый чат",
        on_click=show_contact_selection,
        mini=True
    )
    
    ##########################################################################################################################################################################
    # ВКЛАДКИ И ОСНОВНОЙ ИНТЕРФЕЙС
    ##########################################################################################################################################################################
    
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
        [tabs, dlg, contact_dialog],
        appbar=appbar,
        padding=0,
    )