"""Tests for phlowtop configuration management."""

import os
from unittest.mock import patch

import pytest

from src.phlow.phlowtop.config import PhlowTopConfig


class TestPhlowTopConfig:
    """Test phlowtop configuration."""

    def test_config_from_env_with_required_fields(self):
        """Test creating config from environment variables with required fields."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_ANON_KEY": "test-anon-key",
            },
        ):
            config = PhlowTopConfig.from_env()
            assert config.supabase_url == "https://test.supabase.co"
            assert config.supabase_anon_key == "test-anon-key"
            assert config.refresh_rate_ms == 1000  # default
            assert config.max_messages_per_task == 1000  # default
            assert config.datetime_format == "%Y-%m-%d %H:%M:%S"  # default
            assert config.default_view == "agents"  # default
            assert config.connection_timeout_ms == 5000  # default

    def test_config_from_env_with_custom_settings(self):
        """Test creating config with custom environment settings."""
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://custom.supabase.co",
                "SUPABASE_ANON_KEY": "custom-key",
                "PHLOWTOP_REFRESH_RATE": "2000",
                "PHLOWTOP_MAX_MESSAGES": "500",
                "PHLOWTOP_DATETIME_FORMAT": "%m/%d/%Y %H:%M",
                "PHLOWTOP_DEFAULT_VIEW": "tasks",
                "PHLOWTOP_CONNECTION_TIMEOUT": "10000",
            },
        ):
            config = PhlowTopConfig.from_env()
            assert config.supabase_url == "https://custom.supabase.co"
            assert config.supabase_anon_key == "custom-key"
            assert config.refresh_rate_ms == 2000
            assert config.max_messages_per_task == 500
            assert config.datetime_format == "%m/%d/%Y %H:%M"
            assert config.default_view == "tasks"
            assert config.connection_timeout_ms == 10000

    def test_config_validation_success(self):
        """Test successful validation of required fields."""
        config = PhlowTopConfig(
            supabase_url="https://test.supabase.co", supabase_anon_key="test-key"
        )
        # Should not raise
        config.validate_required_fields()

    def test_config_validation_missing_url(self):
        """Test validation fails when URL is missing."""
        config = PhlowTopConfig(supabase_url="", supabase_anon_key="test-key")
        with pytest.raises(
            ValueError, match="SUPABASE_URL environment variable is required"
        ):
            config.validate_required_fields()

    def test_config_validation_missing_key(self):
        """Test validation fails when anon key is missing."""
        config = PhlowTopConfig(
            supabase_url="https://test.supabase.co", supabase_anon_key=""
        )
        with pytest.raises(
            ValueError, match="SUPABASE_ANON_KEY environment variable is required"
        ):
            config.validate_required_fields()

    def test_config_field_constraints(self):
        """Test pydantic field constraints."""
        # Test refresh_rate constraints
        with pytest.raises(ValueError):
            PhlowTopConfig(
                supabase_url="https://test.supabase.co",
                supabase_anon_key="test-key",
                refresh_rate_ms=50,  # Below minimum of 100
            )

        with pytest.raises(ValueError):
            PhlowTopConfig(
                supabase_url="https://test.supabase.co",
                supabase_anon_key="test-key",
                refresh_rate_ms=15000,  # Above maximum of 10000
            )

        # Test max_messages constraints
        with pytest.raises(ValueError):
            PhlowTopConfig(
                supabase_url="https://test.supabase.co",
                supabase_anon_key="test-key",
                max_messages_per_task=5,  # Below minimum of 10
            )

    def test_config_from_env_missing_required(self):
        """Test config creation fails gracefully with missing required env vars."""
        with patch.dict(os.environ, {}, clear=True):
            config = PhlowTopConfig.from_env()
            # Should create config with empty required fields
            assert config.supabase_url == ""
            assert config.supabase_anon_key == ""

            # Validation should fail
            with pytest.raises(ValueError):
                config.validate_required_fields()
