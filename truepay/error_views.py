from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError


def custom_404_view(request, exception=None):
    """
    自定義 404 錯誤頁面處理器
    """
    context = {
        'request_path': request.path,
        'now': request.timestamp if hasattr(request, 'timestamp') else None,
    }
    return HttpResponseNotFound(render(request, '404.html', context).content)


def custom_500_view(request):
    """
    自定義 500 錯誤頁面處理器
    """
    context = {
        'request_path': request.path,
        'debug': getattr(request, 'debug', False),
        'now': request.timestamp if hasattr(request, 'timestamp') else None,
    }
    return HttpResponseServerError(render(request, '500.html', context).content)