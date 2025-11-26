from django.contrib import admin, messages

from .api import FastlyAPIError, get_fastly_client
from .models import FastlyConfig, PurgeLog, EdgeModuleCors


@admin.register(FastlyConfig)
class FastlyConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "General",
            {
                "fields": (
                    "enabled",
                    "api_token",
                    "service_id",
                    "api_endpoint",
                ),
                "description": "Configure your Fastly credentials and API endpoint.",
            },
        ),
        (
            "Advanced cache settings",
            {
                "fields": (
                    "soft_purge",
                    "default_ttl",
                    "cache_ttl",
                    "stale_while_revalidate",
                    "stale_if_error",
                    "allow_full_cache_purges",
                    "log_purges",
                    "debug_mode",
                    "always_purged_keys",
                ),
            },
        ),
        (
            "Webhooks",
            {
                "fields": (
                    "webhook_url",
                    "webhook_username",
                    "webhook_channel",
                    "webhook_active",
                ),
                "description": "Optional webhook (e.g. Slack) notifications for purges.",
            },
        ),
    )
    actions = ["test_connection", "purge_all_cache", "validate_active_vcl"]

    def has_add_permission(self, request):
        if FastlyConfig.objects.exists():
            return False
        return super().has_add_permission(request)

    @admin.action(description="Test Fastly connection")
    def test_connection(self, request, queryset):
        config = FastlyConfig.get_solo()
        try:
            client = get_fastly_client(config)
            ok, msg = client.test_connection()
            level = messages.SUCCESS if ok else messages.ERROR
            self.message_user(request, msg, level=level)
        except FastlyAPIError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)

    @admin.action(description="Purge all Fastly cache")
    def purge_all_cache(self, request, queryset):
        config = FastlyConfig.get_solo()

        if not config.allow_full_cache_purges:
            self.message_user(
                request,
                "Full cache purges are disabled. Enable 'allow_full_cache_purges' "
                "in the Advanced settings if you really want this.",
                level=messages.ERROR,
            )
            return

        try:
            client = get_fastly_client(config)
            client.purge_all(soft=config.soft_purge)
        except FastlyAPIError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        else:
            self.message_user(
                request,
                "Triggered Fastly purge-all.",
                level=messages.WARNING,
            )

    @admin.action(description="Validate active Fastly VCL")
    def validate_active_vcl(self, request, queryset):
        config = FastlyConfig.get_solo()
        try:
            client = get_fastly_client(config)
            ok, msg = client.validate_active_vcl()
            level = messages.SUCCESS if ok else messages.ERROR
            self.message_user(request, msg, level=level)
        except FastlyAPIError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        
@admin.register(PurgeLog)
class PurgeLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "method", "target", "success", "response_status")
    list_filter = ("method", "success", "response_status")
    readonly_fields = (
        "created_at",
        "method",
        "target",
        "success",
        "response_status",
        "response_body",
    )
    search_fields = ("target",)


@admin.register(EdgeModuleCors)
class EdgeModuleCorsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Edge Module",
            {
                "fields": ("enabled",),
                "description": (
                    "Configure CORS headers to be applied via Fastly VCL in a "
                    "future step. For now this stores the settings."
                ),
            },
        ),
        (
            "CORS configuration",
            {
                "fields": (
                    "allowed_origins",
                    "allowed_methods",
                    "allowed_headers",
                    "expose_headers",
                    "max_age",
                    "allow_credentials",
                )
            },
        ),
    )

    list_display = (
        "enabled",
        "allowed_origins_short",
        "max_age",
        "allow_credentials",
        "updated_at",
    )

    def allowed_origins_short(self, obj):
        value = (obj.allowed_origins or "").strip()
        if not value:
            return "(none)"
        first_line = value.splitlines()[0]
        if len(first_line) > 40:
            return first_line[:37] + "..."
        return first_line

    allowed_origins_short.short_description = "Allowed origins"
