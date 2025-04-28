from django.db import models

class Bull(models.Model):
    registered_name = models.CharField(max_length=128, default=0)
    birth_date = models.DateField(default="2000-01-01")
    identification_number = models.CharField(max_length=20, unique=True, default=0, db_index=True)
    pta_milk = models.FloatField(default=0)  # PTA Milk
    pta_fat = models.FloatField(default=0)  # PTA Fat
    pta_protein = models.FloatField(default=0)  # PTA Protein
    pta_productive_life = models.FloatField(default=0)  # PTA Productive Life
    pta_scs = models.FloatField(default=0)  # PTA SCS
    pta_dpr = models.FloatField(default=0)  # PTA DPR
    pta_hcr = models.FloatField(default=0)  # PTA HCR
    pta_ccr = models.FloatField(default=0)  # PTA CCR
    pta_gestation_length = models.FloatField(default=0)  # PTA Gestation Length
    pta_milk_fever = models.FloatField(default=0)  # PTA Milk Fever
    pta_displaced_abomasum = models.FloatField(default=0)  # PTA Displaced Abomasum
    pta_ketosis = models.FloatField(default=0)  # PTA Ketosis
    pta_mastitis = models.FloatField(default=0)  # PTA Mastitis
    pta_metritis = models.FloatField(default=0)  # PTA Metritis
    pta_retained_placenta = models.FloatField(default=0)  # PTA Retained Placenta
    pta_early_first_calving = models.FloatField(default=0)  # PTA Early First Calving
    pta_heifer_livability = models.FloatField(default=0)  # PTA Heifer Livability
    pta_feed_saved = models.FloatField(default=0)  # PTA Feed Saved
    pta_residual_feed_intake = models.FloatField(default=0)  # PTA Residual Feed Intake

    def __str__(self):
        return f'\nnumber: {self.identification_number}\nname: {str(self.registered_name)}\nbirth: {str(self.birth_date)}'
