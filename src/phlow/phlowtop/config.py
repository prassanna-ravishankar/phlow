"""Configuration management for phlowtop."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


class PhlowTopConfig(BaseModel):
    """Configuration for phlowtop application."""

    # Supabase connection
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")

    # UI settings
    refresh_rate_ms: int = Field(
        default=1000, description="UI refresh rate in milliseconds", ge=100, le=10000
    )

    max_messages_per_task: int = Field(
        default=1000,
        description="Maximum messages to display per task",
        ge=10,
        le=10000,
    )

    # Display settings
    datetime_format: str = Field(
        default="%Y-%m-%d %H:%M:%S", description="Format for displaying timestamps"
    )

    # Filtering
    default_view: str = Field(
        default="agents", description="Default view to show on startup"
    )

    # Connection settings
    connection_timeout_ms: int = Field(
        default=5000,
        description="Connection timeout in milliseconds",
        ge=1000,
        le=30000,
    )

    @classmethod
    def from_env(cls) -> "PhlowTopConfig":
        """Create configuration from environment variables."""
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            refresh_rate_ms=int(os.getenv("PHLOWTOP_REFRESH_RATE", "1000")),
            max_messages_per_task=int(os.getenv("PHLOWTOP_MAX_MESSAGES", "1000")),
            datetime_format=os.getenv("PHLOWTOP_DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S"),
            default_view=os.getenv("PHLOWTOP_DEFAULT_VIEW", "agents"),
            connection_timeout_ms=int(os.getenv("PHLOWTOP_CONNECTION_TIMEOUT", "5000")),
        )

    def validate_required_fields(self) -> None:
        """Validate that required configuration is present."""
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.supabase_anon_key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")
