from typing import Optional

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CredentialsException,
    InactiveUserException,
    PermissionDeniedException,
)
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT bearer token, load user from DB, and enforce active status and tenant match."""
    if auth is None or not auth.credentials:
        raise CredentialsException("Authentication credentials were not provided")

    token = auth.credentials

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        token_tenant_id: int = payload.get("tenant_id")
        token_role: str = payload.get("role")

        if user_id_str is None or token_tenant_id is None:
            raise CredentialsException("Invalid token payload")

        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError as err:
        raise CredentialsException("Token has expired") from err
    except (jwt.PyJWTError, ValueError) as err:
        raise CredentialsException("Could not validate credentials: malformed or tampered token") from err

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise CredentialsException("User not found")

    if not user.is_active:
        raise InactiveUserException("User account is inactive")

    # Verify that the user's current tenant matches the token tenant
    if user.tenant_id != token_tenant_id:
        raise CredentialsException("Tenant context mismatch")

    # Security check: verify that the user's role in DB matches the token role
    # This prevents privilege escalation via forged/manipulated role claims
    if user.role != token_role:
        raise PermissionDeniedException("Token role claim does not match user account")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure current user is active."""
    if not current_user.is_active:
        raise InactiveUserException("User account is inactive")
    return current_user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role for protected administrative endpoints."""
    if current_user.role != UserRole.ADMIN.value:
        raise PermissionDeniedException("Administrator privileges required for this action")
    return current_user
