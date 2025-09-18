from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'embed_system'

router = DefaultRouter()

urlpatterns = [
    # API 路由
    path('api/', include([
        # 商品相關 API
        path('products/<int:product_id>/', views.ProductDetailAPIView.as_view(), name='product-detail'),
        path('products/<int:product_id>/update/', views.ProductUpdateAPIView.as_view(), name='product-update'),
        path('products/create-from-article/', views.CreateProductFromArticleAPIView.as_view(), name='product-create-from-article'),

        # 認證相關 API
        path('auth/session/', views.SessionCheckAPIView.as_view(), name='auth-session'),
        path('auth/verify-token/', views.VerifyTokenAPIView.as_view(), name='auth-verify-token'),
        path('manage-token/', views.GenerateManageTokenAPIView.as_view(), name='generate-manage-token'),
    ])),

    # 嵌入頁面
    path('product/<int:product_id>/', views.EmbedProductView.as_view(), name='embed-product'),
]