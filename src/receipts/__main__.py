"""Small CLI for reproducible metadata operations. Apache-2.0."""
import argparse
import json
from pathlib import Path
from .evidence import utc, snowflake_utc, receipt, summarize_posts, direct_funding


def main():
    parser = argparse.ArgumentParser(prog="python -m receipts")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["snowflake", "utc"]:
        sub = commands.add_parser(name)
        sub.add_argument("value")
    sub = commands.add_parser("receipt")
    sub.add_argument("file", type=Path)
    sub.add_argument("--url", required=True)
    sub.add_argument("--retrieved-at", required=True)
    sub.add_argument("--locator", required=True)
    sub.add_argument("--access-basis", choices=["public_without_login"], required=True)
    sub = commands.add_parser("style")
    sub.add_argument("file", type=Path)
    sub = commands.add_parser("funding")
    sub.add_argument("file", type=Path)
    sub.add_argument("--payer", required=True)
    sub.add_argument("--payee", required=True)
    args = parser.parse_args()
    if args.command == "snowflake":
        result = {"decoded_utc": snowflake_utc(args.value), "authenticated": False}
    elif args.command == "utc":
        result = {"utc": utc(args.value), "original": args.value}
    elif args.command == "receipt":
        result = receipt(args.file, args.url, args.retrieved_at, args.access_basis, args.locator)
    elif args.command == "style":
        result = summarize_posts(json.loads(args.file.read_text()))
    else:
        result = direct_funding(json.loads(args.file.read_text()), args.payer, args.payee)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
