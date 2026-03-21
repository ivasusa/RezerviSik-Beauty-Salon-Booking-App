#Jovana Simic 2022/0466
"""
URL konfiguracija aplikacije appJovana.

Definiše mapiranje URL ruta na view funkcije koje upravljaju:
- prikazom salona,
- recenzijama klijenata i vlasnika,
- pregledom termina osoblja,
- izmenom profila zaposlenih.

Svaka ruta odgovara view-u dokumentovanom u
:view:`appJovana.salonViews` i ostalim view funkcijama.
"""


from django.urls import path
from .views import salonViews, salon_detail, clientReviews, add_review, owner_reviews, osoblje_pregled, \
    osoblje_izmeni_profil

urlpatterns = [
    path('salon/<int:salon_id>/', salon_detail, name='salon_detail'),
    path('salons/',salonViews, name='salonViews'),
    path('reviews/', clientReviews, name='klijent_recenzije'),
    path('reviews/add/', add_review, name='dodaj_recenziju'),
    path('owner/reviews/', owner_reviews, name='owner_reviews'),
    path("osoblje/pregled/", osoblje_pregled, name="osoblje_pregled"),
    path("osoblje/moj-profil/izmeni/", osoblje_izmeni_profil, name="osoblje_izmeni_profil"),

]