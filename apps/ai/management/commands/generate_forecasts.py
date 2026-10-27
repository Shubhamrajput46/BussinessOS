from django.core.management.base import BaseCommand

from apps.ai.services import generate_forecast
from apps.organizations.models import Organisation


class Command(BaseCommand):
    help = "Generate sales forecasts for every active organisation (run it daily from cron / CI)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        for organisation in Organisation.objects.filter(is_active=True):
            created = generate_forecast(organisation, days=options["days"])
            self.stdout.write(f"{organisation.name}: {len(created)} forecast rows")
