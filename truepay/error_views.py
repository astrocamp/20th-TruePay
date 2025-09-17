from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest


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


def custom_403_view(request, exception=None):
    """
    自定義 403 權限拒絕錯誤頁面處理器
    """
    context = {
        'request_path': request.path,
        'user': request.user,
        'now': request.timestamp if hasattr(request, 'timestamp') else None,
    }
    return HttpResponseForbidden(render(request, '403.html', context).content)


def custom_400_view(request, exception=None):
    """
    自定義 400 錯誤請求頁面處理器
    """
    context = {
        'request_path': request.path,
        'now': request.timestamp if hasattr(request, 'timestamp') else None,
    }
    return HttpResponseBadRequest(render(request, '400.html', context).content)