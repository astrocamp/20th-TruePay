from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Customer
import re
from django.utils import timezone

Member = get_user_model()


class CustomerRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入密碼（至少8個字元）"),
            }
        ),
        label="密碼 *",
        help_text="密碼長度至少需要8個字元",
    )

    password_confirm = forms.CharField(
        max_length=128,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("確認密碼"),
            }
        ),
        label="確認密碼 *",
    )
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入電子郵件"),
                "required": True,
            }
        ),
        label="電子郵件 *",
    )

    class Meta:
        model = Customer
        fields = ["name", "id_number", "birth_date", "phone"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": _("請輸入姓名"),
                    "required": True,
                }
            ),
            "id_number": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": _("請輸入身分證字號（格式：A123456789）"),
                }
            ),
            "birth_date": forms.DateInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "type": "date",
                    "max": timezone.now().date().isoformat(),  # 防止選擇未來日期
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": _("請輸入電話號碼（格式：09xxxxxxxx）"),
                }
            ),
        }
        labels = {
            "name": "姓名 *",
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
        if id_number and not re.match(r"^[A-Z][12][0-9]{8}$", id_number):
            raise ValidationError("身分證字號格式不正確")
        return id_number

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            today = timezone.now().date()
            if birth_date > today:
                raise ValidationError("生日不能是未來的日期")
        return birth_date

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and not re.match(r"^09[0-9]{8}$", phone):
            raise ValidationError("手機號碼格式不正確（格式：09xxxxxxxx）")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        existing_members = Member.objects.filter(email=email, member_type="customer")
        if existing_members.filter(socialaccount__provider="google").exists():
            raise ValidationError("此電子郵件已透過Google帳號註冊，請使用Google登入。")
        elif existing_members.exists():
            raise ValidationError("此電子郵件已被註冊使用，請使用登入功能。")
        return email

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
                "placeholder": _("請輸入電子郵件"),
            }
        ),
        label="電子郵件",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入密碼"),
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
                member = Member.objects.filter(
                    email=email, member_type="customer"
                ).first()

                if not member:
                    raise ValidationError("電子郵件或密碼錯誤")

                if not member.has_usable_password():
                    if member.socialaccount_set.filter(provider="google").exists():
                        raise ValidationError("您有用過google去登入，請點擊google按鈕")

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
                        member.last_login = timezone.now()
                        member.save(update_fields=["login_failed_count", "last_login"])

                        cleaned_data["member"] = member
                        cleaned_data["customer"] = customer
                    else:
                        raise ValidationError("客戶資料不存在，請聯絡客服")
            except Member.DoesNotExist:
                raise ValidationError("電子郵件或密碼錯誤")

        return cleaned_data


class CustomerProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入電子郵件"),
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
                    "placeholder": _("請輸入姓名"),
                }
            ),
            "id_number": forms.TextInput(
                attrs={
                    "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": _("請輸入身分證字號"),
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
                    "placeholder": _("請輸入電話號碼"),
                }
            ),
        }
        labels = {
            "name": "姓名",
            "id_number": "身分證字號",
            "birth_date": "生日",
            "phone": "電話",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email

    def clean_id_number(self):
        id_number = self.cleaned_data.get("id_number")
        if id_number and not re.match(r"^[A-Z][12][0-9]{8}$", id_number):
            raise ValidationError("身分證字號格式不正確")
        
        # 檢查是否與其他用戶重複（排除自己）
        if id_number and Customer.objects.exclude(pk=self.instance.pk).filter(id_number=id_number).exists():
            raise ValidationError("此身分證字號已被使用")
        
        return id_number

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and not re.match(r"^09[0-9]{8}$", phone):
            raise ValidationError("手機號碼格式不正確（格式：09xxxxxxxx）")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and get_user_model().objects.exclude(pk=self.user.pk).filter(email=email).exists():
            raise ValidationError("此電子郵件已被使用")
        return email

    def save(self, commit=True):
        customer = super().save(commit=False)
        if commit:
            customer.save()
            # 更新 Member 的 email
            if self.user:
                self.user.email = self.cleaned_data['email']
                # 更新 username (格式: ID_email)
                self.user.username = f"{self.user.pk}_{self.cleaned_data['email']}"
                self.user.save(update_fields=['email', 'username'])
        return customer


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入目前密碼"),
            }
        ),
        label="目前密碼",
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入新密碼"),
            }
        ),
        label="新密碼",
        min_length=8,
        help_text="密碼長度至少需要8個字元"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("確認新密碼"),
            }
        ),
        label="確認新密碼",
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise ValidationError("目前密碼錯誤")
        return old_password

    def clean_confirm_password(self):
        confirm_password = self.cleaned_data.get("confirm_password")
        return confirm_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', "新密碼確認不相符")
        
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


class ForgotPasswordForm(forms.Form):
    """忘記密碼表單"""
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入您的電子郵件"),
            }
        ),
        label="電子郵件",
        help_text="我們將發送密碼重設連結到您的電子郵件",
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        
        # 查找符合條件的客戶帳號（取最新的一個）
        member = Member.objects.filter(
            email=email, 
            member_type="customer"
        ).order_by('-id').first()
        
        if not member:
            raise ValidationError("此電子郵件未註冊，請檢查輸入是否正確")
        
        # 檢查是否為 Google 登入用戶
        if not member.has_usable_password():
            if member.socialaccount_set.filter(provider="google").exists():
                raise ValidationError("您使用 Google 帳號登入，無法重設密碼。請使用 Google 登入。")
        
        # 檢查帳號是否啟用
        if not member.is_active:
            raise ValidationError("此帳號已停用，請聯絡客服")
        
        self.member = member
        
        return email


class PasswordResetForm(forms.Form):
    """密碼重設表單"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("請輸入新密碼"),
            }
        ),
        label="新密碼",
        min_length=8,
        help_text="密碼長度至少需要8個字元"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": _("確認新密碼"),
            }
        ),
        label="確認新密碼",
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', "新密碼確認不相符")
        
        return cleaned_data
