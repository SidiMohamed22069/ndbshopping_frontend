IMAGE_PATH_KEYS = (
    "relativePath",
    "relative_path",
    "url",
    "imageUrl",
    "image_url",
    "path",
)


def extract_image_path(value) -> str:
    """Chemin d'image depuis une chaîne ou un objet API (camelCase / snake_case)."""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in IMAGE_PATH_KEYS:
            raw = value.get(key)
            if raw:
                return str(raw).strip()
        return ""
    getter = getattr(value, "get", None)
    if callable(getter):
        for key in IMAGE_PATH_KEYS:
            raw = getter(key)
            if raw:
                return str(raw).strip()
    return str(value).strip()


def normalize_product_images(product: dict | None) -> dict | None:
    """Uniformise product.images / videos à partir du JSON API."""
    if not isinstance(product, dict):
        return product
    raw = product.get("images")
    if raw is None:
        raw = product.get("product_images") or product.get("productImages") or []
    images = []
    for img in raw or []:
        path = extract_image_path(img)
        if not path:
            continue
        img_id = img.get("id") if isinstance(img, dict) else None
        images.append({"id": img_id, "url": path})
    videos = []
    for vid in product.get("videos") or []:
        path = extract_image_path(vid)
        if not path:
            continue
        vid_id = vid.get("id") if isinstance(vid, dict) else None
        videos.append({"id": vid_id, "url": path})
    normalized = dict(product)
    normalized["images"] = images
    normalized["videos"] = videos
    normalized["aVideo"] = bool(product.get("aVideo") or videos)
    return normalized


def normalize_category_image(category: dict | None) -> dict | None:
    """Uniformise imageUrl (image_url / imageUrl) y compris les enfants."""
    if not isinstance(category, dict):
        return category
    normalized = dict(category)
    path = (
        normalized.get("imageUrl")
        or normalized.get("image_url")
        or normalized.get("image")
        or ""
    )
    normalized["imageUrl"] = path or None
    children = normalized.get("children")
    if isinstance(children, list):
        normalized["children"] = [normalize_category_image(child) for child in children]
    return normalized


def flatten_categories(categories: list | None, prefix: str = "") -> list[dict]:
    """Aplatit l'arbre de catégories pour les <select>."""
    result: list[dict] = []
    for cat in categories or []:
        result.append(
            {
                "id": cat.get("id"),
                "nom": f"{prefix}{cat.get('nom', '')}",
                "type": cat.get("type"),
                "imageUrl": cat.get("imageUrl") or cat.get("image_url"),
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
