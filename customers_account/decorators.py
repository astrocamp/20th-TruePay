from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps


def customer_login_required(view_func):
    """
    自定義的客戶登入檢查裝飾器
    檢查 session 中是否有 customer_id
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'customer_id' not in request.session:
            # 建立登入URL，並加上 next 參數
            login_url = reverse('customers_account:login')
            next_url = request.get_full_path()
            return redirect(f"{login_url}?next={next_url}")
        return view_func(request, *args, **kwargs)
    return wrapper