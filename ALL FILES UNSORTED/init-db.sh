#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
```

**2. Update `Dockerfile`:**
Add `ffmpeg` (for audio processing) and `python3-git` (for GitPython).
```dockerfile
# ... (inside your Dockerfile) ...
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
    && apt-get clean \
# ...
```

**3. Update `requirements.txt`:**
Add `GitPython` and `websocket-client` (for `ComfyUI`'s API).
```txt
# ... (all your other libraries) ...
openai-whisper
GitPython
websocket-client # <-- ADD THIS for ComfyUI
```

**4. Rebuild your stack:**
```bash
docker-compose up -d --build