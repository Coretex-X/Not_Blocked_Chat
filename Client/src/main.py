import flet as ft
import sqlite3 as ql
import path
import websocket
import json
import threading
import requests
from app import notification_bridge
from app.settings import settings_view
from app.registration import main_registartion
from app.sign_up import main_sign_up

db_path  = f"{path.db_path()}user_data.db"
WS_HOST  = "ws://127.0.0.1:5000"
API_HOST = "http://127.0.0.1:5000"

ws_notification   = None
_notif_thread     = None

# ── Инициализация БД ──────────────────────────────────────────────────────────
with ql.connect(db_path) as _con:
    _cur = _con.cursor()
    _cur.execute("""CREATE TABLE IF NOT EXISTS users_data(
        id_user INTEGER, name TEXT, profile TEXT,
        number TEXT, token TEXT, room TEXT, avatar TEXT)""")
    _cur.execute("""CREATE TABLE IF NOT EXISTS user_settings(
        authorization TEXT DEFAULT 'false',
        color_theme TEXT DEFAULT 'light',
        language TEXT DEFAULT 'ru',
        font_size TEXT DEFAULT '17')""")
    try:
        _cur.execute("ALTER TABLE user_settings ADD COLUMN font_size TEXT DEFAULT '14'")
    except ql.OperationalError:
        pass
    _con.commit()

with ql.connect(db_path) as _con:
    _cur = _con.cursor()
    _cur.execute("SELECT authorization, color_theme FROM user_settings LIMIT 1")
    _row = _cur.fetchone()
    is_authorized = (_row[0] if _row else 'false') == 'true'
    color_theme   = _row[1] if _row and _row[1] else 'dark'


# ── Утилиты БД ────────────────────────────────────────────────────────────────

def get_user_data():
    with ql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id_user, token, room FROM users_data LIMIT 1")
        row = cur.fetchone()
        return {"user_id": row[0], "token": row[1], "room": row[2]} \
            if (row and row[0] and row[1] and row[2]) else None


def is_contact_blocked(sender_id: str) -> bool:
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT is_blocked FROM contacts WHERE user_id=?", (sender_id,))
            row = cur.fetchone()
            return bool(row[0]) if row and row[0] else False
    except Exception:
        return False


def get_chat_id_by_contact(sender_id: str):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT chat_id FROM chats WHERE contact_id=?", (sender_id,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def increment_unread(chat_id: int):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE chats SET unread_count=unread_count+1 WHERE chat_id=?", (chat_id,))
            con.commit()
    except Exception as e:
        print(f"[UNREAD] {e}")


def reset_unread(chat_id: int):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE chats SET unread_count=0 WHERE chat_id=?", (chat_id,))
            con.commit()
    except Exception as e:
        print(f"[UNREAD reset] {e}")


def save_message_to_db(sender_id: str, text: str, chat_id: int, timestamp: str = None):
    import datetime
    try:
        ts = (timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))[:19]
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute(
                "SELECT id FROM messages WHERE chat_id=? AND sender_id=? AND timestamp=? LIMIT 1",
                (chat_id, sender_id, ts))
            if cur.fetchone():
                return
            cur.execute(
                "INSERT INTO messages (chat_id,sender_id,msg_type,content,is_user,one_time,timestamp)"
                " VALUES (?,?,'text',?,0,0,?)",
                (chat_id, sender_id, text, ts))
            cur.execute(
                "UPDATE chats SET last_message=?,last_message_time=? WHERE chat_id=?",
                (text[:80], ts, chat_id))
            con.commit()
        print(f"[БД] ✅ chat={chat_id}: '{text[:25]}'")
    except Exception as ex:
        print(f"[БД] ❌ {ex}")


# ── Уведомления ───────────────────────────────────────────────────────────────

def _listen_notifications():
    global ws_notification
    while True:
        try:
            raw  = ws_notification.recv()
            data = json.loads(raw)
            print(f"[УВ] {json.dumps(data, ensure_ascii=False)}")

            if data.get("type") != "new_message":
                continue

            sender_id = str(data.get("sender_id", ""))
            text      = data.get("message", "")
            ts        = data.get("timestamp", "")

            if not sender_id or not text:
                continue
            if is_contact_blocked(sender_id):
                continue

            chat_id = get_chat_id_by_contact(sender_id)
            if not chat_id:
                continue

            from app.components.chat.chat_manager import get_chat_id as _gcid
            if _gcid() != chat_id:
                # Чат не открыт — сохраняем и обновляем счётчик
                save_message_to_db(sender_id, text, chat_id, ts)
                increment_unread(chat_id)
                notification_bridge.fire_notification(chat_id)

        except Exception as ex:
            print(f"[УВ] Поток завершён: {ex}")
            break


def _connect_notifications(user_id, room):
    global ws_notification, _notif_thread
    try:
        ws_notification = websocket.WebSocket()
        ws_notification.connect(f"{WS_HOST}/ws/notifications/")
        ws_notification.send(json.dumps({"user_id": user_id, "room": room}))
        ws_notification.recv()
        _notif_thread = threading.Thread(target=_listen_notifications, daemon=True)
        _notif_thread.start()
        print("[УВ] ✅ Подключен")
    except Exception as e:
        print(f"[УВ] ❌ {e}")


def _disconnect_notifications():
    global ws_notification
    if ws_notification:
        try: ws_notification.close()
        except Exception: pass
        ws_notification = None


def _check_offline():
    ud = get_user_data()
    if not ud:
        return
    try:
        r = requests.post(f"{API_HOST}/notification/v2/user/notification/",
                          json={"id_users": ud["user_id"], "token": ud["token"]})
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for msg in data:
                    sid = str(msg.get('id_senders', ''))
                    txt = msg.get('message', '')
                    ts  = msg.get('timestamp', '')
                    if sid and txt and not is_contact_blocked(sid):
                        cid = get_chat_id_by_contact(sid)
                        if cid:
                            save_message_to_db(sid, txt, cid, ts)
                            increment_unread(cid)
    except Exception as e:
        print(f"[ОФЛАЙН] {e}")


def _init_notifications():
    if not is_authorized:
        return
    ud = get_user_data()
    if not ud:
        return
    _check_offline()
    _connect_notifications(ud["user_id"], ud["room"])


# ── Главная функция ───────────────────────────────────────────────────────────

def main(page: ft.Page):
    page.theme_mode = color_theme
    _init_notifications()

    from app.menu import main_menu
    menu_view = main_menu(page)

    _current_chat_view = [None]
    _route_lock = threading.Lock()  # блокировка от двойного вызова route_change

    def route_change(route):
        # Если route_change уже выполняется — пропускаем
        if not _route_lock.acquire(blocking=False):
            return
        try:
            _route_change_impl(route)
        finally:
            _route_lock.release()

    def _route_change_impl(route):
        from app.components.chat.chat_manager import get_chat_id
        from app.components.chat import chat_connection as _conn

        prev = getattr(page, '_prev_route', None)
        cur  = page.route

        # Уходим из чата → закрываем соединение
        if prev == "/chat" and cur != "/chat":
            _conn.stop_connection()
            _current_chat_view[0] = None  # сбрасываем кеш

        page._prev_route = cur
        page.views.clear()

        if not is_authorized:
            page.views.append(main_sign_up(page))
            page.update()
            return

        if cur == "/chat":
            # Сбрасываем счётчик непрочитанных
            _cid = get_chat_id()
            if _cid:
                reset_unread(_cid)
            # Создаём chat_view ТОЛЬКО если его ещё нет
            if _current_chat_view[0] is None:
                from app.chat import chat_view
                _current_chat_view[0] = chat_view(page)
            page.views.append(menu_view)
            page.views.append(_current_chat_view[0])
        elif cur == "/settings":
            page.views.append(menu_view)
            page.views.append(settings_view(page))
        elif cur == "/registration":
            page.views.append(main_registartion(page))
        elif cur == "/login":
            page.views.append(main_sign_up(page))
        else:
            page.views.append(menu_view)

        page.update()

    page.on_close        = lambda e: _disconnect_notifications()
    page.on_route_change = route_change
    page.go(page.route)


ft.app(main)