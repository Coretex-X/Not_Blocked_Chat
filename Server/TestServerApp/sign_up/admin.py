from django.contrib import admin
from .models import Models
# Register your models here.

@admin.register(Models)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'login', 'email', 'brief_info')
    list_display_links = ('login', )
    list_per_page = 5
    search_fields = ['login']
    list_filter = ['email']

    @admin.display(description="Краткое описание")
    def brief_info(self, model: Models):
        return f"Описание {len(model.login)} символов."