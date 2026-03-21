# Autor: Sandra Bubanja

import time
from datetime import timedelta

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from django.contrib.auth.models import User as DjangoUser
from appIva.models import (
    User as LegacyUser,
    UserProfile,
    Salon,
    Owner,
    Staff,
    Service,
    Appointment,
)

PASSWORD = "TestPass123!"


class WebDriverAppMasaTests(StaticLiveServerTestCase):
    """
    Selenium integracioni testovi za upravljanje uslugama,
    rezervacijama i zakazivanje termina u sistemu.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1400,900")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, 12)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        finally:
            super().tearDownClass()

    def setUp(self):
        self.salon = Salon.objects.create(
            name="Beauty Salon",
            address="Bulevar 1",
            contact="0611111111",
            working_hours="09:00-17:00",
            description="Test beauty salon",
            grade=None,
        )

        self.owner_email = "vlasnik@test.com"

        dj_owner = DjangoUser.objects.create_user(
            username=self.owner_email,
            email=self.owner_email,
            password=PASSWORD,
            first_name="Vlasnik",
            last_name="Test",
        )

        leg_owner = LegacyUser.objects.create(
            name="Vlasnik",
            surname="Test",
            email=self.owner_email,
            password="x",
            phone="0600000001",
        )

        UserProfile.objects.create(django_user=dj_owner, legacy_user=leg_owner)
        Owner.objects.create(userid=leg_owner, salonid=self.salon, verified=1)

        self.staff_email = "osoblje@test.com"

        dj_staff = DjangoUser.objects.create_user(
            username=self.staff_email,
            email=self.staff_email,
            password=PASSWORD,
            first_name="Ana",
            last_name="Osoblje",
        )

        self.leg_staff = LegacyUser.objects.create(
            name="Ana",
            surname="Osoblje",
            email=self.staff_email,
            password="x",
            phone="0600000002",
        )

        UserProfile.objects.create(django_user=dj_staff, legacy_user=self.leg_staff)

        self.staff = Staff.objects.create(
            userid=self.leg_staff,
            salonid=self.salon,
            position="Kozmeticar",
        )

        self.client_email = "klijent@test.com"

        dj_client = DjangoUser.objects.create_user(
            username=self.client_email,
            email=self.client_email,
            password=PASSWORD,
            first_name="Marko",
            last_name="Klijent",
        )

        self.leg_client = LegacyUser.objects.create(
            name="Marko",
            surname="Klijent",
            email=self.client_email,
            password="x",
            phone="0600000003",
        )

        UserProfile.objects.create(django_user=dj_client, legacy_user=self.leg_client)

        self.service = Service.objects.create(
            name="Manikir",
            price=2000,
            duration=30,
            salonid=self.salon,
            category="Nega noktiju",
            is_active=True,
        )

    def login(self, email, password=PASSWORD):
        d = self.driver
        d.get(self.live_server_url + "/login/")
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))

        d.find_element(By.ID, "email").send_keys(email)
        d.find_element(By.ID, "password").send_keys(password)

        d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def login_owner(self):
        self.login(self.owner_email)
        self.wait.until(EC.url_contains("/owner/"))

    def login_staff(self):
        self.login(self.staff_email)
        self.wait.until(EC.url_contains("/osoblje/"))

    def login_client(self):
        self.login(self.client_email)
        time.sleep(1)

    def go_to_owner_services(self):
        self.login_owner()
        self.driver.get(self.live_server_url + "/owner/services/")
        self.wait.until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Upravljanje Uslugama")
        )

    def test_owner_can_open_services_page(self):
        """Proverava da vlasnik može da pristupi stranici za upravljanje uslugama."""
        self.go_to_owner_services()
        self.assertIn("Upravljanje Uslugama", self.driver.page_source)

    def test_owner_can_add_service(self):
        """Proverava uspešno dodavanje nove usluge."""
        self.go_to_owner_services()

        self.driver.find_element(By.ID, "showAddServiceBtn").click()

        self.wait.until(EC.visibility_of_element_located((By.ID, "add-service-form")))

        form = self.driver.find_element(By.ID, "add-service-form")
        form.find_element(By.NAME, "name").send_keys("Pedikir")
        form.find_element(By.NAME, "category").send_keys("Nega noktiju")
        form.find_element(By.NAME, "duration").send_keys("45")
        form.find_element(By.NAME, "price").send_keys("2500")

        form.find_element(By.ID, "dodajUsluguBtn").click()

        self.wait.until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Pedikir")
        )

    def test_owner_cannot_add_duplicate_service(self):
        """Proverava da sistem sprečava dodavanje duplirane usluge."""
        self.go_to_owner_services()

        self.driver.find_element(By.ID, "showAddServiceBtn").click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "add-service-form")))

        form = self.driver.find_element(By.ID, "add-service-form")
        form.find_element(By.NAME, "name").send_keys("Manikir")
        form.find_element(By.NAME, "category").send_keys("Nega noktiju")
        form.find_element(By.NAME, "duration").send_keys("30")
        form.find_element(By.NAME, "price").send_keys("2000")

        form.find_element(By.ID, "dodajUsluguBtn").click()
        time.sleep(1)

        self.assertEqual(
            Service.objects.filter(
                salonid=self.salon,
                name="Manikir",
                category="Nega noktiju",
                is_active=True
            ).count(),
            1
        )

    def test_owner_can_delete_service(self):
        """
        Proverava da vlasnik može da obriše uslugu.
        """

        self.login_owner()

        self.driver.get(f"{self.live_server_url}/owner/services/")

        service_name = "Nega noktiju"
        self.assertIn(service_name, self.driver.page_source)

        row = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//tr[td[contains(normalize-space(), '{service_name}')]]")
            )
        )

        delete_btn = row.find_element(By.XPATH, ".//button[starts-with(@id, 'deleteUslugaBtn_')]")
        delete_btn.click()

        alert = self.wait.until(EC.alert_is_present())
        self.assertEqual(
            alert.text,
            "Da li ste sigurni da želite da obrišete ovu uslugu?"
        )
        alert.accept()

        self.driver.refresh()
        self.assertNotIn(service_name, self.driver.page_source)

    def test_client_can_view_reservations(self):
        """Proverava prikaz rezervacija klijenta."""
        sutra = timezone.now() + timedelta(days=1)

        Appointment.objects.create(
            userid=self.leg_client,
            staffid=self.staff,
            serviceid=self.service,
            datetime=sutra.replace(hour=14, minute=0),
            status=1,
        )

        self.login_client()

        self.driver.get(self.live_server_url + "/klijent/moje-rez/")

        self.assertIn("Manikir", self.driver.page_source)

    def test_client_can_cancel_reservation(self):
        """Proverava otkazivanje rezervacije."""
        sutra = timezone.now() + timedelta(days=1)

        appointment = Appointment.objects.create(
            userid=self.leg_client,
            staffid=self.staff,
            serviceid=self.service,
            datetime=sutra.replace(hour=10, minute=0),
            status=1,
        )

        self.login_client()

        self.driver.get(self.live_server_url + "/klijent/moje-rez/")

        cancel_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-cancel"))
        )

        cancel_btn.click()

        time.sleep(2)

        appointment.refresh_from_db()

        self.assertEqual(appointment.status, 2)

    def test_staff_can_open_booking_page(self):
        """Proverava pristup stranici za zakazivanje termina."""
        self.login_staff()

        self.driver.get(self.live_server_url + "/osoblje/zakazi-termin/")

        self.wait.until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Zakaži termin")
        )

    def test_protected_pages_require_login(self):
        """Proverava da neprijavljen korisnik ne može pristupiti zaštićenim stranicama."""
        d = self.driver

        d.get(self.live_server_url + "/owner/services/")
        self.wait.until(EC.url_contains("login"))

        d.get(self.live_server_url + "/klijent/moje-rez/")
        self.wait.until(EC.url_contains("login"))

        d.get(self.live_server_url + "/osoblje/zakazi-termin/")
        self.wait.until(EC.url_contains("login"))

    def test_staff_can_open_calendar(self):
        """Proverava da osoblje može da pristupi stranici kalendara."""
        self.login_staff()

        self.driver.get(self.live_server_url + "/osoblje/kalendar/")

        self.wait.until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Kalendar")
        )

    def test_staff_can_get_free_slots(self):
        """Proverava da sistem vraća listu slobodnih termina za izabrani datum."""
        self.login_staff()

        sutra = (timezone.localdate() + timedelta(days=1)).isoformat()

        url = (
            f"{self.live_server_url}/osoblje/api/free-slots/"
            f"?date={sutra}&service_id={self.service.idservice}&staff_id={self.staff.staffid}"
        )

        self.driver.get(url)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        body = self.driver.find_element(By.TAG_NAME, "body").text

        self.assertNotIn("error", body.lower())
        self.assertIn("09:00", body)