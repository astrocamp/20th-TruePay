from django.shortcuts import render, redirect


# Create your views here.
def home(req):
    return render(req, "Merchant/home.html")
