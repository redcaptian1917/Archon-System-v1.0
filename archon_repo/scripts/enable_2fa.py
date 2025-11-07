#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - 2FA (TOTP) ENROLLER (vFINAL)
#
# This is a one-time-use utility script to enable 2FA on an
# existing user account.
#
# It MUST be run from within the `archon-app` container, as it
# needs access to the database and Python libraries.
#
# e.g., `docker-compose exec archon-app python /app/scripts/enable_2fa.py`
# -----------------------------------------------------------------

import sys
import pyotp
import qrcode
from getpass import getpass

# --- Internal Imports ---
# These scripts must be in the same Python path
try:
    import auth
    import db_manager
except ImportError:
    print("CRITICAL: auth.py or db_manager.py not found.", file=sys.stderr)
    sys.exit(1)

def main():
    """
    Generates a new TOTP secret for a user, saves it to the DB,
    and displays a QR code for scanning.
    """
    print("--- Archon 2FA (TOTP) Enroller ---")
    
    # 1. Authenticate the old-fashioned way (to prove it's you)
    username = input("Enter username to enroll (e.g., william): ")
    password = getpass("Enter password to verify: ")
    
    # We use the existing auth library
    user_id, privilege = auth.authenticate_user(username, password)
    
    if not user_id:
        print("[FATAL] Authentication failed. Cannot enroll 2FA.", file=sys.stderr)
        sys.exit(1)
        
    print(f"\n[INFO] User '{username}' authenticated successfully.")

    # 2. Generate a new TOTP secret
    # This is the 32-character Base32 key (e.g., 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP')
    totp_secret = pyotp.random_base32()
    
    # 3. Create the provisioning URI
    # This is the data the QR code will contain
    provisioning_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=username,
        issuer_name="Archon System"
    )

    # 4. Save the secret to the database
    conn = None
    try:
        conn = db_manager.db_connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET totp_secret = %s, totp_enabled = TRUE
                WHERE user_id = %s;
                """,
                (totp_secret, user_id)
            )
            conn.commit()
        print(f"[SUCCESS] 2FA secret saved and enabled for '{username}'.")
    except Exception as e:
        print(f"[FATAL] Could not save 2FA secret to database: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

    # 5. Display the QR code in the terminal
    print("\n[ACTION REQUIRED]")
    print("Scan this QR code with your authenticator app (e.g., Authy, Google Authenticator):")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    # Print the QR code directly to the console
    qr.print_tty()
    
    print(f"\nIf you cannot scan, manually enter this key: {totp_secret}")
    print("\n--- 2FA Enrollment Complete ---")
    print("Your next login via the API or Tauri app will now require a 6-digit code.")

if __name__ == "__main__":
    main()
