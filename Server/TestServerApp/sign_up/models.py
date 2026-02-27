from django.db import models
from django.contrib.auth.hashers import check_password


# Create your models here.
class Models(models.Model):
    login = models.CharField(max_length=225, unique=True)
    email = models.EmailField(unique=True)
    number = models.TextField()
    status = models.TextField()
    password = models.TextField()
    token = models.TextField(unique=True)
    sessuon_token_id_consuner = models.TextField(unique=True)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.login