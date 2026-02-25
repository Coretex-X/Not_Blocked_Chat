# 🚀 БЫСТРАЯ ШПАРГАЛКА

## СЕРВЕРНАЯ ЧАСТЬ (consumers.py)

### Что изменилось:
```python
# БЫЛО:
async def receive(self, text_data):
    # только текст

# СТАЛО:
async def receive(self, text_data=None, bytes_data=None):
    # текст И бинарные данные
```

### Новые методы в ChatConsumer, NewChatConsumer, GroupChatConsumer:

1. **_detect_file_type(data)** - определяет тип файла
2. **chat_file(event)** - отправляет файл клиентам

---

## КЛИЕНТСКАЯ ЧАСТЬ (Python)

### Установка:
```bash
pip install websockets
```

### Базовое использование:

```python
from client_example import ChatClient

client = ChatClient("ws://localhost:8000/ws/chat/TOKEN/")
await client.connect()

# Текст
await client.send_text_message("Привет!")

# Файл
await client.send_file("photo.jpg")

# Прием
asyncio.create_task(client.receive_messages())

await client.disconnect()
```

---

## ФОРМАТЫ СООБЩЕНИЙ

### Отправка клиентом:

**Текст:**
```python
# JSON через text frame
{"type": "text", "message": "Привет!"}
```

**Файл:**
```python
# Сырые байты через binary frame
with open("file.jpg", "rb") as f:
    await websocket.send(f.read())
```

### Получение клиентом:

**Текст:**
```json
{"type": "text", "message": "Привет!"}
```

**Файл:**
```json
{
    "type": "file",
    "file_data": "base64...",
    "file_type": "image/jpeg",
    "file_size": 12345
}
```

---

## ПОДДЕРЖИВАЕМЫЕ ТИПЫ

| Категория | Типы |
|-----------|------|
| 📸 Изображения | jpg, png, gif, webp |
| 🎥 Видео | mp4, webm, flv |
| 🎵 Аудио | mp3, wav, ogg |
| 📄 Документы | pdf, zip, docx, xlsx |

---

## ВАЖНО!

✅ Текст → сохраняется в БД  
❌ Файлы → НЕ сохраняются в БД (только пересылка)  
🔒 Токены проверяются при подключении  
⏱️ Сессии в Redis живут 300 секунд  

---

## БЫСТРЫЙ ТЕСТ

```bash
# Запуск интерактивного клиента:
python client_example.py

# Выбери опцию 2
# Введи: ws://localhost:8000/ws/chat/YOUR_TOKEN/
# Команды:
#   /file photo.jpg  - отправить файл
#   /quit            - выйти
#   любой текст      - отправить сообщение
```

---

## TROUBLESHOOTING

**Проблема:** Файл не отправляется  
**Решение:** Проверь, что отправляешь bytes, а не строку

**Проблема:** Получаю ошибку при декодировании base64  
**Решение:** Убедись, что сервер отправляет `file_data` в base64

**Проблема:** Соединение закрывается при отправке файла  
**Решение:** Увеличь timeout в настройках channels

---

🎯 Все готово к использованию!
