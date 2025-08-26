from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CustomerRegistrationForm, CustomerLoginForm
from .models import Customer
from newebpay.models import Payment
from merchant_marketplace.models import Product


def register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            try:
                customer = form.save()
                messages.success(request, "註冊成功！請登入您的帳號。")
                return redirect("customers_account:login")
            except Exception as e:
                messages.error(request, "註冊失敗，請重試。")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CustomerRegistrationForm()

    return render(request, "customers/register.html", {"form": form})


def login(request):
    if request.method == "POST":
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data["customer"]
            customer.update_last_login()

            # 在這裡可以設定 session 或其他登入狀態管理
            request.session["customer_id"] = customer.id
            request.session["customer_name"] = customer.name

            return redirect("customers_account:dashboard")  # 重定向到用戶dashboard
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CustomerLoginForm()

    return render(request, "customers/login.html", {"form": form})


def logout(request):
    # 清除 session
    if "customer_id" in request.session:
        del request.session["customer_id"]
    if "customer_name" in request.session:
        del request.session["customer_name"]

    messages.success(request, "已成功登出")
    return redirect("pages:home")


def dashboard(request):
    """用戶dashboard - 查看購買的商品"""
    # 檢查用戶是否已登入
    if "customer_id" not in request.session:
        messages.error(request, "請先登入")
        return redirect("customers_account:login")
    
    try:
        customer_id = request.session["customer_id"]
        customer = Customer.objects.get(id=customer_id)
        
        # 取得該用戶的付款記錄（已付款的訂單）
        paid_orders = Payment.objects.filter(
            email=customer.email,
            status='paid'
        ).order_by('-created_at')
        
        # 創建一個包含商品信息的列表
        order_details = []
        total_amount = 0
        
        for payment in paid_orders:
            # 這裡我們假設可以從payment的item_desc中獲取商品信息
            # 在實際應用中，你可能需要更複雜的關聯邏輯
            order_info = {
                'payment': payment,
                'order_no': payment.merchant_order_no,
                'amount': payment.amt,
                'item_description': payment.item_desc,
                'payment_time': payment.pay_time,
                'payment_type': payment.payment_type,
            }
            order_details.append(order_info)
            total_amount += payment.amt
        
        context = {
            'customer': customer,
            'order_details': order_details,
            'total_orders': len(order_details),
            'total_amount': total_amount
        }
        
        return render(request, "customers/dashboard.html", context)
        
    except Customer.DoesNotExist:
        messages.error(request, "用戶不存在")
        return redirect("customers_account:login")
    except Exception as e:
        messages.error(request, "載入資料時發生錯誤")
        return redirect("pages:home")


def use_ticket(request, order_no):
    """票券使用頁面"""
    # 檢查用戶是否已登入
    if "customer_id" not in request.session:
        messages.error(request, "請先登入")
        return redirect("customers_account:login")
    
    try:
        customer_id = request.session["customer_id"]
        customer = Customer.objects.get(id=customer_id)
        
        # 查找該用戶的付款記錄
        payment = Payment.objects.get(
            merchant_order_no=order_no,
            email=customer.email,
            status='paid'
        )
        
        context = {
            'customer': customer,
            'payment': payment,
            'ticket_type': '電子票券',
            'venue_info': {
                'name': '台北小巨蛋',
                'address': '台北市松山區南京東路四段2號',
                'date': '2024-11-10',
                'time': '19:00',
                'gate': 'A區入口',
                'seat': 'VIP區 A1-15'
            }
        }
        
        return render(request, "customers/use_ticket.html", context)
        
    except Payment.DoesNotExist:
        messages.error(request, "找不到該票券記錄")
        return redirect("customers_account:dashboard")
    except Customer.DoesNotExist:
        messages.error(request, "用戶不存在")
        return redirect("customers_account:login")
    except Exception as e:
        messages.error(request, "載入票券時發生錯誤")
        return redirect("customers_account:dashboard")
