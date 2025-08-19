from django.shortcuts import render


# Create your views here.
def session(req):
    return render(req, "MerchantAcount/Session.html")


def register(req):
    return render(req, "MerchantAcount/Register.html")
