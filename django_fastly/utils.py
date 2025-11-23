from __future__ import annotations

from typing import Iterable, Set

from django.core.exceptions import ImproperlyConfigured

from .api import get_fastly_client, FastlyAPIError
from .models import FastlyConfig


def build_surrogate_keys_for_instance(instance) -> list[str]:
    config = FastlyConfig.get_solo()

    keys: Set[str] = set()
    model = type(instance)
    label = model._meta.label_lower
    keys.add(label)

    pk = getattr(instance, "pk", None)
    if pk:
        keys.add(f"{label}:{pk}")

    slug = getattr(instance, "slug", None)
    if slug:
        keys.add(f"{label}:slug:{slug}")

    for line in (config.always_purged_keys or "").splitlines():
        line = line.strip()
        if line:
            keys.add(line)

    return sorted(keys)


def purge_instance(instance, use_keys: bool = True, use_url: bool = True) -> None:
    config = FastlyConfig.get_solo()
    if not config.enabled:
        return

    try:
        client = get_fastly_client(config)
    except FastlyAPIError:
        return

    soft = config.soft_purge
    last_error: Exception | None = None

    if use_keys:
        for key in build_surrogate_keys_for_instance(instance):
            try:
                client.purge_key(key, soft=soft)
            except Exception as exc:  # noqa: BLE001
                last_error = exc

    if use_url:
        if not hasattr(instance, "get_absolute_url"):
            raise ImproperlyConfigured(
                f"{instance.__class__.__name__} must implement get_absolute_url() "
                "for URL purging to work."
            )
        try:
            path = instance.get_absolute_url()
            client.purge_url_path(path, soft=soft)
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error:
        raise last_error
