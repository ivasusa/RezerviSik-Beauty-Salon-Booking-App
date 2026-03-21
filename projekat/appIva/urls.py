#Iva Susa

from django.urls import path
from .views import home, register_user, login_user, logout_user, profile_view, \
    klijent_rec, klijent_moj_profil, update_profile, owner_staff_view, add_staff, delete_staff

urlpatterns = [
    path('registration/',register_user,name='register_user'),
path('login/',login_user,name='login_user'),
path('logout/', logout_user, name='logout_user'),
path('profile/', profile_view, name='profile'),
#path('kiljent/pregled/', klijent_pregled, name='klijent_pregled'), sandra radila prebacila kod sebe
    #path('klijent/moje-rez/', klijent_moje_rez, name='klijent_moje_rez'), prebaceno u appMasa
    path('klijent/recenzije/', klijent_rec, name='klijent_rec'),
    path('kiljent/profil/', klijent_moj_profil, name='klijent_moj_profil'),
    path('profile/update/', update_profile, name='update_profile'),
#path('owner/staff/', owner_staff_view, name='owner_staff'),
path('owner/staff/add/', add_staff, name='add_staff'),
path('owner/staff/delete/<int:staff_id>/', delete_staff, name='delete_staff'),
    path('',home,name='home'),
]