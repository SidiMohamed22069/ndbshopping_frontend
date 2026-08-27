from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "api/categories/<int:category_id>/attributes/",
        views.category_attributes_json,
        name="category_attributes",
    ),
]
