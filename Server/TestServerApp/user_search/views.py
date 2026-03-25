from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from rest_framework.views import *
from sign_up.models import *
from .serializer import Serializer
from rest_framework.exceptions import AuthenticationFailed
from pydantic import BaseModel, Field, ConfigDict
import json

@csrf_exempt
def index(request):
    #if request.method == 'POST':
    #    data = json.loads(request.body)
    #    query = data["query"]
    #    print(f"Received search query: {query}")
    #    return JsonResponse({"status": "ok"})
    if request.method == 'GET':
        print("Received GET request")
        return HttpResponse("Hello, this is the user search app!")
    

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
            "status": queryset.status,
            "post":status.HTTP_200_OK
            })