from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.utils import quote
from django.utils import timezone

from .base import FilteredManager
from .methods import StudiesModel

class ResultsModel(models.Model):
    class Meta:
        db_table = 'database_results'
        verbose_name = 'Result'
        verbose_name_plural = 'Results'

    IMPORT_FIELDS = [
        'Study_ID',
        'Age_general',
        'Age_min',
        'Age_max',
        'Age_specific',
        'Population_gender',
        'Indigenous_status',
        'Indigenous_population',
        'Country',
        'Jurisdiction',
        'Specific_location',
        'Year_start',
        'Year_stop',
        'Observation_time_years',
        'Numerator',
        'Denominator',
        'Point_estimate',
        'Measure',
        'Interpolated_from_graph',
        'Proportion',
        'Mortality_flag',
        'Recurrent_ARF_flag',
        'Schoolchildren_flag',
        'Hospitalised_flag',
        'StrepA_attributable_fraction',
    ]
    
    Study = models.ForeignKey(
        StudiesModel,
        on_delete = models.CASCADE,
        help_text = "Select or add the study where these results were published.",
        related_name = 'results',
    )

    Import_row_number = models.PositiveIntegerField(
        null = True,
        blank = True,
        verbose_name = 'Excel row number',
        help_text = 'Row number from spreadsheet (only if imported from Excel)',
    )

    AGE_CHOICES = [
        (x, x) for x in (
            'Infants',
            'Children',
            'Children and adolescents',
            'Children, adolescents and young adults',
            'Adolescents and adults',
            'Adults',
            'Elderly adults',
            'All ages',
        )
    ]
    Age_general = models.CharField(
        max_length = 50,
        blank = True,
        verbose_name = 'Age category',
        choices = AGE_CHOICES,
        help_text = 'The general age grouping considered for inclusion by the study.'
    )
    
    Age_min = models.DecimalField(
        validators = [MaxValueValidator(150.0)],
        decimal_places = 2,
        max_digits = 10,
        null = True,
        blank = True,
        verbose_name = 'Youngest age in study (years)',
        help_text = 'Leave blank if unknown or study does not define a lower age limit.',
    )

    Age_max = models.DecimalField(
        validators = [MaxValueValidator(150.0)],
        decimal_places = 2,
        max_digits = 10,
        null = True,
        blank = True,
        verbose_name = 'Oldest age in study (years)',
        help_text = 'Leave blank if unknown or study does not define upper age limits.'
    )

    Age_specific = models.CharField(
        max_length = 50,
        blank = True,
        verbose_name = 'Specific age category',
        help_text = 'More specific description of age group as reported by the study.'
    )
    
    GENDER_CHOICES = [
        (x, x) for x in (
            'Females',
            'Males',
            'Males and females',
        )
    ]
    Population_gender = models.CharField(
        max_length = 30,
        blank = True,
        choices = GENDER_CHOICES,
        verbose_name = 'Population - Gender',
        help_text = 'This variable captures stratification by sex (where reported), with categories of “males”, “females”, “males and females”.'
    )
    
    Indigenous_status = models.BooleanField(
        blank = True,
        null = True,
        verbose_name = 'Indigenous',
        help_text = 'Flag indicating whether the measure includes an Indigenous population',
    )
    
    INDIGENOUS_POPULATION_CHOICES = [
        (x, x) for x in (
            'Aboriginal population',
            'General - special population',
            'General population',
            'Non-Indigenous population',
            'Not Defined',
            'Torres Strait Islander',
        )
    ]
    Indigenous_population = models.CharField(
        max_length = 50,
        blank = True,
        choices = INDIGENOUS_POPULATION_CHOICES,
        help_text = 'This variable captures stratification of the Indigenous population (where reported) into “Aboriginal”, “Torres Strait Islander” or “both Aboriginal and Torres Strait Islanders”.'
    )
    
    Country = models.CharField(
        max_length = 30,
        blank = True,
        default = 'Australia',
        help_text = 'Country where study was conducted (for future use, in the case that international studies are added to the data collection).'
    )

    Jurisdiction = models.CharField(
        max_length = 30,
        blank = True,
        help_text = 'Jurisdictional location of the study, categorized by individual jurisdiction name (WA, NT, SA, QLD, NSW, Vic) '
            'or combination of jurisdictions (Combination – Northern Australia or Combination- others).'
    )
    
    Specific_location = models.CharField(
        max_length = 100,
        blank = True,
        null = True,
        verbose_name = 'Specific geographic locations',
        help_text = 'Point estimates stratified by specific geographic locations (where reported), for example: Kimberley, Far North Queensland or Central Australia.'
    )
    
    Year_start = models.PositiveSmallIntegerField(
        validators = [MinValueValidator(1900), MaxValueValidator(2100)],
        null = True,
        blank = True,
        help_text = 'Start year for the observed point estimates within the study, allowing for temporal mapping of the point estimates.'
    )
    
    Year_stop = models.PositiveSmallIntegerField(
        validators = [MinValueValidator(1900), MaxValueValidator(2100)],
        null = True,
        blank = True,
        help_text = 'End year for the observed point estimates within the study, allowing for temporal mapping of the point estimates.'
    )
    
    Observation_time_years = models.DecimalField(
        validators = [MaxValueValidator(200.0)],
        decimal_places = 2,
        max_digits = 10,
        null = True,
        blank = True,
        verbose_name = 'Observational time (years)',
        help_text = 'Total observation time used by the study for generating the point estimate.'
    )
    
    Numerator = models.PositiveIntegerField(
        null = True,
        blank = True,
        help_text = 'This variable reports the numerators for studies reporting point estimates as proportions (non-population based).'
    )
    
    Denominator = models.PositiveIntegerField(
        null = True,
        blank = True,
        help_text = 'This variable reports the denominators for studies reporting point estimates as proportions (non-population based).'
    )
    
    Point_estimate = models.CharField(
        null = True,
        blank = True,
        max_length = 100,
        help_text = 'Must be interpreted together with Measure to provide the point estimate reported by the study within the correct '
            'measurement context. For example: 2020KATZ reports a point estimate of “4.6” and measure of “per 100,000 population”.'
    )
    
    Measure = models.TextField(
        blank = True,
        help_text = "Description of what the Point Estimate refers to and how it is calculated."
    )
    
    Interpolated_from_graph = models.BooleanField(
        blank = True,
        verbose_name = 'Interpolated',
        help_text = 'Indicator variable which is “Yes” if point estimate is interpolated and “No” if a numeric figure is given in the publication.'
    )

    Proportion = models.BooleanField(
        blank = True,
        verbose_name = 'Proportion',
        help_text = 'Indicator variable which is “Yes” if point estimate is a proportion and “No” if it is a measure of incidence or prevalence.'
    )

    Mortality_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Mortality',
        help_text = 'Indicator variable which is “Yes” if point estimate is a mortality estimate and “No” or “Unknown” otherwise.'
    )
    
    Recurrent_ARF_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Recurrent ARF',
        help_text = 'Indicator variable which is “Yes” if point estimate includes recurrent ARF and “No” or “Unknown” otherwise (applicable to ARF burden estimates only).'
    )
    
    StrepA_attributable_fraction = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Strep.A fraction',
        help_text = 'Indicator variable which is “Yes” if point estimate is a proportion which is Strep.A-specific and therefore represents a Strep.A-attributable fraction and “No” or “Unknown” otherwise.'
    )

    Hospitalised_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Hospitalised',
        help_text = 'Point estimate includes hospitalised patients',
    )

    Schoolchildren_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Schoolchildren',
        help_text = 'Point estimate includes data of school children',
    )
    
    def get_flags(self):
        return (
            {'field': field, 'value': getattr(self, field.name)}
            for field in self._meta.get_fields()
            if isinstance(field, models.BooleanField) and field.name != 'is_approved'
        )

    @property
    def exact_age_text(self):
        if self.Age_min is not None and self.Age_min > 0:
            if self.Age_max is not None and self.Age_max < 999:
                return '%d to %d years old' % (self.Age_min, self.Age_max)
            else:
                return '%d years and older' % self.Age_min
        elif self.Age_max is not None and self.Age_max < 999:
            return 'Up to %d years old' % self.Age_max

    @property
    def observation_time_text(self):
        if self.Observation_time_years is None:
            return 'N/A'
            
        years = int(self.Observation_time_years)
        years_pl = '' if years == 1 else 's'

        if self.Observation_time_years % 1 == 0:
            return '%d year%s' % (self.Observation_time_years, years_pl)
        months = round((self.Observation_time_years % 1) * 12)
        months_pl = '' if months == 1 else 's'

        if years:
            return '%d year%s %d month%s' % (years, years_pl, months, months_pl)
        return '%d month%s' % (months, months_pl)

    @property
    def view_results_studies_url(self):
        return reverse('admin:database_studies_change', args=[self.Study_id])

    @classmethod
    def get_view_results_studies_url(cls, study_id_list):
        if 'pending' in cls._meta.model_name:
            return None
        return reverse('admin:database_studies_changelist') + '?pk__in=' + ','.join(quote(str(id)) for id in study_id_list)

    def __str__(self):
        return '%s%s (Burden: %s)' % ('[Pending Approval] ' if self.pending else '', self.Study.Study_description if self.Study.Study_description else self.Study.Unique_identifier, self.Point_estimate)

    @property
    def owner_id(self):
        return self.Study.Created_by_id

# Additional proxy models here, for the various stages of submission/approval
# Proxy models are only needed just to allow more ModelAdmins registered in admin for the same model (it's a Django admin site limitation)
# Note that the Proxy Model class names are set up for the Admin Site URLs more than to follow Python/Django conventions
class Results(ResultsModel):
    class Meta:
        proxy = True
        verbose_name = 'Result'
        verbose_name_plural = 'Results'

    objects = FilteredManager(filter_args={
        'Study__Approved_by__isnull': False
    })

