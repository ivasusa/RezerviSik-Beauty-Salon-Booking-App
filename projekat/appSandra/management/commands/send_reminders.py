from django.core.management.base import BaseCommand
from appSandra.services.notifications import send_daily_reminders

class Command(BaseCommand):
    help = "Šalje MOCK podsetnike za sutrašnje termine"

    def handle(self, *args, **options):
        sent = send_daily_reminders()
        self.stdout.write(self.style.SUCCESS(f"Podsetnici poslati: {sent}"))
