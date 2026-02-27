from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path("ws/data/", consumers.DataConsumer.as_asgi()),
    re_path("ws/my_chat/", consumers.YourConsumer.as_asgi()),
    re_path(r"ws/chat_user/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/new_chat_user/(?P<room_name>\w+)/$", consumers.NewChatConsumer.as_asgi()),
    re_path(r"ws/groop_user/(?P<room_name>\w+)/$", consumers.GroupChatConsumer.as_asgi()),
    re_path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),

]