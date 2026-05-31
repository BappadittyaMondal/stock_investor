"""
HFOS v5.0 — Unit Tests: Auth Service
"""
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_jwt_secret():
    os.environ["HFOS_JWT_SECRET"] = "a" * 32  # 32 char test secret
    yield


class TestPasswordService:
    @pytest.fixture
    def svc(self):
        from services.auth_service import PasswordService
        return PasswordService()

    def test_hash_and_verify(self, svc):
        pwd = "StrongPass1!"
        hashed = svc.hash_password(pwd)
        assert svc.verify_password(pwd, hashed)

    def test_wrong_password_fails(self, svc):
        hashed = svc.hash_password("StrongPass1!")
        assert not svc.verify_password("WrongPass1!", hashed)

    def test_weak_password_raises_short(self, svc):
        with pytest.raises(ValueError, match="12 characters"):
            svc.hash_password("Short1!")

    def test_weak_password_no_upper(self, svc):
        with pytest.raises(ValueError, match="uppercase"):
            svc.hash_password("alllowercase1!")

    def test_weak_password_no_digit(self, svc):
        with pytest.raises(ValueError, match="digit"):
            svc.hash_password("AllUpperNoDigit!")

    def test_different_hashes_for_same_password(self, svc):
        pwd = "StrongPass1!"
        h1 = svc.hash_password(pwd)
        h2 = svc.hash_password(pwd)
        assert h1 != h2  # different salts


class TestJWTManager:
    @pytest.fixture
    def jwt(self):
        from services.auth_service import JWTManager
        with patch("services.auth_service.execute_one", return_value=None):
            return JWTManager()

    def test_create_and_verify(self, jwt):
        with patch("services.auth_service.execute_one", return_value=None):
            token = jwt.create_token(42, "ADMIN")
            payload = jwt.verify_token(token)
            assert payload["user_id"] == 42
            assert payload["role"] == "ADMIN"

    def test_invalid_token_raises(self, jwt):
        with pytest.raises(ValueError, match="Invalid"):
            jwt.verify_token("not.a.token")

    def test_wrong_secret_raises(self, jwt):
        import jwt as pyjwt
        # Token signed with different secret
        token = pyjwt.encode({"user_id": 1, "role": "VIEWER"}, "wrong_secret", "HS256")
        with pytest.raises(ValueError):
            jwt.verify_token(token)


class TestRBAC:
    def test_admin_has_all_permissions(self):
        from services.auth_service import AuthService
        with patch("services.auth_service.JWTManager.__init__", return_value=None):
            svc = AuthService.__new__(AuthService)
            svc.jwt = MagicMock()
            svc.pwd = MagicMock()
            assert svc.has_permission("ADMIN", "portfolio", "delete")
            assert svc.has_permission("ADMIN", "users", "write")
            assert svc.has_permission("ADMIN", "calibration", "approve")

    def test_viewer_read_only(self):
        from services.auth_service import AuthService
        with patch("services.auth_service.JWTManager.__init__", return_value=None):
            svc = AuthService.__new__(AuthService)
            svc.jwt = MagicMock()
            svc.pwd = MagicMock()
            assert svc.has_permission("VIEWER", "stocks", "read")
            assert not svc.has_permission("VIEWER", "stocks", "write")
            assert not svc.has_permission("VIEWER", "users", "read")

    def test_researcher_cannot_delete(self):
        from services.auth_service import AuthService
        with patch("services.auth_service.JWTManager.__init__", return_value=None):
            svc = AuthService.__new__(AuthService)
            svc.jwt = MagicMock()
            svc.pwd = MagicMock()
            assert not svc.has_permission("RESEARCHER", "stocks", "delete")
            assert svc.has_permission("RESEARCHER", "stocks", "write")
