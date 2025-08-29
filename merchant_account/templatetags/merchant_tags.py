from django import template
from merchant_account.models import Merchant

register = template.Library()


@register.simple_tag(takes_context=True)
def get_current_merchant(context):
    request = context["request"]
    if request.user.is_authenticated and request.user.username.startswith("merchant_"):
        email = request.user.username.replace("merchant_", "")
        try:
            merchant = Merchant.objects.get(Email=email)
            if merchant.subdomain:
                return f"/merchant/dashboard/?shop={merchant.subdomain}"
            else:
                return f"/merchant/dashboard/?shop_id={merchant.id}"
        except Merchant.DoesNotExist:
            pass
    return "/merchant/login/"
