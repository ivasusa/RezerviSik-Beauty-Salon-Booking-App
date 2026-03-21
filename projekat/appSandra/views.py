# appSandra/views.py
# Autor: Sandra Bubanja
#Iva Susa, male izmene
# Opis: Django views za vlasnike (Owner), osoblje (Staff) i klijente (Client) u aplikaciji
# za upravljanje salonima i terminima. Obuhvata render HTML stranica, REST API JSON odgovore,
# statistike, prikaz rasporeda termina, slobodna vremena i dnevne notifikacije.

from django.db.models import Sum, Avg
from django.db.models.functions import ExtractDay
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from appSandra.services.notifications import send_daily_reminders
from datetime import datetime as dt, time as dtime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
import calendar
from datetime import datetime, time
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from appIva.models import (
    Appointment,
    Notification,
    UserProfile,
    Staff,
    Owner,
    Review,
    Service,
    GoogleCalendarConnection,
)

# ============================================================
# Konstantne vrednosti
# ============================================================

STATUS_BOOKED = 1
STATUS_CANCELED = 2

WORK_HOURS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00"
]

# ============================================================
# Helper funkcije
# ============================================================

def get_legacy_user(request):
    """
    Vraca povezanu legacy (stari sistem) korisnicku instancu
    na osnovu trenutnog Django auth user-a.
    Returns:
        appIva.User instanca ili None ako korisnik nije autentifikovan
    """
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.profile.legacy_user
    except Exception:
        return None


def get_staff_for_request(request):
    """
    Vraca Staff instancu povezanu sa trenutnim korisnikom.
    Returns:
        Staff instanca ili None
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return None
    return Staff.objects.filter(userid=legacy).select_related("salonid").first()


def get_owner_for_request(request):
    """
    Vraca Owner instancu povezanu sa trenutnim korisnikom.
    Returns:
        Owner instanca ili None
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return None
    return Owner.objects.filter(userid=legacy).select_related("salonid").first()


def _tomorrow_bounds_local():
    """
    Pomocna funkcija koja vraca pocetak i kraj sutrasnjeg dana po lokalnom vremenu
    Returns:
        tuple: (tomorrow_date, start_datetime_aware, end_datetime_aware)
    """
    tomorrow = timezone.localdate() + timedelta(days=1)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(dt.combine(tomorrow, dtime.min), tz)
    end = start + timedelta(days=1)
    return tomorrow, start, end


# ============================================================
# OWNER: osnovne stranice
# ============================================================

@login_required
def owner_dashboard(request):

    owner = get_owner_for_request(request)
    if not owner or not owner.salonid_id:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    salon = owner.salonid
    salon_id = owner.salonid_id

    today = timezone.localdate()

    reservations_today = Appointment.objects.filter(
        staffid__salonid_id=salon_id,
        datetime__date=today,
        status=STATUS_BOOKED
    ).count()

    active_services = Service.objects.filter(
        salonid_id=salon_id,
        is_active=True
    ).count()

    employees_count = Staff.objects.filter(
        salonid_id=salon_id
    ).count()

    now = timezone.localtime(timezone.now())
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start_of_month.month == 12:
        next_month = start_of_month.replace(year=start_of_month.year + 1, month=1)
    else:
        next_month = start_of_month.replace(month=start_of_month.month + 1)

    monthly_earnings = (
        Appointment.objects.filter(
            staffid__salonid_id=salon_id,
            status=STATUS_BOOKED,
            datetime__gte=start_of_month,
            datetime__lt=next_month
        ).aggregate(total=Sum("serviceid__price"))["total"] or 0
    )

    return render(request, "owner-dashboard.html", {
        "owner": owner,
        "salon": salon,
        "reservations_today": reservations_today,
        "active_services": active_services,
        "employees_count": employees_count,
        "monthly_earnings": monthly_earnings,
    })

@login_required
def owner_calendar(request):
    """
    Renderuje HTML stranicu kalendara za vlasnika.
    Returns:
        "owner-calendar.html" sa kontekstom initial_year i initial_month
    """
    owner = get_owner_for_request(request)
    if not owner:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    salon = owner.salonid
    today = timezone.localdate()

    return render(request, "owner-calendar.html", {
        "owner": owner,
        "salon": salon,
        "initial_year": today.year,
        "initial_month": today.month,
    })


@login_required
def owner_reviews(request):
    """
    Renderuje stranicu sa recenzijama vlasnika.
    Returns:
        "owner-reviews.html"
    """
    return render(request, "owner-reviews.html")


@login_required
def klijent_pregled(request):
    legacy_user = get_legacy_user(request)
    if not legacy_user:
        return JsonResponse({"error": "Niste prijavljeni kao klijent."}, status=403)

    try:
        tomorrow = timezone.localdate() + timedelta(days=1)

        reminders = Appointment.objects.filter(
            userid=legacy_user,
            datetime__date=tomorrow,
            status=STATUS_BOOKED
        ).select_related("serviceid", "staffid__salonid")

        next_two = Appointment.objects.filter(
            userid=legacy_user,
            datetime__gte=timezone.now(),
            status=STATUS_BOOKED
        ).select_related("serviceid", "staffid__salonid").order_by("datetime")[:2]

        active_count = Appointment.objects.filter(
            userid=legacy_user,
            status=STATUS_BOOKED,
            datetime__gte=timezone.now()
        ).count()

        google_conn = GoogleCalendarConnection.objects.filter(
            userid=legacy_user
        ).first()

        return render(request, "klijentPregled.html", {
            "reminders": reminders,
            "next_two": next_two,
            "active_count": active_count,
            "google_connected": google_conn is not None,
            "google_email": google_conn.google_email if google_conn else None,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def owner_staff(request):
    """
    Renderuje stranicu sa listom zaposlenih u salonu vlasnika.
    Returns:
        "owner-staff.html" sa kontekstom listom zaposlenih
    """
    owner = get_owner_for_request(request)
    if not owner:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    salon = owner.salonid

    staff_list = (
        Staff.objects
        .filter(salonid=salon)
        .select_related("userid")
        .order_by("userid__surname", "userid__name")
    )

    return render(request, "owner-staff.html", {
        "owner": owner,
        "salon": salon,
        "staff_list": staff_list,
    })



@login_required
def owner_statistics(request):

    owner = get_owner_for_request(request)
    if not owner:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    salon = owner.salonid

    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0)

    # svi termini samo za salon ovog vlasnika
    appointments = Appointment.objects.filter(
        staffid__salonid=salon,
        datetime__gte=start_of_month
    )

    total_appointments = appointments.count()

    canceled_appointments = appointments.filter(
        status=2
    ).count()

    total_earnings = appointments.filter(
        status=1
    ).aggregate(total=Sum("serviceid__price"))["total"] or 0

    avg_rating = Review.objects.filter(
        salonid=salon
    ).aggregate(avg=Avg("rating"))["avg"] or 0

    context = {
        "owner": owner,
        "salon": salon,
        "salon_id": salon.salonid,
        "total_appointments": total_appointments,
        "canceled_appointments": canceled_appointments,
        "total_earnings": total_earnings,
        "avg_rating": round(avg_rating, 2)
    }

    return render(request, "owner-statistics.html", context)

# ============================================================
# OWNER: API JSON funkcije
# ============================================================

@login_required
def api_owner_kalendar_mesec(request):
    """
    Vraca JSON sa podacima kalendara za odredjeni mesec.
    GET parametri: "year", "month"
    Returns:
        JsonResponse sa nedeljama i informacijom o terminima
    """
    owner = get_owner_for_request(request)
    if not owner or not owner.salonid_id:
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        year = int(request.GET.get("year"))
        month = int(request.GET.get("month"))
        if month < 1 or month > 12:
            raise ValueError()
    except Exception:
        return JsonResponse({"error": "bad params"}, status=400)

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    start_day = weeks[0][0]
    end_day = weeks[-1][-1]

    qs = Appointment.objects.filter(
        staffid__salonid_id=owner.salonid_id,
        datetime__date__gte=start_day,
        datetime__date__lte=end_day
    )

    days_with_appts = set(qs.values_list("datetime__date", flat=True))
    payload_weeks = []

    for w in weeks:
        week_payload = []
        for d in w:
            week_payload.append({
                "date": d.isoformat(),
                "day": d.day,
                "in_month": (d.month == month),
                "has_appointments": (d in days_with_appts),
            })
        payload_weeks.append(week_payload)

    month_title = f"{calendar.month_name[month]} {year}"
    return JsonResponse({
        "title": month_title,
        "year": year,
        "month": month,
        "weeks": payload_weeks,
    })


@login_required
def api_owner_termini_dan(request):
    """
    Vraca JSON sa terminima vlasnika na odredjeni datum.
    GET parametar: "date" (YYYY-MM-DD)
    Returns:
        JsonResponse sa listom termina
    """
    owner = get_owner_for_request(request)
    if not owner or not owner.salonid_id:
        return JsonResponse({"error": "forbidden"}, status=403)

    day_str = request.GET.get("date")
    day = parse_date(day_str) if day_str else None
    if not day:
        return JsonResponse({"error": "bad date"}, status=400)

    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)

    qs = (
        Appointment.objects
        .select_related("userid", "serviceid", "staffid__userid")
        .filter(
            staffid__salonid_id=owner.salonid_id,
            datetime__gte=start,
            datetime__lt=end
        )
        .order_by("datetime", "staffid__userid__surname")
    )

    appts = []
    for a in qs:
        start_local = timezone.localtime(a.datetime)
        duration_min = a.serviceid.duration or 0
        end_local = start_local + timedelta(minutes=duration_min)

        appts.append({
            "id": a.appointmentid,
            "start": start_local.strftime("%H:%M"),
            "end": end_local.strftime("%H:%M"),
            "service": a.serviceid.name,
            "client": f"{a.userid.name} {a.userid.surname}",
            "staff": f"{a.staffid.userid.name} {a.staffid.userid.surname}",
            "status": a.status,
        })

    return JsonResponse({
        "date": day.isoformat(),
        "appointments": appts,
    })


# ============================================================
# STAFF: profile i raspored
# ============================================================

@login_required
def osoblje_moj_profil(request):
    """
    Renderuje stranicu sa informacijama o trenutnom osoblju.
    Returns:
        "osoblje_moj_profil.html" sa imenom, pozicijom i salonom
    """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    salon = staff.salonid

    context = {
        "staff": staff,
        "staff_name": f"{staff.userid.name} {staff.userid.surname}",
        "staff_role": staff.position,
        "salon_name": salon.name if salon else "Wizard",
    }
    return render(request, "osoblje_moj_profil.html", context)


@login_required
def osoblje_moj_raspored(request):
    """
    Renderuje stranicu rasporeda trenutnog osoblja.
    Returns:
        "osoblje_moj_raspored.html"
    """
    return render(request, "osoblje_moj_raspored.html")


@login_required
def osoblje_pregled(request):
    """
    Renderuje stranicu pregleda trenutnog osoblja sa informacijama
    o salona i zaposlenom.
    Returns:
        "osoblje_pregled.html"
    """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    context = {
        "staff": staff,
        "staff_name": f"{staff.userid.name} {staff.userid.surname}",
        "staff_role": staff.position,
        "salon_name": staff.salonid.name if staff.salonid else "Wizard",
    }
    return render(request, "osoblje_pregled.html", context)


# ============================================================
# STAFF: day schedule + free slots + booked days
# ============================================================

@login_required
def staff_day_schedule(request, date_str):
    """
    Vraca JSON sa terminima za osoblje na odredjeni dan.
    Args:
        date_str: str u formatu "YYYY-MM-DD"
    Returns:
        JsonResponse lista sa terminima booked
    """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    day = parse_date(date_str)
    if not day:
        return JsonResponse({"error": "Neispravan datum. Koristi YYYY-MM-DD."}, status=400)

    appointments = (
        Appointment.objects.filter(
            staffid_id=staff.staffid,
            datetime__date=day,
            status=STATUS_BOOKED
        )
        .select_related("userid", "serviceid")
        .order_by("datetime")
    )

    data = [{
        "time": a.datetime.strftime("%H:%M"),
        "client": f"{a.userid.name} {a.userid.surname}",
        "service": a.serviceid.name
    } for a in appointments]

    return JsonResponse(data, safe=False)


@login_required
def staff_free_slots_test(request, date_str):
    """
    Vraca JSON listu slobodnih termina za osoblje na odredjeni dan.
    Returns:
        JsonResponse lista slobodnih vremena (HH:MM)
    """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    day = parse_date(date_str)
    if not day:
        return JsonResponse({"error": "Neispravan datum. Koristi YYYY-MM-DD."}, status=400)

    taken = Appointment.objects.filter(
        staffid_id=staff.staffid,
        datetime__date=day,
        status=STATUS_BOOKED
    ).order_by("datetime")

    taken_times = {a.datetime.strftime("%H:%M") for a in taken}
    free = [t for t in WORK_HOURS if t not in taken_times]

    return JsonResponse(free, safe=False)


@login_required
def staff_booked_days_test(request, year, month):
    """
    Vraca JSON listu dana u mesecu koji imaju booked termine za osoblje.
    Args:
        year: int
        month: int
    Returns:
        JsonResponse lista dana [1, 2, ...]
    """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)

    qs = Appointment.objects.filter(
        staffid_id=staff.staffid,
        datetime__year=year,
        datetime__month=month,
        status=STATUS_BOOKED
    ).values_list("datetime", flat=True)

    days = sorted({dt.day for dt in qs})
    return JsonResponse(days, safe=False)


# ============================================================
# OWNER: day schedule + booked days
# ============================================================

@login_required
def owner_day_schedule_test(request, date_str):
    """
    Vraca JSON sa terminima vlasnika na odredjeni dan.
    Args:
        date_str: str u formatu "YYYY-MM-DD"
    Returns:
        JsonResponse lista sa terminima booked
    """
    owner = get_owner_for_request(request)
    if not owner or not owner.salonid_id:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    day = parse_date(date_str)
    if not day:
        return JsonResponse({"error": "Neispravan datum. Koristi YYYY-MM-DD."}, status=400)

    appointments = (
        Appointment.objects.filter(
            staffid__salonid_id=owner.salonid_id,
            datetime__date=day,
            status=STATUS_BOOKED
        )
        .select_related("userid", "serviceid", "staffid", "staffid__userid")
        .order_by("datetime")
    )

    data = [{
        "time": a.datetime.strftime("%H:%M"),
        "client": f"{a.userid.name} {a.userid.surname}",
        "service": a.serviceid.name,
        "staff": f"{a.staffid.userid.name} {a.staffid.userid.surname}",
    } for a in appointments]

    return JsonResponse(data, safe=False)


@login_required
def owner_booked_days_test(request, year: int, month: int):
    """
    Vraca JSON listu dana u mesecu koji imaju booked termine za vlasnika.
    Returns:
        JsonResponse lista dana [1, 2, ...]
    """
    owner = get_owner_for_request(request)
    if not owner or not owner.salonid_id:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    qs = (
        Appointment.objects.filter(
            staffid__salonid_id=owner.salonid_id,
            datetime__year=year,
            datetime__month=month,
            status=STATUS_BOOKED
        )
        .annotate(day=ExtractDay("datetime"))
        .values_list("day", flat=True)
    )

    days = sorted(set(qs))
    return JsonResponse(days, safe=False)


# ============================================================
# Notifications
# ============================================================

@login_required
def daily_reminders(request):
    """
    Salje dnevne notifikacije svim korisnicima.
    Returns:
        JsonResponse sa brojem poslatih notifikacija
    """
    sent_count = send_daily_reminders()
    return JsonResponse({"sent": sent_count})

@login_required
def send_reminders_view(request):
    owner = get_owner_for_request(request)
    if not owner:
        return JsonResponse({"error": "Niste prijavljeni kao vlasnik."}, status=403)

    broj_poslatih = send_daily_reminders()

    return JsonResponse({
        "message": f"Poslato notifikacija: {broj_poslatih}"
    })


@login_required
def osoblje_izmeni_profil(request):
    """
    Ažurira podatke profila za osoblje.
    POST parametri: name, surname, phone, password, confirm_password
    Returns:
        redirect na osoblje_moj_profil nakon uspešne izmene
    """
    if request.method == "POST":
        staff = get_staff_for_request(request)
        if not staff:
            return redirect("osoblje_pregled")

        legacy_user = staff.userid
        django_user = legacy_user.profile.django_user

        name = request.POST.get("name", "").strip()
        surname = request.POST.get("surname", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        # Validacija
        if not name or not surname:
            return redirect("osoblje_moj_profil")

        # Ažuriranje osnovnih podataka
        django_user.first_name = name
        django_user.last_name = surname
        django_user.save()

        legacy_user.name = name
        legacy_user.surname = surname
        legacy_user.phone = phone

        # Ako je korisnik unešao lozinku, promeni je
        if password and password == confirm_password and len(password) >= 8:
            django_user.set_password(password)
            django_user.save()
            legacy_user.password = make_password(password)

        legacy_user.save()

        return redirect("osoblje_moj_profil")

    return redirect("osoblje_moj_profil")
