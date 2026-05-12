from __future__ import annotations

import sys
import tarfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXPECTED_SCRIPTS = {
    "inter-agent-server",
    "inter-agent-connect",
    "inter-agent-send",
    "inter-agent-list",
    "inter-agent-shutdown",
    "inter-agent-pi",
}
EXPECTED_WHEEL_SUFFIXES = {
    "inter_agent/core/server.py",
    "inter_agent/adapters/pi/cli.py",
    "share/inter-agent/spec/asyncapi.yaml",
    "share/inter-agent/spec/schemas/hello.json",
    "share/inter-agent/spec/examples/shutdown.json",
}
EXPECTED_SDIST_SUFFIXES = {
    "src/inter_agent/core/server.py",
    "src/inter_agent/adapters/pi/cli.py",
    "spec/asyncapi.yaml",
    "spec/schemas/hello.json",
    "spec/examples/shutdown.json",
}


def latest(pattern: str) -> Path:
    matches = sorted(DIST.glob(pattern))
    if not matches:
        raise AssertionError(f"no artifact matching {pattern} in {DIST}")
    return matches[-1]


def assert_suffixes(paths: set[str], expected_suffixes: set[str], artifact: Path) -> None:
    for expected in expected_suffixes:
        if not any(path.endswith(expected) for path in paths):
            raise AssertionError(f"{artifact} is missing {expected}")


def validate_wheel(path: Path) -> None:
    with ZipFile(path) as wheel:
        names = set(wheel.namelist())
        assert_suffixes(names, EXPECTED_WHEEL_SUFFIXES, path)
        entry_points_name = next(
            (name for name in names if name.endswith(".dist-info/entry_points.txt")),
            None,
        )
        if entry_points_name is None:
            raise AssertionError(f"{path} is missing entry_points.txt")
        entry_points = wheel.read(entry_points_name).decode("utf-8")
        for script in EXPECTED_SCRIPTS:
            if f"{script} =" not in entry_points:
                raise AssertionError(f"{path} is missing console script {script}")


def validate_sdist(path: Path) -> None:
    with tarfile.open(path) as sdist:
        names = set(sdist.getnames())
    assert_suffixes(names, EXPECTED_SDIST_SUFFIXES, path)


def main() -> int:
    validate_wheel(latest("*.whl"))
    validate_sdist(latest("*.tar.gz"))
    print("release build artifacts validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
