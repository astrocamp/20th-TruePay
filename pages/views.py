from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from merchant_marketplace.models import Product


def home(req):
    return render(req, "pages/home.html")


def marketplace(req):
    # 取得所有已發布的商品，按照建立時間排序
    product_list = (
        Product.objects.filter(is_active=True)
        .select_related("merchant")
        .order_by("-created_at")
    )

    paginator = Paginator(product_list, 12)  # 每頁顯示 12 個商品，可以常數調整
    page_number = req.GET.get("page")
    products = paginator.get_page(page_number)

    context = {"products": products, "page_title": "商品總覽"}
    return render(req, "pages/marketplace.html", context)


def about(req):
    return render(req, "pages/about.html")


def contact(req):
    return render(req, "pages/contact.html")


def selectrole(req):
    return render(req, "pages/selectrole.html")
