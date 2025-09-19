from django.utils.deprecation import MiddlewareMixin

class CSPFrameAncestorsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # 允許所有 Blogger 用戶嵌入（所有 *.blogspot.com 網址）
        response['Content-Security-Policy'] = "frame-ancestors 'self' https://*.blogspot.com"
        return response
