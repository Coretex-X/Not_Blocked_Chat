# test_client.py
import asyncio
import websockets
import json
import requests
from datetime import datetime

# ============================================================
# ГЛОБАЛЬНЫЕ НАСТРОЙКИ - МЕНЯЙ ТОЛЬКО ЗДЕСЬ
# ============================================================

# ID пользователя и его токен
MY_USER_ID = 2
MY_TOKEN = "ciwYBfMXR3qLTicFMkbUQoySuS1XXE2aIJAImWEM0I2ZwYch0WqXDZpRBzKMPLjUeV2MREPYaT0x7c3UxDaIUW88jDZut48TxrMJRcL9LKDKUw"

# Мои комнаты чатов
MY_CHATS = ["lobbi_1", "lobbi_2", "lobbi_3"]

# С кем я общаюсь в каждой комнате (guest_id)
GUEST_IDS = {
    "lobbi_1": 2,
    "lobbi1": 1,
    "lobbi_3": 4,
}

# URL-ы сервера
BASE_URL = "http://127.0.0.1:5000"
WS_HOST = "127.0.0.1"
WS_PORT = 8000

# Имя пользователя (для красивого вывода)
MY_NAME = "Я"

# ============================================================
# URL-ы (не трогай, формируются автоматически)
# ============================================================

WS_DATA_URL = f"ws://{WS_HOST}:{WS_PORT}/ws/data/"
WS_CHAT_URL = f"ws://{WS_HOST}:{WS_PORT}/ws/chat_user"
WS_NEW_CHAT_URL = f"ws://{WS_HOST}:{WS_PORT}/ws/new_chat_user"
WS_NOTIFICATION_URL = f"ws://{WS_HOST}:{WS_PORT}/ws/notifications/"
NOTIFICATION_API = f"{BASE_URL}/notification/v2/user/notification/"

# ============================================================
# КОД КЛИЕНТА
# ============================================================

class ChatClient:
    def __init__(self, user_id, token, name, chats, guest_ids):
        self.user_id = user_id
        self.token = token
        self.name = name
        self.chats = chats
        self.guest_ids = guest_ids
        self.current_room = None
        self.ws_chat = None
        self.ws_notification = None
        self.notification_messages = []
        
    def log(self, message, msg_type="INFO"):
        colors = {
            "INFO": "\033[94m",
            "SEND": "\033[92m",
            "RECV": "\033[93m",
            "NOTIF": "\033[96m",
            "ERROR": "\033[91m",
            "SYSTEM": "\033[95m",
            "DEBUG": "\033[90m",
        }
        reset = "\033[0m"
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = colors.get(msg_type, "")
        print(f"{color}[{timestamp}] [{self.name}] {message}{reset}")
    
    async def connect_notification(self):
        """Подключается к WebSocket уведомлений"""
        try:
            self.ws_notification = await websockets.connect(WS_NOTIFICATION_URL)
            
            # Отправляем user_id и первую комнату
            first_room = self.chats[0] if self.chats else "lobbi_1"
            connect_data = {
                "user_id": self.user_id,
                "room": first_room
            }
            await self.ws_notification.send(json.dumps(connect_data))
            
            response = await self.ws_notification.recv()
            data = json.loads(response)
            if data.get("type") == "connected":
                self.log(f"✅ Уведомления подключены (комната: {first_room})", "SYSTEM")
            else:
                self.log(f"Ошибка: {data.get('message', 'Неизвестная ошибка')}", "ERROR")
                return False
            
            asyncio.create_task(self.listen_notifications())
            return True
            
        except Exception as e:
            self.log(f"Ошибка подключения уведомлений: {e}", "ERROR")
            return False
    
    async def listen_notifications(self):
        """Слушает уведомления"""
        try:
            async for message in self.ws_notification:
                data = json.loads(message)
                if data.get("type") == "new_message":
                    msg = f"🔔 Новое сообщение в {data['room']} от User {data['sender_id']}: {data['message']}"
                    self.log(msg, "NOTIF")
                    self.notification_messages.append(data)
        except websockets.exceptions.ConnectionClosed:
            self.log("Соединение уведомлений закрыто", "ERROR")
        except Exception as e:
            self.log(f"Ошибка уведомлений: {e}", "ERROR")
    
    async def check_offline_messages(self):
        """Проверяет офлайн-сообщения"""
        try:
            response = requests.post(NOTIFICATION_API, json={
                "id_users": self.user_id,
                "token": self.token
            })
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log(f"📬 Получено {len(data)} офлайн-сообщений", "SYSTEM")
                    for msg in data:
                        self.log(f"  От User {msg['id_senders']} в {msg['room']}: {msg['message']}", "NOTIF")
                elif isinstance(data, dict) and data.get("message") == "no message":
                    self.log("📭 Нет офлайн-сообщений", "SYSTEM")
        except Exception as e:
            self.log(f"Ошибка проверки офлайн-сообщений: {e}", "ERROR")
    
    async def connect_chat(self, room_name, is_new=False):
        """Подключается к чату"""
        token = f"token_{self.user_id}_{room_name}_{datetime.now().timestamp()}"
        guest_id = self.guest_ids.get(room_name, 0)
        
        # Авторизация через DataConsumer
        try:
            async with websockets.connect(WS_DATA_URL) as ws_data:
                auth_data = {
                    "room": room_name,
                    "user_id": self.user_id,
                    "guest_id": guest_id,
                    "status_chat": "new_chat" if is_new else "existing_chat",
                    "token": token
                }
                await ws_data.send(json.dumps(auth_data))
                auth_response = await ws_data.recv()
                auth_data_resp = json.loads(auth_response)
                if auth_data_resp.get("status") != "success":
                    self.log(f"Ошибка авторизации: {auth_response}", "ERROR")
                    return False
                self.log(f"Авторизация пройдена", "SYSTEM")
        except Exception as e:
            self.log(f"Ошибка авторизации: {e}", "ERROR")
            return False
        
        # Подключение к чату
        ws_url = f"{WS_NEW_CHAT_URL}/{token}/" if is_new else f"{WS_CHAT_URL}/{token}/"
        
        try:
            self.ws_chat = await websockets.connect(ws_url)
            self.current_room = room_name
            self.log(f"✅ Подключен к чату {room_name} (собеседник: User {guest_id})", "SYSTEM")
            
            asyncio.create_task(self.listen_chat())
            return True
            
        except Exception as e:
            self.log(f"Ошибка подключения к чату: {e}", "ERROR")
            return False
    
    async def listen_chat(self):
        """Слушает сообщения из чата"""
        try:
            async for message in self.ws_chat:
                try:
                    data = json.loads(message)
                    if data.get("type") == "message":
                        self.log(f"💬 {data['message']}", "RECV")
                except json.JSONDecodeError:
                    self.log(f"Получены бинарные данные, {len(message)} байт", "RECV")
        except websockets.exceptions.ConnectionClosed:
            self.log("Чат закрыт", "ERROR")
        except Exception as e:
            self.log(f"Ошибка чата: {e}", "ERROR")
    
    async def send_message(self, message_text):
        """Отправляет сообщение в текущий чат"""
        if not self.ws_chat:
            self.log("Не подключен к чату!", "ERROR")
            return
        
        message_data = json.dumps({"message": message_text})
        await self.ws_chat.send(message_data)
        self.log(f"📤 {message_text}", "SEND")
    
    async def disconnect_chat(self):
        """Отключается от чата"""
        if self.ws_chat:
            await self.ws_chat.close()
            self.ws_chat = None
            self.current_room = None
            self.log("Отключен от чата", "SYSTEM")
    
    async def close(self):
        """Закрывает все соединения"""
        if self.ws_chat:
            await self.ws_chat.close()
        if self.ws_notification:
            await self.ws_notification.close()
        self.log("Все соединения закрыты", "SYSTEM")


async def main():
    """Главное меню"""
    print("\n" + "="*50)
    print(f"  ЧАТ-КЛИЕНТ | {MY_NAME} (ID: {MY_USER_ID})")
    print("="*50)
    print(f"\n  Мои чаты:")
    for room in MY_CHATS:
        print(f"  • {room} → User {GUEST_IDS.get(room, '?')}")
    
    client = ChatClient(MY_USER_ID, MY_TOKEN, MY_NAME, MY_CHATS, GUEST_IDS)
    
    # Подключаем уведомления
    print("\n  Подключение уведомлений...")
    await client.connect_notification()
    
    # Проверяем офлайн-сообщения
    await client.check_offline_messages()
    
    while True:
        print(f"\n{'─'*40}")
        print(f"  Статус: {'В чате ' + client.current_room if client.current_room else 'Не в чате'}")
        print(f"  Уведомлений: {len(client.notification_messages)}")
        print(f"{'─'*40}")
        print("  1. Подключиться к чату")
        print("  2. Отправить сообщение")
        print("  3. Отключиться от чата")
        print("  4. Показать уведомления")
        print("  5. Проверить офлайн-сообщения")
        print("  6. Мои чаты")
        print("  0. Выйти")
        print(f"{'─'*40}")
        
        choice = input("  Выбор: ").strip()
        
        if choice == "1":
            print("\n  Мои чаты:")
            for i, chat in enumerate(MY_CHATS, 1):
                print(f"  {i}. {chat} (с User {GUEST_IDS.get(chat, '?')})")
            chat_choice = input("  Номер чата: ").strip()
            try:
                idx = int(chat_choice) - 1
                room = MY_CHATS[idx]
                is_new = input("  Новый чат? (y/n): ").strip().lower() == 'y'
                await client.connect_chat(room, is_new)
            except (ValueError, IndexError):
                print("  Неверный выбор!")
        
        elif choice == "2":
            if client.current_room:
                message = input("  Сообщение: ").strip()
                if message:
                    await client.send_message(message)
            else:
                print("  Сначала подключись к чату!")
        
        elif choice == "3":
            await client.disconnect_chat()
        
        elif choice == "4":
            print(f"\n  Уведомления ({len(client.notification_messages)}):")
            for i, notif in enumerate(client.notification_messages, 1):
                print(f"  {i}. [{notif['room']}] от User {notif['sender_id']}: {notif['message']}")
        
        elif choice == "5":
            await client.check_offline_messages()
        
        elif choice == "6":
            print(f"\n  Мои чаты:")
            for room in MY_CHATS:
                print(f"  • {room} → User {GUEST_IDS.get(room, '?')}")
        
        elif choice == "0":
            await client.close()
            break
        
        else:
            print("  Неверный выбор!")

if __name__ == "__main__":
    asyncio.run(main())