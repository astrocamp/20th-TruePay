from django.db import models


# Create your models here.
class Merchant(models.Model):
    UnifiedNumber = models.IntegerField(null=False)
    NationalNumber = models.CharField(null=False)
    Email = models.CharField(null=False)
    Name = models.CharField(null=False)
    Address = models.CharField(null=False)
    Cellphone = models.IntegerField(null=False)
    Password = models.CharField(null=False)
