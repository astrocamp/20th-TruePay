from django import template
from merchant_account.models import Merchant

register = template.Library()


@register.simple_tag(takes_context=True)
def get_current_merchant(context):
    request = context["request"]
    if request.user.is_authenticated and request.user.member_type == "merchant":
        email = request.user.email
        try:
            merchant = Merchant.objects.get(Email=email)
            if merchant.subdomain:
                return f"/merchant/dashboard/{merchant.subdomain}/"
        except Merchant.DoesNotExist:
            pass
    return "/merchant/login/"
