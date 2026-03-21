import os
import json
from math import ceil
import calendar
from datetime import datetime, time, timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from django.conf import settings
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from .forms import OwnerForm, SalonForm, ServiceForm
from appIva.models import Appointment, Notification, Staff, Owner, Service, Salon, User, GoogleCalendarConnection
from appSandra.services.notifation_hooks import (
    on_appointment_booked,
    on_appointment_canceled
)
import secrets

from appMasa.google_calendar_service import (
    create_google_event_for_appointment,
    delete_google_event_for_appointment,
)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def generate_work_slots(working_hours_str):
    """
    Generiše listu vremenskih slotova u koraku od 30 minuta na osnovu radnog vremena salona.

    Parametri:
        working_hours_str (str): Radno vreme u formatu "HH:MM-HH:MM".

    Povratna vrednost:
        list[str]: Lista vremenskih slotova u formatu "HH:MM".
    """
    try:
        start_str, end_str = working_hours_str.split("-")
        start = datetime.strptime(start_str, "%H:%M")
        end = datetime.strptime(end_str, "%H:%M")
    except Exception:
        start = datetime.strptime("09:00", "%H:%M")
        end = datetime.strptime("16:00", "%H:%M")

    slots = []
    current = start

    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=30)

    return slots


def get_legacy_user(request):
    """
    Vraća legacy korisnika povezanog sa trenutno ulogovanim Django korisnikom.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        User | None: Legacy korisnik ako postoji, u suprotnom None.
    """
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.profile.legacy_user
    except Exception:
        return None


def get_staff_for_request(request):
    """
    Pronalaži zapis zaposlenog za trenutno ulogovanog korisnika.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        Staff | None: Objekat zaposlenog ako postoji, u suprotnom None.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return None
    return (
        Staff.objects
        .select_related("userid", "salonid")
        .filter(userid=legacy)
        .first()
    )


STATUS_BOOKED = 1
STATUS_CANCELED = 2


def _slots_needed(duration_min: int) -> int:
    """
    Izračunava broj polusatnih slotova potrebnih za uslugu zadatog trajanja.

    Parametri:
        duration_min (int): Trajanje usluge u minutima.

    Povratna vrednost:
        int: Broj potrebnih slotova.
    """
    return max(1, ceil(int(duration_min) / 30))


def _get_owner_and_salon(request):
    """
    Pronalaži vlasnika i njegov salon na osnovu trenutno ulogovanog korisnika.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        tuple: Par objekata (owner, salon).

    Izuzeci:
        PermissionError: Ako legacy korisnik ne postoji.
    """
    legacy_user = get_legacy_user(request)
    if not legacy_user:
        raise PermissionError("Legacy user not found")

    owner = get_object_or_404(Owner, userid=legacy_user)
    salon = owner.salonid
    return owner, salon


@login_required
@require_http_methods(["GET", "POST"])
def owner_services(request):
    """
    Prikazuje aktivne usluge vlasnika salona i omogućava dodavanje nove usluge.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponse: Renderovana stranica sa listom usluga i formom za dodavanje.
    """
    owner, salon = _get_owner_and_salon(request)

    form = ServiceForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"]
        category = form.cleaned_data["category"]

        if Service.objects.filter(
            salonid=salon,
            name=name,
            category=category,
            is_active=True
        ).exists():
            form.add_error("name", "Usluga već postoji za ovaj salon (isti naziv i kategorija).")
        else:
            obj = form.save(commit=False)
            obj.salonid = salon
            obj.save()
            return redirect("owner_services")

    services = Service.objects.filter(salonid=salon, is_active=True).order_by("name")

    return render(request, "owner-services.html", {
        "services": services,
        "form": form,
        "salon": salon,
        "owner": owner,
    })


@login_required
@require_POST
def owner_service_delete(request, service_id: int):
    """
    Deaktivira uslugu vlasnika salona postavljanjem polja is_active na False.

    Parametri:
        request: HTTP zahtev.
        service_id (int): Identifikator usluge koja se briše.

    Povratna vrednost:
        HttpResponseRedirect: Preusmerenje na stranicu sa uslugama vlasnika.
    """
    owner, salon = _get_owner_and_salon(request)

    service = get_object_or_404(Service, idservice=service_id, salonid=salon)
    service.is_active = False
    service.save(update_fields=["is_active"])

    return redirect("owner_services")


@login_required
def owner_salon(request):
    """
    Omogućava vlasniku pregled i izmenu podataka o svom profilu i salonu.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponse: Renderovana stranica sa formama za izmenu vlasnika i salona.
    """
    owner, salon = _get_owner_and_salon(request)
    legacy_user = get_legacy_user(request)

    if request.method == "POST":
        owner_form = OwnerForm(request.POST, instance=legacy_user)
        salon_form = SalonForm(request.POST, instance=salon)

        if owner_form.is_valid() and salon_form.is_valid():
            owner_form.save()
            salon_form.save()
            return redirect("owner_salon")
    else:
        owner_form = OwnerForm(instance=legacy_user)
        salon_form = SalonForm(instance=salon)

    return render(request, "owner-salon.html", {
        "salon": salon,
        "owner": owner,
        "owner_form": owner_form,
        "salon_form": salon_form,
    })


@login_required
def client_free_slots_by_salon(request, salon_id: int, date_str: str):
    """
    Vraća slobodne termine za zadati salon i datum, uz proveru trajanja usluge.

    Parametri:
        request: HTTP zahtev.
        salon_id (int): Identifikator salona.
        date_str (str): Datum u formatu YYYY-MM-DD.

    Povratna vrednost:
        JsonResponse: JSON lista slobodnih slotova ili JSON poruka o grešci.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return JsonResponse({"error": "Niste ulogovani."}, status=403)

    day = parse_date(date_str)
    if not day:
        return JsonResponse({"error": "Neispravan datum."}, status=400)

    salon = Salon.objects.filter(salonid=salon_id).first()
    if not salon:
        return JsonResponse({"error": "Salon ne postoji."}, status=404)

    WORK_HOURS = generate_work_slots(salon.working_hours)
    IDX = {t: i for i, t in enumerate(WORK_HOURS)}

    try:
        service_id = int(request.GET.get("service_id", "0"))
    except Exception:
        service_id = 0

    service_obj = None
    if service_id:
        service_obj = Service.objects.filter(
            idservice=service_id,
            salonid_id=salon_id,
            is_active=True,
        ).first()

        if not service_obj:
            return JsonResponse({"error": "Usluga ne pripada ovom salonu."}, status=400)

    needed = _slots_needed(service_obj.duration) if service_obj else 1

    staff_list = Staff.objects.filter(
        salonid_id=salon_id
    ).select_related("userid")

    if not staff_list.exists():
        return JsonResponse([], safe=False)

    now_local = timezone.localtime(timezone.now())
    today = now_local.date()

    current_slot_idx = None
    if day == today:
        now_str = now_local.strftime("%H:%M")
        current_slot_idx = len(WORK_HOURS)

        for t in WORK_HOURS:
            if t > now_str:
                current_slot_idx = IDX[t]
                break

    start = timezone.make_aware(
        timezone.datetime(day.year, day.month, day.day),
        timezone.get_current_timezone()
    )
    end = start + timedelta(days=1)

    result = []

    for st in staff_list:
        appts = Appointment.objects.filter(
            staffid_id=st.staffid,
            datetime__gte=start,
            datetime__lt=end,
            status=STATUS_BOOKED
        ).select_related("serviceid")

        taken_slots = set()

        for a in appts:
            dur = int(a.serviceid.duration)
            blocks = _slots_needed(dur)

            t = timezone.localtime(a.datetime).strftime("%H:%M")
            if t not in IDX:
                continue

            base = IDX[t]

            for k in range(blocks):
                j = base + k
                if j < len(WORK_HOURS):
                    taken_slots.add(WORK_HOURS[j])

        free = []

        for t in WORK_HOURS:
            i = IDX[t]

            if t in taken_slots:
                continue

            if current_slot_idx is not None and i < current_slot_idx:
                continue

            free.append(t)

        free_set = set(free)

        for t in free:
            i = IDX[t]
            ok = True

            for k in range(needed):
                j = i + k
                if j >= len(WORK_HOURS) or WORK_HOURS[j] not in free_set:
                    ok = False
                    break

            if ok:
                result.append({
                    "time": t,
                    "staff_id": st.staffid,
                    "staff_name": f"{st.userid.name} {st.userid.surname}"
                })

    result.sort(key=lambda x: (x["time"], x["staff_name"]))
    return JsonResponse(result, safe=False)


@login_required
@require_POST
def client_book_appointment(request):
    """
    Kreira novu rezervaciju termina za klijenta uz proveru konflikta i trajanja usluge.

    Parametri:
        request: HTTP zahtev sa JSON telom koje sadrži datum, vreme, uslugu, osoblje i salon.

    Povratna vrednost:
        JsonResponse: JSON odgovor o uspehu rezervacije ili JSON poruka o grešci.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return JsonResponse({"error": "Niste ulogovani."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        date_str = payload["date"]
        time_str = payload["time"]
        service_id = int(payload["service_id"])
        staff_id = int(payload["staff_id"])
        salon_id = int(payload["salon_id"])
    except Exception:
        return JsonResponse({"error": "Neispravan JSON body."}, status=400)

    day = parse_date(date_str)
    if not day:
        return JsonResponse({"error": "Neispravan datum."}, status=400)

    salon = Salon.objects.filter(salonid=salon_id).first()
    if not salon:
        return JsonResponse({"error": "Salon ne postoji."}, status=404)

    WORK_HOURS = generate_work_slots(salon.working_hours)
    IDX = {t: i for i, t in enumerate(WORK_HOURS)}

    if time_str not in IDX:
        return JsonResponse({"error": "Neispravno vreme."}, status=400)

    staff_obj = Staff.objects.filter(
        staffid=staff_id,
        salonid_id=salon_id
    ).first()

    if not staff_obj:
        return JsonResponse({"error": "Osoblje nije iz ovog salona."}, status=400)

    service_obj = Service.objects.filter(
        idservice=service_id,
        salonid_id=salon_id,
        is_active=True,
    ).first()

    if not service_obj:
        return JsonResponse({"error": "Usluga nije dostupna."}, status=400)

    needed = _slots_needed(service_obj.duration)

    dt_start = timezone.make_aware(
        timezone.datetime.fromisoformat(f"{date_str}T{time_str}:00"),
        timezone.get_current_timezone()
    )

    if dt_start < timezone.localtime(timezone.now()):
        return JsonResponse({"error": "Ne možeš zakazati termin u prošlosti."}, status=400)

    start_idx = IDX[time_str]
    end_idx = start_idx + needed - 1

    if end_idx >= len(WORK_HOURS):
        return JsonResponse(
            {"error": "Molimo izaberite drugi termin — nema dovoljno vremena za vašu uslugu."},
            status=400
        )

    requested_slots = {WORK_HOURS[start_idx + k] for k in range(needed)}

    with transaction.atomic():
        day_start = timezone.make_aware(
            timezone.datetime(day.year, day.month, day.day),
            timezone.get_current_timezone()
        )
        day_end = day_start + timedelta(days=1)

        existing = (
            Appointment.objects
            .select_for_update()
            .filter(
                staffid_id=staff_obj.staffid,
                datetime__gte=day_start,
                datetime__lt=day_end,
                status=STATUS_BOOKED
            )
            .select_related("serviceid")
        )

        taken_slots = set()

        for a in existing:
            dur = int(a.serviceid.duration) if a.serviceid_id else 30
            blocks = _slots_needed(dur)

            t = timezone.localtime(a.datetime).strftime("%H:%M")
            if t not in IDX:
                continue

            base = IDX[t]
            for k in range(blocks):
                j = base + k
                if j < len(WORK_HOURS):
                    taken_slots.add(WORK_HOURS[j])

        if requested_slots & taken_slots:
            return JsonResponse(
                {"error": "Molimo izaberite drugi termin — nema dovoljno vremena za vašu uslugu."},
                status=409
            )

        a = Appointment.objects.create(
            userid_id=legacy.useriid,
            staffid_id=staff_obj.staffid,
            serviceid_id=service_id,
            datetime=dt_start,
            status=STATUS_BOOKED
        )

        google_event_id = create_google_event_for_appointment(a)
        if google_event_id:
            a.google_event_id = google_event_id
            a.save(update_fields=["google_event_id"])

        on_appointment_booked(a)

    return JsonResponse({"ok": True, "appointment_id": a.appointmentid})


@login_required
def klijent_moje_rez(request):
    """
    Prikazuje klijentu njegove buduće, prošle i otkazane rezervacije.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponse: Renderovana stranica sa podelom rezervacija po statusu i vremenu.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return render(request, "klijentMojeRez.html", {
            "upcoming": [],
            "past": [],
            "canceled": []
        })

    now_local = timezone.localtime(timezone.now())

    base_qs = (
        Appointment.objects
        .filter(userid_id=legacy.useriid)
        .select_related("serviceid", "staffid__salonid")
    )

    upcoming = (
        base_qs
        .filter(status=STATUS_BOOKED, datetime__gte=now_local)
        .order_by("datetime")
    )

    past = (
        base_qs
        .filter(status=STATUS_BOOKED, datetime__lt=now_local)
        .order_by("datetime")
    )

    canceled = (
        base_qs
        .filter(status=STATUS_CANCELED)
        .order_by("datetime")
    )

    return render(request, "klijentMojeRez.html", {
        "upcoming": upcoming,
        "past": past,
        "canceled": canceled,
        "now": now_local,
    })


@login_required
@require_POST
def client_cancel_appointment(request, appointment_id: int):
    """
    Otkazuje klijentov budući aktivni termin i uklanja odgovarajući Google Calendar događaj.

    Parametri:
        request: HTTP zahtev.
        appointment_id (int): Identifikator termina koji se otkazuje.

    Povratna vrednost:
        HttpResponseRedirect: Preusmerenje na stranicu sa klijentovim rezervacijama.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return redirect("klijent_moje_rez")

    a = get_object_or_404(
        Appointment,
        appointmentid=appointment_id,
        userid_id=legacy.useriid
    )

    now_local = timezone.localtime(timezone.now())
    if a.status != STATUS_BOOKED:
        return redirect("klijent_moje_rez")

    if timezone.localtime(a.datetime) < now_local:
        return redirect("klijent_moje_rez")

    delete_google_event_for_appointment(a)

    a.status = STATUS_CANCELED
    a.google_event_id = None
    a.save(update_fields=["status", "google_event_id"])

    on_appointment_canceled(a)

    return redirect("klijent_moje_rez")


@login_required
def api_staff_book_data(request):
    """
    Vraća podatke potrebne osoblju za zakazivanje termina, uključujući salon, usluge i zaposlene.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        JsonResponse: JSON objekat sa podacima o salonu, uslugama i osoblju ili greška pristupa.
    """
    staff = get_staff_for_request(request)
    if not staff:
        return JsonResponse({"error": "forbidden"}, status=403)

    salon = staff.salonid

    services = list(Service.objects.filter(salonid=salon, is_active=True).values("idservice", "name", "duration", "category"))
    staff_list = list(
        Staff.objects
        .select_related("userid")
        .filter(salonid=salon)
        .order_by("userid__surname", "userid__name")
        .values("staffid", "userid__name", "userid__surname", "position")
    )

    return JsonResponse({
        "salon_id": salon.salonid,
        "services": services,
        "staff_list": staff_list,
    })


@login_required
@require_POST
def api_staff_cancel_appointment(request, appointment_id: int):
    """
    Otkazuje termin iz ugla osoblja ako termin pripada salonu u kome korisnik radi.

    Parametri:
        request: HTTP zahtev.
        appointment_id (int): Identifikator termina koji se otkazuje.

    Povratna vrednost:
        JsonResponse: JSON odgovor o uspehu otkazivanja ili JSON poruka o grešci.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return JsonResponse({"error": "forbidden"}, status=403)

    a = get_object_or_404(Appointment, appointmentid=appointment_id)

    if not user_is_staff_in_salon(request, a.staffid.salonid_id):
        return JsonResponse({"error": "forbidden"}, status=403)

    if a.status != STATUS_BOOKED:
        return JsonResponse({"error": "Termin nije aktivan."}, status=400)

    now_local = timezone.localtime(timezone.now())
    if timezone.localtime(a.datetime) < now_local:
        return JsonResponse({"error": "Termin je već prošao."}, status=400)

    delete_google_event_for_appointment(a)

    a.status = STATUS_CANCELED
    a.google_event_id = None
    a.save(update_fields=["status", "google_event_id"])

    on_appointment_canceled(a)

    return JsonResponse({"ok": True})


@login_required
def osoblje_zakazi_termin(request):
    """
    Prikazuje stranicu za zakazivanje termina od strane zaposlenog u salonu.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponse: Renderovana stranica za zakazivanje ili stranica bez pristupa.
    """
    staff = get_staff_for_request(request)
    if not staff:
        return render(request, "no_access.html", status=403)

    salon = staff.salonid

    services = Service.objects.filter(salonid=salon, is_active=True).order_by("category", "name")
    staff_list = (
        Staff.objects
        .select_related("userid")
        .filter(salonid=salon)
        .order_by("userid__surname", "userid__name")
    )

    today = timezone.localdate()

    return render(request, "osoblje_zakazi_termin.html", {
        "salon_name": salon.name,
        "staff_name": f"{staff.userid.name} {staff.userid.surname}",
        "staff_role": staff.position,
        "services": services,
        "staff_list": staff_list,
        "min_date": today.isoformat(),
        "STATUS_BOOKED": STATUS_BOOKED,
        "STATUS_CANCELED": STATUS_CANCELED,
    })


@login_required
def api_staff_free_slots(request):
    """
    Vraća slobodne slotove za osoblje, uz mogućnost filtriranja po zaposlenom i usluzi.

    Parametri:
        request: HTTP zahtev sa query parametrima date, service_id i opciono staff_id.

    Povratna vrednost:
        JsonResponse: JSON lista slobodnih slotova ili JSON poruka o grešci.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return JsonResponse({"error": "Niste ulogovani."}, status=403)

    day_str = request.GET.get("date")
    day = parse_date(day_str) if day_str else None
    if not day:
        return JsonResponse({"error": "Neispravan datum."}, status=400)

    try:
        service_id = int(request.GET.get("service_id", "0"))
    except Exception:
        service_id = 0

    if not service_id:
        return JsonResponse({"error": "service_id je obavezan."}, status=400)

    try:
        staff_id = int(request.GET.get("staff_id", "0"))
    except Exception:
        staff_id = 0

    target_salon = None
    target_staff = None

    if staff_id:
        target_staff = Staff.objects.select_related("salonid", "userid").filter(staffid=staff_id).first()
        if not target_staff:
            return JsonResponse({"error": "Neispravno osoblje."}, status=400)

        target_salon = target_staff.salonid

        if not user_is_staff_in_salon(request, target_salon.salonid):
            return JsonResponse({"error": "forbidden"}, status=403)

    else:
        st_any = Staff.objects.select_related("salonid").filter(userid=legacy).first()
        if not st_any:
            return JsonResponse({"error": "Niste prijavljeni kao osoblje."}, status=403)
        target_salon = st_any.salonid

    service_obj = Service.objects.filter(
        idservice=service_id,
        salonid=target_salon,
        is_active=True,
    ).first()

    if not service_obj:
        return JsonResponse({"error": "Usluga ne pripada ovom salonu."}, status=400)

    WORK_HOURS = generate_work_slots(target_salon.working_hours)
    IDX = {t: i for i, t in enumerate(WORK_HOURS)}

    needed = _slots_needed(service_obj.duration)

    staff_qs = Staff.objects.filter(salonid=target_salon).select_related("userid")
    if staff_id:
        staff_qs = staff_qs.filter(staffid=staff_id)

    if not staff_qs.exists():
        return JsonResponse([], safe=False)

    now_local = timezone.localtime(timezone.now())
    today = now_local.date()

    current_slot_idx = None
    if day == today:
        now_str = now_local.strftime("%H:%M")
        current_slot_idx = len(WORK_HOURS)
        for t in WORK_HOURS:
            if t > now_str:
                current_slot_idx = IDX[t]
                break

    start = timezone.make_aware(
        timezone.datetime(day.year, day.month, day.day),
        timezone.get_current_timezone()
    )
    end = start + timedelta(days=1)

    result = []

    for st in staff_qs:
        appts = (
            Appointment.objects
            .filter(
                staffid_id=st.staffid,
                datetime__gte=start,
                datetime__lt=end,
                status=STATUS_BOOKED
            )
            .select_related("serviceid")
        )

        taken_slots = set()

        for a in appts:
            dur = int(a.serviceid.duration) if a.serviceid_id else 30
            blocks = _slots_needed(dur)

            t = timezone.localtime(a.datetime).strftime("%H:%M")
            if t not in IDX:
                continue

            base = IDX[t]
            for k in range(blocks):
                j = base + k
                if j < len(WORK_HOURS):
                    taken_slots.add(WORK_HOURS[j])

        free = []
        for t in WORK_HOURS:
            i = IDX[t]

            if t in taken_slots:
                continue

            if current_slot_idx is not None and i < current_slot_idx:
                continue

            free.append(t)

        free_set = set(free)

        for t in free:
            i = IDX[t]
            ok = True

            for k in range(needed):
                j = i + k
                if j >= len(WORK_HOURS) or WORK_HOURS[j] not in free_set:
                    ok = False
                    break

            if ok:
                result.append({
                    "time": t,
                    "staff_id": st.staffid,
                    "staff_name": f"{st.userid.name} {st.userid.surname}"
                })

    print("STAFF_ID =", staff_id)
    print("RESULT TIMES =", [x["time"] for x in result])
    result.sort(key=lambda x: (x["time"], x["staff_name"]))
    return JsonResponse(result, safe=False)


def user_is_staff_in_salon(request, salon_id: int) -> bool:
    """
    Proverava da li je trenutno ulogovani korisnik član osoblja u zadatom salonu.

    Parametri:
        request: HTTP zahtev.
        salon_id (int): Identifikator salona.

    Povratna vrednost:
        bool: True ako je korisnik osoblje u datom salonu, inače False.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return False
    return Staff.objects.filter(userid=legacy, salonid_id=salon_id).exists()


@login_required
@require_POST
def api_staff_book_appointment(request):
    """
    Kreira novu rezervaciju termina iz ugla osoblja, za postojećeg ili novog klijenta.

    Parametri:
        request: HTTP zahtev sa JSON telom koje sadrži podatke o klijentu, datumu, vremenu, usluzi i zaposlenom.

    Povratna vrednost:
        JsonResponse: JSON odgovor o uspehu rezervacije i Google sinhronizaciji ili JSON poruka o grešci.
    """
    legacy = get_legacy_user(request)
    if not legacy:
        return JsonResponse({"error": "Niste ulogovani."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        client_name = (payload.get("client_name") or "").strip()
        client_phone = (payload.get("client_phone") or "").strip()
        client_email = (payload.get("client_email") or "").strip().lower()

        date_str = payload["date"]
        time_str = payload["time"]
        service_id = int(payload["service_id"])
        staff_id = int(payload["staff_id"])
    except Exception:
        return JsonResponse({"error": "Neispravan JSON body."}, status=400)

    if not client_name or not client_phone:
        return JsonResponse({"error": "Ime i telefon su obavezni."}, status=400)

    day = parse_date(date_str)
    if not day:
        return JsonResponse({"error": "Neispravan datum."}, status=400)

    staff_obj = Staff.objects.select_related("salonid").filter(staffid=staff_id).first()
    if not staff_obj:
        return JsonResponse({"error": "Neispravno osoblje."}, status=400)

    salon = staff_obj.salonid

    if not user_is_staff_in_salon(request, salon.salonid):
        return JsonResponse({"error": "forbidden"}, status=403)

    service_obj = Service.objects.filter(
        idservice=service_id,
        salonid=salon,
        is_active=True,
    ).first()

    if not service_obj:
        return JsonResponse({"error": "Usluga ne pripada ovom salonu."}, status=400)

    WORK_HOURS = generate_work_slots(salon.working_hours)
    IDX = {t: i for i, t in enumerate(WORK_HOURS)}

    if time_str not in IDX:
        return JsonResponse({"error": "Neispravno vreme."}, status=400)

    needed = _slots_needed(service_obj.duration)

    dt_start = timezone.make_aware(
        timezone.datetime.fromisoformat(f"{date_str}T{time_str}:00"),
        timezone.get_current_timezone()
    )

    if dt_start < timezone.localtime(timezone.now()):
        return JsonResponse({"error": "Ne možeš zakazati termin u prošlosti."}, status=400)

    start_idx = IDX[time_str]
    end_idx = start_idx + needed - 1

    if end_idx >= len(WORK_HOURS):
        return JsonResponse(
            {"error": "Molimo izaberite drugi termin — nema dovoljno vremena za ovu uslugu."},
            status=400
        )

    requested_slots = {WORK_HOURS[start_idx + k] for k in range(needed)}

    client_user = None

    if client_email:
        client_user = User.objects.filter(email__iexact=client_email).first()

    if not client_user:
        if not client_email:
            client_email = f"guest_{secrets.token_hex(6)}@no-login.local"

        parts = client_name.split()
        name = parts[0][:30]
        surname = (" ".join(parts[1:]) if len(parts) > 1 else "-")[:30]

        client_user = User.objects.create(
            name=name,
            surname=surname,
            email=client_email[:40],
            password="",
            phone=client_phone[:20],
        )
    else:
        if client_phone and not client_user.phone:
            client_user.phone = client_phone[:20]
            client_user.save(update_fields=["phone"])

    with transaction.atomic():
        day_start = timezone.make_aware(
            timezone.datetime(day.year, day.month, day.day),
            timezone.get_current_timezone()
        )
        day_end = day_start + timedelta(days=1)

        existing = (
            Appointment.objects
            .select_for_update()
            .filter(
                staffid_id=staff_obj.staffid,
                datetime__gte=day_start,
                datetime__lt=day_end,
                status=STATUS_BOOKED
            )
            .select_related("serviceid")
        )

        taken_slots = set()

        for a in existing:
            dur = int(a.serviceid.duration) if a.serviceid_id else 30
            blocks = _slots_needed(dur)

            t = timezone.localtime(a.datetime).strftime("%H:%M")
            if t not in IDX:
                continue

            base = IDX[t]
            for k in range(blocks):
                j = base + k
                if j < len(WORK_HOURS):
                    taken_slots.add(WORK_HOURS[j])

        if requested_slots & taken_slots:
            return JsonResponse(
                {"error": "Molimo izaberite drugi termin — nema dovoljno vremena za ovu uslugu."},
                status=409
            )

        appointment = Appointment.objects.create(
            userid_id=client_user.useriid,
            staffid_id=staff_obj.staffid,
            serviceid_id=service_obj.idservice,
            datetime=dt_start,
            status=STATUS_BOOKED
        )

        google_event_id = create_google_event_for_appointment(appointment)
        if google_event_id:
            appointment.google_event_id = google_event_id
            appointment.save(update_fields=["google_event_id"])

        on_appointment_booked(appointment)

    return JsonResponse({
        "ok": True,
        "appointment_id": appointment.appointmentid,
        "google_synced": bool(appointment.google_event_id),
    })


@login_required
def osoblje_kalendar(request):
    """
    Prikazuje početnu stranicu kalendara za zaposlenog.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponse: Renderovana stranica kalendara ili stranica bez pristupa.
    """
    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return render(request, "no_access.html", status=403)

    staff = (
        Staff.objects
        .select_related("userid", "salonid")
        .filter(userid=legacy_user)
        .first()
    )

    if not staff:
        return render(request, "no_access.html", status=403)

    today = timezone.localdate()

    return render(request, "osoblje_kalendar.html", {
        "staff_name": f"{legacy_user.name} {legacy_user.surname}",
        "staff_role": staff.position,
        "salon_name": staff.salonid.name,
        "initial_year": today.year,
        "initial_month": today.month,
    })


@login_required
def api_osoblje_kalendar_mesec(request):
    """
    Vraća mesečni prikaz kalendara zaposlenog sa informacijom koji dani imaju termine.

    Parametri:
        request: HTTP zahtev sa query parametrima year i month.

    Povratna vrednost:
        JsonResponse: JSON objekat sa strukturom meseca ili JSON poruka o grešci.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
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
        staffid__userid=legacy_user,
        datetime__date__gte=start_day,
        datetime__date__lte=end_day
    )

    days_with_appts = set(qs.values_list("datetime__date", flat=True))

    month_title = f"{calendar.month_name[month]} {year}"

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

    return JsonResponse({
        "title": month_title,
        "year": year,
        "month": month,
        "weeks": payload_weeks,
    })


@login_required
def api_osoblje_termini_dan(request):
    """
    Vraća listu termina zaposlenog za jedan konkretan dan.

    Parametri:
        request: HTTP zahtev sa query parametrom date.

    Povratna vrednost:
        JsonResponse: JSON objekat sa datumom i listom termina ili JSON poruka o grešci.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return JsonResponse({"error": "forbidden"}, status=403)

    day_str = request.GET.get("date")
    day = parse_date(day_str) if day_str else None
    if not day:
        return JsonResponse({"error": "bad date"}, status=400)

    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)

    qs = (
        Appointment.objects
        .select_related("userid", "serviceid", "staffid")
        .filter(
            staffid__userid=legacy_user,
            datetime__gte=start,
            datetime__lt=end
        )
        .order_by("datetime")
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
            "status": a.status,
            "can_cancel": (
                a.status == STATUS_BOOKED and
                start_local > timezone.localtime(timezone.now())
            ),
        })

    return JsonResponse({
        "date": day.isoformat(),
        "appointments": appts,
    })


def google_connect(request):
    """
    Pokreće OAuth proces povezivanja korisnika sa Google Calendar nalogom.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponseRedirect: Preusmerenje na Google autorizacionu stranicu ili login stranicu.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        autogenerate_code_verifier=True,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    request.session["google_oauth_state"] = state
    request.session["google_code_verifier"] = flow.code_verifier

    return redirect(authorization_url)


def google_callback(request):
    """
    Obrađuje povratni OAuth zahtev sa Google-a i čuva pristupne podatke za Google Calendar konekciju.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponseRedirect: Preusmerenje na klijentsku početnu stranicu ili login stranicu.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    state = request.session.get("google_oauth_state")
    code_verifier = request.session.get("google_code_verifier")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
        state=state,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        code_verifier=code_verifier,
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    service = build("calendar", "v3", credentials=credentials)
    calendar_info = service.calendarList().get(calendarId="primary").execute()

    try:
        legacy_user = request.user.profile.legacy_user
    except Exception:
        return redirect("klijent_pregled")

    conn, created = GoogleCalendarConnection.objects.get_or_create(
        userid=legacy_user,
        defaults={
            "google_email": calendar_info.get("id"),
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "scopes": " ".join(credentials.scopes) if credentials.scopes else "",
            "expiry": credentials.expiry,
        }
    )

    if not created:
        conn.google_email = calendar_info.get("id")
        conn.access_token = credentials.token
        conn.token_uri = credentials.token_uri
        conn.scopes = " ".join(credentials.scopes) if credentials.scopes else ""
        conn.expiry = credentials.expiry

        if credentials.refresh_token:
            conn.refresh_token = credentials.refresh_token

        conn.save()

    request.session.pop("google_oauth_state", None)
    request.session.pop("google_code_verifier", None)

    return redirect("klijent_pregled")


@login_required
@require_POST
def google_disconnect(request):
    """
    Prekida vezu između korisnika i Google Calendar naloga brisanjem sačuvane konekcije.

    Parametri:
        request: HTTP zahtev.

    Povratna vrednost:
        HttpResponseRedirect: Preusmerenje na klijentsku početnu stranicu.
    """
    legacy = get_legacy_user(request)
    if legacy:
        GoogleCalendarConnection.objects.filter(userid=legacy).delete()
    return redirect("klijent_pregled")