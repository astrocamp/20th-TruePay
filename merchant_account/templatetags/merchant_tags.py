from django import template
from merchant_account.models import Merchant

register = template.Library()


@register.simple_tag(takes_context=True)
def get_current_merchant(context):
    request = context["request"]
    if request.user.is_authenticated and request.user.member_type == "merchant":
        try:
            merchant = Merchant.objects.get(member=request.user)
            if merchant.subdomain:
                return f"/merchant/dashboard/{merchant.subdomain}/"
        except Merchant.DoesNotExist:
            pass
    return "/merchant/login/"


@register.simple_tag(takes_context=True)
def get_page_merchant(context):
    """取得當前頁面的商家資料"""
    request = context["request"]

    # 先檢查模板context中是否已有商家資料
    if 'merchant' in context:
        return context['merchant']
    elif 'product' in context and hasattr(context['product'], 'merchant'):
        return context['product'].merchant

    # 如果沒有，嘗試從URL路徑中取得subdomain
    path_parts = request.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'shop':
        subdomain = path_parts[1]
        try:
            merchant = Merchant.objects.get(subdomain=subdomain)
            return merchant
        except Merchant.DoesNotExist:
            pass

    return None


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
