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
                username_save TEXT,
                status TEXT,
                phone TEXT,
                status_user_contact TEXT,
                redacted_username TEXT,
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
                is_favorite INTEGER DEFAULT 0,
                FOREIGN KEY (contact_id) REFERENCES contacts (user_id)
            )''')

        # Добавляем колонку is_favorite если её ещё нет (для существующих БД)
        try:
            cur.execute("ALTER TABLE chats ADD COLUMN is_favorite INTEGER DEFAULT 0")
            con.commit()
        except sql.OperationalError:
            pass  # Колонка уже существует

        con.commit()


def load_contacts(db_path):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id, username, status, phone, status_user_contact FROM contacts ORDER BY username")
        return [
            {"id": c[0], "username": c[1], "status": c[2], "phone": c[3], "status_user_contact": c[4]}
            for c in cur.fetchall()
        ]


def load_chats(db_path):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('''
            SELECT chat_id, chat_name, last_message, last_message_time, unread_count, is_favorite, contact_id
            FROM chats ORDER BY last_message_time DESC
        ''')
        return [
            {"id": c[0], "name": c[1], "last_message": c[2], "last_time": c[3], "unread": c[4], "is_favorite": bool(c[5]), "contact_id": c[6]}
            for c in cur.fetchall()
        ]


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


def save_contact_if_not_exists(db_path, contact_id, username, phone=""):
    """
    Сохраняет пользователя найденного через поиск по номеру в таблицу contacts,
    если его там ещё нет. Помечает как 'not_save_user' в поле status_user_contact.
    Возвращает True если запись была создана, False если уже существовала.
    """
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id FROM contacts WHERE user_id = ?", (contact_id,))
        if cur.fetchone() is not None:
            return False
        cur.execute(
            """INSERT INTO contacts (user_id, username, status, phone, status_user_contact, avatar)
               VALUES (?, ?, ?, ?, 'not_save_user', '')""",
            (contact_id, username, "", phone)
        )
        con.commit()
        return True


def get_contact_display_name(db_path, contact_id):
    """
    Возвращает отображаемое имя контакта:
    - если status_user_contact = 'not_save_user' — возвращает номер в формате +7 (XXX) XXX-XX-XX
    - иначе — возвращает username
    """
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT username, phone, status_user_contact FROM contacts WHERE user_id = ?",
            (contact_id,)
        )
        row = cur.fetchone()
        if row is None:
            return "Неизвестный"
        username, phone, status_user_contact = row
        if status_user_contact == 'not_save_user':
            return _format_phone(phone)
        return username if username else "Неизвестный"


def _format_phone(number):
    """Форматирует номер телефона в вид +7 (XXX) XXX-XX-XX"""
    if not number:
        return "Неизвестный"
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return number


# ─── ИЗБРАННОЕ ────────────────────────────────────────────────────────────────

def toggle_chat_favorite(db_path, chat_id):
    """Переключает статус избранного чата. Возвращает новое значение (True/False)."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT is_favorite FROM chats WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if row is None:
            return False
        new_value = 0 if row[0] else 1
        cur.execute("UPDATE chats SET is_favorite = ? WHERE chat_id = ?", (new_value, chat_id))
        con.commit()
        return bool(new_value)


def is_chat_favorite(db_path, chat_id):
    """Проверяет, находится ли чат в избранном."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT is_favorite FROM chats WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False


def load_favorite_chats(db_path):
    """Загружает только избранные чаты."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute('''
            SELECT chat_id, chat_name, last_message, last_message_time, unread_count, is_favorite, contact_id
            FROM chats WHERE is_favorite = 1 ORDER BY last_message_time DESC
        ''')
        return [
            {"id": c[0], "name": c[1], "last_message": c[2], "last_time": c[3], "unread": c[4], "is_favorite": True, "contact_id": c[6]}
            for c in cur.fetchall()
        ]


# ─── УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ И КОНТАКТОВ ────────────────────────────────────────

def delete_user_and_contacts(db_path):
    """
    Удаляет данные текущего пользователя и все его контакты из БД.
    Вызывается при нажатии кнопки 'Выйти'.
    """
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("UPDATE user_settings SET authorization = 'false'")
        cur.execute("DELETE FROM users_data")
        cur.execute("DELETE FROM contacts")
        cur.execute("DELETE FROM chats")
        con.commit()