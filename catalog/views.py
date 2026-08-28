from django.contrib import messages
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from core.utils import normalize_category_image, normalize_product_images, page_from_request
from services import api_client


@require_GET
def product_list(request, category_id=None):
    page = page_from_request(request)
    category_id = category_id or request.GET.get("category") or request.GET.get("categorie") or ""
    q = (request.GET.get("q") or "").strip()
    min_prix = request.GET.get("min_prix") or ""
    max_prix = request.GET.get("max_prix") or ""

    result = api_client.get_products(
        category_id=category_id or None,
        q=q or None,
        min_prix=min_prix or None,
        max_prix=max_prix or None,
        page=page - 1,
        size=12,
    )

    products, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        products = [normalize_product_images(p) for p in (result.data.get("content") or []) if isinstance(p, dict)]
        pagination = result.data
    elif not result.ok and result.status != 0:
        messages.error(request, result.error or api_client.UNAVAILABLE)

    selected_category = None
    if category_id:
        cats = api_client.get_categories()
        if cats.ok:

            def find(nodes, cid):
                for n in nodes or []:
                    if str(n.get("id")) == str(cid):
                        return n
                    found = find(n.get("children") or [], cid)
                    if found:
                        return found
                return None

            selected_category = find(cats.data if isinstance(cats.data, list) else [], category_id)

    return render(
        request,
        "catalog/product_list.html",
        {
            "products": products,
            "pagination": pagination,
            "q": q,
            "category_id": str(category_id),
            "min_prix": min_prix,
            "max_prix": max_prix,
            "selected_category": selected_category,
            "page": page,
        },
    )


@require_GET
def product_detail(request, product_id):
    result = api_client.get_product(product_id)
    if not result.ok or not isinstance(result.data, dict):
        if result.status == 404:
            raise Http404("Produit introuvable")
        messages.error(request, result.error or api_client.UNAVAILABLE)
        return render(request, "catalog/product_detail.html", {"product": None})
    return render(
        request,
        "catalog/product_detail.html",
        {"product": normalize_product_images(result.data)},
    )


@require_GET
def categories(request):
    result = api_client.get_categories()
    tree = result.data if result.ok and isinstance(result.data, list) else []
    tree = [normalize_category_image(cat) for cat in tree if isinstance(cat, dict)]
    if not result.ok and result.status != 0:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(request, "catalog/categories.html", {"categories": tree})


@require_GET
def publication_list(request):
    page = page_from_request(request)
    result = api_client.get_publications(page=page - 1, size=10)
    publications, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        publications = result.data.get("content") or []
        pagination = result.data
    elif not result.ok and result.status != 0:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "catalog/publication_list.html",
        {"publications": publications, "pagination": pagination, "page": page},
    )


@require_GET
def publication_detail(request, publication_id):
    """Pas d'endpoint GET /publications/{id} : on cherche dans les pages publiées."""
    page = 0
    found = None
    while page < 10:
        result = api_client.get_publications(page=page, size=50)
        if not result.ok or not isinstance(result.data, dict):
            messages.error(request, result.error or api_client.UNAVAILABLE)
            break
        for pub in result.data.get("content") or []:
            if str(pub.get("id")) == str(publication_id):
                found = pub
                break
        if found:
            break
        total_pages = result.data.get("totalPages") or 1
        page += 1
        if page >= total_pages:
            break
    if not found:
        raise Http404("Publication introuvable")

    linked_product = None
    if found.get("produitLieId"):
        prod = api_client.get_product(found["produitLieId"])
        if prod.ok and isinstance(prod.data, dict):
            linked_product = normalize_product_images(prod.data)

    return render(
        request,
        "catalog/publication_detail.html",
        {"publication": found, "linked_product": linked_product},
    )
