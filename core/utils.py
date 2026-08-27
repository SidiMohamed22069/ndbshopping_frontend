def flatten_categories(categories: list | None, prefix: str = "") -> list[dict]:
    """Aplatit l'arbre de catégories pour les <select>."""
    result: list[dict] = []
    for cat in categories or []:
        result.append(
            {
                "id": cat.get("id"),
                "nom": f"{prefix}{cat.get('nom', '')}",
                "type": cat.get("type"),
                "imageUrl": cat.get("imageUrl"),
            }
        )
        children = cat.get("children") or []
        if children:
            result.extend(flatten_categories(children, prefix=f"{prefix}{cat.get('nom', '')} › "))
    return result


def safe_next_url(next_url: str | None, fallback: str = "/") -> str:
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return fallback


def page_from_request(request, default: int = 1) -> int:
    """Page 1-indexée dans l'URL → soustraire 1 avant l'appel API Spring."""
    try:
        page = int(request.GET.get("page", default))
    except (TypeError, ValueError):
        page = default
    return max(page, 1)
