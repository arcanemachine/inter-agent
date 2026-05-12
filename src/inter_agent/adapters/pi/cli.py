from __future__ import annotations

import argparse
from collections.abc import Sequence

from inter_agent.adapters.pi import commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-pi")
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect")
    connect.add_argument("name")
    connect.add_argument("--label")

    send = sub.add_parser("send")
    send.add_argument("to")
    send.add_argument("text")

    broadcast = sub.add_parser("broadcast")
    broadcast.add_argument("text")

    sub.add_parser("list")
    sub.add_parser("status")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "connect":
        return commands.connect(args.name, args.label)
    if args.command == "send":
        return commands.send(args.to, args.text)
    if args.command == "broadcast":
        return commands.broadcast(args.text)
    if args.command == "list":
        return commands.list_sessions()
    if args.command == "status":
        print(commands.status_json())
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
