# 📚 ДОКУМЕНТАЦИЯ - СИСТЕМА WEBSOCKET ЧАТА

## 📋 Содержание
1. [Обзор системы](#обзор-системы)
2. [Архитектура](#архитектура)
3. [Установка и настройка](#установка-и-настройка)
4. [Консумеры](#консумеры)
5. [Протоколы обмена данными](#протоколы-обмена-данными)
6. [Примеры использования](#примеры-использования)
7. [Обработка ошибок](#обработка-ошибок)
8. [Расширение функционала](#расширение-функционала)
9. [FAQ](#faq)

---

## 🎯 Обзор системы

Это система чата в реальном времени на основе Django Channels и WebSocket. Поддерживает:
- ✅ Личные чаты (1-на-1)
- ✅ Групповые чаты (множество участников)
- ✅ Отправку текстовых сообщений
- ✅ Отправку файлов (изображения, видео, документы)
- ✅ Аутентификацию через Redis
- ✅ Безопасность через временные токены

---

## 🏗️ Архитектура

### Диаграмма потока данных

```
┌──────────┐         ┌─────────────┐         ┌──────────┐
│  Клиент  │────1───▶│DataConsumer │────2───▶│  Redis   │
│          │◀───3────│             │         │  (TTL)   │
└──────────┘         └─────────────┘         └──────────┘
     │
     │ 4. Подключение с токеном
     ▼
┌─────────────────┐        ┌──────────────┐
│ ChatConsumer /  │───5───▶│    Redis     │
│NewChatConsumer  │        │  (проверка)  │
└─────────────────┘        └──────────────┘
     │
     │ 6. Валидация OK
     ▼
┌─────────────────┐        ┌──────────────┐
│  Channel Layer  │───7───▶│   Database   │
│   (группы)      │        │  (сообщения) │
└─────────────────┘        └──────────────┘
     │
     │ 8. Broadcast
     ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│Клиент 1  │  │Клиент 2  │  │Клиент 3  │
└──────────┘  └──────────┘  └──────────┘
```

### Компоненты системы

| Компонент | Описание | Технология |
|-----------|----------|------------|
| **DataConsumer** | Аутентификация клиента | WebSocket |
| **ChatConsumer** | Существующие чаты | WebSocket + Channels |
| **NewChatConsumer** | Создание новых чатов | WebSocket + Channels |
| **GroupChatConsumer** | Групповые чаты | WebSocket + Channels |
| **Redis** | Хранение временных сессий | Redis 6.0+ |
| **PostgreSQL/MySQL** | Хранение сообщений | Django ORM |
| **Channel Layer** | Межпроцессная коммуникация | Redis Channel Layer |

---

## 🔧 Установка и настройка

### 1. Установка зависимостей

```bash
pip install channels channels-redis redis django
```

### 2. Настройка Django settings.py

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',  # ← Добавить
    'your_app',  # ← Ваше приложение
]

# ASGI конфигурация
ASGI_APPLICATION = 'your_project.asgi.application'

# Настройка Channel Layer (Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Настройка логирования
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

### 3. Настройка ASGI (asgi.py)

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import your_app.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            your_app.routing.websocket_urlpatterns
        )
    ),
})
```

### 4. Настройка routing.py

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Аутентификация
    re_path(r'ws/data/$', consumers.DataConsumer.as_asgi()),
    
    # Существующие чаты
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Новые чаты
    re_path(r'ws/new_chat_user/(?P<room_name>\w+)/$', consumers.NewChatConsumer.as_asgi()),
    
    # Групповые чаты
    re_path(r'ws/group/(?P<room_name>\w+)/$', consumers.GroupChatConsumer.as_asgi()),
    
    # Тестовый эхо
    re_path(r'ws/your/$', consumers.YourConsumer.as_asgi()),
]
```

### 5. Модели данных (models.py)

```python
from django.db import models

class UserData(models.Model):
    """Связь пользователей и комнат"""
    user_id = models.CharField(max_length=100)
    guest_id = models.CharField(max_length=100)
    room = models.CharField(max_length=200)
    count = models.IntegerField(default=2)  # Количество участников
    groups = models.CharField(max_length=100, default="default")
    
    class Meta:
        db_table = 'user_data'
        indexes = [
            models.Index(fields=['user_id', 'guest_id', 'room']),
            models.Index(fields=['room']),
        ]

class DataMessage(models.Model):
    """Сообщения в чатах"""
    sender_id = models.CharField(max_length=100)
    receiver_id = models.CharField(max_length=100)
    room = models.CharField(max_length=200)
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'data_message'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['room', '-timestamp']),
            models.Index(fields=['sender_id', 'receiver_id']),
        ]
```

### 6. Запуск сервера

```bash
# 1. Применить миграции
python manage.py makemigrations
python manage.py migrate

# 2. Запустить Redis (в отдельном терминале)
redis-server

# 3. Запустить Django сервер
python manage.py runserver
```

---

## 📦 Консумеры

### 🔐 DataConsumer - Аутентификация

**URL:** `ws://localhost:8000/ws/data/`

**Назначение:** Создание временной сессии для последующего подключения к чату

**Входные данные:**
```json
{
    "room": "lobbi_1",
    "user_id": 3,
    "guest_id": 4,
    "status_chat": "new_chat",
    "token": "api87"
}
```

**Параметры:**
- `room` - ID комнаты (обязательно)
- `user_id` - ID текущего пользователя
- `guest_id` - ID собеседника
- `status_chat` - Тип чата:
  - `"new_chat"` - Создание нового чата
  - `"existing_chat"` - Подключение к существующему
- `token` - Уникальный токен для последующей авторизации (обязательно)

**Выходные данные:**
```json
{
    "action": "connect_to_chat",
    "status": "success"
}
```

**Коды закрытия:**
- `1000` - Успешная аутентификация
- `4001` - Отказ в доступе (комната существует / нет прав)

**Пример использования (Python):**
```python
import websocket
import json

# Подключение
ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8000/ws/data/")

# Аутентификация
ws.send(json.dumps({
    "room": "lobbi_1",
    "user_id": 3,
    "guest_id": 4,
    "status_chat": "new_chat",
    "token": "api87"
}))

# Ответ
response = ws.recv()
print(response)  # {"action": "connect_to_chat", "status": "success"}

ws.close()
```

---

### 💬 ChatConsumer - Существующие чаты

**URL:** `ws://localhost:8000/ws/chat/{token}/`

**Назначение:** Работа с существующим личным чатом

**Требования:**
- Пройти аутентификацию через DataConsumer
- Иметь запись в таблице UserData

**Отправка текстового сообщения:**
```json
{
    "message": "Привет, как дела?"
}
```

**Отправка файла:**
```
[METADATA_JSON] + |||BINARY_DATA||| + [FILE_BYTES]

Метаданные:
{
    "file_name": "photo.jpg",
    "file_type": "image/jpeg",
    "file_size": 12345
}
```

**Получение текстового сообщения:**
```json
{
    "type": "message",
    "message": "Привет, как дела?",
    "sender_id": 3
}
```

**Получение файла:**
```
[METADATA_JSON] + |||BINARY_DATA||| + [FILE_BYTES]

Метаданные:
{
    "type": "file",
    "file_name": "photo.jpg",
    "file_type": "image/jpeg",
    "file_size": 12345,
    "sender_id": 3
}
```

---

### 🆕 NewChatConsumer - Новые чаты

**URL:** `ws://localhost:8000/ws/new_chat_user/{token}/`

**Назначение:** Создание нового личного чата

**Отличия от ChatConsumer:**
- Автоматически создает записи UserData для обоих пользователей
- Проверяет что комната еще не существует

**Использование:** Аналогично ChatConsumer

---

### 👥 GroupChatConsumer - Групповые чаты

**URL:** `ws://localhost:8000/ws/group/{room_name}/`

**Статус:** В разработке (базовая реализация)

**TODO:**
- Добавить аутентификацию
- Добавить роли пользователей (админ, модератор, участник)
- Добавить список участников онлайн
- Добавить уведомления о входе/выходе

---

## 📨 Протоколы обмена данными

### Текстовые сообщения

**Формат отправки:**
```json
{
    "message": "Текст сообщения"
}
```

**Формат получения:**
```json
{
    "type": "message",
    "message": "Текст сообщения",
    "sender_id": 123
}
```

### Файлы (Бинарные данные)

**Структура пакета:**
```
┌─────────────────────┐
│  METADATA (JSON)    │  ← UTF-8 строка
├─────────────────────┤
│ |||BINARY_DATA|||   │  ← Разделитель
├─────────────────────┤
│  FILE BYTES         │  ← Сырые байты файла
└─────────────────────┘
```

**Метаданные файла:**
```json
{
    "file_name": "document.pdf",
    "file_type": "application/pdf",
    "file_size": 1048576
}
```

**Поддерживаемые типы файлов:**
- Изображения: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Видео: `.mp4`, `.avi`, `.mov`, `.mkv`
- Аудио: `.mp3`, `.wav`, `.ogg`, `.flac`
- Документы: `.pdf`, `.doc`, `.docx`, `.txt`, `.xlsx`
- Архивы: `.zip`, `.rar`, `.7z`

**Ограничения:**
- Максимальный размер файла: 50 МБ (настраивается)
- Файлы НЕ сохраняются на сервере (пока)
- Передаются напрямую между клиентами

---

## 💡 Примеры использования

### Пример 1: Создание нового чата

```python
import websocket
import json
import threading

# 1. АУТЕНТИФИКАЦИЯ
ws_auth = websocket.WebSocket()
ws_auth.connect("ws://127.0.0.1:8000/ws/data/")
ws_auth.send(json.dumps({
    "room": "room_12345",
    "user_id": 100,
    "guest_id": 200,
    "status_chat": "new_chat",
    "token": "secure_token_123"
}))
response = ws_auth.recv()
print(f"Auth: {response}")
ws_auth.close()

# 2. ПОДКЛЮЧЕНИЕ К ЧАТУ
ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8000/ws/new_chat_user/secure_token_123/")

# 3. ПРОСЛУШИВАНИЕ СООБЩЕНИЙ (в отдельном потоке)
def listen():
    while True:
        try:
            data = ws.recv()
            print(f"Received: {data}")
        except:
            break

thread = threading.Thread(target=listen, daemon=True)
thread.start()

# 4. ОТПРАВКА СООБЩЕНИЙ
ws.send(json.dumps({"message": "Привет!"}))
ws.send(json.dumps({"message": "Как дела?"}))

# 5. ЗАКРЫТИЕ
input("Press Enter to exit...")
ws.close()
```

### Пример 2: Отправка файла

```python
import websocket
import json
import os
import mimetypes

ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8000/ws/chat/your_token/")

# Читаем файл
file_path = "photo.jpg"
with open(file_path, 'rb') as f:
    file_data = f.read()

# Формируем метаданные
metadata = json.dumps({
    "file_name": os.path.basename(file_path),
    "file_type": mimetypes.guess_type(file_path)[0],
    "file_size": len(file_data)
}).encode('utf-8')

# Отправляем
separator = b"|||BINARY_DATA|||"
ws.send(metadata + separator + file_data, opcode=websocket.ABNF.OPCODE_BINARY)

ws.close()
```

### Пример 3: Получение файла

```python
import websocket

ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8000/ws/chat/your_token/")

# Получаем данные
opcode, data = ws.recv_data()

if opcode == websocket.ABNF.OPCODE_BINARY:
    # Парсим файл
    separator = b"|||BINARY_DATA|||"
    sep_idx = data.find(separator)
    
    metadata = json.loads(data[:sep_idx].decode('utf-8'))
    file_data = data[sep_idx + len(separator):]
    
    # Сохраняем файл
    with open(metadata['file_name'], 'wb') as f:
        f.write(file_data)
    
    print(f"File saved: {metadata['file_name']}")

ws.close()
```

---

## ⚠️ Обработка ошибок

### Коды закрытия WebSocket

| Код | Описание | Действие |
|-----|----------|----------|
| 1000 | Нормальное закрытие | Нет действий |
| 4001 | Нет доступа | Проверить права пользователя |
| 4002 | Невалидный токен | Повторить аутентификацию |
| 4003 | Сессия истекла | Создать новую сессию (< 5 минут) |

### Типичные ошибки и решения

**1. Connection refused**
```
Error: [Errno 111] Connection refused
```
**Решение:** Убедитесь что Redis запущен (`redis-server`)

**2. Session expired**
```
Error: Session not found or expired
```
**Решение:** Токен действителен 5 минут. Повторите аутентификацию.

**3. Room already exists**
```
Error: Room already exists (code 4001)
```
**Решение:** Используйте `status_chat: "existing_chat"` вместо `"new_chat"`

**4. Invalid binary data format**
```
Error: Invalid binary data format: separator not found
```
**Решение:** Убедитесь что разделитель `|||BINARY_DATA|||` присутствует

---

## 🚀 Расширение функционала

### Добавление сохранения файлов в БД

```python
# models.py
class FileMessage(models.Model):
    sender_id = models.CharField(max_length=100)
    receiver_id = models.CharField(max_length=100)
    room = models.CharField(max_length=200)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    file_size = models.IntegerField()
    file_data = models.BinaryField()  # или путь к S3
    timestamp = models.DateTimeField(auto_now_add=True)

# consumers.py (в BaseChatConsumer)
@sync_to_async
def save_file_to_db(self, file_name, file_type, file_size, file_data):
    FileMessage.objects.create(
        sender_id=self.user_id,
        receiver_id=self.guest_id,
        room=self.room_name,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        file_data=file_data  # или загрузка в S3
    )
```

### Добавление статуса "печатает"

```python
# Клиент отправляет
ws.send(json.dumps({"action": "typing"}))

# Консумер обрабатывает
if data.get("action") == "typing":
    await self.channel_layer.group_send(
        self.room_group_name,
        {
            "type": "user.typing",
            "user_id": self.user_id
        }
    )
```

### Добавление уведомлений о прочтении

```python
# Клиент отправляет
ws.send(json.dumps({
    "action": "read",
    "message_ids": [1, 2, 3, 4, 5]
}))

# Консумер помечает как прочитанные
@sync_to_async
def mark_as_read(self, message_ids):
    DataMessage.objects.filter(
        id__in=message_ids,
        receiver_id=self.user_id
    ).update(is_read=True)
```

---

## ❓ FAQ

### Q: Почему используется Redis для сессий?
**A:** Redis обеспечивает:
- Быстрый доступ к данным (in-memory)
- Автоматическое удаление с TTL (5 минут)
- Масштабируемость для множества соединений

### Q: Можно ли использовать без Redis?
**A:** Да, но потребуется:
1. Изменить `validate_token_and_get_session` для работы с БД
2. Добавить модель SessionData в Django
3. Настроить периодическую очистку старых сессий

### Q: Почему файлы не сохраняются на сервере?
**A:** Для экономии места и скорости передачи. Легко добавить:
```python
# В handle_binary_data
file_path = f"uploads/{file_name}"
with open(file_path, 'wb') as f:
    f.write(file_data)
```

### Q: Как ограничить размер файлов?
**A:** В `handle_binary_data` уже есть проверка:
```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
if file_size > MAX_FILE_SIZE:
    # Отклонить файл
```

### Q: Как добавить шифрование сообщений?
**A:** Можно использовать end-to-end encryption на клиенте:
```python
from cryptography.fernet import Fernet

# Генерация ключа (один раз)
key = Fernet.generate_key()
cipher = Fernet(key)

# Шифрование
encrypted = cipher.encrypt(message.encode())

# Отправка
ws.send(json.dumps({"message": encrypted.decode()}))
```

### Q: Поддерживает ли система горизонтальное масштабирование?
**A:** Да! Redis Channel Layer позволяет:
- Запускать несколько экземпляров Django
- Использовать load balancer
- Все экземпляры будут синхронизированы через Redis

---

## 📊 Производительность

### Рекомендации по оптимизации

1. **Используйте пул соединений PostgreSQL**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Переиспользование соединений
    }
}
```

2. **Настройте индексы БД**
```sql
CREATE INDEX idx_room_timestamp ON data_message(room, timestamp DESC);
CREATE INDEX idx_user_guest_room ON user_data(user_id, guest_id, room);
```

3. **Используйте Redis Sentinel для высокой доступности**
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "sentinels": [('localhost', 26379)],
            "master_name": "mymaster",
        },
    },
}
```

4. **Мониторинг**
- Prometheus + Grafana для метрик
- Sentry для ошибок
- Redis monitoring для отслеживания памяти

---

## 📞 Поддержка

Для вопросов и предложений:
- 📧 Email: your-email@example.com
- 💬 Telegram: @your_username
- 🐛 Issues: github.com/your-repo/issues

---

**Версия документации:** 1.0  
**Дата обновления:** 2026-02-11  
**Автор:** Your Name
