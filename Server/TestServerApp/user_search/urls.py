from django.urls import path
from .views import NumberUserView, UserUpdateView, DeleteUser
urlpatterns = [
    #метод as_view используется для привязки класса к маршру URL-адреса 
    path('search_contacts/', NumberUserView.as_view()),
    path('update_user_data/', UserUpdateView.as_view()),
    path('delete_user/', DeleteUser.as_view())
]