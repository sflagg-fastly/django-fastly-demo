from django.db import models
from django.utils.translation import gettext_lazy as _


class FastlyConfig(models.Model):
    api_token = models.CharField(
        max_length=255,
        verbose_name=_("API token"),
        help_text=_("Fastly API token with Global access."),
        blank=True,
    )
    service_id = models.CharField(
        max_length=64,
        verbose_name=_("Service ID"),
        help_text=_("Fastly service ID to control."),
        blank=True,
    )
    enabled = models.BooleanField(default=True)

    # NEW: overrideable API endpoint
    api_endpoint = models.URLField(
        max_length=255,
        blank=True,
        help_text=_(
            "Optional Fastly API endpoint override. "
            "Leave blank to use the default https://api.fastly.com."
        ),
    )

    soft_purge = models.BooleanField(
        default=True,
        help_text=_("Use Fastly Soft Purge by default."),
    )

    # Surrogate TTL (matches “Surrogate Cache TTL”)
    default_ttl = models.PositiveIntegerField(
        default=300,
        help_text=_("Surrogate-Control max-age (seconds)."),
    )

    # NEW: separate cache TTL for Cache-Control (matches “Cache TTL”)
    cache_ttl = models.PositiveIntegerField(
        default=300,
        help_text=_("Cache-Control max-age (seconds)."),
    )

    stale_while_revalidate = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text=_("stale-while-revalidate (seconds, 0 = disabled)."),
    )
    stale_if_error = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text=_("stale-if-error (seconds, 0 = disabled)."),
    )

    # NEW: safety switch for purge-all
    allow_full_cache_purges = models.BooleanField(
        default=False,
        help_text=_("Allow triggering full cache purges from the Django admin."),
    )

    # NEW: toggle logging of purges
    log_purges = models.BooleanField(
        default=True,
        help_text=_("Log Fastly purge requests to the PurgeLog table."),
    )

    # NEW: debug flag
    debug_mode = models.BooleanField(
        default=False,
        help_text=_("Enable extra debug logging for Fastly API calls."),
    )

    always_purged_keys = models.TextField(
        blank=True,
        help_text=_("One surrogate key per line to always purge with blog posts."),
    )

    # Webhooks section
    webhook_url = models.URLField(
        blank=True,
        null=True,
        help_text=_("Optional webhook URL (e.g. Slack) to log purges."),
    )

    # NEW: more webhook options
    webhook_username = models.CharField(
        max_length=80,
        blank=True,
        help_text=_("Optional display name for webhook messages (e.g. Slack username)."),
    )
    webhook_channel = models.CharField(
        max_length=80,
        blank=True,
        help_text=_("Optional channel identifier, e.g. #general."),
    )
    webhook_active = models.BooleanField(
        default=False,
        help_text=_("Send purge notifications to the configured webhook."),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Fastly configuration")
        verbose_name_plural = _("Fastly configuration")

    def __str__(self) -> str:
        return "Fastly configuration"

    @classmethod
    def get_solo(cls) -> "FastlyConfig":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

class PurgeLog(models.Model):
    METHOD_URL = "url"
    METHOD_KEY = "key"
    METHOD_ALL = "all"

    METHOD_CHOICES = (
        (METHOD_URL, "URL"),
        (METHOD_KEY, "Surrogate key"),
        (METHOD_ALL, "Purge all"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=16, choices=METHOD_CHOICES)
    target = models.CharField(max_length=255, blank=True)
    success = models.BooleanField(default=False)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.method} {self.target} @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class EdgeModuleCors(models.Model):
    """
    Edge Module: CORS headers

    Inspired by the Fastly WP plugin Edge Module definition.
    """

    ORIGIN_ANYONE = "anyone"
    ORIGIN_REGEX = "regex-match"

    ORIGIN_MODE_CHOICES = [
        (ORIGIN_ANYONE, "Allow anyone (*)"),
        (ORIGIN_REGEX, "Regex matching set of origins"),
    ]

    enabled = models.BooleanField(
        default=False,
        help_text=_("Enable this Edge Module (CORS headers)."),
    )

    # Matches JSON property "origin"
    origin_mode = models.CharField(
        max_length=20,
        choices=ORIGIN_MODE_CHOICES,
        default=ORIGIN_ANYONE,
        help_text=_("What origins are allowed."),
    )

    # Matches JSON property "cors_allowed_methods"
    allowed_methods = models.CharField(
        max_length=200,
        blank=True,
        default="GET,HEAD,POST,OPTIONS",
        help_text=_(
            "Allowed HTTP methods that the requestor can use, "
            "e.g. GET,HEAD,POST,OPTIONS."
        ),
    )

    # Matches JSON property "cors_allowed_headers"
    allowed_headers = models.CharField(
        max_length=200,
        blank=True,
        help_text=_(
            "Allowed HTTP headers that the requestor can use, "
            "e.g. Content-Type, Authorization."
        ),
    )

    # Matches JSON property "cors_allowed_origins_regex"
    allowed_origins_regex = models.CharField(
        max_length=255,
        blank=True,
        help_text=_(
            "Regex matching origins that are allowed to access this service. "
            'Do not include the leading "http://" or "https://".'
        ),
    )

    # You can keep these for future expansion (not used yet in VCL-equivalent logic)
    max_age = models.PositiveIntegerField(
        default=600,
        help_text=_("Max age (in seconds) for preflight responses (not yet used)."),
    )

    allow_credentials = models.BooleanField(
        default=False,
        help_text=_(
            "Whether to send Access-Control-Allow-Credentials: true. "
            "Requires a non-* origin (not yet used in VCL-equivalent logic)."
        ),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Edge module: CORS headers")
        verbose_name_plural = _("Edge modules: CORS headers")

    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"CORS Edge Module ({status})"

    @classmethod
    def get_solo(cls) -> "EdgeModuleCors":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
