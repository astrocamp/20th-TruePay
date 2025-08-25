from django.shortcuts import render
import os, uuid, requests, hmac, hashlib, base64, json, time, logging
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from linepay.models import Order
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, HttpResponse
from merchant_marketplace.models import Product

LINEPAY_CHANNEL_ID = os.getenv("LINEPAY_CHANNEL_ID")
LINEPAY_CHANNEL_SECRET = os.getenv("LINEPAY_CHANNEL_SECRET")
LINEPAY_API_URL = os.getenv("LINEPAY_API_URL", "https://sandbox-api-pay.line.me")
LINEPAY_CONFIRM_URL = os.getenv("LINEPAY_CONFIRM_URL")
LINEPAY_CANCEL_URL = os.getenv("LINEPAY_CANCEL_URL")

logger = logging.getLogger(__name__)

def generate_line_pay_signature(channel_secret, uri, request_body, nonce):
    """生成 LINE Pay API 所需的 HMAC-SHA256 簽名
    authMacText = channelSecret + uri + queryOrBody + nonce
    """
    auth_mac_text = channel_secret + uri + request_body + nonce
    signature = base64.b64encode(
        hmac.new(
            channel_secret.encode('utf-8'), 
            auth_mac_text.encode('utf-8'), 
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    return signature

def reserve(request, order_id):
    print(">>> DEBUG: reserve 函數被呼叫了")
    order = get_object_or_404(Order, id=order_id)
    print(f">>> DEBUG: 找到訂單 {order.id}, 金額 {order.total_price}")

    body = {
        "amount": order.total_price,
        "currency": "TWD",
        "orderId": str(order.id),
        "packages": [
            {
                "id": "package1",
                "amount": order.total_price,
                "name": "商品包裝",
                "products": [
                    {
                        "name": order.product.name,
                        "quantity": 1,
                        "price": order.total_price,
                    }
                ],
            }
        ],
        "redirectUrls": {
            "confirmUrl": LINEPAY_CONFIRM_URL,
            "cancelUrl": LINEPAY_CANCEL_URL,
        },
    }

    # 生成 nonce 和簽名
    uri = "/v3/payments/request"
    request_body = json.dumps(body, separators=(',', ':'), ensure_ascii=True)
    nonce = str(int(time.time() * 1000))
    signature = generate_line_pay_signature(LINEPAY_CHANNEL_SECRET, uri, request_body, nonce)
    
    headers = {
        "Content-Type": "application/json",
        "X-LINE-ChannelId": LINEPAY_CHANNEL_ID,
        "X-LINE-Authorization": signature,
        "X-LINE-Authorization-Nonce": nonce,
    }

    print(">>> request_body:", request_body)
    
    response = requests.post(
        f"{LINEPAY_API_URL}/v3/payments/request",
        headers=headers,
        data=request_body
    )
    
    print(">>> response.request.body:", response.request.body)
    data = response.json()

    if data["returnCode"] == "0000":
        return redirect(data["info"]["paymentUrl"]["web"])
    return JsonResponse(data)

@csrf_exempt
def confirm(request):
    transaction_id = request.GET.get("transactionId")
    order_id = request.GET.get("orderId")

    if not transaction_id or not order_id:
        return HttpResponseBadRequest("缺少參數")

    order = get_object_or_404(Order, id=order_id)
    
    body = {
        "amount": order.total_price,
        "currency": "TWD",
    }

    # 生成 nonce 和簽名
    uri = f"/v3/payments/{transaction_id}/confirm"
    request_body = json.dumps(body, separators=(',', ':'), ensure_ascii=True)
    nonce = str(int(time.time() * 1000))
    signature = generate_line_pay_signature(LINEPAY_CHANNEL_SECRET, uri, request_body, nonce)
    
    headers = {
        "Content-Type": "application/json",
        "X-LINE-ChannelId": LINEPAY_CHANNEL_ID,
        "X-LINE-Authorization": signature,
        "X-LINE-Authorization-Nonce": nonce,
    }

    r = requests.post(
        f"{LINEPAY_API_URL}/v3/payments/{transaction_id}/confirm",
        headers=headers,
        data=request_body
    )
    data = r.json()

    if data.get("returnCode") == "0000":
        order.status = "paid"
        order.save()
        return HttpResponse("付款成功")
    else:
        return HttpResponseBadRequest(data.get("returnMessage", "確認失敗"))
    
def cancel(request):
    return HttpResponse("使用者取消付款")

def success(request):
    return HttpResponse("付款成功頁（可以設計好看的頁面）")

def canceled(request):
    return HttpResponse("取消付款頁（可以設計好看的頁面）")

@csrf_exempt
def create_order_and_pay(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        if not product_id:
            return HttpResponseBadRequest("缺少商品 ID")
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # 創建訂單
        order = Order.objects.create(
            product=product,
            total_price=product.price,
            status="pending"
        )
        
        # 直接重導向到 reserve
        return redirect("linepay:linepay_reserve", order_id=order.id)
    
    return HttpResponseBadRequest("僅支援 POST 請求")