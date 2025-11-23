import logging
from typing import Tuple

import requests

from .conf import get_setting
from .models import PurgeLog, FastlyConfig

logger = logging.getLogger(__name__)


class FastlyAPIError(Exception):
    pass


class FastlyClient:
    def __init__(self, api_token: str, service_id: str, base_url: str | None = None):
        self.api_token = api_token
        self.service_id = service_id
        self.base_url = base_url or get_setting("API_URL")

    def _headers(self) -> dict:
        return {
            "Fastly-Key": self.api_token,
            "Accept": "application/json",
        }

    def test_connection(self) -> Tuple[bool, str]:
        url = f"{self.base_url}/service/{self.service_id}"
        resp = requests.get(url, headers=self._headers(), timeout=5)
        if resp.ok:
            data = resp.json()
            name = data.get("name") or "Unknown"
            return True, f"Connection OK. Service name: {name}"
        return False, f"Fastly API error ({resp.status_code}): {resp.text}"

    def purge_all(self, soft: bool = True) -> None:
        url = f"{self.base_url}/service/{self.service_id}/purge_all"
        headers = self._headers()
        if soft:
            headers["Fastly-Soft-Purge"] = "1"
        resp = requests.post(url, headers=headers, timeout=10)

        PurgeLog.objects.create(
            method=PurgeLog.METHOD_ALL,
            target="*",
            success=resp.ok,
            response_status=resp.status_code,
            response_body=resp.text[:4000],
        )

        if not resp.ok:
            raise FastlyAPIError(f"Purge all failed ({resp.status_code})")

    def purge_key(self, key: str, soft: bool = True) -> None:
        url = f"{self.base_url}/service/{self.service_id}/purge"
        headers = self._headers()
        if soft:
            headers["Fastly-Soft-Purge"] = "1"

        payload = {"surrogate_keys": [key]}
        resp = requests.post(url, json=payload, headers=headers, timeout=10)

        PurgeLog.objects.create(
            method=PurgeLog.METHOD_KEY,
            target=key,
            success=resp.ok,
            response_status=resp.status_code,
            response_body=resp.text[:4000],
        )

        if not resp.ok:
            raise FastlyAPIError(f"Purge key '{key}' failed ({resp.status_code})")

    def purge_url_path(self, path: str, soft: bool = True) -> None:
        url = f"{self.base_url}/purge/{path.lstrip('/')}"
        headers = self._headers()
        if soft:
            headers["Fastly-Soft-Purge"] = "1"

        resp = requests.post(url, headers=headers, timeout=10)

        PurgeLog.objects.create(
            method=PurgeLog.METHOD_URL,
            target=path,
            success=resp.ok,
            response_status=resp.status_code,
            response_body=resp.text[:4000],
        )

        if not resp.ok:
            raise FastlyAPIError(f"Purge URL '{path}' failed ({resp.status_code})")


def get_fastly_client(config: FastlyConfig | None = None) -> FastlyClient:
    if config is None:
        config = FastlyConfig.get_solo()
    if not (config.enabled and config.api_token and config.service_id):
        raise FastlyAPIError("Fastly is not configured (missing token, service ID, or disabled).")
    return FastlyClient(config.api_token, config.service_id)
