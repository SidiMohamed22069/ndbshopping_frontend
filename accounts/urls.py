from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("connexion/", views.login_view, name="login"),
    path("inscription/", views.register_view, name="register"),
    path("otp/", views.otp_view, name="otp"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("commander/", views.checkout, name="checkout"),
    path("commandes/", views.orders, name="orders"),
]
