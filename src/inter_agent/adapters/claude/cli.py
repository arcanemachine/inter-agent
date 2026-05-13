from __future__ import annotations

import argparse
from collections.abc import Sequence

from inter_agent.adapters.claude import commands
from inter_agent.adapters.claude.listener import main as listen_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-claude")
    sub = parser.add_subparsers(dest="command", required=True)

    listen = sub.add_parser("listen")
    listen.add_argument("--host", default="127.0.0.1")
    listen.add_argument("--port", type=int, default=9473)
    listen.add_argument("--name", default="")
    listen.add_argument("--label")
    listen.add_argument("--session-id")

    sub.add_parser("connect")

    send = sub.add_parser("send")
    send.add_argument("to")
    send.add_argument("text")

    broadcast = sub.add_parser("broadcast")
    broadcast.add_argument("text")

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--json", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")

    sub.add_parser("shutdown")
    sub.add_parser("disconnect")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "listen":
        return listen_main(
            [
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--name",
                args.name,
            ]
            + (["--label", args.label] if args.label else [])
            + (["--session-id", args.session_id] if args.session_id else [])
        )
    if args.command == "connect":
        return commands.connect(args.name or "claude", args.label)
    if args.command == "send":
        return commands.send(args.to, args.text)
    if args.command == "broadcast":
        return commands.broadcast(args.text)
    if args.command == "list":
        return commands.list_sessions()
    if args.command == "status":
        if args.json:
            print(commands.status_json())
        else:
            payload = commands.status()
            print(f"state={payload['state']}")
            print(f"host={payload['host']}")
            print(f"port={payload['port']}")
            print(f"reachable={payload['server_reachable']}")
            print(f"identity_verified={payload['identity_verified']}")
            print(f"message={payload['message']}")
        return 0
    if args.command == "shutdown":
        return commands.shutdown()
    if args.command == "disconnect":
        return commands.disconnect()

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
