from django.urls import path, include
from rest_framework import routers
from .views import *
from .consumers import *


urlpatterns = [
    #метод as_view используется для привязки класса к маршру URL-адреса 
    path('chat/', index),
    path('creat_new_chat/', CreateChat.as_view())
]
