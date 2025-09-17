from django.forms import (
    ModelForm,
    TextInput,
    EmailInput,
    CharField,
    PasswordInput,
    Form,
    EmailField,
)
from django import forms
from .models import Merchant
from .utils import generate_unique_subdomain
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.conf import settings
import re


Member = get_user_model()


class RegisterForm(ModelForm):
    email = EmailField(
        max_length=254,
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
            "ShopName": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "maxlength": "50",
                    "placeholder": "請輸入商店名稱",
                }
            ),
            "UnifiedNumber": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "maxlength": "30",
                    "placeholder": "請輸入統一編號",
                }
            ),
            "NationalNumber": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入身分證字號",
                }
            ),
            "Name": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入負責人姓名",
                }
            ),
            "Address": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "maxlength": "50",
                    "placeholder": "請輸入地址",
                }
            ),
            "Cellphone": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "maxlength": "15",
                    "placeholder": "請輸入手機號碼",
                }
            ),
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


class SubdomainChangeForm(forms.Form):
    new_subdomain = CharField(
        max_length=30,
        min_length=3,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例如：mystore",
                "pattern": "[a-zA-Z0-9-]+",
                "title": "只能使用英文字母、數字和連字號",
            }
        ),
        label="新的子網域名稱",
    )

    reason = CharField(
        max_length=200,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "請說明修改原因...",
            }
        ),
        label="修改原因",
        required=False,
    )

    def __init__(self, merchant, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.merchant = merchant

        can_change, message = merchant.can_change_subdomain()
        if not can_change:
            self.fields["new_subdomain"].widget.attrs["disabled"] = True
            self.fields["new_subdomain"].help_text = f"⚠️ {message}"

    def clean_new_subdomain(self):
        new_subdomain = self.cleaned_data["new_subdomain"].lower().strip()
        if new_subdomain == self.merchant.subdomain:
            raise forms.ValidationError("新名稱不能與目前相同")

        is_valid, message = Merchant.validate_subdomain_format(new_subdomain)
        if not is_valid:
            raise forms.ValidationError(message)

        if Merchant.objects.filter(subdomain=new_subdomain).exists():
            raise forms.ValidationError("此子網域名稱已被使用")

        return new_subdomain

    def clean(self):
        cleaned_data = super().clean()

        can_change, message = self.merchant.can_change_subdomain()
        if not can_change:
            raise forms.ValidationError(message)
        return cleaned_data


class MerchantProfileUpdateForm(ModelForm):
    email = EmailField(
        max_length=254,
        widget=EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "請輸入電子郵件",
            }
        ),
        label="電子郵件",
    )

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
            "ShopName": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入商店名稱",
                }
            ),
            "UnifiedNumber": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入統一編號",
                }
            ),
            "NationalNumber": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入身分證字號",
                }
            ),
            "Name": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入負責人姓名",
                }
            ),
            "Address": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入地址",
                }
            ),
            "Cellphone": TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入手機號碼",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["email"].initial = self.user.email

    def clean_UnifiedNumber(self):
        unified_number = self.cleaned_data.get("UnifiedNumber")
        if unified_number and len(unified_number) != 8:
            raise ValidationError("統一編號必須為8位數字")

        # 檢查是否與其他商家重複（排除自己）
        if (
            unified_number
            and Merchant.objects.exclude(pk=self.instance.pk)
            .filter(UnifiedNumber=unified_number)
            .exists()
        ):
            raise ValidationError("此統一編號已被使用")

        return unified_number

    def clean_NationalNumber(self):
        national_number = self.cleaned_data.get("NationalNumber")
        if national_number and len(national_number) != 10:
            raise ValidationError("身分證字號必須為10位")

        # 檢查是否與其他商家重複（排除自己）
        if (
            national_number
            and Merchant.objects.exclude(pk=self.instance.pk)
            .filter(NationalNumber=national_number)
            .exists()
        ):
            raise ValidationError("此身分證字號已被使用")

        return national_number

    def clean_Cellphone(self):
        cellphone = self.cleaned_data.get("Cellphone")
        if cellphone and len(cellphone) > 15:
            raise ValidationError("手機號碼長度不能超過15位")
        return cellphone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        Member = get_user_model()

        # 只有在電子郵件實際被修改時才檢查唯一性
        if email and self.user and email != self.user.email:
            if Member.objects.exclude(pk=self.user.pk).filter(email=email).exists():
                raise ValidationError("此電子郵件已被使用")
        return email

    def save(self, commit=True):
        merchant = super().save(commit=False)
        if commit:
            merchant.save()
            # 更新 Member 的 email
            if self.user:
                self.user.email = self.cleaned_data["email"]
                # 更新 username (格式: ID_email)
                self.user.username = f"{self.user.pk}_{self.cleaned_data['email']}"
                self.user.save(update_fields=["email", "username"])
        return merchant


