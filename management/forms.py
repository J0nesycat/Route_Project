import logging
from django import forms
from .models import DailyDistribution, DailyWorkForce, Depot

logger = logging.getLogger(__name__)

class WorkforceForm(forms.ModelForm):
    depot = forms.ModelChoiceField(
        queryset=Depot.objects.all(),
        label='מרלוג',
        empty_label="בחר מרלוג",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = DailyWorkForce
        fields = ['date', 'number_of_drivers', 'depot']
        labels = {
            'date': 'תאריך',
            'number_of_drivers': 'מספר נהגים',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'number_of_drivers': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_date(self):
        logger.debug("Cleaning date input for WorkforceForm.")
        return self.cleaned_data['date']

    def validate_unique(self):
        logger.debug("Skipping unique validation in WorkforceForm.")
        pass


class DistributionForm(forms.ModelForm):
    class Meta:
        model = DailyDistribution
        fields = ['city', 'number_of_packages']
        labels = {
            'city': 'עיר',
            'number_of_packages': 'מספר חבילות',
        }
        widgets = {
            'city': forms.Select(attrs={'class': 'form-control'}),
            'number_of_packages': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class CSVUploadForm(forms.Form):
    file = forms.FileField(label="קובץ")
