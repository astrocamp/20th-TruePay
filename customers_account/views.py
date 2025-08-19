from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CustomerRegistrationForm, CustomerLoginForm


def customer_register(request):
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

    return render(request, "customers/customer_register.html", {"form": form})


def customer_login(request):
    if request.method == "POST":
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data["customer"]
            customer.update_last_login()

            # 在這裡可以設定 session 或其他登入狀態管理
            request.session["customer_id"] = customer.id
            request.session["customer_name"] = customer.name

            return redirect("pages:home")  # 重定向到首頁
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CustomerLoginForm()

    return render(request, "customers/customer_login.html", {"form": form})


def customer_logout(request):
    # 清除 session
    if "customer_id" in request.session:
        del request.session["customer_id"]
    if "customer_name" in request.session:
        del request.session["customer_name"]

    messages.success(request, "已成功登出")
    return redirect("pages:home")
