from django.urls import path
from . import views

app_names = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="home"),
    path("contact/", views.contact, name="home"),
]
