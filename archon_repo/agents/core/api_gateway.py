#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - API GATEWAY (vFINAL)
#
# This is the "Secure Front Door" to the entire Archon system.
# It is a FastAPI server that handles:
# 1. User Authentication (Password + 2FA/TOTP)
# 2. Secure JWT Token Generation
# 3. Securely delegating commands to the `archon_ceo.py` worker.
#
# All external apps (Tauri Desktop, Mobile) MUST communicate
# with this API.
# -----------------------------------------------------------------

import os
import subprocess
import sys
import pyotp
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import StreamingResponse, PlainTextResponse
from jose import JWTError, jwt
from pydantic import BaseModel

# --- Internal Imports ---
# These scripts must be in the same Python path
try:
    import auth
    import db_manager
except ImportError:
    print("CRITICAL: auth.py or db_manager.py not found.", file=sys.stderr)
    sys.exit(1)


# --- Configuration ---
# Load from environment variables set in docker-compose.yml
API_SECRET_KEY = os.environ.get("API_SECRET_KEY")
if not API_SECRET_KEY:
    print("FATAL: API_SECRET_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

app = FastAPI(title="Archon API Gateway")
# The 'tokenUrl' tells clients where to POST to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Pydantic Models (Data Shapes) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    """The user object that will be attached to authenticated requests."""
    username: str
    privilege: str
    user_id: int

class CommandRequest(BaseModel):
    """The JSON body for a command request."""
    command: str

# --- JWT & Auth Helpers ---

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Creates a new JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    FastAPI Dependency: Decodes the JWT from the "Authorization: Bearer"
    header. Validates it and returns the User object.
    This protects all endpoints that depend on it.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        privilege: str = payload.get("priv")
        user_id: int = payload.get("uid")
        
        if username is None or privilege is None or user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    return User(username=username, privilege=privilege, user_id=user_id)

async def get_current_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    FastAPI Dependency: A *stricter* version of get_current_user.
    It ensures the user is specifically an 'admin'.
    """
    if current_user.privilege != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires 'admin' privileges"
        )
    return current_user

# --- API Endpoints ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Login endpoint. This is the "Front Door".
    It handles both password and 2FA (TOTP) logic.
    
    The client app must send the password in one of two formats:
    1. 2FA Disabled: password="<THE_USER_PASSWORD>"
    2. 2FA Enabled:  password="<THE_USER_PASSWORD>|<THE_6_DIGIT_TOTP_CODE>"
    """
    username = form_data.username
    password_full = form_data.password
    
    password = ""
    totp_code = ""

    # 1. Check if the user has 2FA enabled in the database
    conn = db_manager.db_connect()
    totp_secret = None
    totp_enabled = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT totp_secret, totp_enabled FROM users WHERE username = %s", (username,))
            result = cur.fetchone()
            if result:
                totp_secret, totp_enabled = result
    except Exception as e:
        print(f"[API ERROR] Database check failed: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        conn.close()

    # 2. Parse the password and TOTP code based on 2FA status
    if totp_enabled:
        if "|" not in password_full:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA (TOTP) code is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        parts = password_full.split("|")
        if len(parts) != 2 or not parts[1].isdigit() or len(parts[1]) != 6:
             raise HTTPException(status_code=401, detail="Invalid 2FA code format.")
        password = parts[0]
        totp_code = parts[1]
    else:
        password = password_full

    # 3. Authenticate Password
    # We use our existing 'auth.py' library
    user_id, privilege = auth.authenticate_user(username, password)
    
    if not user_id or not privilege:
        # Log the failed password attempt
        auth.log_activity(None, 'login_fail_pass', f"Failed password attempt for '{username}'.", 'failure')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 4. (If Enabled) Authenticate 2FA
    if totp_enabled:
        totp = pyotp.TOTP(totp_secret)
        if not totp.verify(totp_code):
            # Log this specific failed 2FA attempt
            auth.log_activity(user_id, 'login_fail_2fa', f"User {username} provided invalid 2FA code.", 'failure')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA (TOTP) code",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # 5. Issue Token (All checks passed)
    auth.log_activity(user_id, 'login_success', f"User {username} authenticated successfully.", 'success')
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # This is the "payload" of the token.
    # It securely stores the user's identity for all future requests.
    access_token = create_access_token(
        data={"sub": username, "priv": privilege, "uid": user_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/command/sync")
async def execute_command_sync(
    cmd: CommandRequest,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Protected endpoint to run an Archon command. (For simple clients like Tauri)
    Runs the command as a blocking process and returns the
    full output once complete.
    """
    user_id = current_user.user_id
    privilege = current_user.privilege
    command_str = cmd.command
    
    # This is the "worker" command that calls the CEO agent.
    # We securely pass the authenticated user's ID and privilege
    # to the CEO, which will then enforce the policy.
    full_cmd = [
        sys.executable,
        "/app/agents/core/archon_ceo.py",
        "--user-id", str(user_id),
        "--privilege", privilege,
        "--command", command_str
    ]
    
    print(f"[API Gateway] Executing for user {user_id}: {' '.join(full_cmd)}")
    
    try:
        # Run as a blocking process and capture all output
        # Use a long timeout for complex agent tasks (e.g., OpenVAS)
        result = subprocess.run(
            full_cmd, 
            capture_output=True, 
            text=True, 
            timeout=3600 # 1 hour
        )
        
        if result.returncode != 0:
            # The agent itself failed
            return PlainTextResponse(result.stderr, status_code=500)
        
        # Success, return the agent's full report
        return PlainTextResponse(result.stdout)
        
    except subprocess.TimeoutExpired:
        auth.log_activity(user_id, 'command_fail', "Command timed out after 1 hour.", 'failure')
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="The Archon command timed out after 1 hour."
        )
    except Exception as e:
        auth.log_activity(user_id, 'command_fail', f"API Gateway Error: {e}", 'failure')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred: {e}"
        )

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    A simple protected endpoint to check if your token is valid
    and see your own user details.
    """
    return current_user

# --- Uvicorn Runner ---
if __name__ == "__main__":
    import uvicorn
    # This makes it runnable (e.g., 'python api_gateway.py')
    # It listens on 0.0.0.0 (all interfaces) inside the container
    print("[API Gateway] Starting server on 0.0.0.0:8000...")
    uvicorn.run("api_gateway:app", host="0.0.0.0", port=8000, reload=True)
