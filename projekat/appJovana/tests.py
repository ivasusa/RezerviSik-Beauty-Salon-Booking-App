from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User as DjangoUser
from appIva.models import User as LegacyUser, UserProfile, Salon, Service, Review, Appointment, Owner, Staff

#Iva Susa

class AppJovanaUnitTests(TestCase):
    """Unit testovi za aplikaciju koji proveravaju view-ove i logiku bez browsera."""

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

    def test_salons_view_filters(self):
        """Proverava da lista salona vraća 200 i da filteri po imenu i oceni rade ispravno."""
        salon_b = Salon.objects.create(name='Other Salon', address='Addr 2', contact='456', working_hours='09-17', grade=3.0)
        Service.objects.create(name='Massage', price=30.0, duration=60, salonid=salon_b, category='wellness', is_active=True)

        url = reverse('salonViews')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Salon Test', content)
        self.assertIn('Other Salon', content)

        resp = self.client.get(url, {'search-name': 'Other'})
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Other Salon', content)
        self.assertNotIn('Salon Test', content)

        resp = self.client.get(url, {'rating': '4.5'})
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertNotIn('Salon Test', content)

    def test_salon_detail(self):
        """Proverava da stranica sa detaljima salona vraća 200 i prikazuje usluge i recenzije."""
        url = reverse('salon_detail', args=[self.salon.salonid])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Salon Test', content)
        self.assertIn('Cut', content)
        self.assertIn('Good', content)

    def test_client_reviews_and_add_review(self):
        """Proverava da prijavljeni klijent može da vidi recenzije i uspešno doda novu."""
        login = self.client.login(username='client@example.com', password='pass1234')
        self.assertTrue(login)

        url = reverse('klijent_recenzije')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        add_url = reverse('dodaj_recenziju')
        resp = self.client.post(add_url, {'salon_id': self.salon.salonid, 'rating': '5', 'comment': 'Excellent service'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        messages = list(resp.context.get('messages')) if resp.context else []
        self.assertTrue(any('Recenzija uspešno dodata' in str(m) for m in messages))
        self.assertTrue(Review.objects.filter(salonid=self.salon, comment='Excellent service').exists())

    def test_owner_reviews(self):
        """Proverava da vlasnik može da pristupi stranici recenzija i da kontekst sadrži prosečnu ocenu."""
        login = self.client.login(username='owner@example.com', password='ownerpass')
        self.assertTrue(login)
        url = reverse('owner_reviews')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('avg_rating', resp.context)

    def test_staff_pregled_and_profile_edit(self):
        """Proverava da osoblje može da pristupi pregledu i da izmena profila ispravno ažurira podatke u bazi."""
        login = self.client.login(username='staff@example.com', password='staffpass')
        self.assertTrue(login)

        pregled_url = reverse('osoblje_pregled')
        resp = self.client.get(pregled_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('staff', resp.context)

        edit_url = reverse('osoblje_izmeni_profil')
        resp = self.client.get(edit_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('staff', resp.context)

        resp = self.client.post(edit_url, {'name': 'NewName', 'surname': 'NewSurname', 'phone': '555-000', 'password': 'newstaffpass', 'confirm_password': 'newstaffpass'}, follow=True)
        self.assertEqual(resp.status_code, 200)
        messages = list(resp.context.get('messages')) if resp.context else []
        self.assertTrue(any('Podaci uspešno ažurirani' in str(m) for m in messages))

        self.staff_legacy = LegacyUser.objects.get(pk=self.staff.userid.useriid)
        self.assertEqual(self.staff_legacy.name, 'NewName')
        self.assertEqual(self.staff_legacy.surname, 'NewSurname')