# Jovana Simic 2022/0466
import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from django.contrib.auth.models import User as DjangoUser
from appIva.models import User as LegacyUser, UserProfile, Salon, Owner, Staff

PASSWORD = "OwnerPass123!"


class WebDriverAppIvaTests(StaticLiveServerTestCase):
    """
    Selenium integracioni testovi za:
    1. Registraciju klijenta
    2. Login i logout korisnika
    3. Zaštitu stranica koje zahtevaju autentifikaciju
    4. Upravljanje osobljem od strane vlasnika salona
    """

    @classmethod
    def setUpClass(cls):
        """
        Pokretanje Selenium Chrome drivera u headless režimu
        i inicijalizacija WebDriverWait objekta.
        """
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
        """
        Gašenje Selenium drivera nakon završetka svih testova.
        """
        try:
            cls.driver.quit()
        finally:
            super().tearDownClass()

    def setUp(self):
        """
        Kreiranje početnih test podataka:
        - vlasnički nalog
        - legacy korisnik
        - povezani UserProfile
        - salon
        - Owner veza između vlasnika i salona
        """
        self.owner_email = "owner_test@test.com"

        dj_owner = DjangoUser.objects.create_user(
            username=self.owner_email,
            email=self.owner_email,
            password=PASSWORD,
            first_name="Owner",
            last_name="Test",
        )

        legacy_owner = LegacyUser.objects.create(
            name="Owner",
            surname="Test",
            email=self.owner_email,
            password="legacy",
            phone="060000000",
        )

        UserProfile.objects.create(django_user=dj_owner, legacy_user=legacy_owner)

        salon = Salon.objects.create(
            name="Salon Test",
            address="Adresa 1",
            contact="060000000",
            working_hours="",
            description="",
            grade=None,
        )

        Owner.objects.create(userid=legacy_owner, salonid=salon, verified=1)

    def _unique_email(self, prefix: str) -> str:
        """
        Generiše jedinstven email za test korisnike
        kako bi se izbegli konflikti u bazi.
        """
        return f"{prefix}_{int(time.time() * 1000)}@test.com"

    def register_client(self) -> str:
        """
        Automatska registracija klijenta kroz UI.
        Popunjava formu za registraciju i vraća email novog korisnika.
        """
        d = self.driver
        d.get(self.live_server_url + reverse("register_user"))

        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Klijent')]"))
        ).click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "client-name")))

        email = self._unique_email("wd_client")

        d.find_element(By.ID, "client-name").send_keys("Test")
        d.find_element(By.ID, "client-surname").send_keys("Client")
        d.find_element(By.ID, "client-email").send_keys(email)
        d.find_element(By.ID, "client-password").send_keys("Pass12345!")
        d.find_element(By.ID, "client-phone").send_keys("061111111")

        d.find_element(By.XPATH, "//form[@id='client-registration']//button[@type='submit']").click()
        self.wait.until(EC.url_to_be(self.live_server_url + reverse("home")))
        return email

    def login(self, email: str, password: str):
        """
        Generička metoda za login korisnika preko login forme.
        """
        d = self.driver
        d.get(self.live_server_url + reverse("login_user"))

        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))
        d.find_element(By.ID, "email").clear()
        d.find_element(By.ID, "email").send_keys(email)

        d.find_element(By.ID, "password").clear()
        d.find_element(By.ID, "password").send_keys(password)

        d.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def login_owner_go_to_staff_page(self):
        """
        Login vlasnika i navigacija na stranicu za upravljanje osobljem.
        """
        self.login(self.owner_email, PASSWORD)
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Osoblje')]"))
        ).click()

        self.wait.until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Upravljanje osobljem")
        )

    def test_01_register_client_success(self):
        """
        Test uspešne registracije klijenta kroz UI.
        """
        email = self.register_client()
        self.assertTrue(email.endswith("@test.com"))

    def test_02_login_client_success_after_registration(self):
        """
        Test uspešnog logovanja klijenta nakon registracije.
        """
        email = self.register_client()
        self.login(email, "Pass12345!")
        self.wait.until(EC.url_contains("/kiljent/profil/"))
        self.assertIn("/kiljent/profil/", self.driver.current_url)

    def test_03_login_wrong_password_shows_error(self):
        """
        Test neuspešnog logovanja sa pogrešnom lozinkom
        i proverava da li se prikazuje poruka o grešci.
        """
        email = self.register_client()
        self.login(email, "WRONGPASS")
        self.wait.until(
            EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Pogrešan email ili lozinka")
        )

    def test_04_logout_redirects_home(self):
        """
        Test logout funkcionalnosti i redirekcije na početnu stranicu.
        """
        email = self.register_client()
        self.login(email, "Pass12345!")
        self.wait.until(EC.url_contains("/kiljent/profil/"))

        self.driver.get(self.live_server_url + reverse("logout_user"))
        self.wait.until(EC.url_to_be(self.live_server_url + reverse("home")))

    def test_05_profile_requires_login(self):
        """
        Test zaštite stranice profila.
        Ako korisnik nije prijavljen mora biti preusmeren na login stranicu.
        """
        self.driver.get(self.live_server_url + reverse("profile"))
        self.wait.until(EC.url_contains("login"))

    def test_06_owner_add_staff_success(self):
        """
        Test dodavanja novog člana osoblja od strane vlasnika salona.
        """
        self.login_owner_go_to_staff_page()

        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Dodaj novog člana osoblja')]"))
        ).click()

        self.wait.until(EC.visibility_of_element_located((By.ID, "staff-name")))

        staff_email = self._unique_email("wd_staff")

        self.driver.find_element(By.ID, "staff-name").send_keys("Test")
        self.driver.find_element(By.ID, "staff-surname").send_keys("Staff")
        self.driver.find_element(By.ID, "staff-email").send_keys(staff_email)
        self.driver.find_element(By.ID, "staff-password").send_keys("StaffPass123!")

        self.driver.find_element(By.CSS_SELECTOR, "#staff-form button[type='submit']").click()

        msg = self.wait.until(EC.visibility_of_element_located((By.ID, "staff-message")))
        self.assertIn("uspešno", msg.text.lower())

        self.wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), staff_email))

    def test_07_owner_delete_staff(self):
        """
        Test brisanja člana osoblja.
        Dodaje se novi član, zatim se briše i proverava da više ne postoji u tabeli.
        """
        self.login_owner_go_to_staff_page()

        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Dodaj novog člana osoblja')]"))
        ).click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "staff-name")))

        staff_email = self._unique_email("wd_del")

        self.driver.find_element(By.ID, "staff-name").send_keys("Delete")
        self.driver.find_element(By.ID, "staff-surname").send_keys("User")
        self.driver.find_element(By.ID, "staff-email").send_keys(staff_email)
        self.driver.find_element(By.ID, "staff-password").send_keys("StaffPass123!")
        self.driver.find_element(By.CSS_SELECTOR, "#staff-form button[type='submit']").click()

        self.wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), staff_email))

        row = self.wait.until(
            EC.presence_of_element_located((By.XPATH, f"//tr[td[contains(., '{staff_email}')]]"))
        )
        row.find_element(By.XPATH, ".//button[contains(., 'Obriši')]").click()

        for _ in range(2):
            try:
                self.wait.until(EC.alert_is_present())
                Alert(self.driver).accept()
                time.sleep(1)
            except:
                break

        self.assertFalse(
            Staff.objects.filter(userid__email=staff_email).exists()
        )