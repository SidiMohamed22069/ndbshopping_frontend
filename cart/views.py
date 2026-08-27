from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from services import api_client

from . import utils as cart_utils


def _wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in (
        request.headers.get("Accept") or ""
    )


def _parse_product_qty(request):
    source = request.POST
    product_id = source.get("product_id")
    quantite = source.get("quantite", 1)
    try:
        return int(product_id), int(quantite)
    except (TypeError, ValueError):
        return None, None


@require_http_methods(["GET"])
def detail(request):
    """Affiche le panier. Les prix viennent toujours de GET /products/{id}."""
    raw = cart_utils.get_cart(request.session)
    lines = []
    total = Decimal("0")
    unavailable = False

    for item in raw:
        result = api_client.get_product(item["product_id"])
        if not result.ok or not isinstance(result.data, dict):
            unavailable = unavailable or (result.status == 0)
            continue
        product = result.data
        try:
            prix = Decimal(str(product.get("prix") or 0))
        except Exception:
            prix = Decimal("0")
        qty = item["quantite"]
        sous_total = prix * qty
        total += sous_total
        lines.append(
            {
                "product": product,
                "product_id": item["product_id"],
                "quantite": qty,
                "prix": prix,
                "sous_total": sous_total,
            }
        )

    if unavailable:
        messages.error(request, api_client.UNAVAILABLE)

    return render(
        request,
        "cart/cart.html",
        {"lines": lines, "total": total},
    )


@require_POST
def add(request):
    product_id, quantite = _parse_product_qty(request)
    if not product_id:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": _("Produit invalide.")}, status=400)
        messages.error(request, _("Produit invalide."))
        return redirect("catalog:product_list")

    result = api_client.get_product(product_id)
    if not result.ok:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": result.error}, status=result.status or 400)
        messages.error(request, result.error or _("Produit introuvable."))
        return redirect("catalog:product_list")

    cart_utils.add_item(request.session, product_id, quantite or 1)
    cart_utils.sync_if_authenticated(request)

    if _wants_json(request):
        return JsonResponse(
            {
                "ok": True,
                "cart_count": cart_utils.cart_quantity(request.session),
                "message": _("Ajouté au panier."),
            }
        )
    messages.success(request, _("Produit ajouté au panier."))
    next_url = request.POST.get("next") or reverse("cart:detail")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("cart:detail")


@require_POST
def update(request):
    product_id, quantite = _parse_product_qty(request)
    if not product_id:
        messages.error(request, _("Produit invalide."))
        return redirect("cart:detail")
    cart_utils.update_item(request.session, product_id, quantite if quantite is not None else 1)
    cart_utils.sync_if_authenticated(request)
    messages.success(request, _("Panier mis à jour."))
    return redirect("cart:detail")


@require_POST
def remove(request):
    product_id, _ = _parse_product_qty(request)
    if product_id:
        cart_utils.remove_item(request.session, product_id)
        cart_utils.sync_if_authenticated(request)
        messages.success(request, _("Article retiré du panier."))
    return redirect("cart:detail")
