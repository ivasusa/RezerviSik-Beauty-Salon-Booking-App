from django.urls import path

from appSandra.views import*

urlpatterns = [
    path("owner/statistics/", owner_statistics, name="owner_statistics"),
    path("owner/dashboard/", owner_dashboard, name="owner_dashboard"),
    path("owner/calendar/", owner_calendar, name="owner_calendar"),

    path("owner/staff/", owner_staff, name="owner_staff"),

    path("osoblje/moj-raspored/", osoblje_moj_raspored, name="osoblje_moj_raspored"),
    path("osoblje/moj-profil/", osoblje_moj_profil, name="osoblje_moj_profil"),
    path("osoblje/izmeni-profil/", osoblje_izmeni_profil, name="osoblje_izmeni_profil"),
    path("staff/day-test/<str:date_str>/",  staff_day_schedule, name="staff_day_schedule_test"),
    path("staff/free-slots-test/<str:date_str>/", staff_free_slots_test, name="staff_free_slots_test"),
    path("staff/api/booked-days-test/<int:year>/<int:month>/", staff_booked_days_test, name="staff_booked_days_test"),
    path("owner/day-test/<str:date_str>/", owner_day_schedule_test, name="owner_day_schedule_test"),
    path("owner/api/booked-days-test/<int:year>/<int:month>/", owner_booked_days_test, name="owner_booked_days_test"),
    path("client/pregled/",klijent_pregled,name="klijent_pregled"),
    path("owner/api/calendar/month/", api_owner_kalendar_mesec, name="api_owner_kalendar_mesec"),
    path("owner/api/calendar/day/", api_owner_termini_dan, name="api_owner_termini_dan"),
    path("owner/send-reminders/", send_reminders_view, name="send_reminders"),

]
