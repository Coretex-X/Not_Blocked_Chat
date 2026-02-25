##############################################################################
# ФАЙЛ: database.py
# НАЗНАЧЕНИЕ: Все функции для работы с SQLite базой данных чата
# 
# СОДЕРЖАНИЕ:
# 1. Инициализация таблиц (contacts, chats)
# 2. Загрузка данных (контакты, чаты, пользователь)
# 3. Операции с чатами (создание, удаление)
# 4. Добавление тестовых данных при первом запуске
# 
# ОСНОВНЫЕ ФУНКЦИИ:
# - init_database()     - создает таблицы если их нет
# - load_contacts()     - загружает список контактов
# - load_chats()        - загружает список чатов
# - delete_chat_from_db()- удаляет чат по ID
# - create_new_chat()   - создает новый чат с контактом
# - get_user_data()     - получает данные текущего пользователя
# 
# ПРИМЕР ИСПОЛЬЗОВАНИЯ:
# from database import load_chats, create_new_chat
# chats = load_chats("путь/к/базе.db")
# new_chat_id = create_new_chat("путь/к/базе.db", 1, "Имя контакта")
# 
# ДЛЯ РАСШИРЕНИЯ:
# - Добавьте функции для работы с сообщениями
# - Добавьте функции для работы с группами
# - Реализуйте поиск по контактам/чатам
##############################################################################

import sqlite3 as sql
from datetime import datetime

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
            test_contacts = [
                ('Алексей Петров', 'В сети', '+79123456789', None),
                ('Мария Иванова', 'Был(а) недавно', '+79123456780', None),
                ('Иван Сидоров', 'В сети', '+79123456781', None),
                ('Елена Козлова', 'Не беспокоить', '+79123456782', None),
                ('Дмитрий Волков', 'В сети', '+79123456783', None),
            ]
            cur.executemany('INSERT INTO contacts (username, status, phone, avatar) VALUES (?, ?, ?, ?)', test_contacts)
            
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

def delete_chat_from_db(db_path, chat_id):
    """Удаление чата из базы данных"""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
        con.commit()
        return cur.rowcount > 0

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
            return result[0] if result else ['None', 'None']
        except sql.OperationalError:
            return ['None', 'None']