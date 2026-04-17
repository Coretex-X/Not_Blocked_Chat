import json
import base64
import threading
import queue
import websocket
from .geniration_token import GuaranteedUniqueTokenGenerator

# ── Генерация токенов ─────────────────────────────────────────────────────────

_gen   = GuaranteedUniqueTokenGenerator()
token  = _gen.generate_token(90)
lobbi  = _gen.generate_token(90)

# ── Константы ─────────────────────────────────────────────────────────────────

WS_URL_DATA     = "ws://127.0.0.1:5000/ws/data/"
WS_URL_CHAT     = f"ws://127.0.0.1:5000/ws/chat_user/{token}/"
WS_URL_NEW_CHAT = f"ws://127.0.0.1:5000/ws/new_chat_user/{token}/"
FILE_SEPARATOR  = b"|||BINARY_DATA|||"
LOBBI_TIME      = "lobbi"

# ── Состояние ─────────────────────────────────────────────────────────────────

message_queue: queue.Queue = queue.Queue()
ws: websocket.WebSocket | None = None
running = True


# ── Публичный API ─────────────────────────────────────────────────────────────

def start_connection(my_id: str, contact_id: str, status_chat: str):
    """Аутентифицирует чат-комнату, открывает WS и запускает поток чтения."""
    global ws
    try:
        _authenticate(my_id, contact_id, status_chat)
        ws = websocket.WebSocket()
        ws.connect(WS_URL_NEW_CHAT if status_chat == 'new_chat' else WS_URL_CHAT)
        threading.Thread(target=_receive_loop, daemon=True).start()
    except Exception:
        pass


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
            "room":        LOBBI_TIME if status_chat == 'existing_chat' else lobbi,
            "user_id":     my_id,
            "guest_id":    contact_id,
            "status_chat": status_chat,
            "token":       token,
        }))
        conn.close()
    except Exception:
        pass


def _receive_loop():
    global running
    while running:
        try:
            raw = ws.recv()
            if isinstance(raw, str):
                message_queue.put(json.loads(raw))
            elif isinstance(raw, bytes):
                sep = raw.find(FILE_SEPARATOR)
                if sep == -1:
                    print("❌ Разделитель не найден в бинарных данных")
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
            print("❌ WebSocket соединение закрыто")
            break
        except Exception as e:
            print(f"❌ Ошибка получения: {e}")
            break
