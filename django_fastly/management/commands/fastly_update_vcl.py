# django_fastly/management/commands/fastly_update_vcl.py

from django.core.management.base import BaseCommand, CommandError

from django_fastly.api import FastlyAPIError, get_fastly_client
from django_fastly.models import FastlyConfig


class Command(BaseCommand):
    help = "Validate the active Fastly VCL version for the configured service."

    def handle(self, *args, **options):
        config = FastlyConfig.get_solo()

        try:
            client = get_fastly_client(config)
        except FastlyAPIError as exc:
            raise CommandError(str(exc))

        ok, msg = client.validate_active_vcl()
        if ok:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            raise CommandError(msg)
