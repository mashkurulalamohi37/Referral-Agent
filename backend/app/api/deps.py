"""FastAPI request dependencies (auth, roles, API clients, DB sessions)."""

from __future__ import annotations

import base64
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import service as catalog_service
from app.catalog.models import ApiClient
from app.core.errors import ErrorCode, PlatformError
from app.core.resources import Resources
from app.core.security import decode_jwt_token
from app.identity import service as identity_service
from app.identity.models import User

_bearer_security = HTTPBearer(auto_error=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yields a database session from the application pool."""
    resources: Resources = request.app.state.resources
    async with resources.session_factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer_security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Validates JWT access token and returns the current active user."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise PlatformError(ErrorCode.AUTH_REQUIRED, "Missing or invalid authorization header")

    token = credentials.credentials
    payload = decode_jwt_token(token, settings=request.app.state.settings)
    sub = payload.get("sub")
    if not sub:
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Missing subject claim in token")

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError) as exc:
        raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Invalid user identifier in token") from exc

    user = await identity_service.get_user_by_id(session, user_id)
    if not user or user.status != "ACTIVE":
        raise PlatformError(ErrorCode.PERMISSION_DENIED, "User account is suspended or not found")

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Dependency factory checking if the authenticated user has at least one required role."""

    def _role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        user_roles = {r.role for r in user.roles}
        if "SUPER_ADMIN" in user_roles:
            return user
        if not any(role in user_roles for role in allowed_roles):
            raise PlatformError(
                ErrorCode.PERMISSION_DENIED, f"Requires one of roles: {', '.join(allowed_roles)}"
            )
        return user

    return _role_checker


async def get_authenticated_api_client(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    x_api_secret: Annotated[str | None, Header(alias="X-API-Secret")] = None,
) -> ApiClient:
    """Authenticates API client via X-API-Key/X-API-Secret or Basic auth."""
    key_id: str | None = None
    secret: str | None = None

    if x_api_key and x_api_secret:
        key_id = x_api_key
        secret = x_api_secret
    elif authorization and authorization.lower().startswith("bearer "):
        token_str = authorization.split(" ", 1)[1].strip()
        if "." in token_str and not token_str.startswith("eyJ"):
            parts = token_str.split(".", 1)
            key_id, secret = parts[0], parts[1]
    elif authorization and authorization.lower().startswith("basic "):
        encoded = authorization.split(" ", 1)[1]
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
            parts = decoded.split(":", 1)
            if len(parts) == 2:
                key_id, secret = parts[0], parts[1]
        except Exception as exc:
            raise PlatformError(ErrorCode.AUTH_INVALID_CREDENTIALS, "Malformed Basic auth credentials") from exc

    if not key_id or not secret:
        raise PlatformError(
            ErrorCode.AUTH_REQUIRED,
            "API client credentials required (via Authorization Bearer <key_id>.<secret>, X-API-Key / X-API-Secret or Basic auth)",
        )

    return await catalog_service.authenticate_api_client(session, key_id=key_id, secret=secret)


# Aliases
get_current_active_user = get_current_user
authenticate_api_client_dep = get_authenticated_api_client


def require_api_scopes(*required_scopes: str) -> Callable[[ApiClient], ApiClient]:
    """Dependency factory checking API client scopes."""

    def _scope_checker(client: Annotated[ApiClient, Depends(get_authenticated_api_client)]) -> ApiClient:
        client_scopes = set(client.scopes)
        if "*" in client_scopes:
            return client
        missing = [s for s in required_scopes if s not in client_scopes]
        if missing:
            raise PlatformError(
                ErrorCode.SCOPE_MISSING, f"API client missing required scopes: {', '.join(missing)}"
            )
        return client

    return _scope_checker

