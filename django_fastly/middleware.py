# django_fastly/middleware.py
import logging
import re

from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

from .models import FastlyConfig, EdgeModuleCors
from .utils import build_surrogate_keys_for_instance

logger = logging.getLogger(__name__)


class FastlySurrogateKeyMiddleware(MiddlewareMixin):
    # ... your existing code unchanged ...
    def process_template_response(self, request, response):
        context = getattr(response, "context_data", None)
        if not context:
            return response

        obj = None
        for key in ("object", "post"):
            if key in context:
                obj = context[key]
                break

        if obj is None:
            return response

        config = FastlyConfig.get_solo()
        if not config.enabled:
            return response

        keys = build_surrogate_keys_for_instance(obj)
        if keys:
            response["Surrogate-Key"] = " ".join(keys)

        if config.default_ttl:
            parts = [f"max-age={config.default_ttl}"]
            if config.stale_while_revalidate:
                parts.append(f"stale-while-revalidate={config.stale_while_revalidate}")
            if config.stale_if_error:
                parts.append(f"stale-if-error={config.stale_if_error}")
            response["Surrogate-Control"] = ", ".join(parts)

        cache_ttl = config.cache_ttl or config.default_ttl
        if cache_ttl:
            response.setdefault("Cache-Control", f"public, max-age={cache_ttl}")

        return response


class FastlyCorsEdgeModuleMiddleware(MiddlewareMixin):
    """
    Apply CORS headers using the EdgeModuleCors config.

    This mirrors the WP Edge Module behavior:
    - Only acts if req Origin is present.
    - Only sets headers if they aren't already set.
    - Supports "anyone" and "regex-match" origin modes.
    """

    def process_response(self, request, response):
        module = EdgeModuleCors.get_solo()

        if not module.enabled:
            return response

        origin = request.META.get("HTTP_ORIGIN")
        if not origin:
            return response

        # If CORS headers already present, don't touch them
        if (
            response.has_header("Access-Control-Allow-Origin")
            or response.has_header("Access-Control-Allow-Methods")
            or response.has_header("Access-Control-Allow-Headers")
        ):
            return response

        allowed_origin = None

        # origin == "anyone"
        if module.origin_mode == EdgeModuleCors.ORIGIN_ANYONE:
            allowed_origin = "*"

        # origin == "regex-match"
        elif (
            module.origin_mode == EdgeModuleCors.ORIGIN_REGEX
            and module.allowed_origins_regex
        ):
            pattern = rf"^https?://{module.allowed_origins_regex}"
            try:
                if re.match(pattern, origin):
                    allowed_origin = origin
            except re.error:
                logger.exception(
                    "Invalid CORS allowed_origins_regex: %s",
                    module.allowed_origins_regex,
                )
                # If regex is invalid, we just skip setting CORS

        # If we still don't have an allowed origin, do nothing.
        if not allowed_origin:
            return response

        # Now apply headers
        response["Access-Control-Allow-Origin"] = allowed_origin

        if module.allowed_methods:
            response["Access-Control-Allow-Methods"] = module.allowed_methods

        if module.allowed_headers:
            response["Access-Control-Allow-Headers"] = module.allowed_headers

        # VCL: set resp.http.Vary:Origin = "";
        # Django equivalent: ensure "Origin" is in Vary
        patch_vary_headers(response, ["Origin"])

        return response
