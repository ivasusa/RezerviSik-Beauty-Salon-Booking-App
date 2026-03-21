# Jovana Simic 2022/0466

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User as DjangoUser

from appIva.models import User as LegacyUser, UserProfile, Salon, Owner, Staff


class AuthAndStaffTests_NoPayload(TestCase):
    """
    Jedinični testovi za funkcionalnosti:
    1. Registracija korisnika
    2. Autorizacija i odjava
    3. Administracija osoblja (owner)
    """
    def setUp(self):
        self.client_email = "client@test.com"
        self.client_password = "Pass12345!"

        self.dj_client = DjangoUser.objects.create_user(
            username=self.client_email,
            email=self.client_email,
            password=self.client_password,
            first_name="Client",
            last_name="Test",
        )
        self.legacy_client = LegacyUser.objects.create(
            name="Client",
            surname="Test",
            email=self.client_email,
            password="hashed",
            phone="061111111",
        )
        UserProfile.objects.create(django_user=self.dj_client, legacy_user=self.legacy_client)

        self.owner_email = "owner@test.com"
        self.owner_password = "Pass12345!"

        self.dj_owner = DjangoUser.objects.create_user(
            username=self.owner_email,
            email=self.owner_email,
            password=self.owner_password,
            first_name="Owner",
            last_name="Test",
        )
        self.legacy_owner = LegacyUser.objects.create(
            name="Owner",
            surname="Test",
            email=self.owner_email,
            password="hashed",
            phone="062222222",
        )
        UserProfile.objects.create(django_user=self.dj_owner, legacy_user=self.legacy_owner)

        self.salon = Salon.objects.create(
            name="Salon A",
            description="Opis",
            address="Adresa",
            working_hours="",
            contact="060000000",
            grade=None,
        )
        self.owner = Owner.objects.create(userid=self.legacy_owner, salonid=self.salon, verified=0)


    def test_register_client_success_creates_django_legacy_profile(self):
        """
        Registracija klijenta kreira DjangoUser + LegacyUser + UserProfile i redirectuje na home.
        """
        url = reverse("register_user")
        resp = self.client.post(url, {
            "user_type": "client",
            "name": "New",
            "surname": "Client",
            "email": "newclient@test.com",
            "password": "Pass12345!",
        })
        self.assertEqual(resp.status_code, 302)

        self.assertTrue(DjangoUser.objects.filter(username="newclient@test.com").exists())
        self.assertTrue(LegacyUser.objects.filter(email="newclient@test.com").exists())

        legacy = LegacyUser.objects.get(email="newclient@test.com")
        self.assertTrue(UserProfile.objects.filter(legacy_user=legacy).exists())

    def test_register_owner_success_creates_owner_and_salon(self):
        """
        Registracija vlasnika kreira salon + Owner i ostaje na register.html (status 200) sa porukom.
        """
        url = reverse("register_user")
        resp = self.client.post(url, {
            "user_type": "owner",
            "name": "New",
            "surname": "Owner",
            "email": "newowner@test.com",
            "password": "Pass12345!",
            "salon_name": "Salon New",
            "salon_address": "Addr",
            "salon_contact": "060111111",
            "salon_description": "Opis",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(DjangoUser.objects.filter(username="newowner@test.com").exists())
        self.assertTrue(LegacyUser.objects.filter(email="newowner@test.com").exists())

        legacy = LegacyUser.objects.get(email="newowner@test.com")
        self.assertTrue(Owner.objects.filter(userid=legacy).exists())
        self.assertEqual(Owner.objects.get(userid=legacy).salonid.name, "Salon New")

    def test_register_duplicate_email_shows_message(self):
        """
        Registracija sa postojećim email-om mora vratiti register stranicu sa porukom o grešci.
        """
        url = reverse("register_user")
        resp = self.client.post(url, {
            "user_type": "client",
            "name": "X",
            "surname": "Y",
            "email": self.client_email,
            "password": "Pass12345!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nalog sa ovom email adresom")


    def test_login_client_redirects_to_client_profile(self):
        """
        Login klijenta vodi na klijent_moj_profil.
        """
        url = reverse("login_user")
        resp = self.client.post(url, {
            "email": self.client_email,
            "password": self.client_password,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("klijent_moj_profil"), resp["Location"])

    def test_login_wrong_password_shows_error(self):
        """
        Pogrešna lozinka mora prikazati poruku greške na login stranici.
        """
        url = reverse("login_user")
        resp = self.client.post(url, {
            "email": self.client_email,
            "password": "WRONGPASS",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pogrešan email ili lozinka")

    def test_logout_redirects_home(self):
        """
        Logout vraća redirect na home.
        """
        self.client.login(username=self.client_email, password=self.client_password)
        resp = self.client.get(reverse("logout_user"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("home"), resp["Location"])


    def test_add_staff_requires_login(self):
        """
        add_staff je @login_required -> kada nije ulogovan mora da redirectuje na login.
        """
        resp = self.client.post(reverse("add_staff"), {})
        self.assertEqual(resp.status_code, 302)

    def test_add_staff_as_owner_success_creates_staff(self):
        """
        Owner može dodati osoblje:
        kreira DjangoUser + LegacyUser + UserProfile + Staff i vraća success JSON.
        """
        self.client.login(username=self.owner_email, password=self.owner_password)

        resp = self.client.post(reverse("add_staff"), {
            "name": "Staff",
            "surname": "User",
            "email": "staff@test.com",
            "password": "Pass12345!",
        })
        self.assertEqual(resp.status_code, 200)

        # JSON provera (string containment je dovoljno robustan)
        self.assertIn(b'"status": "success"', resp.content)

        self.assertTrue(DjangoUser.objects.filter(username="staff@test.com").exists())
        self.assertTrue(LegacyUser.objects.filter(email="staff@test.com").exists())
        legacy_staff = LegacyUser.objects.get(email="staff@test.com")

        self.assertTrue(UserProfile.objects.filter(legacy_user=legacy_staff).exists())
        self.assertTrue(Staff.objects.filter(userid=legacy_staff, salonid=self.salon).exists())

    def test_add_staff_duplicate_email_returns_error_json(self):
        """
        Ako je email već registrovan kao DjangoUser -> vraća error JSON.
        """
        self.client.login(username=self.owner_email, password=self.owner_password)

        DjangoUser.objects.create_user(
            username="dup@test.com",
            email="dup@test.com",
            password="Pass12345!",
        )

        resp = self.client.post(reverse("add_staff"), {
            "name": "X",
            "surname": "Y",
            "email": "dup@test.com",
            "password": "Pass12345!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'"status": "error"', resp.content)

    def test_delete_staff_success(self):
        """
        Owner briše zaposlene:
        briše Staff + associated DjangoUser + LegacyUser.
        """
        # napravi staff korisnika
        dj_staff = DjangoUser.objects.create_user(
            username="delstaff@test.com",
            email="delstaff@test.com",
            password="Pass12345!",
            first_name="Del",
            last_name="Staff",
        )
        legacy_staff = LegacyUser.objects.create(
            name="Del",
            surname="Staff",
            email="delstaff@test.com",
            password="hashed",
            phone="",
        )
        UserProfile.objects.create(django_user=dj_staff, legacy_user=legacy_staff)
        staff = Staff.objects.create(userid=legacy_staff, salonid=self.salon, position="osoblje")

        self.client.login(username=self.owner_email, password=self.owner_password)

        resp = self.client.get(reverse("delete_staff", kwargs={"staff_id": staff.staffid}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'"status": "success"', resp.content)

        self.assertFalse(Staff.objects.filter(staffid=staff.staffid).exists())
        self.assertFalse(LegacyUser.objects.filter(email="delstaff@test.com").exists())
        self.assertFalse(DjangoUser.objects.filter(username="delstaff@test.com").exists())

    def test_delete_staff_not_found(self):
        """
        Brisanje nepostojećeg staff_id vraća error JSON.
        """
        self.client.login(username=self.owner_email, password=self.owner_password)

        resp = self.client.get(reverse("delete_staff", kwargs={"staff_id": 999999}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'"status": "error"', resp.content)