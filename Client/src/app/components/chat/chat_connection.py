import json
import base64
import threading
import queue
import websocket
import sqlite3 as ql
import path
from .geniration_token import GuaranteedUniqueTokenGenerator

_gen = GuaranteedUniqueTokenGenerator()

WS_URL_DATA     = "ws://127.0.0.1:5000/ws/data/"
WS_URL_CHAT     = "ws://127.0.0.1:5000/ws/chat_user/{}/"
WS_URL_NEW_CHAT = "ws://127.0.0.1:5000/ws/new_chat_user/{}/"
FILE_SEPARATOR  = b"|||BINARY_DATA|||"

db_path = f"{path.db_path()}user_data.db"

message_queue: queue.Queue = queue.Queue()
ws          = None
running     = False
_stop_event = threading.Event()
LOBBI_TIME  = None


def get_room_by_contact(contact_id: str) -> str | None:
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT room FROM contacts WHERE user_id=?", (str(contact_id),))
            row = cur.fetchone()
            return row[0] if row and row[0] else None
    except Exception as e:
        print(f"[ЧАТ] Ошибка чтения комнаты: {e}")
        return None


def save_room_for_contact(my_id: str, contact_id: str, room: str):
    try:
        with ql.connect(db_path) as con:
            cur = con.cursor()
            for uid in (str(my_id), str(contact_id)):
                cur.execute("SELECT user_id FROM contacts WHERE user_id=?", (uid,))
                if cur.fetchone():
                    cur.execute("UPDATE contacts SET room=? WHERE user_id=?", (room, uid))
                else:
                    cur.execute(
                        "INSERT INTO contacts (user_id, room, status_user_contact) VALUES (?,?,'not_save_user')",
                        (uid, room))
            con.commit()
    except Exception as e:
        print(f"[ЧАТ] Ошибка сохранения комнаты: {e}")


_connect_lock = threading.Lock()


def start_connection(my_id: str, contact_id: str, status_chat: str):
    global ws, LOBBI_TIME, running, _stop_event

    # Блокировка от двойного вызова
    if not _connect_lock.acquire(blocking=False):
        print("[ЧАТ] start_connection уже выполняется, пропускаем")
        return

    try:
        # Если уже подключены к этой же комнате — не переподключаемся
        if running and ws:
            expected = get_room_by_contact(contact_id) if status_chat == 'existing_chat' else None
            if expected and expected == LOBBI_TIME:
                print(f"[ЧАТ] Уже подключен к {LOBBI_TIME}, пропускаем")
                return

        stop_connection()

        print(f"[ЧАТ] my_id={my_id}, contact_id={contact_id}, status_chat={status_chat}")

        new_token = _gen.generate_token(90)

        if status_chat == 'existing_chat':
            LOBBI_TIME = get_room_by_contact(contact_id)
            if not LOBBI_TIME:
                print("[ЧАТ] ❌ Комната не найдена")
                return
        else:
            LOBBI_TIME = _gen.generate_token(90)
            save_room_for_contact(my_id, contact_id, LOBBI_TIME)

        print(f"[ЧАТ] Комната: {LOBBI_TIME}")

        _authenticate(my_id, contact_id, status_chat, new_token)

        ws_url = (WS_URL_NEW_CHAT if status_chat == 'new_chat' else WS_URL_CHAT).format(new_token)
        ws = websocket.WebSocket()
        ws.connect(ws_url)

        _stop_event.clear()
        running = True
        threading.Thread(target=_receive_loop, daemon=True).start()
        print(f"[ЧАТ] ✅ Подключен к {LOBBI_TIME}")

    except Exception as e:
        print(f"[ЧАТ] ❌ Ошибка: {e}")
    finally:
        _connect_lock.release()


def stop_connection():
    global ws, running
    running = False
    _stop_event.set()
    if ws:
        try:
            ws.close()
        except Exception:
            pass
        ws = None
    # Очищаем очередь чтобы старые сообщения не появились при следующем входе
    while not message_queue.empty():
        try:
            message_queue.get_nowait()
        except queue.Empty:
            break
    print("[ЧАТ] Соединение закрыто")


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
            print(f"[ЧАТ] Ошибка отправки файла: {e}")


def _authenticate(my_id: str, contact_id: str, status_chat: str, token: str):
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
        print(f"[АВТОРИЗАЦИЯ] ❌ {e}")


def _receive_loop():
    global running
    print("[ЧАТ] Слушаю входящие...")
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
                    "type":          "file",
                    "file_name":     meta.get("file_name", "unknown"),
                    "file_type":     meta.get("file_type", "unknown"),
                    "file_size":     meta.get("file_size", len(fbytes)),
                    "file_data":     base64.b64encode(fbytes).decode("utf-8"),
                    "sender_id":     meta.get("sender_id"),
                    "one_time_view": meta.get("one_time_view", False),
                })
        except websocket.WebSocketConnectionClosedException:
            print("[ЧАТ] Соединение закрыто сервером")
            break
        except Exception as e:
            if not _stop_event.is_set():
                print(f"[ЧАТ] ❌ Ошибка получения: {e}")
            break
    running = False