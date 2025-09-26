from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.conf import settings
from merchant_marketplace.models import Product


def home(req):
    return render(req, "pages/home.html")


def marketplace(req):
    # 取得所有已發布的商品，排除已刪除的商品和過期商品，按照建立時間排序
    product_list = (
        Product.objects.filter(
            Q(ticket_expiry__isnull=True) | Q(ticket_expiry__gt=timezone.now()),
            is_active=True,
            is_deleted=False,
        )
        .select_related("merchant")
        .order_by("-created_at")
    )

    paginator = Paginator(product_list, 12)  # 每頁顯示 12 個商品，可以常數調整
    page_number = req.GET.get("page")
    products = paginator.get_page(page_number)

    context = {
        "products": products,
        "page_title": "商品總覽",
        "BASE_DOMAIN": settings.BASE_DOMAIN
    }
    return render(req, "pages/marketplace.html", context)


def selectrole(req):
    return render(req, "pages/selectrole.html")


def terms(req):
    return render(req, "pages/terms.html")


def privacy(req):
    return render(req, "pages/privacy.html")


def get_csrf_token_api(request):
    """提供新的 CSRF token API 端點"""
    return JsonResponse({'csrf_token': get_token(request)})
