FROM python:3.11-slim

# Installation des dépendances système pour Chrome & Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    fonts-liberation \
    libasound2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Installation de Google Chrome Stable via le paquet .deb officiel
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source backend
COPY . .

# Création des dossiers nécessaires avec autorisations
RUN mkdir -p /app/robot_tests/suites /robot_tests/suites /app/instance /app/reports \
    && chmod -R 777 /app/robot_tests /robot_tests /app/instance /app/reports

EXPOSE 5000

# Démarrage de Gunicorn avec 1 Processus Multi-Threaded (Mémoire partagée pour les Jobs)
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 run:app"]