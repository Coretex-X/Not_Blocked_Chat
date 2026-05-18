from django.contrib.auth.hashers import make_password
from rest_framework.generics import *
from rest_framework.views import *
from rest_framework.exceptions import AuthenticationFailed
from .models import *
from chat.models import UserNotification
from .geniration_token import GuaranteedUniqueTokenGenerator, GuaranteedUniqueRoomGenerator
from .serializer import Serializer
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from django.views.decorators.csrf import csrf_exempt

class RegistrationView(APIView):
    serializer_class = Serializer

    def post(self, request):
        #получаем данные пользовтеля
        response_login = request.data.get('login')
        response_email = request.data.get('email')
        response_number = request.data.get('number')
        response_password = request.data.get('password')

        #Валидация (проверка) данных
        class Validate(BaseModel):
            login:str = Field(min_length=3,max_length=40)
            email:EmailStr = Field(min_length=3,max_length=50)
            number:str = Field(min_length=10, max_length=10)
            password:str = Field(min_length=4,max_length=40)
            model_config=ConfigDict(extra='forbid') 
        Validate(**request.data)

        #Хеширование поролей
        response_password_hash = make_password(response_password)

        #Генерация токена
        geniration = GuaranteedUniqueTokenGenerator()
        token = geniration.generate_token(100)
        #Генерация комнаты
        generator_room = GuaranteedUniqueRoomGenerator()
        room = generator_room.generate_room(110)
        
        #Запись данных в БД
        Models.objects.create(
            login=response_login, 
            email=response_email,
            number=response_number, 
            password=response_password_hash,
            token=token,
            room=room
            )
           
        return Response({"post":status.HTTP_201_CREATED})
        
        
class LoginView(APIView): 
                                                                                             
    def post(self, request):
        #получаем данные пользовтеля                                                                                        
        response_login = request.data.get('login')                                                                  
        response_password = request.data.get('password')

        #Проверка данных
        class Validate(BaseModel):
            login:str=Field(min_length=3,max_length=40)
            password:str=Field(min_length=4,max_length=40)
            model_config=ConfigDict(extra='forbid')
        Validate(**request.data)

        #Проверка пользователя
        try:
            queryset_data_user =  Models.objects.get(login=response_login)
        except Models.DoesNotExist:
            raise AuthenticationFailed({
                'meaning': 'Неверные учетные данные',
                'status': status.HTTP_401_UNAUTHORIZED
            })
        
        #проверка пороли
        if queryset_data_user.check_password(response_password):
            UserNotification.objects.create(
                user_id = queryset_data_user.id,
                room=queryset_data_user.room
            )
            #Если всё верно возврощаем данные пользователя
            return Response({
                'id_users':queryset_data_user.id,
                'login': response_login,
                'number':queryset_data_user.number,
                'token':queryset_data_user.token,
                'profil':queryset_data_user.profil,
                'room':queryset_data_user.room,
                'status': status.HTTP_200_OK
                })
        
        #Если пороль не верный
        raise AuthenticationFailed({
            'meaning': 'Неверные учетные данные',
            'status': status.HTTP_401_UNAUTHORIZED
        })
