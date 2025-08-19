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
            "ShopName": TextInput(attrs={"class": "input"}),
            "UnifiedNumber": TextInput(attrs={"class": "input"}),
            "NationalNumber": TextInput(attrs={"class": "input"}),
            "Email": EmailInput(attrs={"class": "input"}),
            "Name": TextInput(attrs={"class": "input"}),
            "Address": TextInput(attrs={"class": "input"}),
            "Cellphone": TextInput(attrs={"class": "input"}),
            "Password": PasswordInput(attrs={"class": "input"}),
        }


class LoginForm(Form):
    email = EmailField(widget=EmailInput(attrs={"class": "input"}), label="電子郵件")
    password = CharField(widget=PasswordInput(attrs={"class": "input"}), label="密碼")
