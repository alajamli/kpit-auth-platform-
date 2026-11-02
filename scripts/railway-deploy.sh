#!/usr/bin/env bash
# Déploiement KPIT Auth Platform sur Railway, 100 % CLI (sans interface web).
# Prérequis : CLI installée (npm i -g @railway/cli) et `railway login` fait.
# Usage (depuis la racine du dépôt, Git Bash) :  bash scripts/railway-deploy.sh
set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-kpit-auth-platform}"
cd "$(dirname "$0")/.."

railway whoami >/dev/null || { echo "Non connecté : lance d'abord 'railway login'"; exit 1; }

# Lit une clé du .env sans l'afficher ni l'exécuter
env_get() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true; }

# --- 1. Projet + services -----------------------------------------------------
railway init --name "$PROJECT_NAME"
railway add --service backend
railway add --service frontend

# --- 2. Variables backend (secrets lus depuis .env, jamais affichés) ----------
JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
railway variables --service backend \
  --set "PORT=5000" \
  --set "FLASK_ENV=production" \
  --set "JWT_SECRET_KEY=$JWT_SECRET" \
  --set "GROQ_API_KEY=$(env_get GROQ_API_KEY)" \
  --set "SMTP_HOST=$(env_get SMTP_HOST)" \
  --set "SMTP_PORT=587" \
  --set "SMTP_USER=$(env_get SMTP_USER)" \
  --set "SMTP_PASSWORD=$(env_get SMTP_PASSWORD)" >/dev/null

# Volume persistant pour la base SQLite (instance/dev.db)
railway volume --service backend add --mount-path /app/instance

# --- 3. Variables frontend (nginx -> backend via le réseau privé Railway) -----
railway variables --service frontend \
  --set "PORT=80" \
  --set "BACKEND_URL=http://backend.railway.internal:5000" \
  --set "NGINX_RESOLVER=[fd12::10]" >/dev/null

# --- 4. Déploiement (le dossier courant est envoyé : il contient railway.json)
(cd backend  && railway up --service backend  --ci)
(cd frontend && railway up --service frontend --ci)

# --- 5. URL publique du frontend ----------------------------------------------
railway domain --service frontend
echo "Terminé. Logs : railway logs --service backend | railway logs --service frontend"
