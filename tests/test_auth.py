#!/usr/bin/env python3
# -----------------------------------------------------------------
# ARCHON SYSTEM - AUTHENTICATION TEST (vFINAL)
#
# This is the "Cheka" (Internal Security) test suite.
# It runs "interrogations" (tests) on the core security
# logic of the Archon system.
#
# To run: `docker-compose exec archon-app pytest /app/tests/`
# -----------------------------------------------------------------

import pytest
import bcrypt
import sys
import os
from unittest.mock import patch, MagicMock

# --- Path Setup ---
# This ensures that 'pytest' (the "Cheka") can find
# your "ministries" (the /agents/core code).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Internal Imports ---
# We are now testing the *real*, *final* files.
from agents.core import auth, db_manager, fapc_tools

# ----------------------------------------
# --- TEST SUITE 1: UNIT TESTS ---
# (The "Ideological Purity" Test)
# ----------------------------------------

def test_bcrypt_password_verification():
    """
    UNIT TEST
    Tests the core "Spock" logic of your authentication.
    Does the hash (from the DB) match the password (from the user)?
    This test is fast, simple, and has ZERO dependencies.
    """
    print("\n[TEST] Running 'Cheka' Unit Test on 'bcrypt' logic...")
    
    # 1. The "State" (what's in your DB)
    password = "MySuperSecretPassword123!"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # 2. The "Test" (what the user provides)
    correct_password = "MySuperSecretPassword123!"
    wrong_password = "MySuperSecretPassword456!"
    
    # 3. The "Verdict" (The Interrogation)
    assert bcrypt.checkpw(correct_password.encode('utf-8'), hashed_password) == True, \
        "CATASTROPHIC FAILURE: The CORRECT password failed to verify!"
    assert bcrypt.checkpw(wrong_password.encode('utf-8'), hashed_password) == False, \
        "CATASTROPHIC FAILURE: The WRONG password was accepted!"
    
    print("[SUCCESS] 'bcrypt' logic is sound. The 'State's' core math is secure.")

# ----------------------------------------
# --- TEST SUITE 2: INTEGRATION TESTS ---
# (The "State Security" Test)
# ----------------------------------------

# We use 'pytest fixtures' to set up our mocks
@pytest.fixture
def mock_db():
    """Mocks the database connection."""
    with patch('db_manager.db_connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        yield mock_cursor

@pytest.fixture
def mock_auth_log():
    """Mocks the activity logger."""
    with patch('auth.log_activity') as mock_log:
        yield mock_log

@pytest.fixture
def mock_auth_get_username():
    """Mocks the function that checks the admin's username."""
    # This is the *real* function our tool uses, not the obsolete 'get_privilege_by_id'
    with patch('auth.get_username_from_id') as mock_get_username:
        yield mock_get_username

def test_auth_management_tool_admin_access(mock_db, mock_auth_log, mock_auth_get_username):
    """
    INTEGRATION TEST (The "Loyalty Test")
    Tests: Does the 'auth_management_tool' correctly give access to
           the 'admin' ('william')?
    """
    print("\n[TEST] Running 'Cheka' Integration Test on 'admin' access...")
    
    # 1. The "Setup" (The "Sting Operation")
    # We mock the function that checks the user.
    # We tell it that the user (user_id=1) *is* 'william'.
    mock_auth_get_username.return_value = 'william'
    
    # 2. The "Test" (The "Command")
    # We (as user 1) try to lock the 'testuser' account.
    result = fapc_tools.auth_management_tool(
        action='lock', 
        username='testuser', 
        user_id=1 # 'william's ID
    )
    
    # 3. The "Verdict" (The "Interrogation")
    assert "Success" in result, \
        "FAILURE: The 'admin' user ('william') was *blocked* from using the admin tool!"
    assert mock_db.execute.called, \
        "FAILURE: The tool reported success but never actually ran the DB command."
    
    print("[SUCCESS] 'admin' (william) was correctly granted access.")

def test_auth_management_tool_non_admin_access(mock_db, mock_auth_log, mock_auth_get_username):
    """
    INTEGRATION TEST (The "Counter-Revolutionary" Test)
    Tests: Does the 'auth_management_tool' *block* a non-admin 'user'?
    """
    print("\n[TEST] Running 'Cheka' Integration Test on 'user' (non-admin) denial...")
    
    # 1. The "Setup" (The "Sting Operation")
    # We mock the function that checks the user.
    # We tell it that the user (user_id=2) is a *non-admin* (e.g., 'support_team').
    mock_auth_get_username.return_value = 'support_team'
    
    # 2. The "Test" (The "Attack")
    # The 'support_team' (user 2) tries to lock the 'testuser' account.
    result = fapc_tools.auth_management_tool(
        action='lock', 
        username='testuser', 
        user_id=2 # 'support_team's ID
    )
    
    # 3. The "Verdict" (The "Interrogation")
    assert "Error: This tool can only be run by the primary admin" in result, \
        "CATASTROPHIC FAILURE: A 'user' was *not* blocked from the admin tool!"
    assert not mock_db.execute.called, \
        "CATASTROPHIC FAILURE: The tool *ran the DB command* even though the user was non-admin!"
    
    print("[SUCCESS] 'user' (support_team) was correctly *denied* access. The 'Policy' is strong.")
