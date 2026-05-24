import asyncio
import websockets
import json
import requests
'''
x = '".rSSm9.v$d$kZ6f'

# ===== НАСТРОЙКИ (МЕНЯЙ ТОЛЬКО ЗДЕСЬ) =====
USER_ID = 2                          # Твой ID
TOKEN = f"llifbkdogcoggjeefpjleplhmbjfcgninamakplhdklnhfijkobmofheaghagded4|%4q_*_wJ4wG'L`>;X9{x}"                 # Твой токен из sign_up_models
ROOM_CHAT = "lobbi1"                # Комната чата
GUEST_ID = 1                         # ID собеседника
STATUS_CHAT = "existing_chat"        # "new_chat" или "existing_chat"
NOTIFICATION_ROOM = "ciwYBfMXR3qLTicFMkbUQoySuS1XXE2aIJAImWEM0I2ZwYch0WqXDZpRBzKMPLjUeV2MREPYaT0x7c3UxDaIUW88jDZut48TxrMJRcL9LKDKUw"   # Твоя личная комната для уведомлений

# ===== URL (НЕ ТРОГАЙ) =====
HOST = "ws://127.0.0.1:5000"
WS_NOTIF = f"{HOST}/ws/notifications/"
WS_DATA = f"{HOST}/ws/data/"
API_OFFLINE = "http://127.0.0.1:5000/notification/v2/user/notification/"

CHAT_TOKEN = f"token_{USER_ID}_{ROOM_CHAT}"

if STATUS_CHAT == "new_chat":
    WS_CHAT = f"{HOST}/ws/new_chat_user/{CHAT_TOKEN}/"
else:
    WS_CHAT = f"{HOST}/ws/chat_user/{CHAT_TOKEN}/"


class ChatClient:
    def __init__(self):
        self.ws_notif = None
        self.ws_chat = None
        self.in_chat = False
        self.running = True
        
    async def connect_notifications(self):
        """Подключаем уведомления и слушаем их вечно"""
        try:
            self.ws_notif = await websockets.connect(WS_NOTIF)
            await self.ws_notif.send(json.dumps({
                "user_id": USER_ID,
                "room": NOTIFICATION_ROOM
            }))
            response = await self.ws_notif.recv()
            print(f"[УВЕДОМЛЕНИЯ] Подключены: {response}")
            
            # Слушаем уведомления в фоне
            asyncio.create_task(self.listen_notifications())
        except Exception as e:
            print(f"[ОШИБКА] Уведомления: {e}")
    
    async def listen_notifications(self):
        """Слушает входящие уведомления"""
        try:
            async for msg in self.ws_notif:
                data = json.loads(msg)
                if data.get("type") == "new_message":
                    print("\n" + '"' * 40)
                    print(f'  Новая сообшение: User {data["sender_id"]}')
                    print(f'  Комната: {data["room"]}')
                    print(f'  Сообщение: {data["message"]}')
                    print('"' * 40)
                    print(">>> ", end="", flush=True)
        except:
            pass
    
    async def connect_chat(self):
        """Подключаемся к чату"""
        # Авторизация
        async with websockets.connect(WS_DATA) as ws_data:
            await ws_data.send(json.dumps({
                "room": ROOM_CHAT,
                "user_id": USER_ID,
                "guest_id": GUEST_ID,
                "status_chat": STATUS_CHAT,
                "token": CHAT_TOKEN
            }))
            auth_resp = await ws_data.recv()
        
        # Подключаемся к чату
        self.ws_chat = await websockets.connect(WS_CHAT)
        self.in_chat = True
        print(f"[ЧАТ] Подключен к {ROOM_CHAT}")
        
        # Слушаем сообщения чата
        asyncio.create_task(self.listen_chat())
    
    async def listen_chat(self):
        """Слушает сообщения из чата"""
        try:
            async for msg in self.ws_chat:
                data = json.loads(msg)
                if data.get("type") == "message":
                    print("\n" + '"' * 40)
                    print(f'  Новая сообшение: User {data["sender_id"]}')
                    print(f'  Сообщение: {data["message"]}')
                    print('"' * 40)
                    print(">>> ", end="", flush=True)
        except:
            self.in_chat = False
            print("\n[ЧАТ] Отключен")
    
    async def disconnect_chat(self):
        """Отключаемся от чата"""
        if self.ws_chat:
            await self.ws_chat.close()
            self.ws_chat = None
            self.in_chat = False
            print("[ЧАТ] Вышел из чата")
    
    async def send_message(self, text):
        """Отправляет сообщение"""
        if self.in_chat and self.ws_chat:
            await self.ws_chat.send(json.dumps({"message": text}))
        else:
            print("[ОШИБКА] Не в чате!")
    
    async def check_offline(self):
        """Проверяет офлайн-сообщения"""
        try:
            r = requests.post(API_OFFLINE, json={
                "id_users": USER_ID,
                "token": TOKEN
            })
            data = r.json()
            if isinstance(data, list):
                print(f"\n📬 [ОФЛАЙН] Получено {len(data)} сообщений:")
                for msg in data:
                    print('"' * 40)
                    print(f'  Новая сообшение: User {msg["id_senders"]}')
                    print(f'  Комната: {msg["room"]}')
                    print(f'  Сообщение: {msg["message"]}')
                    print('"' * 40)
            elif isinstance(data, dict) and data.get("message") == "no message":
                print("\n📭 [ОФЛАЙН] Нет сообщений")
        except Exception as e:
            print(f"\n[ОШИБКА] {e}")
    
    async def close(self):
        """Закрывает всё"""
        self.running = False
        if self.ws_chat:
            await self.ws_chat.close()
        if self.ws_notif:
            await self.ws_notif.close()


async def main():
    client = ChatClient()
    
    print("=" * 50)
    print(f"  ЧАТ-КЛИЕНТ | User {USER_ID}")
    print(f"  Чат: {ROOM_CHAT} | Собеседник: User {GUEST_ID}")
    print("=" * 50)
    
    # Подключаем уведомления
    await client.connect_notifications()
    
    # Проверяем офлайн
    await client.check_offline()
    
    print("\nКоманды:")
    print("  chat   - войти в чат")
    print("  leave  - выйти из чата")
    print("  check  - проверить офлайн-сообщения")
    print("  exit   - выход")
    print("  (любой текст отправляется в чат)\n")
    
    while client.running:
        text = await asyncio.get_event_loop().run_in_executor(None, input, ">>> ")
        text = text.strip()
        
        if text == "exit":
            await client.close()
            break
        elif text == "chat":
            if client.in_chat:
                print("[ОШИБКА] Ты уже в чате!")
            else:
                await client.connect_chat()
        elif text == "leave":
            if client.in_chat:
                await client.disconnect_chat()
            else:
                print("[ОШИБКА] Ты не в чате!")
        elif text == "check":
            await client.check_offline()
        elif text:
            if client.in_chat:
                await client.send_message(text)
            else:
                print("[ОШИБКА] Сначала войди в чат (команда chat)")

asyncio.run(main())'''

'''import websocket
import json

# ===== НАСТРОЙКИ =====
USER_ID = 2
NOTIFICATION_ROOM = "ciwYBfMXR3qLTicFMkbUQoySuS1XXE2aIJAImWEM0I2ZwYch0WqXDZpRBzKMPLjUeV2MREPYaT0x7c3UxDaIUW88jDZut48TxrMJRcL9LKDKUw"

WS_HOST = "ws://127.0.0.1:5000"

# ===== ПОДКЛЮЧЕНИЕ =====
ws_notif = websocket.WebSocket()
ws_notif.connect(f"{WS_HOST}/ws/notifications/")
ws_notif.send(json.dumps({
    "user_id": USER_ID,
    "room": NOTIFICATION_ROOM
}))

response = ws_notif.recv()
print(f"Подключено: {response}")
print("Ожидание уведомлений...\n")

# ===== СЛУШАЕМ =====
while True:
    try:
        message = ws_notif.recv()
        print(message)
    except Exception as e:
        print(f"Ошибка: {e}")
        break

ws_notif.close()'''


import websocket
import json
import threading
import queue

# ===== НАСТРОЙКИ =====
USER_ID = 1
NOTIFICATION_ROOM = "XVrYLQc7gdiSX4IVmSPlPGr2XU7WntzWA25gxqjMyFwVQWhtquLhItcWR9C94D8ylRjJBJH21GTDzPPN1dzhABq7Q94j8sf95HNzUf7qgleI0t"
ROOM_CHAT = "lobbi1"
GUEST_ID = 2
STATUS_CHAT = "existing_chat"
CHAT_TOKEN = "api87"

WS_HOST = "ws://127.0.0.1:5000"

# Очередь для сообщений чата
message_queue = queue.Queue()

# ===== 1. ПОДКЛЮЧЕНИЕ УВЕДОМЛЕНИЙ (автоматически) =====
ws_notif = websocket.WebSocket()
ws_notif.connect(f"{WS_HOST}/ws/notifications/")
ws_notif.send(json.dumps({
    "user_id": USER_ID,
    "room": NOTIFICATION_ROOM
}))

response = ws_notif.recv()
print(f"[УВЕДОМЛЕНИЯ] Подключено: {response}")


def receive_notifications():
    while True:
        try:
            message = ws_notif.recv()
            print(message)
        except Exception as e:
            print(f"[УВЕДОМЛЕНИЯ] Ошибка: {e}")
            break


notif_thread = threading.Thread(target=receive_notifications, daemon=True)
notif_thread.start()

# ===== 2. АУТЕНТИФИКАЦИЯ ЧАТА =====
ws_auth = websocket.WebSocket()
ws_auth.connect(f"{WS_HOST}/ws/data/")
ws_auth.send(json.dumps({
    "room": ROOM_CHAT,
    "user_id": USER_ID,
    "guest_id": GUEST_ID,
    "status_chat": STATUS_CHAT,
    "token": CHAT_TOKEN
}))
auth_response = ws_auth.recv()
print(f"[АВТОРИЗАЦИЯ] {auth_response}")
ws_auth.close()

# ===== 3. ПОДКЛЮЧЕНИЕ К ЧАТУ =====
ws_chat = websocket.WebSocket()
if STATUS_CHAT == "new_chat":
    ws_chat.connect(f"{WS_HOST}/ws/new_chat_user/{CHAT_TOKEN}/")
else:
    ws_chat.connect(f"{WS_HOST}/ws/chat_user/{CHAT_TOKEN}/")
print(f"[ЧАТ] Подключен к {ROOM_CHAT}")


def receive_chat():
    while True:
        try:
            message = ws_chat.recv()
            print(message)
            message_queue.put(message)
        except Exception as e:
            print(f"[ЧАТ] Отключен: {e}")
            break


chat_thread = threading.Thread(target=receive_chat, daemon=True)
chat_thread.start()

# ===== 4. ОСНОВНОЙ ЦИКЛ =====
while True:
    message = input()
    if message == "exit":
        break
    ws_chat.send(json.dumps({"message": message}))

ws_chat.close()
ws_notif.close()