from django.http import HttpResponse
from rest_framework.views import *
from rest_framework.exceptions import AuthenticationFailed
from .models import *
from .serializer import Serializer
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# Create your views here.
def index(requests):
    return HttpResponse('<h1>Hello is this my Chat</h1>')

class CreateChat(APIView):
    serializer_class = Serializer

    def post(self, request):
        response_user_id = request.data.get('user_id')
        response_guest_id = request.data.get('guest_id')
        response_room = request.data.get('room')
        count_user = 2

        #Валидация (проверка) данных
        '''class Validate(BaseModel):
            user_id:Optional[int] = Field(default=None)
            guest_id:Optional[int] = Field(default=None)
            room:str = Field(min_length=50,max_length=60)
            groups:str = Field(default=None)
            model_config=ConfigDict(extra='forbid') 
        Validate(**request.data)'''

        UserData.objects.create(
            user_id = response_user_id, 
            guest_id = response_guest_id,
            room = response_room,
            count = count_user 
            )
           
        return Response({"post":status.HTTP_201_CREATED})