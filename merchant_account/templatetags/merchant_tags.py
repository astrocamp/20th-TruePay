from django import template
from merchant_account.models import Merchant

register = template.Library()


@register.simple_tag(takes_context=True)
def get_current_merchant(context):
    request = context["request"]
    merchant_id = request.session.get("merchant_id")

    if merchant_id:
        try:
            return Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return None
