#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - DATABASE & CRYPTO ENGINE (vFINAL)
#
# This is a foundational library AND a CLI tool.
# - As a Library: It is imported by `auth.py` and `fapc_tools.py`
#   to use its helper functions (db_connect, encrypt/decrypt).
# - As a CLI Tool: It is run by the 'admin' to initialize
#   the database (`init`) and create new users (`adduser`).
# -----------------------------------------------------------------

import os
import sys
import argparse
import bcrypt
import psycopg2
from getpass import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- Configuration ---
# Load from environment variables set in docker-compose.yml
try:
    DB_NAME = os.environ["DB_NAME"]
    DB_USER = os.environ["DB_USER"]
    DB_PASS = os.environ["POSTGRES_PASSWORD"]
    DB_HOST = "postgres" # The Docker service name
    FAPC_MASTER_KEY_ENV = "FAPC_MASTER_KEY"
except KeyError as e:
    print(f"FATAL: Environment variable {e} not set.", file=sys.stderr)
    sys.exit(1)

# ---
# 1. CORE DATABASE CONNECTION
# ---

def db_connect():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port="5432"
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"[FATAL] Could not connect to database at host '{DB_HOST}'. Is it running?", file=sys.stderr)
        print(f"       Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)

# ---
# 2. ENCRYPTION ENGINE (THE "STATE VAULT")
# ---

def get_master_key() -> bytes:
    """Retrieves the 32-byte master key from the environment."""
    key_hex = os.environ.get(FAPC_MASTER_KEY_ENV)
    if not key_hex or len(key_hex) != 64:
        print(f"[FATAL] Master key not found or invalid.", file=sys.stderr)
        print(f"       Please set the {FAPC_MASTER_KEY_ENV} env variable to a 64-char hex string.", file=sys.stderr)
        print(f"       Run: export {FAPC_MASTER_KEY_ENV}=$(openssl rand -hex 32)", file=sys.stderr)
        sys.exit(1)
    return bytes.fromhex(key_hex)

def encrypt_credential(password: str) -> dict:
    """
    Encrypts a password using AES-GCM with the master key.
    Returns a dict with the parts needed for storage.
    """
    key = get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12) # 12-byte (96-bit) nonce, as recommended
    password_bytes = password.encode('utf-8')
    
    # Encrypt, returns ciphertext + 16-byte auth tag
    ciphertext_with_tag = aesgcm.encrypt(nonce, password_bytes, None) # No associated data
    
    return {
        "nonce": nonce,
        "tag": ciphertext_with_tag[-16:], # Get the 16-byte tag
        "encrypted_password": ciphertext_with_tag[:-16] # Get the ciphertext
    }

def decrypt_credential(nonce: bytes, tag: bytes, encrypted_password: bytes) -> str | None:
    """
    Decrypts a password using AES-GCM with the master key.
    Returns the plaintext string, or None if decryption fails.
    """
    key = get_master_key()
    aesgcm = AESGCM(key)
    ciphertext_with_tag = encrypted_password + tag # Recombine for decryption
    
    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        # This will fail if the key is wrong OR the data was tampered with
        print(f"[ERROR] DECRYPTION FAILED! {e}", file=sys.stderr)
        return None

# ---
# 3. DATABASE SCHEMA (THE "CHARTER")
# ---

def create_tables():
    """Creates all 6 necessary tables and pre-populates roles."""
    
    # This is the full schema definition
    schema_sql = """
    -- 1. Privileges Table (The Ranks)
    CREATE TABLE IF NOT EXISTS privileges (
        privilege_id SERIAL PRIMARY KEY,
        privilege_name VARCHAR(50) UNIQUE NOT NULL  -- 'admin', 'user', 'guest'
    );

    -- 2. Users Table (The Party Members)
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL, -- For bcrypt hashes
        privilege_id INTEGER NOT NULL REFERENCES privileges(privilege_id),
        totp_secret VARCHAR(32), -- 16-char Base32 string
        totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 3. Activity Logs Table (The Permanent Record)
    CREATE TABLE IF NOT EXISTS activity_logs (
        log_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL, -- Keep logs even if user is deleted
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        action_type VARCHAR(100) NOT NULL, -- e.g., 'login', 'cli_command', 'delegate_fail'
        details TEXT,                      -- e.g., The command, the error
        status VARCHAR(20) NOT NULL        -- e.g., 'success', 'failure', 'pending'
    );

    -- 4. Credentials Table (The State Vault)
    CREATE TABLE IF NOT EXISTS credentials (
        credential_id SERIAL PRIMARY KEY,
        owner_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        service_name VARCHAR(255) NOT NULL, -- e.g., 'twilio_api', 'admin_phone'
        username VARCHAR(255),
        encrypted_password BYTEA NOT NULL,  -- The encrypted secret
        encryption_nonce BYTEA NOT NULL,    -- 12-byte nonce
        encryption_tag BYTEA NOT NULL,      -- 16-byte auth tag
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(owner_user_id, service_name) -- A user can't have two 'gmail' entries
    );

    -- 5. Tasks Table (The Work Orders / CAPTCHA queue)
    CREATE TABLE IF NOT EXISTS tasks (
        task_id SERIAL PRIMARY KEY,
        created_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
        assigned_to_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'new', -- 'new', 'in_progress', 'blocked', 'completed'
        priority VARCHAR(50) NOT NULL DEFAULT 'Medium', -- 'Low', 'Medium', 'High', 'Critical'
        title VARCHAR(255) NOT NULL,
        details TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 6. Knowledge Base (The Collective Consciousness / AI Memory)
    CREATE TABLE IF NOT EXISTS knowledge_base (
        fact_id SERIAL PRIMARY KEY,
        owner_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        fact_text TEXT NOT NULL,
        -- This vector(384) *must* match your embedding model
        -- nomic-embed-text (the one we use) has 384 dimensions
        embedding vector(384),
        last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        importance_score SMALLINT NOT NULL DEFAULT 50 CHECK (importance_score >= 1 AND importance_score <= 100),
        do_not_delete BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create the vector index for fast similarity search
    CREATE INDEX IF NOT EXISTS on knowledge_base
    USING HNSW (embedding vector_l2_ops);

    -- Pre-populate the privilege roles
    INSERT INTO privileges (privilege_name) VALUES ('admin'), ('user'), ('guest')
    ON CONFLICT (privilege_name) DO NOTHING;
    """
    
    print("[INFO] Connecting to database to initialize schema...")
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
        print("[SUCCESS] All 6 tables and 3 privilege roles are present and correct.")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}", file=sys.stderr)
        conn.rollback()
    finally:
        conn.close()

def add_user(username, password, privilege_name):
    """Creates a new user in the database."""
    
    # 1. Hash the password with bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    print(f"[INFO] Creating user '{username}' with privilege '{privilege_name}'...")
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            # 2. Get the privilege_id from the name
            cur.execute("SELECT privilege_id FROM privileges WHERE privilege_name = %s;", (privilege_name,))
            result = cur.fetchone()
            if not result:
                print(f"[ERROR] Privilege level '{privilege_name}' does not exist.", file=sys.stderr)
                return
            admin_priv_id = result[0]
            
            # 3. Insert the new user
            cur.execute(
                "INSERT INTO users (username, password_hash, privilege_id) VALUES (%s, %s, %s)",
                (username, hashed_password.decode('utf-8'), admin_priv_id)
            )
            conn.commit()
        print(f"[SUCCESS] User '{username}' created.")
    except psycopg2.errors.UniqueViolation:
        print(f"[ERROR] User '{username}' already exists.", file=sys.stderr)
        conn.rollback()
    except Exception as e:
        print(f"[ERROR] Failed to create user: {e}", file=sys.stderr)
        conn.rollback()
    finally:
        conn.close()

# ---
# 4. COMMAND-LINE INTERFACE
# ---
def main():
    parser = argparse.ArgumentParser(
        description="Archon Database Manager (db_manager.py)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # --- 'init' command ---
    subparsers.add_parser(
        "init", 
        help="Initialize the database: create all 6 tables and default roles."
    )
    
    # --- 'adduser' command ---
    admin_parser = subparsers.add_parser(
        "adduser", 
        help="Create a new user (admin, user, or guest)."
    )
    admin_parser.add_argument(
        "username", 
        type=str, 
        help="Username for the new user."
    )
    admin_parser.add_argument(
        "--privilege", 
        type=str, 
        default="admin",
        choices=['admin', 'user', 'guest'],
        help="Privilege level for the new user (default: admin)."
    )
    
    args = parser.parse_args()
    
    if args.command == "init":
        create_tables()
    
    elif args.command == "adduser":
        password = getpass(f"Enter password for '{args.username}': ")
        password_confirm = getpass("Confirm password: ")
        
        if password != password_confirm:
            print("[ERROR] Passwords do not match.", file=sys.stderr)
            sys.exit(1)
        if not password:
            print("[ERROR] Password cannot be empty.", file=sys.stderr)
            sys.exit(1)
            
        add_user(args.username, password, args.privilege)

if __name__ == "__main__":
    main()
