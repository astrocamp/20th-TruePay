from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
import json

from .forms import RegisterForm, LoginForm, domain_settings_form
from .models import Merchant
from merchant_marketplace.models import Product
from .services.ticket_service import TicketService
from .services.exceptions import TicketError


# Create your views here.
def register(req):
    if req.method == "POST":
        form = RegisterForm(req.POST)

        if form.is_valid():
            subdomain = form.cleaned_data["subdomain"]
            if Merchant.objects.filter(subdomain=subdomain).exists():
                form.add_error(
                    "subdomain", "此網址已被其他商家註冊了，請重新設定其他網址"
                )
                messages.error(req, "註冊失敗，請重新再試")
            else:
                form.save()
                messages.success(req, "註冊成功！")
                return redirect("merchant_account:login")
        else:
            messages.error(req, "註冊失敗，請重新再試")
    else:
        form = RegisterForm()

    return render(req, "merchant_account/Register.html", {"form": form})


def login(req):
    if req.method == "POST":
        form = LoginForm(req.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                merchant = Merchant.objects.get(Email=email)

                if merchant.Password == password:
                    req.session["merchant_id"] = merchant.id
                    req.session["merchant_name"] = merchant.Name
                    messages.success(req, "歡迎進入！！！")
                    if merchant.subdomain:
                        return redirect(f"/marketplace/?shop={merchant.subdomain}")
                    else:
                        return redirect(f"/marketplace/?shop_id={merchant.id}")
                else:
                    messages.error(req, "密碼錯誤")
            except Merchant.DoesNotExist:
                messages.error(req, "帳號未註冊")
    else:
        form = LoginForm()

    return render(req, "merchant_account/login.html", {"form": form})


def logout(req):
    if "merchant_id" in req.session:
        del req.session["merchant_id"]
    if "merchant_name" in req.session:
        del req.session["merchant_name"]

    storage = messages.get_messages(req)
    for message in storage:
        pass

    messages.success(req, "已成功登出")
    return redirect("merchant_account:login")


def domain_settings(request):
    merchant_id = request.session.get("merchant_id")
    if not merchant_id:
        messages.error(request, "請先登入")
        return redirect("merchant_account:login")
    merchant = get_object_or_404(Merchant, id=merchant_id)
    if request.method == "POST":
        form = domain_settings_form(request.POST, instance=merchant)
        if form.is_valid():
            form.save()
            messages.success(request, "網域名稱已更新")
            return redirect("merchant_account:domain_settings")
        else:
            messages.error(request, "設定失敗，請檢查內容")
    else:
        form = domain_settings_form(instance=merchant)
    return render(request, "merchant_account/domain_settings.html", {"form": form})


def shop_overview(request, subdomain):
    try:
        merchant = Merchant.objects.get(subdomain=subdomain)
        products = Product.objects.filter(merchant=merchant, is_active=True).order_by(
            "-created_at"
        )
        context = {"merchant": merchant, "products": products}
        return render(request, "merchant_account/shop_overview.html", context)
    except Merchant.DoesNotExist:
        return redirect("pages:home")


def merchant_required(view_func):
    """確保商家已登入的裝飾器"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('merchant_id'):
            return JsonResponse({'success': False, 'message': '請先登入'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def qrscan(request):
    """QR掃描頁面"""
    merchant_id = request.session.get('merchant_id')
    if not merchant_id:
        messages.error(request, "請先登入")
        return redirect("merchant_account:login")
    
    merchant = get_object_or_404(Merchant, id=merchant_id)
    return render(request, "merchant_account/qrscan.html", {'merchant': merchant})

@csrf_exempt
@merchant_required
@require_http_methods(["POST"])
def validate_ticket(request):
    """驗證票券API - 返回HTML片段"""
    try:
        # 取得請求數據
        qr_data = _get_qr_data_from_request(request)
        merchant_id = request.session.get('merchant_id')
        
        # Debug 輸出
        print(f"Debug: qr_data={qr_data}, merchant_id={merchant_id}")
        
        # 呼叫服務層處理業務邏輯
        result = TicketService.validate_qr_code(qr_data, merchant_id)
        
        print(f"Debug: Service result={result}")
        
        # 返回成功模板
        return render(request, 'merchant_account/partials/ticket_success.html', result)
        
    except TicketError as e:
        print(f"Debug: TicketError={str(e)}")
        return _render_error(request, str(e))
    except Exception as e:
        print(f"Debug: Exception={str(e)}")
        import traceback
        print(traceback.format_exc())
        return _render_error(request, f'系統錯誤: {str(e)}')

@csrf_exempt
@merchant_required
@require_http_methods(["POST"])
def use_ticket(request):
    """使用票券API - 返回HTML片段"""
    try:
        ticket_code = request.POST.get('ticket_code')
        merchant_id = request.session.get('merchant_id')
        
        # 呼叫服務層處理業務邏輯
        result = TicketService.use_ticket(ticket_code, merchant_id)
        
        # 返回使用成功模板
        return render(request, 'merchant_account/partials/ticket_used.html', result)
        
    except TicketError as e:
        return _render_error(request, str(e))
    except Exception as e:
        return _render_error(request, '使用失敗，系統錯誤')

@csrf_exempt
def restart_scan(request):
    """重新開始掃描 - 返回初始HTML"""
    return render(request, 'merchant_account/partials/scan_ready.html')

# 輔助函數
def _get_qr_data_from_request(request):
    """從請求中取得QR數據"""
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        return data.get('qr_data')
    else:
        return request.POST.get('qr_data')

def _render_error(request, error_message):
    """渲染錯誤模板"""
    return render(request, 'merchant_account/partials/ticket_error.html', {
        'error_message': error_message
    })
