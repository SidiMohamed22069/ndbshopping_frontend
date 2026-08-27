from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _


def login_required_api(view_func):
    """Redirige vers la connexion si la session n'a pas de JWT Spring Boot."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("jwt_token"):
            messages.warning(request, _("Veuillez vous connecter pour continuer."))
            login_url = reverse("accounts:login")
            return redirect(f"{login_url}?next={request.get_full_path()}")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_required_api(view_func):
    """Exige un JWT + rôle ADMIN (stocké en session après verify-otp)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("jwt_token"):
            messages.warning(request, _("Connectez-vous avec un compte administrateur."))
            login_url = reverse("accounts:login")
            return redirect(f"{login_url}?next={request.get_full_path()}")
        if request.session.get("user_role") != "ADMIN":
            messages.error(request, _("Accès réservé aux administrateurs."))
            return redirect("core:home")
        return view_func(request, *args, **kwargs)

    return _wrapped
