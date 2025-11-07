#!/usr/bin/env python3

import psycopg2
import psycopg2.sql
import bcrypt
import os
import argparse
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from getpass import getpass

# --- Configuration ---
# !! IMPORTANT: Set these to your new DB credentials !!
DB_NAME = "fapc_db"
DB_USER = "archon_admin"
DB_PASS = "YOUR_DB_PASSWORD" # The password you set in Step 1
DB_HOST = "localhost"

# !! CRITICAL SECURITY WARNING !!
# This master key encrypts all your agent's credentials.
# DO NOT hardcode it. Load it from a secure environment variable.
# In your terminal: export FAPC_MASTER_KEY=$(openssl rand -hex 32)
FAPC_MASTER_KEY_ENV = "FAPC_MASTER_KEY"

def get_master_key() -> bytes:
    """Retrieves the 32-byte master key from the environment."""
    key_hex = os.environ.get(FAPC_MASTER_KEY_ENV)
    if not key_hex or len(key_hex) != 64:
        print(f"[FATAL] Master key not found or invalid.", file=sys.stderr)
        print(f"       Please set the {FAPC_MASTER_KEY_ENV} environment variable.", file=sys.stderr)
        print(f"       Run: export {FAPC_MASTER_KEY_ENV}=$(openssl rand -hex 32)", file=sys.stderr)
        sys.exit(1)
    return bytes.fromhex(key_hex)

def db_connect():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST
        )
        return conn
    except Exception as e:
        print(f"[FATAL] Could not connect to database: {e}", file=sys.stderr)
        sys.exit(1)

def create_tables():
    """Creates all necessary tables and pre-populates roles."""

    schema_sql = """
    CREATE TABLE IF NOT EXISTS privileges (
        privilege_id SERIAL PRIMARY KEY,
        privilege_name VARCHAR(50) UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        privilege_id INTEGER NOT NULL REFERENCES privileges(privilege_id),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS activity_logs (
        log_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id),
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        action_type VARCHAR(100) NOT NULL,
        details TEXT,
        status VARCHAR(20) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS credentials (
        credential_id SERIAL PRIMARY KEY,
        owner_user_id INTEGER NOT NULL REFERENCES users(user_id),
        service_name VARCHAR(255) NOT NULL,
        username VARCHAR(255),
        encrypted_password BYTEA NOT NULL,
        encryption_nonce BYTEA NOT NULL,
        encryption_tag BYTEA NOT NULL,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    -- 5. Tasks Table (For agent-human communication)
    CREATE TABLE IF NOT EXISTS tasks (
        task_id SERIAL PRIMARY KEY,
        created_by_user_id INTEGER REFERENCES users(user_id),
        assigned_to_user_id INTEGER REFERENCES users(user_id), -- Can be null
        status VARCHAR(50) NOT NULL DEFAULT 'new', -- e.g., 'new', 'in_progress', 'blocked'
        priority VARCHAR(50) NOT NULL DEFAULT 'Medium', -- e.g., 'Low', 'Medium', 'High', 'Critical'
        title VARCHAR(255) NOT NULL,
        details TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    -- 6. Knowledge Base Table (For Agent Memory)
    CREATE TABLE IF NOT EXISTS knowledge_base (
    fact_id SERIAL PRIMARY KEY,
    owner_user_id INTEGER NOT NULL REFERENCES users(user_id),
    fact_text TEXT NOT NULL,
    -- This 'vector(384)' must match your embedding model's dimensions
    -- nomic-embed-text (the one we use) has 384 dimensions
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Create a search index for the embeddings
    CREATE INDEX IF NOT EXISTS on knowledge_base
    USING HNSW (embedding vector_l2_ops);
    
    INSERT INTO privileges (privilege_name) VALUES ('admin'), ('user'), ('guest')
    ON CONFLICT (privilege_name) DO NOTHING;
    """

    print("[INFO] Connecting to database...")
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
        print("[SUCCESS] All tables created and roles populated.")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}", file=sys.stderr)
        conn.rollback()
    finally:
        conn.close()

def create_first_admin(username, password):
    """Creates the first admin user (e.g., you)."""

    # Hash the password with bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    print(f"[INFO] Creating admin user '{username}'...")
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            # Get the 'admin' privilege ID (should be 1)
            cur.execute("SELECT privilege_id FROM privileges WHERE privilege_name = 'admin';")
            admin_priv_id = cur.fetchone()[0]

            # Insert the new user
            cur.execute(
                "INSERT INTO users (username, password_hash, privilege_id) VALUES (%s, %s, %s)",
                (username, hashed_password.decode('utf-8'), admin_priv_id)
            )
            conn.commit()
        print(f"[SUCCESS] Admin user '{username}' created.")
        print("         You can now log in.")
    except psycopg2.errors.UniqueViolation:
        print(f"[ERROR] User '{username}' already exists.", file=sys.stderr)
        conn.rollback()
    except Exception as e:
        print(f"[ERROR] Failed to create admin user: {e}", file=sys.stderr)
        conn.rollback()
    finally:
        conn.close()

# --- Encryption Stub Functions ---
# These functions will be used by your agent's tools.

def encrypt_credential(password: str) -> dict:
    """Encrypts a password using AES-GCM with the master key."""
    key = get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12) # 12-byte nonce
    password_bytes = password.encode('utf-8')

    ciphertext = aesgcm.encrypt(nonce, password_bytes, None) # No additional data

    return {
        "nonce": nonce,
        "tag": ciphertext[-16:], # GCM tag is last 16 bytes
        "encrypted_password": ciphertext[:-16]
    }

def decrypt_credential(nonce: bytes, tag: bytes, encrypted_password: bytes) -> str:
    """Decrypts a password using AES-GCM with the master key."""
    key = get_master_key()
    aesgcm = AESGCM(key)
    ciphertext = encrypted_password + tag # Recombine for decryption

    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Decryption failed! {e}", file=sys.stderr)
        return None

# --- Main CLI ---
def main():
    parser = argparse.ArgumentParser(description="Archon Database Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'init' command
    subparsers.add_parser("init", help="Initialize the database and create all tables.")

    # 'addadmin' command
    admin_parser = subparsers.add_parser("addadmin", help="Create the first admin user.")
    admin_parser.add_argument("username", type=str, help="Username for the admin.")

    args = parser.parse_args()

    if args.command == "init":
        create_tables()
    elif args.command == "addadmin":
        password = getpass(f"Enter password for '{args.username}': ")
        password_confirm = getpass("Confirm password: ")

        if password != password_confirm:
            print("[ERROR] Passwords do not match.", file=sys.stderr)
            sys.exit(1)

        create_first_admin(args.username, password)

if __name__ == "__main__":
    main()