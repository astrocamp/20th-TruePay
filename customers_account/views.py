from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from .forms import CustomerRegistrationForm, CustomerLoginForm
from .models import Customer, PurchaseRecord


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

            # 檢查是否有 next 參數（登入後要重導向的頁面）
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                messages.success(request, "登入成功")
                return redirect(next_url)
            else:
                messages.success(request, "登入成功")
                return redirect("pages:home")  # 沒有指定頁面則重定向到首頁
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


def purchase_history(request):
    """消費者購買記錄頁面"""
    # 檢查用戶是否已登入
    if 'customer_id' not in request.session:
        messages.error(request, "請先登入以查看購買記錄")
        return redirect("customers_account:login")
    
    customer_id = request.session['customer_id']
    customer = get_object_or_404(Customer, id=customer_id)
    
    # 根據 customer 直接查詢購買記錄
    purchase_records = PurchaseRecord.objects.select_related(
        'payment', 'product__merchant'
    ).filter(
        customer=customer
    ).order_by('-payment__created_at')
    
    # 分頁處理
    paginator = Paginator(purchase_records, 10)  # 每頁顯示10筆記錄
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customer': customer,
        'page_obj': page_obj,
        'purchase_records': page_obj
    }
    
    return render(request, 'customers/purchase_history.html', context)
