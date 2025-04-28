# myapp/forms.py
import json
from django import forms
from django.core.exceptions import ValidationError
# from django.template import loader
# from django.utils.safestring import mark_safe


class CsvUploadForm(forms.Form):
    csv_file = forms.FileField(label="Вставьте файл CSV")


class BullSortForm(forms.Form):
    PTA_CHOICES = [
        ('pta_milk', 'PTA Milk'),
        ('pta_fat', 'PTA Fat'),
        ('pta_protein', 'PTA Protein'),
        ('pta_productive_life', 'PTA Productive Life'),
        ('pta_scs', 'PTA SCS'),
        ('pta_dpr', 'PTA DPR'),
        ('pta_hcr', 'PTA HCR'),
        ('pta_ccr', 'PTA CCR'),
        ('pta_gestation_length', 'PTA Gestation Length'),
        ('pta_milk_fever', 'PTA Milk Fever'),
        ('pta_displaced_abomasum', 'PTA Displaced Abomasum'),
        ('pta_ketosis', 'PTA Ketosis'),
        ('pta_mastitis', 'PTA Mastitis'),
        ('pta_metritis', 'PTA Metritis'),
        ('pta_retained_placenta', 'PTA Retained Placenta'),
        ('pta_early_first_calving', 'PTA Early First Calving'),
        ('pta_heifer_livability', 'PTA Heifer Livability'),
        ('pta_feed_saved', 'PTA Feed Saved'),
        ('pta_residual_feed_intake', 'PTA Residual Feed Intake'),
    ]

    # phenotype_order = forms.MultipleChoiceField(
    #     widget=forms.SelectMultiple(attrs={'size': 6}),
    #     choices=PTA_CHOICES,
    #     label="Select PTA Priorities"
    # )

    phenotype_order = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    thresholds = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def clean_phenotype_order(self):
        order = self.cleaned_data['phenotype_order']
        try:
            order_data = json.loads(order)
            if not isinstance(order_data, list):
                raise ValidationError("Invalid format for phenotype order")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in phenotype order")
        
        valid_choices = dict(self.PTA_CHOICES).keys()
        invalid_choices = [item for item in order_data if item not in valid_choices]
        
        if invalid_choices:
            raise ValidationError(f"Invalid choices: {', '.join(invalid_choices)}")
        
        return order_data

    def clean_thresholds(self):
        thresholds = self.cleaned_data['thresholds']
        try:
            thresholds_data = json.loads(thresholds)
            if not isinstance(thresholds_data, list):
                raise ValidationError("Thresholds must be a list")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format in thresholds")
        
        expected_length = len(self.PTA_CHOICES)
        if len(thresholds_data) != expected_length:
            raise ValidationError(
                f"Thresholds array must contain exactly {expected_length} elements"
            f" (got {len(thresholds_data)})"
            )
        
        return [None if isinstance(x, str) and x.lower() == 'none' else x 
               for x in thresholds_data]
    

class PairingForm(forms.Form):
    num_cows_to_breed = forms.IntegerField(
        label="Количество коров для осеменения (N)",
        min_value=1,
        required=True,
        widget=forms.NumberInput(attrs={'placeholder': 'Например: 100'})
    )
    budget = forms.FloatField(
        label="Бюджет на закупку быков (B)",
        min_value=0.0,
        required=True,
        widget=forms.NumberInput(attrs={'placeholder': 'Например: 5000.0', 'step': '100.0'})
    )