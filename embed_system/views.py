import jwt
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from merchant_marketplace.models import Product
from merchant_account.models import Merchant

User = get_user_model()


class ProductDetailAPIView(APIView):
    """
    GET /api/products/:id - 取得商品資訊
    公開 API，無需認證
    """
    def get(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)

            # 構建購買連結
            purchase_url = request.build_absolute_uri(
                f'/shop/{product.merchant.subdomain}/product/{product.id}/'
            )

            data = {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': product.price,
                'image': product.image.url if product.image else None,
                'merchant': {
                    'name': product.merchant.business_name,
                    'subdomain': product.merchant.subdomain,
                },
                'purchase_url': purchase_url,
                'stock': product.stock,
                'is_active': product.is_active,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response(
                {'error': '商品不存在或已下架'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            return Response(
                {'error': '獲取商品資訊失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionCheckAPIView(APIView):
    """
    GET /api/auth/session - 檢查登入狀態
    透過 Cookie 判斷使用者登入狀態和管理權限
    """
    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return Response({
                    'loggedIn': False,
                    'userId': None,
                    'canManage': []
                })

            # 取得使用者可管理的商品列表
            can_manage = []
            if hasattr(request.user, 'merchant'):
                # 如果是商家，可以管理自己的所有商品
                products = Product.objects.filter(
                    merchant=request.user.merchant
                ).values_list('id', flat=True)
                can_manage = list(products)

            return Response({
                'loggedIn': True,
                'userId': request.user.id,
                'canManage': can_manage
            })

        except Exception:
            return Response(
                {'error': '檢查登入狀態失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyTokenAPIView(APIView):
    """
    POST /api/auth/verify-token - 驗證管理 Token
    驗證短效 JWT 是否能操作指定商品
    """
    def post(self, request):
        try:
            token = request.data.get('token')
            product_id = request.data.get('product_id')

            if not token or not product_id:
                return Response(
                    {'error': '缺少必要參數'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # 解碼 JWT
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=['HS256']
                )

                # 檢查 Token 是否對應正確的商品
                if payload.get('product_id') != int(product_id):
                    return Response(
                        {'error': 'Token 與商品不匹配'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # 檢查 Token 是否過期
                if payload.get('exp', 0) < datetime.now().timestamp():
                    return Response(
                        {'error': 'Token 已過期'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )

                # 檢查商家是否存在
                merchant_id = payload.get('merchant_id')
                merchant = get_object_or_404(Merchant, id=merchant_id)

                return Response({
                    'valid': True,
                    'merchant_id': merchant_id,
                    'product_id': product_id
                })

            except jwt.ExpiredSignatureError:
                return Response(
                    {'error': 'Token 已過期'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            except jwt.InvalidTokenError:
                return Response(
                    {'error': 'Token 無效'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        except Exception:
            return Response(
                {'error': '驗證 Token 失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductUpdateAPIView(APIView):
    """
    PATCH /api/products/:id - 更新商品資訊
    需要權限驗證
    """
    def patch(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)

            # 檢查權限
            can_edit = False

            # 方法1: 檢查是否為商品擁有者
            if (request.user.is_authenticated and
                hasattr(request.user, 'merchant') and
                product.merchant == request.user.merchant):
                can_edit = True

            # 方法2: 檢查 Token (如果提供)
            token = request.META.get('HTTP_AUTHORIZATION')
            if token and token.startswith('Bearer '):
                token = token[7:]  # 移除 "Bearer " 前綴
                try:
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=['HS256']
                    )
                    if (payload.get('product_id') == product_id and
                        payload.get('exp', 0) >= datetime.now().timestamp()):
                        can_edit = True
                except jwt.InvalidTokenError:
                    pass

            if not can_edit:
                return Response(
                    {'error': '無權限編輯此商品'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 更新商品資訊
            allowed_fields = ['name', 'description', 'price', 'stock', 'is_active']
            updated_fields = []

            for field in allowed_fields:
                if field in request.data:
                    setattr(product, field, request.data[field])
                    updated_fields.append(field)

            if updated_fields:
                product.save(update_fields=updated_fields)

            return Response({
                'success': True,
                'updated_fields': updated_fields,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'stock': product.stock,
                    'is_active': product.is_active,
                }
            })

        except Product.DoesNotExist:
            return Response(
                {'error': '商品不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            return Response(
                {'error': '更新商品失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateManageTokenAPIView(APIView):
    """
    POST /api/manage-token - 產生管理連結
    為商家產生帶有 JWT 的臨時管理 URL
    """
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': '需要登入'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not hasattr(request.user, 'merchant'):
                return Response(
                    {'error': '只有商家可以產生管理連結'},
                    status=status.HTTP_403_FORBIDDEN
                )

            product_id = request.data.get('product_id')
            if not product_id:
                return Response(
                    {'error': '缺少商品 ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 驗證商品屬於該商家
            product = get_object_or_404(
                Product,
                id=product_id,
                merchant=request.user.merchant
            )

            # 產生 JWT Token (有效期30分鐘)
            payload = {
                'merchant_id': request.user.merchant.id,
                'product_id': product.id,
                'exp': datetime.now() + timedelta(minutes=30),
                'iat': datetime.now(),
            }

            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            return Response({
                'token': token,
                'expires_in': 1800,  # 30 minutes in seconds
                'product_id': product_id
            })

        except Product.DoesNotExist:
            return Response(
                {'error': '商品不存在或無權限'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            return Response(
                {'error': '產生管理連結失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateProductFromArticleAPIView(APIView):
    """
    POST /api/products/create-from-article - 文章轉商品
    將文章內容轉換為新商品並產生嵌入碼
    """
    def post(self, request):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': '需要登入'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not hasattr(request.user, 'merchant'):
                return Response(
                    {'error': '只有商家可以創建商品'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 取得必要參數
            required_fields = ['title', 'description', 'price']
            for field in required_fields:
                if not request.data.get(field):
                    return Response(
                        {'error': f'缺少必要欄位: {field}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 創建商品
            product = Product.objects.create(
                name=request.data['title'],
                description=request.data['description'],
                price=request.data['price'],
                merchant=request.user.merchant,
                stock=request.data.get('stock', 999),  # 預設庫存
                phone_number=request.user.merchant.phone_number,
            )

            # 如果有提供封面圖，處理圖片上傳
            if 'cover_image' in request.FILES:
                product.image = request.FILES['cover_image']
                product.save()

            # 產生商品連結
            base_url = request.build_absolute_uri('/')[:-1]  # 移除結尾的 /

            return Response({
                'success': True,
                'product_id': product.id,
                'product_url': f'{base_url}/marketplace/shop/{product.merchant.subdomain}/product/{product.id}/',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'image': product.image.url if product.image else None,
                }
            }, status=status.HTTP_201_CREATED)

        except Exception:
            return Response(
                {'error': '創建商品失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmbedProductView(TemplateView):
    """
    iframe 嵌入頁面 - /embed/product/:id
    """
    template_name = 'embed_system/embed_product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_id = kwargs.get('product_id')

        try:
            product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
            context['product'] = product

            # 檢查是否有管理權限
            manage_token = self.request.GET.get('tp_manage')
            context['can_manage'] = False

            if manage_token:
                try:
                    payload = jwt.decode(
                        manage_token,
                        settings.SECRET_KEY,
                        algorithms=['HS256']
                    )
                    if (payload.get('product_id') == product_id and
                        payload.get('exp', 0) >= datetime.now().timestamp()):
                        context['can_manage'] = True
                        context['manage_token'] = manage_token
                except jwt.InvalidTokenError:
                    pass

        except Product.DoesNotExist:
            context['error'] = '商品不存在或已下架'

        return context


