from django.shortcuts import render, redirect, get_object_or_404


def home(req):
    return render(req, "pages/home.html")


def about(req):
    return render(req, "pages/about.html")


def contact(req):
    return render(req, "pages/contact.html")
