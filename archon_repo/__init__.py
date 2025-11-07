# -----------------------------------------------------------------
# ARCHON SYSTEM - ROOT PACKAGE (vFINAL)
#
# This file is intentionally present.
#
# Its presence defines the 'archon_repo' (or '/app') directory
# as the single, explicit, "Regular Package" root for the
# entire Archon system.
#
# This is the "Master Border Guard" of the Archon namespace.
# It is the primary defense against PEP 420 "Namespace
# Hijacking" attacks and ensures all 'import' statements
# (e.g., 'import agents.core.auth') are resolved from
# *this* directory and *only* this directory.
#
# - Archon Internal Security Mandate (Zero-Trust)
# -----------------------------------------------------------------
