from django.http import Http404, HttpResponseServerError
from django.shortcuts import render
from .error_views import custom_404_view, custom_500_view


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