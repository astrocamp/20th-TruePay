from django.db import models
from django.contrib.auth.hashers import make_password, check_password


# Create your models here.
class Merchant(models.Model):
    ShopName = models.CharField(max_length=50, null=False)
    UnifiedNumber = models.CharField(max_length=8, null=False)
    NationalNumber = models.CharField(max_length=10, null=False)
    Email = models.EmailField(unique=True, null=False)
    Name = models.CharField(max_length=30, null=False)
    Address = models.CharField(max_length=50, null=False)
    Cellphone = models.CharField(max_length=15, null=False)
    Password = models.CharField(max_length=128, null=False)
    subdomain = models.SlugField(max_length=50, unique=True, null=True, blank=True)
    merchant_domain = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="自訂域名"
    )
    use_merchant_domain = models.BooleanField(
        default=False, verbose_name="使用自訂域名"
    )

    def __str__(self):
        return self.ShopName

    def set_password(self, raw_password):
        self.Password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.Password)
