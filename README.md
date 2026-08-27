# NDB SHOPPING — Frontend Django

Frontend HTML de la marketplace **NDB SHOPPING** (Nouadhibou, Zouérat, Nouakchott).  
Ce projet **ne stocke aucune donnée métier** : pas de modèles User / Product / Order. Tout vit dans l'API Spring Boot. Django rend les templates, garde le JWT et le panier invité en session, et appelle l'API en HTTP/JSON.

## Prérequis

- Docker + Docker Compose
- L'API Spring Boot déjà déployée (ou accessible)

## Lancer en local

```bash
cp .env.example .env
```

Pour tester contre le backend déjà en ligne, éditez `.env` :

```
API_BASE_URL=https://ndbshopping.duckdns.org/api
MEDIA_BACKEND_URL=https://ndbshopping.duckdns.org/media
PUBLIC_BACKEND_HOST=ndbshopping.duckdns.org
DJANGO_DEBUG=True
DJANGO_COOKIE_SECURE=False
```

```bash
docker compose up --build
```

Ouvrez [http://localhost:8000](http://localhost:8000). Si le catalogue s'affiche, Django parle bien à l'API.

Sans Docker :

```bash
python -m venv .venv
source .venv/bin/activate   # Windows Git Bash : source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver
```

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `API_BASE_URL` | Appels **serveur → API**. En Docker sur le VPS : `http://backend:8080/api`. En local : URL publique HTTPS. |
| `MEDIA_BACKEND_URL` | Préfixe des images dans les templates (`/media/...`). Toujours une URL **publique**. |
| `PUBLIC_BACKEND_HOST` | Hôte du WebSocket STOMP **dans le navigateur**. Domaine public, jamais le nom du conteneur. |
| `DJANGO_SECRET_KEY` | Clé Django (générez-en une pour la prod). |
| `DJANGO_DEBUG` | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origines CSRF (`https://ndbshopping.duckdns.org`) |
| `DJANGO_COOKIE_SECURE` | `True` en HTTPS production |

## Déploiement (même VPS que le backend)

1. `API_BASE_URL=http://backend:8080/api` (réseau Docker interne).
2. Fusionnez le service `frontend` de `docker-compose.yml` dans celui du backend **ou** déclarez le réseau externe `ndbshopping_default`.
3. Nginx : `/` → Django `:8000`, `/api/` et `/media/` et `/ws` → backend.
4. Passez `DJANGO_COOKIE_SECURE=True` et une vraie `DJANGO_SECRET_KEY`.

Le WebSocket admin se connecte en **WSS** vers `PUBLIC_BACKEND_HOST/ws` (pas de proxy Django). Nginx doit upgrader `/ws`.

## Parcours utilisateurs

- Catalogue public, panier en session (prix toujours relus via `GET /products/{id}`).
- Commande : nom + téléphone + mot de passe → OTP SMS (`/api/auth/register-or-login` puis `/verify-otp`).
- Après OTP : JWT en session + `POST /api/cart/sync`.
- Admin : `/admin-ndb/` (rôle `ADMIN`). Notifications temps réel : topic `/topic/admin-notifications`.

## Structure

```
config/        settings, URLs, WSGI
core/          layout, décorateurs, contexte
catalog/       produits, catégories, publications
cart/          panier session
accounts/      OTP, commandes
adminpanel/    back-office
services/      client HTTP unique (api_client.py)
templates/     Bootstrap 5 (CDN cdnjs)
```
