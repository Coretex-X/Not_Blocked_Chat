# ДОКУМЕНТАЦИЯ: WebSocket ЧАТ С ПОДДЕРЖКОЙ ФАЙЛОВ

## 📋 ОГЛАВЛЕНИЕ

1. Что изменилось в consumers.py
2. Как это работает
3. Как использовать клиент
4. Примеры отправки разных типов файлов
5. Формат сообщений
6. Важные особенности

---

## 1️⃣ ЧТО ИЗМЕНИЛОСЬ В CONSUMERS.PY

### ✨ Основные изменения:

1. **Метод `receive()` теперь принимает два параметра:**
   ```python
   async def receive(self, text_data=None, bytes_data=None):
   ```
   - `text_data` - текстовые сообщения (JSON)
   - `bytes_data` - бинарные данные (файлы)

2. **Добавлена функция определения типа файла:**
   ```python
   def _detect_file_type(self, data):
   ```
   Определяет тип по magic bytes (первым байтам файла)

3. **Новый обработчик для отправки файлов клиентам:**
   ```python
   async def chat_file(self, event):
   ```

4. **Бинарные файлы НЕ сохраняются в БД** (по твоему требованию)
   - Только пересылаются между клиентами
   - Текстовые сообщения сохраняются как раньше

### 📦 Затронутые консюмеры:

✅ **ChatConsumer** - обновлен
✅ **NewChatConsumer** - обновлен  
✅ **GroupChatConsumer** - обновлен
⬜ **DataConsumer** - без изменений (это консюмер для авторизации)
⬜ **YourConsumer** - без изменений (тестовый)
⬜ **NotificationConsumer** - пока пустой

---

## 2️⃣ КАК ЭТО РАБОТАЕТ

### 🔄 Поток данных для ТЕКСТА:

```
Клиент → WebSocket (text frame) → receive(text_data) 
    → Парсинг JSON 
    → Сохранение в БД (через save_message_to_db)
    → group_send(type="chat.message")
    → chat_message() 
    → Отправка всем клиентам как JSON
```

### 🔄 Поток данных для ФАЙЛОВ:

```
Клиент → WebSocket (binary frame) → receive(bytes_data)
    → Конвертация в base64
    → Определение типа (_detect_file_type)
    → БД НЕ ИСПОЛЬЗУЕТСЯ ❌
    → group_send(type="chat.file")
    → chat_file()
    → Отправка всем клиентам как JSON с base64
```

### 🎯 Ключевые моменты:

1. **Клиент отправляет файл как БИНАРНЫЕ данные** (bytes)
2. **Сервер конвертирует в base64** для передачи через JSON
3. **Клиент получает JSON** с полем `file_data` в base64
4. **Клиент декодирует base64** обратно в байты
5. **Клиент сохраняет файл** на диск (или показывает в UI)

---

## 3️⃣ КАК ИСПОЛЬЗОВАТЬ КЛИЕНТ

### 📥 Установка зависимостей:

```bash
pip install websockets
```

### 🚀 Быстрый старт:

```python
import asyncio
from client_example import ChatClient

async def test():
    # Создаем клиента
    client = ChatClient("ws://localhost:8000/ws/chat/YOUR_TOKEN/")
    
    # Подключаемся
    await client.connect()
    
    # Запускаем прием сообщений в фоне
    asyncio.create_task(client.receive_messages())
    
    # Отправляем текст
    await client.send_text_message("Привет!")
    
    # Отправляем файл
    await client.send_file("photo.jpg")
    
    # Ждем ответы
    await asyncio.sleep(10)
    
    # Отключаемся
    await client.disconnect()

asyncio.run(test())
```

### 🎮 Интерактивный режим:

```bash
python client_example.py
# Выбери опцию 2
# Введи WebSocket URL
# Используй команды:
#   /file путь/к/файлу  - отправить файл
#   /quit               - выйти
#   любой текст         - отправить сообщение
```

---

## 4️⃣ ПРИМЕРЫ ОТПРАВКИ РАЗНЫХ ТИПОВ ФАЙЛОВ

### 📸 Изображения:

```python
await client.send_file("photo.jpg")      # JPEG
await client.send_file("screenshot.png") # PNG
await client.send_file("animation.gif")  # GIF
await client.send_file("avatar.webp")    # WebP
```

### 🎥 Видео:

```python
await client.send_file("video.mp4")      # MP4
await client.send_file("clip.webm")      # WebM
await client.send_file("movie.avi")      # AVI
```

### 🎵 Аудио:

```python
await client.send_file("song.mp3")       # MP3
await client.send_file("voice.wav")      # WAV
await client.send_file("podcast.ogg")    # OGG
```

### 📄 Документы:

```python
await client.send_file("report.pdf")     # PDF
await client.send_file("data.docx")      # Word (как ZIP)
await client.send_file("table.xlsx")     # Excel (как ZIP)
```

---

## 5️⃣ ФОРМАТ СООБЩЕНИЙ

### 📤 ОТПРАВКА от клиента:

#### Текстовое сообщение:
```python
# Клиент отправляет JSON как текст:
{
    "type": "text",
    "message": "Привет, мир!"
}
```

#### Файл:
```python
# Клиент отправляет сырые байты (binary frame)
file_bytes = open("photo.jpg", "rb").read()
await websocket.send(file_bytes)  # НЕ JSON!
```

### 📥 ПОЛУЧЕНИЕ на клиенте:

#### Текстовое сообщение:
```json
{
    "type": "text",
    "message": "Привет, мир!"
}
```

#### Файл:
```json
{
    "type": "file",
    "file_data": "base64_encoded_string_here...",
    "file_type": "image/jpeg",
    "file_size": 45678
}
```

---

## 6️⃣ ВАЖНЫЕ ОСОБЕННОСТИ

### ✅ Что СОХРАНЯЕТСЯ:

- ✅ Текстовые сообщения → в БД (таблица DataMessage)
- ✅ Информация о чатах → в БД (таблица UserData)
- ✅ Токены сессий → в Redis (с TTL 300 секунд)

### ❌ Что НЕ СОХРАНЯЕТСЯ:

- ❌ Бинарные файлы → НЕ в БД
- ❌ Только пересылка между клиентами в реальном времени

### 🔒 Безопасность:

1. **Токен проверяется** при подключении
2. **Права доступа проверяются** через check_access()
3. **Сессия удаляется** после успешного подключения
4. **TTL 300 секунд** для токенов в Redis

### 🎯 Поддерживаемые типы файлов:

| Тип | Расширения | MIME-тип |
|-----|-----------|----------|
| Изображения | jpg, png, gif, webp | image/* |
| Видео | mp4, webm, flv | video/* |
| Аудио | mp3, wav, ogg | audio/* |
| Документы | pdf, docx, xlsx, zip | application/* |

### ⚡ Производительность:

- **Max размер файла**: зависит от настроек Django Channels
- **Рекомендуется**: до 10-20 MB для стабильной работы
- **Для больших файлов**: лучше использовать отдельный file upload API

### 🐛 Обработка ошибок:

```python
# В консюмерах все обернуто в try-except
try:
    # код обработки
except Exception as e:
    print(f"Error: {e}")
    # Соединение НЕ закрывается, продолжает работать
```

---

## 🔧 НАСТРОЙКА DJANGO

### settings.py:

```python
# WebSocket timeout (для больших файлов)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
            # Увеличь для больших файлов:
            "capacity": 1500,
            "expiry": 10,
        },
    },
}
```

### routing.py (пример):

```python
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<str:room_name>/', consumers.ChatConsumer.as_asgi()),
    path('ws/new-chat/<str:room_name>/', consumers.NewChatConsumer.as_asgi()),
    path('ws/group/<str:room_name>/', consumers.GroupChatConsumer.as_asgi()),
    path('ws/connect/', consumers.DataConsumer.as_asgi()),
]
```

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ ПРИМЕРЫ

### Пример 1: Отправка нескольких файлов подряд

```python
files = ["photo1.jpg", "photo2.jpg", "video.mp4"]

for file_path in files:
    await client.send_file(file_path)
    await asyncio.sleep(0.5)  # Небольшая задержка между файлами
```

### Пример 2: Отправка файла с метаданными

Можно сначала отправить текст с описанием:

```python
# Отправляем описание
await client.send_text_message("Отправляю тебе фото с отпуска!")

# Через секунду отправляем файл
await asyncio.sleep(1)
await client.send_file("vacation.jpg")
```

### Пример 3: Обработка полученного файла

```python
async def on_file_received(file_bytes, file_type):
    if file_type.startswith("image/"):
        # Это изображение - можно показать в UI
        display_image(file_bytes)
    elif file_type.startswith("video/"):
        # Это видео - сохраняем и запускаем плеер
        save_and_play_video(file_bytes)
    elif file_type == "application/pdf":
        # Это PDF - открываем в просмотрщике
        open_pdf(file_bytes)
```

---

## ❓ FAQ

**Q: Можно ли отправить файл больше 100 MB?**  
A: Технически да, но лучше использовать chunking или отдельный upload API

**Q: Почему файлы не сохраняются в БД?**  
A: По твоему требованию. Можно добавить позже, если нужно

**Q: Как отправить имя файла?**  
A: Можно расширить формат, добавив поле `filename` в JSON при отправке file

**Q: Работает ли это с несколькими клиентами одновременно?**  
A: Да! Все клиенты в группе получат файл

**Q: Как узнать, что файл получен успешно?**  
A: Можно добавить подтверждение (acknowledgment) отдельным сообщением

---

## 🎉 ГОТОВО!

Твоя система теперь поддерживает:
- ✅ Текстовые сообщения (с сохранением в БД)
- ✅ Бинарные файлы (без сохранения в БД)
- ✅ Автоматическое определение типа файла
- ✅ Групповые чаты
- ✅ Личные чаты
- ✅ Новые чаты
- ✅ Безопасную авторизацию через токены

Вся твоя концепция с Redis-сессиями и токенами осталась нетронутой! 🚀
