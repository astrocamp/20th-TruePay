from django import forms
from django.core.exceptions import ValidationError
from .models import Product
from .validators import validate_image_file


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'stock', 'image',
            'phone_number', 'verification_timing', 'ticket_expiry'
        ]

    def clean_image(self):
        image = self.cleaned_data.get('image')

        # 新增商品時必須上傳圖片
        if not self.instance.pk and not image:
            raise ValidationError('新增商品時必須上傳圖片')

        # 如果有圖片，進行驗證
        if image:
            validate_image_file(image)

        return image


class ProductEditForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'stock', 'image',
            'phone_number', 'verification_timing', 'ticket_expiry'
        ]

    def clean_image(self):
        image = self.cleaned_data.get('image')

        # 編輯時如果有新圖片才驗證
        if image:
            validate_image_file(image)

        return image