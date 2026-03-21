#Maša Avramović
from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta, time

from appIva.models import User, Staff, Service, Salon, Appointment
from appSandra.services.notifications import send_daily_reminders
from appSandra.views import STATUS_BOOKED


class SandraCalendarStatsTests(TestCase):
    """
    Test klasa za proveru funkcionalnosti statistike salona,
    kalendarskog prikaza termina i sistema podsetnika.

    U okviru testova proverava se:
    - broj zakazanih termina u salonu
    - ukupna zarada na osnovu cena usluga
    - postojanje termina u kalendaru za određeni dan i mesec
    - ispravnost funkcije za slanje dnevnih podsetnika
    - da li je termin postavljen u budućnosti
    """

    def setUp(self):
        """
        Kreiranje test podataka potrebnih za sve testove.

        Postavljaju se:
        - jedan salon
        - jedan korisnik (klijent)
        - jedan zaposleni
        - jedna usluga
        - jedan termin zakazan za sutra

        Ovi podaci se koriste u svim testovima kako bi se
        proverila logika statistike, kalendara i podsetnika.
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
        datetime.combine(tomorrow, time(10, 0))
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
        Proverava da li sistem pravilno računa broj zakazanih
        termina u određenom salonu.
        """

        count = Appointment.objects.filter(
        staffid__salonid=self.salon,
        status=STATUS_BOOKED
        ).count()

        self.assertEqual(count, 1)

    def test_statistics_total_earnings(self):
        """
        Proverava da li se ukupna zarada salona pravilno
        računa na osnovu cena usluga zakazanih termina.
        """

        total = Appointment.objects.filter(
        staffid__salonid=self.salon,
        status=STATUS_BOOKED
        ).aggregate(total=Sum("serviceid__price"))["total"]

        self.assertEqual(total, 1000)

    def test_calendar_day_has_appointment(self):
        """
        Proverava da li kalendar prepoznaje da postoji
        zakazan termin za određeni dan.
        """
        day = self.appointment_time.date()

        start = timezone.make_aware(datetime.combine(day, time.min))
        end = start + timedelta(days=1)

        exists = Appointment.objects.filter(
        staffid__salonid=self.salon,
        datetime__gte=start,
        datetime__lt=end
        ).exists()

        self.assertTrue(exists)

    def test_calendar_month_appointments(self):
        """
        Proverava da li sistem pronalazi termine
        u okviru odgovarajućeg meseca.
        """
        day = self.appointment_time.date()

        start = timezone.make_aware(datetime(day.year, day.month, 1, 0, 0))

        if day.month == 12:
            end = timezone.make_aware(datetime(day.year + 1, 1, 1, 0, 0))
        else:
            end = timezone.make_aware(datetime(day.year, day.month + 1, 1, 0, 0))

        appointments = Appointment.objects.filter(
        staffid__salonid=self.salon,
        datetime__gte=start,
        datetime__lt=end
        )

        self.assertEqual(appointments.count(), 1)

    def test_send_daily_reminders_returns_number(self):
        """
        Proverava da funkcija za slanje dnevnih podsetnika
        vraća broj poslatih podsetnika.
        """

        sent = send_daily_reminders()
        self.assertIsInstance(sent, int)

    def test_reminder_for_tomorrow_exists(self):
        """
        Proverava da postoji termin zakazan za sutrašnji dan,
        što predstavlja osnov za slanje podsetnika korisniku.
        """
        tomorrow = timezone.localdate() + timedelta(days=1)

        start = timezone.make_aware(datetime.combine(tomorrow, time.min))
        end = start + timedelta(days=1)

        reminders = Appointment.objects.filter(
        datetime__gte=start,
        datetime__lt=end,
        status=STATUS_BOOKED
        )

        self.assertEqual(reminders.count(), 1)

    def test_future_appointment(self):
        """
        Proverava da li je termin zakazan u budućnosti.
        """
        self.assertGreater(self.appointment.datetime, timezone.now())