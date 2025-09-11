import base64
import hashlib
import hmac
import json
import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import login as django_login
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Member
from .models import Order

logger = logging.getLogger(__name__)


def process_linepay(order, request):
    """處理 LINE Pay 付款"""
    try:
        # 使用系統統一 LINE Pay 設定
        channel_id = settings.LINEPAY_CHANNEL_ID
        channel_secret = settings.LINEPAY_CHANNEL_SECRET

        api_url = getattr(
            settings, "LINEPAY_API_URL", "https://sandbox-api-pay.line.me"
        )

        # 為重新付款生成唯一的 LINE Pay orderId
        is_retry = order.updated_at != order.created_at
        if is_retry:
            # 重新付款時生成唯一的 orderId
            retry_suffix = str(int(timezone.now().timestamp()))
            linepay_order_id = f"{order.id}-retry-{retry_suffix}"
        else:
            # 首次付款使用原始訂單ID
            linepay_order_id = str(order.id)

        # 準備付款資料
        order_data = {
            "amount": int(order.amount),
            "currency": "TWD",
            "orderId": linepay_order_id,
            "packages": [
                {
                    "id": str(order.product.id),
                    "amount": int(order.amount),
                    "products": [
                        {
                            "name": order.product.name,
                            "quantity": order.quantity,
                            "price": int(order.unit_price),
                        }
                    ],
                }
            ],
            "redirectUrls": {
                "confirmUrl": settings.LINEPAY_CONFIRM_URL,
                "cancelUrl": settings.LINEPAY_CANCEL_URL,
            },
        }

        # 生成簽名
        uri = "/v3/payments/request"
        nonce = str(int(timezone.now().timestamp()))
        signature = generate_linepay_signature(
            channel_secret, uri, json.dumps(order_data), nonce
        )

        headers = {
            "Content-Type": "application/json",
            "X-LINE-ChannelId": channel_id,
            "X-LINE-Authorization-Nonce": nonce,
            "X-LINE-Authorization": signature,
        }

        # 發送請求到 LINE Pay
        response = requests.post(f"{api_url}{uri}", headers=headers, json=order_data)
        result = response.json()

        if result.get("returnCode") == "0000":
            # 儲存交易資訊
            order.provider_transaction_id = result["info"]["transactionId"]
            order.linepay_payment_url = result["info"]["paymentUrl"]["web"]
            order.save()

            # 重導向到 LINE Pay
            return redirect(result["info"]["paymentUrl"]["web"])
        else:
            return JsonResponse(
                {"error": f"LINE Pay 錯誤: {result.get('returnMessage')}"}, status=400
            )

    except Exception as e:
        logger.error(f"LINE Pay 處理失敗: {e}")
        
        # 檢查是否為庫存不足錯誤
        error_msg = str(e)
        if "庫存不足" in error_msg or "庫存扣減失敗" in error_msg:
            # 嘗試從訂單中獲取必要資訊
            try:
                params = urlencode({
                    'product_id': order.product.id,
                    'requested_quantity': order.quantity
                })
                return redirect(f"{reverse('payments:stock_insufficient_error')}?{params}")
            except:
                pass
        
        return JsonResponse({"error": "LINE Pay 處理失敗"}, status=500)


@csrf_exempt
def linepay_confirm(request):
    """LINE Pay 確認付款"""
    try:
        transaction_id = request.GET.get("transactionId")
        linepay_order_id = request.GET.get("orderId")

        if not transaction_id or not linepay_order_id:
            return render(
                request,
                "payments/linepay/payment_result.html",
                {"success": False, "message": "缺少必要參數"},
            )

        # 解析 LINE Pay orderId 以獲取真實的訂單ID
        # 格式可能是 "123" 或 "123-retry-1693817234"
        if "-retry-" in linepay_order_id:
            # 重新付款的情況，提取原始訂單ID
            real_order_id = linepay_order_id.split("-retry-")[0]
        else:
            # 首次付款的情況
            real_order_id = linepay_order_id

        order = get_object_or_404(Order, id=int(real_order_id))

        # 使用系統統一 LINE Pay 設定
        channel_id = settings.LINEPAY_CHANNEL_ID
        channel_secret = settings.LINEPAY_CHANNEL_SECRET

        api_url = getattr(
            settings, "LINEPAY_API_URL", "https://sandbox-api-pay.line.me"
        )

        confirm_data = {"amount": int(order.amount), "currency": "TWD"}

        uri = f"/v3/payments/{transaction_id}/confirm"
        nonce = str(int(timezone.now().timestamp()))
        signature = generate_linepay_signature(
            channel_secret, uri, json.dumps(confirm_data), nonce
        )

        headers = {
            "Content-Type": "application/json",
            "X-LINE-ChannelId": channel_id,
            "X-LINE-Authorization-Nonce": nonce,
            "X-LINE-Authorization": signature,
        }

        response = requests.post(f"{api_url}{uri}", headers=headers, json=confirm_data)
        result = response.json()

        if result.get("returnCode") == "0000":
            order.status = "paid"
            order.provider_transaction_id = transaction_id
            order.paid_at = timezone.now()
            order.save()

            # 付款成功後扣減庫存
            _deduct_product_stock(order)

            # 付款成功後恢復用戶登入狀態（金流回調不攜帶 session）
            if order.customer:
                try:
                    # 直接使用已存在的 Member 記錄（不要創建新的）
                    member = order.customer.member
                    # 建立用戶認證 session
                    django_login(request, member, backend='django.contrib.auth.backends.ModelBackend')
                    logger.info(
                        f"LINE Pay 付款成功，已為用戶 {order.customer.member.email} 恢復登入狀態"
                    )
                except Exception as e:
                    logger.warning(f"LINE Pay 付款成功後恢復登入狀態失敗: {e}")

            return render(
                request,
                "payments/linepay/payment_success.html",
                {"success": True, "order": order, "message": "付款成功"},
            )
        else:
            logger.warning(
                f"LINE Pay 確認失敗: returnCode={result.get('returnCode')}, message={result.get('returnMessage')}"
            )
            return render(
                request,
                "payments/linepay/payment_result.html",
                {
                    "success": False,
                    "message": result.get("returnMessage", "付款確認失敗"),
                },
            )

    except Exception as e:
        logger.error(f"LINE Pay 確認失敗: {e}")
        return render(
            request,
            "payments/linepay/payment_result.html",
            {"success": False, "message": "付款處理失敗"},
        )


def linepay_cancel(request):
    """LINE Pay 取消付款"""
    return render(
        request, "payments/linepay/payment_cancel.html", {"message": "您已取消付款"}
    )


def _deduct_product_stock(order):
    """扣減商品庫存"""
    try:
        with transaction.atomic():
            product = order.product
            rows_updated = product.__class__.objects.filter(
                id=product.id, stock__gte=order.quantity  # 確保庫存足夠
            ).update(stock=F("stock") - order.quantity)

            if rows_updated == 0:
                error_msg = f"訂單 {order.provider_order_id} 庫存扣減失敗 - 庫存不足或商品不存在"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.info(
                    f"訂單 {order.provider_order_id} 成功扣減 {order.quantity} 件庫存"
                )

    except Exception as e:
        logger.error(f"扣減庫存時發生錯誤: {e}")
        raise


# 工具函數
def generate_linepay_signature(channel_secret, uri, body, nonce):
    """生成 LINE Pay 簽名"""
    message = channel_secret + uri + body + nonce
    signature = base64.b64encode(
        hmac.new(
            channel_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).digest()
    ).decode("utf-8")
    return signature
