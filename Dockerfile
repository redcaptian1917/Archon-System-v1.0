# -----------------------------------------------------------------
# ARCHON SYSTEM - MAIN APPLICATION DOCKERFILE (vFINAL)
#
# This is the "Genetic Blueprint" for the `archon-app` and
# `api-gateway` services defined in docker-compose.yml.
#
# It builds a Debian-based container with all system
# dependencies for all 14+ crews and 40+ tools.
# -----------------------------------------------------------------

# Start from a clean, modern, and minimal Debian base
FROM python:3.11-slim-bookworm

# 1. Set working directory
WORKDIR /app

# Set non-interactive mode for apt-get to prevent prompts
ENV DEBIAN_FRONTEND=noninteractive

# 2. Install all System Dependencies (Consolidated)
RUN apt-get update && apt-get install -y \
    # --- Core ---
    git \
    curl \
    wget \
    build-essential \
    python3-dev \
    libpq-dev \
    postgresql-client \
    python3-git \
    
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
    openvas-cli \
    
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
    
    # --- Browser Automation ---
    firefox-esr \
    
    # --- Utilities ---
    jq \
    
    # --- Cleanup ---
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Install GeckoDriver for Selenium/BrowserTool
RUN GECKO_VER="v0.34.0" && \
    wget "https://github.com/mozilla/geckodriver/releases/download/${GECKO_VER}/geckodriver-${GECKO_VER}-linux64.tar.gz" && \
    tar -xzf geckodriver-${GECKO_VER}-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    rm geckodriver-${GECKO_VER}-linux64.tar.gz

# 4. Install Python Dependencies
# We copy this file first to leverage Docker's build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the entire application structure
COPY . .

# 6. Set permissions for all scripts
# This ensures all your scripts are executable inside the container
RUN chmod +x /app/init-db.sh
RUN find /app -name "*.py" -exec chmod +x {} +
RUN find /app -name "*.sh" -exec chmod +x {} +

# 7. Default command (keeps the container alive)
# The API Gateway and CEO scripts are started by docker-compose or exec.
CMD ["tail", "-f", "/dev/null"]
