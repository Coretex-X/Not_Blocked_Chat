from sign_up.models import *
from rest_framework.views import *
from .serializer import Serializer
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from pydantic import BaseModel, Field, ConfigDict
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class NumberUserView(APIView):
    serializer_class = Serializer

    def post(self, request):
        #получаем данные пользовтеля
        response_number = request.data.get('number')
        #Валидация (проверка) данных
        class Validate(BaseModel):
            number:str = Field(min_length=10, max_length=10)
            model_config=ConfigDict(extra='forbid') 
        Validate(**request.data)
        try:
            queryset =  Models.objects.get(number=response_number)
        except Models.DoesNotExist:
            raise AuthenticationFailed({
                'meaning': 'Пользователь не найден',
                'status': status.HTTP_401_UNAUTHORIZED
            })
        return Response({
            "id": queryset.pk,
            "login": queryset.login,
            "number": queryset.number,
            "status": queryset.profil,
            "post":status.HTTP_200_OK
            })
    

@method_decorator(csrf_exempt, name='dispatch')
class UserUpdateView(APIView):
    serializer_class = Serializer
    def post(self, request):
        response_id = request.data.get('id')
        response_token = request.data.get('token')
        #User ubdate date
        response_update_login = request.data.get('login')
        response_update_number = request.data.get('number')
        response_update_status = request.data.get('status')

        # 3. Ищем пользователя по id
        try:
            user = Models.objects.get(pk=response_id)
        except Models.DoesNotExist:
            raise AuthenticationFailed({
                'meaning': 'Пользователь не найден',
                'status': status.HTTP_401_UNAUTHORIZED
            })

        # 4. Проверяем токен
        if user.token != response_token:
            raise AuthenticationFailed({
                'meaning': 'Неверный токен',
                'status': status.HTTP_401_UNAUTHORIZED
            })
        
        # 5. Проверяем уникальность логина (кроме текущего пользователя)
        if Models.objects.filter(login=response_update_login).exclude(pk=response_id).exists():
            return Response(
                {'error': '404_Login_already_covered'},
                status=status.HTTP_409_CONFLICT
            )

        # 6. Проверяем уникальность номера (кроме текущего пользователя)
        if Models.objects.filter(number=response_update_number).exclude(pk=response_id).exists():
            return Response(
                {'error':'404_Number_already_covered'},
                status=status.HTTP_409_CONFLICT
            )

        # 7. Обновляем данные
        user.login = response_update_login
        user.number = response_update_number
        user.profil = response_update_status
        user.save()

        return Response({
            "post": status.HTTP_200_OK
        })
    

class DeleteUser(APIView):
    serializer_class = Serializer
    
    def post(self, request):
        response_id = request.data.get('id')
        response_token = request.data.get('token')
        
        # 1. Находим пользователя по id
        try:
            user = Models.objects.get(id=response_id)  # замените UserModel на вашу модель
        except Models.DoesNotExist:
            return Response(
                {"error": "Пользователь с таким id не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 2. Сравниваем токены
        if user.token != response_token:  # предполагаем, что у модели есть поле token
            return Response(
                {"error": "Неверный токен. Доступ запрещен"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        
        user.delete()
        
        # 4. Возвращаем успешный ответ
        return Response(
            status=status.HTTP_200_OK
        )