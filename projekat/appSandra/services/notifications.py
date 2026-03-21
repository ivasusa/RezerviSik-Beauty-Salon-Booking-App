# appSandra/services/notifications.py

from datetime import datetime as dt, time as dtime, timedelta
from django.utils import timezone
from appIva.models import Appointment, Notification
from django.core.mail import send_mail
from django.conf import settings

APPOINTMENT_STATUS_SCHEDULED = 1
NOTIF_TYPE_REMINDER = 2


def _send_email(to_email: str, message: str) -> None:
    """Šalje email korisniku sa podsetnikom."""
    if not to_email:
        return

    send_mail(
        subject="Podsetnik za termin sutra",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )


def _tomorrow_bounds_local():
    """Vrati granice sutrašnjeg dana po lokalnom vremenu."""
    tomorrow = timezone.localdate() + timedelta(days=1)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(dt.combine(tomorrow, dtime.min), tz)
    end = start + timedelta(days=1)
    return tomorrow, start, end


def send_daily_reminders() -> int:
    """
    Šalje podsetnike za sve termine koji su zakazani sutra.
    """
    _, start, end = _tomorrow_bounds_local()

    # svi termini sutra sa statusom zakazan
    appointments = (
        Appointment.objects
        .select_related("userid", "serviceid", "serviceid__salonid")
        .filter(
            datetime__gte=start,
            datetime__lt=end,
            status=APPOINTMENT_STATUS_SCHEDULED
        )
        .order_by("datetime")
    )

    sent_count = 0

    for a in appointments:
        user = a.userid  # Django ORM polje
        email = (getattr(user, "email", "") or "").strip()

        if not email:
            continue  # preskoči ako korisnik nema email

        # proveri da li je notifikacija već poslana
        if Notification.objects.filter(
            appointmentid=a,
            type=NOTIF_TYPE_REMINDER
        ).exists():
            continue

        salon_name = a.serviceid.salonid.name
        service_name = a.serviceid.name
        dt_str = timezone.localtime(a.datetime).strftime("%d.%m.%Y %H:%M")

        message = (
            f"Podsetnik za termin sutra\n"
            f"Datum i vreme: {dt_str}\n"
            f"Usluga: {service_name}\n"
            f"Salon: {salon_name}"
        )

        _send_email(email, message)

        # upis u Notification
        Notification.objects.create(
            appointmentid=a,
            userid=user,
            message=message[:255],
            sendat=timezone.now(),
            type=NOTIF_TYPE_REMINDER
        )

        sent_count += 1

    return sent_count