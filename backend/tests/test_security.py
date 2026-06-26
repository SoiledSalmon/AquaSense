import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from app.core.config import Settings
from app.core.security import verify_jwt, create_cookie_params
from app.core.exceptions import InvalidCredentialsError

@pytest.fixture
def mock_settings():
    return Settings(
        SUPABASE_URL="https://mock.supabase.co",
        SUPABASE_KEY="mock-anon-key",
        SUPABASE_SERVICE_ROLE_KEY="mock-service-role-key",
        SUPABASE_JWT_SECRET="testsecretsecretsecretsecretsecretsecretsecret",
        FRONTEND_URL="http://localhost:3000",
        ENVIRONMENT="development",
        THINGSPEAK_MQTT_USER="mock-user",
        THINGSPEAK_MQTT_API_KEY="mock-key",
    )

def test_verify_jwt_valid(mock_settings):
    payload = {"sub": "user-uuid-123", "email": "test@example.com"}
    token = jwt.encode(payload, mock_settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    decoded = verify_jwt(token, mock_settings)
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["email"] == "test@example.com"

def test_verify_jwt_expired(mock_settings):
    payload = {
        "sub": "user-uuid-123",
        "email": "test@example.com",
        "exp": int((datetime.now(tz=timezone.utc) - timedelta(seconds=10)).timestamp())
    }
    token = jwt.encode(payload, mock_settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    with pytest.raises(InvalidCredentialsError):
        verify_jwt(token, mock_settings)

def test_verify_jwt_invalid_signature(mock_settings):
    payload = {"sub": "user-uuid-123"}
    token = jwt.encode(payload, "wrong_secret_key_wrong_secret_key_wrong_secret", algorithm="HS256")
    with pytest.raises(InvalidCredentialsError):
        verify_jwt(token, mock_settings)

def test_create_cookie_params_development(mock_settings):
    params = create_cookie_params(mock_settings)
    assert params["httponly"] is True
    assert params["secure"] is False
    assert params["samesite"] == "lax"
    assert params["path"] == "/"

def test_create_cookie_params_production(mock_settings):
    mock_settings.ENVIRONMENT = "production"
    params = create_cookie_params(mock_settings)
    assert params["secure"] is True
