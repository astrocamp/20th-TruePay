from django.urls import path
from . import views

app_name = "public_store"

urlpatterns = [
    # 商店總覽 - /store/{subdomain}/
    path("<slug:subdomain>/", views.shop_overview, name="shop_overview"),
    # 付款頁面 - /store/pay/{id}/
    path("<slug:subdomain>/pay/<int:id>/", views.payment_page, name="payment_page"),
]
