"""
Client HTTP centralisé vers l'API Spring Boot (/api/).

Toutes les vues Django passent par ce module : aucun appel `requests`
ailleurs dans le projet. Les exceptions réseau sont capturées et
transformées en ApiResult.ok=False pour que les templates affichent
« service temporairement indisponible » au lieu d'une page 500.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _lazy

logger = logging.getLogger(__name__)

# Timeout réseau : ne jamais laisser une vue bloquer indéfiniment.
DEFAULT_TIMEOUT = getattr(settings, "API_TIMEOUT", 15)

UNAVAILABLE = _lazy("Service temporairement indisponible. Veuillez réessayer dans un instant.")


@dataclass
class ApiResult:
    ok: bool
    status: int
    data: Any
    error: str | None = None

    @property
    def json(self) -> Any:
        return self.data


def _headers(token: str | None = None, json_body: bool = True) -> dict[str, str]:
    headers: dict[str, str] = {}
    if json_body:
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
    else:
        headers["Accept"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _url(path: str) -> str:
    base = settings.API_BASE_URL.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _parse_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return payload.get("error") or payload.get("message") or response.reason
    except ValueError:
        pass
    return response.text or response.reason or f"Erreur HTTP {response.status_code}"


def _result(response: requests.Response) -> ApiResult:
    if response.status_code == 204:
        return ApiResult(ok=True, status=204, data=None)
    try:
        data = response.json() if response.content else None
    except ValueError:
        data = None
    if 200 <= response.status_code < 300:
        return ApiResult(ok=True, status=response.status_code, data=data)
    error = _parse_error(response)
    return ApiResult(ok=False, status=response.status_code, data=data, error=error)


def call(
    method: str,
    path: str,
    token: str | None = None,
    json: Any = None,
    params: dict | None = None,
    files: dict | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> ApiResult:
    """Point d'entrée unique. `files` désactive Content-Type JSON (multipart)."""
    json_body = files is None
    url = _url(path)
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=_headers(token, json_body=json_body),
            json=json if json_body else None,
            params=params,
            files=files,
            timeout=timeout,
        )
        result = _result(response)
        if not result.ok:
            logger.error(
                "API %s %s → HTTP %s: %s",
                method.upper(),
                url,
                result.status,
                result.error,
            )
        return result
    except requests.exceptions.RequestException:
        logger.exception("Échec appel API %s %s", method.upper(), url)
        return ApiResult(ok=False, status=0, data=None, error=UNAVAILABLE)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def register_or_login(telephone: str, password: str, lang: str = "fr") -> ApiResult:
    """Connexion : JWT si le compte est vérifié, sinon 202 needsVerification."""
    return call(
        "POST",
        "/auth/register-or-login",
        json={"telephone": telephone, "password": password, "lang": lang},
    )


def register(nom: str, telephone: str, password: str, lang: str = "fr") -> ApiResult:
    """Inscription CLIENT : envoie un OTP (pas de JWT tant que le téléphone n'est pas vérifié)."""
    return call(
        "POST",
        "/auth/register",
        json={"nom": nom, "telephone": telephone, "password": password, "lang": lang},
    )


def verify_otp(telephone: str, code: str) -> ApiResult:
    return call("POST", "/auth/verify-otp", json={"telephone": telephone, "code": code})


def me(token: str) -> ApiResult:
    return call("GET", "/auth/me", token=token)


# ---------------------------------------------------------------------------
# Catalogue public
# ---------------------------------------------------------------------------

def get_categories() -> ApiResult:
    return call("GET", "/categories")


def get_category_attributes(category_id: int | str) -> ApiResult:
    return call("GET", f"/categories/{category_id}/attributes")


def get_products(
    category_id: int | str | None = None,
    q: str | None = None,
    min_prix=None,
    max_prix=None,
    page: int = 0,
    size: int = 20,
) -> ApiResult:
    params: dict[str, Any] = {"page": page, "size": size}
    if category_id not in (None, ""):
        params["categoryId"] = category_id
    if q:
        params["q"] = q
    if min_prix not in (None, ""):
        params["minPrix"] = min_prix
    if max_prix not in (None, ""):
        params["maxPrix"] = max_prix
    return call("GET", "/products", params=params)


def get_product(product_id: int | str, token: str | None = None) -> ApiResult:
    return call("GET", f"/products/{product_id}", token=token)


def get_my_products(token: str, page: int = 0, size: int = 20) -> ApiResult:
    return call("GET", "/products/me", token=token, params={"page": page, "size": size})


def submit_product(token: str, payload: dict) -> ApiResult:
    return call("POST", "/products", token=token, json=payload)


def upload_product_image(token: str, product_id: int | str, django_file) -> ApiResult:
    django_file.seek(0)
    files = {
        "file": (django_file.name, django_file.read(), django_file.content_type or "application/octet-stream"),
    }
    return call("POST", f"/products/{product_id}/images", token=token, files=files)


def delete_product_image(token: str, product_id: int | str, image_id: int | str) -> ApiResult:
    return call("DELETE", f"/products/{product_id}/images/{image_id}", token=token)


def upload_product_video(token: str, product_id: int | str, django_file) -> ApiResult:
    django_file.seek(0)
    files = {
        "video": (django_file.name, django_file.read(), django_file.content_type or "application/octet-stream"),
    }
    return call("POST", f"/products/{product_id}/videos", token=token, files=files, timeout=90)


def delete_product_video(token: str, product_id: int | str, video_id: int | str) -> ApiResult:
    return call("DELETE", f"/products/{product_id}/videos/{video_id}", token=token)


def mark_product_sold(token: str, product_id: int | str) -> ApiResult:
    return call("PATCH", f"/products/{product_id}/vendu", token=token)


def archive_product(token: str, product_id: int | str) -> ApiResult:
    return call("PATCH", f"/products/{product_id}/archiver", token=token)


def reactivate_product(token: str, product_id: int | str) -> ApiResult:
    return call("PATCH", f"/products/{product_id}/reactiver", token=token)


def get_publications(page: int = 0, size: int = 20) -> ApiResult:
    return call("GET", "/publications", params={"page": page, "size": size})


def get_featured_publications() -> ApiResult:
    """Bandeau public : publications mises en avant (liste, pas une page)."""
    return call("GET", "/publications/mises-en-avant")


# ---------------------------------------------------------------------------
# Panier (JWT requis) — POST /cart/sync remplace le panier serveur entier
# ---------------------------------------------------------------------------

def get_cart(token: str) -> ApiResult:
    return call("GET", "/cart", token=token)


def sync_cart(token: str, items: list[dict]) -> ApiResult:
    """
    items : [{"productId": int, "quantite": int}, ...]
    Correspond à CartSyncRequest du backend. Appelé après OTP et à chaque
    modification du panier dès que l'utilisateur est connecté, car POST /orders
    utilise le panier persisté côté Spring Boot.
    """
    return call("POST", "/cart/sync", token=token, json={"items": items})


# ---------------------------------------------------------------------------
# Commandes client
# ---------------------------------------------------------------------------

def create_order(token: str, ville_livraison: str, adresse_details: str) -> ApiResult:
    return call(
        "POST",
        "/orders",
        token=token,
        json={"villeLivraison": ville_livraison, "adresseDetails": adresse_details},
    )


def get_my_orders(token: str, page: int = 0, size: int = 20) -> ApiResult:
    return call("GET", "/orders/me", token=token, params={"page": page, "size": size})


# ---------------------------------------------------------------------------
# Admin — catégories
# ---------------------------------------------------------------------------

def admin_create_category(token: str, payload: dict) -> ApiResult:
    return call("POST", "/admin/categories", token=token, json=payload)


def admin_update_category(token: str, category_id: int | str, payload: dict) -> ApiResult:
    return call("PUT", f"/admin/categories/{category_id}", token=token, json=payload)


def admin_delete_category(token: str, category_id: int | str) -> ApiResult:
    return call("DELETE", f"/admin/categories/{category_id}", token=token)


def admin_reorder_categories(token: str, ordre_ids: list) -> ApiResult:
    return call("PATCH", "/admin/categories/reorder", token=token, json={"ordreIds": ordre_ids})


def admin_upload_category_image(token: str, category_id: int | str, django_file) -> ApiResult:
    django_file.seek(0)
    files = {
        "image": (django_file.name, django_file.read(), django_file.content_type or "application/octet-stream"),
    }
    return call("POST", f"/admin/categories/{category_id}/image", token=token, files=files)


def admin_add_attribute(token: str, category_id: int | str, payload: dict) -> ApiResult:
    return call("POST", f"/admin/categories/{category_id}/attributes", token=token, json=payload)


def admin_delete_attribute(token: str, category_id: int | str, attribute_id: int | str) -> ApiResult:
    return call(
        "DELETE",
        f"/admin/categories/{category_id}/attributes/{attribute_id}",
        token=token,
    )


# ---------------------------------------------------------------------------
# Admin — produits
# ---------------------------------------------------------------------------

def admin_get_products(
    token: str,
    statut: str | None = None,
    category_id: int | str | None = None,
    q: str | None = None,
    page: int = 0,
    size: int = 20,
) -> ApiResult:
    params: dict[str, Any] = {"page": page, "size": size}
    if statut:
        params["statut"] = statut
    if category_id not in (None, ""):
        params["categoryId"] = category_id
    if q:
        params["q"] = q
    return call("GET", "/admin/products", token=token, params=params)


def admin_get_product(token: str, product_id: int | str) -> ApiResult:
    return call("GET", f"/admin/products/{product_id}", token=token)


def admin_create_product(token: str, payload: dict) -> ApiResult:
    return call("POST", "/admin/products", token=token, json=payload)


def admin_update_product(token: str, product_id: int | str, payload: dict) -> ApiResult:
    return call("PUT", f"/admin/products/{product_id}", token=token, json=payload)


def admin_delete_product(token: str, product_id: int | str) -> ApiResult:
    return call("DELETE", f"/admin/products/{product_id}", token=token)


def admin_upload_product_image(token: str, product_id: int | str, django_file) -> ApiResult:
    django_file.seek(0)
    files = {
        "file": (django_file.name, django_file.read(), django_file.content_type or "application/octet-stream"),
    }
    return call("POST", f"/admin/products/{product_id}/images", token=token, files=files)


def admin_delete_product_image(token: str, product_id: int | str, image_id: int | str) -> ApiResult:
    return call("DELETE", f"/admin/products/{product_id}/images/{image_id}", token=token)


def admin_validate_product(token: str, product_id: int | str) -> ApiResult:
    return call("PATCH", f"/admin/products/{product_id}/valider", token=token)


def admin_reject_product(token: str, product_id: int | str, raison: str) -> ApiResult:
    return call(
        "PATCH",
        f"/admin/products/{product_id}/rejeter",
        token=token,
        json={"raison": raison},
    )


def admin_import_url(token: str, url: str, category_id: int | str | None = None) -> ApiResult:
    payload: dict[str, Any] = {"url": url}
    if category_id not in (None, ""):
        payload["categoryId"] = int(category_id)
    return call("POST", "/admin/products/import/url", token=token, json=payload)


def admin_import_csv(token: str, django_file) -> ApiResult:
    files = {
        "file": (django_file.name, django_file.read(), django_file.content_type or "text/csv"),
    }
    return call("POST", "/admin/products/import/csv", token=token, files=files)


# ---------------------------------------------------------------------------
# Admin — commandes
# ---------------------------------------------------------------------------

def admin_get_orders(
    token: str,
    statut: str | None = None,
    ville: str | None = None,
    page: int = 0,
    size: int = 20,
) -> ApiResult:
    params: dict[str, Any] = {"page": page, "size": size}
    if statut:
        params["statut"] = statut
    if ville:
        params["ville"] = ville
    return call("GET", "/admin/orders", token=token, params=params)


def admin_update_order_status(token: str, order_id: int | str, statut: str) -> ApiResult:
    return call("PATCH", f"/admin/orders/{order_id}/statut", token=token, json={"statut": statut})


# ---------------------------------------------------------------------------
# Admin — notifications
# ---------------------------------------------------------------------------

def admin_get_notifications(
    token: str,
    lu: bool | None = None,
    page: int = 0,
    size: int = 20,
) -> ApiResult:
    params: dict[str, Any] = {"page": page, "size": size}
    if lu is not None:
        params["lu"] = str(lu).lower()
    return call("GET", "/admin/notifications", token=token, params=params)


def admin_mark_notification_read(token: str, notification_id: int | str) -> ApiResult:
    return call("PATCH", f"/admin/notifications/{notification_id}/lire", token=token)


def admin_unread_count(token: str) -> ApiResult:
    return call("GET", "/admin/notifications/count-non-lues", token=token)


# ---------------------------------------------------------------------------
# Admin — publications
# ---------------------------------------------------------------------------

def admin_get_publications(token: str, page: int = 0, size: int = 20) -> ApiResult:
    return call("GET", "/admin/publications", token=token, params={"page": page, "size": size})


def admin_create_publication(token: str, payload: dict) -> ApiResult:
    return call("POST", "/admin/publications", token=token, json=payload)


def admin_update_publication(token: str, publication_id: int | str, payload: dict) -> ApiResult:
    return call("PUT", f"/admin/publications/{publication_id}", token=token, json=payload)


def admin_delete_publication(token: str, publication_id: int | str) -> ApiResult:
    return call("DELETE", f"/admin/publications/{publication_id}", token=token)


def admin_upload_publication_image(token: str, publication_id: int | str, django_file) -> ApiResult:
    django_file.seek(0)
    files = {
        "image": (django_file.name, django_file.read(), django_file.content_type or "application/octet-stream"),
    }
    return call("POST", f"/admin/publications/{publication_id}/image", token=token, files=files)


# ---------------------------------------------------------------------------
# Admin — comptes utilisateurs
# ---------------------------------------------------------------------------

def admin_get_users(token: str, role: str | None = None, page: int = 0, size: int = 20) -> ApiResult:
    params: dict[str, Any] = {"page": page, "size": size}
    if role:
        params["role"] = role
    return call("GET", "/admin/users", token=token, params=params)


def admin_create_user(token: str, payload: dict) -> ApiResult:
    return call("POST", "/admin/users", token=token, json=payload)


def admin_update_user_role(token: str, user_id: int | str, role: str) -> ApiResult:
    return call("PATCH", f"/admin/users/{user_id}/role", token=token, json={"role": role})


def admin_update_user_status(token: str, user_id: int | str, actif: bool) -> ApiResult:
    return call("PATCH", f"/admin/users/{user_id}/status", token=token, json={"actif": actif})


def admin_delete_user(token: str, user_id: int | str) -> ApiResult:
    return call("DELETE", f"/admin/users/{user_id}", token=token)
