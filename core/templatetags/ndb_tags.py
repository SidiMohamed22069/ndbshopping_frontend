from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings
from django.utils.translation import gettext as _

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
    unit = _("UM")
    return f"{formatted} {unit}"


@register.filter
def ville_label(code: str | None) -> str:
    labels = {
        "NOUADHIBOU": _("Nouadhibou"),
        "ZOUERAT": _("Zouérat"),
        "NOUAKCHOTT": _("Nouakchott"),
    }
    return labels.get(code or "", code or "—")


@register.filter
def statut_label(code: str | None) -> str:
    labels = {
        "EN_ATTENTE": _("En attente"),
        "CONFIRMEE": _("Confirmée"),
        "EN_LIVRAISON": _("En livraison"),
        "LIVREE": _("Livrée"),
        "ANNULEE": _("Annulée"),
        "BROUILLON": _("Brouillon"),
        "PUBLIE": _("Publié"),
        "PRODUIT": _("Produit"),
        "HOTEL": _("Hôtel"),
        "VOITURE": _("Voiture"),
        "SERVICE": _("Service"),
        "AUTRE": _("Autre"),
        "CLIENT": _("Client"),
        "ADMIN": _("Admin"),
        "NOUVELLE_COMMANDE": _("Nouvelle commande"),
        "SOLDE_SMS_BAS": _("Solde SMS bas"),
        "MANUEL": _("Manuel"),
        "FACEBOOK": "Facebook",
        "ALIBABA": "Alibaba",
        "TEXTE": _("Texte"),
        "NOMBRE": _("Nombre"),
        "DATE": _("Date"),
        "BOOLEEN": _("Oui / Non"),
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
