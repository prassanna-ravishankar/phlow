"""Tests for RBAC role cache module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from phlow.rbac.cache import RoleCache


def _make_supabase_mock():
    return MagicMock()


def _make_cached_role_data(
    agent_id="agent-1",
    role="admin",
    expired=False,
    no_expiry=False,
):
    now = datetime.now(timezone.utc)
    expires = None
    if not no_expiry:
        if expired:
            expires = (now - timedelta(hours=1)).isoformat()
        else:
            expires = (now + timedelta(hours=1)).isoformat()

    return {
        "id": "cache-1",
        "agent_id": agent_id,
        "role": role,
        "verified_at": now.isoformat(),
        "expires_at": expires,
        "credential_hash": "hash-abc",
        "issuer_did": "did:example:issuer",
        "metadata": {"source": "test"},
    }


class TestRoleCacheGetCachedRole:
    @pytest.mark.asyncio
    async def test_returns_cached_role(self):
        supabase = _make_supabase_mock()
        data = _make_cached_role_data()
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[data]
        )

        cache = RoleCache(supabase)
        result = await cache.get_cached_role("agent-1", "admin")

        assert result is not None
        assert result.role == "admin"
        assert result.agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        cache = RoleCache(supabase)
        result = await cache.get_cached_role("agent-1", "admin")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_and_cleans_expired(self):
        supabase = _make_supabase_mock()
        data = _make_cached_role_data(expired=True)
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[data]
        )

        cache = RoleCache(supabase)
        result = await cache.get_cached_role("agent-1", "admin")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception(
            "db error"
        )

        cache = RoleCache(supabase)
        result = await cache.get_cached_role("agent-1", "admin")
        assert result is None


class TestRoleCacheCacheVerifiedRole:
    @pytest.mark.asyncio
    async def test_caches_role_successfully(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock(data=[{"id": 1}])
        )

        cache = RoleCache(supabase)
        result = await cache.cache_verified_role(
            agent_id="agent-1",
            role="admin",
            credential_hash="hash-abc",
            issuer_did="did:example:issuer",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_empty_data(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        cache = RoleCache(supabase)
        result = await cache.cache_verified_role(
            agent_id="agent-1", role="admin", credential_hash="hash"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.upsert.return_value.execute.side_effect = Exception(
            "db error"
        )

        cache = RoleCache(supabase)
        result = await cache.cache_verified_role(
            agent_id="agent-1", role="admin", credential_hash="hash"
        )
        assert result is False


class TestRoleCacheRemoveCachedRole:
    @pytest.mark.asyncio
    async def test_removes_successfully(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        cache = RoleCache(supabase)
        result = await cache.remove_cached_role("agent-1", "admin")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception(
            "db error"
        )

        cache = RoleCache(supabase)
        result = await cache.remove_cached_role("agent-1", "admin")
        assert result is False


class TestRoleCacheGetAgentRoles:
    @pytest.mark.asyncio
    async def test_returns_non_expired_roles(self):
        supabase = _make_supabase_mock()
        data = [
            _make_cached_role_data(role="admin"),
            _make_cached_role_data(role="viewer"),
        ]
        supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=data
        )
        # Mock remove for any expired roles
        supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        cache = RoleCache(supabase)
        roles = await cache.get_agent_roles("agent-1")
        assert len(roles) == 2

    @pytest.mark.asyncio
    async def test_filters_expired_roles(self):
        supabase = _make_supabase_mock()
        data = [
            _make_cached_role_data(role="admin"),
            _make_cached_role_data(role="expired-role", expired=True),
        ]
        supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=data
        )
        supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        cache = RoleCache(supabase)
        roles = await cache.get_agent_roles("agent-1")
        assert len(roles) == 1
        assert roles[0].role == "admin"

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
            "db error"
        )

        cache = RoleCache(supabase)
        roles = await cache.get_agent_roles("agent-1")
        assert roles == []


class TestRoleCacheCleanupExpiredRoles:
    @pytest.mark.asyncio
    async def test_cleans_expired_roles(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.lt.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[{"id": "r1"}, {"id": "r2"}]
        )
        supabase.table.return_value.delete.return_value.in_.return_value.execute.return_value = MagicMock()

        cache = RoleCache(supabase)
        count = await cache.cleanup_expired_roles()
        assert count == 2

    @pytest.mark.asyncio
    async def test_returns_zero_when_none_expired(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.lt.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[]
        )

        cache = RoleCache(supabase)
        count = await cache.cleanup_expired_roles()
        assert count == 0

    @pytest.mark.asyncio
    async def test_returns_zero_on_exception(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.lt.return_value.is_.return_value.execute.side_effect = Exception(
            "db error"
        )

        cache = RoleCache(supabase)
        count = await cache.cleanup_expired_roles()
        assert count == 0
