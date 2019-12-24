from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserModel(AbstractUser):
    # Add my own defined items
    # ['FEA Leader', 'FEA analyst', 'PE Leader', 'PE Member']
    position=models.CharField(max_length=20)
    # ['CH', 'EU', 'NA']
    location=models.CharField(max_length=20)

    class Meta:
        db_table='user_table'

    def __str__(self):
        return self.first_name+'.'+self.last_name

# UserModel.objects.create_superuser(username='liw00073',password='cadfea73',email='wei.li@tenneco.com')