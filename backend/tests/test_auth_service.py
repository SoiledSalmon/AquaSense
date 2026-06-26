import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.auth_service import AuthService
from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ProfileUpdateError,
)

@pytest.fixture
def mock_supabase():
    return MagicMock()

@pytest.fixture
def mock_supabase_admin():
    return MagicMock()

@pytest.fixture
def auth_service(mock_supabase, mock_supabase_admin, monkeypatch):
    mock_repo = MagicMock()
    monkeypatch.setattr("app.services.auth_service.UserRepository", lambda client: mock_repo)
    service = AuthService(mock_supabase, mock_supabase_admin)
    service._users = mock_repo
    return service, mock_repo

@pytest.mark.asyncio
async def test_signup_success(auth_service, mock_supabase_admin):
    service, mock_repo = auth_service

    user_mock = MagicMock()
    user_mock.id = "mock-uuid-123"
    session_mock = MagicMock()
    session_mock.access_token = "access-token-abc"
    session_mock.refresh_token = "refresh-token-xyz"

    auth_response_mock = MagicMock()
    auth_response_mock.user = user_mock
    auth_response_mock.session = session_mock

    mock_supabase_admin.auth.sign_up.return_value = auth_response_mock
    mock_repo.create_user = AsyncMock(return_value={"id": "mock-uuid-123", "email": "test@example.com", "full_name": "Test User", "role": "user"})

    result = await service.signup(
        email="test@example.com",
        password="securepassword123",
        full_name="Test User",
    )

    assert result["user"]["id"] == "mock-uuid-123"
    assert result["access_token"] == "access-token-abc"
    assert result["refresh_token"] == "refresh-token-xyz"
    mock_supabase_admin.auth.sign_up.assert_called_once()
    mock_supabase_admin.auth.admin.update_user_by_id.assert_called_once_with(
        "mock-uuid-123", {"app_metadata": {"role": "user"}}
    )
    mock_repo.create_user.assert_called_once()

@pytest.mark.asyncio
async def test_login_success(auth_service, mock_supabase_admin):
    service, mock_repo = auth_service

    user_mock = MagicMock()
    user_mock.id = "mock-uuid-123"
    session_mock = MagicMock()
    session_mock.access_token = "access-token-abc"
    session_mock.refresh_token = "refresh-token-xyz"

    auth_response_mock = MagicMock()
    auth_response_mock.user = user_mock
    auth_response_mock.session = session_mock

    mock_supabase_admin.auth.sign_in_with_password.return_value = auth_response_mock

    profile_data = {
        "id": "mock-uuid-123",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "user",
    }
    mock_repo.get_user_by_id = AsyncMock(return_value=profile_data)

    result = await service.login(email="test@example.com", password="securepassword123")

    assert result["user"]["full_name"] == "Test User"
    assert result["access_token"] == "access-token-abc"
    assert result["refresh_token"] == "refresh-token-xyz"
    mock_supabase_admin.auth.sign_in_with_password.assert_called_once()
    mock_repo.get_user_by_id.assert_called_once_with("mock-uuid-123")

@pytest.mark.asyncio
async def test_logout_success(auth_service, mock_supabase_admin):
    service, mock_repo = auth_service

    await service.logout(user_id="mock-uuid-123")

    mock_supabase_admin.auth.admin.sign_out.assert_called_once_with("mock-uuid-123", scope="global")

@pytest.mark.asyncio
async def test_get_profile_not_found(auth_service):
    service, mock_repo = auth_service
    mock_repo.get_user_by_id = AsyncMock(return_value=None)

    with pytest.raises(UserNotFoundError):
        await service.get_profile("nonexistent-uuid")
