#!/bin/bash
# Script to create the directory structure and placeholder files for the Archon System
# Execute this on your local machine to create the Git repository structure.

# Main Directory
mkdir -p fapc_server/offline_dbs
mkdir -p fapc_server/outputs/comfyui
mkdir -p fapc_server/outputs/coqui

# 1. Core Config & Docker Files (from Section 1A)
touch fapc_server/.env.sample
touch fapc_server/docker-compose.yml
touch fapc_server/Dockerfile
touch fapc_server/Dockerfile.vpn
touch fapc_server/requirements.txt
touch fapc_server/init-db.sh

# 2. Core Agent & API Files (from Section 1B)
touch fapc_server/archon_ceo.py
touch fapc_server/api_gateway.py
touch fapc_server/archon_daemon.py
touch fapc_server/auth.py
touch fapc_server/db_manager.py
touch fapc_server/enable_2fa.py
touch fapc_server/knowledge_primer.py

# 3. Master Tool Library (from Section 1D)
touch fapc_server/fapc_tools.py

# 4. Specialist Crew Files (from Section 2)
touch fapc_server/coding_crew.py
touch fapc_server/purpleteam_crew.py
touch fapc_server/dfir_crew.py
touch fapc_server/networking_crew.py
touch fapc_server/mediasynthesis_crew.py
touch fapc_server/ai_and_research_crew.py
touch fapc_server/plausiden_crew.py
touch fapc_server/support_crew.py
touch fapc_server/hardening_crew.py
touch fapc_server/memory_manager_crew.py
touch fapc_server/infrastructure_crew.py
touch fapc_server/internal_affairs_crew.py

# 5. Worker Agent Files (from Section 3)
touch fapc_server/hardware_agent.py
touch fapc_server/LocalDeviceAgent.py