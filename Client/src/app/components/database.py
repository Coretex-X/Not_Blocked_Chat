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
    with sql.connect(db_path) as con:
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users_data(
                id_user INTEGER,
                name TEXT,
                profile TEXT,
                number TEXT,
                token TEXT,
                avatar TEXT
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS contacts(
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                status TEXT,
                phone TEXT,
                avatar TEXT
            )""")

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
            )''')

        con.commit()

def load_contacts(db_path):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id, username, status FROM contacts ORDER BY username")
        return [{"id": c[0], "username": c[1], "status": c[2]} for c in cur.fetchall()]

def load_chats(db_path):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('''
            SELECT chat_id, chat_name, last_message, last_message_time, unread_count 
            FROM chats ORDER BY last_message_time DESC
        ''')
        return [{"id": c[0], "name": c[1], "last_message": c[2], "last_time": c[3], "unread": c[4]}
                for c in cur.fetchall()]

def delete_chat_from_db(db_path, chat_id):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('DELETE FROM chats WHERE chat_id = ?', (chat_id,))
        con.commit()
        return cur.rowcount > 0

def create_new_chat(db_path, contact_id, contact_name):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('SELECT chat_id FROM chats WHERE contact_id = ?', (contact_id,))
        existing = cur.fetchone()
        if existing:
            return existing[0]
        cur.execute('''
            INSERT INTO chats (chat_name, chat_type, last_message_time, contact_id) 
            VALUES (?, 'private', ?, ?)
        ''', (contact_name, datetime.now(), contact_id))
        con.commit()
        return cur.lastrowid

def get_user_data(db_path):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT name, profile FROM users_data")
            result = cur.fetchone()
            return result if result else ('None', 'None')
        except sql.OperationalError:
            return ('None', 'None')
        
def get_contact_id_by_chat(db_path, chat_id):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT contact_id FROM chats WHERE chat_id = ?", (chat_id,))
        result = cur.fetchone()
        return result[0] if result else None
    
