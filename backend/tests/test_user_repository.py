import pytest
from unittest.mock import MagicMock, AsyncMock
from app.repositories.user_repository import UserRepository
from app.repositories.admin_repository import AdminRepository
from app.core.exceptions import ProfileCreationError

@pytest.fixture
def mock_supabase():
    return MagicMock()

@pytest.mark.asyncio
async def test_user_repository_get_user_by_id_exists(mock_supabase):
    repo = UserRepository(mock_supabase)
    
    mock_execute = MagicMock()
    # maybe_single() returns a single dict under .data
    mock_execute.execute = AsyncMock(return_value=MagicMock(data={"id": "u1", "email": "test@test.com"}))
    
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.maybe_single = MagicMock(return_value=mock_execute)
    
    mock_supabase.table.return_value = mock_table
    
    user = await repo.get_user_by_id("u1")
    assert user is not None
    assert user["id"] == "u1"

@pytest.mark.asyncio
async def test_user_repository_get_user_by_id_not_found(mock_supabase):
    repo = UserRepository(mock_supabase)
    
    # postgrest-py returns None when maybe_single() has 0 matches
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.maybe_single = MagicMock(return_value=mock_table)
    # execute() returns None
    mock_table.execute = AsyncMock(return_value=None)
    
    mock_supabase.table.return_value = mock_table
    
    user = await repo.get_user_by_id("nonexistent")
    assert user is None

@pytest.mark.asyncio
async def test_admin_repository_get_user_by_id_exists(mock_supabase):
    repo = AdminRepository(mock_supabase)
    
    mock_execute = MagicMock()
    # admin_repository uses async execute()
    mock_execute.execute = AsyncMock(return_value=MagicMock(data={"id": "u1", "email": "test@test.com"}))
    
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.maybe_single = MagicMock(return_value=mock_execute)
    
    mock_supabase.table.return_value = mock_table
    
    user = await repo.get_user_by_id("u1")
    assert user is not None
    assert user["id"] == "u1"

@pytest.mark.asyncio
async def test_admin_repository_get_user_by_id_not_found(mock_supabase):
    repo = AdminRepository(mock_supabase)
    
    # postgrest-py returns None when maybe_single() has 0 matches
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.maybe_single = MagicMock(return_value=mock_table)
    # admin_repository uses async execute() returning None
    mock_table.execute = AsyncMock(return_value=None)
    
    mock_supabase.table.return_value = mock_table
    
    user = await repo.get_user_by_id("nonexistent")
    assert user is None

@pytest.mark.asyncio
async def test_user_repository_create_user_success(mock_supabase):
    repo = UserRepository(mock_supabase)
    user_data = {"id": "u1", "email": "test@test.com"}
    
    mock_execute = MagicMock()
    mock_execute.execute = AsyncMock(return_value=MagicMock(data=[user_data]))
    
    mock_table = MagicMock()
    mock_table.insert = MagicMock(return_value=mock_execute)
    mock_supabase.table.return_value = mock_table
    
    result = await repo.create_user(user_data)
    assert result == user_data

@pytest.mark.asyncio
async def test_user_repository_create_user_failure(mock_supabase):
    repo = UserRepository(mock_supabase)
    user_data = {"id": "u1", "email": "test@test.com"}
    
    mock_execute = MagicMock()
    mock_execute.execute = AsyncMock(return_value=MagicMock(data=[]))
    
    mock_table = MagicMock()
    mock_table.insert = MagicMock(return_value=mock_execute)
    mock_supabase.table.return_value = mock_table
    
    with pytest.raises(ProfileCreationError):
        await repo.create_user(user_data)
