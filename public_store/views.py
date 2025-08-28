from django.shortcuts import render, redirect, get_object_or_404
from merchant_account.models import Merchant
from merchant_marketplace.models import Product


def shop_overview(request, subdomain):
    """商店總覽頁面 - 客戶查看商家的所有商品"""
    try:
        merchant = Merchant.objects.get(subdomain=subdomain)
        products = Product.objects.filter(merchant=merchant, is_active=True).order_by(
            "-created_at"
        )
        context = {"merchant": merchant, "products": products}
        return render(request, "public_store/shop_overview.html", context)
    except Merchant.DoesNotExist:
        return redirect("pages:home")


def product_detail(request, subdomain, product_id):
    """單一商品詳細頁面 - 客戶查看特定商品"""
    try:
        merchant = Merchant.objects.get(subdomain=subdomain)
        product = get_object_or_404(
            Product, 
            id=product_id, 
            merchant=merchant, 
            is_active=True
        )
        context = {
            "merchant": merchant, 
            "product": product
        }
        return render(request, "public_store/product_detail.html", context)
    except Merchant.DoesNotExist:
        return redirect("pages:home")


def payment_page(request, id):
    """商品收款頁面 - 客戶進行付款"""
    product = get_object_or_404(Product, id=id, is_active=True)
    return render(
        request, "public_store/payment_page.html", {"product": product}
    )


def custom_domain_shop(request, merchant):
    """自定義域名的商店頁面 - 從 middleware 調用"""
    products = Product.objects.filter(merchant=merchant, is_active=True).order_by(
        "-created_at"
    )
    context = {"merchant": merchant, "products": products}
    return render(request, "public_store/shop_overview.html", context)