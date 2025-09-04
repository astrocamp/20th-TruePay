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
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


Member = get_user_model()


class RegisterForm(ModelForm):
    email = EmailField(
        widget=EmailInput(attrs={"class": "input", "maxlength": "254"}),
        label="電子郵件",
    )
    password = CharField(widget=PasswordInput(attrs={"class": "input"}), label="密碼")

    class Meta:
        model = Merchant
        fields = [
            "ShopName",
            "UnifiedNumber",
            "NationalNumber",
            "Name",
            "Address",
            "Cellphone",
        ]
        labels = {
            "ShopName": "商店名稱",
            "UnifiedNumber": "統一編號",
            "NationalNumber": "身分證號",
            "Name": "負責人姓名",
            "Address": "地址",
            "Cellphone": "手機號碼",
        }
        widgets = {
            "ShopName": TextInput(attrs={"class": "input", "maxlength": "50"}),
            "UnifiedNumber": TextInput(attrs={"class": "input", "maxlength": "30"}),
            "NationalNumber": TextInput(attrs={"class": "input"}),
            "Name": TextInput(attrs={"class": "input"}),
            "Address": TextInput(attrs={"class": "input", "maxlength": "50"}),
            "Cellphone": TextInput(attrs={"class": "input", "maxlength": "15"}),
        }

    def save(self, commit=True):
        email = self.cleaned_data["email"]

        member = Member.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password"],
            member_type="merchant",
        )
        merchant = super().save(commit=False)
        merchant.member = member
        try:
            merchant.subdomain = generate_unique_subdomain()
        except ValueError as e:
            raise ValidationError("無法生成唯一的商店網址") from e

        if commit:
            merchant.save()
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

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            try:
                Member = get_user_model()
                member = Member.objects.get(email=email, member_type="merchant")

                if not member.check_password(password):
                    raise ValidationError("電子郵件或密碼錯誤")
                elif not member.is_active:
                    raise ValidationError("帳號已停用，請聯絡客服")
                else:
                    merchant = Merchant.objects.get(member=member)
                    cleaned_data["member"] = member
                    cleaned_data["merchant"] = merchant

            except Member.DoesNotExist:
                raise ValidationError("電子郵件或密碼錯誤")
            except Merchant.DoesNotExist:
                raise ValidationError("商家資料不存在")

        return cleaned_data


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
                    "placeholder": "在網址上的shop後面會加上您填寫的名稱",
                }
            ),
        }
        help_texts = {
            "subdomain": "系統會自動生成",
        }
