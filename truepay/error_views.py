from django.shortcuts import render
from django.utils import timezone


def custom_404_view(request, exception=None):
    """
    自定義 404 錯誤頁面處理器
    """
    context = {
        'request_path': request.path,
        'now': timezone.now(),
    }
    return render(request, '404.html', context, status=404)


def custom_500_view(request):
    """
    自定義 500 錯誤頁面處理器
    """
    context = {
        'request_path': request.path,
        'debug': getattr(request, 'debug', False),
        'now': timezone.now(),
    }
    return render(request, '500.html', context, status=500)


def custom_403_view(request, exception=None):
    """
    自定義 403 權限拒絕錯誤頁面處理器
    """
    context = {
        'request_path': request.path,
        'user': request.user,
        'now': timezone.now(),
    }
    return render(request, '403.html', context, status=403)


def custom_400_view(request, exception=None):
    """
    自定義 400 錯誤請求頁面處理器
    """
    context = {
        'request_path': request.path,
        'now': timezone.now(),
    }
    return render(request, '400.html', context, status=400)