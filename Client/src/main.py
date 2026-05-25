import flet as ft
import sqlite3 as ql
import path
import websocket
import json
import threading
from app.menu import main_menu
from app.settings import settings_view
from app.registration import main_registartion
from app.sign_up import main_sign_up
from app.chat import chat_view

db_path = f"{path.db_path()}user_data.db"

WS_HOST = "ws://127.0.0.1:5000"

ws_notification = None
notification_thread = None
notification_messages = []

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_data(
            id_user INTEGER,
            name TEXT,
            profile TEXT,
            number TEXT,
            token TEXT,
            room TEXT,
            avatar TEXT)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings(
            authorization TEXT DEFAULT 'false',
            color_theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'ru',
            font_size TEXT DEFAULT '17'
        )
    """)
    try:
        cur.execute("ALTER TABLE user_settings ADD COLUMN font_size TEXT DEFAULT '14'")
    except ql.OperationalError:
        pass
    con.commit()

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("SELECT authorization, color_theme, font_size FROM user_settings LIMIT 1")
    row = cur.fetchone()
    is_authorized = (row[0] if row else 'false') == 'true'
    start_theme = row[1] if row and row[1] else 'dark'
    start_font = int(row[2]) if row and row[2] else 14

with ql.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("SELECT color_theme FROM user_settings LIMIT 1")
    row = cur.fetchone()
    color_theme = row[0] if row else "dark"


def get_user_data():
    with ql.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT id_user, token, room FROM users_data LIMIT 1")
        row = cur.fetchone()
        if row and row[0] and row[1] and row[2]:
            return {"user_id": row[0], "token": row[1], "room": row[2]}
        return None


def connect_notifications(user_id, notification_room):
    global ws_notification, notification_thread
    
    try:
        ws_notification = websocket.WebSocket()
        ws_notification.connect(f"{WS_HOST}/ws/notifications/")
        ws_notification.send(json.dumps({
            "user_id": user_id,
            "room": notification_room
        }))
        
        ws_notification.recv()
        
        notification_thread = threading.Thread(target=listen_notifications, daemon=True)
        notification_thread.start()
        return True
    except Exception as e:
        print(f"[УВЕДОМЛЕНИЯ] Ошибка подключения: {e}")
        return False


def listen_notifications():
    global ws_notification, notification_messages
    
    while True:
        try:
            message = ws_notification.recv()
            data = json.loads(message)
            notification_messages.append(data)
            print(f"[УВЕДОМЛЕНИЕ] {json.dumps(data, ensure_ascii=False)}")
        except:
            break


def disconnect_notifications():
    global ws_notification
    if ws_notification:
        try:
            ws_notification.close()
        except:
            pass
        ws_notification = None


def init_notifications():
    if not is_authorized:
        return
    
    user_data = get_user_data()
    if not user_data:
        return
    
    connect_notifications(user_data["user_id"], user_data["room"])


def main(page: ft.Page):
    page.theme_mode = color_theme
    
    init_notifications()
    
    def route_change(route):
        page.views.clear()
        page.views.append(main_menu(page))

        if not is_authorized:
            page.views.append(main_sign_up(page))

        if page.route == "/main":
            page.views.append(main_menu(page))
        elif page.route == "/settings":
            page.views.append(settings_view(page))
        elif page.route == "/registration":
            page.views.append(main_registartion(page))
        elif page.route == "/login":
            page.views.append(main_sign_up(page))
        elif page.route == "/chat":
            page.views.append(chat_view(page))

        page.update()
    
    def on_close(e):
        disconnect_notifications()
    
    page.on_close = on_close
    page.on_route_change = route_change
    page.go(page.route)


ft.app(main)