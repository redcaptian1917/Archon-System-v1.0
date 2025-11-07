#!/bin/bash
# -----------------------------------------------------------------
# ARCHON SYSTEM - DATABASE INITIALIZATION SCRIPT (vFINAL)
#
# This script is executed *by the postgres container* on its
# first boot. Its ONLY job is to enable the 'pgvector'
# extension, which is required for the 'knowledge_base'
# table's 'vector' data type.
# -----------------------------------------------------------------

set -e

# This command is fed into the 'psql' utility.
# The $POSTGRES_USER and $POSTGRES_DB variables are
# automatically provided by the official postgres image
# from the values in our .env file.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  
  -- Enable the pgvector extension
  CREATE EXTENSION IF NOT EXISTS vector;
  
EOSQL
