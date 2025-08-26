import hashlib
import hmac
import base64
import json
import requests
import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.conf import settings
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


def process_linepay(order, request):
    """處理 LINE Pay 付款"""
    try:
        # LINE Pay 設定
        channel_id = settings.LINEPAY_CHANNEL_ID
        channel_secret = settings.LINEPAY_CHANNEL_SECRET
        api_url = getattr(settings, 'LINEPAY_API_URL', 'https://sandbox-api-pay.line.me')
        
        # 準備付款資料
        order_data = {
            'amount': int(order.amount),
            'currency': 'TWD',
            'orderId': str(order.id),
            'packages': [{
                'id': str(order.product.id),
                'amount': int(order.amount),
                'products': [{
                    'name': order.product.name,
                    'quantity': order.quantity,
                    'price': int(order.unit_price)
                }]
            }],
            'redirectUrls': {
                'confirmUrl': settings.LINEPAY_CONFIRM_URL,
                'cancelUrl': settings.LINEPAY_CANCEL_URL
            }
        }
        
        # 生成簽名
        uri = '/v3/payments/request'
        nonce = str(int(timezone.now().timestamp()))
        signature = generate_linepay_signature(channel_secret, uri, json.dumps(order_data), nonce)
        
        headers = {
            'Content-Type': 'application/json',
            'X-LINE-ChannelId': channel_id,
            'X-LINE-Authorization-Nonce': nonce,
            'X-LINE-Authorization': signature
        }
        
        # 發送請求到 LINE Pay
        response = requests.post(f"{api_url}{uri}", headers=headers, json=order_data)
        result = response.json()
        
        if result.get('returnCode') == '0000':
            # 儲存交易資訊
            order.provider_transaction_id = result['info']['transactionId']
            order.save()
            
            # 重導向到 LINE Pay
            return redirect(result['info']['paymentUrl']['web'])
        else:
            return JsonResponse({"error": f"LINE Pay 錯誤: {result.get('returnMessage')}"}, status=400)
            
    except Exception as e:
        logger.error(f"LINE Pay 處理失敗: {e}")
        return JsonResponse({"error": "LINE Pay 處理失敗"}, status=500)


@csrf_exempt  
def linepay_confirm(request):
    """LINE Pay 確認付款"""
    try:
        transaction_id = request.GET.get('transactionId')
        order_id = request.GET.get('orderId')
        
        logger.info(f"LINE Pay 回調收到: transaction_id={transaction_id}, order_id={order_id}")
        
        if not transaction_id or not order_id:
            return render(request, 'payments/linepay/payment_result.html', {
                'success': False,
                'message': '缺少必要參數'
            })
        
        order = get_object_or_404(Order, id=order_id)
        
        # 確認付款
        channel_id = settings.LINEPAY_CHANNEL_ID
        channel_secret = settings.LINEPAY_CHANNEL_SECRET
        api_url = getattr(settings, 'LINEPAY_API_URL', 'https://sandbox-api-pay.line.me')
        
        confirm_data = {
            'amount': int(order.amount),
            'currency': 'TWD'
        }
        
        uri = f'/v3/payments/{transaction_id}/confirm'
        nonce = str(int(timezone.now().timestamp()))
        signature = generate_linepay_signature(channel_secret, uri, json.dumps(confirm_data), nonce)
        
        headers = {
            'Content-Type': 'application/json',
            'X-LINE-ChannelId': channel_id,
            'X-LINE-Authorization-Nonce': nonce,
            'X-LINE-Authorization': signature
        }
        
        response = requests.post(f"{api_url}{uri}", headers=headers, json=confirm_data)
        result = response.json()
        
        logger.info(f"LINE Pay 確認回應: {result}")
        
        if result.get('returnCode') == '0000':
            order.status = 'paid'
            order.provider_transaction_id = transaction_id
            order.paid_at = timezone.now()
            order.save()
            
            logger.info(f"訂單 {order_id} 狀態已更新為 paid")
            
            return render(request, 'payments/linepay/payment_success.html', {
                'success': True,
                'order': order,
                'message': '付款成功'
            })
        else:
            logger.warning(f"LINE Pay 確認失敗: returnCode={result.get('returnCode')}, message={result.get('returnMessage')}")
            return render(request, 'payments/linepay/payment_result.html', {
                'success': False,
                'message': result.get('returnMessage', '付款確認失敗')
            })
            
    except Exception as e:
        logger.error(f"LINE Pay 確認失敗: {e}")
        return render(request, 'payments/linepay/payment_result.html', {
            'success': False,
            'message': '付款處理失敗'
        })


def linepay_cancel(request):
    """LINE Pay 取消付款"""
    return render(request, 'payments/linepay/payment_cancel.html', {
        'message': '您已取消付款'
    })


# 工具函數
def generate_linepay_signature(channel_secret, uri, body, nonce):
    """生成 LINE Pay 簽名"""
    message = channel_secret + uri + body + nonce
    signature = base64.b64encode(
        hmac.new(
            channel_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    return signature