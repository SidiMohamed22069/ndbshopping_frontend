from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.detail, name="detail"),
    path("ajouter/", views.add, name="add"),
    path("modifier/", views.update, name="update"),
    path("retirer/", views.remove, name="remove"),
]
