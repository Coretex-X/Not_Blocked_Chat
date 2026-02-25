# Документация API для WebSocket Consumers

## Оглавление
- [Обзор](#обзор)
- [DataConsumer - Аутентификация](#dataconsumer---аутентификация)
- [ChatConsumer - Существующий чат](#chatconsumer---существующий-чат)
- [NewChatConsumer - Новый чат](#newchatconsumer---новый-чат)
- [YourConsumer - Echo сервер](#yourconsumer---echo-сервер)
- [GroupChatConsumer - Групповой чат](#groupchatconsumer---групповой-чат)
- [Форматы данных](#форматы-данных)

---

## Обзор

Все consumer'ы работают через WebSocket. Базовый URL: `ws://localhost:8000`

### Общий процесс работы с приватными чатами:

```
1. Подключиться к DataConsumer → Отправить данные аутентификации → Получить подтверждение
2. Отключиться от DataConsumer
3. Подключиться к ChatConsumer/NewChatConsumer с токеном из URL
4. Отправлять/получать сообщения
```

---

## DataConsumer - Аутентификация

### URL подключения:
```
ws://localhost:8000/ws/auth/
```

### Назначение:
Проверка прав доступа и создание временной сессии в Redis с токеном.

### Порядок работы:

#### 1. Подключиться к WebSocket
```
CONNECT ws://localhost:8000/ws/auth/
```

#### 2. Отправить JSON с данными аутентификации

**Для НОВОГО чата:**
```json
{
  "room": "уникальный-id-комнаты",
  "user_id": "id-пользователя",
  "guest_id": "id-собеседника",
  "status_chat": "new_chat",
  "token": "уникальный-токен-сессии"
}
```

**Для СУЩЕСТВУЮЩЕГО чата:**
```json
{
  "room": "существующий-id-комнаты",
  "user_id": "id-пользователя",
  "guest_id": "id-собеседника",
  "status_chat": "existing_chat",
  "token": "уникальный-токен-сессии"
}
```

#### 3. Получить ответ

**Успех:**
```json
{
  "action": "connect_to_chat",
  "status": "success"
}
```

**Ошибка:**
Соединение закроется с кодом `4001`

#### 4. Соединение автоматически закроется

DataConsumer сразу закрывается после ответа.

---

### Параметры запроса:

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `room` | string | ✅ Да | ID комнаты чата |
| `user_id` | string | ❌ Нет* | ID текущего пользователя |
| `guest_id` | string | ❌ Нет* | ID собеседника |
| `status_chat` | string | ✅ Да | Тип: `"new_chat"` или `"existing_chat"` |
| `token` | string | ✅ Да | Уникальный токен (UUID) |

\* Для `new_chat` можно не указывать, для `existing_chat` обязательны.

---

### Логика проверки:

**Для `new_chat`:**
- Проверяет, что комната с таким `room` НЕ существует в базе
- Если существует → отказ (код 4001)
- Если не существует → создаёт сессию в Redis

**Для `existing_chat`:**
- Проверяет, что в базе есть запись с `user_id`, `guest_id` и `room`
- Если запись есть → создаёт сессию в Redis
- Если записи нет → отказ (код 4001)

---

### Сессия в Redis:

После успешной аутентификации создаётся запись:

**Ключ:** `session:{status_chat}:{token}`
- Пример: `session:new_chat:abc-123-def`

**Значение (JSON):**
```json
{
  "room": "room123",
  "user_id": "user1",
  "guest_id": "user2",
  "token": "abc-123-def"
}
```

**Время жизни:** 5 минут (300 секунд)

⚠️ **Токен одноразовый** — после использования удаляется из Redis!

---

### Примеры:

#### Пример 1: Создание нового чата

**Отправляем:**
```json
{
  "room": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "alice",
  "guest_id": "bob",
  "status_chat": "new_chat",
  "token": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

**Получаем:**
```json
{
  "action": "connect_to_chat",
  "status": "success"
}
```

**Теперь можно подключиться:**
```
ws://localhost:8000/ws/new_chat/f47ac10b-58cc-4372-a567-0e02b2c3d479/
```

---

#### Пример 2: Подключение к существующему чату

**Отправляем:**
```json
{
  "room": "existing-room-123",
  "user_id": "alice",
  "guest_id": "bob",
  "status_chat": "existing_chat",
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Получаем:**
```json
{
  "action": "connect_to_chat",
  "status": "success"
}
```

**Теперь можно подключиться:**
```
ws://localhost:8000/ws/chat/a1b2c3d4-e5f6-7890-abcd-ef1234567890/
```

---

## ChatConsumer - Существующий чат

### URL подключения:
```
ws://localhost:8000/ws/chat/{TOKEN}/
```

Где `{TOKEN}` — токен, полученный от DataConsumer.

### Назначение:
Работа с существующим чатом (отправка/получение сообщений).

---

### Порядок работы:

#### 1. Получить токен от DataConsumer
```json
{
  "room": "room123",
  "user_id": "alice",
  "guest_id": "bob",
  "status_chat": "existing_chat",
  "token": "your-token-here"
}
```

#### 2. Подключиться к ChatConsumer
```
CONNECT ws://localhost:8000/ws/chat/your-token-here/
```

При подключении:
- Токен проверяется в Redis
- Если валиден → токен удаляется, соединение принимается
- Если невалиден → соединение закрывается (код 4002)

#### 3. Отправить/получить сообщения

---

### Отправка ТЕКСТОВОГО сообщения:

**Формат:**
```json
{
  "message": "текст сообщения"
}
```

**Пример:**
```json
{
  "message": "Привет! Как дела?"
}
```

Что происходит:
1. Сообщение сохраняется в базу данных
2. Рассылается ВСЕМ участникам комнаты (включая отправителя)

---

### Получение ТЕКСТОВОГО сообщения:

**Формат ответа:**
```json
{
  "type": "message",
  "message": "текст сообщения",
  "sender_id": "id-отправителя"
}
```

**Пример:**
```json
{
  "type": "message",
  "message": "Привет! Как дела?",
  "sender_id": "alice"
}
```

---

### Отправка ФАЙЛА:

**Формат:** Бинарные данные в специальном формате

**Структура:**
```
[МЕТАДАННЫЕ В JSON] + [РАЗДЕЛИТЕЛЬ] + [БИНАРНЫЕ ДАННЫЕ ФАЙЛА]
```

**Разделитель:** `|||BINARY_DATA|||` (в байтах: `b"|||BINARY_DATA|||"`)

**Метаданные (JSON):**
```json
{
  "file_name": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 12345
}
```

**Полный формат в байтах:**
```
{"file_name":"document.pdf","file_type":"application/pdf","file_size":12345}|||BINARY_DATA|||[БАЙТЫ ФАЙЛА]
```

**Пример в Python:**
```python
import json

# Метаданные
metadata = {
    "file_name": "photo.jpg",
    "file_type": "image/jpeg",
    "file_size": len(file_bytes)
}

# Формируем пакет
metadata_bytes = json.dumps(metadata).encode('utf-8')
separator = b"|||BINARY_DATA|||"
packet = metadata_bytes + separator + file_bytes

# Отправляем
await websocket.send(packet)
```

**Ограничения:**
- Максимальный размер файла: **50 МБ**
- Если файл больше → ошибка, соединение не закроется

---

### Получение ФАЙЛА:

**Формат:** Бинарные данные

**Структура:**
```
[МЕТАДАННЫЕ В JSON] + [РАЗДЕЛИТЕЛЬ] + [БИНАРНЫЕ ДАННЫЕ ФАЙЛА]
```

**Метаданные:**
```json
{
  "type": "file",
  "file_name": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 12345,
  "sender_id": "alice"
}
```

**Пример обработки в Python:**
```python
# Получаем данные
data = await websocket.recv()

# Разделяем
separator = b"|||BINARY_DATA|||"
separator_index = data.find(separator)

# Извлекаем части
metadata_bytes = data[:separator_index]
file_data = data[separator_index + len(separator):]

# Парсим метаданные
metadata = json.loads(metadata_bytes.decode('utf-8'))

# Сохраняем файл
with open(metadata['file_name'], 'wb') as f:
    f.write(file_data)
```

---

## NewChatConsumer - Новый чат

### URL подключения:
```
ws://localhost:8000/ws/new_chat/{TOKEN}/
```

Где `{TOKEN}` — токен, полученный от DataConsumer для `new_chat`.

### Назначение:
Создание нового чата и работа с ним.

---

### Отличия от ChatConsumer:

1. **При подключении создаются записи в БД:**
   - Первая запись: `user_id=alice, guest_id=bob, room=room123`
   - Вторая запись: `user_id=bob, guest_id=alice, room=room123`

2. **Используется только ОДИН РАЗ** при создании чата

3. **При следующем подключении** к этому же чату используй `ChatConsumer`

---

### Работа с сообщениями:

**Полностью идентична ChatConsumer:**

- Отправка текста: `{"message": "..."}`
- Отправка файлов: метаданные + разделитель + данные
- Получение: такие же форматы

---

## YourConsumer - Echo сервер

### URL подключения:
```
ws://localhost:8000/ws/echo/
```

### Назначение:
Простой echo-сервер для тестирования WebSocket.

---

### Работа:

#### Отправить:
```json
{
  "message": "Hello, World!"
}
```

#### Получить обратно:
```json
{
  "message": "Hello, World!"
}
```

**Особенности:**
- Не требует аутентификации
- Не сохраняет сообщения
- Просто отправляет обратно то, что получил
- Полезен для проверки работоспособности WebSocket

---

## GroupChatConsumer - Групповой чат

### URL подключения:
```
ws://localhost:8000/ws/group/{ROOM_NAME}/
```

Где `{ROOM_NAME}` — название комнаты.

### Назначение:
Групповой публичный чат без аутентификации.

---

### Особенности:

- ✅ Не требует токена
- ✅ Любой может подключиться к любой комнате
- ✅ Неограниченное количество участников
- ❌ Нет сохранения в базу данных
- ❌ Нет информации об отправителе

---

### Отправка сообщения:

```json
{
  "message": "Всем привет!"
}
```

### Получение сообщения:

```json
{
  "message": "Всем привет!"
}
```

**Обратите внимание:**
- Нет поля `sender_id`
- Нет поля `type`
- Только `message`

---

### Пример: 3 пользователя в группе "python-room"

**User1 подключается:**
```
CONNECT ws://localhost:8000/ws/group/python-room/
```

**User2 подключается:**
```
CONNECT ws://localhost:8000/ws/group/python-room/
```

**User3 подключается:**
```
CONNECT ws://localhost:8000/ws/group/python-room/
```

**User1 отправляет:**
```json
{"message": "Привет всем!"}
```

**Все три получают:**
```json
{"message": "Привет всем!"}
```

---

## Форматы данных

### Текстовое сообщение (JSON)

**Отправка:**
```json
{
  "message": "текст"
}
```

**Получение (ChatConsumer/NewChatConsumer):**
```json
{
  "type": "message",
  "message": "текст",
  "sender_id": "user_id"
}
```

**Получение (GroupChatConsumer):**
```json
{
  "message": "текст"
}
```

**Получение (YourConsumer/Echo):**
```json
{
  "message": "текст"
}
```

---

### Файл (Binary)

**Структура пакета:**
```
┌─────────────────────────────────────────────────────────┐
│  Метаданные (JSON в UTF-8)                              │
├─────────────────────────────────────────────────────────┤
│  Разделитель: |||BINARY_DATA||| (17 байт)              │
├─────────────────────────────────────────────────────────┤
│  Бинарные данные файла                                  │
└─────────────────────────────────────────────────────────┘
```

**Метаданные при отправке:**
```json
{
  "file_name": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 12345
}
```

**Метаданные при получении:**
```json
{
  "type": "file",
  "file_name": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 12345,
  "sender_id": "alice"
}
```

---

### Разделитель

**В байтах:**
```python
separator = b"|||BINARY_DATA|||"
```

**Длина:** 17 байт

**Кодировка:** ASCII (одинакова в UTF-8)

---

## Коды закрытия WebSocket

| Код | Где используется | Значение |
|-----|------------------|----------|
| `1000` | Все | Нормальное закрытие |
| `4001` | DataConsumer | Ошибка аутентификации / нет прав доступа |
| `4002` | ChatConsumer, NewChatConsumer | Невалидный токен сессии |

---

## Примеры последовательностей

### Пример 1: Полный цикл создания нового чата

```
1. CONNECT ws://localhost:8000/ws/auth/

2. SEND →
   {
     "room": "room-abc-123",
     "user_id": "alice",
     "guest_id": "bob",
     "status_chat": "new_chat",
     "token": "token-xyz-789"
   }

3. RECEIVE ←
   {
     "action": "connect_to_chat",
     "status": "success"
   }

4. DISCONNECT (автоматически)

5. CONNECT ws://localhost:8000/ws/new_chat/token-xyz-789/

6. SEND →
   {
     "message": "Привет, Bob!"
   }

7. RECEIVE ←
   {
     "type": "message",
     "message": "Привет, Bob!",
     "sender_id": "alice"
   }

8. DISCONNECT
```

---

### Пример 2: Отправка файла

```
1. [Аутентификация - пропущено]

2. CONNECT ws://localhost:8000/ws/chat/token/

3. Формируем пакет:
   metadata = {"file_name": "image.png", "file_type": "image/png", "file_size": 5000}
   metadata_bytes = json.dumps(metadata).encode('utf-8')
   separator = b"|||BINARY_DATA|||"
   file_bytes = [байты файла]
   packet = metadata_bytes + separator + file_bytes

4. SEND → packet (как бинарные данные)

5. RECEIVE ← (бинарные данные)
   
6. Разбираем ответ:
   separator_index = data.find(b"|||BINARY_DATA|||")
   metadata = json.loads(data[:separator_index].decode('utf-8'))
   file_data = data[separator_index + 17:]
```

---

### Пример 3: Два пользователя общаются

```
ALICE:
1. CONNECT ws://localhost:8000/ws/auth/
2. SEND {"room":"room1", "user_id":"alice", "guest_id":"bob", "status_chat":"new_chat", "token":"token-a"}
3. RECEIVE {"status":"success"}
4. DISCONNECT
5. CONNECT ws://localhost:8000/ws/new_chat/token-a/

BOB (через несколько секунд):
1. CONNECT ws://localhost:8000/ws/auth/
2. SEND {"room":"room1", "user_id":"bob", "guest_id":"alice", "status_chat":"existing_chat", "token":"token-b"}
3. RECEIVE {"status":"success"}
4. DISCONNECT
5. CONNECT ws://localhost:8000/ws/chat/token-b/

ALICE:
6. SEND {"message": "Привет, Bob!"}

BOB:
7. RECEIVE {"type":"message", "message":"Привет, Bob!", "sender_id":"alice"}

BOB:
8. SEND {"message": "Привет, Alice!"}

ALICE:
9. RECEIVE {"type":"message", "message":"Привет, Alice!", "sender_id":"bob"}
```

---

## Важные моменты

### ⚠️ Токены одноразовые
- Токен можно использовать ТОЛЬКО ОДИН РАЗ
- После подключения к ChatConsumer/NewChatConsumer токен удаляется из Redis
- Для повторного подключения нужен новый токен

### ⚠️ Время жизни токена
- Токен живёт 5 минут (300 секунд)
- Если не подключиться за это время — токен истекает

### ⚠️ Регистр важен
- `"new_chat"` ≠ `"New_Chat"` ≠ `"NEW_CHAT"`
- Используй точно `"new_chat"` или `"existing_chat"`

### ⚠️ Проверка прав
- Для `existing_chat` должна быть запись в БД
- Для `new_chat` комната НЕ должна существовать

### ⚠️ Максимальный размер файла
- 50 МБ (52,428,800 байт)
- При превышении — ошибка, но соединение не закрывается

---

## Генерация ID и токенов

### Рекомендации:

**Room ID:**
- Используй UUID v4: `550e8400-e29b-41d4-a716-446655440000`
- Или любую уникальную строку

**Token:**
- Используй UUID v4: `f47ac10b-58cc-4372-a567-0e02b2c3d479`
- Длина не ограничена, но рекомендуется UUID

**Примеры генерации:**

Python:
```python
import uuid
room_id = str(uuid.uuid4())
token = str(uuid.uuid4())
```

JavaScript:
```javascript
function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

const roomId = uuidv4();
const token = uuidv4();
```

---

**Всё!** Это вся информация, которая нужна для работы с твоими consumer'ами. 🚀
