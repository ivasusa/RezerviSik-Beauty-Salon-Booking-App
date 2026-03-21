from django import forms
from appIva.models import Service, Salon
from django.contrib.auth.models import User

#Masa Avramovic, Iva Susa

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "category", "duration", "price"]

    def clean(self):
        cleaned = super().clean()

        name = (cleaned.get("name") or "").strip()
        category = (cleaned.get("category") or "").strip()

        if not name:
            self.add_error("name", "Naziv je obavezan.")
        if not category:
            self.add_error("category", "Opis/Kategorija je obavezna.")

        price = cleaned.get("price")
        if price is not None and price <= 0:
            self.add_error("price", "Cena mora biti veća od 0.")

        duration = cleaned.get("duration")
        if duration is not None and duration <= 0:
            self.add_error("duration", "Trajanje mora biti veće od 0.")

        cleaned["name"] = name
        cleaned["category"] = category
        return cleaned

from django import forms
from appIva.models import User as LegacyUser, Salon

class OwnerForm(forms.ModelForm):
    full_name = forms.CharField(label="Ime i prezime")

    class Meta:
        model = LegacyUser
        fields = ["full_name", "email", "phone"]
        widgets = {
            "email": forms.EmailInput(attrs={"readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["full_name"].initial = f"{self.instance.name} {self.instance.surname}"

    def save(self, commit=True):
        user = super().save(commit=False)
        full = self.cleaned_data["full_name"].strip().split()
        user.name = full[0]
        user.surname = " ".join(full[1:]) if len(full) > 1 else ""
        if commit:
            user.save()
        return user


class SalonForm(forms.ModelForm):
    working_hours = forms.CharField(
        max_length=50,
        label="Radno vreme",
        widget=forms.TextInput(attrs={
            'placeholder': '9:00-17:00',
            'pattern': r'\d{1,2}:\d{2}-\d{1,2}:\d{2}',
            'class': 'form-control'
        }),
        help_text="Format: HH:MM-HH:MM (npr. 9:00-17:00)"
    )

    class Meta:
        model = Salon
        fields = ["name", "address", "contact", "description", "working_hours"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_working_hours(self):
        working_hours = self.cleaned_data.get("working_hours", "").strip()
        if not working_hours:
            raise forms.ValidationError("Radno vreme je obavezno.")

        import re
        pattern = r'^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$'
        match = re.match(pattern, working_hours)
        if not match:
            raise forms.ValidationError("Format radnog vremena mora biti HH:MM-HH:MM (npr. 9:00-17:00)")

        start_hour, start_min, end_hour, end_min = match.groups()
        start_total = int(start_hour) * 60 + int(start_min)
        end_total = int(end_hour) * 60 + int(end_min)

        if start_total >= end_total:
            raise forms.ValidationError("Početak radnog vremena mora biti pre kraja.")

        return working_hours
