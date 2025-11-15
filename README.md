Archon: The Autonomous FOSS Agent Corporation 
Archon is a self-hosted, autonomous, multi-agent "corporation" designed for maximum privacy, security, and scalability. It is a "generalist" coordinator (the ```archon_ceo```) that manages a "federation" of specialist crews, enabling it to perform complex, parallel tasks across all digital and physical domains.

This is not a tool; it is an autonomous workforce.

**1. ☭ The Archon Manifesto (Philosophy)**
* **Seize the Means of Computation:** This system is built on the FOSS principle that you must own your infrastructure. It is designed to run on self-hosted, "Zero-Trust Fortress" hardware, eliminating reliance on corporate "bourgeois" cloud providers who surveil your data.
* **A "Super Society" Architecture:** The system is designed to be a "digital state." It has an "Internal Security" policy (the ```InternalAffairsCrew```), a "State Planning Committee" (```InfrastructureCrew```), a "Signals Corps" (```NetworkingCrew```), and "Red/Blue Armies" (```PurpleTeamCrew```).
* **The Agent is a "Super-Employee":** The goal is to solve the "lack of personnel" problem by manufacturing digital personnel (agents/crews) on demand.

**2. 🏛️ Core Architecture: The "C2" Model**
   Archon operates on a "Command & Control" (C2) model for maximum Operational Security (OPSEC).
   1. ```Archon-Prime``` **(The "Brain"):** This is your primary, high-GPU, high-RAM dedicated server. It runs the Docker stack (Postgres, Ollama, API) and is kept "clean." It never performs a "dirty" action (like scanning or connecting to Tor). Its only job is to think, plan, and command.
   3. ```Archon-Ops``` **(The "Hands"):** These are one or more cheap, disposable "worker" servers (or your local Kali/Pi devices). They run the ```LocalDeviceAgent``` and ```HardwareAgent```. They do all the "dirty" work (pentesting, connecting to VPNs, hardware injection). They are controlled only via their secure Tor Hidden Service addresses.

**3. 🚀 Core Features & Tools**
This system is a "generalist" that is also a "master-of-all-specialists" by having access to over 40 unique tools, managed by 14 specialist crews.

**| Category | Capabilities || Self-Improvement |** Autonomous self-healing (```InternalAffairsCrew```), self-updating (```GitTool```), and memory garbage collection (```MemoryManagerCrew```). **|| Self-Replication |* Autonomously provision and configure new "worker" servers (```InfrastructureCrew``` with ```AnsibleTool```). **|| Self-Scaling |** Create "swarms" of agents by dynamically spawning/destroying Docker containers (```SwarmTool```). **|| Security & OPSEC |** Full "Purple Team" auditing (```OpenVAS```, ```Nmap```, ```ExploitDBTool```), OS hardening (```OSHardeningTool```), and metadata scrubbing (```mat2```). **|| Anonymity |** Dynamic, policy-driven networking. Can use Tor, VPNs (```VPNControlTool```), or layered proxies (```ProxyChainsTool```) based on the task's risk. **|| Senses & Control |** Software: CLI, GUI (Click/Screenshot). **Hardware:** (via Raspberry Pi) Keystroke/Mouse Injection. **Physical:** Webcam, Microphone. **|| AI & Reasoning | Local:** ```llama3:8b``` (generalist), ```deepseek-coder-v2``` (code/math), ```LLaVA``` (vision), ```Whisper``` (transcription). **External:** Can "phone-a-friend" to GPT-4o, Claude 3, or Grok via the ```ExternalLlmTool```. **|| Media Synthesis |** Generate images (```ComfyUI/SDXL```), videos (```SVD```), voice-cloned audio (```Coqui-TTS```), and music (```MusicGen```). **|| Business & Comms |** Send/Receive Email, create web accounts (```BrowserTool)```, send SMS/Calls (```CommsTool```), and create client-ready PDF reports. **|| PlausiDen Core |** Generate plausibly deniable data: fake locations (```MapTool```), fake browser histories, mock hardware (```VirtualDeviceTool```), and "log noise." |

**4. 📁 Repository Structure**
```
/archon_repo
├── .env.sample               # <- MASTER SECRETS (DB passwords, API keys, Master Key)
├── docker-compose.yml        # <- MASTER BLUEPRINT (Defines 14+ services)
├── Dockerfile                # <- Builds the main 'archon-app' container
├── Dockerfile.vpn            # <- Builds the 'openvpn-client' sidecar
├── requirements.txt          # <- All Python dependencies (crewai, pgvector, etc.)
├── init-db.sh                # <- Postgres script to enable 'pgvector'
|
├── /agents
│   ├── /core                 # <- Agent Core Logic
│   │   ├── archon_ceo.py     # <- The GENERALIST CEO & POLICY ENGINE (The Brain)
│   │   ├── api_gateway.py    # <- The SECURE FRONT DOOR (FastAPI, JWT/TOTP Auth)
│   │   ├── auth.py           # <- Authentication & Logging Library (Bcrypt/TOTP Logic)
│   │   ├── db_manager.py     # <- DB Schema and Credential Management
│   │   └── fapc_tools.py     # <- MASTER TOOL LIBRARY (All 40+ atomic functions)
│   │
│   └── /crews                # <- Specialist Crews (The Departments)
│       ├── ai_and_research_crew.py
│       ├── business_crew.py
│       ├── coding_crew.py
│       ├── cybersecurity_crew.py
│       ├── dfir_crew.py
│       ├── hardening_crew.py
│       ├── infrastructure_crew.py
│       ├── internal_affairs_crew.py
│       ├── mediasynthesis_crew.py
│       ├── memory_manager_crew.py
│       ├── networking_crew.py
│       ├── plausiden_crew.py
│       ├── purpleteam_crew.py
│       └── support_crew.py
|
├── /scripts                  # <- Utility Executables
│   ├── archon_daemon.py      # <- PROACTIVE COWORKER (OODA Loop)
│   ├── enable_2fa.py         # <- 2FA Setup (TOTP QR Code Generator)
│   └── knowledge_primer.py   # <- BULK TRAINER (Scans and teaches memory)
|
└── /workers                  # <- Worker Agent Code (NOT run on Prime server)
    ├── /kali
    │   └── LocalDeviceAgent.py # <- Software Worker (Webcam, Mic, CLI)
    └── /pi
        ├── hardware_agent.py   # <- Hardware Worker (Pi HID agent code)
        ├── hid-setup.sh      # <- Pi HID setup script
        └── archon-hid.service  # <- Pi systemd service
```
**5. 🚀 Installation & Setup (For ```Archon-Prime```)**
This guide is for deploying the "Brain" on a new, dedicated Debian 12 server.

**Step 1: Hardware Requirements**
* **CPU:** 12+ Cores (AMD Ryzen 9 / Threadripper recommended)
* **RAM:** 128 GB (64 GB minimum)
* **GPU:** 2x NVIDIA RTX 4090 / 3090 (24GB VRAM) - (One for LLMs, one for Media Gen)
* **Storage:** 2TB+ NVMe SSD

**Step 2: Server Preparation**
Install Git, Docker, Docker Compose, and NVIDIA Container Toolkit.

```
 # 1. Install core tools}
 sudo apt-get update
 sudo apt-get install -y git docker.io docker-compose

 # 2. Install NVIDIA Docker Toolkit (for GPU access)
 # (Follow official NVIDIA instructions for your Debian version)
```

**Step 3: Clone & Configure**
```
# 1. Clone your new repository
git clone git@your-git-host.com:william/archon.git /opt/archon
cd /opt/archon

# 2. Create your secrets file
cp .env.sample .env

# 3. Generate your master key (save this in a password manager!)
FAPC_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 32)
echo "FAPC_MASTER_KEY=$FAPC_KEY" >> .env
echo "API_SECRET_KEY=$API_KEY" >> .env

# 4. Edit the .env file with your DB/API passwords
nano .env
```

**Step 4: Build & Launch The Stack**
This will build all containers and start all services. This will take a very long time as it downloads models and builds the app.
```
docker-compose up -d --build
```

**Step 5: Initialize the System**
You must run these commands once to set up the database and your admin account.
```
# 1. Initialize the database schema (creates tables, etc.)
docker-compose exec archon-app python /app/agents/core/db_manager.py init

# 2. Create your 'admin' user
docker-compose exec archon-app python /app/agents/core/db_manager.py addadmin william

# 3. Enroll in 2FA (MFA)
# A QR code will appear in your terminal. Scan it with your authenticator app.
docker-compose exec archon-app python /app/scripts/enable_2fa.py
```

**Step 6: (Optional) Train the Agent**
To make Archon smart, "prime" its memory by pointing it at your notes/projects.
```
# 1. Copy your projects into the /app directory (or another volume)
# 2. Run the primer
docker-compose exec archon-app python /app/scripts/knowledge_primer.py "/app/your_project_folder"
```

**Step 7: (Optional) Deploy Worker Agents**
1. Copy the files from ```/workers/kali``` to your Kali machine, install dependencies, and run ```LocalDeviceAgent.py```.
2. Copy the files from ```/workers/pi``` to your Raspberry Pi and run the setup.
3. Configure the ```.onion``` addresses from your workers in the ```fapc_tools.py``` file on the ```Archon-Prime``` server and restart the stack.

**6. 🧑‍💻 Usage**
All interaction is now handled via the secure **API Gateway**.
* **To Run a Command (Tauri App):**
  1. Start the Tauri app on your desktop.
  2. Enter the ```api-gateway```'s address (or its Tor ```.onion``` address).
  3. Log in with ```[your_username]``` / ```[your_password]``` / ```[your_2FA_code]```.
  4. You now have a chat interface to command your entire corporation.

* **To Run a Command (CLI):**
  ```
  # This is how the API Gateway calls the CEO script
  # You can also run it manually for testing:
  docker-compose exec archon-app python /app/agents/core/archon_ceo.py \
    --user-id 1 \
    --command "Delegate to the PurpleTeamCrew: 'Run a full audit on localhost'"
  ```

