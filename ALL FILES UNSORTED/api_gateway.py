#!/usr/bin/env python3

import os
import subprocess
import sys
import pyotp
from datetime import datetime, timedelta, timezone
from typing import Annotated, AsyncGenerator
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
import auth

# --- Configuration ---
# Load from environment variables set in docker-compose
API_SECRET_KEY = os.environ.get("API_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

app = FastAPI(title="Archon API Gateway")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Pydantic Models (Data Shapes) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    privilege: str
    user_id: int

class CommandRequest(BaseModel):
    command: str

# --- JWT & Auth Helpers ---

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """Dependency: Decodes JWT, validates user, and returns user object."""
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
    """Dependency: Ensures the user is an 'admin'."""
    if current_user.privilege != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires admin privileges"
        )
    return current_user

# --- API Endpoints ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
Login endpoint.
This now requires a 'username', 'password', AND a 'totp_code'.
The client app must be smart enough to ask for the TOTP code
if 2FA is enabled.

For this, we'll use a simple but effective trick:
The 'password' field will be a *concatenated* string.
The app will send:
password="<THE_USER_PASSWORD>|<THE_6_DIGIT_TOTP_CODE>"

If 2FA is not enabled, it will just send:
password="<THE_USER_PASSWORD>"
    """
    username = form_data.username
    password_full = form_data.password

    password = ""
    totp_code = ""

    # 1. Check if the user has 2FA enabled
    conn = auth.db_connect()
    totp_secret = None
    totp_enabled = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT totp_secret, totp_enabled FROM users WHERE username = %s", (username,))
            result = cur.fetchone()
            if result:
                totp_secret, totp_enabled = result
    finally:
        conn.close()

    # 2. Parse the password and TOTP code
    if totp_enabled:
        if "|" not in password_full:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA (TOTP) code is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        parts = password_full.split("|")
        password = parts[0]
        totp_code = parts[1]
    else:
        password = password_full

    # 3. Authenticate Password
    user_id, privilege = auth.authenticate_user(username, password)

    if not user_id or not privilege:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. (If Enabled) Authenticate 2FA
    if totp_enabled:
        totp = pyotp.TOTP(totp_secret)
        if not totp.verify(totp_code):
            # Log this failed 2FA attempt
            auth.log_activity(user_id, 'login_fail_2fa', f"User {username} provided invalid 2FA code.", 'failure')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA (TOTP) code",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 5. Issue Token (All checks passed)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username, "priv": privilege, "uid": user_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/command")
async def execute_command(
    cmd: CommandRequest,
    current_user: Annotated[User, Depends(get_current_admin)]
):
    """
    Protected endpoint to run an Archon command.
    Streams the output in real-time.
    """
    user_id = current_user.user_id
    command_str = cmd.command

    # This is the refactored command we'll run
    full_cmd = ["./archon_ceo.py", "--user-id", str(user_id), "--command", command_str]

    async def stream_output():
        """Reads stdout/stderr from the subprocess and yields it."""
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        async for line in process.stdout:
            yield line.decode('utf-8')

        async for line in process.stderr:
            yield line.decode('utf-8')

    return StreamingResponse(stream_output(), media_type="text/plain")

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Test endpoint to check your own token."""
    return current_user

## 7. 🚀 How to Use It

1.  **Make the enroller executable:**
    ```bash
    docker-compose exec archon-app chmod +x enable_2fa.py
    ```
2.  **Run the Enroller (One Time):**
    ```bash
    docker-compose exec archon-app ./enable_2fa.py


# --- Uvicorn Runner ---
if __name__ == "__main__":
    import uvicorn
    # This makes it runnable (e.g., 'python api_gateway.py')
    # It listens on 0.0.0.0 (all interfaces) inside the container
    uvicorn.run("api_gateway:app", host="0.0.0.0", port=8000, reload=True)