#!/usr/bin/env python3
"""Run installed acceptance for the three Python child artifacts and OpenCode source submodule."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHILD_SOURCES = {
    "core": ROOT / "core",
    "extensions/pi": ROOT / "extensions/pi",
    "extensions/claude-code": ROOT / "extensions/claude-code",
}
SUBMODULE_SOURCES = {
    **CHILD_SOURCES,
    "extensions/opencode": ROOT / "extensions/opencode",
}


def indexed_revisions(root: Path) -> dict[str, str]:
    revisions = {}
    for path in CHILD_SOURCES:
        entry = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-s", "--", path], text=True
        ).strip()
        fields = entry.split(maxsplit=3)
        if len(fields) != 4 or fields[0] != "160000" or fields[3] != path:
            raise RuntimeError(f"missing indexed gitlink: {path}")
        revisions[path] = fields[1]
    return revisions


EXPECTED = indexed_revisions(ROOT)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(argv, cwd=cwd, env=env, check=True)


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def check_index(root: Path) -> None:
    for path, commit in EXPECTED.items():
        actual = subprocess.check_output(["git", "-C", str(root / path), "rev-parse", "HEAD"], text=True).strip()
        if actual != commit:
            raise RuntimeError(f"{path} is at {actual}, expected {commit}")


def local_recursive_clone(destination: Path) -> None:
    # Materialize the current index so Phase E can test staged gitlinks before
    # the ecosystem pin commit exists; this never approximates the candidate by
    # copying selected files.
    tree = subprocess.check_output(["git", "-C", str(ROOT), "write-tree"], text=True).strip()
    run(["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(ROOT), str(destination)])
    run(["git", "-C", str(destination), "read-tree", tree])
    run(["git", "-C", str(destination), "checkout-index", "-a"])
    for path, source in SUBMODULE_SOURCES.items():
        run(["git", "-C", str(destination), "config", f"submodule.{path}.url", str(source)])
    run(
        ["git", "-C", str(destination), "-c", "protocol.file.allow=always", "submodule", "update", "--init", "--recursive"]
    )
    check_index(destination)


def child_gates(checkout: Path, env: dict[str, str]) -> None:
    run(["uv", "sync", "--locked", "--offline"], cwd=checkout / "core", env=env)
    run(["./run-checks.sh"], cwd=checkout / "core", env=env)
    pi = checkout / "extensions/pi"
    run(["uv", "sync", "--locked", "--offline"], cwd=pi, env=env)
    run(["npm", "ci", "--offline"], cwd=pi, env=env)
    run(["scripts/run-checks.sh"], cwd=pi, env=env)
    claude = checkout / "extensions/claude-code"
    run(["uv", "sync", "--locked", "--offline"], cwd=claude, env=env)
    run(["scripts/run-checks.sh"], cwd=claude, env=env)


def install_artifacts(checkout: Path, runtime: Path, env: dict[str, str]) -> None:
    run(["uv", "venv", str(runtime)], cwd=checkout, env=env)
    wheels = [
        next((checkout / "core" / "dist").glob("inter_agent_core-*.whl"), None),
        next((checkout / "extensions/pi" / "dist").glob("inter_agent_pi-*.whl"), None),
        next((checkout / "extensions/claude-code" / "dist").glob("inter_agent_claude_code-*.whl"), None),
    ]
    if any(path is None for path in wheels):
        raise RuntimeError("child gates did not produce all expected wheels")
    run(["uv", "pip", "install", "--offline", "--python", str(runtime / "bin/python"), *(str(path) for path in wheels if path)], cwd=checkout, env=env)
    clean = dict(env)
    clean.pop("PYTHONPATH", None)
    clean["PATH"] = f"{runtime / 'bin'}:/usr/bin:/bin"
    run([str(runtime / "bin/python"), "-c", "import inter_agent, inter_agent_pi, inter_agent_claude"], cwd=checkout, env=clean)
    for command in ("inter-agent-server", "inter-agent-pi", "inter-agent-claude"):
        run([str(runtime / "bin" / command), "--help"], cwd=checkout, env=clean)


class Scene:
    def __init__(self, base: Path, socket_base: Path, runtime: Path, label: str, *, tls: bool = False):
        self.base = base
        self.socket_base = socket_base
        self.runtime = runtime
        self.label = label
        self.host = "127.0.0.1"
        self.port = free_port()
        self.state = socket_base / f"state-{label}"
        self.state.mkdir(parents=True, exist_ok=True)
        self.secret = secrets.token_urlsafe(32)
        self.env = {
            "PATH": f"{runtime / 'bin'}:/usr/bin:/bin",
            "HOME": str(base / "home"),
            "INTER_AGENT_HOST": self.host,
            "INTER_AGENT_PORT": str(self.port),
            "INTER_AGENT_DATA_DIR": str(self.state),
            "INTER_AGENT_SECRET": self.secret,
        }
        if tls:
            self.env["INTER_AGENT_TLS"] = "true"
            self.env["INTER_AGENT_TLS_CERT"] = str(base / "tls-material" / "tls-cert.pem")
            self.env["INTER_AGENT_TLS_KEY"] = str(base / "tls-material" / "tls-key.pem")
        self.procs: list[subprocess.Popen] = []

    def __enter__(self) -> Scene:
        return self

    def __exit__(self, *_: object) -> None:
        for proc in reversed(self.procs):
            if proc.poll() is None:
                proc.terminate()
        for proc in self.procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    def spawn(self, argv: list[str], name: str) -> subprocess.Popen:
        log = open(self.base / f"{self.label}-{name}.log", "w", encoding="utf-8")
        proc = subprocess.Popen(argv, env=self.env, stdout=log, stderr=subprocess.STDOUT, text=True)
        self.procs.append(proc)
        return proc

    def server(self, tls: bool = False) -> subprocess.Popen:
        argv = [str(self.runtime / "bin/inter-agent-server"), "--host", self.host, "--port", str(self.port)]
        cert = self.base / "tls-material" / "tls-cert.pem"
        key = self.base / "tls-material" / "tls-key.pem"
        argv += ["--tls", "--tls-cert", str(cert), "--tls-key", str(key)] if tls else ["--no-tls"]
        return self.spawn(argv, "server")

    def pi(self, name: str) -> subprocess.Popen:
        return self.spawn([str(self.runtime / "bin/inter-agent-pi"), "connect", name], f"pi-{name}")

    def claude_listener(self, name: str) -> subprocess.Popen:
        return self.spawn([str(self.runtime / "bin/inter-agent-claude"), "listen", "--name", name], f"claude-{name}")

    def command(self, binary: str, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(self.runtime / "bin" / binary), *args], env=self.env, capture_output=True, text=True, timeout=15)

    def wait_ready(self) -> None:
        end = time.monotonic() + 10
        while time.monotonic() < end:
            if self.command("inter-agent-status", ["--json"]).returncode == 0:
                return
            time.sleep(0.05)
        raise AssertionError(f"{self.label}: server did not become ready")

    def wait_sessions(self, names: set[str]) -> None:
        end = time.monotonic() + 15
        while time.monotonic() < end:
            result = self.command("inter-agent-list", [])
            try:
                connected = {entry["name"] for entry in json.loads(result.stdout).get("sessions", [])}
            except (ValueError, KeyError, TypeError):
                connected = set()
            if names <= connected:
                return
            time.sleep(0.05)
        raise AssertionError(f"{self.label}: sessions did not connect")

    def wait_log(self, name: str, needle: str) -> None:
        path = self.base / f"{self.label}-{name}.log"
        end = time.monotonic() + 10
        while time.monotonic() < end:
            if path.exists() and needle in path.read_text(encoding="utf-8"):
                return
            time.sleep(0.05)
        content = path.read_text(encoding="utf-8") if path.exists() else "<missing>"
        raise AssertionError(f"{self.label}: {needle!r} not found: {content[:500]!r}")


def require(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"{label}=passed")


def installed_matrix(base: Path, socket_base: Path, runtime: Path, env: dict[str, str]) -> None:
    tls_dir = base / "tls-material"
    tls_dir.mkdir()
    tls_env = dict(env)
    tls_env["PATH"] = f"{runtime / 'bin'}:/usr/bin:/bin"
    tls_env.pop("PYTHONPATH", None)
    run([str(runtime / "bin/python"), "-c", "from inter_agent.core.tls import ensure_tls_material; ensure_tls_material(__import__('pathlib').Path(__import__('sys').argv[1]), '127.0.0.1')", str(tls_dir)], env=tls_env)

    with Scene(base, socket_base, runtime, "direct") as scene:
        scene.server(); scene.wait_ready(); scene.pi("pi"); scene.claude_listener("claude"); scene.wait_sessions({"pi", "claude"})
        require("direct-pi-to-claude", scene.command("inter-agent-pi", ["send", "claude", "hello-from-pi", "--from", "pi"]).returncode == 0)
        scene.wait_log("claude-claude", "hello-from-pi")
        require("direct-claude-to-pi", scene.command("inter-agent-claude", ["send", "pi", "hello-from-claude"]).returncode == 0)
        scene.wait_log("pi-pi", "hello-from-claude")

    with Scene(base, socket_base, runtime, "broadcast") as scene:
        scene.server(); scene.wait_ready(); scene.pi("pi"); scene.claude_listener("claude"); scene.wait_sessions({"pi", "claude"})
        require("broadcast-pi", scene.command("inter-agent-pi", ["broadcast", "bcast-from-pi"]).returncode == 0)
        scene.wait_log("claude-claude", "bcast-from-pi")
        require("broadcast-claude", scene.command("inter-agent-claude", ["broadcast", "bcast-from-claude"]).returncode == 0)
        scene.wait_log("pi-pi", "bcast-from-claude")

    with Scene(base, socket_base, runtime, "channel") as scene:
        scene.server(); scene.wait_ready(); scene.pi("pi"); scene.claude_listener("claude"); scene.wait_sessions({"pi", "claude"})
        require("channel-subscribe", scene.command("inter-agent-pi", ["subscribe", "room", "--name", "pi"]).returncode == 0)
        require("channel-publish", scene.command("inter-agent-claude", ["publish", "room", "channel-message"]).returncode == 0)
        scene.wait_log("pi-pi", "channel-message")
        require("channel-unsubscribe", scene.command("inter-agent-pi", ["unsubscribe", "room", "--name", "pi"]).returncode == 0)

    with Scene(base, socket_base, runtime, "preconnect") as scene:
        scene.server(); scene.wait_ready()
        result = scene.command("inter-agent-list", [])
        require("preconnect-list", result.returncode == 0 and json.loads(result.stdout).get("sessions") == [])
        require("preconnect-status", json.loads(scene.command("inter-agent-status", ["--json"]).stdout).get("state") == "available")

    with Scene(base, socket_base, runtime, "kick") as scene:
        scene.server(); scene.wait_ready(); pi_proc = scene.pi("pi"); scene.claude_listener("claude"); scene.wait_sessions({"pi", "claude"})
        require("kick-command", scene.command("inter-agent-claude", ["kick", "pi"]).returncode == 0)
        end = time.monotonic() + 6
        while time.monotonic() < end and pi_proc.poll() is None:
            time.sleep(0.05)
        require("kick-stops", pi_proc.poll() is not None)

    with Scene(base, socket_base, runtime, "isolation-a") as first, Scene(base, socket_base, runtime, "isolation-b") as second:
        first.server(); first.wait_ready(); second.server(); second.wait_ready()
        first.pi("pi-a"); first.claude_listener("claude-a"); first.wait_sessions({"pi-a", "claude-a"})
        second.pi("pi-b")
        end = time.monotonic() + 10
        names: set[str] = set()
        while time.monotonic() < end:
            try:
                names = {entry["name"] for entry in json.loads(second.command("inter-agent-list", []).stdout).get("sessions", [])}
                if "pi-b" in names:
                    break
            except (ValueError, KeyError, TypeError):
                pass
            time.sleep(0.05)
        require("isolated-bus-connect", "pi-b" in names)
        require("isolated-a-send", first.command("inter-agent-pi", ["send", "claude-a", "isolated-message"]).returncode == 0)
        first.wait_log("claude-claude-a", "isolated-message")
        time.sleep(0.5)
        second_log = base / "isolation-b-pi-pi-b.log"
        require("isolated-no-cross-delivery", "isolated-message" not in second_log.read_text(encoding="utf-8"))

    with Scene(base, socket_base, runtime, "tls", tls=True) as scene:
        scene.server(tls=True); scene.wait_ready(); scene.pi("pi"); scene.claude_listener("claude"); scene.wait_sessions({"pi", "claude"})
        require("trusted-tls", scene.command("inter-agent-pi", ["send", "claude", "tls-message", "--from", "pi"]).returncode == 0)
        scene.wait_log("claude-claude", "tls-message")

    with Scene(base, socket_base, runtime, "plaintext-rejection") as scene:
        scene.server(tls=True); scene.wait_ready()
        bad_env = dict(scene.env)
        bad_env["INTER_AGENT_TLS"] = "false"
        log = open(base / "plaintext-client.log", "w", encoding="utf-8")
        proc = subprocess.Popen([str(runtime / "bin/inter-agent-pi"), "connect", "bad"], env=bad_env, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            end = time.monotonic() + 5
            while time.monotonic() < end and proc.poll() is None:
                time.sleep(0.05)
            require("plaintext-to-tls-rejected", proc.poll() is not None)
        finally:
            if proc.poll() is None:
                proc.terminate(); proc.wait(timeout=5)


def main() -> int:
    if os.environ.get("PYTHONPATH"):
        raise SystemExit("PYTHONPATH must be unset")
    check_index(ROOT)
    temp = Path(tempfile.mkdtemp(prefix="inter-agent-ecosystem-acceptance.", dir="/tmp"))
    alias = Path(tempfile.mkdtemp(prefix="iag-", dir="/tmp"))
    alias.rmdir()
    alias.symlink_to(temp, target_is_directory=True)
    try:
        checkout = temp / "checkout"
        runtime = temp / "runtime"
        home = temp / "home"
        home.mkdir()
        local_recursive_clone(checkout)
        environment = dict(os.environ)
        environment.update(
            {
                "HOME": str(home),
                "BASH_ENV": "/dev/null",
                "UV_OFFLINE": "1",
                "NPM_CONFIG_OFFLINE": "true",
                "NPM_CONFIG_USERCONFIG": str(temp / ".npmrc"),
            }
        )
        (temp / ".npmrc").write_text("fund=false\naudit=false\n", encoding="utf-8")
        child_gates(checkout, environment)
        install_artifacts(checkout, runtime, environment)
        installed_matrix(temp, alias, runtime, environment)
        for path in SUBMODULE_SOURCES:
            if subprocess.check_output(["git", "-C", str(checkout / path), "status", "--porcelain"], text=True):
                raise RuntimeError(f"child worktree changed: {path}")
        print("installed acceptance passed")
    finally:
        alias.unlink(missing_ok=True)
        shutil.rmtree(temp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
