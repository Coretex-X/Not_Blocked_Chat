from django.db import models

# Create your models here.
class Notification(models.Model):
    user_id = models.TextField()
    guests_id = models.TextField()
    lobbi = models.TextField()
    message = models.TextField()
    read_message = models.TextField()