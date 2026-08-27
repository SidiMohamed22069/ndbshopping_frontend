from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("produits/", views.product_list, name="product_list"),
    path("produits/<int:product_id>/", views.product_detail, name="product_detail"),
    path("categories/", views.categories, name="categories"),
    path("categories/<int:category_id>/", views.product_list, name="category_products"),
    path("actualites/", views.publication_list, name="publication_list"),
    path("actualites/<int:publication_id>/", views.publication_detail, name="publication_detail"),
]
