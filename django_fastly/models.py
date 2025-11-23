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

    soft_purge = models.BooleanField(
        default=True,
        help_text=_("Use Fastly Soft Purge by default."),
    )

    default_ttl = models.PositiveIntegerField(
        default=300,
        help_text=_("Surrogate-Control max-age (seconds)."),
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

    always_purged_keys = models.TextField(
        blank=True,
        help_text=_("One surrogate key per line to always purge with blog posts."),
    )

    webhook_url = models.URLField(
        blank=True,
        null=True,
        help_text=_("Optional webhook URL (e.g. Slack) to log purges."),
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
