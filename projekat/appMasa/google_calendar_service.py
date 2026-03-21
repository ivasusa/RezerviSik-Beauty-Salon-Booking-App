from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from appIva.models import GoogleCalendarConnection, UserProfile


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _is_registered_user(legacy_user):
    """
    Legacy user smatramo registrovanim korisnikom sistema
    samo ako postoji UserProfile veza ka Django user-u.
    """
    if not legacy_user:
        return False

    return UserProfile.objects.filter(legacy_user=legacy_user).exists()


def get_google_credentials(legacy_user):
    """
    Vraća Google credentials samo ako:
    1) legacy user predstavlja registrovanog korisnika sistema
    2) taj korisnik ima sačuvanu Google konekciju

    U suprotnom vraća None.
    """
    if not _is_registered_user(legacy_user):
        return None

    connection = GoogleCalendarConnection.objects.filter(userid=legacy_user).first()
    if not connection:
        return None

    credentials = Credentials(
        token=connection.access_token,
        refresh_token=connection.refresh_token,
        token_uri=connection.token_uri or "https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )

    # osveži token ako je istekao
    try:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            connection.access_token = credentials.token
            if getattr(credentials, "refresh_token", None):
                connection.refresh_token = credentials.refresh_token
            connection.expiry = credentials.expiry
            connection.save(update_fields=["access_token", "refresh_token", "expiry"])
    except Exception:
        return None

    return credentials


def create_google_event_for_appointment(appointment):
    """
    Pravi Google Calendar event za dati appointment samo ako
    korisnik ima validnu Google konekciju.

    Ako ne može da napravi event, vraća None.
    """
    try:
        credentials = get_google_credentials(appointment.userid)
        if not credentials:
            return None

        service = build("calendar", "v3", credentials=credentials)

        start_dt = timezone.localtime(appointment.datetime)
        duration_minutes = int(appointment.serviceid.duration) if appointment.serviceid and appointment.serviceid.duration else 30
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        salon = appointment.staffid.salonid
        service_obj = appointment.serviceid
        staff_user = appointment.staffid.userid
        client_user = appointment.userid

        event_body = {
            "summary": f"RezerviŠik – {service_obj.name}",
            "location": salon.address or "",
            "description": (
                f"Salon: {salon.name}\n"
                f"Adresa: {salon.address}\n"
                f"Usluga: {service_obj.name}\n"
                f"Osoblje: {staff_user.name} {staff_user.surname}\n"
                f"Klijent: {client_user.name} {client_user.surname}\n"
                f"Kontakt salona: {salon.contact}"
            ),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Europe/Belgrade",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Belgrade",
            },
        }

        created_event = service.events().insert(
            calendarId="primary",
            body=event_body
        ).execute()

        return created_event.get("id")

    except Exception:
        return None


def delete_google_event_for_appointment(appointment):
    """
    Briše Google event ako postoji google_event_id i ako korisnik
    ima validnu Google konekciju.
    Ako ne uspe, samo ignoriše grešku.
    """
    if not appointment.google_event_id:
        return False

    try:
        credentials = get_google_credentials(appointment.userid)
        if not credentials:
            return False

        service = build("calendar", "v3", credentials=credentials)

        service.events().delete(
            calendarId="primary",
            eventId=appointment.google_event_id
        ).execute()

        return True

    except Exception:
        return False