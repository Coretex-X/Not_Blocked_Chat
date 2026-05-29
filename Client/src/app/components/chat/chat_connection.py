import json
import base64
import threading
import queue
import websocket
import sqlite3 as ql
import path
from .geniration_token import GuaranteedUniqueTokenGenerator

# ── Генерация токенов ─────────────────────────────────────────────────────────

_gen       = GuaranteedUniqueTokenGenerator()
token      = _gen.generate_token(90)
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
running   = False   # FIX: не запускаем receive_loop пока не подключились
LOBBI_TIME = None
_stop_event = threading.Event()


# ── Вспомогательные функции БД ────────────────────────────────────────────────

def get_room_by_contact(contact_id: str) -> str | None:
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
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            for uid in (str(my_id), str(contact_id)):
                cur.execute("SELECT user_id FROM contacts WHERE user_id = ?", (uid,))
                if cur.fetchone():
                    cur.execute("UPDATE contacts SET room = ? WHERE user_id = ?", (room, uid))
                else:
                    cur.execute(
                        "INSERT INTO contacts (user_id, room, status_user_contact) VALUES (?, ?, 'not_save_user')",
                        (uid, room)
                    )
            con.commit()
            print(f"[БД] Комната {room} сохранена")
    except Exception as e:
        print(f"[БД] Ошибка сохранения комнаты: {e}")


# ── Публичный API ─────────────────────────────────────────────────────────────

def start_connection(my_id: str, contact_id: str, status_chat: str):
    """Закрывает предыдущее соединение, аутентифицирует и открывает новое."""
    global ws, LOBBI_TIME, running, _stop_event

    # Защита от двойного вызова: если уже подключены к той же комнате — пропускаем
    if running and ws and LOBBI_TIME:
        expected_room = get_room_by_contact(contact_id) if status_chat == 'existing_chat' else None
        if expected_room and expected_room == LOBBI_TIME:
            print(f"[ЧАТ] Уже подключен к {LOBBI_TIME}, пропускаем")
            return

    stop_connection()

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

        # Сбрасываем stop_event и запускаем receive_loop
        _stop_event.clear()
        running = True
        threading.Thread(target=_receive_loop, daemon=True).start()
        print(f"[ЧАТ] ✅ Подключен к {LOBBI_TIME}")

    except Exception as e:
        print(f"[ЧАТ] ❌ Ошибка подключения: {e}")


def stop_connection():
    """FIX 1: Корректно закрывает WebSocket соединение при выходе из чата."""
    global ws, running
    running = False
    _stop_event.set()
    if ws:
        try:
            ws.close()
        except Exception:
            pass
        ws = None
    print("[ЧАТ] Соединение закрыто")

    # FIX 4: очищаем очередь сообщений чтобы старые сообщения не дублировались
    # при следующем входе в чат
    while not message_queue.empty():
        try:
            message_queue.get_nowait()
        except queue.Empty:
            break


def send_text(payload: dict):
    if ws:
        try:
            ws.send(json.dumps(payload))
        except Exception as e:
            print(f"[ЧАТ] Ошибка отправки: {e}")


def send_binary(data: bytes):
    if ws:
        try:
            ws.send_binary(data)
        except Exception as e:
            print(f"[ЧАТ] Ошибка отправки бинарных данных: {e}")


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
    while running and not _stop_event.is_set():
        try:
            raw = ws.recv()
            if _stop_event.is_set():
                break
            if isinstance(raw, str):
                message_queue.put(json.loads(raw))
            elif isinstance(raw, bytes):
                sep = raw.find(FILE_SEPARATOR)
                if sep == -1:
                    continue
                meta   = json.loads(raw[:sep].decode("utf-8"))
                fbytes = raw[sep + len(FILE_SEPARATOR):]
                message_queue.put({
                    "type":      "file",
                    "file_name": meta.get("file_name", "unknown"),
                    "file_type": meta.get("file_type", "unknown"),
                    "file_size": meta.get("file_size", len(fbytes)),
                    "file_data": base64.b64encode(fbytes).decode("utf-8"),
                    "sender_id": meta.get("sender_id"),
                    "one_time_view": meta.get("one_time_view", False),
                })
        except websocket.WebSocketConnectionClosedException:
            print("[ЧАТ] Соединение закрыто")
            break
        except Exception as e:
            if not _stop_event.is_set():
                print(f"[ЧАТ] ❌ Ошибка получения: {e}")
            break


def close():
    """Алиас для обратной совместимости."""
    stop_connection()