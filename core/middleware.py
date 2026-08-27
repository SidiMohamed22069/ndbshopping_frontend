"""
Attache à chaque requête les infos d'auth provenant de la session Django
(JWT Spring Boot), sans passer par django.contrib.auth.
"""


class ApiAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.jwt_token = request.session.get("jwt_token")
        request.user_role = request.session.get("user_role")
        request.user_nom = request.session.get("user_nom")
        request.user_id = request.session.get("user_id")
        request.is_authenticated_api = bool(request.jwt_token)
        request.is_admin_api = request.user_role == "ADMIN"
        return self.get_response(request)
