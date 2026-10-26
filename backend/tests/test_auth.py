import base64
import json
import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

from auth import parse_easy_auth_principal, require_app_role
from config import Settings, get_settings
from main import app


def encode_principal(claims: list[dict[str, str]]) -> str:
    value = json.dumps(
        {
            "auth_typ": "aad",
            "claims": claims,
            "name_typ": "name",
            "role_typ": "roles",
        }
    ).encode()
    return base64.b64encode(value).decode()


class EasyAuthPrincipalTests(unittest.TestCase):
    def test_parses_user_identity_and_app_roles(self) -> None:
        principal = encode_principal(
            [
                {"typ": "oid", "val": "user-object-id"},
                {"typ": "name", "val": "Test User"},
                {"typ": "roles", "val": "americanusers"},
                {"typ": "roles", "val": "reader"},
            ]
        )

        user = parse_easy_auth_principal(principal)

        self.assertEqual(user.user_id, "user-object-id")
        self.assertEqual(user.display_name, "Test User")
        self.assertEqual(user.roles, ("americanusers", "reader"))

    def test_reads_role_claims_using_easy_auth_role_type(self) -> None:
        principal = encode_principal(
            [
                {"typ": "oid", "val": "user-object-id"},
                {
                    "typ": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
                    "val": "americanusers",
                },
            ]
        )

        user = parse_easy_auth_principal(principal)

        self.assertEqual(user.roles, ("americanusers",))

    def test_missing_principal_is_unauthorized(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            parse_easy_auth_principal(None)

        self.assertEqual(raised.exception.status_code, 401)

    def test_malformed_principal_is_unauthorized(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            parse_easy_auth_principal("not-base64-json")

        self.assertEqual(raised.exception.status_code, 401)

    def test_authenticated_user_without_required_role_is_forbidden(self) -> None:
        user = parse_easy_auth_principal(
            encode_principal(
                [
                    {"typ": "oid", "val": "user-object-id"},
                    {"typ": "roles", "val": "reader"},
                ]
            )
        )

        with self.assertRaises(HTTPException) as raised:
            require_app_role(user, SimpleNamespace(required_app_role="americanusers"))

        self.assertEqual(raised.exception.status_code, 403)


class EasyAuthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_overrides = app.dependency_overrides.copy()
        settings = Settings()
        settings.required_app_role = "americanusers"
        app.dependency_overrides[get_settings] = lambda: settings
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.original_overrides)
        self.client.close()

    def test_current_user_requires_principal(self) -> None:
        response = self.client.get("/auth/me")

        self.assertEqual(response.status_code, 401)

    def test_reader_role_cannot_access_app(self) -> None:
        response = self.client.get(
            "/auth/me",
            headers={
                "X-MS-CLIENT-PRINCIPAL": encode_principal(
                    [
                        {"typ": "oid", "val": "user-object-id"},
                        {"typ": "roles", "val": "reader"},
                    ]
                )
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_americanusers_role_can_access_current_user(self) -> None:
        response = self.client.get(
            "/auth/me",
            headers={
                "X-MS-CLIENT-PRINCIPAL": encode_principal(
                    [
                        {"typ": "oid", "val": "user-object-id"},
                        {"typ": "name", "val": "Test User"},
                        {"typ": "roles", "val": "americanusers"},
                    ]
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "userId": "user-object-id",
                "displayName": "Test User",
                "roles": ["americanusers"],
            },
        )

    def test_chat_routes_reject_reader_role(self) -> None:
        headers = {
            "X-MS-CLIENT-PRINCIPAL": encode_principal(
                [
                    {"typ": "oid", "val": "user-object-id"},
                    {"typ": "roles", "val": "reader"},
                ]
            )
        }

        chat_response = self.client.post(
            "/chat",
            json={"message": "hello"},
            headers=headers,
        )
        stream_response = self.client.post(
            "/chat/stream",
            json={"message": "hello"},
            headers=headers,
        )

        self.assertEqual(chat_response.status_code, 403)
        self.assertEqual(stream_response.status_code, 403)

    def test_frontend_fallback_does_not_serve_files_outside_static_root(self) -> None:
        response = self.client.get("/..%2F..%2Fbackend%2Fconfig.py")

        self.assertNotIn("Configuration loader for the TPF Assistant backend.", response.text)
