# --- Dockerfile ---
# Start from a clean Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# 1. Install System Dependencies
# We need:
# - tor: For the SOCKS proxy client
# - postgresql-client: For psycopg2
# - firefox-esr & wget: For Selenium/BrowserTool
# - libnotify-bin: For the daemon's notification tool
# - git, curl, etc: For general utilities
RUN apt-get update && apt-get install -y \
    tor \
    postgresql-client \
    firefox-esr \
    wget \
    git \
    curl \
    scrot \
    nmap \
    libnotify-bin \
    ffmpeg \
    jq \
    mat2 \
    python3-git \
    ansible \
    sshpass \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Install GeckoDriver for Selenium
RUN GECKO_VER="v0.34.0" && \
    wget "https://github.com/mozilla/geckodriver/releases/download/${GECKO_VER}/geckodriver-${GECKO_VER}-linux64.tar.gz" && \
    tar -xzf geckodriver-${GECKO_VER}-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/

# 3. Install Python Dependencies
# We'll copy just the requirements file first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy all your agent code into the container
COPY . .

# 5. Keep the container running
CMD ["tail", "-f", "/dev/null"]