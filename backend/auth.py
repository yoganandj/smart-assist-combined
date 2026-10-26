"""Authentication helpers for Azure App Service Authentication (Easy Auth)."""

import base64
import json
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from config import Settings, get_settings

_ROLE_CLAIM_TYPES = {
    "role",
    "roles",
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
}
_USER_ID_CLAIM_TYPES = {
    "oid",
    "http://schemas.microsoft.com/identity/claims/objectidentifier",
    "sub",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
}
_DISPLAY_NAME_CLAIM_TYPES = {
    "name",
    "preferred_username",
    "upn",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
}


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity and app roles supplied by the Easy Auth principal."""

    user_id: str
    display_name: str
    roles: tuple[str, ...]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )


def parse_easy_auth_principal(encoded_principal: str | None) -> AuthenticatedUser:
    """Decode and validate the App Service X-MS-CLIENT-PRINCIPAL value."""
    if not encoded_principal:
        raise _unauthorized()

    try:
        principal: Any = json.loads(
            base64.b64decode(encoded_principal, validate=True)
        )
    except ValueError as exc:
        raise _unauthorized() from exc

    if not isinstance(principal, dict) or not isinstance(principal.get("claims"), list):
        raise _unauthorized()

    role_claim_type = principal.get("role_typ")
    name_claim_type = principal.get("name_typ")
    claims: list[tuple[str, str]] = []

    for claim in principal["claims"]:
        if (
            not isinstance(claim, dict)
            or not isinstance(claim.get("typ"), str)
            or not isinstance(claim.get("val"), str)
        ):
            raise _unauthorized()
        claims.append((claim["typ"].lower(), claim["val"]))

    def claim_value(
        claim_types: set[str], preferred_type: str | None = None
    ) -> str | None:
        if preferred_type:
            preferred_type = preferred_type.lower()
            for claim_type, value in claims:
                if claim_type == preferred_type and value:
                    return value
        for claim_type, value in claims:
            if claim_type in claim_types and value:
                return value
        return None

    user_id = claim_value(_USER_ID_CLAIM_TYPES)
    if not user_id:
        raise _unauthorized()

    roles = tuple(
        dict.fromkeys(
            value
            for claim_type, value in claims
            if value
            and (
                claim_type in _ROLE_CLAIM_TYPES
                or (
                    isinstance(role_claim_type, str)
                    and claim_type == role_claim_type.lower()
                )
            )
        )
    )
    display_name = claim_value(_DISPLAY_NAME_CLAIM_TYPES, name_claim_type) or user_id
    return AuthenticatedUser(user_id=user_id, display_name=display_name, roles=roles)


def get_authenticated_user(
    client_principal: str | None = Header(
        default=None,
        alias="X-MS-CLIENT-PRINCIPAL",
    ),
) -> AuthenticatedUser:
    """Require an identity injected by Azure App Service Authentication."""
    return parse_easy_auth_principal(client_principal)


def require_app_role(
    user: AuthenticatedUser = Depends(get_authenticated_user),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """Require the configured Entra app role."""
    if settings.required_app_role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the app role required to use this application.",
        )
    return user
