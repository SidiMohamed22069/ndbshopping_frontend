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
    path("vendre/", views.sell, name="sell"),
    path("vendre/confirmation/", views.sell_confirmation, name="sell_confirmation"),
    path("mes-annonces/", views.my_listings, name="my_listings"),
]
