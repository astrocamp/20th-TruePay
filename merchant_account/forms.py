from django.forms import (
    ModelForm,
    TextInput,
    EmailInput,
    CharField,
    PasswordInput,
    Form,
    EmailField,
    SlugField,
    CheckboxInput,
)
from .models import Merchant


class RegisterForm(ModelForm):
    subdomain = SlugField(
        max_length=50,
        required=False,
        help_text="商家專屬網址，例如：ownshop會變成－ownshop.truepay.com",
        widget=TextInput(attrs={"class": "input"}),
    )

    class Meta:
        model = Merchant
        fields = [
            "ShopName",
            "subdomain",
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
            "subdomain": "專屬網址",
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
        fields = ["subdomain", "merchant_domain", "use_merchant_domain"]
        labels = {
            "subdomain": "子網域名稱",
            "merchant_domain": "自訂網域名稱",
            "use_merchant_domain": "啟用自訂網域",
        }
        widgets = {
            "subdomain": TextInput(
                attrs={
                    "class": "input",
                    "palceholder": "在網址上的shop後面會加上您填寫的名稱",
                }
            ),
            "merchant_domain": TextInput(
                attrs={"class": "input", "placeholder": "例如：bakery.com(不要加 www)"}
            ),
            "use_merchant_domain": CheckboxInput(attrs={"class": "checkbox"}),
        }
        help_texts = {
            "subdomain": "設定後可使用 /marketplace/?shop=子網域名稱訪問後台",
            "merchant_domain": "請輸入您的網域名稱，不需要加上 www",
            "use_merchant_domain": "勾選後就使用您自訂的網域名稱",
        }
