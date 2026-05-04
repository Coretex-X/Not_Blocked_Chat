import sqlite3 as sql
from datetime import datetime
from .utils import format_phone


def init_database(db_path: str):
    """Создаёт все таблицы если их нет."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users_data(
                id_user INTEGER, name TEXT, profile TEXT,
                number TEXT, token TEXT, avatar TEXT)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contacts(
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT, username_save TEXT, status TEXT,
                phone TEXT, status_user_contact TEXT,
                redacted_username TEXT, avatar TEXT)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats(
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT NOT NULL,
                chat_type TEXT DEFAULT 'private',
                last_message TEXT,
                last_message_time DATETIME,
                unread_count INTEGER DEFAULT 0,
                contact_id INTEGER,
                is_favorite INTEGER DEFAULT 0,
                FOREIGN KEY (contact_id) REFERENCES contacts(user_id))
        """)
        # Миграция: добавляем is_favorite в старые БД
        try:
            cur.execute("ALTER TABLE chats ADD COLUMN is_favorite INTEGER DEFAULT 0")
            con.commit()
        except sql.OperationalError:
            pass
        con.commit()


# ── Пользователи ──────────────────────────────────────────────────────────────

def get_user_data(db_path: str) -> tuple:
    """Возвращает (name, profile) текущего пользователя."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        try:
            cur.execute("SELECT name, profile FROM users_data")
            return cur.fetchone() or ('None', 'None')
        except sql.OperationalError:
            return ('None', 'None')


def delete_user_and_contacts(db_path: str):
    """Удаляет все данные пользователя (выход из аккаунта)."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("UPDATE user_settings SET authorization = 'false'")
        cur.execute("DELETE FROM users_data")
        cur.execute("DELETE FROM contacts")
        cur.execute("DELETE FROM chats")
        con.commit()


# ── Контакты ──────────────────────────────────────────────────────────────────

def load_contacts(db_path: str) -> list:
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT user_id, username, status, phone, status_user_contact "
            "FROM contacts ORDER BY username"
        )
        return [
            {"id": r[0], "username": r[1], "status": r[2],
             "phone": r[3], "status_user_contact": r[4]}
            for r in cur.fetchall()
        ]


def save_contact_if_not_exists(db_path: str, contact_id, username, phone="") -> bool:
    """Сохраняет найденного пользователя как 'not_save_user'. Возвращает True если создан."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id FROM contacts WHERE user_id = ?", (contact_id,))
        if cur.fetchone():
            return False
        cur.execute(
            "INSERT INTO contacts (user_id, username, status, phone, status_user_contact, avatar) "
            "VALUES (?, ?, ?, ?, 'not_save_user', '')",
            (contact_id, username, "", phone)
        )
        con.commit()
        return True


def save_contact_name(db_path: str, contact_id, name: str) -> bool:
    """Сохраняет имя контакту и меняет статус на save_user."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE contacts SET username = ?, status_user_contact = 'save_user' "
            "WHERE user_id = ?",
            (name, contact_id)
        )
        # Обновляем имя чата тоже
        cur.execute(
            "UPDATE chats SET chat_name = ? WHERE contact_id = ?",
            (name, contact_id)
        )
        con.commit()
        return cur.rowcount > 0


def get_contact_display_name(db_path: str, contact_id) -> str:
    """Возвращает имя контакта или номер телефона, если контакт не сохранён."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT username, phone, status_user_contact FROM contacts WHERE user_id = ?",
            (contact_id,)
        )
        row = cur.fetchone()
    if not row:
        return "Неизвестный"
    username, phone, status = row
    if status == 'not_save_user':
        return format_phone(phone) or "Неизвестный"
    return username or "Неизвестный"


# ── Чаты ──────────────────────────────────────────────────────────────────────

def load_chats(db_path: str) -> list:
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT chat_id, chat_name, last_message, last_message_time, "
            "unread_count, is_favorite, contact_id "
            "FROM chats ORDER BY last_message_time DESC"
        )
        return [
            {"id": r[0], "name": r[1], "last_message": r[2], "last_time": r[3],
             "unread": r[4], "is_favorite": bool(r[5]), "contact_id": r[6]}
            for r in cur.fetchall()
        ]


def load_favorite_chats(db_path: str) -> list:
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT chat_id, chat_name, last_message, last_message_time, "
            "unread_count, is_favorite, contact_id "
            "FROM chats WHERE is_favorite = 1 ORDER BY last_message_time DESC"
        )
        return [
            {"id": r[0], "name": r[1], "last_message": r[2], "last_time": r[3],
             "unread": r[4], "is_favorite": True, "contact_id": r[6]}
            for r in cur.fetchall()
        ]


def create_new_chat(db_path: str, contact_id, contact_name: str) -> int:
    """Создаёт чат или возвращает существующий."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT chat_id FROM chats WHERE contact_id = ?", (contact_id,))
        existing = cur.fetchone()
        if existing:
            return existing[0]
        cur.execute(
            "INSERT INTO chats (chat_name, chat_type, last_message_time, contact_id) "
            "VALUES (?, 'private', ?, ?)",
            (contact_name, datetime.now(), contact_id)
        )
        con.commit()
        return cur.lastrowid


def delete_chat(db_path: str, chat_id: int) -> bool:
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        con.commit()
        return cur.rowcount > 0


def toggle_chat_favorite(db_path: str, chat_id: int) -> bool:
    """Переключает избранное. Возвращает новое значение."""
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT is_favorite FROM chats WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if not row:
            return False
        new_val = 0 if row[0] else 1
        cur.execute("UPDATE chats SET is_favorite = ? WHERE chat_id = ?", (new_val, chat_id))
        con.commit()
        return bool(new_val)


def get_contact_id_by_chat(db_path: str, chat_id: int):
    with sql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT contact_id FROM chats WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return row[0] if row else None