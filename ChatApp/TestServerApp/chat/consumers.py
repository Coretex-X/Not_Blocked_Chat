from channels.generic.websocket import AsyncWebsocketConsumer
from .models import UserData, DataMessage
from datetime import datetime
import json
import base64
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

redis_pool = ConnectionPool.from_url(
    'redis://localhost:6379/0',
    max_connections=100,
    decode_responses=True,
    socket_keepalive=True
)
redis_client = Redis(connection_pool=redis_pool)


#Базовый наследуемый класс
class BaseChatConsumer(AsyncWebsocketConsumer):
    @sync_to_async
    def save_message_to_db(self, user_id, guest_id, room, message_text, is_user_message=True):
        try:
            sender = str(user_id) if is_user_message else str(guest_id)
            receiver = str(guest_id) if is_user_message else str(user_id)
            
            DataMessage.objects.create(
                sender_id=sender,
                receiver_id=receiver,
                room=str(room),
                message_text=message_text
            )
            
            logger.info(f"Message saved: {sender} -> {receiver} in room {room}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving message to DB: {e}", exc_info=True)
            return False
    
    async def validate_token_and_get_session(self, token_session, session_type):
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
    
    async def handle_text_message(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message", "").strip()
            
            if not message:
                logger.warning("Empty message received, ignoring")
                return False
            
            await self.save_message_to_db(
                user_id=self.user_id,
                guest_id=self.guest_id,
                room=self.room_name,
                message_text=message,
                is_user_message=True
            )
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": message,
                    "sender_id": self.user_id
                }
            )
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in text message: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)
            return False
    
    async def handle_binary_data(self, bytes_data):
        try:
            separator = b"|||BINARY_DATA|||"
            separator_index = bytes_data.find(separator)
            
            if separator_index == -1:
                logger.error("Invalid binary data format: separator not found")
                return False
            
            metadata_bytes = bytes_data[:separator_index]
            file_data = bytes_data[separator_index + len(separator):]
            
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            file_name = metadata.get("file_name", "unknown")
            file_type = metadata.get("file_type", "application/octet-stream")
            file_size = metadata.get("file_size", len(file_data))
            
            MAX_FILE_SIZE = 50 * 1024 * 1024
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")
                await self.send(text_data=json.dumps({
                    "error": "File too large",
                    "max_size": MAX_FILE_SIZE
                }))
                return False
            
            logger.info(f"Received file: {file_name} ({file_type}, {file_size} bytes) from user {self.user_id}")
            
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.file",
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "file_data": file_data_base64,
                    "sender_id": self.user_id
                }
            )
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file metadata: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error processing binary data: {e}", exc_info=True)
            return False
    
    async def chat_message(self, event):
        message = event.get("message", "")
        sender_id = event.get("sender_id")
        
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": message,
            "sender_id": sender_id
        }, ensure_ascii=False))
    
    async def chat_file(self, event):
        file_name = event.get("file_name")
        file_type = event.get("file_type")
        file_size = event.get("file_size")
        file_data_base64 = event.get("file_data")
        sender_id = event.get("sender_id")
        
        file_data = base64.b64decode(file_data_base64)
        
        metadata = json.dumps({
            "type": "file",
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "sender_id": sender_id
        }).encode('utf-8')
        
        separator = b"|||BINARY_DATA|||"
        await self.send(bytes_data=metadata + separator + file_data)



#класс для проверки доступа пользователя к чату и создания сессии в Redis
class DataConsumer(AsyncWebsocketConsumer):
    
    @sync_to_async
    def check_access(self, id_user, guest_id, room_chat, status_chat):
        try:
            if status_chat == "existing_chat":
                user_exists = UserData.objects.filter(
                    user_id=str(id_user),
                    guest_id=str(guest_id),
                    room=str(room_chat)
                ).exists()
                return user_exists
                
            elif status_chat == "new_chat":
                room_exists = UserData.objects.filter(room=str(room_chat)).exists()
                return not room_exists
                
        except Exception as e:
            logger.error(f"Error in check_access: {e}", exc_info=True)
            return False
    
    async def connect(self):
        await self.accept()
        logger.info(f"Auth connection accepted: {self.channel_name}")
    
    async def disconnect(self, close_code):
        logger.info(f"Auth connection closed: {self.channel_name}, code: {close_code}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            room_chat = data.get("room")
            id_user = data.get("user_id")
            guest_id = data.get("guest_id")
            status_chat = data.get("status_chat")
            token = data.get("token")
            
            if not all([room_chat, token, status_chat]):
                logger.warning("Missing required fields in auth data")
                await self.close(code=4001)
                return
            
            if status_chat == "new_chat":
                has_access = await self.check_access(
                    id_user=None,
                    guest_id=None,
                    room_chat=room_chat,
                    status_chat="new_chat"
                )
                
                if not has_access:
                    logger.warning(f"Room already exists: {room_chat}")
                    await self.close(code=4001)
                    return
                
                await redis_client.setex(
                    f"session:new_chat:{token}",
                    300,
                    json.dumps({
                        "room": room_chat,
                        "user_id": id_user,
                        "guest_id": guest_id,
                        "token": token
                    })
                )
                
                logger.info(f"New chat session created: {token}")
                
            elif status_chat == "existing_chat":
                has_access = await self.check_access(
                    id_user=id_user,
                    guest_id=guest_id,
                    room_chat=room_chat,
                    status_chat="existing_chat"
                )
                
                if not has_access:
                    logger.warning(f"Access denied for user {id_user} to room {room_chat}")
                    await self.close(code=4001)
                    return
                
                await redis_client.setex(
                    f"session:existing_chat:{token}",
                    300,
                    json.dumps({
                        "room": room_chat,
                        "user_id": id_user,
                        "guest_id": guest_id,
                        "token": token
                    })
                )
                
                logger.info(f"Existing chat session created: {token}")
            
            await self.send(json.dumps({
                "action": "connect_to_chat",
                "status": "success"
            }))
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in auth data: {e}", exc_info=True)
            await self.close(code=4001)
        except Exception as e:
            logger.error(f"Error in auth receive: {e}", exc_info=True)
            await self.close(code=4001)
        finally:
            await self.close()


#класс для обработки сообщений в приватных чатах
class ChatConsumer(BaseChatConsumer):
    async def connect(self):
        token_session = self.scope["url_route"]["kwargs"]["room_name"]
        
        session_data = await self.validate_token_and_get_session(token_session, "existing_chat")
        
        if session_data is None:
            logger.warning(f"Invalid session for existing chat: {token_session}")
            await self.close(code=4002)
            return
        
        self.room_name = session_data["room"]
        self.user_id = session_data["user_id"]
        self.guest_id = session_data["guest_id"]
        self.room_group_name = f"chat_{self.room_name}"
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        logger.info(f"User {self.user_id} connected to existing chat {self.room_name}")
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"User {self.user_id} disconnected from chat {self.room_name}")
    
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self.handle_text_message(text_data)
        elif bytes_data:
            await self.handle_binary_data(bytes_data)



#класс для создания нового чата и добавления в БД информации о нем, а также для обработки сообщений в новом чате
class NewChatConsumer(BaseChatConsumer):
    @sync_to_async
    def add_chat(self, user_id, guest_id, room_id):
        try:
            UserData.objects.create(
                user_id=str(user_id),
                guest_id=str(guest_id),
                room=str(room_id),
                count=2,
                groups="default"
            )
            logger.info(f"Chat record created: {user_id} <-> {guest_id} in room {room_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding chat connection: {e}", exc_info=True)
            return False
    
    async def connect(self):
        token_session = self.scope["url_route"]["kwargs"]["room_name"]
        
        session_data = await self.validate_token_and_get_session(token_session, "new_chat")
        
        if session_data is None:
            logger.warning(f"Invalid session for new chat: {token_session}")
            await self.close(code=4002)
            return
        
        self.room_name = session_data["room"]
        self.user_id = session_data["user_id"]
        self.guest_id = session_data["guest_id"]
        self.room_group_name = f"chat_{self.room_name}"
        
        await self.add_chat(self.user_id, self.guest_id, self.room_name)
        await self.add_chat(self.guest_id, self.user_id, self.room_name)
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        logger.info(f"User {self.user_id} created new chat {self.room_name} with {self.guest_id}")
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"User {self.user_id} disconnected from new chat {self.room_name}")
    
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self.handle_text_message(text_data)
        elif bytes_data:
            await self.handle_binary_data(bytes_data)


class YourConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        await self.accept()
        logger.info(f"Echo connection accepted: {self.channel_name}")
    
    async def disconnect(self, close_code):
        logger.info(f"Echo connection closed: {self.channel_name}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message", "")
            
            await self.send(text_data=json.dumps({
                "message": message,
            }))
            
        except Exception as e:
            logger.error(f"Error in echo consumer: {e}", exc_info=True)






class GroupDataConsumer(AsyncWebsocketConsumer):
    @sync_to_async
    def check_group_access(self, user_id, group_id, action):
        try:
            from .models import GroupData, GroupMember
            
            if action == "create_group":
                group_exists = GroupData.objects.filter(group_id=str(group_id)).exists()
                return not group_exists
            
            elif action == "join_group":
                try:
                    group = GroupData.objects.get(group_id=str(group_id))
                    is_member = GroupMember.objects.filter(
                        group_id=str(group_id),
                        user_id=str(user_id)
                    ).exists()
                    return is_member
                except GroupData.DoesNotExist:
                    logger.error(f"Group {group_id} does not exist")
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
            action = data.get("action")
            token = data.get("token")
            group_name = data.get("group_name", "Unnamed Group")
            group_description = data.get("group_description", "")
            member_ids = data.get("member_ids", [])
            if not all([group_id, user_id, action, token]):
                logger.warning("Missing required fields in group auth data")
                await self.close(code=4001)
                return
            if action not in ["create_group", "join_group"]:
                logger.warning(f"Invalid action: {action}")
                await self.close(code=4001)
                return
            if action == "create_group":
                if not group_name:
                    logger.warning("Group name is required for create_group")
                    await self.close(code=4001)
                    return
                if not member_ids or user_id not in member_ids:
                    if user_id not in member_ids:
                        member_ids.append(user_id)
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
            session_data = {
                "group_id": group_id,
                "user_id": user_id,
                "action": action,
                "token": token
            }
            if action == "create_group":
                session_data["group_name"] = group_name
                session_data["group_description"] = group_description
                session_data["member_ids"] = member_ids
            await redis_client.setex(
                f"session:group:{action}:{token}",
                300,
                json.dumps(session_data)
            )
            
            logger.info(f"Group session created: {action} for group {group_id}")
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

class GroupChatConsumer(BaseChatConsumer):
    @sync_to_async
    def create_group_with_members(self, group_id, group_name, group_description, creator_id, member_ids):
        try:
            from .models import GroupData, GroupMember
            group = GroupData.objects.create(
                group_id=str(group_id),
                name=group_name,
                description=group_description,
                created_by=str(creator_id)
            )
            GroupMember.objects.create(
                group_id=str(group_id),
                user_id=str(creator_id),
                role='admin'
            )
            for member_id in member_ids:
                if str(member_id) != str(creator_id):
                    GroupMember.objects.create(
                        group_id=str(group_id),
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
        try:
            from .models import GroupMessage
            
            GroupMessage.objects.create(
                group_id=str(group_id),
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
        session_data = await self.validate_token_and_get_session(
            token_session, 
            "group:create_group"
        )
        if session_data is None:
            session_data = await self.validate_token_and_get_session(
                token_session, 
                "group:join_group"
            )
        if session_data is None:
            logger.warning(f"Invalid session for group chat: {token_session}")
            await self.close(code=4002)
            return
        self.group_id = session_data["group_id"]
        self.user_id = session_data["user_id"]
        self.action = session_data["action"]
        self.room_group_name = f"group_chat_{self.group_id}"
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
        try:
            data = json.loads(text_data)
            message = data.get("message", "").strip()
            if not message:
                logger.warning("Empty group message received")
                return False
            await self.save_group_message(
                group_id=self.group_id,
                user_id=self.user_id,
                message_text=message
            )
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
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in group text message: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error handling group text message: {e}", exc_info=True)
            return False
    
    async def handle_group_binary_data(self, bytes_data):
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
            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"Group file too large: {file_size}")
                await self.send(text_data=json.dumps({
                    "error": "File too large",
                    "max_size": MAX_FILE_SIZE
                }))
                return False
            logger.info(f"Group file received: {file_name} from {self.user_id}")
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
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
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in group file metadata: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error processing group binary data: {e}", exc_info=True)
            return False
    async def group_message(self, event):
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

class NotificationConsumer(AsyncWebsocketConsumer):
    pass

async def broadcast_user_status(user_id, status, room_ids):
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    
    for room_id in room_ids:
        room_group_name = f"chat_{room_id}"
        await channel_layer.group_send(
            room_group_name,
            {
                "type": "user.status",
                "user_id": user_id,
                "status": status
            }
        )
    
    logger.info(f"User {user_id} status broadcasted: {status}")