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
    path("vendre/<int:product_id>/medias/", views.sell_media, name="sell_media"),
    path(
        "vendre/<int:product_id>/medias/images/",
        views.sell_media_image_add,
        name="sell_media_image_add",
    ),
    path(
        "vendre/<int:product_id>/medias/images/<int:image_id>/supprimer/",
        views.sell_media_image_delete,
        name="sell_media_image_delete",
    ),
    path(
        "vendre/<int:product_id>/medias/videos/",
        views.sell_media_video_add,
        name="sell_media_video_add",
    ),
    path(
        "vendre/<int:product_id>/medias/videos/<int:video_id>/supprimer/",
        views.sell_media_video_delete,
        name="sell_media_video_delete",
    ),
    path("vendre/confirmation/", views.sell_confirmation, name="sell_confirmation"),
    path("mes-annonces/", views.my_listings, name="my_listings"),
    path("mes-annonces/<int:product_id>/vendu/", views.listing_mark_sold, name="listing_mark_sold"),
    path("mes-annonces/<int:product_id>/archiver/", views.listing_archive, name="listing_archive"),
    path("mes-annonces/<int:product_id>/reactiver/", views.listing_reactivate, name="listing_reactivate"),
]
