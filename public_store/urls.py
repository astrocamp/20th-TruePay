from django.urls import path
from . import views

app_name = "public_store"

urlpatterns = [
    # 商店總覽 - /store/{subdomain}/
    path("<slug:subdomain>/", views.shop_overview, name="shop_overview"),
    
    # 單一商品頁面 - /store/{subdomain}/product/{id}/
    path("<slug:subdomain>/product/<int:product_id>/", views.product_detail, name="product_detail"),
    
    # 付款頁面 - /store/pay/{id}/
    path("pay/<int:id>/", views.payment_page, name="payment_page"),
]