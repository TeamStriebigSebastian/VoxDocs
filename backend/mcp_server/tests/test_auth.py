"""
Tests for VoxDocs MCP Server Authentication
"""

import pytest
import tempfile
import json
from pathlib import Path

from mcp_server.auth import (
    AuthManager,
    User,
    DenyReason,
    authenticate_and_authorize,
)


@pytest.fixture
def temp_users_file():
    """Create a temporary users file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        users_data = {
            "users": [
                {
                    "username": "test_admin",
                    "token_hash": AuthManager._hash_token("admin-token"),
                    "allowed_groups": ["*"],
                    "allowed_cases": ["*"],
                    "is_admin": True,
                },
                {
                    "username": "test_user",
                    "token_hash": AuthManager._hash_token("user-token"),
                    "allowed_groups": ["group1", "group2"],
                    "allowed_cases": ["case1", "case2"],
                    "is_admin": False,
                },
            ]
        }
        json.dump(users_data, f)
        return Path(f.name)


def test_authenticate_valid_admin(temp_users_file):
    """Test authentication with valid admin credentials."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_admin", "admin-token")
    
    assert result.success
    assert result.user is not None
    assert result.user.username == "test_admin"
    assert result.user.is_admin


def test_authenticate_valid_user(temp_users_file):
    """Test authentication with valid user credentials."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_user", "user-token")
    
    assert result.success
    assert result.user is not None
    assert result.user.username == "test_user"
    assert not result.user.is_admin


def test_authenticate_invalid_token(temp_users_file):
    """Test authentication with invalid token."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_user", "wrong-token")
    
    assert not result.success
    assert result.deny_reason == DenyReason.INVALID_TOKEN


def test_authenticate_user_not_found(temp_users_file):
    """Test authentication with non-existent user."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("nonexistent", "any-token")
    
    assert not result.success
    assert result.deny_reason == DenyReason.USER_NOT_FOUND


def test_authorize_case_allowed(temp_users_file):
    """Test case authorization when allowed."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_user", "user-token")
    user = result.user
    
    deny_reason = auth.authorize_case(user, "case1")
    assert deny_reason is None


def test_authorize_case_denied(temp_users_file):
    """Test case authorization when denied."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_user", "user-token")
    user = result.user
    
    deny_reason = auth.authorize_case(user, "case999")
    assert deny_reason == DenyReason.CASE_NOT_ALLOWED


def test_authorize_group_allowed(temp_users_file):
    """Test group authorization when allowed."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_user", "user-token")
    user = result.user
    
    deny_reason = auth.authorize_group(user, "group1")
    assert deny_reason is None


def test_authorize_group_denied(temp_users_file):
    """Test group authorization when denied."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_user", "user-token")
    user = result.user
    
    deny_reason = auth.authorize_group(user, "group999")
    assert deny_reason == DenyReason.GROUP_NOT_ALLOWED


def test_admin_wildcard_access(temp_users_file):
    """Test that admin has wildcard access."""
    auth = AuthManager(users_db_path=temp_users_file)
    result = auth.authenticate("test_admin", "admin-token")
    user = result.user
    
    # Admin should have access to any case/group
    assert auth.authorize_case(user, "any_case") is None
    assert auth.authorize_group(user, "any_group") is None


def test_default_users_created():
    """Test that default users are created if file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        users_path = Path(tmpdir) / "users.json"
        auth = AuthManager(users_db_path=users_path)
        
        # File should be created
        assert users_path.exists()
        
        # Default admin should exist
        result = auth.authenticate("admin", "admin-dev-token")
        assert result.success
        assert result.user.is_admin
