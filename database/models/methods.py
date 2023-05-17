from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.utils import quote
from django.utils import timezone

from .base import ImportSource, FilteredManager
from .users import Users

class StudiesModel(models.Model):
    class Meta:
        db_table = 'database_studies'
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'

    IMPORT_FIELDS = [
        'Unique_identifier',
        'Study_group',
        'Paper_title',
        'Paper_link',
        'Year',
        'Study_description',
        'Disease',
        'Study_design',
        'Diagnosis_method',
        'Data_source',
        'Data_source_name',
        'Surveillance_setting',
        'Clinical_definition_category',
        'Coverage',
        'Climate',
        'Urban_rural_coverage',
        'Focus_of_study',
        'Limitations_identified',
        'Other_points',
    ]

    Import_source = models.ForeignKey(ImportSource, on_delete=models.CASCADE,
        null=True, blank=True, related_name='studies')
    Created_time = models.DateTimeField(auto_now_add=True, verbose_name='Contribution date')
    Created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, 
        null=True, blank=True, verbose_name='Contributed by', related_name='studies')
    Updated_time = models.DateTimeField(auto_now=True, verbose_name='Last modified')
    Approved_time = models.DateTimeField(null=True, blank=True, verbose_name='Approval date')
    Approved_by = models.ForeignKey(Users, on_delete=models.SET_NULL, 
        null=True, blank=True, verbose_name='Approved by', related_name='approved_studies')

    @property
    def owner_id(self):
        return self.Created_by_id

    @property
    def pending(self):
        return self.Approved_by is None

    @property
    def change_url(self):
        return reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])

    @property
    def Created_by_name(self):
        if self.Created_by:
            return str(self.Created_by)
        else:
            return 'N/A'

    @property
    def Approved_by_name(self):
        if self.Approved_by:
            return str(self.Approved_by)
        else:
            return 'N/A'

    Import_row_id = models.CharField(
        max_length = 20,
        null = True,
        blank = True,
        verbose_name = 'Unique row identifier',
        help_text = 'Unique Study identifier for linked Results (only if imported from Excel)',
    )

    Import_row_number = models.PositiveIntegerField(
        null = True,
        blank = True,
        verbose_name = 'Excel row number',
        help_text = 'Row number from spreadsheet (only if imported from Excel)',
    )

    STUDY_GROUPS = (
        (x, x) for x in (
            'Superficial skin and throat',
            'Invasive Strep A',
            'ARF',
            'APSGN',
        )
    )
    Study_group = models.CharField(
        max_length = 50,
        choices = STUDY_GROUPS,
        blank = True,
        verbose_name = 'Study Group',
        help_text = 'Broad classification of the Strep A-associated disease type that the study was based on: '
            '(i) Superficial skin and/or throat infections, (ii) Invasive Strep A infections, '
            '(iii) Acute Rheumatic Fever (ARF), (iv) Acute Post Streptococcal Glomerulonephritis (APSGN).'
    )
    
    Paper_title = models.CharField(
        max_length = 500,
        verbose_name = 'Paper Title',
        help_text = 'Title of the published manuscript/report.'
    )

    Paper_link = models.CharField(
        max_length = 1000,
        blank = True,
        verbose_name = 'Paper Link',
        help_text = 'URL or doi link for access to the source manuscript/report, full access will depend on open/institutional access permissions set by each journal.'
    )

    Year = models.PositiveSmallIntegerField(
        validators = [MinValueValidator(1900), MaxValueValidator(2100)],
        null = True,
        blank = True,
        verbose_name = 'Publication Year',
        help_text = 'Year of publication of manuscript/report.'
    )

    DISEASE_TYPES = [
        (x, x) for x in (
            'APSGN',
            'ARF',
            'iStrep A - NF',
            'iStrep A - Scarlet fever',
            'iStrep A - bacteraemia',
            'iStrep A - cellulitis',
            'iStrep A - pneumonia',
            'iStrep A - sepsis',
            'iStrep A - severe TSS',
            'iStrep A - all',
            'Superficial skin & throat infection',
            'Superficial throat infection',
            'Superficial skin infection',
            'Other',
        )
    ]
    Disease = models.CharField(
        max_length = 100,
        blank = True,
        choices = DISEASE_TYPES,
        verbose_name = 'Specific Disease',
        help_text = "Subcategory of disease within the broader study group. Example: iStrepA - bactaraemia"
    )

    STUDY_DESIGNS = (
        (x, x) for x in (
            'Case series',
            'Cross-sectional',
            'Prospective',
            'Prospective and Retrospective',
            'Prospective cohort',
            'Report',
            'Retrospective',
            'Retrospective review',
            'Retrospective cohort',
            'Review article',
            'Other',
        )      
    )
    
    Study_design = models.CharField(
        max_length = 50,
        choices = STUDY_DESIGNS,
        help_text = 'Study classification based on the temporality of data collection. '
            'Prospective (if study involves screening or active surveillance or primary data collection) or retrospective '
            '(study involves using either administrative/medical record data from hospitals, primary health centres, laboratory'
            ' or population datasets) or both prospective and retrospective (if study has both components). Other categories '
            'which are rarely used include report and outbreak investigation.'
    )    

    Study_description = models.CharField(
        max_length = 200,
        verbose_name = 'Publication info',
        blank = True,
        help_text = 'Name of the first author, abbreviated name of journal and year of manuscript publication. Example: McDonald, Clin Infect Dis, 2006'
    )

    DIAGNOSIS_METHODS = (
        (x, x) for x in (
            'Clinical and laboratory diagnosis',
            'Clinical diagnosis only',
            'ICD codes',
            'Laboratory diagnosis',
            'Notifications',
            'Primary Health Care codes (SNOMED/ICPC)',
            'Self report (questionnaire/survey)',
            'Other',
        )
    )
    Diagnosis_method = models.CharField(
        max_length = 200,
        blank = True,
        choices = DIAGNOSIS_METHODS,
        help_text = 'Indicates the process used to identify/diagnose Strep A-associated diseases, such as: notifications, ICD codes, '
            'Snowmed/ICPC codes, clinical diagnosis, laboratory diagnosis, echocardiography or combined methods.'
    )

    DATA_SOURCE_TYPES = (
        (x, x) for x in (
            'ED presentations only',
            'Hospital admissions',
            'Hospital admissions & active surveillance',
            'ICU admissions',
            'Laboratory records only',
            'Medical records only',
            'Multiple sources',
            'Outbreak investigations',
            'PHC health service data',
            'Register or notification',
            'Screening programme',
            'Survey/Questionnaire',
            'Other',
        )
    )
    Data_source = models.CharField(
        max_length = 50,
        blank = True,
        choices = DATA_SOURCE_TYPES,
        verbose_name = 'Data source',
        help_text = 'Method of case finding/identification, for example: screening or active surveillance for reporting '
            'cases of impetigo or skin sores; population registers for ARF; medical record review.'
    )
    
    SURVEILLANCE_SETTINGS = (
        (x, x) for x in (
            'Unknown',
            'Community',
            'Hospital',
            'Household',
            'Laboratory',
            'Multiple',
            'Primary health centre',
            'Schools',
            'Other'
        )
    )

    Surveillance_setting = models.CharField(
        max_length = 25,
        blank = True,
        verbose_name = 'Surveillance setting',
        choices = SURVEILLANCE_SETTINGS,
        help_text = 'The type of institution where the study was conducted. Classifications include primary health care clinic (PHC), tertiary hospital, '
            'outpatient clinics, school clinics, households, early childhood centers, aged care facilities etc.'
    )

    Data_source_name = models.CharField(
        max_length = 200,
        blank = True,
        null = True,
        verbose_name = 'Name of data source',
        help_text = 'Name of the dataset, project, consortium or specific disease register (if applicable).'
    )

    CDC_CHOICES = (
        (x, x) for x in (
            'Undefined or unknown',
            'Both confirmed and probable cases',
            'Confirmed case',
            'Definite and probable ARF',
            'Suspected or probable case',
            'Other'
        )
    )
    Clinical_definition_category = models.CharField(
        max_length = 50,
        blank = True,
        verbose_name = 'Clinical definition category',
        choices = CDC_CHOICES,
        help_text = 'Category for capturing the disease classification that was included in the study, if reported. Classifications '
            'depend on the disease and can include confirmed, suspected, probably, active, inactive, recurrent, total, undefined or unknown, subclinical or asymptomatic.'
    )
    
    COVERAGE_CHOICES = (
        (x, x) for x in (
            'National/multi-jurisdictional',
            'Single Institution/service',
            'State',
            'Subnational/region',
        )
    )
    Coverage = models.CharField(
        max_length = 200,
        blank = True,
        choices = COVERAGE_CHOICES,
        verbose_name = 'Geographic Coverage Level',
        help_text = 'Level of geographic coverage in the study, categorised as (i) national/multli-jurisdictional, (ii) state, (iii) subnational/ regional, (iv) single institution/ service.'
    )

    CLIMATE_CHOICES = (
        (x, x) for x in (
            'Arid',
            'Combination',
            'Temperate',
            'Tropical',
        )
    )
    Climate = models.CharField(
        max_length = 20,
        blank = True,
        choices = CLIMATE_CHOICES,
        help_text = 'Climatic conditions based on the geographic coverage of studies, for example: “Tropical” for studies conducted at the Top-End NT, “Temperate” for studies from Victoria or NSW.'
    )
    
    REMOTENESS_CHOICES = (
        (x, x) for x in (
            'Combination',
            'Metropolitan',
            'Regional',
            'Remote',
        )
    )
    Urban_rural_coverage = models.CharField(
        max_length = 20,
        blank = True,
        choices = REMOTENESS_CHOICES,
        verbose_name = 'Urban-Rural Coverage',
        help_text = 'Classification into metropolitan, urban/regional, and rural/remote areas.'
    )

    Focus_of_study = models.CharField(
        max_length = 1000,
        blank = True,
        help_text = 'Brief description of the focus of the study.'
    )

    Limitations_identified = models.CharField(
        max_length = 1000,
        blank = True,
        null = True,
        help_text = 'Brief summary of any limitations identified by authors of the publication. (Optional)'
    )

    Other_points = models.TextField(
        blank = True,
        null = True,
        help_text = 'This variable captures any other relevant notes relating to the study that may impact the interpretation of Strep A burden estimates. (Optional)'
    )

    def get_export_id(self):
        return self.Unique_identifier or self.id

    @classmethod
    def get_view_study_results_url(cls, study_id_list):
        if cls._meta.model_name == 'my_drafts' or cls._meta.model_name == 'my_submissions':
            return None
        return reverse('admin:database_results_changelist') + '?Study_id__in=' + ','.join(quote(str(id)) for id in study_id_list)

    @property
    def view_study_results_url(self):
        return self.get_view_study_results_url((self.pk, ))

    def __str__(self):
        return "%s%s (%s)" % ('[Pending Approval] ' if self.pending else '', self.Paper_title, self.Year)


# Additional proxy models here, for the various stages of submission/approval
# Proxy models are only needed just to allow more ModelAdmins registered in admin for the same model (it's a Django admin site limitation)
# Note that the Proxy Model class names are set up for the Admin Site URLs more than to follow Python/Django conventions
class Studies(StudiesModel):
    """ Approved Studies (for general display) """
    class Meta:
        proxy = True
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'
    
    objects = FilteredManager(filter_args={'Approved_by__isnull': False})
    
class My_Drafts(StudiesModel):
    class Meta:
        proxy = True
        verbose_name = 'Study (Draft)'
        verbose_name_plural = 'Studies (Draft)'

    objects = FilteredManager(filter_args={'Approved_by__isnull': True})

