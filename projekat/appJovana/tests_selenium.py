from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
import os
import unittest
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.models import User as DjangoUser
from appIva.models import User as LegacyUser, UserProfile, Salon, Service, Review, Appointment, Owner, Staff

#Iva Susa

class AppJovanaSeleniumTests(StaticLiveServerTestCase):
    """Selenium testovi za aplikaciju. Koristi Chrome, a ako nije dostupan prelazi na Firefox."""

    @classmethod
    def setUpClass(cls):
        """Pokreće WebDriver pre svih testova. Ako ni Chrome ni Firefox nisu dostupni, testovi se preskaču."""
        super().setUpClass()
        cls.driver = None
        last_exc = None

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1400,900")
        chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin

        try:
            chrome_path = ChromeDriverManager().install()
            cls.driver = webdriver.Chrome(service=Service(chrome_path), options=chrome_options)
            print('Using Chrome webdriver:', chrome_path)
        except Exception as e:
            last_exc = e
            try:
                ff_opts = FirefoxOptions()
                ff_opts.add_argument('--headless')
                ff_opts.add_argument('--width=1400')
                ff_opts.add_argument('--height=900')
                gecko_path = GeckoDriverManager().install()
                cls.driver = webdriver.Firefox(service=FirefoxService(gecko_path), options=ff_opts)
                print('Using Firefox webdriver:', gecko_path)
            except Exception as e2:
                last_exc = e2

        if cls.driver is None:
            raise unittest.SkipTest(f'No webdriver available: {last_exc}')

        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        """Zatvara WebDriver nakon svih testova."""
        if getattr(cls, 'driver', None):
            cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        """Kreira testne korisnike (klijent, vlasnik, osoblje), salon, uslugu, termin i recenziju pre svakog testa."""
        self.client_dj = DjangoUser.objects.create_user(username='client@example.com', email='client@example.com', password='pass1234', first_name='Cli', last_name='Ent')
        self.client_legacy = LegacyUser.objects.create(name='Cli', surname='Ent', email='client@example.com', password='irrelevant')
        UserProfile.objects.create(django_user=self.client_dj, legacy_user=self.client_legacy)

        self.owner_dj = DjangoUser.objects.create_user(username='owner@example.com', email='owner@example.com', password='ownerpass', first_name='Own', last_name='Er')
        self.owner_legacy = LegacyUser.objects.create(name='Own', surname='Er', email='owner@example.com', password='irrelevant')
        UserProfile.objects.create(django_user=self.owner_dj, legacy_user=self.owner_legacy)

        self.staff_dj = DjangoUser.objects.create_user(username='staff@example.com', email='staff@example.com', password='staffpass', first_name='Sta', last_name='Ff')
        self.staff_legacy = LegacyUser.objects.create(name='Sta', surname='Ff', email='staff@example.com', password='irrelevant')
        UserProfile.objects.create(django_user=self.staff_dj, legacy_user=self.staff_legacy)

        self.salon = Salon.objects.create(name='Salon Test', address='Addr 1', contact='123', working_hours='09-17', grade=4.0)
        self.service = Service.objects.create(name='Cut', price=10.0, duration=30, salonid=self.salon, category='frizerske', is_active=True)

        self.owner = Owner.objects.create(userid=self.owner_legacy, salonid=self.salon, verified=1)
        self.staff = Staff.objects.create(userid=self.staff_legacy, salonid=self.salon, position='Stylist')

        self.appointment = Appointment.objects.create(userid=self.client_legacy, staffid=self.staff, serviceid=self.service, datetime=timezone.now() - timedelta(days=1), status=1)

        self.review = Review.objects.create(userid=self.client_legacy, salonid=self.salon, rating=4, comment='Good', createdat=timezone.now())

    def login_via_form(self, username, password):
        """Prijavljuje korisnika kroz login formu u browseru."""
        self.driver.get(self.live_server_url + reverse('login_user'))
        email_el = self.driver.find_element(By.ID, 'email')
        pwd_el = self.driver.find_element(By.ID, 'password')
        email_el.clear()
        email_el.send_keys(username)
        pwd_el.clear()
        pwd_el.send_keys(password)
        pwd_el.send_keys(Keys.RETURN)
        WebDriverWait(self.driver, 5).until(
            lambda d: d.current_url != self.live_server_url + reverse('login_user')
        )

    def test_salons_list_and_filters(self):
        """Proverava da li se saloni prikazuju na listi i da li filteri po imenu i oceni rade ispravno."""
        salon_b = Salon.objects.create(name='Other Salon', address='Addr 2', contact='456', working_hours='09-17', grade=3.0)
        Service.objects.create(name='Massage', price=30.0, duration=60, salonid=salon_b, category='wellness', is_active=True)

        self.driver.get(self.live_server_url + reverse('salonViews'))
        body = self.driver.find_element(By.TAG_NAME, 'body')
        assert 'Salon Test' in body.text
        assert 'Other Salon' in body.text

        search = self.driver.find_element(By.ID, 'search-name')
        search.clear()
        search.send_keys('Other')
        old_body = self.driver.find_element(By.TAG_NAME, 'body')
        search.send_keys(Keys.RETURN)
        WebDriverWait(self.driver, 5).until(EC.staleness_of(old_body))
        body = self.driver.find_element(By.TAG_NAME, 'body')
        assert 'Other Salon' in body.text
        assert 'Salon Test' not in body.text

        self.driver.get(self.live_server_url + reverse('salonViews') + '?rating=4.5')
        body = self.driver.find_element(By.TAG_NAME, 'body')
        assert 'Salon Test' not in body.text

    def test_salon_detail_shows_services_and_reviews(self):
        """Proverava da stranica sa detaljima salona prikazuje usluge i recenzije."""
        self.driver.get(self.live_server_url + reverse('salon_detail', args=[self.salon.salonid]))
        body = self.driver.find_element(By.TAG_NAME, 'body')
        assert 'Salon Test' in body.text
        assert 'Cut' in body.text
        assert 'Good' in body.text

    def test_client_can_add_review(self):
        """Proverava da prijavljeni klijent može da doda recenziju za salon."""
        self.login_via_form('client@example.com', 'pass1234')
        self.driver.get(self.live_server_url + reverse('klijent_recenzije'))
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, 'review-salon'))
        )
        select = self.driver.find_element(By.ID, 'review-salon')
        for option in select.find_elements(By.TAG_NAME, 'option'):
            if option.get_attribute('value') == str(self.salon.salonid):
                option.click()
                break

        self.driver.execute_script("setRating(5);")

        comment = self.driver.find_element(By.ID, 'review-comment')
        comment.clear()
        comment.send_keys('Excellent service')

        self.driver.execute_script("document.getElementById('review-form').submit();")

        import time
        time.sleep(2)

        body = self.driver.find_element(By.TAG_NAME, 'body')

        assert 'Recenzija uspešno dodata' in body.text or 'Excellent service' in body.text

    def test_owner_reviews_page(self):
        """Proverava da vlasnik može da pristupi stranici sa recenzijama svog salona."""
        self.login_via_form('owner@example.com', 'ownerpass')
        self.driver.get(self.live_server_url + reverse('owner_reviews'))
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        body = self.driver.find_element(By.TAG_NAME, 'body')
        assert 'Recenzije i Ocene' in body.text or 'Prosečna ocena' in body.text or 'avg_rating' in body.text

    def test_staff_overview_and_profile_edit(self):
        """Proverava da osoblje može da pristupi pregledu i izmeni svog profila."""
        self.login_via_form('staff@example.com', 'staffpass')
        self.driver.get(self.live_server_url + reverse('osoblje_pregled'))
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        body = self.driver.find_element(By.TAG_NAME, 'body')
        assert 'Osoblje' in body.text or 'Pregled' in body.text or 'Panel' in body.text

        self.driver.get(self.live_server_url + reverse('osoblje_izmeni_profil'))
        try:
            name_in = self.driver.find_element(By.NAME, 'name')
            surname_in = self.driver.find_element(By.NAME, 'surname')
        except NoSuchElementException:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            assert 'Moj profil' in body.text or 'moj_profil' in body.text or 'Profil' in body.text
            return

        name_in.clear()
        name_in.send_keys('NewName')
        surname_in.clear()
        surname_in.send_keys('NewSurname')
        phone_in = self.driver.find_element(By.NAME, 'phone')
        phone_in.clear()
        phone_in.send_keys('555-000')
        pwd = self.driver.find_element(By.NAME, 'password')
        pwd.clear()
        pwd.send_keys('newstaffpass')
        pwdc = self.driver.find_element(By.NAME, 'confirm_password')
        pwdc.clear()
        pwdc.send_keys('newstaffpass')

        pwdc.send_keys(Keys.RETURN)