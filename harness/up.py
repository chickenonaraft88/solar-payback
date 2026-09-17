"""Bring up the disposable HA test harness with the integration loaded and seeded."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import requests

HARNESS_DIR = Path(__file__).parent
BASE_URL = "http://localhost:8123"


def wait_until_ready(timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if requests.get(f"{BASE_URL}/api/onboarding", timeout=5).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise TimeoutError("HA did not become ready in time")


def main() -> None:
    (HARNESS_DIR / "config").mkdir(exist_ok=True)
    subprocess.run(["docker", "compose", "up", "-d"], cwd=HARNESS_DIR, check=True)
    wait_until_ready()
    subprocess.run(
        [sys.executable, str(HARNESS_DIR / "seed" / "seed_demo.py")], check=True
    )


if __name__ == "__main__":
    main()
