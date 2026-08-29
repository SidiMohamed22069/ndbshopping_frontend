from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Catégories
    path("categories/", views.category_list, name="category_list"),
    path("categories/nouvelle/", views.category_create, name="category_create"),
    path("categories/reorder/", views.category_reorder, name="category_reorder"),
    path("categories/<int:category_id>/modifier/", views.category_edit, name="category_edit"),
    path("categories/<int:category_id>/supprimer/", views.category_delete, name="category_delete"),
    path("categories/<int:category_id>/attributs/", views.category_attributes, name="category_attributes"),
    path(
        "categories/<int:category_id>/attributs/<int:attribute_id>/supprimer/",
        views.category_attribute_delete,
        name="category_attribute_delete",
    ),
    # Produits
    path("produits/", views.product_list, name="product_list"),
    path("produits/nouveau/", views.product_create, name="product_create"),
    path("produits/import/", views.product_import, name="product_import"),
    path("produits/a-valider/", views.product_pending, name="product_pending"),
    path("produits/<int:product_id>/valider/", views.product_validate, name="product_validate"),
    path("produits/<int:product_id>/rejeter/", views.product_reject, name="product_reject"),
    path("produits/<int:product_id>/vendu/", views.product_mark_sold, name="product_mark_sold"),
    path("produits/<int:product_id>/archiver/", views.product_archive, name="product_archive"),
    path("produits/<int:product_id>/reactiver/", views.product_reactivate, name="product_reactivate"),
    path("produits/<int:product_id>/modifier/", views.product_edit, name="product_edit"),
    path("produits/<int:product_id>/supprimer/", views.product_delete, name="product_delete"),
    path("produits/<int:product_id>/images/", views.product_images, name="product_images"),
    path(
        "produits/<int:product_id>/images/<int:image_id>/supprimer/",
        views.product_image_delete,
        name="product_image_delete",
    ),
    path(
        "produits/<int:product_id>/medias/images/",
        views.product_media_image_add,
        name="product_media_image_add",
    ),
    path(
        "produits/<int:product_id>/medias/images/<int:image_id>/supprimer/",
        views.product_media_image_delete,
        name="product_media_image_delete",
    ),
    path(
        "produits/<int:product_id>/medias/videos/",
        views.product_media_video_add,
        name="product_media_video_add",
    ),
    path(
        "produits/<int:product_id>/medias/videos/<int:video_id>/supprimer/",
        views.product_media_video_delete,
        name="product_media_video_delete",
    ),
    # Commandes
    path("commandes/", views.order_list, name="order_list"),
    path("commandes/<int:order_id>/", views.order_detail, name="order_detail"),
    # Publications
    path("publications/", views.publication_list, name="publication_list"),
    path("publications/nouvelle/", views.publication_create, name="publication_create"),
    path("publications/<int:publication_id>/modifier/", views.publication_edit, name="publication_edit"),
    path("publications/<int:publication_id>/supprimer/", views.publication_delete, name="publication_delete"),
    # Notifications
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:notification_id>/lire/", views.notification_read, name="notification_read"),
    # Comptes
    path("utilisateurs/", views.user_list, name="user_list"),
    path("utilisateurs/creer/", views.user_create, name="user_create"),
    path("utilisateurs/<int:user_id>/role/", views.user_toggle_role, name="user_toggle_role"),
    path("utilisateurs/<int:user_id>/statut/", views.user_toggle_status, name="user_toggle_status"),
    path("utilisateurs/<int:user_id>/supprimer/", views.user_delete, name="user_delete"),
]
