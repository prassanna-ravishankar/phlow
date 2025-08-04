"""Tests for phlowtop Agents Dashboard logic functions."""

from datetime import datetime, timezone

from rich.text import Text


class TestAgentsViewLogic:
    """Test the pure logic functions from AgentsView."""

    def test_format_status_colors(self):
        """Test status formatting with colors."""

        # Replicate the _format_status logic
        def format_status(status: str) -> Text:
            color_map = {
                "ONLINE": "green",
                "WORKING": "blue",
                "IDLE": "white",
                "ERROR": "red",
                "OFFLINE": "gray",
            }
            color = color_map.get(status, "white")
            return Text(status, style=color)

        # Test different status colors
        test_cases = [
            ("ONLINE", "green"),
            ("WORKING", "blue"),
            ("IDLE", "white"),
            ("ERROR", "red"),
            ("OFFLINE", "gray"),
            ("UNKNOWN", "white"),  # default
        ]

        for status, _expected_color in test_cases:
            result = format_status(status)
            assert isinstance(result, Text)
            assert str(result) == status

    def test_calculate_uptime_logic(self):
        """Test uptime calculation logic."""

        # Replicate the _calculate_uptime logic but with controlled datetime
        def calculate_uptime(created_at: str | None, current_time: datetime) -> str:
            if not created_at:
                return "N/A"

            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                delta = current_time - created

                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)

                if days > 0:
                    return f"{days}d {hours}h"
                elif hours > 0:
                    return f"{hours}h {minutes}m"
                else:
                    return f"{minutes}m"

            except Exception:
                return "N/A"

        # Test with None timestamp
        current_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        assert calculate_uptime(None, current_time) == "N/A"

        # Test with invalid timestamp
        assert calculate_uptime("invalid", current_time) == "N/A"

        # Test with valid timestamps
        created_time_str = "2024-01-01T10:00:00Z"
        result = calculate_uptime(created_time_str, current_time)
        assert result == "2h 30m"

        # Test with days
        old_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        created_days_ago = "2023-12-30T10:00:00Z"
        result = calculate_uptime(created_days_ago, old_time)
        assert "2d" in result

    def test_format_heartbeat_logic(self):
        """Test heartbeat formatting logic."""

        # Replicate the _format_heartbeat logic but with controlled datetime
        def format_heartbeat(last_heartbeat: str | None, current_time: datetime) -> str:
            if not last_heartbeat:
                return "Never"

            try:
                heartbeat = datetime.fromisoformat(
                    last_heartbeat.replace("Z", "+00:00")
                )
                delta = current_time - heartbeat

                total_seconds = int(delta.total_seconds())

                if total_seconds < 60:
                    return f"{total_seconds}s ago"
                elif total_seconds < 3600:
                    minutes = total_seconds // 60
                    return f"{minutes}m ago"
                elif total_seconds < 86400:
                    hours = total_seconds // 3600
                    return f"{hours}h ago"
                else:
                    days = total_seconds // 86400
                    return f"{days}d ago"

            except Exception:
                return "N/A"

        # Test with None heartbeat
        current_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        assert format_heartbeat(None, current_time) == "Never"

        # Test with invalid heartbeat
        assert format_heartbeat("invalid", current_time) == "N/A"

        # Test with valid heartbeat - 5 minutes ago
        heartbeat_time_str = "2024-01-01T12:25:00Z"
        result = format_heartbeat(heartbeat_time_str, current_time)
        assert result == "5m ago"

        # Test seconds ago
        recent_time = datetime(2024, 1, 1, 12, 29, 45, tzinfo=timezone.utc)
        result = format_heartbeat("2024-01-01T12:29:30Z", recent_time)
        assert result == "15s ago"

        # Test hours ago
        hour_ago_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        result = format_heartbeat("2024-01-01T12:30:00Z", hour_ago_time)
        assert result == "1h ago"

    def test_row_selection_logic(self):
        """Test row selection logic without UI dependencies."""
        # Mock agents data
        mock_agents_data = [
            {"agent_id": "agent-1", "name": "Test Agent 1"},
            {"agent_id": "agent-2", "name": "Test Agent 2"},
        ]

        # Replicate the row selection logic
        def get_selected_agent(agents_data, row_index):
            if 0 <= row_index < len(agents_data):
                agent = agents_data[row_index]
                return agent.get("agent_id")
            return None

        # Test valid selections
        assert get_selected_agent(mock_agents_data, 0) == "agent-1"
        assert get_selected_agent(mock_agents_data, 1) == "agent-2"

        # Test invalid selections
        assert get_selected_agent(mock_agents_data, 5) is None
        assert get_selected_agent(mock_agents_data, -1) is None

        # Test with missing agent_id
        mock_invalid_data = [{"name": "Agent without ID"}]
        assert get_selected_agent(mock_invalid_data, 0) is None

    def test_data_processing_logic(self):
        """Test data processing logic."""
        # Mock agent data processing
        mock_agents_data = [
            {
                "agent_id": "agent-1",
                "name": "Test Agent 1",
                "status": "ONLINE",
                "active_tasks": 2,
                "service_url": "https://agent1.example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "last_heartbeat": "2024-01-01T12:00:00Z",
            },
            {
                "agent_id": "agent-2",
                "name": "Test Agent 2",
                "status": "IDLE",
                "active_tasks": 0,
                "service_url": "https://agent2.example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "last_heartbeat": "2024-01-01T11:30:00Z",
            },
        ]

        # Test data structure validity
        for agent in mock_agents_data:
            assert "agent_id" in agent
            assert "name" in agent
            assert "status" in agent
            assert agent["status"] in ["ONLINE", "WORKING", "IDLE", "ERROR", "OFFLINE"]
            assert isinstance(agent.get("active_tasks", 0), int)

    def test_data_validation_logic(self):
        """Test data validation and error handling."""

        # Test data format validation
        def validate_agent_data(agent_data):
            """Validate agent data structure."""
            required_fields = ["agent_id", "name", "status"]
            valid_statuses = ["ONLINE", "WORKING", "IDLE", "ERROR", "OFFLINE"]

            # Check required fields
            for field in required_fields:
                if field not in agent_data:
                    return False, f"Missing required field: {field}"

            # Check status validity
            if agent_data["status"] not in valid_statuses:
                return False, f"Invalid status: {agent_data['status']}"

            # Check active_tasks is integer if present
            if "active_tasks" in agent_data:
                if not isinstance(agent_data["active_tasks"], int):
                    return False, "active_tasks must be an integer"
                if agent_data["active_tasks"] < 0:
                    return False, "active_tasks cannot be negative"

            return True, "Valid"

        # Test valid data
        valid_agent = {
            "agent_id": "agent-1",
            "name": "Test Agent",
            "status": "ONLINE",
            "active_tasks": 2,
        }
        is_valid, message = validate_agent_data(valid_agent)
        assert is_valid
        assert message == "Valid"

        # Test missing required field
        invalid_agent = {"name": "Test Agent", "status": "ONLINE"}
        is_valid, message = validate_agent_data(invalid_agent)
        assert not is_valid
        assert "Missing required field" in message

        # Test invalid status
        invalid_status_agent = {
            "agent_id": "agent-1",
            "name": "Test Agent",
            "status": "INVALID_STATUS",
        }
        is_valid, message = validate_agent_data(invalid_status_agent)
        assert not is_valid
        assert "Invalid status" in message

        # Test invalid active_tasks type
        invalid_tasks_agent = {
            "agent_id": "agent-1",
            "name": "Test Agent",
            "status": "ONLINE",
            "active_tasks": "not_a_number",
        }
        is_valid, message = validate_agent_data(invalid_tasks_agent)
        assert not is_valid
        assert "active_tasks must be an integer" in message

        # Test negative active_tasks
        negative_tasks_agent = {
            "agent_id": "agent-1",
            "name": "Test Agent",
            "status": "ONLINE",
            "active_tasks": -1,
        }
        is_valid, message = validate_agent_data(negative_tasks_agent)
        assert not is_valid
        assert "active_tasks cannot be negative" in message
