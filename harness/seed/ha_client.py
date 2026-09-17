"""Minimal REST + websocket client for bootstrapping a fresh HA test instance."""

from __future__ import annotations

import itertools
import json

import requests
from websockets.sync.client import ClientConnection, connect as ws_connect

ONBOARDING_CLIENT_ID = "http://localhost:8123/"


class HAClient:
    def __init__(self, base_url: str, access_token: str, ws: ClientConnection) -> None:
        self.base_url = base_url
        self.access_token = access_token
        self._ws = ws
        self._ids = itertools.count(1)

    @classmethod
    def onboard(
        cls, base_url: str, name: str, username: str, password: str
    ) -> "HAClient":
        session = requests.Session()

        resp = session.post(
            f"{base_url}/api/onboarding/users",
            json={
                "name": name,
                "username": username,
                "password": password,
                "client_id": ONBOARDING_CLIENT_ID,
                "language": "en",
            },
        )
        resp.raise_for_status()
        auth_code = resp.json()["auth_code"]

        resp = session.post(
            f"{base_url}/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": ONBOARDING_CLIENT_ID,
            },
        )
        resp.raise_for_status()
        access_token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        session.post(
            f"{base_url}/api/onboarding/core_config", headers=headers
        ).raise_for_status()
        session.post(
            f"{base_url}/api/onboarding/analytics", headers=headers
        ).raise_for_status()
        session.post(
            f"{base_url}/api/onboarding/integration",
            headers=headers,
            json={
                "client_id": ONBOARDING_CLIENT_ID,
                "redirect_uri": ONBOARDING_CLIENT_ID,
            },
        ).raise_for_status()

        ws_url = base_url.replace("http://", "ws://") + "/api/websocket"
        ws = ws_connect(ws_url)
        ws.recv()
        ws.send(json.dumps({"type": "auth", "access_token": access_token}))
        auth_result = json.loads(ws.recv())
        if auth_result["type"] != "auth_ok":
            raise RuntimeError(f"websocket auth failed: {auth_result}")

        return cls(base_url=base_url, access_token=access_token, ws=ws)

    def call(self, **command: object) -> dict:
        msg_id = next(self._ids)
        self._ws.send(json.dumps({"id": msg_id, **command}))
        while True:
            result = json.loads(self._ws.recv())
            if result.get("id") != msg_id:
                continue
            if not result.get("success", True):
                raise RuntimeError(f"command failed: {result}")
            return result

    def close(self) -> None:
        self._ws.close()
