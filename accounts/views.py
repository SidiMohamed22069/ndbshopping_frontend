from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from cart.utils import clear_cart, sync_if_authenticated, to_sync_payload
from core.decorators import login_required_api
from core.media_upload import json_error, json_ok, media_initial_json, upload_and_respond, validate_image, validate_video
from core.utils import normalize_product_images, page_from_request, safe_next_url
from services import api_client

VILLE_LIVRAISON = "NOUADHIBOU"


def _establish_session(request, token: str, user: dict, next_url: str | None):
    """Enregistre le JWT Spring Boot en session et synchronise le panier."""
    request.session["jwt_token"] = token
    request.session["user_role"] = user.get("role")
    request.session["user_nom"] = user.get("nom")
    request.session["user_id"] = user.get("id")
    request.session.pop("pending_phone", None)
    request.session.pop("pending_next", None)

    sync = api_client.sync_cart(token, to_sync_payload(request.session))
    if not sync.ok:
        messages.warning(
            request,
            _("Connecté, mais le panier n'a pas pu être synchronisé. ") + (sync.error or ""),
        )
    messages.success(request, _("Bienvenue %(nom)s !") % {"nom": user.get("nom") or ""})
    return redirect(safe_next_url(next_url or reverse("core:home")))


def _go_to_otp(request, telephone: str, next_url: str, message: str | None = None):
    request.session["pending_phone"] = telephone
    request.session["pending_next"] = next_url
    messages.success(request, message or _("Code envoyé par SMS."))
    return redirect("accounts:otp")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("jwt_token"):
        return redirect("core:home")

    next_url = safe_next_url(request.GET.get("next") or request.POST.get("next"))
    unknown_account = False

    if request.method == "POST":
        telephone = (request.POST.get("telephone") or "").strip()
        password = request.POST.get("password") or ""
        if not telephone or not password:
            messages.error(request, _("Téléphone et mot de passe sont obligatoires."))
        else:
            result = api_client.register_or_login(telephone, password)
            data = result.data if isinstance(result.data, dict) else {}
            if result.ok and data.get("token"):
                return _establish_session(request, data["token"], data.get("user") or {}, next_url)
            if result.ok and (result.status == 202 or data.get("needsVerification")):
                return _go_to_otp(request, telephone, next_url, data.get("message"))
            if result.status == 404:
                unknown_account = True
            else:
                messages.error(request, result.error or _("Connexion impossible."))

    return render(
        request,
        "accounts/login.html",
        {"next": next_url, "unknown_account": unknown_account},
    )


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.session.get("jwt_token"):
        return redirect("core:home")

    next_url = safe_next_url(request.GET.get("next") or request.POST.get("next"))
    account_exists = False

    if request.method == "POST":
        nom = (request.POST.get("nom") or "").strip()
        telephone = (request.POST.get("telephone") or "").strip()
        password = request.POST.get("password") or ""
        if not nom or not telephone or not password:
            messages.error(request, _("Nom, téléphone et mot de passe sont obligatoires."))
        else:
            result = api_client.register(nom, telephone, password)
            if result.ok:
                data = result.data if isinstance(result.data, dict) else {}
                return _go_to_otp(request, telephone, next_url, data.get("message"))
            if result.status == 409:
                account_exists = True
            else:
                messages.error(request, result.error or _("Inscription impossible."))

    return render(
        request,
        "accounts/register.html",
        {"next": next_url, "account_exists": account_exists},
    )


@require_http_methods(["GET", "POST"])
def otp_view(request):
    telephone = request.session.get("pending_phone")
    if not telephone:
        messages.warning(request, _("Commencez par renseigner vos informations."))
        return redirect("accounts:login")

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        if not code:
            messages.error(request, _("Saisissez le code reçu par SMS."))
        else:
            result = api_client.verify_otp(telephone, code)
            if result.ok and isinstance(result.data, dict) and result.data.get("token"):
                next_url = request.session.get("pending_next")
                return _establish_session(
                    request,
                    result.data["token"],
                    result.data.get("user") or {},
                    next_url,
                )
            messages.error(request, result.error or _("Code incorrect."))

    return render(request, "accounts/otp.html", {"telephone": telephone})


@require_http_methods(["POST", "GET"])
def logout_view(request):
    request.session.flush()
    messages.success(request, _("Vous êtes déconnecté."))
    return redirect("core:home")


@login_required_api
@require_http_methods(["GET", "POST"])
def checkout(request):
    from cart.utils import get_cart

    if not get_cart(request.session):
        messages.warning(request, _("Votre panier est vide."))
        return redirect("cart:detail")

    if request.method == "POST":
        adresse = (request.POST.get("adresseDetails") or "").strip()
        if not adresse:
            messages.error(request, _("Indiquez une adresse."))
        else:
            sync_if_authenticated(request)
            result = api_client.create_order(request.jwt_token, VILLE_LIVRAISON, adresse)
            if result.ok:
                clear_cart(request.session)
                messages.success(request, _("Commande enregistrée. Merci !"))
                return redirect("accounts:orders")
            messages.error(request, result.error or _("Impossible de passer la commande."))

    return render(request, "accounts/checkout.html")


@login_required_api
@require_http_methods(["GET"])
def orders(request):
    page = page_from_request(request)
    result = api_client.get_my_orders(request.jwt_token, page=page - 1, size=10)
    orders_list, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        orders_list = result.data.get("content") or []
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "accounts/orders.html",
        {"orders": orders_list, "pagination": pagination, "page": page},
    )


def _client_product_payload(request) -> dict:
    attributs = []
    for key in request.POST:
        if key.startswith("attr_"):
            raw_id = key[5:]
            try:
                attributs.append(
                    {
                        "attributeDefinitionId": int(raw_id),
                        "valeur": request.POST.get(key) or "",
                    }
                )
            except ValueError:
                continue
    category_id = request.POST.get("categoryId")
    stock = request.POST.get("stock") or 0
    prix_raw = (request.POST.get("prix") or "").strip()
    try:
        prix = str(Decimal(prix_raw)) if prix_raw else "0"
    except InvalidOperation:
        prix = prix_raw or "0"
    return {
        "nom": (request.POST.get("nom") or "").strip(),
        "description": (request.POST.get("description") or "").strip() or None,
        "prix": prix,
        "stock": int(stock) if str(stock).isdigit() else 0,
        "categoryId": int(category_id) if category_id else None,
        "attributs": attributs,
    }


@login_required_api
@require_http_methods(["GET", "POST"])
def sell(request):
    form = {
        "nom": request.POST.get("nom") or "",
        "description": request.POST.get("description") or "",
        "prix": request.POST.get("prix") or "",
        "stock": request.POST.get("stock") or "0",
        "categoryId": request.POST.get("categoryId") or "",
    }
    if request.method == "POST":
        payload = _client_product_payload(request)
        if not payload["nom"] or payload["categoryId"] is None:
            messages.error(request, _("Le nom et la catégorie sont obligatoires."))
        else:
            result = api_client.submit_product(request.jwt_token, payload)
            if result.ok and isinstance(result.data, dict) and result.data.get("id"):
                return redirect("accounts:sell_media", product_id=result.data["id"])
            messages.error(request, result.error or _("Soumission impossible."))
    return render(
        request,
        "accounts/sell.html",
        {"form": form, "product_attrs_json": "[]"},
    )


def _load_own_product(request, product_id):
    result = api_client.get_product(product_id, token=request.jwt_token)
    if not result.ok or not isinstance(result.data, dict):
        return None, result
    product = normalize_product_images(result.data)
    owner_id = product.get("soumisParUserId")
    session_uid = request.session.get("user_id")
    if owner_id is not None and session_uid is not None and str(owner_id) != str(session_uid):
        if request.session.get("user_role") != "ADMIN":
            return None, result
    return product, result


@login_required_api
@require_http_methods(["GET", "POST"])
def sell_media(request, product_id):
    product, result = _load_own_product(request, product_id)
    if product is None:
        messages.error(request, (result.error if result else None) or _("Produit introuvable."))
        return redirect("accounts:my_listings")
    if request.method == "POST":
        request.session["product_submitted"] = True
        return redirect("accounts:sell_confirmation")
    request.session["product_submitted"] = True
    return render(
        request,
        "accounts/sell_media.html",
        {
            "product": product,
            "media_url_ns": "accounts",
            "media_initial_json": media_initial_json(product),
        },
    )


@login_required_api
@require_POST
def sell_media_image_add(request, product_id):
    product, result = _load_own_product(request, product_id)
    if product is None:
        return json_error((result.error if result else None) or _("Produit introuvable."), result.status if result else 404)
    return upload_and_respond(request, product_id, "file", validate_image, api_client.upload_product_image)


@login_required_api
@require_POST
def sell_media_image_delete(request, product_id, image_id):
    product, result = _load_own_product(request, product_id)
    if product is None:
        return json_error((result.error if result else None) or _("Produit introuvable."), result.status if result else 404)
    deleted = api_client.delete_product_image(request.jwt_token, product_id, image_id)
    if deleted.ok:
        return json_ok()
    return json_error(deleted.error or _("Suppression impossible."), deleted.status or 400)


@login_required_api
@require_POST
def sell_media_video_add(request, product_id):
    product, result = _load_own_product(request, product_id)
    if product is None:
        return json_error((result.error if result else None) or _("Produit introuvable."), result.status if result else 404)
    return upload_and_respond(request, product_id, "video", validate_video, api_client.upload_product_video)


@login_required_api
@require_POST
def sell_media_video_delete(request, product_id, video_id):
    product, result = _load_own_product(request, product_id)
    if product is None:
        return json_error((result.error if result else None) or _("Produit introuvable."), result.status if result else 404)
    deleted = api_client.delete_product_video(request.jwt_token, product_id, video_id)
    if deleted.ok:
        return json_ok()
    return json_error(deleted.error or _("Suppression impossible."), deleted.status or 400)


@login_required_api
@require_http_methods(["GET"])
def sell_confirmation(request):
    if not request.session.pop("product_submitted", None):
        return redirect("accounts:my_listings")
    return render(request, "accounts/sell_confirmation.html")


@login_required_api
@require_http_methods(["GET"])
def my_listings(request):
    page = page_from_request(request)
    result = api_client.get_my_products(request.jwt_token, page=page - 1, size=12)
    products, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        products = [
            normalize_product_images(p) for p in (result.data.get("content") or []) if isinstance(p, dict)
        ]
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "accounts/my_listings.html",
        {"products": products, "pagination": pagination, "page": page},
    )


@login_required_api
@require_POST
def listing_mark_sold(request, product_id):
    result = api_client.mark_product_sold(request.jwt_token, product_id)
    if result.ok:
        messages.success(request, _("Annonce marquée comme vendue."))
    else:
        messages.error(request, result.error or _("Action impossible."))
    return redirect("accounts:my_listings")


@login_required_api
@require_POST
def listing_archive(request, product_id):
    result = api_client.archive_product(request.jwt_token, product_id)
    if result.ok:
        messages.success(request, _("Annonce archivée."))
    else:
        messages.error(request, result.error or _("Action impossible."))
    return redirect("accounts:my_listings")


@login_required_api
@require_POST
def listing_reactivate(request, product_id):
    result = api_client.reactivate_product(request.jwt_token, product_id)
    if result.ok:
        messages.success(request, _("Annonce remise en ligne."))
    else:
        messages.error(request, result.error or _("Action impossible."))
    return redirect("accounts:my_listings")
