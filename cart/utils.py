"""
Panier invité : liste [{ "product_id": int, "quantite": int }, ...] dans la session.

Les prix ne sont JAMAIS stockés ici : l'affichage du total rappelle
GET /products/{id} pour le tarif à jour. Une fois connecté, on synchronise
vers POST /api/cart/sync (le backend remplace le panier serveur).
"""
from services import api_client

CART_SESSION_KEY = "cart"


def get_cart(session) -> list[dict]:
    cart = session.get(CART_SESSION_KEY)
    if not isinstance(cart, list):
        return []
    cleaned = []
    for item in cart:
        try:
            cleaned.append(
                {
                    "product_id": int(item["product_id"]),
                    "quantite": max(1, int(item["quantite"])),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return cleaned


def save_cart(session, cart: list[dict]) -> None:
    session[CART_SESSION_KEY] = cart
    session.modified = True


def cart_quantity(session) -> int:
    return sum(item["quantite"] for item in get_cart(session))


def add_item(session, product_id: int, quantite: int = 1) -> list[dict]:
    cart = get_cart(session)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantite"] += max(1, quantite)
            save_cart(session, cart)
            return cart
    cart.append({"product_id": product_id, "quantite": max(1, quantite)})
    save_cart(session, cart)
    return cart


def update_item(session, product_id: int, quantite: int) -> list[dict]:
    cart = get_cart(session)
    if quantite <= 0:
        cart = [i for i in cart if i["product_id"] != product_id]
    else:
        found = False
        for item in cart:
            if item["product_id"] == product_id:
                item["quantite"] = quantite
                found = True
                break
        if not found:
            cart.append({"product_id": product_id, "quantite": quantite})
    save_cart(session, cart)
    return cart


def remove_item(session, product_id: int) -> list[dict]:
    cart = [i for i in get_cart(session) if i["product_id"] != product_id]
    save_cart(session, cart)
    return cart


def clear_cart(session) -> None:
    session[CART_SESSION_KEY] = []
    session.modified = True


def to_sync_payload(session) -> list[dict]:
    """Format attendu par CartSyncRequest : productId + quantite."""
    return [{"productId": i["product_id"], "quantite": i["quantite"]} for i in get_cart(session)]


def sync_if_authenticated(request) -> None:
    """Pousse le panier session vers le backend si un JWT est présent."""
    token = request.session.get("jwt_token")
    if not token:
        return
    api_client.sync_cart(token, to_sync_payload(request.session))
