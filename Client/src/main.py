import flet as ft
import sqlite3 as ql
import path
import websocket
import json
import threading
import requests
from app import notification_bridge
from app.menu import main_menu
from app.settings import settings_view
from app.registration import main_registartion
from app.sign_up import main_sign_up
from app.chat import chat_view

db_path  = f"{path.db_path()}user_data.db"
WS_HOST  = "ws://127.0.0.1:5000"
API_HOST = "http://127.0.0.1:5000"

ws_notification     = None
notification_thread = None

# ── Инициализация БД ──────────────────────────────────────────────────────────

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_data(
            id_user INTEGER, name TEXT, profile TEXT,
            number TEXT, token TEXT, room TEXT, avatar TEXT)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings(
            authorization TEXT DEFAULT 'false',
            color_theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'ru',
            font_size TEXT DEFAULT '17')
    """)
    try:
        cur.execute("ALTER TABLE user_settings ADD COLUMN font_size TEXT DEFAULT '14'")
    except ql.OperationalError:
        pass
    con.commit()

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("SELECT authorization, color_theme FROM user_settings LIMIT 1")
    row = cur.fetchone()
    is_authorized = (row[0] if row else 'false') == 'true'
    color_theme   = row[1] if row and row[1] else 'dark'


# ── Вспомогательные функции БД ────────────────────────────────────────────────

def get_user_data():
    with ql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id_user, token, room FROM users_data LIMIT 1")
        row = cur.fetchone()
        return {"user_id": row[0], "token": row[1], "room": row[2]} if (row and row[0] and row[1] and row[2]) else None


def is_contact_blocked(sender_id: str) -> bool:
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT is_blocked FROM contacts WHERE user_id = ?", (sender_id,))
            row = cur.fetchone()
            return bool(row[0]) if row and row[0] else False
    except Exception:
        return False


def get_chat_id_by_contact(sender_id: str):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT chat_id FROM chats WHERE contact_id = ?", (sender_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def increment_unread(chat_id: int):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE chats SET unread_count = unread_count + 1 WHERE chat_id = ?", (chat_id,))
            con.commit()
    except Exception as e:
        print(f"[UNREAD] Ошибка: {e}")


def reset_unread(chat_id: int):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE chats SET unread_count = 0 WHERE chat_id = ?", (chat_id,))
            con.commit()
    except Exception as e:
        print(f"[UNREAD] Ошибка сброса: {e}")


def save_message_to_db(sender_id: str, message: str, chat_id: int, timestamp: str = None):
    """Сохраняет входящее сообщение напрямую через sqlite."""
    try:
        import datetime
        ts = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with ql.connect(db_path) as con:
            cur = con.cursor()
            # Дедупликация по точному timestamp + sender + content
            cur.execute("""
                SELECT id FROM messages
                WHERE chat_id=? AND content=? AND sender_id=? AND timestamp=?
                LIMIT 1
            """, (chat_id, message, sender_id, ts))
            if cur.fetchone():
                print(f"[УВЕДОМЛЕНИЕ] Дубликат по timestamp, пропускаем")
                return
            cur.execute("""
                INSERT INTO messages (chat_id, sender_id, msg_type, content, is_user, one_time, timestamp)
                VALUES (?, ?, 'text', ?, 0, 0, ?)
            """, (chat_id, sender_id, message, ts))
            preview = message[:80]
            cur.execute(
                "UPDATE chats SET last_message=?, last_message_time=? WHERE chat_id=?",
                (preview, ts, chat_id))
            con.commit()
        print(f"[УВЕДОМЛЕНИЕ] ✅ Сохранено в чат {chat_id}: {message[:30]}")
    except Exception as ex:
        print(f"[УВЕДОМЛЕНИЕ] ❌ Ошибка сохранения: {ex}")


# ── Уведомления ───────────────────────────────────────────────────────────────

def listen_notifications():
    global ws_notification
    while True:
        try:
            raw  = ws_notification.recv()
            data = json.loads(raw)
            print(f"[УВЕДОМЛЕНИЕ] {json.dumps(data, ensure_ascii=False)}")
            if data.get("type") == "new_message":
                sender_id = str(data.get("sender_id", ""))
                msg_text  = data.get("message", "")
                msg_ts    = data.get("timestamp", "")
                if not sender_id:
                    continue
                if is_contact_blocked(sender_id):
                    print(f"[УВЕДОМЛЕНИЕ] Отправитель {sender_id} заблокирован, пропускаем")
                    continue
                chat_id = get_chat_id_by_contact(sender_id)
                if not chat_id:
                    print(f"[УВЕДОМЛЕНИЕ] Чат для {sender_id} не найден")
                    continue
                if msg_text:
                    # Не сохраняем если этот чат сейчас открыт — poll_queue сам сохранит
                    from app.components.chat.chat_manager import get_chat_id as _gcid
                    if _gcid() != chat_id:
                        save_message_to_db(sender_id, msg_text, chat_id, msg_ts)
                increment_unread(chat_id)
                notification_bridge.fire_notification(chat_id)
        except Exception as ex:
            print(f"[УВЕДОМЛЕНИЯ] Поток завершён: {ex}")
            break


def connect_notifications(user_id, notification_room):
    global ws_notification, notification_thread
    try:
        ws_notification = websocket.WebSocket()
        ws_notification.connect(f"{WS_HOST}/ws/notifications/")
        ws_notification.send(json.dumps({"user_id": user_id, "room": notification_room}))
        ws_notification.recv()
        notification_thread = threading.Thread(target=listen_notifications, daemon=True)
        notification_thread.start()
        print(f"[УВЕДОМЛЕНИЯ] ✅ Подключен")
        return True
    except Exception as e:
        print(f"[УВЕДОМЛЕНИЯ] ❌ Ошибка: {e}")
        return False


def disconnect_notifications():
    global ws_notification
    if ws_notification:
        try:
            ws_notification.close()
        except Exception:
            pass
        ws_notification = None


def check_offline_messages():
    user_data = get_user_data()
    if not user_data:
        return
    try:
        response = requests.post(
            f"{API_HOST}/notification/v2/user/notification/",
            json={"id_users": user_data["user_id"], "token": user_data["token"]}
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"[ОФЛАЙН] {len(data)} сообщений")
                for msg in data:
                    sid = str(msg.get('id_senders', ''))
                    txt = msg.get('message', '')
                    if sid and not is_contact_blocked(sid):
                        chat_id = get_chat_id_by_contact(sid)
                        if chat_id:
                            if txt:
                                save_message_to_db(sid, txt, chat_id)
                            increment_unread(chat_id)
                            notification_bridge.fire_notification(chat_id)
    except Exception as e:
        print(f"[ОФЛАЙН] Ошибка: {e}")


def init_notifications():
    if not is_authorized:
        return
    user_data = get_user_data()
    if not user_data:
        return
    check_offline_messages()
    connect_notifications(user_data["user_id"], user_data["room"])


# ── Главная функция ───────────────────────────────────────────────────────────

def main(page: ft.Page):
    page.theme_mode = color_theme
    init_notifications()

    # Создаём main_menu ОДИН РАЗ — не пересоздаём при каждом route_change
    menu_view = main_menu(page)

    def route_change(route):
        from app.components.chat.chat_manager import get_chat_id

        # Уходим из чата → закрываем соединение
        prev = getattr(page, '_prev_route', None)
        if prev == "/chat" and page.route != "/chat":
            try:
                from app.components.chat import chat_connection as _conn
                _conn.stop_connection()
            except Exception:
                pass

        page._prev_route = page.route
        page.views.clear()

        if not is_authorized:
            page.views.append(main_sign_up(page))
            page.update()
            return

        if page.route == "/chat":
            # Сбрасываем счётчик при ВХОДЕ в чат
            _cid = get_chat_id()
            if _cid:
                reset_unread(_cid)
            page.views.append(menu_view)
            page.views.append(chat_view(page))
        elif page.route == "/settings":
            page.views.append(menu_view)
            page.views.append(settings_view(page))
        elif page.route == "/registration":
            page.views.append(main_registartion(page))
        elif page.route == "/login":
            page.views.append(main_sign_up(page))
        else:
            page.views.append(menu_view)

        page.update()

    page.on_close        = lambda e: disconnect_notifications()
    page.on_route_change = route_change
    page.go(page.route)


ft.app(main)