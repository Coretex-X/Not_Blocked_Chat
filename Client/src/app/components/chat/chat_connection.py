import json
import base64
import threading
import queue
import websocket
import sqlite3 as ql
import path
from .geniration_token import GuaranteedUniqueTokenGenerator

# ── Генерация токенов ─────────────────────────────────────────────────────────

_gen   = GuaranteedUniqueTokenGenerator()
token  = _gen.generate_token(90)
lobbi_new  = _gen.generate_token(90)

# ── Константы ─────────────────────────────────────────────────────────────────

WS_URL_DATA     = "ws://127.0.0.1:5000/ws/data/"
WS_URL_CHAT     = f"ws://127.0.0.1:5000/ws/chat_user/{token}/"
WS_URL_NEW_CHAT = f"ws://127.0.0.1:5000/ws/new_chat_user/{token}/"
FILE_SEPARATOR  = b"|||BINARY_DATA|||"

# ── Путь к БД ─────────────────────────────────────────────────────────────────

db_path = f"{path.db_path()}user_data.db"

# ── Состояние ─────────────────────────────────────────────────────────────────

message_queue: queue.Queue = queue.Queue()
ws: websocket.WebSocket | None = None
running = True
LOBBI_TIME = None


# ── Вспомогательные функции БД ────────────────────────────────────────────────

def get_room_by_contact(contact_id: str) -> str | None:
    """Ищет комнату по contact_id в таблице contacts"""
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT room FROM contacts WHERE user_id = ?", (str(contact_id),))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
        return None
    except Exception as e:
        print(f"[БД] Ошибка чтения комнаты: {e}")
        return None


def save_room_for_contact(my_id: str, contact_id: str, room: str):
    """Сохраняет или создаёт запись с комнатой в contacts для обоих пользователей"""
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            
            for uid in (str(my_id), str(contact_id)):
                cur.execute("SELECT user_id FROM contacts WHERE user_id = ?", (uid,))
                if cur.fetchone():
                    # Запись есть - обновляем комнату
                    cur.execute("UPDATE contacts SET room = ? WHERE user_id = ?", (room, uid))
                    print(f"[БД] Обновлена комната для user_id={uid}")
                else:
                    # Записи нет - создаём с комнатой
                    cur.execute(
                        "INSERT INTO contacts (user_id, room, status_user_contact) VALUES (?, ?, 'not_save_user')",
                        (uid, room)
                    )
                    print(f"[БД] Создана запись для user_id={uid} с комнатой {room}")
            
            con.commit()
            print(f"[БД] Комната {room} сохранена")
    except Exception as e:
        print(f"[БД] Ошибка сохранения комнаты: {e}")


# ── Публичный API ─────────────────────────────────────────────────────────────

def start_connection(my_id: str, contact_id: str, status_chat: str):
    """Аутентифицирует чат-комнату, открывает WS и запускает поток чтения."""
    global ws, LOBBI_TIME
    
    print(f"[ЧАТ] my_id={my_id}, contact_id={contact_id}, status_chat={status_chat}")
    
    try:
        if status_chat == 'existing_chat':
            LOBBI_TIME = get_room_by_contact(contact_id)
            if not LOBBI_TIME:
                print("[ЧАТ] ❌ Комната не найдена для контакта")
                return
            print(f"[ЧАТ] Комната из БД: {LOBBI_TIME}")
        else:
            LOBBI_TIME = lobbi_new
            save_room_for_contact(my_id, contact_id, LOBBI_TIME)
            print(f"[ЧАТ] Новая комната: {LOBBI_TIME}")
        
        _authenticate(my_id, contact_id, status_chat)
        
        ws = websocket.WebSocket()
        ws.connect(WS_URL_NEW_CHAT if status_chat == 'new_chat' else WS_URL_CHAT)
        threading.Thread(target=_receive_loop, daemon=True).start()
        print(f"[ЧАТ] ✅ Подключен к {LOBBI_TIME}")
        
    except Exception as e:
        print(f"[ЧАТ] ❌ Ошибка подключения: {e}")


def send_text(payload: dict):
    if ws:
        ws.send(json.dumps(payload))


def send_binary(data: bytes):
    if ws:
        ws.send_binary(data)


# ── Внутренние функции ────────────────────────────────────────────────────────

def _authenticate(my_id: str, contact_id: str, status_chat: str):
    if my_id == "None" and contact_id == "None":
        return
    try:
        conn = websocket.WebSocket()
        conn.connect(WS_URL_DATA)
        conn.send(json.dumps({
            "room":        LOBBI_TIME,
            "user_id":     my_id,
            "guest_id":    contact_id,
            "status_chat": status_chat,
            "token":       token,
        }))
        response = conn.recv()
        print(f"[АВТОРИЗАЦИЯ] {response}")
        conn.close()
    except Exception as e:
        print(f"[АВТОРИЗАЦИЯ] ❌ Ошибка: {e}")


def _receive_loop():
    global running
    print("[ЧАТ] Слушаю входящие сообщения...")
    while running:
        try:
            raw = ws.recv()
            if isinstance(raw, str):
                message_queue.put(json.loads(raw))
            elif isinstance(raw, bytes):
                sep = raw.find(FILE_SEPARATOR)
                if sep == -1:
                    continue
                meta  = json.loads(raw[:sep].decode("utf-8"))
                fbytes = raw[sep + len(FILE_SEPARATOR):]
                message_queue.put({
                    "type":      "file",
                    "file_name": meta.get("file_name", "unknown"),
                    "file_type": meta.get("file_type", "unknown"),
                    "file_size": meta.get("file_size", len(fbytes)),
                    "file_data": base64.b64encode(fbytes).decode("utf-8"),
                    "sender_id": meta.get("sender_id"),
                })
        except websocket.WebSocketConnectionClosedException:
            print("[ЧАТ] Соединение закрыто")
            break
        except Exception as e:
            print(f"[ЧАТ] ❌ Ошибка получения: {e}")
            break


def close():
    global running, ws
    running = False
    if ws:
        try:
            ws.close()
        except:
            pass
    print("[ЧАТ] Соединение закрыто")