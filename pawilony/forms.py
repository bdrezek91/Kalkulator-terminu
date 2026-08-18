from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

KUCHNIA_CHOICES = [("", "brak"), ("Standard", "Standard"), ("Lux", "Lux")]
WARIANT_CHOICES = [("", "brak"), ("Standard", "Standard"), ("Komfort", "Komfort"), ("Premium", "Premium")]


class CalculatorForm(forms.Form):
    kuchnia = forms.ChoiceField(
        choices=KUCHNIA_CHOICES, required=False, label="Kuchnia",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    toaleta = forms.ChoiceField(
        choices=WARIANT_CHOICES, required=False, label="Toaleta",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_toaleta"}),
    )
    lazienka = forms.ChoiceField(
        choices=WARIANT_CHOICES, required=False, label="Łazienka",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_lazienka"}),
    )
    prysznic = forms.BooleanField(
        required=False, label="Samodzielny prysznic",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_prysznic"}),
    )
    wc_addon_fibo = forms.BooleanField(
        required=False, label="Fibo (dodatkowo)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    wc_addon_plytki = forms.BooleanField(
        required=False, label="Płytki (dodatkowo)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    wc_addon_boazeria = forms.BooleanField(
        required=False, label="Boazeria WC/łazienki (dodatkowo)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    pelna_statyka = forms.BooleanField(
        required=False, label="Pełna konstrukcja / statyka",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    kratownica = forms.BooleanField(
        required=False, label="Kratownica", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    fibo = forms.BooleanField(
        required=False, label="FIBO", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    boazeria = forms.BooleanField(
        required=False, label="Boazeria", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    stolarka_nst = forms.BooleanField(
        required=False, label="Stolarka niestandardowa", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    zaluzje_fasadowe = forms.BooleanField(
        required=False, label="Żaluzje fasadowe", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    rolety = forms.BooleanField(
        required=False, label="Rolety", widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("lazienka"):
            # Łazienka jest kompletem — toaleta i samodzielny prysznic nie zwiększają godzin.
            cleaned["toaleta"] = ""
            cleaned["prysznic"] = False
        if cleaned.get("pelna_statyka") and cleaned.get("kratownica"):
            raise ValidationError(
                "Pełna konstrukcja/statyka i kratownica wykluczają się — wybierz jedną z opcji."
            )
        return cleaned


ALLOWED_IMPORT_EXTENSIONS = [".xlsx"]


class ImportUploadForm(forms.Form):
    file = forms.FileField(
        label="Plik XLSX z Optimy",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = f.name or ""
        if not any(name.lower().endswith(ext) for ext in ALLOWED_IMPORT_EXTENSIONS):
            raise ValidationError("Dozwolone są tylko pliki .xlsx.")
        max_bytes = settings.IMPORT_MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if f.size > max_bytes:
            raise ValidationError(f"Plik jest za duży (limit {settings.IMPORT_MAX_UPLOAD_SIZE_MB} MB).")
        return f
