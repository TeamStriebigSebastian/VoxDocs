"""
Authentication and RBAC for VoxDocs MCP Server

Provides token validation and role-based access control.
Users are stored in a JSON file (mock DB for development).
"""

import json
import hashlib
import secrets
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from .config import get_settings


class DenyReason(str, Enum):
    """Reasons for access denial."""
    INVALID_TOKEN = "invalid_token"
    USER_NOT_FOUND = "user_not_found"
    GROUP_NOT_ALLOWED = "group_not_allowed"
    CASE_NOT_ALLOWED = "case_not_allowed"
    ADMIN_REQUIRED = "admin_required"


@dataclass
class User:
    """User model for RBAC."""
    username: str
    token_hash: str
    allowed_groups: list[str] = field(default_factory=list)
    allowed_cases: list[str] = field(default_factory=list)
    is_admin: bool = False
    
    def can_access_group(self, group_id: str) -> bool:
        """Check if user can access a group."""
        if self.is_admin:
            return True
        return "*" in self.allowed_groups or group_id in self.allowed_groups
    
    def can_access_case(self, case_id: str) -> bool:
        """Check if user can access a case."""
        if self.is_admin:
            return True
        return "*" in self.allowed_cases or case_id in self.allowed_cases


@dataclass
class AuthResult:
    """Result of authentication attempt."""
    success: bool
    user: Optional[User] = None
    deny_reason: Optional[DenyReason] = None


class AuthManager:
    """Manages authentication and authorization."""
    
    def __init__(self, users_db_path: Optional[Path] = None):
        settings = get_settings()
        self.users_db_path = users_db_path or settings.users_db_path
        self._users: dict[str, User] = {}
        self._load_users()
    
    def _load_users(self) -> None:
        """Load users from JSON file."""
        if not self.users_db_path.exists():
            # Create default admin user if no users file exists
            self._create_default_users()
            return
        
        try:
            with open(self.users_db_path, "r") as f:
                data = json.load(f)
            
            for user_data in data.get("users", []):
                user = User(
                    username=user_data["username"],
                    token_hash=user_data["token_hash"],
                    allowed_groups=user_data.get("allowed_groups", []),
                    allowed_cases=user_data.get("allowed_cases", []),
                    is_admin=user_data.get("is_admin", False),
                )
                self._users[user.username] = user
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid users database: {e}")
    
    def _create_default_users(self) -> None:
        """Create default users file with admin user."""
        # Generate a random token for the default admin
        default_token = "admin-dev-token"
        token_hash = self._hash_token(default_token)
        
        default_data = {
            "users": [
                {
                    "username": "admin",
                    "token_hash": token_hash,
                    "allowed_groups": ["*"],
                    "allowed_cases": ["*"],
                    "is_admin": True,
                },
                {
                    "username": "agent",
                    "token_hash": self._hash_token("agent-dev-token"),
                    "allowed_groups": ["default"],
                    "allowed_cases": ["*"],
                    "is_admin": False,
                },
            ],
            "_comment": "Development users. Replace tokens in production!"
        }
        
        # Ensure directory exists
        self.users_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.users_db_path, "w") as f:
            json.dump(default_data, f, indent=2)
        
        # Load the created users
        self._load_users()
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def authenticate(self, username: str, api_token: str) -> AuthResult:
        """Authenticate a user by username and token."""
        user = self._users.get(username)
        
        if user is None:
            return AuthResult(success=False, deny_reason=DenyReason.USER_NOT_FOUND)
        
        token_hash = self._hash_token(api_token)
        if not secrets.compare_digest(token_hash, user.token_hash):
            return AuthResult(success=False, deny_reason=DenyReason.INVALID_TOKEN)
        
        return AuthResult(success=True, user=user)
    
    def authorize_case(self, user: User, case_id: str) -> Optional[DenyReason]:
        """Check if user can access a case. Returns None if allowed."""
        if not user.can_access_case(case_id):
            return DenyReason.CASE_NOT_ALLOWED
        return None
    
    def authorize_group(self, user: User, group_id: str) -> Optional[DenyReason]:
        """Check if user can access a group. Returns None if allowed."""
        if not user.can_access_group(group_id):
            return DenyReason.GROUP_NOT_ALLOWED
        return None
    
    def authorize_admin(self, user: User) -> Optional[DenyReason]:
        """Check if user is admin. Returns None if allowed."""
        if not user.is_admin:
            return DenyReason.ADMIN_REQUIRED
        return None


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


async def authenticate_and_authorize(
    username: str,
    api_token: str,
    case_id: Optional[str] = None,
    group_id: Optional[str] = None,
    require_admin: bool = False,
) -> tuple[bool, Optional[User], Optional[DenyReason]]:
    """
    Authenticate and authorize a user for a specific operation.
    
    Returns:
        Tuple of (success, user, deny_reason)
    """
    auth_manager = get_auth_manager()
    
    # Authenticate
    auth_result = auth_manager.authenticate(username, api_token)
    if not auth_result.success:
        return False, None, auth_result.deny_reason
    
    user = auth_result.user
    
    # Check admin requirement
    if require_admin:
        deny_reason = auth_manager.authorize_admin(user)
        if deny_reason:
            return False, user, deny_reason
    
    # Check case access
    if case_id:
        deny_reason = auth_manager.authorize_case(user, case_id)
        if deny_reason:
            return False, user, deny_reason
    
    # Check group access
    if group_id:
        deny_reason = auth_manager.authorize_group(user, group_id)
        if deny_reason:
            return False, user, deny_reason
    
    return True, user, None
