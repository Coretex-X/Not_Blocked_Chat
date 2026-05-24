import sqlite3 as sql
import datetime
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


# ── История сообщений ─────────────────────────────────────────────────────────

def init_messages_table():
    """Создаёт таблицу messages если её нет."""
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                sender_id   INTEGER,
                msg_type    TEXT    NOT NULL DEFAULT 'text',
                content     TEXT,
                file_path   TEXT,
                file_name   TEXT,
                quote_text  TEXT,
                is_user     INTEGER NOT NULL DEFAULT 1,
                one_time    INTEGER NOT NULL DEFAULT 0,
                timestamp   TEXT    NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
        """)
        con.commit()


def save_message(chat_id: int, sender_id, msg_type: str, content: str = None,
                 file_path: str = None, file_name: str = None,
                 quote_text: str = None, is_user: bool = True,
                 one_time: bool = False) -> int:
    """
    Сохраняет сообщение в БД. Возвращает id новой записи.
    msg_type: 'text' | 'image' | 'video' | 'audio' | 'document'
    """
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO messages
                (chat_id, sender_id, msg_type, content, file_path, file_name,
                 quote_text, is_user, one_time, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, sender_id, msg_type,
              content, file_path, file_name,
              quote_text, 1 if is_user else 0,
              1 if one_time else 0, ts))
        con.commit()
        # Обновляем last_message в чате
        preview = content if content else (file_name or "Медиафайл")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        cur.execute("""
            UPDATE chats SET last_message = ?, last_message_time = ?
            WHERE chat_id = ?
        """, (preview, ts, chat_id))
        con.commit()
        return cur.lastrowid


def load_messages(chat_id: int) -> list:
    """
    Загружает все сообщения чата в хронологическом порядке.
    Возвращает список словарей.
    """
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT id, sender_id, msg_type, content, file_path, file_name,
                   quote_text, is_user, one_time, timestamp
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
        """, (chat_id,))
        rows = cur.fetchall()
    return [
        {
            "id":         r[0],
            "sender_id":  r[1],
            "msg_type":   r[2],
            "content":    r[3],
            "file_path":  r[4],
            "file_name":  r[5],
            "quote_text": r[6],
            "is_user":    bool(r[7]),
            "one_time":   bool(r[8]),
            "timestamp":  r[9],
        }
        for r in rows
    ]


def delete_messages_for_chat(chat_id: int):
    """Удаляет все сообщения чата из БД (для «Очистить чат»)."""
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cur.execute(
            "UPDATE chats SET last_message = NULL, last_message_time = NULL WHERE chat_id = ?",
            (chat_id,)
        )
        con.commit()


def delete_single_message(msg_db_id: int):
    """Удаляет одно сообщение и обновляет last_message чата."""
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        # Узнаём chat_id удаляемого сообщения
        cur.execute("SELECT chat_id FROM messages WHERE id = ?", (msg_db_id,))
        row = cur.fetchone()
        chat_id = row[0] if row else None

        cur.execute("DELETE FROM messages WHERE id = ?", (msg_db_id,))
        con.commit()

        # Обновляем last_message: берём последнее оставшееся сообщение
        if chat_id:
            cur.execute("""
                SELECT content, file_name, timestamp FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC LIMIT 1
            """, (chat_id,))
            last = cur.fetchone()
            if last:
                preview = last[0] if last[0] else (last[1] or "Медиафайл")
                if len(preview) > 80:
                    preview = preview[:77] + "..."
                cur.execute(
                    "UPDATE chats SET last_message = ?, last_message_time = ? WHERE chat_id = ?",
                    (preview, last[2], chat_id)
                )
            else:
                cur.execute(
                    "UPDATE chats SET last_message = NULL, last_message_time = NULL WHERE chat_id = ?",
                    (chat_id,)
                )
            con.commit()


def update_message_content(msg_db_id: int, new_content: str):
    """Обновляет текст сообщения и last_message чата если это последнее сообщение."""
    with sql.connect(_db_path) as con:
        cur = con.cursor()
        # Узнаём chat_id сообщения
        cur.execute("SELECT chat_id FROM messages WHERE id = ?", (msg_db_id,))
        row = cur.fetchone()
        chat_id = row[0] if row else None

        cur.execute(
            "UPDATE messages SET content = ? WHERE id = ?",
            (new_content, msg_db_id)
        )
        con.commit()

        # Если это последнее сообщение чата — обновляем превью
        if chat_id:
            cur.execute("""
                SELECT id FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC LIMIT 1
            """, (chat_id,))
            last_row = cur.fetchone()
            if last_row and last_row[0] == msg_db_id:
                preview = new_content if new_content else "Медиафайл"
                if len(preview) > 80:
                    preview = preview[:77] + "..."
                cur.execute(
                    "UPDATE chats SET last_message = ? WHERE chat_id = ?",
                    (preview, chat_id)
                )
                con.commit()