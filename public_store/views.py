from django.shortcuts import render, redirect, get_object_or_404
from merchant_account.models import Merchant
from merchant_marketplace.models import Product
from customers_account.models import Customer
from django.http import HttpResponsePermanentRedirect
import os


def get_store_template(merchant, template_name):
    template_id = getattr(merchant, "store_template_id", "modern")
    if not template_id:
        template_id = "modern"
    return f"shop_templates/{template_id}/{template_name}"


def shop_overview(request, subdomain=None):
    """商店總覽頁面 - 客戶查看商家的所有商品"""

    # 本地開發：通過 subdomain 參數找到商家
    if not hasattr(request, "merchant") or request.merchant is None:
        if subdomain:
            merchant = get_object_or_404(Merchant, subdomain=subdomain)
        else:
            return render(request, "pages/home.html")
    else:
        # 正式環境：使用 middleware 設定的 merchant
        merchant = request.merchant

    products = Product.objects.filter(merchant=merchant, is_active=True).order_by(
        "-created_at"
    )

    preview_template = request.GET.get("preview")
    if preview_template and preview_template in [
        "modern_light",
        "modern",
        "tech",
        "handcraft",
        "vintage",
    ]:
        # 使用預覽模板
        template_path = f"shop_templates/{preview_template}/shop_overview.html"
    else:
        # 使用商家設定的模板
        template_path = get_store_template(merchant, "shop_overview.html")

    context = {"merchant": merchant, "products": products}
    return render(request, template_path, context)


def payment_page(request, subdomain=None, id=None):
    """商品收款頁面 - 客戶進行付款"""

    # 本地開發：直接通過商品 ID 找到商品和商家
    if not hasattr(request, "merchant") or request.merchant is None:
        product = get_object_or_404(Product, id=id, is_active=True)
        merchant = product.merchant
    else:
        # 正式環境：使用 middleware 設定的 merchant
        merchant = request.merchant
        product = get_object_or_404(Product, id=id, merchant=merchant, is_active=True)
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
    template_path = get_store_template(merchant, "payment_page.html")
    return render(request, template_path, context)
