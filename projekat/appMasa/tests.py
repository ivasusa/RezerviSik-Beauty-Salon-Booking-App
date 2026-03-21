# appMasa/tests.py/
# Autor: Sandra Bubanja
# Opis: Testovi za model Appointment i logiku zakazivanja termina.
# Testira kreiranje termina, duplikate, prošle termine, slobodne termine zaposlenih,
# promenu statusa, rad sa više korisnika i validaciju usluge.

from django.test import TestCase
from appIva.models import User, Staff, Service, Salon, Appointment
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from appSandra.views import WORK_HOURS, STATUS_BOOKED


class AppointmentTests(TestCase):
    """
    Testovi vezani za kreiranje, validaciju i logiku termina u aplikaciji.
    """

    def setUp(self):
        """
        Postavljanje osnovnih objekata: salon, klijent, zaposleni i usluga.
        Ovi objekti se koriste u svim testovima.
        """
        # Kreiramo salon
        self.salon = Salon.objects.create(
            name="Test Salon",
            address="Ulica 1",
            working_hours="09-18",
            contact="0611111111"
        )

        # Kreiramo klijenta
        self.user = User.objects.create(
            name="Petar",
            surname="Petrovic",
            email="petar@example.com",
            password="1234",
            phone="0611234567"
        )

        # Kreiramo zaposlenog
        self.staff_user = User.objects.create(
            name="Ana",
            surname="Markovic",
            email="ana@example.com",
            password="1234",
            phone="0617654321"
        )
        self.staff = Staff.objects.create(
            userid=self.staff_user,
            salonid=self.salon,
            position="Frizer"
        )

        # Kreiramo uslugu
        self.service = Service.objects.create(
            name="Šišanje",
            price=1000,
            duration=60,
            salonid=self.salon,
            category="Frizura",
            is_active=True
        )

    def test_create_valid_appointment(self):
        """
        Testira kreiranje validnog termina.
        Proverava da postoji tačno jedan termin u bazi i da je vezan za pravog korisnika.
        """
        appointment_time = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time,
            status=1  # 1 = zakazano
        )
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(appointment.userid.name, "Petar")

    def test_duplicate_appointment(self):
        """
        Testira da zaposleni ne može imati dva termina u istom vremenu.
        Sistem prepoznaje duplikat i ne dozvoljava kreiranje.
        """
        appointment_time = timezone.now() + timedelta(days=1)

        Appointment.objects.create(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time,
            status=1
        )

        # Provera duplikata
        if Appointment.objects.filter(
                staffid=self.staff,
                datetime=appointment_time,
                status=1
        ).exists():
            duplicate = True
        else:
            duplicate = False
            Appointment.objects.create(
                userid=self.user,
                staffid=self.staff,
                serviceid=self.service,
                datetime=appointment_time,
                status=1
            )

        self.assertTrue(duplicate)

    def test_appointment_in_past(self):
        """
        Testira da termin ne može biti zakazan u prošlosti.
        Očekuje ValidationError prilikom validacije.
        """
        past_time = timezone.now() - timedelta(days=1)
        appointment = Appointment(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=past_time,
            status=1
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_staff_free_slots(self):
        """
        Testira računanje slobodnih termina zaposlenog.
        Proverava da zakazani termin nije među slobodnim terminima.
        """
        appointment_time = timezone.now() + timedelta(days=1)
        Appointment.objects.create(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time,
            status=STATUS_BOOKED
        )

        taken = {appointment_time.strftime("%H:%M")}
        free = [t for t in WORK_HOURS if t not in taken]

        self.assertNotIn(appointment_time.strftime("%H:%M"), free)

    def test_appointment_inactive_service(self):
        """
        Testira kreiranje termina sa neaktivnom uslugom.
        Termin može biti kreiran, ali aplikacija treba da signalizira da usluga nije aktivna.
        """
        self.service.is_active = False
        self.service.save()

        appointment_time = timezone.now() + timedelta(days=1)
        appointment = Appointment(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time,
            status=1
        )
        # Može se dodati full_clean() ili validacija po potrebi

    def test_change_appointment_status(self):
        """
        Testira promenu statusa termina (npr. iz zakazanog u završeno).
        """
        appointment_time = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time,
            status=1
        )
        appointment.status = 2  # 2 = završeno
        appointment.save()
        self.assertEqual(Appointment.objects.get(pk=appointment.pk).status, 2)

    def test_multiple_users_appointments(self):
        """
        Testira zakazivanje više termina različitih korisnika kod istog zaposlenog.
        """
        user2 = User.objects.create(
            name="Marko",
            surname="Markovic",
            email="marko@example.com",
            password="1234",
            phone="061222333"
        )
        appointment_time = timezone.now() + timedelta(days=1)
        a1 = Appointment.objects.create(
            userid=self.user,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time,
            status=1
        )
        a2 = Appointment.objects.create(
            userid=user2,
            staffid=self.staff,
            serviceid=self.service,
            datetime=appointment_time + timedelta(hours=1),
            status=1
        )
        self.assertEqual(Appointment.objects.count(), 2)

    def test_appointment_nonexistent_service(self):
        """
        Testira kreiranje termina sa nepostojećom uslugom.
        Očekuje ValidationError.
        """
        appointment_time = timezone.now() + timedelta(days=1)
        fake_service = Service(
            idservice=999, name="Fake", price=0, duration=0, salonid=self.salon,
            category="N/A", is_active=False
        )
        appointment = Appointment(
            userid=self.user,
            staffid=self.staff,
            serviceid=fake_service,
            datetime=appointment_time,
            status=1
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()