from __future__ import annotations

import argparse
from collections.abc import Sequence

from inter_agent.adapters.claude import commands
from inter_agent.adapters.claude.listener import main as listen_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inter-agent-claude")
    sub = parser.add_subparsers(dest="command", required=True)

    listen = sub.add_parser("listen")
    listen.add_argument("--host")
    listen.add_argument("--port", type=int)
    listen.add_argument("--name", default="")
    listen.add_argument("--label")
    listen.add_argument("--session-id")

    sub.add_parser("connect")

    send = sub.add_parser("send")
    send.add_argument("to")
    send.add_argument("text")
    send.add_argument("--from", dest="from_name")

    broadcast = sub.add_parser("broadcast")
    broadcast.add_argument("text")
    broadcast.add_argument("--from", dest="from_name")

    subscribe = sub.add_parser("subscribe")
    subscribe.add_argument("channel")

    unsubscribe = sub.add_parser("unsubscribe")
    unsubscribe.add_argument("channel")

    publish = sub.add_parser("publish")
    publish.add_argument("channel")
    publish.add_argument("text")

    channels = sub.add_parser("channels")
    channels.add_argument("--json", action="store_true")

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--json", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")

    messages = sub.add_parser("messages")
    messages.add_argument("msg_id")
    messages.add_argument("--json", action="store_true")

    sub.add_parser("shutdown")
    sub.add_parser("disconnect")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "listen":
        listen_args = ["--name", args.name]
        if args.host is not None:
            listen_args.extend(["--host", args.host])
        if args.port is not None:
            listen_args.extend(["--port", str(args.port)])
        if args.label:
            listen_args.extend(["--label", args.label])
        if args.session_id:
            listen_args.extend(["--session-id", args.session_id])
        return listen_main(listen_args)
    if args.command == "connect":
        return commands.connect(args.name or "claude", args.label)
    if args.command == "send":
        return commands.send(args.to, args.text, args.from_name)
    if args.command == "broadcast":
        return commands.broadcast(args.text, args.from_name)
    if args.command == "subscribe":
        return commands.subscribe(args.channel)
    if args.command == "unsubscribe":
        return commands.unsubscribe(args.channel)
    if args.command == "publish":
        return commands.publish(args.channel, args.text)
    if args.command == "channels":
        return commands.channels(as_json=args.json)
    if args.command == "list":
        return commands.list_sessions()
    if args.command == "messages":
        return commands.message(args.msg_id, as_json=args.json)
    if args.command == "status":
        if args.json:
            print(commands.status_json())
        else:
            payload = commands.status()
            print(f"state={payload['state']}")
            print(f"host={payload['host']}")
            print(f"port={payload['port']}")
            print(f"reachable={payload['server_reachable']}")
            print(f"configured_host={payload['configured_host']}")
            print(f"configured_port={payload['configured_port']}")
            print(f"host_source={payload['host_source']}")
            print(f"port_source={payload['port_source']}")
            print(f"data_dir={payload['data_dir']}")
            print(f"data_dir_source={payload['data_dir_source']}")
            print(f"config_path={payload['config_path'] or ''}")
            print(f"message={payload['message']}")
            hints = payload.get("hints")
            if isinstance(hints, list):
                for hint in hints:
                    print(f"hint={hint}")
            connected_name = payload.get("connected_name")
            print(f"connected={payload['connected']}")
            print(f"connected_name={connected_name if connected_name is not None else ''}")
        return 0
    if args.command == "shutdown":
        return commands.shutdown()
    if args.command == "disconnect":
        return commands.disconnect()

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
