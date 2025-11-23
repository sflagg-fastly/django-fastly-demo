from django.utils.deprecation import MiddlewareMixin

from .models import FastlyConfig
from .utils import build_surrogate_keys_for_instance


class FastlySurrogateKeyMiddleware(MiddlewareMixin):
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

        response.setdefault("Cache-Control", f"public, max-age={config.default_ttl}")

        return response
