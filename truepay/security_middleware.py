from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.contrib import messages


class SecurityHeadersMiddleware(MiddlewareMixin):
    """為所有回應加上安全性 headers"""

    def process_response(self, request, response):
        # 為需要登入的頁面加上防快取 headers
        if request.path.startswith("/customers/") and "dashboard" in request.path:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        if request.path.startswith("/marketplace/"):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        # 加入其他安全 headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class SessionSecurityMiddleware(MiddlewareMixin):
    """加強 Session 安全性檢查"""

    def process_request(self, request):
        # 檢查 session 是否過期（額外安全檢查）
        if hasattr(request, "user") and request.user.is_authenticated:
            # 如果是敏感操作路徑，確保 session 是新鮮的
            sensitive_paths = [
                "/customers/dashboard/",
                "/customers/purchase_history/",
                "/marketplace/",
                "/payments/",
            ]

            if any(request.path.startswith(path) for path in sensitive_paths):
                # 檢查 session 中是否有最後活動時間戳記
                last_activity = request.session.get("last_activity")
                if last_activity:
                    import time

                    # 如果超過 30 分鐘沒有活動，強制登出
                    if time.time() - last_activity > 1800:  # 30 minutes
                        from django.contrib.auth import logout

                        logout(request)
                        messages.warning(request, "因長時間未活動，已自動登出")
                        return redirect("customers_account:login")

                # 更新最後活動時間
                import time

                request.session["last_activity"] = time.time()

        return None
