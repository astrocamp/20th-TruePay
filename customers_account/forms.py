from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Customer
import re

Member = get_user_model()


class CustomerRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "請輸入密碼",
            }
        ),
        label="密碼",
    )

    password_confirm = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "確認密碼",
            }
        ),
        label="確認密碼",
    )
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "請輸入電子郵件",
            }
        ),
        label="電子郵件",
    )

    class Meta:
        model = Customer
        fields = ["name", "id_number", "birth_date", "phone"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入姓名",
                }
            ),
            "id_number": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入身分證字號",
                }
            ),
            "birth_date": forms.DateInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "請輸入電話號碼",
                }
            ),
        }
        labels = {
            "name": "姓名",
            "id_number": "身分證字號",
            "birth_date": "生日",
            "phone": "電話",
        }

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if len(password) < 8:
            raise ValidationError("密碼長度至少需要8個字元")
        return password

    def clean_password_confirm(self):
        password = self.cleaned_data.get("password")
        password_confirm = self.cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise ValidationError("密碼確認不相符")
        return password_confirm

    def clean_id_number(self):
        id_number = self.cleaned_data.get("id_number")
        if not re.match(r"^[A-Z][12][0-9]{8}$", id_number):
            raise ValidationError("身分證字號格式不正確")
        return id_number

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not re.match(r"^09[0-9]{8}$", phone):
            raise ValidationError("手機號碼格式不正確（格式：09xxxxxxxx）")
        return phone

    def save(self, commit=True):

        member = Member.objects.create_user(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            member_type="customer",
        )
        customer = super().save(commit=False)
        customer.member = member
        if commit:
            customer.save()
        return customer


class CustomerLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "請輸入電子郵件",
            }
        ),
        label="電子郵件",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
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
                member = Member.objects.get(email=email, member_type="customer")
                if not member.check_password(password):
                    member.login_failed_count += 1
                    member.save(update_fields=["login_failed_count"])
                    raise ValidationError("電子郵件或密碼錯誤")
                elif not member.is_active:
                    raise ValidationError("帳號已停用，請聯絡客服")
                else:
                    if hasattr(member, "customer"):
                        customer = Customer.objects.get(member=member)
                        member.login_failed_count = 0
                        member.update_last_login()
                        member.save(update_fields=["login_failed_count"])

                        cleaned_data["member"] = member
                        cleaned_data["customer"] = customer
                    else:
                        raise ValidationError("客戶資料不存在，請聯絡客服")
            except Member.DoesNotExist:
                raise ValidationError("電子郵件或密碼錯誤")

        return cleaned_data
