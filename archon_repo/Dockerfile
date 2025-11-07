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

# Set the working directory inside the container
WORKDIR /app

# Set environment variable to prevent apt-get from hanging on user prompts
ENV DEBIAN_FRONTEND=noninteractive

# ----------------------------------------
# --- 1. SYSTEM DEPENDENCIES ---
# Install all required system packages for all tools.
# ----------------------------------------
RUN apt-get update && apt-get install -y \
    # --- CORE ---
    git                 # For GitTool & OfflineDBTool
    curl                # For general API calls
    wget                # For downloading drivers/files
    jq                  # For parsing JSON (e.g., CVESearchTool)
    
    # --- NETWORKING & OPSEC ---
    tor                 # For the SOCKS5 proxy (TOR_PROXY_URL)
    proxychains4        # For the ProxyChainsTool (layering)
    sshpass             # For Ansible password auth
    network-manager     # For nmcli (InterfaceControlTool)
    macchanger          # For MacChangerTool
    
    # --- PENTESTING & DFIR ---
    nmap                # For NmapTool
    sleuthkit           # For ForensicsTool (tsk_*)
    mat2                # For MetadataScrubberTool
    
    # --- INFRASTRUCTURE (IaC) ---
    ansible             # For AnsibleTool
    
    # --- BROWSER AUTOMATION ---
    firefox-esr         # The browser for Selenium
    
    # --- GUI/SENSORY (LOCAL) ---
    # These are for the *worker* agent, but installing in the
    # main app allows the API to test/validate media locally.
    ffmpeg              # For Whisper/Coqui audio processing
    libnotify-bin       # For DesktopNotificationTool
    libopencv-dev       # For OpenCV (AnalyzeScreenshotTool)
    
    # --- PYTHON & DB LIBS ---
    postgresql-client   # For psycopg2 (Postgres driver)
    python3-pip         # To install requirements.txt
    python3-git         # For GitPython library
    python3-opencv      # For OpenCV Python bindings
    
    # --- CLEANUP ---
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------
# --- 2. GECKODRIVER (for Selenium) ---
# Install the driver for the Firefox-based BrowserTool.
# ----------------------------------------
RUN GECKO_VER="v0.34.0" && \
    wget "https://github.com/mozilla/geckodriver/releases/download/${GECKO_VER}/geckodriver-${GECKO_VER}-linux64.tar.gz" && \
    tar -xzf geckodriver-${GECKO_VER}-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    rm geckodriver-${GECKO_VER}-linux64.tar.gz

# ----------------------------------------
# --- 3. PYTHON DEPENDENCIES ---
# Copy *only* the requirements file first to leverage
# Docker's layer caching.
# ----------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------
# --- 4. COPY APPLICATION CODE ---
# Copy the entire Archon system (all scripts, all crews)
# into the container's /app directory.
# ----------------------------------------
COPY . .

# ----------------------------------------
# --- 5. FINAL COMMAND ---
# This is the default command. It keeps the `archon-app`
# container alive and idling (as a "worker").
# This command will be *overridden* by the `api-gateway`
# service in docker-compose.yml, which runs `python api_gateway.py`.
# ----------------------------------------
CMD ["tail", "-f", "/dev/null"]
