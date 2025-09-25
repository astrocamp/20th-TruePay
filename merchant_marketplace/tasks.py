from celery import shared_task
from django.utils import timezone
from .models import Product


@shared_task(name="merchant_marketplace.auto_deactivate_expired_products")
def auto_deactivate_expired_products():
    return Product.objects.filter(
        ticket_expiry__lt=timezone.now(), is_active=True, is_deleted=False
    ).update(is_active=False)
