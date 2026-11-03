# Pinned to Debian bookworm: the floating "3.11-slim" tag now points to Debian trixie,
# where the `libasound2` package used below no longer exists (build error).
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#  - xvfb / xauth : virtual display so the (non-headless) Selenium suites can run in a container
#  - socat        : bridges http://localhost:4200 (URL hard-coded in the Robot suites) to the nginx container
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    unzip \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    xdg-utils \
    xvfb \
    xauth \
    socat \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome Stable (official .deb – apt resolves its remaining dependencies)
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Chrome refuses to start as root inside a container without these flags
# ("DevToolsActivePort file doesn't exist" / "Chrome failed to start: crashed").
# Patch the launcher script once so EVERY suite (hand-written or AI-generated) gets them.
RUN sed -i 's|"\$HERE/chrome" "\$@"|"$HERE/chrome" --no-sandbox --disable-dev-shm-usage --disable-gpu "$@"|' /opt/google/chrome/google-chrome \
    && grep -q -- '--no-sandbox' /opt/google/chrome/google-chrome

WORKDIR /app

# Python dependencies (separate layer = cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Backend source
COPY . .

RUN mkdir -p /app/robot_tests/suites /app/robot_tests/results /app/instance /app/reports \
    && chmod -R 777 /app/robot_tests /app/instance /app/reports

EXPOSE 5000 4200

# 1 worker + threads: Robot jobs live in memory, so they must share one process.
# socat : localhost:4200 -> frontend (nginx) so the unmodified Robot suites reach the UI
# Xvfb  : virtual 1920x1080 screen for Chrome. Started by hand (xvfb-run can hang in containers)
#         and in the background, so a display problem can never stop the API from starting.
CMD ["sh", "-c", "rm -f /tmp/.X99-lock /tmp/.X11-unix/X99; socat TCP-LISTEN:4200,fork,reuseaddr TCP:frontend:80 & Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & export DISPLAY=:99; i=0; while [ ! -e /tmp/.X11-unix/X99 ] && [ $i -lt 30 ]; do i=$((i+1)); sleep 0.2; done; exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - run:app"]
