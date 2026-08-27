from django.conf import settings
from django.urls import include, path

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("core.urls")),
    path("", include("catalog.urls")),
    path("panier/", include("cart.urls")),
    path("compte/", include("accounts.urls")),
    path("admin-ndb/", include("adminpanel.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
