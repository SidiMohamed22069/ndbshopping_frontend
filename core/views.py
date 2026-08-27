from django.shortcuts import render
from django.views.decorators.http import require_GET

from services import api_client


@require_GET
def home(request):
    products_result = api_client.get_products(page=0, size=8)
    publications_result = api_client.get_publications(page=0, size=6)

    products = []
    if products_result.ok and isinstance(products_result.data, dict):
        products = products_result.data.get("content") or []
    elif not products_result.ok and products_result.status != 0:
        from django.contrib import messages

        messages.error(request, products_result.error or api_client.UNAVAILABLE)

    publications = []
    if publications_result.ok and isinstance(publications_result.data, dict):
        publications = publications_result.data.get("content") or []

    return render(
        request,
        "core/home.html",
        {
            "products": products,
            "publications": publications,
        },
    )


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


@require_GET
def category_attributes_json(request, category_id):
    """
    Proxy JSON pour le formulaire admin produits (évite les soucis CORS en local).
    Le JS appelle cette URL Django, qui relaie GET /api/categories/{id}/attributes.
    """
    from django.http import JsonResponse

    result = api_client.get_category_attributes(category_id)
    if not result.ok:
        return JsonResponse({"error": result.error}, status=result.status or 503)
    return JsonResponse(result.data, safe=False)
