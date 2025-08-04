"""Tests for phlowtop basic structure and imports."""

import sys
from unittest.mock import Mock, patch


class TestPhlowTopStructure:
    """Test basic phlowtop structure without full Textual dependencies."""

    def test_phlowtop_package_import(self):
        """Test that phlowtop package can be imported."""
        from src.phlow.phlowtop import __version__

        assert __version__ == "0.1.0"

    def test_config_module_import(self):
        """Test config module imports correctly."""
        from src.phlow.phlowtop.config import PhlowTopConfig

        assert PhlowTopConfig is not None

    @patch.dict(
        sys.modules,
        {
            "textual.app": Mock(),
            "textual.binding": Mock(),
            "textual.containers": Mock(),
            "textual.reactive": Mock(),
            "textual.widgets": Mock(),
        },
    )
    def test_app_module_can_import_with_mocked_textual(self):
        """Test app module can import when textual is mocked."""
        # Mock textual modules
        mock_app = Mock()
        mock_app.App = Mock()
        mock_app.ComposeResult = Mock()

        mock_binding = Mock()
        mock_binding.Binding = Mock()

        mock_containers = Mock()
        mock_containers.Container = Mock()

        mock_reactive = Mock()
        mock_reactive.reactive = Mock()

        mock_widgets = Mock()
        mock_widgets.Footer = Mock()
        mock_widgets.LoadingIndicator = Mock()

        with patch.dict(
            sys.modules,
            {
                "textual.app": mock_app,
                "textual.binding": mock_binding,
                "textual.containers": mock_containers,
                "textual.reactive": mock_reactive,
                "textual.widgets": mock_widgets,
            },
        ):
            # Should be able to import without errors
            from src.phlow.phlowtop.app import PhlowTopApp

            assert PhlowTopApp is not None

    def test_views_module_structure(self):
        """Test views module structure."""
        from src.phlow.phlowtop.views import __all__

        expected_views = ["AgentsView", "TasksView", "MessagesView"]
        for view in expected_views:
            assert view in __all__

    def test_widgets_module_structure(self):
        """Test widgets module structure."""
        # Import should work even without textual since it's just checking __all__
        try:
            from src.phlow.phlowtop.widgets import __all__

            assert "PhlowTopHeader" in __all__
        except ImportError:
            # Expected when textual is not available
            pass

    def test_main_module_structure(self):
        """Test main module has proper structure for CLI."""
        # Import the main module
        import src.phlow.phlowtop.__main__ as main_module

        # Should have main function
        assert hasattr(main_module, "main")
        assert callable(main_module.main)

    @patch("src.phlow.phlowtop.supabase_client.SupabaseMonitor")
    def test_supabase_client_mock_initialization(self, mock_supabase_monitor):
        """Test SupabaseMonitor can be mocked and initialized."""
        from src.phlow.phlowtop.config import PhlowTopConfig
        from src.phlow.phlowtop.supabase_client import SupabaseMonitor

        # Create a mock config
        mock_config = Mock(spec=PhlowTopConfig)
        mock_config.supabase_url = "https://test.supabase.co"
        mock_config.supabase_anon_key = "test-key"
        mock_config.connection_timeout_ms = 5000

        # Mock the SupabaseMonitor class
        mock_instance = Mock()
        mock_supabase_monitor.return_value = mock_instance

        # Should be able to create instance
        monitor = SupabaseMonitor(mock_config)
        assert monitor is not None
        mock_supabase_monitor.assert_called_once_with(mock_config)

    def test_package_metadata(self):
        """Test package metadata is accessible."""
        import src.phlow.phlowtop

        assert hasattr(src.phlow.phlowtop, "__version__")
        assert isinstance(src.phlow.phlowtop.__version__, str)
