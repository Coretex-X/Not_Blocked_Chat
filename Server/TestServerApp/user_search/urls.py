from django.urls import path
from .views import NumberUserView
urlpatterns = [
    #метод as_view используется для привязки класса к маршру URL-адреса 
    path('search_contacts/', NumberUserView.as_view())
]