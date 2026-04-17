"""
chat_connection.py — WebSocket-соединение и приём сообщений
"""

import json
import base64
import threading
import queue
import websocket
from .geniration_token import GuaranteedUniqueTokenGenerator

# ─────────────────────────── Генирация Токена и Комнаты ───────────────────────

geniration = GuaranteedUniqueTokenGenerator()
token = geniration.generate_token(90)
#token = '65'
lobbi = geniration.generate_token(90)

# ─────────────────────────── Константы ────────────────────────────────────────

WS_URL_DATA    = "ws://127.0.0.1:5000/ws/data/"
WS_URL_CHAT    = f"ws://127.0.0.1:5000/ws/chat_user/{token}/"
WS_URL_NEW_CHAT    = f"ws://127.0.0.1:5000/ws/new_chat_user/{token}/"
FILE_SEPARATOR = b"|||BINARY_DATA|||"
lobbi_time = "lobbi"

# ─────────────────────────── Состояние соединения ─────────────────────────────

message_queue: queue.Queue = queue.Queue()
ws: websocket.WebSocket | None = None
running = True


def authenticate(my_id: str, contact_id: str, status_chat: str):
    """Регистрирует чат-комнату на сервере."""
    try:
        if my_id == "None" and contact_id == "None":
            print("Данных нет")
        else:
            conn = websocket.WebSocket()
            conn.connect(WS_URL_DATA)
            conn.send(json.dumps({
                "room":lobbi_time if status_chat == 'existing_chat' else lobbi,
                "user_id":my_id,
                "guest_id":contact_id,
                "status_chat":status_chat,
                "token": token,
            }))
            conn.close()
    except Exception:
        pass


def receive_messages():
    """Фоновый поток: читает сообщения из WebSocket и кладёт в очередь."""
    global running
    while running:
        try:
            raw = ws.recv()

            # Текстовые данные — JSON-сообщение
            if isinstance(raw, str):
                message_queue.put(json.loads(raw))

            # Бинарные данные — файл: метаданные + разделитель + байты файла
            elif isinstance(raw, bytes):
                sep_pos = raw.find(FILE_SEPARATOR)
                if sep_pos == -1:
                    print("❌ Не найден разделитель в бинарных данных")
                    continue
                metadata   = json.loads(raw[:sep_pos].decode("utf-8"))
                file_bytes = raw[sep_pos + len(FILE_SEPARATOR):]
                message_queue.put({
                    "type":      "file",
                    "file_name": metadata.get("file_name", "unknown"),
                    "file_type": metadata.get("file_type", "unknown"),
                    "file_size": metadata.get("file_size", len(file_bytes)),
                    "file_data": base64.b64encode(file_bytes).decode("utf-8"),
                    "sender_id": metadata.get("sender_id"),
                })
        except websocket.WebSocketConnectionClosedException:
            print("❌ WebSocket соединение закрыто")
            break
        except Exception as e:
            import traceback
            print(f"❌ Ошибка получения сообщения: {e}")
            traceback.print_exc()
            break


def start_connection(my_id: str, contact_id: str, status_chat: str):
    """Инициализирует аутентификацию, открывает WS и запускает фоновый поток."""
    global ws
    try:
        authenticate(my_id, contact_id, status_chat)
        ws = websocket.WebSocket()
        if status_chat == 'new_chat':
            ws.connect(WS_URL_NEW_CHAT)
        else:
            ws.connect(WS_URL_CHAT)
        threading.Thread(target=receive_messages, daemon=True).start()
        #print(f"Соединение установлено (симуляция)")
    except Exception:
        pass


def send_text(payload: dict):
    """Отправляет JSON-сообщение через WebSocket."""
    if ws:
        ws.send(json.dumps(payload))


def send_binary(data: bytes):
    """Отправляет бинарные данные через WebSocket."""
    if ws:
        ws.send_binary(data)
