from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib import admin
from django.conf import settings

STUDY_GROUPS = (
    ('SST', 'Superficial skin and throat'),
    ('IG', 'Invasive Strep A'),
    ('ARF', 'ARF'),
    ('ASPGN', 'APSGN'),
)

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
        return self.email
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return True
     
class Studies(models.Model):
    class Meta:
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'

    Unique_identifier = models.CharField(
        max_length = 12,
        null = True,
        blank = True,
        verbose_name = 'Unique Identifier (Internal Use Only)',
        help_text = 'Identifier linking individual Results to each Study in the Studies/Methods data'
    ) 

    Study_group = models.CharField(
        max_length = 5,
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

    Disease = models.CharField(
        max_length = 100,
        blank = True,
        verbose_name = 'Specific Disease',
        help_text = "Subcategory of disease within the broader study group. Example: iStrepA - bactaraemia"
    )

    STUDY_DESIGNS = (
        ('CS', 'Case series'),
        ('CST', 'Cross-sectional'),
        ('P', 'Prospective'),
        ('PRP', 'Prospective and Retrospective'),
        ('PC', 'Prospective cohort'),
        ('R', 'Report'),
        ('RP', 'Retrospective'),  
        ('RPR', 'Retrospective review'), 
        ('RPC', 'Retrospective cohort'),  
        ('RA', 'Review article'),              
        ('O', 'Other'),        
    )
    
    Study_design = models.CharField(
        max_length = 3,
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

    Diagnosis_method = models.CharField(
        max_length = 200,
        blank = True,
        help_text = 'Indicates the process used to identify/diagnose Strep A-associated diseases, such as: notifications, ICD codes, '
            'Snowmed/ICPC codes, clinical diagnosis, laboratory diagnosis, echocardiography or combined methods.'
    )

    Data_source = models.CharField(
        max_length = 200,
        blank = True,
        verbose_name = 'Data source',
        help_text = 'Method of case finding/identification, for example: screening or active surveillance for reporting '
            'cases of impetigo or skin sores; population registers for ARF; medical record review.'
    )
    
    SURVEILLANCE_SETTINGS = [
        (x, x) for x in ('Unknown', 'Community', 'Hospital', 'Household', 'Laboratory',
            'Multiple', 'Primary health centre', 'School', 'Other')
    ]

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
        verbose_name = 'Name of data source',
        help_text = 'Name of the dataset, project, consortium or specific disease register (if applicable).'
    )

    CDC_CHOICES = [
        (x, x) for x in ('Undefined or unknown', 'Both confirmed and probable cases',
        'Confirmed case', 'Definite and probable ARF', 'Suspected or probable case', 'Other')
    ]

    Clinical_definition_category = models.CharField(
        max_length = 50,
        blank = True,
        verbose_name = 'Clinical definition category',
        choices = CDC_CHOICES,
        help_text = 'Category for capturing the disease classification that was included in the study, if reported. Classifications '
            'depend on the disease and can include confirmed, suspected, probably, active, inactive, recurrent, total, undefined or unknown, subclinical or asymptomatic.'
    )
    
    Coverage = models.CharField(
        max_length = 200,
        blank = True,
        verbose_name = 'Geographic Coverage Level',
        help_text = 'Level of geographic coverage in the study, categorised as (i) national/multli-jurisdictional, (ii) state, (iii) subnational/ regional, (iv) single institution/ service.'
    )

    Climate = models.CharField(
        max_length = 200,
        blank = True,
        help_text = 'Climatic conditions based on the geographic coverage of studies, for example: “Tropical” for studies conducted at the Top-End NT, “Temperate” for studies from Victoria or NSW.'
    )
    
    Aria_remote = models.CharField(
        max_length = 200,
        blank = True,
        verbose_name = 'ARIA+ Remoteness Classification',
        help_text = 'Classification into metropolitan, regional and remote areas based on the ARIA+ (Accessibility and Remoteness Index of Australia) system.'
    )

    Method_limitations = models.BooleanField(
        null = True,
        blank = True,
        help_text = 'This variable indicates whether method limitations were specified by the authors of the publication.'
    )

    Limitations_identified = models.CharField(
        max_length = 1000,
        blank = True,
        help_text = 'Summary of any limitations identified by authors of the publication.'
    )

    Other_points = models.TextField(
        blank = True,
        help_text = 'This variable captures any other relevant notes relating to the study that may impact the interpretation of Strep A burden estimates.'
    )

    # For approving the adding of studies
    is_approved = models.BooleanField(
        default = False,
        verbose_name = 'Study approved',
        blank = False,
        help_text = _('Designates whether this study has been approved or is pending approval.')
    )
    
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null = True,
        blank = True,
        on_delete = models.SET_NULL,
        verbose_name = 'Study added/submitted by user',
    )
    
    def get_study_design(self):
        for code, desc in self.STUDY_DESIGNS:
            if code == self.Study_design:
                return desc
        return ''

    def get_export_id(self):
        return self.Unique_identifier or self.id

    def get_flags(self):
        return (
            {'field': field, 'value': getattr(self, field.name)}
            for field in self._meta.get_fields()
            if isinstance(field, models.BooleanField) and field.name != 'is_approved'
        )

    def __str__(self):
        return "%s (%s)" % (self.Paper_title, self.Year)

class Results(models.Model):
    class Meta:
        verbose_name = 'Result'
        verbose_name_plural = 'Results' 
    
    Study = models.ForeignKey(
        Studies,
        on_delete = models.CASCADE,
        null = True,
        help_text = "Select or add the study where these results were published.",
    )

    Age_general = models.CharField(
        max_length = 50,
        blank = True,
        verbose_name = 'Age category',
        help_text = 'The general age grouping considered for inclusion by the study, classified as “all ages” (if studies did not have any age restrictions); '
            '“infants”, “young children”, “children and adolescents”, “18 years and younger” and “16 years and older”. '
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
    
    Population_gender = models.CharField(
        max_length = 30,
        blank = True,
        verbose_name = 'Population - Gender',
        help_text = 'This variable captures stratification by sex (where reported), with categories of “males”, “females”, “males and females”.'
    )
    
    Indigenous_status = models.BooleanField(
        blank = True,
        null = True,
        verbose_name = 'Population - Indigenous Status',
        help_text = 'Flag indicating whether this measure involves an Indigenous population',
    )
    
    Indigenous_population = models.CharField(
        max_length = 50,
        blank = True,
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
        verbose_name = 'Observational period',
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
        help_text = 'Indicator variable which is “Yes” if point estimate is interpolated and “No” if a numeric figure is given in the publication.'
    )

    Proportion = models.BooleanField(
        blank = True,
        verbose_name = 'Point estimate is proportion',
        help_text = 'Indicator variable which is “Yes” if point estimate is a proportion and “No” if it is a measure of incidence or prevalence.'
    )

    Mortality_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Point estimate is mortality estimate',
        help_text = 'Indicator variable which is “Yes” if point estimate is a mortality estimate and “No” or “Unknown” otherwise.'
    )
    
    Recurrent_ARF_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Point estimate includes recurrent ARF',
        help_text = 'Indicator variable which is “Yes” if point estimate includes recurrent ARF and “No” or “Unknown” otherwise (applicable to ARF burden estimates only).'
    )
    
    StrepA_attributable_fraction = models.BooleanField(
        null = True,
        blank = True,
        help_text = 'Indicator variable which is “Yes” if point estimate is a proportion which is Strep.A-specific and therefore represents a Strep.A-attributable fraction and “No” or “Unknown” otherwise.'
    )

    #Burden_measure = models.CharField(
    #    max_length = 50,
    #    blank = True,
    #    help_text = 'The epidemiological measure presented as a point estimate by the study. The categories include: population incidence, population prevalence or proportion (not population based).'
    #)

    Hospitalised_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Point estimate includes hospitalised patients',
    )

    Schoolchildren_flag = models.BooleanField(
        null = True,
        blank = True,
        verbose_name = 'Point estimate includes data of school children',
    )

    # For approving the adding of results
    is_approved = models.BooleanField(
        default = False,
        verbose_name = 'Results approved',
        blank = False,
        help_text = _('Determines whether this study has been approved by an administrator or is submitted and pending approval.')
    )
    
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null = True,
        blank = True,
        on_delete = models.SET_NULL,
        verbose_name = 'Results added/submitted by user')
    
    def get_flags(self):
        return (
            {'field': field, 'value': getattr(self, field.name)}
            for field in self._meta.get_fields()
            if isinstance(field, models.BooleanField) and field.name != 'is_approved'
        )

    def __str__(self):
        if not self.Study:
            return "Burden: %s" % (self.Point_estimate, )
        return '%s (Burden: %s)' % (self.Study.Paper_title, self.Point_estimate)

class ProxyManager(models.Manager):
    filter_args = None
    def __init__(self, filter_args=None):
        self.filter_args = filter_args or {}
        super().__init__()
    
    def get_queryset(self):
        return super().get_queryset().filter(**self.filter_args)

proxies = []
def proxy_model_factory(model, verbose_name, **filter_args):
    global proxies
    name = '_'.join('%s.%s' % (k.replace('_', ''), v) for k, v in filter_args.items()) + '_' + model._meta.model_name

    meta = type('Meta', (), {
        'proxy': True,
        'verbose_name': verbose_name,
        'verbose_name_plural': verbose_name,
    })

    cls = type(name, (model, ), {
        '__module__': __name__,
        'Meta': meta,
        'objects': ProxyManager(filter_args=filter_args),
    })

    proxies.append(cls)

    return cls

# one way to possibly add admin page approval function
#UnapprovedResults = proxy_model_factory(Results, 'Results (Pending Approval)', Is_approved=False)

is_approved_proxies = []
def is_approved_proxy_model_factory(model, verbose_name, **filter_args):
    global is_approved_proxies
    name = '_'.join('%s_%s' % (k.replace('_', ''), v) for k, v in filter_args.items()) + '_' + model._meta.model_name

    meta = type('Meta', (), {
        'proxy': True,
        'verbose_name': verbose_name,
        'verbose_name_plural': verbose_name,
    })

    cls = type(name, (model, ), {
        '__module__': __name__,
        'Meta': meta,
        'objects': ProxyManager(filter_args=filter_args),
    })

    is_approved_proxies.append(cls)

    return cls

UnapprovedStudies = is_approved_proxy_model_factory(Studies, 'Studies (Pending Approval)', is_approved=False)
UnapprovedResults = is_approved_proxy_model_factory(Results, 'Results (Pending Approval)', is_approved=False)