from django.urls import path, include
from rest_framework import routers
from .views import *

urlpatterns = [
    #метод as_view используется для привязки класса к маршру URL-адреса 
    path('registration/', RegistrationView.as_view()),
    path('login/', LoginView.as_view()),
    path('sesion/', UserStatusAPI.as_view())
]
