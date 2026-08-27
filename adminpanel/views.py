import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from core.decorators import admin_required_api
from core.utils import flatten_categories, page_from_request
from services import api_client

CATEGORY_TYPES = [
    ("PRODUIT", "Produit"),
    ("HOTEL", "Hôtel"),
    ("VOITURE", "Voiture"),
    ("SERVICE", "Service"),
    ("AUTRE", "Autre"),
]
ATTR_TYPES = [
    ("TEXTE", "Texte"),
    ("NOMBRE", "Nombre"),
    ("DATE", "Date"),
    ("BOOLEEN", "Oui / Non"),
]
PRODUCT_STATUSES = [("BROUILLON", "Brouillon"), ("PUBLIE", "Publié")]
PRODUCT_SOURCES = [
    ("MANUEL", "Manuel"),
    ("FACEBOOK", "Facebook"),
    ("ALIBABA", "Alibaba"),
    ("AUTRE", "Autre"),
]
ORDER_STATUSES = [
    ("EN_ATTENTE", "En attente"),
    ("CONFIRMEE", "Confirmée"),
    ("EN_LIVRAISON", "En livraison"),
    ("LIVREE", "Livrée"),
    ("ANNULEE", "Annulée"),
]
CITIES = [
    ("NOUADHIBOU", "Nouadhibou"),
    ("ZOUERAT", "Zouérat"),
    ("NOUAKCHOTT", "Nouakchott"),
]
PUB_STATUSES = [("BROUILLON", "Brouillon"), ("PUBLIE", "Publié")]


def _token(request) -> str:
    return request.jwt_token


def _find_in_tree(nodes, cid):
    for n in nodes or []:
        if str(n.get("id")) == str(cid):
            return n
        found = _find_in_tree(n.get("children") or [], cid)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_required_api
@require_http_methods(["GET"])
def dashboard(request):
    token = _token(request)
    pending = api_client.admin_get_orders(token, statut="EN_ATTENTE", page=0, size=5)
    recent = api_client.admin_get_orders(token, page=0, size=8)
    notifs = api_client.admin_get_notifications(token, lu=False, page=0, size=8)
    unread = api_client.admin_unread_count(token)

    pending_data = pending.data if pending.ok else {}
    recent_data = recent.data if recent.ok else {}
    notifs_data = notifs.data if notifs.ok else {}
    unread_count = unread.data.get("count", 0) if unread.ok and isinstance(unread.data, dict) else 0

    for result in (pending, recent, notifs, unread):
        if not result.ok:
            messages.error(request, result.error or api_client.UNAVAILABLE)
            break

    return render(
        request,
        "adminpanel/dashboard.html",
        {
            "pending_count": pending_data.get("totalElements", 0) if isinstance(pending_data, dict) else 0,
            "pending_orders": pending_data.get("content") or [] if isinstance(pending_data, dict) else [],
            "recent_orders": recent_data.get("content") or [] if isinstance(recent_data, dict) else [],
            "notifications": notifs_data.get("content") or [] if isinstance(notifs_data, dict) else [],
            "unread_count": unread_count,
        },
    )


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------

@admin_required_api
@require_http_methods(["GET"])
def category_list(request):
    result = api_client.get_categories()
    tree = result.data if result.ok and isinstance(result.data, list) else []
    if not result.ok:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(request, "adminpanel/categories/list.html", {"categories": tree})


def _category_payload(request) -> dict:
    parent = request.POST.get("parentId") or None
    return {
        "nom": (request.POST.get("nom") or "").strip(),
        "type": request.POST.get("type") or "PRODUIT",
        "parentId": int(parent) if parent else None,
        "imageUrl": (request.POST.get("imageUrl") or "").strip() or None,
    }


@admin_required_api
@require_http_methods(["GET", "POST"])
def category_create(request):
    cats = api_client.get_categories()
    flat = flatten_categories(cats.data if cats.ok else [])
    if request.method == "POST":
        payload = _category_payload(request)
        result = api_client.admin_create_category(_token(request), payload)
        if result.ok:
            messages.success(request, "Catégorie créée.")
            return redirect("adminpanel:category_list")
        messages.error(request, result.error or "Création impossible.")
    return render(
        request,
        "adminpanel/categories/form.html",
        {"category": None, "parents": flat, "types": CATEGORY_TYPES},
    )


@admin_required_api
@require_http_methods(["GET", "POST"])
def category_edit(request, category_id):
    cats = api_client.get_categories()
    tree = cats.data if cats.ok else []
    category = _find_in_tree(tree, category_id)
    if not category:
        messages.error(request, "Catégorie introuvable.")
        return redirect("adminpanel:category_list")
    flat = [c for c in flatten_categories(tree) if str(c["id"]) != str(category_id)]
    if request.method == "POST":
        payload = _category_payload(request)
        result = api_client.admin_update_category(_token(request), category_id, payload)
        if result.ok:
            messages.success(request, "Catégorie mise à jour.")
            return redirect("adminpanel:category_list")
        messages.error(request, result.error or "Mise à jour impossible.")
    return render(
        request,
        "adminpanel/categories/form.html",
        {"category": category, "parents": flat, "types": CATEGORY_TYPES},
    )


@admin_required_api
@require_POST
def category_delete(request, category_id):
    result = api_client.admin_delete_category(_token(request), category_id)
    if result.ok:
        messages.success(request, "Catégorie supprimée.")
    else:
        messages.error(request, result.error or "Suppression impossible.")
    return redirect("adminpanel:category_list")


@admin_required_api
@require_http_methods(["GET", "POST"])
def category_attributes(request, category_id):
    cats = api_client.get_categories()
    category = _find_in_tree(cats.data if cats.ok else [], category_id)
    attrs = api_client.get_category_attributes(category_id)
    attributes = attrs.data if attrs.ok and isinstance(attrs.data, list) else []
    if request.method == "POST":
        payload = {
            "nomAttribut": (request.POST.get("nomAttribut") or "").strip(),
            "typeValeur": request.POST.get("typeValeur") or "TEXTE",
        }
        result = api_client.admin_add_attribute(_token(request), category_id, payload)
        if result.ok:
            messages.success(request, "Attribut ajouté.")
            return redirect("adminpanel:category_attributes", category_id=category_id)
        messages.error(request, result.error or "Ajout impossible.")
    return render(
        request,
        "adminpanel/categories/attributes.html",
        {
            "category": category,
            "attributes": attributes,
            "attr_types": ATTR_TYPES,
            "category_id": category_id,
        },
    )


@admin_required_api
@require_POST
def category_attribute_delete(request, category_id, attribute_id):
    result = api_client.admin_delete_attribute(_token(request), category_id, attribute_id)
    if result.ok:
        messages.success(request, "Attribut supprimé.")
    else:
        messages.error(request, result.error or "Suppression impossible.")
    return redirect("adminpanel:category_attributes", category_id=category_id)


# ---------------------------------------------------------------------------
# Produits
# ---------------------------------------------------------------------------

def _product_payload(request) -> dict:
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
    return {
        "nom": (request.POST.get("nom") or "").strip(),
        "description": (request.POST.get("description") or "").strip() or None,
        "prix": request.POST.get("prix") or "0",
        "stock": int(stock) if str(stock).isdigit() else 0,
        "categoryId": int(category_id) if category_id else None,
        "sourceOrigine": request.POST.get("sourceOrigine") or "MANUEL",
        "sourceUrl": (request.POST.get("sourceUrl") or "").strip() or None,
        "statut": request.POST.get("statut") or "BROUILLON",
        "attributs": attributs,
    }


@admin_required_api
@require_http_methods(["GET"])
def product_list(request):
    page = page_from_request(request)
    statut = request.GET.get("statut") or ""
    category_id = request.GET.get("category") or ""
    q = (request.GET.get("q") or "").strip()
    result = api_client.admin_get_products(
        _token(request),
        statut=statut or None,
        category_id=category_id or None,
        q=q or None,
        page=page - 1,
        size=20,
    )
    products, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        products = result.data.get("content") or []
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    cats = api_client.get_categories()
    return render(
        request,
        "adminpanel/products/list.html",
        {
            "products": products,
            "pagination": pagination,
            "page": page,
            "statut": statut,
            "category_id": category_id,
            "q": q,
            "statuses": PRODUCT_STATUSES,
            "categories_flat": flatten_categories(cats.data if cats.ok else []),
        },
    )


@admin_required_api
@require_http_methods(["GET", "POST"])
def product_create(request):
    cats = api_client.get_categories()
    flat = flatten_categories(cats.data if cats.ok else [])
    if request.method == "POST":
        payload = _product_payload(request)
        result = api_client.admin_create_product(_token(request), payload)
        if result.ok and isinstance(result.data, dict):
            messages.success(request, "Produit créé. Vous pouvez ajouter des images.")
            return redirect("adminpanel:product_images", product_id=result.data.get("id"))
        messages.error(request, result.error or "Création impossible.")
    return render(
        request,
        "adminpanel/products/form.html",
        {
            "product": None,
            "product_attrs_json": "[]",
            "categories_flat": flat,
            "statuses": PRODUCT_STATUSES,
            "sources": PRODUCT_SOURCES,
        },
    )


@admin_required_api
@require_http_methods(["GET", "POST"])
def product_edit(request, product_id):
    token = _token(request)
    prod = api_client.admin_get_product(token, product_id)
    if not prod.ok:
        messages.error(request, prod.error or "Produit introuvable.")
        return redirect("adminpanel:product_list")
    cats = api_client.get_categories()
    flat = flatten_categories(cats.data if cats.ok else [])
    if request.method == "POST":
        payload = _product_payload(request)
        result = api_client.admin_update_product(token, product_id, payload)
        if result.ok:
            messages.success(request, "Produit mis à jour.")
            return redirect("adminpanel:product_list")
        messages.error(request, result.error or "Mise à jour impossible.")
    return render(
        request,
        "adminpanel/products/form.html",
        {
            "product": prod.data,
            "product_attrs_json": json.dumps(prod.data.get("attributs") or []),
            "categories_flat": flat,
            "statuses": PRODUCT_STATUSES,
            "sources": PRODUCT_SOURCES,
        },
    )


@admin_required_api
@require_POST
def product_delete(request, product_id):
    result = api_client.admin_delete_product(_token(request), product_id)
    if result.ok:
        messages.success(request, "Produit supprimé.")
    else:
        messages.error(request, result.error or "Suppression impossible.")
    return redirect("adminpanel:product_list")


@admin_required_api
@require_http_methods(["GET", "POST"])
def product_images(request, product_id):
    token = _token(request)
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Choisissez une image (jpg, png, webp — 5 Mo max).")
        else:
            result = api_client.admin_upload_product_image(token, product_id, upload)
            if result.ok:
                messages.success(request, "Image ajoutée.")
            else:
                messages.error(request, result.error or "Upload impossible.")
        return redirect("adminpanel:product_images", product_id=product_id)

    prod = api_client.admin_get_product(token, product_id)
    if not prod.ok:
        messages.error(request, prod.error or "Produit introuvable.")
        return redirect("adminpanel:product_list")
    return render(request, "adminpanel/products/images.html", {"product": prod.data})


@admin_required_api
@require_POST
def product_image_delete(request, product_id, image_id):
    result = api_client.admin_delete_product_image(_token(request), product_id, image_id)
    if result.ok:
        messages.success(request, "Image supprimée.")
    else:
        messages.error(request, result.error or "Suppression impossible.")
    return redirect("adminpanel:product_images", product_id=product_id)


@admin_required_api
@require_http_methods(["GET", "POST"])
def product_import(request):
    cats = api_client.get_categories()
    flat = flatten_categories(cats.data if cats.ok else [])
    csv_result = None
    if request.method == "POST":
        action = request.POST.get("action")
        token = _token(request)
        if action == "url":
            url = (request.POST.get("url") or "").strip()
            category_id = request.POST.get("categoryId") or None
            if not url:
                messages.error(request, "Collez une URL.")
            else:
                result = api_client.admin_import_url(token, url, category_id)
                if result.ok:
                    messages.success(request, "Import URL : brouillon créé (stub).")
                    if isinstance(result.data, dict) and result.data.get("id"):
                        return redirect("adminpanel:product_edit", product_id=result.data["id"])
                else:
                    messages.error(request, result.error or "Import URL impossible.")
        elif action == "csv":
            upload = request.FILES.get("file")
            if not upload:
                messages.error(request, "Choisissez un fichier CSV.")
            else:
                result = api_client.admin_import_csv(token, upload)
                if result.ok:
                    csv_result = result.data
                    imported = csv_result.get("imported", 0) if isinstance(csv_result, dict) else 0
                    messages.success(request, f"Import CSV terminé : {imported} produit(s).")
                else:
                    messages.error(request, result.error or "Import CSV impossible.")
    return render(
        request,
        "adminpanel/products/import.html",
        {"categories_flat": flat, "csv_result": csv_result},
    )


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------

@admin_required_api
@require_http_methods(["GET"])
def order_list(request):
    page = page_from_request(request)
    statut = request.GET.get("statut") or ""
    ville = request.GET.get("ville") or ""
    result = api_client.admin_get_orders(
        _token(request),
        statut=statut or None,
        ville=ville or None,
        page=page - 1,
        size=20,
    )
    orders, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        orders = result.data.get("content") or []
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "adminpanel/orders/list.html",
        {
            "orders": orders,
            "pagination": pagination,
            "page": page,
            "statut": statut,
            "ville": ville,
            "statuses": ORDER_STATUSES,
            "cities": CITIES,
        },
    )


def _find_order(token, order_id):
    page = 0
    while page < 20:
        result = api_client.admin_get_orders(token, page=page, size=50)
        if not result.ok or not isinstance(result.data, dict):
            return None, result
        for order in result.data.get("content") or []:
            if str(order.get("id")) == str(order_id):
                return order, result
        total = result.data.get("totalPages") or 1
        page += 1
        if page >= total:
            break
    return None, None


@admin_required_api
@require_http_methods(["GET", "POST"])
def order_detail(request, order_id):
    token = _token(request)
    if request.method == "POST":
        statut = request.POST.get("statut")
        result = api_client.admin_update_order_status(token, order_id, statut)
        if result.ok:
            messages.success(request, "Statut mis à jour.")
            return redirect("adminpanel:order_detail", order_id=order_id)
        messages.error(request, result.error or "Mise à jour impossible.")

    order, lookup = _find_order(token, order_id)
    if not order:
        if lookup is not None and not lookup.ok:
            messages.error(request, lookup.error or api_client.UNAVAILABLE)
        else:
            messages.error(request, "Commande introuvable.")
        return redirect("adminpanel:order_list")
    return render(
        request,
        "adminpanel/orders/detail.html",
        {"order": order, "statuses": ORDER_STATUSES},
    )


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------

def _publication_payload(request) -> dict:
    produit = request.POST.get("produitLieId") or None
    return {
        "titre": (request.POST.get("titre") or "").strip(),
        "contenu": (request.POST.get("contenu") or "").strip(),
        "imageUrl": (request.POST.get("imageUrl") or "").strip() or None,
        "produitLieId": int(produit) if produit else None,
        "statut": request.POST.get("statut") or "BROUILLON",
    }


@admin_required_api
@require_http_methods(["GET"])
def publication_list(request):
    page = page_from_request(request)
    result = api_client.admin_get_publications(_token(request), page=page - 1, size=20)
    publications, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        publications = result.data.get("content") or []
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "adminpanel/publications/list.html",
        {"publications": publications, "pagination": pagination, "page": page},
    )


@admin_required_api
@require_http_methods(["GET", "POST"])
def publication_create(request):
    if request.method == "POST":
        result = api_client.admin_create_publication(_token(request), _publication_payload(request))
        if result.ok:
            messages.success(request, "Publication créée.")
            return redirect("adminpanel:publication_list")
        messages.error(request, result.error or "Création impossible.")
    return render(
        request,
        "adminpanel/publications/form.html",
        {"publication": None, "statuses": PUB_STATUSES},
    )


@admin_required_api
@require_http_methods(["GET", "POST"])
def publication_edit(request, publication_id):
    # Pas de GET /admin/publications/{id} : on cherche dans la liste paginée.
    found = None
    page = 0
    while page < 20:
        listing = api_client.admin_get_publications(_token(request), page=page, size=50)
        if not listing.ok:
            messages.error(request, listing.error or api_client.UNAVAILABLE)
            return redirect("adminpanel:publication_list")
        for pub in listing.data.get("content") or []:
            if str(pub.get("id")) == str(publication_id):
                found = pub
                break
        if found:
            break
        if page + 1 >= (listing.data.get("totalPages") or 1):
            break
        page += 1
    if not found:
        messages.error(request, "Publication introuvable.")
        return redirect("adminpanel:publication_list")

    if request.method == "POST":
        result = api_client.admin_update_publication(
            _token(request), publication_id, _publication_payload(request)
        )
        if result.ok:
            messages.success(request, "Publication mise à jour.")
            return redirect("adminpanel:publication_list")
        messages.error(request, result.error or "Mise à jour impossible.")
    return render(
        request,
        "adminpanel/publications/form.html",
        {"publication": found, "statuses": PUB_STATUSES},
    )


@admin_required_api
@require_POST
def publication_delete(request, publication_id):
    result = api_client.admin_delete_publication(_token(request), publication_id)
    if result.ok:
        messages.success(request, "Publication supprimée.")
    else:
        messages.error(request, result.error or "Suppression impossible.")
    return redirect("adminpanel:publication_list")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@admin_required_api
@require_http_methods(["GET"])
def notification_list(request):
    page = page_from_request(request)
    lu_param = request.GET.get("lu")
    lu = None
    if lu_param == "0":
        lu = False
    elif lu_param == "1":
        lu = True
    result = api_client.admin_get_notifications(_token(request), lu=lu, page=page - 1, size=20)
    notifications, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        notifications = result.data.get("content") or []
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "adminpanel/notifications/list.html",
        {
            "notifications": notifications,
            "pagination": pagination,
            "page": page,
            "lu": lu_param or "",
        },
    )


@admin_required_api
@require_POST
def notification_read(request, notification_id):
    result = api_client.admin_mark_notification_read(_token(request), notification_id)
    if result.ok:
        messages.success(request, "Notification marquée comme lue.")
    else:
        messages.error(request, result.error or "Action impossible.")
    next_url = request.POST.get("next") or reverse("adminpanel:notification_list")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("adminpanel:notification_list")


# ---------------------------------------------------------------------------
# Comptes utilisateurs
# ---------------------------------------------------------------------------

USER_ROLES = [("ADMIN", "Admin"), ("CLIENT", "Client")]


@admin_required_api
@require_http_methods(["GET"])
def user_list(request):
    page = page_from_request(request)
    role = request.GET.get("role") or ""
    if role not in {"ADMIN", "CLIENT"}:
        role = ""
    result = api_client.admin_get_users(
        _token(request),
        role=role or None,
        page=page - 1,
        size=20,
    )
    users, pagination = [], None
    if result.ok and isinstance(result.data, dict):
        users = result.data.get("content") or []
        pagination = result.data
    else:
        messages.error(request, result.error or api_client.UNAVAILABLE)
    return render(
        request,
        "adminpanel/users/list.html",
        {
            "users": users,
            "pagination": pagination,
            "page": page,
            "role": role,
            "roles": USER_ROLES,
            "current_user_id": request.user_id,
        },
    )


@admin_required_api
@require_http_methods(["GET", "POST"])
def user_create(request):
    form = {
        "nom": "",
        "telephone": "",
        "role": "CLIENT",
    }
    if request.method == "POST":
        form["nom"] = (request.POST.get("nom") or "").strip()
        form["telephone"] = (request.POST.get("telephone") or "").strip()
        form["role"] = request.POST.get("role") or "CLIENT"
        password = request.POST.get("password") or ""
        if form["role"] not in {"ADMIN", "CLIENT"}:
            messages.error(request, "Rôle invalide.")
        elif not form["nom"] or not form["telephone"] or not password:
            messages.error(request, "Nom, téléphone et mot de passe sont obligatoires.")
        else:
            result = api_client.admin_create_user(
                _token(request),
                {
                    "nom": form["nom"],
                    "telephone": form["telephone"],
                    "password": password,
                    "role": form["role"],
                },
            )
            if result.ok:
                messages.success(request, "Compte créé.")
                return redirect("adminpanel:user_list")
            messages.error(request, result.error or "Création impossible.")
    return render(
        request,
        "adminpanel/users/form.html",
        {"form": form, "roles": USER_ROLES},
    )


@admin_required_api
@require_POST
def user_toggle_role(request, user_id):
    if str(user_id) == str(request.user_id):
        messages.error(request, "Vous ne pouvez pas modifier votre propre rôle.")
        return redirect("adminpanel:user_list")
    current = request.POST.get("current_role") or ""
    new_role = "CLIENT" if current == "ADMIN" else "ADMIN"
    result = api_client.admin_update_user_role(_token(request), user_id, new_role)
    if result.ok:
        messages.success(request, "Rôle mis à jour.")
    else:
        messages.error(request, result.error or "Mise à jour du rôle impossible.")
    return redirect("adminpanel:user_list")


@admin_required_api
@require_POST
def user_toggle_status(request, user_id):
    if str(user_id) == str(request.user_id):
        messages.error(request, "Vous ne pouvez pas modifier le statut de votre propre compte.")
        return redirect("adminpanel:user_list")
    actuel = request.POST.get("actif") == "1"
    result = api_client.admin_update_user_status(_token(request), user_id, not actuel)
    if result.ok:
        messages.success(request, "Compte bloqué." if actuel else "Compte débloqué.")
    else:
        messages.error(request, result.error or "Mise à jour du statut impossible.")
    return redirect("adminpanel:user_list")


@admin_required_api
@require_POST
def user_delete(request, user_id):
    if str(user_id) == str(request.user_id):
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect("adminpanel:user_list")
    result = api_client.admin_delete_user(_token(request), user_id)
    if result.ok:
        messages.success(request, "Compte supprimé.")
    else:
        messages.error(request, result.error or "Suppression impossible.")
    return redirect("adminpanel:user_list")
