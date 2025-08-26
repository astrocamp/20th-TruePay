import hashlib
import hmac
import base64
import json
import requests
import logging
from urllib.parse import parse_qs
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from .models import Order
from customers_account.models import Customer
from merchant_marketplace.models import Product


logger = logging.getLogger(__name__)


@csrf_exempt
def create_payment(request):
    """統一付款入口 - 支援藍新金流和 LINE Pay"""
    if request.method == "POST":
        # 檢查登入狀態
        if not request.user.is_authenticated:
            request.session['payment_data'] = {
                'provider': request.POST.get('provider'),
                'product_id': request.POST.get('product_id'),
                'amt': request.POST.get('amt'),
                'item_desc': request.POST.get('item_desc')
            }
            login_url = reverse('customers_account:login')
            next_url = request.get_full_path()
            return redirect(f"{login_url}?next={next_url}")
        
        # 取得參數
        provider = request.POST.get('provider')
        product_id = request.POST.get('product_id')
        amt = request.POST.get('amt')
        item_desc = request.POST.get('item_desc')
        
        # 調試：記錄 POST 資料
        logger.info(f"POST data: {dict(request.POST)}")
        logger.info(f"provider: {provider}, product_id: {product_id}, amt: {amt}")
        
        if not provider:
            return JsonResponse({"error": "缺少付款方式參數"}, status=400)
        
        if provider not in ['newebpay', 'linepay']:
            return JsonResponse({"error": f"無效的付款方式: {provider}"}, status=400)
        
        try:
            # 透過 email 找到對應的 Customer
            customer = Customer.objects.get(email=request.user.email)
            
            # 根據不同的金流處理參數
            if provider == 'newebpay':
                # 藍新金流：從 amt 和 item_desc 創建付款
                amount = int(float(amt))
                if '|ProductID:' in item_desc:
                    product_id = item_desc.split('|ProductID:')[1]
                else:
                    return JsonResponse({"error": "商品資訊錯誤"}, status=400)
                
            elif provider == 'linepay':
                # LINE Pay：直接使用 product_id
                if not product_id:
                    return JsonResponse({"error": "缺少商品ID"}, status=400)
                product = get_object_or_404(Product, id=product_id, is_active=True)
                amount = product.price
            
            # 取得商品資訊
            product = get_object_or_404(Product, id=int(product_id), is_active=True)
            
            # 建立訂單記錄
            order = Order.objects.create(
                provider=provider,
                amount=amount,
                item_description=f"{product.name}|ProductID:{product.id}",
                product=product,
                customer=customer,
                quantity=1,
                unit_price=product.price,
                status='pending'
            )
            
            # 清除暫存的付款資料
            if 'payment_data' in request.session:
                del request.session['payment_data']
            
            # 處理不同的金流
            if provider == 'newebpay':
                return process_newebpay(order, request)
            elif provider == 'linepay':
                return process_linepay(order, request)
                
        except Customer.DoesNotExist:
            return JsonResponse({"error": "客戶資料不存在"}, status=400)
        except Exception as e:
            logger.error(f"創建付款失敗: {e}")
            return JsonResponse({"error": "付款處理失敗"}, status=500)
    
    # GET 請求：檢查是否有暫存的付款資料
    if not request.user.is_authenticated:
        login_url = reverse('customers_account:login')
        next_url = request.get_full_path()
        return redirect(f"{login_url}?next={next_url}")
    
    # 如果有暫存的付款資料，直接處理付款
    payment_data = request.session.get('payment_data')
    if payment_data:
        try:
            # 透過 email 找到對應的 Customer
            customer = Customer.objects.get(email=request.user.email)
            
            # 取得參數
            provider = payment_data.get('provider')
            product_id = payment_data.get('product_id')
            amt = payment_data.get('amt')
            item_desc = payment_data.get('item_desc')
            
            if not provider or provider not in ['newebpay', 'linepay']:
                messages.error(request, "無效的付款方式")
                return redirect("pages:home")
            
            # 根據不同的金流處理參數
            if provider == 'newebpay':
                # 藍新金流：從 amt 和 item_desc 創建付款
                amount = int(float(amt))
                if '|ProductID:' in item_desc:
                    product_id = item_desc.split('|ProductID:')[1]
                else:
                    messages.error(request, "商品資訊錯誤")
                    return redirect("pages:home")
                    
            elif provider == 'linepay':
                # LINE Pay：直接使用 product_id
                if not product_id:
                    messages.error(request, "缺少商品ID")
                    return redirect("pages:home")
                product = get_object_or_404(Product, id=product_id, is_active=True)
                amount = product.price
            
            # 取得商品資訊
            product = get_object_or_404(Product, id=int(product_id), is_active=True)
            
            # 建立訂單記錄
            order = Order.objects.create(
                provider=provider,
                amount=amount,
                item_description=f"{product.name}|ProductID:{product.id}",
                product=product,
                customer=customer,
                quantity=1,
                unit_price=product.price,
                status='pending'
            )
            
            # 清除暫存的付款資料
            del request.session['payment_data']
            
            # 處理不同的金流
            if provider == 'newebpay':
                return process_newebpay(order, request)
            elif provider == 'linepay':
                return process_linepay(order, request)
                
        except Customer.DoesNotExist:
            messages.error(request, "客戶資料不存在")
            return redirect("pages:home")
        except Exception as e:
            logger.error(f"創建付款失敗: {e}")
            messages.error(request, "付款處理失敗")
            return redirect("pages:home")
    
    # 沒有付款資料，重導向回首頁
    return redirect("pages:home")


def process_newebpay(order, request):
    """處理藍新金流付款"""
    try:
        # 藍新金流設定
        merchant_id = settings.NEWEBPAY_MERCHANT_ID
        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV
        
        # 準備付款資料
        trade_info_data = {
            'MerchantID': merchant_id,
            'RespondType': 'JSON',
            'TimeStamp': str(int(order.created_at.timestamp())),
            'Version': '2.0',
            'MerchantOrderNo': order.provider_order_id,  # 使用短格式訂單編號
            'Amt': str(int(order.amount)),
            'ItemDesc': order.item_description,
            'ReturnURL': settings.PAYMENT_RETURN_URL,
            'NotifyURL': settings.PAYMENT_NOTIFY_URL,
            'Email': order.customer.email,
        }
        
        # 生成 TradeInfo 和 TradeSha
        trade_info_str = '&'.join([f'{k}={v}' for k, v in trade_info_data.items()])
        logger.info(f"Before encrypt: {trade_info_str}")
        
        trade_info = aes_encrypt(trade_info_str, hash_key, hash_iv)
        trade_sha = generate_sha256(f'HashKey={hash_key}&{trade_info}&HashIV={hash_iv}')
        
        logger.info(f"TradeInfo: {trade_info}")
        logger.info(f"TradeSha: {trade_sha}")
        
        # 直接重導向到藍新金流
        from django.http import HttpResponse
        
        form_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>正在跳轉到藍新金流...</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px;">
                <h3>正在跳轉到藍新金流付款頁面...</h3>
                <p>如果頁面沒有自動跳轉，請點擊下方按鈕</p>
                <form id="newebpay_form" method="POST" action="{settings.NEWEBPAY_GATEWAY_URL}">
                    <input type="hidden" name="MerchantID" value="{merchant_id}">
                    <input type="hidden" name="TradeInfo" value="{trade_info}">
                    <input type="hidden" name="TradeSha" value="{trade_sha}">
                    <input type="hidden" name="Version" value="2.0">
                    <button type="submit" style="background: #0056B3; color: white; padding: 10px 20px; border: none; border-radius: 5px;">
                        前往付款
                    </button>
                </form>
                <script>
                    document.getElementById('newebpay_form').submit();
                </script>
            </div>
        </body>
        </html>
        '''
        
        return HttpResponse(form_html)
        
    except Exception as e:
        logger.error(f"藍新金流處理失敗: {e}")
        return JsonResponse({"error": "藍新金流處理失敗"}, status=500)


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


@login_required(login_url='/customers/login/')
def payment_status(request, order_id):
    """查詢訂單狀態"""
    order = get_object_or_404(Order, id=order_id)
    
    # 透過 email 找到對應的 Customer
    try:
        customer = Customer.objects.get(email=request.user.email)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect('pages:home')
    
    # 確保用戶只能查看自己的訂單記錄
    if order.customer_id != customer.id:
        messages.error(request, "您沒有權限查看此訂單記錄")
        return redirect('pages:home')
    
    context = {
        "order": order,
    }
    return render(request, "payments/payment_status.html", context)


# 藍新金流回調處理
@csrf_exempt
def newebpay_return(request):
    """藍新金流付款完成返回處理"""
    try:
        trade_info = request.POST.get('TradeInfo')
        trade_sha = request.POST.get('TradeSha')
        
        logger.info(f"Received TradeInfo: {trade_info}")
        logger.info(f"Received TradeSha: {trade_sha}")
        
        # 解密交易資料
        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV
        
        # 驗證簽名
        check_value = generate_sha256(f'HashKey={hash_key}&{trade_info}&HashIV={hash_iv}')
        if check_value.upper() != trade_sha.upper():
            logger.error(f"簽名驗證失敗 - Expected: {check_value.upper()}, Got: {trade_sha.upper()}")
            return render(request, 'payments/newebpay/payment_result.html', {
                'success': False,
                'message': '簽名驗證失敗'
            })
        
        # 解密資料
        decrypted_data = aes_decrypt(trade_info, hash_key, hash_iv)
        logger.info(f"Decrypted data: {decrypted_data}")
        result_data = json.loads(decrypted_data)
        logger.info(f"Parsed result: {result_data}")
        
        if result_data['Status'] == 'SUCCESS':
            # 更新付款狀態
            merchant_order_no = result_data['Result']['MerchantOrderNo']
            order = get_object_or_404(Order, provider_order_id=merchant_order_no)
            order.status = 'paid'
            order.provider_transaction_id = result_data['Result']['TradeNo']
            order.newebpay_trade_no = result_data['Result']['TradeNo']
            
            # 儲存詳細付款資訊 (如果有的話)
            result = result_data['Result']
            if 'PaymentType' in result:
                order.newebpay_payment_type = result['PaymentType']
            if 'CardInfo' in result and result['CardInfo']:
                card_info = result['CardInfo']
                if 'Card6No' in card_info and 'Card4No' in card_info:
                    order.newebpay_card_info = f"{card_info['Card6No']}******{card_info['Card4No']}"
            
            # 儲存完整原始資料
            order.provider_raw_data = result_data
            order.paid_at = timezone.now()
            order.save()
            
            return render(request, 'payments/newebpay/payment_success.html', {
                'success': True,
                'order': order,
                'message': '付款成功'
            })
        else:
            return render(request, 'payments/newebpay/payment_result.html', {
                'success': False,
                'message': result_data.get('Message', '付款失敗')
            })
            
    except Exception as e:
        logger.error(f"藍新金流回調處理失敗: {e}")
        return render(request, 'payments/newebpay/payment_result.html', {
            'success': False,
            'message': '付款處理失敗'
        })


@csrf_exempt 
def newebpay_notify(request):
    """藍新金流後台通知處理"""
    try:
        # 記錄收到的原始資料
        trade_info = request.POST.get('TradeInfo')
        trade_sha = request.POST.get('TradeSha')
        
        logger.info(f"藍新金流通知 - TradeInfo: {trade_info}")
        logger.info(f"藍新金流通知 - TradeSha: {trade_sha}")
        logger.info(f"藍新金流通知 - 所有 POST 資料: {dict(request.POST)}")
        
        if not trade_info:
            logger.error("藍新金流通知缺少 TradeInfo")
            return HttpResponse('0|Missing TradeInfo')
        
        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV
        
        if not hash_key or not hash_iv:
            logger.error("藍新金流設定不完整 - 缺少 hash_key 或 hash_iv")
            return HttpResponse('0|Config Error')
        
        # 記錄加密設定（不記錄實際值）
        logger.info(f"Key 長度: {len(hash_key) if hash_key else 0}, IV 長度: {len(hash_iv) if hash_iv else 0}")
        
        # 如果有 TradeSha，先驗證簽名
        if trade_sha:
            check_value = generate_sha256(f'HashKey={hash_key}&{trade_info}&HashIV={hash_iv}')
            if check_value.upper() != trade_sha.upper():
                logger.error(f"藍新金流通知簽名驗證失敗 - Expected: {check_value.upper()}, Got: {trade_sha.upper()}")
                return HttpResponse('0|Invalid Signature')
        
        # 嘗試解密
        try:
            decrypted_data = aes_decrypt(trade_info, hash_key, hash_iv)
            logger.info(f"藍新金流通知解密成功: {decrypted_data}")
        except Exception as decrypt_error:
            logger.error(f"AES 解密失敗: {decrypt_error}")
            logger.error(f"TradeInfo 長度: {len(trade_info)}")
            logger.error(f"TradeInfo 內容 (前50字符): {trade_info[:50]}...")
            return HttpResponse('0|Decrypt Error')
        
        # 解析 JSON 資料
        try:
            result_data = json.loads(decrypted_data)
            logger.info(f"藍新金流通知解析 JSON 成功: {result_data}")
        except json.JSONDecodeError as json_error:
            logger.error(f"JSON 解析失敗: {json_error}")
            logger.error(f"解密後的資料: {decrypted_data}")
            return HttpResponse('0|JSON Parse Error')
        
        # 處理付款結果
        if result_data.get('Status') == 'SUCCESS':
            try:
                merchant_order_no = result_data['Result']['MerchantOrderNo']
                order = Order.objects.get(provider_order_id=merchant_order_no)
                
                if order.status == 'pending':
                    order.status = 'paid'
                    order.provider_transaction_id = result_data['Result']['TradeNo']
                    order.newebpay_trade_no = result_data['Result']['TradeNo']
                    
                    # 儲存詳細付款資訊 (如果有的話)
                    result = result_data['Result']
                    if 'PaymentType' in result:
                        order.newebpay_payment_type = result['PaymentType']
                    if 'CardInfo' in result and result['CardInfo']:
                        card_info = result['CardInfo']
                        if 'Card6No' in card_info and 'Card4No' in card_info:
                            order.newebpay_card_info = f"{card_info['Card6No']}******{card_info['Card4No']}"
                    
                    # 儲存完整原始資料
                    order.provider_raw_data = result_data
                    order.paid_at = timezone.now()
                    order.save()
                    
                    logger.info(f"藍新金流通知處理成功 - 訂單 {merchant_order_no} 已更新為已付款")
                else:
                    logger.info(f"藍新金流通知 - 訂單 {merchant_order_no} 狀態已是 {order.status}")
                
                return HttpResponse('1|OK')
                
            except Order.DoesNotExist:
                logger.error(f"藍新金流通知 - 找不到訂單: {merchant_order_no}")
                return HttpResponse('0|Order Not Found')
            except Exception as order_error:
                logger.error(f"藍新金流通知處理訂單時發生錯誤: {order_error}")
                return HttpResponse('0|Order Update Error')
        else:
            logger.warning(f"藍新金流通知 - 付款失敗: {result_data}")
            return HttpResponse('0|Payment Failed')
            
    except Exception as e:
        logger.error(f"藍新金流通知處理失敗: {e}")
        return HttpResponse('0|System Error')


# LINE Pay 回調處理
@csrf_exempt
def linepay_confirm(request):
    """LINE Pay 確認付款"""
    try:
        transaction_id = request.GET.get('transactionId')
        order_id = request.GET.get('orderId')
        
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
        
        if result.get('returnCode') == '0000':
            order.status = 'paid'
            order.provider_transaction_id = transaction_id
            order.paid_at = timezone.now()
            order.save()
            
            return render(request, 'payments/linepay/payment_success.html', {
                'success': True,
                'order': order,
                'message': '付款成功'
            })
        else:
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
def aes_encrypt(data, key, iv):
    """AES 加密 - 藍新金流使用十六進制格式"""
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return encrypted_data.hex()  # 使用十六進制，不是 Base64


def aes_decrypt(encrypted_data, key, iv):
    """AES 解密 - 自動檢測編碼格式"""
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    
    # 記錄輸入資料資訊（不記錄實際內容以保護安全）
    logger.info(f"解密輸入資料長度: {len(encrypted_data)}")
    logger.info(f"Key/IV 長度: {len(key)}/{len(iv)}")
    
    # 先嘗試十六進制解碼（發送給藍新的格式）
    try:
        logger.info("嘗試十六進制解密...")
        decrypted_data = cipher.decrypt(bytes.fromhex(encrypted_data))
        result = unpad(decrypted_data, AES.block_size).decode('utf-8')
        logger.info("十六進制解密成功")
        return result
    except ValueError as hex_error:
        logger.warning(f"十六進制解密失敗: {hex_error}")
    except Exception as hex_error:
        logger.warning(f"十六進制解密過程出錯: {hex_error}")
    
    # 如果失敗，嘗試 Base64 解碼（回調可能使用的格式）
    try:
        logger.info("嘗試 Base64 解密...")
        decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))
        result = unpad(decrypted_data, AES.block_size).decode('utf-8')
        logger.info("Base64 解密成功")
        return result
    except ValueError as b64_error:
        logger.error(f"Base64 解密失敗: {b64_error}")
    except Exception as b64_error:
        logger.error(f"Base64 解密過程出錯: {b64_error}")
    
    # 如果兩種方式都失敗，嘗試直接解碼（以防是其他格式）
    try:
        logger.info("嘗試直接二進制解密...")
        decrypted_data = cipher.decrypt(encrypted_data.encode('utf-8'))
        result = unpad(decrypted_data, AES.block_size).decode('utf-8')
        logger.info("直接二進制解密成功")
        return result
    except Exception as direct_error:
        logger.error(f"直接二進制解密失敗: {direct_error}")
    
    # 所有方法都失敗
    raise ValueError("所有解密方法都失敗了 - 可能是加密格式、Key 或 IV 不正確")


def generate_sha256(data):
    """生成 SHA256"""
    return hashlib.sha256(data.encode('utf-8')).hexdigest().upper()


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