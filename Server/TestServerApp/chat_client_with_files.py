import websocket
import json
import threading
import os
import mimetypes

class ChatClient:
    def __init__(self, server_url, auth_url):
        """
        Инициализация клиента чата
        
        Args:
            server_url: URL WebSocket сервера (например, "ws://127.0.0.1:5000")
            auth_url: Путь для аутентификации (например, "/ws/data/")
        """
        self.server_url = server_url
        self.auth_url = auth_url
        self.ws = None
        self.is_connected = False
        self.download_folder = "downloads"  # Папка для сохранения полученных файлов
        
        # Создаем папку для загрузок, если её нет
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
    
    def authenticate(self, room, user_id, guest_id, status_chat, token):
        """
        Аутентификация на сервере
        
        Args:
            room: ID комнаты
            user_id: ID пользователя
            guest_id: ID собеседника
            status_chat: Статус чата ("new_chat" или "existing_chat")
            token: Токен аутентификации
        """
        print("🔐 Аутентификация...")
        ws_auth = websocket.WebSocket()
        ws_auth.connect(self.server_url + self.auth_url)
        ws_auth.send(json.dumps({
            "room": room,
            "user_id": user_id,
            "guest_id": guest_id,
            "status_chat": status_chat,
            "token": token
        }))
        
        # Получаем ответ
        response = ws_auth.recv()
        print(f"✅ Аутентификация: {response}")
        ws_auth.close()
    
    def connect_to_chat(self, chat_path):
        """
        Подключение к чату
        
        Args:
            chat_path: Путь к чату (например, "/ws/chat_user/api87/")
        """
        print("🔌 Подключение к чату...")
        self.ws = websocket.WebSocket()
        self.ws.connect(self.server_url + chat_path)
        self.is_connected = True
        print("✅ Подключено к чату!")
    
    def receive_messages(self):
        """
        Функция для прослушивания входящих сообщений (запускается в отдельном потоке)
        """
        while self.is_connected:
            try:
                # Проверяем тип данных
                opcode, data = self.ws.recv_data()
                
                if opcode == websocket.ABNF.OPCODE_TEXT:
                    # Текстовое сообщение
                    message = json.loads(data.decode('utf-8'))
                    print(f"\n📩 Сообщение: {message}")
                
                elif opcode == websocket.ABNF.OPCODE_BINARY:
                    # Бинарные данные (файл)
                    self._handle_file_receive(data)
                    
            except Exception as e:
                print(f"\n❌ Отключение: {e}")
                self.is_connected = False
                break
    
    def _handle_file_receive(self, data):
        """
        Обработка полученного файла
        
        Args:
            data: Бинарные данные с метаданными
        """
        try:
            # Ищем разделитель между метаданными и файлом
            separator = b"|||BINARY_DATA|||"
            separator_index = data.find(separator)
            
            if separator_index == -1:
                print("❌ Неверный формат бинарных данных")
                return
            
            # Извлекаем метаданные и данные файла
            metadata_bytes = data[:separator_index]
            file_data = data[separator_index + len(separator):]
            
            # Декодируем метаданные
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            file_name = metadata.get("file_name", "unknown")
            file_type = metadata.get("file_type", "unknown")
            file_size = metadata.get("file_size", 0)
            sender_id = metadata.get("sender_id", "unknown")
            
            print(f"\n📎 Получен файл от пользователя {sender_id}:")
            print(f"   Имя: {file_name}")
            print(f"   Тип: {file_type}")
            print(f"   Размер: {file_size} байт")
            
            # Сохраняем файл
            file_path = os.path.join(self.download_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"   ✅ Сохранён: {file_path}")
            
        except Exception as e:
            print(f"❌ Ошибка при получении файла: {e}")
    
    def send_message(self, message):
        """
        Отправка текстового сообщения
        
        Args:
            message: Текст сообщения
        """
        if not self.is_connected:
            print("❌ Не подключено к чату")
            return
        
        self.ws.send(json.dumps({"message": message}))
        print(f"✉️ Отправлено: {message}")
    
    def send_file(self, file_path):
        """
        Отправка файла
        
        Args:
            file_path: Путь к файлу
        """
        if not self.is_connected:
            print("❌ Не подключено к чату")
            return
        
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {file_path}")
            return
        
        try:
            # Читаем файл
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Получаем информацию о файле
            file_name = os.path.basename(file_path)
            file_size = len(file_data)
            file_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            # Формируем метаданные
            metadata = json.dumps({
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size
            }).encode('utf-8')
            
            # Объединяем метаданные и данные файла
            separator = b"|||BINARY_DATA|||"
            binary_data = metadata + separator + file_data
            
            # Отправляем бинарные данные
            self.ws.send(binary_data, opcode=websocket.ABNF.OPCODE_BINARY)
            
            print(f"📤 Файл отправлен:")
            print(f"   Имя: {file_name}")
            print(f"   Тип: {file_type}")
            print(f"   Размер: {file_size} байт")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке файла: {e}")
    
    def start_listening(self):
        """
        Запуск потока для прослушивания сообщений
        """
        thread = threading.Thread(target=self.receive_messages, daemon=True)
        thread.start()
    
    def close(self):
        """
        Закрытие соединения
        """
        self.is_connected = False
        if self.ws:
            self.ws.close()
        print("👋 Соединение закрыто")


# ==================== ПРИМЕР ИСПОЛЬЗОВАНИЯ ====================

def main():
    # Создаем клиент
    client = ChatClient(
        server_url="ws://127.0.0.1:5000",
        auth_url="/ws/data/"
    )
    
    # 1. Аутентификация
    client.authenticate(
        room="lobbi_3",
        user_id=3,
        guest_id=4,
        status_chat="new_chat",
        token="api87"
    )
    
    # 2. Подключаемся к чату
    client.connect_to_chat("/ws/new_chat_user/api87/")
    
    # 3. Запускаем прослушивание сообщений
    client.start_listening()
    
    # 4. Главный цикл для взаимодействия
    print("\n📝 Команды:")
    print("   - Просто текст для отправки сообщения")
    print("   - /file <путь> для отправки файла")
    print("   - /exit для выхода")
    print("-" * 50)
    
    while True:
        user_input = input("\nВы: ")
        
        if user_input.lower() == '/exit':
            break
        
        elif user_input.startswith('/file '):
            # Отправка файла
            file_path = user_input[6:].strip()
            client.send_file(file_path)
        
        else:
            # Отправка текстового сообщения
            client.send_message(user_input)
    
    # Закрываем соединение
    client.close()


if __name__ == "__main__":
    main()
