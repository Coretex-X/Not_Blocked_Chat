from django.contrib.auth.hashers import make_password
from rest_framework.generics import *
from rest_framework.views import *
from rest_framework.exceptions import AuthenticationFailed
from .models import *
from .geniration_token import GuaranteedUniqueTokenGenerator
from .serializer import Serializer
from pydantic import BaseModel, EmailStr, Field, ConfigDict

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
            number:str = Field(min_length=6, max_length=12)
            password:str = Field(min_length=4,max_length=40)
            model_config=ConfigDict(extra='forbid') 
        Validate(**request.data)

        #Хеширование поролей
        response_password_hash = make_password(response_password)
        
        #Запись данных в БД
        Models.objects.create(
            login=response_login, 
            email=response_email,
            number=response_number, 
            password=response_password_hash
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
            queryset_login =  Models.objects.get(login=response_login)
        except Models.DoesNotExist:
            raise AuthenticationFailed({
                'meaning': 'Неверные учетные данные',
                'status': status.HTTP_401_UNAUTHORIZED
            })
        
        #проверка пороли
        if queryset_login.check_password(response_password):
           #Если всё верно возврощаем данные пользователя
            geniration = GuaranteedUniqueTokenGenerator()
            token = geniration.generate_token(100)
            queryset_login.token = str(token)
            queryset_login.save()
            return Response({
                'id_users':queryset_login.id,
                'login': response_login,
                'number':queryset_login.number,
                'token':token,
                'status':status.HTTP_200_OK
                })
        
        #Если пороль не верный
        raise AuthenticationFailed({
            'meaning': 'Неверные учетные данные',
            'status': status.HTTP_401_UNAUTHORIZED
        })
    
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