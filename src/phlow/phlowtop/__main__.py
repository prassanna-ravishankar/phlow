"""Main entry point for phlowtop."""

import sys

from .app import PhlowTopApp


def main() -> int:
    """Main entry point for phlowtop CLI."""
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
