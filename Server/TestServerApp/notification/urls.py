from django.urls import path
from .views import *

urlpatterns = [
    path('notification/', UserNotification.as_view()),
    path('sesion/', UserStatusAPI.as_view())
]
