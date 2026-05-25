from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from sign_up.models import Models
from chat.models import UserOff
import logging

logger = logging.getLogger(__name__)


class UserNotification(APIView):
    def post(self, request):
        response_id = request.data.get('id_users')
        response_token = request.data.get('token')

        # Поиск пользователя
        try:
            user = Models.objects.get(pk=response_id)
        except Models.DoesNotExist:
            raise AuthenticationFailed({
                'meaning': 'Пользователь не найден',
                'status': status.HTTP_401_UNAUTHORIZED
            })

        # Проверка токена
        if user.token != response_token:
            raise AuthenticationFailed({
                'meaning': 'Неверный токен',
                'status': status.HTTP_401_UNAUTHORIZED
            })

        # Ищем офлайн-сообщения
        offline_messages = UserOff.objects.filter(message_recipient_ID=str(response_id))

        if not offline_messages.exists():
            return Response({"message": "no message"})

        messages_list = []
        for msg in offline_messages:
            messages_list.append({
                "id_senders": msg.user_id,
                "room": msg.room,
                "message": msg.message,
                "status_chat": msg.status_chat,
                "timestamp": str(msg.timestamp) if hasattr(msg, 'timestamp') else ""
            })

        offline_messages.delete()
        return Response(messages_list)
    


class UserStatusAPI(APIView):
    def post(self, request):
        online = 'online'
        offline = 'offline'
        action = request.data.get('action')
        id_users = request.data.get('id_users')
        
        if action == online:
            Models.objects.filter(pk=id_users).update(status=action)
            return Response({"status": status.HTTP_200_OK})
        
        elif action == offline:
            Models.objects.filter(pk=id_users).update(status=action)
            return Response({"status": status.HTTP_404_NOT_FOUND})