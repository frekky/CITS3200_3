from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.utils import quote


class CustomAccountManager(BaseUserManager):
    
    def create_superuser(self, email, first_name, last_name, password, **other_fields):
    
        other_fields.setdefault('is_superuser', True)
        
        if other_fields.get('is_superuser') is not True:
            raise ValueError(
                'Superuser must be assigned to is_superuser=True')
        
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, 
                          **other_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user

    def create_user(self, email, first_name, last_name, password, **other_fields):
        
        if not email:
            raise ValueError(_('You must provide an email address'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name,
                          **other_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user
             
class Users(AbstractBaseUser):
    class Meta:
        verbose_name_plural = 'Users'
    
    email = models.EmailField(_('email'), max_length=100, unique=True)
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    profession = models.CharField(max_length=50, blank=True)
    institution = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    is_superuser = models.BooleanField(_('Superuser status'), default=False, help_text=_('Designates that this user has all permissions without explicitly assigning them.'))
    is_active = models.BooleanField(_('Active'), default=True, help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    
    objects = CustomAccountManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    def __str__(self):
        return '%s %s <%s>' % (self.first_name, self.last_name, self.email)
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return True

class ImportSource(models.Model):
    class Meta:
        verbose_name = 'Imported Datasets'
        verbose_name_plural = 'Imported Datasets'

    Source_file = models.FileField(upload_to='uploads/imports/%Y/%m/%d/')
    Original_filename = models.CharField(max_length=255, blank=True)
    Import_type = models.CharField(max_length=20, blank=True)
    Row_count = models.PositiveIntegerField(null=True)
    Import_time = models.DateTimeField(auto_now_add=True)
    Imported_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    Import_log = models.TextField(blank=True)
    Import_status = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.Original_filename

class FilteredManager(models.Manager):
    filter_args = None
    def __init__(self, filter_args=None):
        self.filter_args = filter_args or {}
        super().__init__()
    
    def get_queryset(self):
        return super().get_queryset().filter(**self.filter_args)
     
class MyModel(models.Model):
    class Meta:
        abstract = True
    
    Import_source = models.ForeignKey(ImportSource, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    Created_time = models.DateTimeField(auto_now_add=True)
    Created_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Submitted by user', related_name='+')
    Updated_time = models.DateTimeField(auto_now=True)
    Approved_time = models.DateTimeField(null=True, blank=True)
    Approved_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Verified by user', related_name='+')

    objects = FilteredManager(filter_args={'Approved_by__isnull': False})

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

class StudiesModel(MyModel):
    class Meta:
        db_table = 'database_studies'
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'

    Unique_identifier = models.CharField(
        max_length = 20,
        null = True,
        blank = True,
        verbose_name = 'Unique Identifier (Internal Use Only)',
        help_text = 'Identifier linking individual Results to each Study in the Studies/Methods data'
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
    Aria_remote = models.CharField(
        max_length = 20,
        blank = True,
        choices = REMOTENESS_CHOICES,
        verbose_name = 'ARIA+ Remoteness Classification',
        help_text = 'Classification into metropolitan, regional and remote areas based on the ARIA+ (Accessibility and Remoteness Index of Australia) system.'
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
        if 'pending' in cls._meta.model_name:
            return None
        return reverse('admin:database_results_changelist') + '?Study_id__in=' + ','.join(quote(str(id)) for id in study_id_list)

    @property
    def view_study_results_url(self):
        return self.get_view_study_results_url((self.pk, ))

    def __str__(self):
        return "%s%s (%s)" % ('[Pending Approval] ' if self.pending else '', self.Paper_title, self.Year)


class ResultsModel(MyModel):
    class Meta:
        db_table = 'database_results'
        verbose_name = 'Result'
        verbose_name_plural = 'Results'
    
    Study = models.ForeignKey(
        StudiesModel,
        on_delete = models.CASCADE,
        help_text = "Select or add the study where these results were published.",
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
        return self.get_view_results_studies_url((self.Study_id, ))

    @classmethod
    def get_view_results_studies_url(cls, study_id_list):
        if 'pending' in cls._meta.model_name:
            return None
        return reverse('admin:database_studies_changelist') + '?pk__in=' + ','.join(quote(str(id)) for id in study_id_list)

    def __str__(self):
        if not self.Study:
            return "%sBurden: %s" % ('[Pending Approval] ' if self.pending else '', self.Point_estimate, )
        return '%s%s (Burden: %s)' % ('[Pending Approval] ' if self.pending else '', self.Study.Study_description if self.Study.Study_description else self.Study.Unique_identifier, self.Point_estimate)

def proxy_model_factory(model, verbose_name, name=None, filter_args={}):
    name = name or ('_'.join('%s.%s' % (k.replace('_', ''), v) for k, v in filter_args.items()) + '_' + model._meta.model_name)

    meta = type('Meta', (), {
        'proxy': True,
        'verbose_name': verbose_name,
        'verbose_name_plural': verbose_name,
    })

    cls = type(name, (model, ), {
        '__module__': __name__,
        'Meta': meta,
        'objects': FilteredManager(filter_args=filter_args),
    })

    return cls

ApprovedStudies = proxy_model_factory(
    StudiesModel,
    'Studies',
    name = 'studies',
    filter_args = {'Approved_by__isnull': False}
)

ApprovedResults = proxy_model_factory(
    ResultsModel,
    'Results',
    name = 'results',
    filter_args = {'Approved_by__isnull': False}
)

PendingStudies = proxy_model_factory(
    StudiesModel,
    'Studies (Pending Approval)',
    name = 'studies_pending',
    filter_args = {'Approved_by__isnull': True},
)

PendingResults = proxy_model_factory(
    ResultsModel,
    'Results (Pending Approval)',
    name = 'results_pending',
    filter_args = {'Approved_by__isnull': True},
)

class Document(models.Model):
    title = models.CharField(max_length=100, help_text="Title of download button shown to users on website home screen")
    upload_file = models.FileField(
        upload_to = 'documents/',
    )
    all_users = models.BooleanField(blank=True, verbose_name = 'Visible to all users', help_text="Whether all users can access this document or if it is only visible to administrators.")

    def __str__(self):
        return self.title