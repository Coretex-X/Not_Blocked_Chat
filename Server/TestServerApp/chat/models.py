from django.db import models
from django.core.exceptions import ValidationError

class UserData(models.Model):
    """Модель для приватных чатов (1 на 1)"""
    user_id = models.TextField()
    guest_id = models.TextField()
    room = models.TextField()
    count = models.TextField()
    groups = models.TextField()
    
    def clean(self):
        # Проверяем, если запись новая, не должно быть > 1, 
        # если обновляется - не должно быть > 2 (с учетом самой себя)
        existing_count = UserData.objects.filter(room=self.room).count()
        if self.pk is None and existing_count >= 2:
            raise ValidationError('Error 404')
        elif self.pk is not None and existing_count > 2:
            raise ValidationError('Error 404')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class DataMessage(models.Model):
    """Модель для сообщений в приватных чатах"""
    sender_id = models.TextField()  # ID отправителя
    receiver_id = models.TextField()  # ID получателя
    room = models.TextField()  # ID комнаты/чата
    message_text = models.TextField()
    photo = models.ImageField(upload_to='chat/photos/%Y/%m/%d/', blank=True, null=True)
    file = models.FileField(upload_to='chat/files/%Y/%m/%d/', blank=True, null=True)
    voice_message = models.FileField(upload_to='chat/voice/%Y/%m/%d/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class GroupData(models.Model):
    """
    Модель для групповых чатов
    Аналог UserData, но для групп
    """
    group_id = models.TextField(db_index=True)  # Уникальный ID группы
    name = models.TextField()  # Название группы
    description = models.TextField(blank=True, null=True)  # Описание
    created_by = models.TextField()  # ID создателя
    created_at = models.DateTimeField(auto_now_add=True)  # Дата создания
    avatar = models.ImageField(upload_to='groups/avatars/%Y/%m/%d/', blank=True, null=True)  # Аватар группы
    
    class Meta:
        db_table = 'group_data'
    
    def __str__(self):
        return f"Group: {self.name} ({self.group_id})"


class GroupMember(models.Model):
    """
    Модель для участников групп
    Связывает пользователей с группами
    """
    group_id = models.TextField(db_index=True)  # ID группы (связь с GroupData)
    user_id = models.TextField(db_index=True)  # ID пользователя
    role = models.TextField(default='member')  # Роль: 'admin' или 'member'
    joined_at = models.DateTimeField(auto_now_add=True)  # Когда присоединился
    
    class Meta:
        db_table = 'group_members'
    
    def __str__(self):
        return f"{self.user_id} in group {self.group_id}"
    
    def clean(self):
        """Проверка, что пользователь не добавлен в группу дважды"""
        if self.pk is None:  # Новая запись
            existing = GroupMember.objects.filter(
                group_id=self.group_id,
                user_id=self.user_id
            ).exists()
            if existing:
                raise ValidationError('User already in this group')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class GroupMessage(models.Model):
    """
    Модель для сообщений в групповых чатах
    Аналог DataMessage, но для групп
    """
    sender_id = models.TextField()  # ID отправителя
    group_id = models.TextField(db_index=True)  # ID группы
    message_text = models.TextField(blank=True, null=True)  # Текст сообщения
    photo = models.ImageField(upload_to='groups/photos/%Y/%m/%d/', blank=True, null=True)
    file = models.FileField(upload_to='groups/files/%Y/%m/%d/', blank=True, null=True)
    voice_message = models.FileField(upload_to='groups/voice/%Y/%m/%d/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_messages'
        ordering = ['-timestamp']  # Новые сообщения первыми
    
    def __str__(self):
        return f"{self.sender_id} in {self.group_id}: {self.message_text[:50] if self.message_text else '[media]'}"