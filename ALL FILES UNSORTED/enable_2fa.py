#!/usr/bin/env python3

import sys
import auth
import db_manager
import pyotp
import qrcode
from getpass import getpass

def main():
    """
    Generates a new TOTP secret for a user, saves it, and displays a QR code.
    """
    print("--- Archon 2FA (TOTP) Enroller ---")
    
    # 1. Authenticate the old-fashioned way (to prove it's you)
    username = input("Enter username to enroll (e.g., william): ")
    password = getpass("Enter password to verify: ")
    
    user_id, privilege = auth.authenticate_user(username, password)
    
    if not user_id:
        print("[FATAL] Authentication failed. Cannot enroll 2FA.", file=sys.stderr)
        sys.exit(1)
        
    print(f"\n[INFO] User '{username}' authenticated successfully.")

    # 2. Generate a new TOTP secret
    # This is the 16-character key (e.g., 'JBSWY3DPEHPK3PXP')
    totp_secret = pyotp.random_base32()
    
    # 3. Create the provisioning URI
    # This is the data the QR code will contain
    provisioning_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=username,
        issuer_name="Archon System"
    )

    # 4. Save the secret to the database
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
        conn.rollback()
        conn.close()
        sys.exit(1)
    finally:
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

if __name__ == "__main__":
    main()