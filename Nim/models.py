from django.db import models

# Create your models here.
class users(models.Model):
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    last_time = models.DateTimeField()
    status = models.IntegerField()


class requests (models.Model):
    frm  = models.CharField(max_length=100)
    to  = models.CharField(max_length=100)
    