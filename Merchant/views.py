from django.shortcuts import render, redirect


# Create your views here.
def new(req):
    return render(req, "Merchant/new.html")


def create(req):
    return render(req, "Merchant/new.html")
