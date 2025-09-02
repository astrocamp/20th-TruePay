from django.forms import (
    ModelForm,
    TextInput,
    EmailInput,
    CharField,
    PasswordInput,
    Form,
    EmailField,
)
from .models import Merchant
from .utils import generate_unique_subdomain
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class RegisterForm(ModelForm):
    class Meta:
        model = Merchant
        fields = [
            "ShopName",
            "UnifiedNumber",
            "NationalNumber",
            "Email",
            "Name",
            "Address",
            "Cellphone",
            "Password",
        ]
        labels = {
            "ShopName": "商店名稱",
            "UnifiedNumber": "統一編號",
            "NationalNumber": "身分證號",
            "Email": "電子郵件",
            "Name": "負責人姓名",
            "Address": "地址",
            "Cellphone": "手機號碼",
            "Password": "密碼",
        }
        widgets = {
            "ShopName": TextInput(attrs={"class": "input", "maxlength": "50"}),
            "UnifiedNumber": TextInput(attrs={"class": "input", "maxlength": "30"}),
            "NationalNumber": TextInput(attrs={"class": "input"}),
            "Email": EmailInput(attrs={"class": "input", "maxlength": "254"}),
            "Name": TextInput(attrs={"class": "input"}),
            "Address": TextInput(attrs={"class": "input", "maxlength": "50"}),
            "Cellphone": TextInput(attrs={"class": "input", "maxlength": "15"}),
            "Password": PasswordInput(attrs={"class": "input"}),
        }

    def save(self, commit=True):
        merchant = super().save(commit=False)
        merchant.set_password(self.cleaned_data["Password"])
        try:
            merchant.subdomain = generate_unique_subdomain()
        except ValueError as e:
            raise ValidationError("無法生成唯一的商店網址") from e

        if commit:
            merchant.save()

        User.objects.get_or_create(
            username=f"merchant_{merchant.Email}",
            defaults={"email": merchant.Email, "first_name": merchant.Name},
        )
        return merchant


class LoginForm(Form):
    email = EmailField(
        widget=EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "請輸入電子郵件",
            }
        ),
        label="電子郵件",
    )
    password = CharField(
        widget=PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "請輸入密碼",
            }
        ),
        label="密碼",
    )


class domain_settings_form(ModelForm):
    class Meta:
        model = Merchant
        fields = ["subdomain"]
        labels = {
            "subdomain": "子網域名稱",
        }
        widgets = {
            "subdomain": TextInput(
                attrs={
                    "class": "input",
                    "palceholder": "在網址上的shop後面會加上您填寫的名稱",
                }
            ),
        }
        help_texts = {
            "subdomain": "系統會自動生成",
        }
