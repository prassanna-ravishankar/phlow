"""Main entry point for phlowtop."""

import sys


def main() -> int:
    """Main entry point for phlowtop CLI."""
    try:
        from .app import PhlowTopApp
    except ImportError as e:
        print(
            "phlowtop requires additional dependencies. Install with: uv add --group phlowtop phlow[phlowtop]",
            file=sys.stderr,
        )
        print(f"Import error: {e}", file=sys.stderr)
        return 1

    try:
        app = PhlowTopApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\nExiting phlowtop...")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
