# appIva/views.py
#Iva Susa

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User as DjangoUser
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from .models import User as LegacyUser, UserProfile, Salon, Owner, Staff, Notification
from appSandra.views import osoblje_pregled

def register_user(request):
    """
        **Opis:**
        Funkcija omogućava registraciju novog korisnika sistema.
        Kreira Django korisnika, legacy korisnika i njihov profil.
        Ukoliko je izabrana opcija vlasnika salona, automatski se
        kreira i salon zajedno sa vlasničkim nalogom.

        **Vraća:**
        Renderuje registracionu stranicu ili preusmerava korisnika
        na početnu stranicu nakon uspešne registracije.

        **Modeli:**
        :model:`appIva.User`
        :model:`appIva.UserProfile`
        :model:`appIva.Salon`
        :model:`appIva.Owner`

        **Template:**
        :template:`register.html`
        """
    msg = None
    selected_type = None

    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        selected_type = user_type
        name = request.POST.get('name')
        surname = request.POST.get('surname')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if DjangoUser.objects.filter(username=email).exists():
            msg = 'Nalog sa ovom email adresom već postoji'
            return render(request, 'register.html', {'msg': msg, 'selected_type': selected_type})

        django_user = DjangoUser.objects.create_user(
            username=email, email=email, password=password,
            first_name=name, last_name=surname
        )

        legacy_user = LegacyUser.objects.create(
            name=name,
            surname=surname,
            email=email,
            password=make_password(password)
        )

        UserProfile.objects.create(django_user=django_user, legacy_user=legacy_user)

        if user_type == 'owner':
            salon = Salon.objects.create(
                name=request.POST.get('salon_name'),
                address=request.POST.get('salon_address'),
                contact=request.POST.get('salon_contact'),
                description=request.POST.get('salon_description'),
                working_hours=request.POST.get('salon_working_hours', '09:00-17:00'),
                grade=None
            )
            Owner.objects.create(userid=legacy_user, salonid=salon, verified=0)
            msg = "Registracija vlasnika salona uspešna."
            return render(request, 'register.html', {'msg': msg, 'selected_type': selected_type})

        return redirect('home')

    return render(request, 'register.html', {'selected_type': selected_type})


def login_user(request):
    """
        **Opis:**
        Funkcija vrši autentifikaciju korisnika na osnovu email adrese
        i lozinke. Nakon uspešne prijave korisnik se preusmerava na
        odgovarajući dashboard u zavisnosti od njegove uloge
        (vlasnik, osoblje ili klijent).

        **Vraća:**
        Render login stranice u slučaju greške ili redirect
        na odgovarajuću korisničku stranicu.

        **Modeli:**
        :model:`django.contrib.auth.models.User`
        :model:`appIva.Owner`
        :model:`appIva.Staff`

        **Template:**
        :template:`login.html`
        """
    errorMsg = None

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is None:
            errorMsg = "Pogrešan email ili lozinka."
            return render(request, 'login.html', {'error': errorMsg})

        login(request, user)

        try:
            legacy_user = user.profile.legacy_user
            if Owner.objects.filter(userid=legacy_user).exists():
                return redirect("owner_dashboard")
            elif Staff.objects.filter(userid=legacy_user).exists():
                return redirect('osoblje_pregled')
        except Exception:
            pass

        return redirect('klijent_moj_profil')

    return render(request, 'login.html', {'error': errorMsg})


def logout_user(request):
    """
        **Opis:**
        Odjavljuje trenutno prijavljenog korisnika iz sistema
        i briše njegovu sesiju.

        **Vraća:**
        Preusmeravanje na početnu stranicu aplikacije.

        **Template:**
        :template:`home.html`
        """
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    """
        **Opis:**
        Prikazuje profil prijavljenog korisnika i omogućava
        izmenu osnovnih ličnih podataka kao što su ime,
        prezime i broj telefona.

        **Vraća:**
        Render stranice korisničkog profila ili redirect
        ukoliko korisnik nema validan profil.

        **Modeli:**
        :model:`appIva.UserProfile`
        :model:`appIva.User`

        **Template:**
        :template:`KlijentMojProfil.html`
        """
    django_user = request.user
    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return redirect("home")

    if legacy_user.payload is None:
        legacy_user.payload = {}

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone = request.POST.get("phone")

        if not first_name or not last_name:
            messages.error(request, "Ime i prezime su obavezni.")
            return redirect("profile")

        if len(phone) < 6:
            messages.error(request, "Telefon nije validan.")
            return redirect("profile")

        django_user.first_name = first_name
        django_user.last_name = last_name
        django_user.save()

        legacy_user.payload["first_name"] = first_name
        legacy_user.payload["last_name"] = last_name
        legacy_user.phone = phone
        legacy_user.save()

        messages.success(request, "Podaci uspešno ažurirani!")
        return redirect("profile")

    context = {
        "django_user": django_user,
        "legacy_user": legacy_user,
    }
    return render(request, "KlijentMojProfil.html", context)


#def klijent_moje_rez(request):
#    return render(request, 'klijentMojeRez.html')


def klijent_rec(request):
    """
        **Opis:**
        Prikazuje stranicu recenzija za klijenta.

        **Vraća:**
        Render stranice sa recenzijama.

        **Template:**
        :template:`klijentRec.html`
        """
    return render(request, 'klijentRec.html')


def klijent_moj_profil(request):
    """
        **Opis:**
        Prikazuje korisnički profil klijenta bez izmene podataka.

        **Vraća:**
        Render stranice korisničkog profila.

        **Template:**
        :template:`KlijentMojProfil.html`
        """
    legacy_user = None
    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        pass

    return render(request, 'KlijentMojProfil.html', {
        'legacy_user': legacy_user
    })


@login_required
def update_profile(request):
    """
     **Opis:**
     Ažurira podatke prijavljenog korisnika uključujući
     ime, prezime, telefon i opcionalno lozinku.

     **Vraća:**
     Preusmeravanje na stranicu profila nakon izmene podataka.

     **Modeli:**
     :model:`appIva.User`
     :model:`appIva.UserProfile`
     """
    if request.method == "POST":
        django_user = request.user
        try:
            legacy_user = django_user.profile.legacy_user
        except Exception:
            return redirect("klijent_moj_profil")

        name = request.POST.get("name")
        surname = request.POST.get("surname")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        django_user.first_name = name
        django_user.last_name = surname
        if password:
            django_user.set_password(password)
        django_user.save()

        if password:
            update_session_auth_hash(request, django_user)

        legacy_user.name = name
        legacy_user.surname = surname
        legacy_user.phone = phone
        if password:
            legacy_user.password = make_password(password)
        legacy_user.save()

        return redirect("klijent_moj_profil")

    return redirect("klijent_moj_profil")


def home(request):
    """
        **Opis:**
        Prikazuje početnu stranicu aplikacije.

        **Vraća:**
        Render početne stranice sistema.

        **Template:**
        :template:`home.html`
        """
    return render(request, 'home.html')


@login_required
def owner_staff_view(request):
    """
        **Opis:**
        Omogućava vlasniku salona pregled zaposlenih
        koji rade u njegovom salonu.

        **Vraća:**
        Render stranice sa listom osoblja ili redirect
        ukoliko korisnik nije vlasnik.

        **Modeli:**
        :model:`appIva.Owner`
        :model:`appIva.Staff`

        **Template:**
        :template:`owner-staff.html`
        """
    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return redirect("home")

    if not Owner.objects.filter(userid=legacy_user).exists():
        return redirect('home')

    owner = Owner.objects.get(userid=legacy_user)
    staff_list = Staff.objects.filter(salonid=owner.salonid).select_related("userid")

    return render(request, "owner-staff.html", {
        "staff_list": staff_list,
        "owner": owner
    })


@login_required
def add_staff(request):
    """
        **Opis:**
        Funkcija omogućava vlasniku salona dodavanje novog
        člana osoblja. Kreira Django korisnika, legacy korisnika
        i zapis o zaposlenom u salonu.

        **Vraća:**
        JSON odgovor koji označava uspeh ili grešku operacije.

        **Modeli:**
        :model:`appIva.Staff`
        :model:`appIva.UserProfile`
        """
    if request.method != "POST":
        return redirect("owner_staff")

    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return redirect("home")

    if not Owner.objects.filter(userid=legacy_user).exists():
        return redirect('home')

    owner = Owner.objects.get(userid=legacy_user)

    name = request.POST.get("name")
    surname = request.POST.get("surname")
    email = request.POST.get("email")
    password = request.POST.get("password")

    if DjangoUser.objects.filter(username=email).exists():
        return JsonResponse({"status": "error", "message": "Email je već registrovan."})

    django_staff_user = DjangoUser.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name,
        last_name=surname
    )

    legacy_staff = LegacyUser.objects.create(
        name=name,
        surname=surname,
        email=email,
        password=make_password(password),
        phone=""
    )

    UserProfile.objects.create(django_user=django_staff_user, legacy_user=legacy_staff)

    Staff.objects.create(
        userid=legacy_staff,
        salonid=owner.salonid,
        position="osoblje"
    )

    return JsonResponse({"status": "success", "message": "Osoblje uspešno dodato."})


@login_required
def delete_staff(request, staff_id):
    """
        **Opis:**
        Omogućava vlasniku salona brisanje zaposlenog
        zajedno sa njegovim korisničkim nalozima.

        **Parametri:**
        ``staff_id`` — identifikator zaposlenog.

        **Vraća:**
        JSON odgovor o uspešnosti brisanja.

        **Modeli:**
        :model:`appIva.Staff`
        """
    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return redirect("home")

    if not Owner.objects.filter(userid=legacy_user).exists():
        return redirect('home')

    try:
        staff = Staff.objects.get(staffid=staff_id)
        legacy_staff_user = staff.userid

        staff.delete()
        legacy_staff_user.profile.django_user.delete()
        legacy_staff_user.delete()

        return JsonResponse({"status": "success"})
    except Staff.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Nalog ne postoji."})
