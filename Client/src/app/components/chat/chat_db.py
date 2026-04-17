import sqlite3 as sql
import path

_db_path = f"{path.db_path()}user_data.db"


def get_current_user_id():
    """Возвращает id_user текущего пользователя."""
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id_user FROM users_data")
        row = cur.fetchone()
        return row[0] if row else None


def get_contact_data(contact_id):
    """Возвращает полную строку contacts по user_id контакта."""
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM contacts WHERE user_id = ?", (contact_id,))
        return cur.fetchone()
