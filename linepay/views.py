from django.shortcuts import render
import os, uuid, requests
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from orders.models import Order

LINEPAY_CHANNEL_ID = os.getenv("LINEPAY_CHANNEL_ID")
LINEPAY_CHANNEL_SECRET = os.getenv("LINEPAY_CHANNEL_SECRET")
LINEPAY_API_URL = os.getenv("LINEPAY_API_URL", "https://sandbox-api-pay.line.me")
LINEPAY_CONFIRM_URL = os.getenv("LINEPAY_CONFIRM_URL")
LINEPAY_CANCEL_URL = os.getenv("LINEPAY_CANCEL_URL")

def reserve(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    headers = {
        "Content-Type": "application/json",
        "X-LINE-ChannelId": LINEPAY_CHANNEL_ID,
        "X-LINE-ChannelSecret": LINEPAY_CHANNEL_SECRET,
    }

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

    response = requests.post(
        f"{LINEPAY_API_URL}/v3/payments/request",
        headers=headers,
        json=body
    )
    data = response.json()

    if data["returnCode"] == "0000":
        return redirect(data["info"]["paymentUrl"]["web"])
    return JsonResponse(data)
