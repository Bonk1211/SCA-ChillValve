"""E2E smoke for the FastAPI backend.

Starts uvicorn on port 8765 in a subprocess, drives a scenario via HTTP,
drains the WebSocket for a couple seconds, asserts >=50 state messages,
then shuts down. Independent from the test suite.

Usage:
    uv run python scripts/validate_backend_e2e.py
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
import websockets  # noqa: E402

PORT = 8765
BASE = f"http://localhost:{PORT}"
WS = f"ws://localhost:{PORT}/ws"


async def drive() -> int:
    async with httpx.AsyncClient() as http:
        for _ in range(40):
            try:
                r = await http.get(f"{BASE}/health")
                if r.status_code == 200:
                    break
            except httpx.RequestError:
                pass
            await asyncio.sleep(0.25)
        else:
            print("FAIL: server didn't come up in 10 s", file=sys.stderr)
            return 1

        r = await http.post(
            f"{BASE}/scenario/start",
            params={"name": "steady_state", "mode": "chillvalve"},
        )
        assert r.status_code == 200, r.text
        print(f"start: {r.json()}")

        received = 0
        async with websockets.connect(WS) as ws:
            try:
                while received < 100:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    assert data["type"] == "state"
                    received += 1
            except asyncio.TimeoutError:
                pass
        print(f"validated: received {received} state messages")
        if received < 50:
            print(f"FAIL: only {received} messages in 2 s", file=sys.stderr)
            return 1
        await http.post(f"{BASE}/scenario/reset")
    return 0


def main() -> int:
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend.main:app", "--port", str(PORT),
            "--log-level", "warning",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
        return asyncio.run(drive())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
