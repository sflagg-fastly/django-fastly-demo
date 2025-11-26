import logging
from typing import Tuple

import requests

from .conf import get_setting
from .models import PurgeLog, FastlyConfig

logger = logging.getLogger(__name__)


class FastlyAPIError(Exception):
    pass


class FastlyClient:
    def __init__(self, config: FastlyConfig):
        self.config = config
        self.api_token = config.api_token
        self.service_id = config.service_id

        # Prefer model-specific endpoint, then global FASTLY["API_URL"]
        self.base_url = (
            config.api_endpoint
            or get_setting("API_URL")
        )

    def _headers(self) -> dict:
        return {
            "Fastly-Key": self.api_token,
            "Accept": "application/json",
        }

    def _log_and_notify(self, method: str, target: str, resp: requests.Response) -> None:
        # DB logging toggle
        if self.config.log_purges:
            PurgeLog.objects.create(
                method=method,
                target=target,
                success=resp.ok,
                response_status=resp.status_code,
                response_body=resp.text[:4000],
            )

        # Optional webhook (Slack-compatible)
        if self.config.webhook_url and self.config.webhook_active:
            payload = {
                "text": f"Fastly purge {method} {target} "
                        f"{'OK' if resp.ok else 'FAILED'} ({resp.status_code})",
            }
            if self.config.webhook_username:
                payload["username"] = self.config.webhook_username
            if self.config.webhook_channel:
                payload["channel"] = self.config.webhook_channel

            try:
                requests.post(self.config.webhook_url, json=payload, timeout=5)
            except Exception:
                # Don’t break the request on webhook failure
                logger.exception("Failed to send Fastly webhook notification")

    def test_connection(self) -> Tuple[bool, str]:
        url = f"{self.base_url}/service/{self.service_id}"
        if self.config.debug_mode:
            logger.debug("Testing Fastly connection: %s", url)

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

        if self.config.debug_mode:
            logger.debug("Fastly purge_all: %s", url)

        resp = requests.post(url, headers=headers, timeout=10)
        self._log_and_notify(PurgeLog.METHOD_ALL, "*", resp)

        if not resp.ok:
            raise FastlyAPIError(f"Purge all failed ({resp.status_code})")

    def purge_key(self, key: str, soft: bool = True) -> None:
        url = f"{self.base_url}/service/{self.service_id}/purge"
        headers = self._headers()
        if soft:
            headers["Fastly-Soft-Purge"] = "1"

        if self.config.debug_mode:
            logger.debug("Fastly purge_key %s: %s", key, url)

        payload = {"surrogate_keys": [key]}
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        self._log_and_notify(PurgeLog.METHOD_KEY, key, resp)

        if not resp.ok:
            raise FastlyAPIError(f"Purge key '{key}' failed ({resp.status_code})")

    def purge_url_path(self, path: str, soft: bool = True) -> None:
        # Purge by URL path (no service prefix in this endpoint)
        url = f"{self.base_url}/purge/{path.lstrip('/')}"
        headers = self._headers()
        if soft:
            headers["Fastly-Soft-Purge"] = "1"

        if self.config.debug_mode:
            logger.debug("Fastly purge_url_path %s: %s", path, url)

        resp = requests.post(url, headers=headers, timeout=10)
        self._log_and_notify(PurgeLog.METHOD_URL, path, resp)

        if not resp.ok:
            raise FastlyAPIError(f"Purge URL '{path}' failed ({resp.status_code})")
        
        # django_fastly/api.py (inside FastlyClient)

    def _get_active_version_number(self) -> int:
        """
        Fetch the currently active version number for this service.
        """
        url = f"{self.base_url}/service/{self.service_id}"
        if self.config.debug_mode:
            logger.debug("Fetching Fastly service detail for active version: %s", url)

        resp = requests.get(url, headers=self._headers(), timeout=10)
        if not resp.ok:
            raise FastlyAPIError(
                f"Failed to fetch service details ({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        versions = data.get("versions") or []
        active = next((v for v in versions if v.get("active")), None)
        if not active:
            raise FastlyAPIError("No active Fastly version found for this service.")

        try:
            return int(active["number"])
        except (KeyError, ValueError, TypeError):
            raise FastlyAPIError("Active version number is missing or invalid.")

    def validate_active_vcl(self) -> Tuple[bool, str]:
        """
        Validate the active VCL version via the Fastly API.
        """
        version = self._get_active_version_number()
        url = f"{self.base_url}/service/{self.service_id}/version/{version}/validate"

        if self.config.debug_mode:
            logger.debug("Validating Fastly VCL: %s", url)

        resp = requests.get(url, headers=self._headers(), timeout=10)
        if resp.ok:
            # Fastly returns JSON with status info; we keep it simple.
            return True, (
                f"Fastly VCL for service {self.service_id} "
                f"version {version} is valid."
            )

        return False, (
            f"Fastly VCL validation failed for service {self.service_id} "
            f"version {version} ({resp.status_code}): {resp.text}"
        )



def get_fastly_client(config: FastlyConfig | None = None) -> FastlyClient:
    if config is None:
        config = FastlyConfig.get_solo()
    if not (config.enabled and config.api_token and config.service_id):
        raise FastlyAPIError("Fastly is not configured (missing token, service ID, or disabled).")
    return FastlyClient(config)
