from django.shortcuts import render, redirect, get_object_or_404
from merchant_account.models import Merchant
from merchant_marketplace.models import Product
from customers_account.models import Customer
from django.http import HttpResponsePermanentRedirect
import os


def shop_overview(request, subdomain=None):
    """商店總覽頁面 - 客戶查看商家的所有商品"""

    merchant = request.merchant
    products = Product.objects.filter(merchant=merchant, is_active=True).order_by(
        "-created_at"
    )
    context = {"merchant": merchant, "products": products}
    return render(request, "public_store/shop_overview.html", context)


def payment_page(request, subdomain=None, id=None):
    """商品收款頁面 - 客戶進行付款"""

    merchant = request.merchant
    product_id = id if id is not None else subdomain

    product = get_object_or_404(
        Product, id=product_id, merchant=merchant, is_active=True
    )
    is_customer = (
        request.user.is_authenticated and request.user.member_type == "customer"
    )

    # 如果是已登入的客戶，取得Customer物件以檢查TOTP狀態
    customer = None
    if is_customer:
        try:
            customer = Customer.objects.get(member=request.user)
        except Customer.DoesNotExist:
            pass

    context = {"product": product, "is_customer": is_customer, "customer": customer}
    return render(request, "public_store/payment_page.html", context)
