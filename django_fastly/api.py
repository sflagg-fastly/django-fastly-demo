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

    def validate_version(self, version: int) -> tuple[bool, str]:
        """
        Validate a specific Fastly service version.
        """
        url = f"{self.base_url}/service/{self.service_id}/version/{version}/validate"
        if self.config.debug_mode:
            logger.debug("Validating Fastly VCL version %s: %s", version, url)

        resp = requests.get(url, headers=self._headers(), timeout=10)
        if resp.ok:
            return True, (
                f"Fastly VCL for service {self.service_id} "
                f"version {version} is valid."
            )

        return False, (
            f"Fastly VCL validation failed for service {self.service_id} "
            f"version {version} ({resp.status_code}): {resp.text}"
        )

    def validate_active_vcl(self) -> tuple[bool, str]:
        """
        Convenience helper that validates the active version.
        """
        version = self._get_active_version_number()
        return self.validate_version(version)

    def _clone_version(self, version: int) -> int:
        """
        Clone a Fastly service version and return the new version number.
        Mirrors the Fastly 'version.clone' endpoint.
        """
        url = f"{self.base_url}/service/{self.service_id}/version/{version}/clone"
        if self.config.debug_mode:
            logger.debug("Cloning Fastly service %s version %s: %s", self.service_id, version, url)

        resp = requests.put(url, headers=self._headers(), timeout=10)
        if not resp.ok:
            raise FastlyAPIError(
                f"Failed to clone service version {version} "
                f"({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        try:
            new_version = int(data["number"])
        except (KeyError, ValueError, TypeError):
            raise FastlyAPIError(
                f"Clone succeeded but response did not include a valid version number: {data}"
            )

        return new_version

    def apply_cors_vcl(self, cors_module, autoclone: bool = True, activate: bool = False) -> tuple[int, bool]:
        """
        Render and apply the CORS Edge Module as a Fastly VCL snippet.

        Steps:
        - Require the module to be enabled.
        - Clone the active version (by default) to get an editable version.
        - Upsert a 'deliver' snippet named 'cors_headers' with rendered content.
        - Validate the new version.
        - Optionally activate it.

        Returns (version_number, activated_flag).
        """
        if not getattr(cors_module, "enabled", False):
            raise FastlyAPIError(
                "CORS Edge Module is disabled; enable it before applying VCL."
            )

        # Determine base version (active) and clone if requested.
        active_version = self._get_active_version_number()
        target_version = active_version

        if autoclone:
            target_version = self._clone_version(active_version)

        # Render VCL snippet from the module
        try:
            content = cors_module.render_vcl_snippet()
        except Exception as exc:
            raise FastlyAPIError(f"Failed to render CORS VCL snippet: {exc}") from exc

        snippet_name = "cors_headers"
        headers = self._headers()
        snippet_base = f"{self.base_url}/service/{self.service_id}/version/{target_version}/snippet"
        get_url = f"{snippet_base}/{snippet_name}"

        # Check if snippet already exists
        if self.config.debug_mode:
            logger.debug(
                "Checking for existing CORS snippet '%s' on version %s: %s",
                snippet_name,
                target_version,
                get_url,
            )

        resp = requests.get(get_url, headers=headers, timeout=10)

        payload = {
            "type": "deliver",
            "priority": "100",
            "content": content,
        }

        if resp.status_code == 404:
            # Create new snippet
            if self.config.debug_mode:
                logger.debug(
                    "Creating new CORS snippet '%s' on version %s",
                    snippet_name,
                    target_version,
                )

            payload["name"] = snippet_name
            create_url = snippet_base
            resp = requests.post(
                create_url, headers=headers, data=payload, timeout=10
            )
        elif resp.ok:
            # Update existing snippet
            if self.config.debug_mode:
                logger.debug(
                    "Updating existing CORS snippet '%s' on version %s",
                    snippet_name,
                    target_version,
                )

            update_url = get_url
            resp = requests.put(
                update_url, headers=headers, data=payload, timeout=10
            )
        else:
            raise FastlyAPIError(
                f"Failed to check existing CORS snippet ({resp.status_code}): {resp.text}"
            )

        if not resp.ok:
            raise FastlyAPIError(
                f"Failed to create/update CORS VCL snippet ({resp.status_code}): {resp.text}"
            )

        # Validate the target version
        ok, msg = self.validate_version(target_version)
        if not ok:
            raise FastlyAPIError(
                f"Fastly reported validation error for version {target_version}: {msg}"
            )

        activated = False
        if activate:
            activate_url = f"{self.base_url}/service/{self.service_id}/version/{target_version}/activate"
            if self.config.debug_mode:
                logger.debug("Activating version %s: %s", target_version, activate_url)

            resp = requests.put(activate_url, headers=headers, timeout=10)
            if not resp.ok:
                raise FastlyAPIError(
                    f"Failed to activate version {target_version} "
                    f"({resp.status_code}): {resp.text}"
                )
            activated = True

        return target_version, activated


def get_fastly_client(config: FastlyConfig | None = None) -> FastlyClient:
    if config is None:
        config = FastlyConfig.get_solo()
    if not (config.enabled and config.api_token and config.service_id):
        raise FastlyAPIError("Fastly is not configured (missing token, service ID, or disabled).")
    return FastlyClient(config)
