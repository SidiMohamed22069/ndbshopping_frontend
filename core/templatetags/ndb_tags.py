from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def media_url(path: str | None) -> str:
    """Construit l'URL publique d'une image backend (/media/...)."""
    if not path:
        return ""
    if str(path).startswith("http://") or str(path).startswith("https://"):
        return str(path)
    base = settings.MEDIA_BACKEND_URL.rstrip("/")
    return f"{base}/{str(path).lstrip('/')}"


@register.filter
def mru(value) -> str:
    """Formate un prix en ouguiya (UM)."""
    if value is None or value == "":
        return "—"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    formatted = f"{number:,.0f}".replace(",", " ")
    return f"{formatted} UM"


@register.filter
def ville_label(code: str | None) -> str:
    labels = {
        "NOUADHIBOU": "Nouadhibou",
        "ZOUERAT": "Zouérat",
        "NOUAKCHOTT": "Nouakchott",
    }
    return labels.get(code or "", code or "—")


@register.filter
def statut_label(code: str | None) -> str:
    labels = {
        "EN_ATTENTE": "En attente",
        "CONFIRMEE": "Confirmée",
        "EN_LIVRAISON": "En livraison",
        "LIVREE": "Livrée",
        "ANNULEE": "Annulée",
        "BROUILLON": "Brouillon",
        "PUBLIE": "Publié",
        "PRODUIT": "Produit",
        "HOTEL": "Hôtel",
        "VOITURE": "Voiture",
        "SERVICE": "Service",
        "AUTRE": "Autre",
        "CLIENT": "Client",
        "ADMIN": "Admin",
        "NOUVELLE_COMMANDE": "Nouvelle commande",
        "SOLDE_SMS_BAS": "Solde SMS bas",
        "MANUEL": "Manuel",
        "FACEBOOK": "Facebook",
        "ALIBABA": "Alibaba",
        "TEXTE": "Texte",
        "NOMBRE": "Nombre",
        "DATE": "Date",
        "BOOLEEN": "Oui / Non",
    }
    return labels.get(code or "", code or "—")


@register.filter
def statut_badge(code: str | None) -> str:
    mapping = {
        "EN_ATTENTE": "warning",
        "CONFIRMEE": "info",
        "EN_LIVRAISON": "primary",
        "LIVREE": "success",
        "ANNULEE": "secondary",
        "BROUILLON": "secondary",
        "PUBLIE": "success",
    }
    return mapping.get(code or "", "secondary")


@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    """Remplace des paramètres GET en conservant les autres (pagination + filtres)."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()
