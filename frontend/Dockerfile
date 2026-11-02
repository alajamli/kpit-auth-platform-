# STAGE 1: Build de l'application Angular
FROM node:18-alpine AS build

WORKDIR /app

# Copie des fichiers de dépendances Node.js
COPY package*.json ./
RUN npm ci

# Copie du code source et compilation de production
COPY . .
RUN npm run build -- --configuration production

# STAGE 2: Serveur Nginx de Production
FROM nginx:alpine

# 1. Nettoyer le dossier HTML par défaut de Nginx
RUN rm -rf /usr/share/nginx/html/*

# 2. Copie de la configuration Nginx Reverse Proxy
# (template : l'image nginx applique envsubst au démarrage)
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV PORT=80
ENV BACKEND_URL=http://backend:5000
ENV BACKEND_HOST=backend
ENV NGINX_RESOLVER=127.0.0.11

# 3. Copie des fichiers compilés par Angular
COPY --from=build /app/dist/frontend /usr/share/nginx/html

# 4. Si Angular 17 a créé un sous-dossier 'browser', ramener les fichiers à la racine
RUN if [ -d "/usr/share/nginx/html/browser" ]; then \
        mv /usr/share/nginx/html/browser/* /usr/share/nginx/html/ && \
        rm -rf /usr/share/nginx/html/browser; \
    fi

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]