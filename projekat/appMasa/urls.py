from django.urls import path
from . import views

urlpatterns = [
    path("owner/services/", views.owner_services, name="owner_services"),
    path("owner/services/<int:service_id>/delete/", views.owner_service_delete, name="owner_service_delete"),
    path("owner/salon/", views.owner_salon, name="owner_salon"),

    path("api/client/free-slots/<int:salon_id>/<str:date_str>/", views.client_free_slots_by_salon, name="client_free_slots_by_salon"),
    path("api/client/book/", views.client_book_appointment, name="client_book_appointment"),
    path('klijent/moje-rez/', views.klijent_moje_rez, name='klijent_moje_rez'),
    path("klijent/appointments/<int:appointment_id>/cancel/", views.client_cancel_appointment, name="client_cancel_appointment"),
    path("osoblje/zakazi-termin/", views.osoblje_zakazi_termin, name="osoblje_zakazi_termin"),
    path("osoblje/kalendar/", views.osoblje_kalendar, name="osoblje_kalendar"),
    path("osoblje/api/kalendar-mesec/", views.api_osoblje_kalendar_mesec, name="api_osoblje_kalendar_mesec"),
    path("osoblje/api/termini-dan/", views.api_osoblje_termini_dan, name="api_osoblje_termini_dan"),
    path("osoblje/api/staff-book-data/", views.api_staff_book_data, name="api_staff_book_data"),
    path("osoblje/api/free-slots/", views.api_staff_free_slots, name="api_staff_free_slots"),
    path("osoblje/api/book/", views.api_staff_book_appointment, name="api_staff_book_appointment"),
    path("osoblje/api/appointments/<int:appointment_id>/cancel/", views.api_staff_cancel_appointment, name="api_staff_cancel_appointment",),
    path("google/connect/", views.google_connect, name="google_connect"),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("google/disconnect/", views.google_disconnect, name="google_disconnect"),
]




