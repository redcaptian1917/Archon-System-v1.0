# --- Archon-App v1.0 Dockerfile ---
# This container is the "Archon-Prime" control center.
# It runs the API Gateway, the CEO Agent, and all Specialist Crews.
FROM python:3.11-slim-bookworm

# 1. Set working directory
WORKDIR /app

# 2. Install all System Dependencies
RUN apt-get update && apt-get install -y \
    # --- Core ---
    git \
    curl \
    wget \
    build-essential \
    python3-dev \
    libpq-dev \
    # --- Networking & OPSEC ---
    tor \
    proxychains4 \
    ansible \
    sshpass \
    macchanger \
    # --- Security & Pentesting ---
    nmap \
    sqlmap \
    nikto \
    openvas-cli \ # GVM/OpenVAS CLI client
    # --- Forensics ---
    sleuthkit \
    # --- Anonymization ---
    mat2 \
    # --- Media & Senses ---
    ffmpeg \
    libnotify-bin \
    scrot \
    libopencv-dev \
    libportaudio2 \
    # --- Utilities ---
    jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Install GeckoDriver for Selenium/BrowserTool
RUN GECKO_VER="v0.34.0" && \
    wget "https://github.com/mozilla/geckodriver/releases/download/${GECKO_VER}/geckodriver-${GECKO_VER}-linux64.tar.gz" && \
    tar -xzf geckodriver-${GECKO_VER}-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    rm geckodriver-${GECKO_VER}-linux64.tar.gz

# 4. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the entire application structure
COPY . .

# 6. Set permissions for all scripts
RUN chmod +x /app/init-db.sh
RUN find /app -name "*.py" -exec chmod +x {} +
RUN find /app -name "*.sh" -exec chmod +x {} +

# 7. Default command (keeps the container alive)
# The API Gateway and CEO scripts are started by docker-compose or exec.
CMD ["tail", "-f", "/dev/null"]
