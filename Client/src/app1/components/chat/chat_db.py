"""
chat_db.py — работа с базой данных SQLite
"""

import sqlite3 as sql
import path  # ваш модуль с путями

db_path = f"{path.db_path()}user_data.db"


def db_user_data(id):
    """Возвращает данные пользователя по user_id из таблицы contacts."""
    with sql.connect(db_path) as con:
        cur_data = con.cursor()
        cur_data.execute("SELECT * FROM contacts WHERE user_id = ?", (id,))
        result = cur_data.fetchone()
        return result
    
def db_user():
    with sql.connect(db_path) as con:
        cur_data = con.cursor()
        cur_data.execute("SELECT id_user FROM users_data")
        result = cur_data.fetchone()
        return result
