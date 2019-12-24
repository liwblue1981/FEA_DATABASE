from django.contrib import admin
from .models import UserModel


class UserModelAdmin(admin.ModelAdmin):
    empty_value_display = '-empty-'
    list_display = ['username', 'first_name', 'last_name', 'email', 'is_superuser', 'position', 'location']
    list_display_links = ['username', ]


# Register your models here.
admin.site.register(UserModel, UserModelAdmin)
