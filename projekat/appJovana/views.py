# autor: Jovana Simic 2022/0466
"""
View funkcije aplikacije appJovana.

Ovaj modul implementira funkcionalnosti vezane za:
- pregled i filtriranje salona,
- prikaz detalja salona,
- upravljanje recenzijama klijenata i vlasnika,
- pregled dnevnih termina osoblja,
- izmenu profila zaposlenih.

View funkcije koriste modele:
:model:`appIva.Salon`,
:model:`appIva.Service`,
:model:`appIva.Review`,
:model:`appIva.Appointment`,
:model:`appIva.Owner`.

Dokumentacija je namenjena Django admindocs sistemu.
"""

from datetime import timedelta, datetime, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.db.models import Avg, Prefetch

from appIva.models import Salon, Service, Review, Appointment, Owner, Staff
from appSandra.views import get_staff_for_request

from datetime import timedelta, datetime, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Prefetch
from django.http import JsonResponse
from django.utils import timezone

from appIva.models import Salon, Service, Review, Appointment, Owner, Staff
from appSandra.views import get_staff_for_request


def salonViews(request):
    search_name = request.GET.get("search-name", "").strip()
    category = request.GET.get("category", "").strip()
    rating = request.GET.get("rating", "").strip()

    salons = Salon.objects.all().prefetch_related(
        Prefetch(
            "service_set",
            queryset=Service.objects.filter(is_active=True).order_by("category", "name")
        )
    )

    if search_name:
        salons = salons.filter(name__icontains=search_name)

    if category:
        salons = salons.filter(
            service__category__iexact=category,
            service__is_active=True
        ).distinct()

    if rating:
        salons = salons.filter(grade__gte=float(rating))

    salons_data = []

    for salon in salons:
        services_qs = salon.service_set.all()

        unique_categories = []
        seen_categories = set()

        unique_services = []
        seen_services = set()

        for service in services_qs:
            if service.category not in seen_categories:
                unique_categories.append(service.category)
                seen_categories.add(service.category)

            if service.name not in seen_services:
                unique_services.append(service.name)
                seen_services.add(service.name)

        salons_data.append({
            "salon": salon,
            "categories": unique_categories,
            "services": unique_services,
        })

    available_categories = (
        Service.objects
        .filter(is_active=True)
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    context = {
        "salons_data": salons_data,
        "available_categories": available_categories,
        "search_name": search_name,
        "category": category,
        "rating": rating,
        "no_results": (search_name or category or rating) and len(salons_data) == 0,
    }

    return render(request, "salons.html", context)


def salon_detail(request, salon_id):
    """
       Prikazuje detalje jednog salona.

       Uključuje listu aktivnih usluga i recenzije korisnika.

       **Args**

       ``salon_id``
           Identifikator salona.

       **Context**

       ``salon``
           Instanca :model:`appIva.Salon`.
       ``services``
           Aktivne usluge (:model:`appIva.Service`).
       ``reviews``
           Recenzije (:model:`appIva.Review`).

       **Template**

       :template:`salon-details.html`
       """
    salon = Salon.objects.get(salonid=salon_id)
    services = Service.objects.filter(
        salonid=salon,
        is_active=True
    ).order_by("category", "name")

    reviews = Review.objects.filter(salonid=salon)

    return render(request, "salon-details.html", {
        "salon": salon,
        "services": services,
        "reviews": reviews
    })


@login_required
def clientReviews(request):
    """
       Prikazuje recenzije prijavljenog klijenta.

       Klijent može videti:
       - salone u kojima je imao termin,
       - svoje prethodne recenzije.

       **Context**

       ``salons``
           Saloni povezani sa terminima korisnika.
       ``reviews``
           Recenzije korisnika (:model:`appIva.Review`).

       **Template**

       :template:`klijentRec.html`
       """
    try:
        user = request.user.profile.legacy_user
    except Exception:
        return redirect("home")

    salons = Salon.objects.filter(
        staff__appointment__userid=user
    ).distinct()
    reviews = Review.objects.filter(userid=user).select_related('salonid')

    context = {
        'salons': salons,
        'reviews': reviews
    }
    return render(request, 'klijentRec.html', context)


@login_required
def add_review(request):
    """
        Dodaje novu recenziju salona.

        Recenzija je dozvoljena samo ako korisnik ima termin
        u tom salonu.

        Nakon dodavanja automatski se ažurira prosečna ocena
        modela :model:`appIva.Salon`.

        **POST parametri**

        ``salon_id`` — ID salona
        ``rating`` — ocena
        ``comment`` — komentar

        **Returns**

        Redirect na :view:`appJovana.klijent_recenzije`.
        """
    if request.method != "POST":
        return redirect('klijent_recenzije')

    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        messages.error(request, "Profil nije pronađen.")
        return redirect('klijent_recenzije')

    salon_id = request.POST.get("salon_id")
    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "").strip()

    if not salon_id or not rating:
        messages.error(request, "Morate izabrati salon i ocenu!")
        return redirect('klijent_recenzije')

    salon = get_object_or_404(Salon, salonid=salon_id)

    has_appointment = Appointment.objects.filter(
        userid=legacy_user,
        staffid__salonid=salon
    ).exists()

    if not has_appointment:
        messages.error(request, "Možete oceniti samo salone u kojima ste imali termin.")
        return redirect('klijent_recenzije')

    Review.objects.create(
        userid=legacy_user,
        salonid=salon,
        rating=int(rating),
        comment=comment,
        createdat=timezone.now()
    )

    avg = Review.objects.filter(salonid=salon).aggregate(Avg('rating'))['rating__avg']
    salon.grade = round(avg, 2) if avg is not None else None
    salon.save()

    messages.success(request, "Recenzija uspešno dodata!")
    return redirect('klijent_recenzije')


@login_required
def owner_reviews(request):
    """
       Prikazuje recenzije salona vlasnika.

       Omogućava filtriranje po oceni.

       **GET parametar**

       ``rating`` — filtriranje po oceni.

       **Template**

       :template:`owner-reviews.html`
       """
    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return redirect("home")

    owner = Owner.objects.filter(userid=legacy_user).select_related("salonid").first()
    if not owner:
        return redirect("home")

    salon = owner.salonid

    rating_filter = request.GET.get("rating")

    reviews = Review.objects.filter(salonid=salon).order_by("-createdat")
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)

    avg_rating = Review.objects.filter(salonid=salon).aggregate(
        Avg("rating")
    )["rating__avg"] or 0

    context = {
        "owner": owner,
        "salon": salon,
        "reviews": reviews,
        "avg_rating": round(avg_rating, 2),
        "selected_rating": rating_filter
    }

    return render(request, "owner-reviews.html", context)

from django.contrib.auth import update_session_auth_hash
from django.db import transaction

@login_required
def osoblje_izmeni_profil(request):
    """
        Omogućava zaposlenom izmenu ličnih podataka i lozinke.

        Ažurira i Django korisnika i legacy korisnika
        unutar jedne transakcije.

        **Template**

        :template:`osoblje_moj_profil.html`
        """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    legacy_user = staff.userid
    django_user = request.user

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        surname = request.POST.get("surname", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not name or not surname:
            messages.error(request, "Ime i prezime su obavezna polja!")
            return redirect('osoblje_moj_profil')

        try:
            with transaction.atomic():

                legacy_user.name = name
                legacy_user.surname = surname
                legacy_user.phone = phone if phone else None
                legacy_user.save()

                django_user.first_name = name
                django_user.last_name = surname

                if password:
                    if password != confirm_password:
                        messages.error(request, "Lozinke se ne poklapaju!")
                        return redirect('osoblje_moj_profil')

                    django_user.set_password(password)
                    legacy_user.password = django_user.password
                    legacy_user.save()

                    update_session_auth_hash(request, django_user)

                django_user.save()

        except Exception as e:
            messages.error(request, f"Greška pri čuvanju: {str(e)}")
            return redirect('osoblje_moj_profil')

        messages.success(request, "Podaci uspešno ažurirani!")
        return redirect('osoblje_moj_profil')

    context = {
        "staff": staff,
        "staff_name": f"{legacy_user.name} {legacy_user.surname}",
        "staff_email": legacy_user.email,
        "staff_phone": legacy_user.phone,
        "staff_role": staff.position,
        "salon_name": staff.salonid.name if staff.salonid else "Wizard",
    }
    return render(request, "osoblje_moj_profil.html", context)

STATUS_BOOKED = 1
STATUS_CANCELED = 2

WORK_HOURS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00"
]

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

@login_required
def osoblje_pregled(request):
    """
       Prikazuje dnevni pregled termina za prijavljeno osoblje.

       Pregled obuhvata samo termine za današnji datum (od 00:00 do 24:00 po lokalnom vremenu)
       i samo termine sa statusom ``STATUS_BOOKED``. Termini se dele na:
       - ``finished``: termini čije je vreme u prošlosti u odnosu na trenutni trenutak,
       - ``upcoming``: termini koji tek slede.

       Ako korisnik nije prijavljen kao osoblje (ne postoji Staff za request), vraća se JSON
       greška sa status kodom 403.

       **Context**

       ``staff``
           Instanca osoblja (model :model:`appIva.Staff`) dobijena funkcijom za autentifikaciju osoblja.
       ``staff_name``
           Ime i prezime zaposlenog (string).
       ``staff_role``
           Pozicija zaposlenog (string).
       ``salon_name``
           Naziv salona u kojem radi osoblje (string).
       ``today_count``
           Ukupan broj današnjih zakazanih termina (int).
       ``finished``
           Broj termina koji su već prošli (int).
       ``upcoming``
           Broj termina koji tek slede (int).
       ``appointments``
           Lista termina za prikaz u UI. Svaki element je dict sa ključevima:
           - ``time`` (HH:MM),
           - ``client`` (ime i prezime klijenta),
           - ``service`` (naziv usluge).

       **Template**

       :template:`osoblje_pregled.html`

       **Returns**

       HttpResponse sa renderovanim template-om ili JsonResponse (403) ako korisnik nije osoblje.
       """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    now = timezone.localtime()

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    end_of_day = start_of_day + timedelta(days=1)

    today_appointments = Appointment.objects.filter(
        staffid=staff,
        datetime__gte=start_of_day,
        datetime__lt=end_of_day,
        status=STATUS_BOOKED
    ).select_related("userid", "serviceid").order_by("datetime")

    today_count = today_appointments.count()
    finished = 0
    upcoming = 0
    appointments_list = []

    for a in today_appointments:
        appointment_dt = timezone.localtime(a.datetime)

        if appointment_dt < now:
            finished += 1
        else:
            upcoming += 1

        appointments_list.append({
            "time": appointment_dt.strftime("%H:%M"),
            "client": f"{a.userid.name} {a.userid.surname}",
            "service": a.serviceid.name
        })

    context = {
        "staff": staff,
        "staff_name": f"{staff.userid.name} {staff.userid.surname}",
        "staff_role": staff.position,
        "salon_name": staff.salonid.name if staff.salonid else "Wizard",
        "today_count": today_count,
        "finished": finished,
        "upcoming": upcoming,
        "appointments": appointments_list,
    }

    return render(request, "osoblje_pregled.html", context)