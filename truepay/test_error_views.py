from django.http import Http404, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from .error_views import custom_404_view, custom_500_view, custom_403_view, custom_400_view


def test_404_view(request):
    """
    測試404錯誤頁面的視圖
    """
    return custom_404_view(request)


def test_500_view(request):
    """
    測試500錯誤頁面的視圖
    """
    return custom_500_view(request)


def test_403_view(request):
    """
    測試403錯誤頁面的視圖
    """
    return custom_403_view(request)


def test_400_view(request):
    """
    測試400錯誤頁面的視圖
    """
    return custom_400_view(request)


def trigger_404_view(request):
    """
    觸發404錯誤
    """
    raise Http404("測試頁面：故意觸發404錯誤")


def trigger_500_view(request):
    """
    觸發500錯誤
    """
    raise Exception("測試頁面：故意觸發500錯誤")


def trigger_403_view(request):
    """
    觸發403權限拒絕錯誤
    """
    raise PermissionDenied("測試頁面：故意觸發403權限拒絕錯誤")


def trigger_400_view(request):
    """
    觸發400錯誤請求
    """
    raise SuspiciousOperation("測試頁面：故意觸發400錯誤請求")