from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from cart.utils import clear_cart, sync_if_authenticated, to_sync_payload
from core.decorators import login_required_api
from core.utils import page_from_request, safe_next_url
from services import api_client

CITIES = [
    ("NOUADHIBOU", "Nouadhibou"),
    ("ZOUERAT", "Zouérat"),
    ("NOUAKCHOTT", "Nouakchott"),
]


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
            "Connecté, mais le panier n'a pas pu être synchronisé. " + (sync.error or ""),
        )
    messages.success(request, f"Bienvenue {user.get('nom') or ''} !")
    return redirect(safe_next_url(next_url or reverse("core:home")))


def _go_to_otp(request, telephone: str, next_url: str, message: str | None = None):
    request.session["pending_phone"] = telephone
    request.session["pending_next"] = next_url
    messages.success(request, message or "Code envoyé par SMS.")
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
            messages.error(request, "Téléphone et mot de passe sont obligatoires.")
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
                messages.error(request, result.error or "Connexion impossible.")

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
            messages.error(request, "Nom, téléphone et mot de passe sont obligatoires.")
        else:
            result = api_client.register(nom, telephone, password)
            if result.ok:
                data = result.data if isinstance(result.data, dict) else {}
                return _go_to_otp(request, telephone, next_url, data.get("message"))
            if result.status == 409:
                account_exists = True
            else:
                messages.error(request, result.error or "Inscription impossible.")

    return render(
        request,
        "accounts/register.html",
        {"next": next_url, "account_exists": account_exists},
    )


@require_http_methods(["GET", "POST"])
def otp_view(request):
    telephone = request.session.get("pending_phone")
    if not telephone:
        messages.warning(request, "Commencez par renseigner vos informations.")
        return redirect("accounts:login")

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        if not code:
            messages.error(request, "Saisissez le code reçu par SMS.")
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
            messages.error(request, result.error or "Code incorrect.")

    return render(request, "accounts/otp.html", {"telephone": telephone})


@require_http_methods(["POST", "GET"])
def logout_view(request):
    request.session.flush()
    messages.success(request, "Vous êtes déconnecté.")
    return redirect("core:home")


@login_required_api
@require_http_methods(["GET", "POST"])
def checkout(request):
    from cart.utils import get_cart

    if not get_cart(request.session):
        messages.warning(request, "Votre panier est vide.")
        return redirect("cart:detail")

    if request.method == "POST":
        ville = request.POST.get("villeLivraison") or ""
        adresse = (request.POST.get("adresseDetails") or "").strip()
        if ville not in {c[0] for c in CITIES} or not adresse:
            messages.error(request, "Choisissez une ville et indiquez une adresse.")
        else:
            sync_if_authenticated(request)
            result = api_client.create_order(request.jwt_token, ville, adresse)
            if result.ok:
                clear_cart(request.session)
                messages.success(request, "Commande enregistrée. Merci !")
                return redirect("accounts:orders")
            messages.error(request, result.error or "Impossible de passer la commande.")

    return render(request, "accounts/checkout.html", {"cities": CITIES})


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
