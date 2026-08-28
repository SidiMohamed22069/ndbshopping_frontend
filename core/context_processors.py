from django.conf import settings

from cart.utils import cart_quantity
from core.utils import flatten_categories, normalize_category_image
from services import api_client


def storefront(request):
    """Contexte partagé : nav, panier, URLs médias, auth session."""
    categories_result = api_client.get_categories()
    categories = categories_result.data if categories_result.ok and isinstance(categories_result.data, list) else []
    categories = [normalize_category_image(cat) for cat in categories if isinstance(cat, dict)]

    featured = []
    if not request.path.startswith("/admin-ndb/"):
        featured_result = api_client.get_featured_publications()
        if featured_result.ok and isinstance(featured_result.data, list):
            featured = featured_result.data

    return {
        "nav_categories": categories,
        "nav_categories_flat": flatten_categories(categories),
        "featured_publications": featured,
        "cart_count": cart_quantity(request.session),
        "is_authenticated_api": bool(request.session.get("jwt_token")),
        "is_admin_api": request.session.get("user_role") == "ADMIN",
        "user_nom": request.session.get("user_nom") or "",
        "MEDIA_BACKEND_URL": settings.MEDIA_BACKEND_URL.rstrip("/"),
        "PUBLIC_BACKEND_HOST": settings.PUBLIC_BACKEND_HOST,
        "api_unavailable": not categories_result.ok,
    }


def admin_badges(request):
    """Badge notifications non lues — uniquement sur l'espace /admin-ndb/."""
    if not request.path.startswith("/admin-ndb/"):
        return {"unread_notifications": 0}
    token = request.session.get("jwt_token")
    if not token or request.session.get("user_role") != "ADMIN":
        return {"unread_notifications": 0}
    result = api_client.admin_unread_count(token)
    count = 0
    if result.ok and isinstance(result.data, dict):
        count = result.data.get("count") or 0
    return {"unread_notifications": count}
