# appSandra/services/event_notifications.py
# Autor: Sandra Bubanja
# Opis: Servis koji kreira notifikacije u bazi prilikom
# zakazivanja ili otkazivanja termina.

from django.utils import timezone
from appIva.models import Notification, Appointment


# ============================================================
# Tipovi notifikacija
# ============================================================
# 1 = booking/confirmation (termin uspešno zakazan)
# 2 = reminder (podsetnik za sutra)
# 3 = cancel (termin otkazan)


# ============================================================
# Event funkcije
# ============================================================

def on_appointment_booked(appointment: Appointment):
    """
    Poziva se kada se termin uspešno zakazuje.

    Kreira notifikaciju u bazi da korisnik vidi potvrdu o
    zakazivanju termina.

    Args:
        appointment (Appointment): instanca zakazanog termina

    Returns:
        Notification: kreirana notifikacija (baza)
    """
    return Notification.objects.create(
        appointmentid=appointment,
        userid=appointment.userid,
        message="Termin je uspešno zakazan.",
        sendat=timezone.now(),
        type=1
    )


def on_appointment_canceled(appointment: Appointment):
    """
    Poziva se kada se termin otkaže.

    Kreira notifikaciju u bazi da korisnik vidi obaveštenje
    o otkazivanju termina.

    Args:
        appointment (Appointment): instanca otkazanog termina

    Returns:
        Notification: kreirana notifikacija (baza)
    """
    return Notification.objects.create(
        appointmentid=appointment,
        userid=appointment.userid,
        message="Termin je otkazan.",
        sendat=timezone.now(),
        type=3
    )