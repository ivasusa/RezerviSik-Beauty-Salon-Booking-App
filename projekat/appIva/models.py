from django.db import models
from django.contrib.auth.models import User as DjangoUser
#Iva Susa

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class User(models.Model):
    """
        User model predstavlja osnovnog korisnika sistema.
        Sadrži lične podatke korisnika kao što su ime, prezime,
        email adresa, lozinka i kontakt telefon.
        Koristi se kao legacy korisnička tabela povezana sa Django autentikacijom.
        """
    useriid = models.AutoField(db_column='useriId', primary_key=True)
    name = models.CharField(max_length=30)
    surname = models.CharField(max_length=30)
    email = models.CharField(max_length=40)
    password = models.CharField(max_length=128)
    phone = models.CharField(max_length=20, null=True, blank=True)


    class Meta:
        db_table = 'user'
# Create your models here.
class UserProfile(models.Model):
    """
        UserProfile model povezuje Django autentifikacionog korisnika sa
        postojećim (legacy) korisnikom aplikacije.
        Omogućava proširenje standardnog Django User modela
        dodatnim podacima iz sistema.
        """
    django_user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='profile')
    legacy_user = models.OneToOneField('User', on_delete=models.CASCADE, db_column='legacy_user_id', related_name='profile')

    class Meta:
        db_table = 'user_profile'

class GoogleCalendarConnection(models.Model):
    userid = models.OneToOneField('User', models.CASCADE, db_column='userId', primary_key=True)
    google_email = models.EmailField(null=True, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_uri = models.CharField(max_length=255, default='https://oauth2.googleapis.com/token')
    scopes = models.TextField(null=True, blank=True)
    expiry = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'google_calendar_connection'


class Appointment(models.Model):
    """
    Appointment model predstavlja zakazani termin u salonu.
    Povezuje korisnika, zaposlenog i uslugu,
    zajedno sa datumom i statusom termina.
    """

    appointmentid = models.AutoField(db_column='appointmentId', primary_key=True)
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId')
    staffid = models.ForeignKey('Staff', models.DO_NOTHING, db_column='staffId')
    serviceid = models.ForeignKey('Service', models.DO_NOTHING, db_column='serviceId')
    datetime = models.DateTimeField(db_column='dateTime')
    status = models.IntegerField()
    google_event_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'appointment'

    def clean(self):
        super().clean()

        if self.datetime and self.datetime < timezone.now():
            raise ValidationError({
                "datetime": "Termin ne može biti u prošlosti."
            })

        existing = Appointment.objects.filter(
            staffid=self.staffid,
            datetime=self.datetime
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError({
                "staffid": "Zaposleni već ima termin u tom vremenu."
            })

        # Provera da klijent nema dupli termin tada
        existing_user = Appointment.objects.filter(
            userid=self.userid,
            datetime=self.datetime
        ).exclude(pk=self.pk)

        if existing_user.exists():
            raise ValidationError({
                "userid": "Korisnik već ima termin u tom vremenu."
            })


class Notification(models.Model):
    """
       Notification model predstavlja notifikaciju vezanu za termin.
       Koristi se za slanje obaveštenja korisnicima
       o promenama, podsetnicima ili statusu termina.
       """
    notificationid = models.AutoField(db_column='notificationId', primary_key=True)  # Field name made lowercase.
    appointmentid = models.ForeignKey(Appointment, models.DO_NOTHING, db_column='appointmentId')  # Field name made lowercase.
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId')  # Field name made lowercase.
    message = models.CharField(max_length=255)
    sendat = models.DateTimeField(db_column='sendAt', blank=True, null=True)  # Field name made lowercase.
    type = models.IntegerField()

    class Meta:
        db_table = 'notification'


class Owner(models.Model):
    """
        Owner model predstavlja vlasnika salona.
        Jedan korisnik može biti vlasnik jednog salona,
        uz informaciju da li je nalog verifikovan.
        """
    userid = models.OneToOneField('User', models.DO_NOTHING, db_column='userId', primary_key=True)  # Field name made lowercase.
    salonid = models.ForeignKey('Salon', models.DO_NOTHING, db_column='salonId')  # Field name made lowercase.
    verified = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'owner'


class Review(models.Model):
    """
        Review model predstavlja ocenu i komentar korisnika
        za određeni salon. Koristi se za sistem
        ocenjivanja i prikaz reputacije salona.
        """
    reviewid = models.AutoField(db_column='reviewId', primary_key=True)  # Field name made lowercase.
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId')  # Field name made lowercase.
    salonid = models.ForeignKey('Salon', models.DO_NOTHING, db_column='salonId')  # Field name made lowercase.
    rating = models.IntegerField()
    comment = models.CharField(max_length=255, blank=True, null=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.

    class Meta:
        db_table = 'review'


class Salon(models.Model):
    """
        Salon model predstavlja salon u sistemu.
        Sadrži osnovne informacije o salonu,
        uključujući naziv, adresu, kontakt,
        radno vreme i prosečnu ocenu.
        """
    salonid = models.AutoField(db_column='salonId', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=100)
    working_hours = models.CharField(max_length=50)
    contact = models.CharField(max_length=45)
    grade = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'salon'


class Service(models.Model):
    """
        Service model predstavlja uslugu koju salon pruža.
        Definiše naziv usluge, cenu, trajanje,
        kategoriju i informaciju da li je usluga aktivna.
        """
    idservice = models.AutoField(db_column='idService', primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=40)
    price = models.FloatField()
    duration = models.IntegerField()
    salonid = models.ForeignKey(Salon, models.DO_NOTHING, db_column='salonId')  # Field name made lowercase.
    category = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'service'


class Staff(models.Model):
    """
        Staff model predstavlja zaposlenog u salonu.
        Povezuje korisnika sa salonom i definiše
        njegovu radnu poziciju.
        """
    staffid = models.AutoField(db_column='staffId', primary_key=True)  # Field name made lowercase.
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId')  # Field name made lowercase.
    salonid = models.ForeignKey(Salon, models.DO_NOTHING, db_column='salonId')  # Field name made lowercase.
    position = models.CharField(max_length=30)

    class Meta:
        db_table = 'staff'

