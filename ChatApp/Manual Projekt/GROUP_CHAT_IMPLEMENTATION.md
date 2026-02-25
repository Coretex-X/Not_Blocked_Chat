# Добавление групповых чатов в твои consumer'ы

## Оглавление
1. [Что нужно сделать](#что-нужно-сделать)
2. [Изменения в моделях](#изменения-в-моделях)
3. [Новые consumer'ы](#новые-consumerы)
4. [Изменения в BaseChatConsumer](#изменения-в-basechatconsumer)
5. [URL routing](#url-routing)
6. [API документация](#api-документация)

---

## Что нужно сделать

Для добавления групповых чатов нужно:

1. ✅ Создать новую модель для групповых чатов
2. ✅ Добавить модель для участников группы
3. ✅ Создать `GroupDataConsumer` для аутентификации
4. ✅ Создать `GroupChatConsumer` для работы с группами
5. ✅ Расширить `BaseChatConsumer` для поддержки групп
6. ✅ Добавить маршруты в `routing.py`

---

## Изменения в моделях

### 1. Создай новый файл `models.py` или добавь в существующий:

```python
# models.py

from django.db import models

# Твои существующие модели (UserData, DataMessage)
# ...

# НОВЫЕ МОДЕЛИ ДЛЯ ГРУППОВЫХ ЧАТОВ:

class GroupChat(models.Model):
    """
    Модель для групповых чатов
    """
    group_id = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)  # Название группы
    description = models.TextField(blank=True, null=True)  # Описание
    created_by = models.CharField(max_length=255)  # ID создателя
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'group_chats'
        indexes = [
            models.Index(fields=['group_id']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"Group: {self.name} ({self.group_id})"


class GroupMember(models.Model):
    """
    Модель для участников групповых чатов
    """
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='members')
    user_id = models.CharField(max_length=255, db_index=True)
    role = models.CharField(
        max_length=50, 
        choices=[
            ('admin', 'Администратор'),
            ('member', 'Участник')
        ],
        default='member'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_members'
        unique_together = ('group', 'user_id')  # Один пользователь один раз в группе
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['group', 'user_id']),
        ]
    
    def __str__(self):
        return f"{self.user_id} in {self.group.name}"


class GroupMessage(models.Model):
    """
    Модель для сообщений в групповых чатах
    """
    group = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.CharField(max_length=255, db_index=True)
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_messages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['sender_id']),
        ]
    
    def __str__(self):
        return f"{self.sender_id}: {self.message_text[:50]}"
```

### 2. Создай и примени миграции:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Новые consumer'ы

### 1. Добавь `GroupDataConsumer` для аутентификации:

```python
# Добавь в consumers.py

class GroupDataConsumer(AsyncWebsocketConsumer):
    """
    Consumer для аутентификации в групповых чатах
    """
    
    @sync_to_async
    def check_group_access(self, user_id, group_id, action):
        """
        Проверка прав доступа к групповому чату
        
        Args:
            user_id: ID пользователя
            group_id: ID группы
            action: 'join_group' или 'create_group'
        """
        try:
            from .models import GroupChat, GroupMember
            
            if action == "create_group":
                # Проверяем, что группы с таким ID не существует
                group_exists = GroupChat.objects.filter(group_id=str(group_id)).exists()
                return not group_exists
            
            elif action == "join_group":
                # Проверяем, что группа существует
                try:
                    group = GroupChat.objects.get(group_id=str(group_id))
                    
                    # Проверяем, что пользователь является участником
                    is_member = GroupMember.objects.filter(
                        group=group,
                        user_id=str(user_id)
                    ).exists()
                    
                    return is_member
                except GroupChat.DoesNotExist:
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in check_group_access: {e}", exc_info=True)
            return False
    
    async def connect(self):
        await self.accept()
        logger.info(f"Group auth connection accepted: {self.channel_name}")
    
    async def disconnect(self, close_code):
        logger.info(f"Group auth connection closed: {self.channel_name}, code: {close_code}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            group_id = data.get("group_id")
            user_id = data.get("user_id")
            action = data.get("action")  # "create_group" или "join_group"
            token = data.get("token")
            
            # Дополнительные данные для создания группы
            group_name = data.get("group_name")
            group_description = data.get("group_description", "")
            member_ids = data.get("member_ids", [])  # Список ID участников
            
            # Проверяем обязательные поля
            if not all([group_id, user_id, action, token]):
                logger.warning("Missing required fields in group auth data")
                await self.close(code=4001)
                return
            
            # Проверяем тип действия
            if action not in ["create_group", "join_group"]:
                logger.warning(f"Invalid action: {action}")
                await self.close(code=4001)
                return
            
            # Проверяем права доступа
            has_access = await self.check_group_access(
                user_id=user_id,
                group_id=group_id,
                action=action
            )
            
            if not has_access:
                if action == "create_group":
                    logger.warning(f"Group already exists: {group_id}")
                else:
                    logger.warning(f"User {user_id} not a member of group {group_id}")
                await self.close(code=4001)
                return
            
            # Создаём сессию в Redis
            session_data = {
                "group_id": group_id,
                "user_id": user_id,
                "action": action,
                "token": token
            }
            
            # Для создания группы добавляем дополнительные данные
            if action == "create_group":
                session_data["group_name"] = group_name
                session_data["group_description"] = group_description
                session_data["member_ids"] = member_ids
            
            await redis_client.setex(
                f"session:group:{action}:{token}",
                300,  # 5 минут
                json.dumps(session_data)
            )
            
            logger.info(f"Group session created: {action} for group {group_id}")
            
            # Отправляем подтверждение
            await self.send(json.dumps({
                "action": "connect_to_group",
                "status": "success"
            }))
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in group auth data: {e}", exc_info=True)
            await self.close(code=4001)
        except Exception as e:
            logger.error(f"Error in group auth receive: {e}", exc_info=True)
            await self.close(code=4001)
        finally:
            await self.close()
```

---

### 2. Добавь `GroupChatConsumer` для работы с группами:

```python
# Добавь в consumers.py

class GroupChatConsumer(BaseChatConsumer):
    """
    Consumer для работы с групповыми чатами
    """
    
    @sync_to_async
    def create_group_with_members(self, group_id, group_name, group_description, creator_id, member_ids):
        """
        Создание группы и добавление участников
        """
        try:
            from .models import GroupChat, GroupMember
            
            # Создаём группу
            group = GroupChat.objects.create(
                group_id=str(group_id),
                name=group_name,
                description=group_description,
                created_by=str(creator_id)
            )
            
            # Добавляем создателя как администратора
            GroupMember.objects.create(
                group=group,
                user_id=str(creator_id),
                role='admin'
            )
            
            # Добавляем остальных участников
            for member_id in member_ids:
                if str(member_id) != str(creator_id):  # Не дублируем создателя
                    GroupMember.objects.create(
                        group=group,
                        user_id=str(member_id),
                        role='member'
                    )
            
            logger.info(f"Group created: {group_name} ({group_id}) with {len(member_ids)} members")
            return True
            
        except Exception as e:
            logger.error(f"Error creating group: {e}", exc_info=True)
            return False
    
    @sync_to_async
    def save_group_message(self, group_id, user_id, message_text):
        """
        Сохранение сообщения в групповой чат
        """
        try:
            from .models import GroupChat, GroupMessage
            
            group = GroupChat.objects.get(group_id=str(group_id))
            
            GroupMessage.objects.create(
                group=group,
                sender_id=str(user_id),
                message_text=message_text
            )
            
            logger.info(f"Group message saved: {user_id} in {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving group message: {e}", exc_info=True)
            return False
    
    async def connect(self):
        token_session = self.scope["url_route"]["kwargs"]["room_name"]
        
        # Пробуем оба типа сессий
        session_data = await self.validate_token_and_get_session(token_session, "group:create_group")
        
        if session_data is None:
            session_data = await self.validate_token_and_get_session(token_session, "group:join_group")
        
        if session_data is None:
            logger.warning(f"Invalid session for group chat: {token_session}")
            await self.close(code=4002)
            return
        
        self.group_id = session_data["group_id"]
        self.user_id = session_data["user_id"]
        self.action = session_data["action"]
        self.room_group_name = f"group_chat_{self.group_id}"
        
        # Если это создание группы - создаём группу в БД
        if self.action == "create_group":
            group_name = session_data.get("group_name", "Unnamed Group")
            group_description = session_data.get("group_description", "")
            member_ids = session_data.get("member_ids", [])
            
            success = await self.create_group_with_members(
                group_id=self.group_id,
                group_name=group_name,
                group_description=group_description,
                creator_id=self.user_id,
                member_ids=member_ids
            )
            
            if not success:
                logger.error(f"Failed to create group {self.group_id}")
                await self.close(code=4003)
                return
        
        # Добавляем в группу
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        logger.info(f"User {self.user_id} connected to group {self.group_id}")
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"User {self.user_id} disconnected from group {self.group_id}")
    
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self.handle_group_text_message(text_data)
        elif bytes_data:
            await self.handle_group_binary_data(bytes_data)
    
    async def handle_group_text_message(self, text_data):
        """
        Обработка текстового сообщения в группе
        """
        try:
            data = json.loads(text_data)
            message = data.get("message", "").strip()
            
            if not message:
                logger.warning("Empty group message received")
                return False
            
            # Сохраняем в БД
            await self.save_group_message(
                group_id=self.group_id,
                user_id=self.user_id,
                message_text=message
            )
            
            # Рассылаем всем участникам
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "group.message",
                    "message": message,
                    "sender_id": self.user_id,
                    "group_id": self.group_id
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling group text message: {e}", exc_info=True)
            return False
    
    async def handle_group_binary_data(self, bytes_data):
        """
        Обработка файлов в группе (аналогично приватному чату)
        """
        try:
            separator = b"|||BINARY_DATA|||"
            separator_index = bytes_data.find(separator)
            
            if separator_index == -1:
                logger.error("Invalid binary data format in group")
                return False
            
            metadata_bytes = bytes_data[:separator_index]
            file_data = bytes_data[separator_index + len(separator):]
            
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            file_name = metadata.get("file_name", "unknown")
            file_type = metadata.get("file_type", "application/octet-stream")
            file_size = metadata.get("file_size", len(file_data))
            
            MAX_FILE_SIZE = 50 * 1024 * 1024
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"Group file too large: {file_size}")
                await self.send(text_data=json.dumps({
                    "error": "File too large",
                    "max_size": MAX_FILE_SIZE
                }))
                return False
            
            logger.info(f"Group file received: {file_name} from {self.user_id}")
            
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Рассылаем всем участникам группы
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "group.file",
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "file_data": file_data_base64,
                    "sender_id": self.user_id,
                    "group_id": self.group_id
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing group binary data: {e}", exc_info=True)
            return False
    
    async def group_message(self, event):
        """
        Обработчик для текстовых сообщений в группе
        """
        message = event.get("message", "")
        sender_id = event.get("sender_id")
        group_id = event.get("group_id")
        
        await self.send(text_data=json.dumps({
            "type": "group_message",
            "message": message,
            "sender_id": sender_id,
            "group_id": group_id
        }, ensure_ascii=False))
    
    async def group_file(self, event):
        """
        Обработчик для файлов в группе
        """
        file_name = event.get("file_name")
        file_type = event.get("file_type")
        file_size = event.get("file_size")
        file_data_base64 = event.get("file_data")
        sender_id = event.get("sender_id")
        group_id = event.get("group_id")
        
        file_data = base64.b64decode(file_data_base64)
        
        metadata = json.dumps({
            "type": "group_file",
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "sender_id": sender_id,
            "group_id": group_id
        }).encode('utf-8')
        
        separator = b"|||BINARY_DATA|||"
        await self.send(bytes_data=metadata + separator + file_data)
```

---

## Изменения в BaseChatConsumer

Если хочешь использовать `BaseChatConsumer` для групп, добавь метод:

```python
# В класс BaseChatConsumer добавь:

async def validate_token_and_get_session(self, token_session, session_type):
    """
    Расширенная версия для поддержки групповых сессий
    """
    try:
        session_data = await redis_client.get(f"session:{session_type}:{token_session}")
        
        if session_data is None:
            logger.warning(f"Session not found or expired: {session_type}:{token_session}")
            return None
        
        data = json.loads(session_data)
        token = data.get("token")
        
        if token != token_session:
            logger.warning(f"Token mismatch: expected {token}, got {token_session}")
            return None
        
        await redis_client.delete(f"session:{session_type}:{token_session}")
        
        logger.info(f"Session validated and deleted: {session_type}:{token_session}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in session data: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error validating token: {e}", exc_info=True)
        raise
```

Этот метод уже есть в твоём коде, просто он теперь поддерживает и групповые сессии!

---

## URL routing

Добавь в `routing.py`:

```python
# routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Существующие маршруты
    re_path(r'ws/auth/$', consumers.DataConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/new_chat/(?P<room_name>[^/]+)/$', consumers.NewChatConsumer.as_asgi()),
    re_path(r'ws/echo/$', consumers.YourConsumer.as_asgi()),
    re_path(r'ws/group/(?P<room_name>[^/]+)/$', consumers.GroupChatConsumer.as_asgi()),
    
    # НОВЫЕ МАРШРУТЫ ДЛЯ ГРУППОВЫХ ЧАТОВ:
    re_path(r'ws/group-auth/$', consumers.GroupDataConsumer.as_asgi()),
    re_path(r'ws/group-chat/(?P<room_name>[^/]+)/$', consumers.GroupChatConsumer.as_asgi()),
]
```

---

## API документация

### Создание группового чата

#### 1. Аутентификация для создания группы

**URL:** `ws://localhost:8000/ws/group-auth/`

**Отправить:**
```json
{
  "group_id": "unique-group-id",
  "user_id": "creator-user-id",
  "action": "create_group",
  "token": "unique-session-token",
  "group_name": "Название группы",
  "group_description": "Описание группы",
  "member_ids": ["user1", "user2", "user3"]
}
```

**Получить:**
```json
{
  "action": "connect_to_group",
  "status": "success"
}
```

#### 2. Подключение к групповому чату

**URL:** `ws://localhost:8000/ws/group-chat/{TOKEN}/`

**Отправить текст:**
```json
{
  "message": "Привет всем в группе!"
}
```

**Получить:**
```json
{
  "type": "group_message",
  "message": "Привет всем в группе!",
  "sender_id": "user1",
  "group_id": "group-123"
}
```

**Отправить файл:**
Формат такой же как в приватных чатах:
```
[Метаданные JSON] + |||BINARY_DATA||| + [Байты файла]
```

**Получить файл:**
```json
{
  "type": "group_file",
  "file_name": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 12345,
  "sender_id": "user1",
  "group_id": "group-123"
}
+ разделитель + файл
```

---

### Подключение к существующей группе

#### 1. Аутентификация для присоединения

**URL:** `ws://localhost:8000/ws/group-auth/`

**Отправить:**
```json
{
  "group_id": "existing-group-id",
  "user_id": "your-user-id",
  "action": "join_group",
  "token": "unique-session-token"
}
```

**Получить:**
```json
{
  "action": "connect_to_group",
  "status": "success"
}
```

Если пользователь не является участником группы → код 4001

#### 2. Подключение к чату

**URL:** `ws://localhost:8000/ws/group-chat/{TOKEN}/`

Работа аналогична созданию группы.

---

## Полный пример использования

### Создание группы с 3 участниками

```
ШАГ 1: Аутентификация
→ CONNECT ws://localhost:8000/ws/group-auth/

→ SEND {
    "group_id": "my-group-123",
    "user_id": "alice",
    "action": "create_group",
    "token": "token-abc",
    "group_name": "Друзья",
    "group_description": "Наша группа друзей",
    "member_ids": ["alice", "bob", "charlie"]
  }

← RECEIVE {
    "action": "connect_to_group",
    "status": "success"
  }

→ DISCONNECT (автоматически)

ШАГ 2: Подключение к группе
→ CONNECT ws://localhost:8000/ws/group-chat/token-abc/

ШАГ 3: Отправка сообщения
→ SEND {
    "message": "Всем привет в новой группе!"
  }

← RECEIVE {
    "type": "group_message",
    "message": "Всем привет в новой группе!",
    "sender_id": "alice",
    "group_id": "my-group-123"
  }
```

### Другой участник подключается

```
ШАГ 1: Bob аутентифицируется
→ CONNECT ws://localhost:8000/ws/group-auth/

→ SEND {
    "group_id": "my-group-123",
    "user_id": "bob",
    "action": "join_group",
    "token": "token-xyz"
  }

← RECEIVE {
    "action": "connect_to_group",
    "status": "success"
  }

ШАГ 2: Bob подключается
→ CONNECT ws://localhost:8000/ws/group-chat/token-xyz/

ШАГ 3: Bob отправляет сообщение
→ SEND {
    "message": "Привет, Alice!"
  }

ШАГ 4: ВСЕ участники получают сообщение
← RECEIVE {
    "type": "group_message",
    "message": "Привет, Alice!",
    "sender_id": "bob",
    "group_id": "my-group-123"
  }
```

---

## Отличия от приватных чатов

| Аспект | Приватный чат | Групповой чат |
|--------|---------------|---------------|
| **Участники** | 2 | Неограниченно |
| **Модель БД** | UserData | GroupChat + GroupMember |
| **Сообщения** | DataMessage | GroupMessage |
| **Аутентификация** | DataConsumer | GroupDataConsumer |
| **Consumer** | ChatConsumer / NewChatConsumer | GroupChatConsumer |
| **URL auth** | /ws/auth/ | /ws/group-auth/ |
| **URL chat** | /ws/chat/{token}/ | /ws/group-chat/{token}/ |
| **Роли** | Нет | admin / member |

---

## Что получилось

✅ Полноценные групповые чаты с аутентификацией  
✅ Поддержка текстовых сообщений  
✅ Поддержка файлов  
✅ Сохранение в базу данных  
✅ Роли участников (admin/member)  
✅ Проверка прав доступа  
✅ Одноразовые токены с TTL  

---

**Готово!** Теперь у тебя есть полноценная система групповых чатов! 🚀
