from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from .models import Merchant


# Create your views here.
def register(req):
    if req.method == "POST":
        form = RegisterForm(req.POST)

        if form.is_valid():
            form.save()

            messages.success(req, "註冊成功！")
            return redirect("merchant_account:login")
        else:
            messages.error(req, "註冊失敗，請重新再試")
            pass
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
                    return redirect("pages:home")
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
