from rest_framework.serializers import *
from .models import UserData

class Serializer(ModelSerializer):
    class Meta:
        model = UserData
        fields = "__all__"

