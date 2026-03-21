# appSandra/tests.py
# Autor: Maša Avramović, [22/0134]
# Opis: Testovi za kalendar, statistiku i notifikacije u aplikaciji appSandra.

from datetime import datetime, time, timedelta

from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone

from appIva.models import Appointment, Salon, Service, Staff, User
from appSandra.services.notifications import send_daily_reminders
from appSandra.views import STATUS_BOOKED


class SandraCalendarStatsTests(TestCase):
    """
    Test klasa za proveru funkcionalnosti kalendara, statistike i notifikacija
    u okviru aplikacije appSandra.
    """

    def setUp(self):
        """
        Inicijalizuje test podatke potrebne za izvršavanje testova.

        Kreira salon, korisnika, zaposlenog, uslugu i jedan zakazan termin
        za sutrašnji datum u 12:00.
        """

        self.salon = Salon.objects.create(
            name="Test Salon",
            address="Test Ulica",
            working_hours="09-17",
            contact="061111111"
        )

        self.user = User.objects.create(
            name="Petar",
            surname="Petrovic",
            email="petar@test.com",
            password="1234",
            phone="061123456"
        )

        self.staff_user = User.objects.create(
            name="Ana",
            surname="Markovic",
            email="ana@test.com",
            password="1234",
            phone="061999999"
        )

        self.staff = Staff.objects.create(
            userid=self.staff_user,
            salonid=self.salon,
            position="Frizer"
        )

        self.service = Service.objects.create(
            name="Šišanje",
            price=1000,
            duration=60,
            salonid=self.salon,
            category="Frizura",
            is_active=True
        )

        tomorrow = timezone.localdate() + timedelta(days=1)

        self.appointment_time = timezone.make_aware(
            datetime.combine(tomorrow, time(12, 0))
        )

        self.appointment = Appointment.objects.create(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=self.appointment_time,
            status=STATUS_BOOKED
        )

    def test_statistics_number_of_appointments(self):
        """
        Proverava broj zakazanih termina u salonu.
        """

        count = Appointment.objects.filter(
            staffid__salonid=self.salon,
            status=STATUS_BOOKED
        ).count()

        self.assertEqual(count, 1)

    def test_statistics_total_earnings(self):
        """
        Proverava ukupnu zaradu salona na osnovu zakazanih termina.
        """

        total = Appointment.objects.filter(
            staffid__salonid=self.salon,
            status=STATUS_BOOKED
        ).aggregate(total=Sum("serviceid__price"))["total"]

        self.assertEqual(total, 1000)

    def test_calendar_day_has_appointment(self):
        """
        Proverava da li za određeni dan postoji zakazan termin.
        """

        day = timezone.localdate(self.appointment_time)

        day_start = timezone.make_aware(datetime.combine(day, time.min))
        day_end = day_start + timedelta(days=1)

        exists = Appointment.objects.filter(
            staffid__salonid=self.salon,
            datetime__gte=day_start,
            datetime__lt=day_end
        ).exists()

        self.assertTrue(exists)

    def test_calendar_month_appointments(self):
        """
        Proverava da li u datom mesecu postoje zakazani termini.
        """

        local_dt = timezone.localtime(self.appointment_time)

        month_start = timezone.make_aware(
            datetime(local_dt.year, local_dt.month, 1, 0, 0, 0)
        )

        if local_dt.month == 12:
            next_month_start = timezone.make_aware(
                datetime(local_dt.year + 1, 1, 1, 0, 0, 0)
            )
        else:
            next_month_start = timezone.make_aware(
                datetime(local_dt.year, local_dt.month + 1, 1, 0, 0, 0)
            )

        appointments = Appointment.objects.filter(
            staffid__salonid=self.salon,
            datetime__gte=month_start,
            datetime__lt=next_month_start
        )

        self.assertEqual(appointments.count(), 1)

    def test_send_daily_reminders_returns_number(self):
        """
        Proverava da funkcija za slanje dnevnih podsetnika vraća broj poslatih
        podsetnika.
        """

        sent = send_daily_reminders()

        self.assertIsInstance(sent, int)

    def test_reminder_for_tomorrow_exists(self):
        """
        Proverava da postoji zakazan termin za sutrašnji datum.
        """

        tomorrow = timezone.localdate() + timedelta(days=1)

        day_start = timezone.make_aware(datetime.combine(tomorrow, time.min))
        day_end = day_start + timedelta(days=1)

        reminders = Appointment.objects.filter(
            datetime__gte=day_start,
            datetime__lt=day_end,
            status=STATUS_BOOKED
        )

        self.assertEqual(reminders.count(), 1)

    def test_future_appointment(self):
        """
        Proverava da je kreirani termin zakazan u budućnosti.
        """

        self.assertGreater(self.appointment.datetime, timezone.now())