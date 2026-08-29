"""Validation et réponses JSON pour la galerie / les vidéos produit."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.translation import gettext as _

from core.templatetags.ndb_tags import media_src

IMAGE_MAX_BYTES = 5 * 1024 * 1024
VIDEO_MAX_BYTES = 20 * 1024 * 1024
MAX_IMAGES = 6
MAX_VIDEOS = 2
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm"}


def posted_file(request, field_name: str):
    upload = request.FILES.get(field_name)
    if upload and getattr(upload, "size", 0):
        return upload
    return None


def validate_image(upload) -> str | None:
    if upload.size > IMAGE_MAX_BYTES:
        return _("Image trop volumineuse (5 Mo maximum).")
    content_type = (upload.content_type or "").lower()
    name = (upload.name or "").lower()
    if content_type not in IMAGE_CONTENT_TYPES and not name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return _("Format non accepté. Utilisez JPG, PNG ou WebP.")
    return None


def validate_video(upload) -> str | None:
    if upload.size > VIDEO_MAX_BYTES:
        return _("Vidéo trop volumineuse (20 Mo maximum).")
    content_type = (upload.content_type or "").lower()
    name = (upload.name or "").lower()
    if content_type not in VIDEO_CONTENT_TYPES and not name.endswith((".mp4", ".webm")):
        return _("Format non accepté. Utilisez MP4 ou WebM.")
    return None


def serialize_media_item(data) -> dict | None:
    if not isinstance(data, dict):
        return None
    item_id = data.get("id")
    url = media_src(data)
    if not item_id:
        return None
    return {"id": item_id, "url": url}


def media_initial_json(product: dict | None) -> str:
    product = product or {}
    images = [item for item in (serialize_media_item(i) for i in (product.get("images") or [])) if item]
    videos = [item for item in (serialize_media_item(v) for v in (product.get("videos") or [])) if item]
    return json.dumps({"images": images, "videos": videos})


def json_ok(item=None) -> JsonResponse:
    payload = {"ok": True}
    if item is not None:
        payload["item"] = item
    return JsonResponse(payload)


def json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


def upload_and_respond(request, product_id, field_name: str, validator, api_fn) -> JsonResponse:
    upload = posted_file(request, field_name)
    if not upload:
        return json_error(_("Choisissez un fichier."))
    error = validator(upload)
    if error:
        return json_error(error)
    result = api_fn(request.jwt_token, product_id, upload)
    if not result.ok:
        return json_error(result.error or _("Impossible d'envoyer le fichier."), result.status or 400)
    item = serialize_media_item(result.data)
    if not item:
        return json_error(_("Impossible d'envoyer le fichier."), 502)
    return json_ok(item)
