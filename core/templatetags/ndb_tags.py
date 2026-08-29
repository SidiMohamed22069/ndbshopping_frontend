from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django import template
from django.conf import settings
from django.utils.translation import gettext as _

from core.utils import extract_image_path

register = template.Library()


def _storage_relative(raw: str) -> str:
    """products/12/uuid.jpg — sans préfixe /media, à partir des formes API."""
    path = raw.strip().replace("\\", "/")
    if path.startswith("http://") or path.startswith("https://"):
        path = urlsplit(path).path
    path = path.lstrip("/")
    if path.lower().startswith("media/"):
        path = path[6:]
    return path.lstrip("/")


def _join_media_url(path: str) -> str:
    raw = str(path).strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.replace("/media/media/", "/media/")
    rel = _storage_relative(raw)
    if not rel:
        return ""
    base = settings.MEDIA_BACKEND_URL.rstrip("/")
    if base.lower().endswith("/media"):
        return f"{base}/{rel}"
    return f"{base}/media/{rel}"


def _with_cache_bust(url: str, version=None) -> str:
    if not url:
        return ""
    token = "" if version in (None, "") else str(version).strip()
    if not token:
        token = urlsplit(url).path.rsplit("/", 1)[-1]
    if not token:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["v"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@register.filter
def image_path(value) -> str:
    """relative_path / url / imageUrl / image_url depuis un objet image ou une catégorie."""
    return extract_image_path(value)


@register.filter
def media_url(path: str | None, version=None) -> str:
    """MEDIA_BACKEND_URL + '/' + relative_path, sans /media/ dupliqué, avec ?v=."""
    if not path:
        return ""
    return _with_cache_bust(_join_media_url(str(path)), version)


@register.filter
def media_src(value, version=None) -> str:
    """URL complète depuis un objet image API (id utilisé pour le cache-busting si besoin)."""
    path = extract_image_path(value)
    if not path:
        return ""
    if version in (None, "") and isinstance(value, dict):
        version = value.get("id")
    return media_url(path, version)


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
        "REJETE": _("Refusé"),
        "VENDU": _("Vendu"),
        "ARCHIVE": _("Archivé"),
        "PRODUIT": _("Produit"),
        "HOTEL": _("Hôtel"),
        "VOITURE": _("Voiture"),
        "SERVICE": _("Service"),
        "AUTRE": _("Autre"),
        "CLIENT": _("Client"),
        "ADMIN": _("Admin"),
        "NOUVELLE_COMMANDE": _("Nouvelle commande"),
        "PRODUIT_A_VALIDER": _("Produit à valider"),
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
        "REJETE": "danger",
        "VENDU": "dark",
        "ARCHIVE": "light",
        "NOUVELLE_COMMANDE": "warning",
        "PRODUIT_A_VALIDER": "info",
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
