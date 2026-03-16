"""Phlow CLI for token operations.

Usage:
    phlow generate-token --key SECRET --agent-id my-agent --name "My Agent"
    phlow decode-token TOKEN
    phlow verify-token TOKEN --key SECRET
"""

import argparse
import json
import sys

from . import decode_token, verify_token
from .auth import PhlowAuth
from .exceptions import PhlowError


def cmd_generate_token(args: argparse.Namespace) -> None:
    """Generate a JWT token for testing."""
    auth = PhlowAuth(
        private_key=args.key,
        token_expiry_hours=args.expiry,
    )
    token = auth.create_token(
        agent_id=args.agent_id,
        name=args.name,
        permissions=args.permissions.split(",") if args.permissions else None,
    )
    print(token)


def cmd_decode_token(args: argparse.Namespace) -> None:
    """Decode a JWT token without verification."""
    try:
        claims = decode_token(args.token)
        print(json.dumps(claims, indent=2, default=str))
    except PhlowError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_verify_token(args: argparse.Namespace) -> None:
    """Verify a JWT token."""
    try:
        claims = verify_token(args.token, args.key)
        print(json.dumps(claims, indent=2, default=str))
    except PhlowError as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="phlow",
        description="Phlow — JWT authentication tools for A2A agents",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate-token
    gen = subparsers.add_parser(
        "generate-token",
        help="Generate a JWT token for testing",
    )
    gen.add_argument(
        "--key", required=True, help="Signing key (secret or PEM file path)"
    )
    gen.add_argument("--agent-id", help="Agent ID (JWT sub claim)")
    gen.add_argument("--name", help="Agent name")
    gen.add_argument("--permissions", help="Comma-separated permissions")
    gen.add_argument(
        "--expiry", type=float, default=1.0, help="Token lifetime in hours (default: 1)"
    )
    gen.set_defaults(func=cmd_generate_token)

    # decode-token
    dec = subparsers.add_parser(
        "decode-token",
        help="Decode a JWT token without verification",
    )
    dec.add_argument("token", help="JWT token to decode")
    dec.set_defaults(func=cmd_decode_token)

    # verify-token
    ver = subparsers.add_parser(
        "verify-token",
        help="Verify a JWT token signature and claims",
    )
    ver.add_argument("token", help="JWT token to verify")
    ver.add_argument("--key", required=True, help="Verification key")
    ver.set_defaults(func=cmd_verify_token)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
