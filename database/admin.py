from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.template.loader import render_to_string
from django.urls import reverse
from rangefilter.filters import NumericRangeFilter
from admin_action_buttons.admin import ActionButtonsMixin

from database.models import Users, Studies, Results, proxies, is_approved_proxies # Custom admin form imported from models.py
from .actions import download_as_csv
from django_admin_listfilter_dropdown.filters import (DropdownFilter, ChoiceDropdownFilter, RelatedDropdownFilter)
from django.db import models
        
# The Custom Admin user model
class AccountAdmin(ActionButtonsMixin, UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'date_joined', 'is_superuser', 'profession', 'institution', 'country')
    fields = ('email', 'first_name', 'last_name', 'date_joined', 'profession', 'institution', 'country', 'is_superuser', 'is_active')
    search_fields = ['email']
    readonly_fields = ('id', 'date_joined')
    actions = [download_as_csv('Export selected accounts to CSV')]
    
    ordering = ['email']
    exclude = ()
    
    filter_horizontal = ()
    list_filter = ('is_superuser', 'is_active',)
    fieldsets = ()
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

# override default behaviour to allow viewing by anyone
class ViewModelAdmin(ActionButtonsMixin, ModelAdmin):
    def has_view_permission(self, request, obj=None):
        return request.user.is_active #and request.user.can_view_data

    def has_add_permission(self, request, obj=None):
        return request.user.is_active #and request.user.can_add_data
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_approved=True)
           
    # save email of user that's adding studies/results
    def save_model(self, request, obj, form, change):
        obj.added_by = request.user
        super().save_model(request, obj, form, change)
    
    # exclude fields so they're not viewable by generic users
    def get_exclude(self, request, obj=None):
            is_superuser = request.user.is_superuser
            excluded = ['added_by']
            if not is_superuser:
                return excluded

class ResultsInline(admin.StackedInline):
    model = Results
    extra = 0
    readonly_fields = ('is_approved',)
    
    def get_readonly_fields(self, request, obj=None):
            is_superuser = request.user.is_superuser
            if is_superuser:
                return []
            return self.readonly_fields
    
    def has_view_permission(self, request, obj=None):
        return True #and request.user.can_add_data
    
    def has_add_permission(self, request, obj=None):
        return True #and request.user.can_add_data
    
    # exclude fields so they're not viewable by generic users    
    def get_exclude(self, request, obj=None):
            is_superuser = request.user.is_superuser
            excluded = ['is_approved', 'added_by']
            if not is_superuser:
                return excluded
   
class StudiesAdmin(ViewModelAdmin):
    inlines = [ResultsInline]
    readonly_fields = ('is_approved',)
    
    list_display = (
        'Paper_title',
        'get_info_html',
        'get_location_html',
        'get_case_html',
        'get_flags_html'
    )
    
    list_filter = (
        ('Study_design', ChoiceDropdownFilter), 
        ('Study_group', ChoiceDropdownFilter), 
        ('Disease', DropdownFilter),
        ('Coverage', DropdownFilter),
        ('Surveillance_setting', DropdownFilter),
        ('Clinical_definition_category', ChoiceDropdownFilter),
        ('Climate', DropdownFilter), 
        ('Aria_remote', DropdownFilter),
    )

    ordering = ('Paper_title', 'Study_group')

    search_fields = ('Paper_title', 'Paper_link', 'Study_description', 'Data_source_name', 'Specific_region', 'Method_limitations', 'Other_points')

    actions = [download_as_csv('Export selected Studies to CSV')]

    search_help_text = 'Search Titles, Study Descriptions, Data Source, Specific Geographic Location, Method Limitations, or Other Points for matching keywords. Put quotes around search terms to find exact phrases only.'

    download_as_csv_verbose_names = False
    download_as_csv_fields = [
        ('get_export_id', 'Unique_identifier'),
        'Study_group',
        'Paper_title',
        'Paper_link',
        'Year',
        'Disease',
        'Study_design',
        'Study_description',
        'Diagnosis_method',
        'Data_source',
        'Surveillance_setting',
        'Data_source_name',
        'Clinical_definition_category',
        'Coverage',
        'Climate',
        'Aria_remote',
        'Method_limitations',
        'Limitations_identified',
        'Other_points',
    ]

    def get_readonly_fields(self, request, obj=None):
        is_superuser = request.user.is_superuser
        if is_superuser:
            return []
        return self.readonly_fields

    @admin.display(ordering='Year', description='Study Info')
    def get_info_html(self, obj):
        return render_to_string('database/data/study_info.html', context={'row': obj})

    @admin.display(description='Flags')
    def get_flags_html(self, obj):
        return render_to_string('database/data/row_flags.html', context={'row': obj})
    
    @admin.display(description='Geography', ordering='Specific_region')
    def get_location_html(self, obj):
        return format_html('<div><b>Aria Remote: </b>{}<br><b>Climate: </b>{}<br><b>Coverage: </b>{}</div>',
            obj.Aria_remote, obj.Climate, obj.Coverage
        )

    @admin.display(description='Data Source', ordering='Diagnosis_method')
    def get_case_html(self, obj):
        return format_html('<div><b>Diagnosis method: </b>{}<br>'
            '<b>Data source: </b>{}<br><b>Data source name: </b>{}<br><b>Surveillance: </b>{}</div>',
            obj.Diagnosis_method, obj.Data_source, obj.Data_source_name, obj.Surveillance_setting,
        )

    # save email of user that's adding studies inline
    def save_formset(self, request, obj, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.added_by = request.user
            instance.save()
            formset.save()


class ResultsAdmin(ViewModelAdmin):
    readonly_fields = ('is_approved',)
    
    list_display = (
        'get_study_info_html',
        'get_method_info_html',
        'get_population_html',
        'get_flags_html',
        'get_point_estimate_html',
    )

    list_display_links = None

    list_filter = (
        ('Study__Study_group', ChoiceDropdownFilter), 
        ('Age_general', DropdownFilter),
        ('Population_gender', DropdownFilter), 
        ('Indigenous_population', DropdownFilter),
        ('Country', DropdownFilter),
        ('Jurisdiction', DropdownFilter),
        ('Year_start', NumericRangeFilter),
        ('Year_stop', NumericRangeFilter),
        'Proportion',
        'StrepA_attributable_fraction',
    )

    download_as_csv_verbose_names = False
    download_as_csv_fields = [
        ('Study__get_export_id', 'Results_ID'),
        ('Study__Study_group', 'Result_group'),
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
        'StrepA_attributable_fraction',
        'is_approved'
    ]

    ordering = ('-Study__Study_group', )    
    actions = [download_as_csv('Export selected results to CSV')]

    search_fields = ('Study__Paper_title', 'Measure', 'Specific_location')
    search_help_text = 'Search Study Titles, Measure, and Specific Location for matching keywords. Put quotes around search terms to find exact phrases only.'

    # from https://stackoverflow.com/questions/727928/django-admin-how-to-access-the-request-object-in-admin-py-for-list-display-met
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request
        return qs

    ## For the sake of sensible people make sure the ordering matches the FIRST item that appears in each cell ##

    @admin.display(ordering='Study__Paper_title', description='Study details')
    def get_study_info_html(self, obj):
        return render_to_string('database/data/result_study_info.html', context={'row': obj})

    @admin.display(ordering='Study__Study_group', description='Method details')
    def get_method_info_html(self, obj):
        return render_to_string('database/data/result_method_info.html', context={'row': obj})

    @admin.display(description='Population', ordering='Population_indigenous')
    def get_population_html(self, obj):
        return render_to_string('database/data/result_population_info.html', context={'row': obj})

    @admin.display(description='Flags')
    def get_flags_html(self, obj):
        return render_to_string('database/data/row_flags.html', context={'row': obj})

    @admin.display(description='Point Estimate')
    def get_point_estimate_html(self, obj):
        return render_to_string('database/data/result_point_estimate.html', context={'row': obj, 'user': self.request.user})

    def get_readonly_fields(self, request, obj=None):
            is_superuser = request.user.is_superuser
            if is_superuser:
                return []
            return self.readonly_fields

from database.admin_site import admin_site # Custom admin site

admin_site.register(Users, AccountAdmin)
admin_site.register(Studies, StudiesAdmin)
admin_site.register(Results, ResultsAdmin)
admin_site.unregister(Group)

def get_proxy_admin(model, base_admin):
    """ create generic admin pages for different results/study groups """
    class AnythingProxyAdmin(base_admin):
        list_display = [
            x for x in base_admin.list_display if x not in {'get_study_group', 'Study_group'}
        ]
        list_filter = [
            x for x in base_admin.list_filter if x not in {'Study__Study_group', 'Study_group'}
        ]
        
        def has_add_permission(self, request):
            # don't confuse users by letting them add "specific group" results/studies,
            # since the proxy admin doesn't actually constrain which group the result belongs to.
            return False

    return AnythingProxyAdmin

def register_proxy_admins():
    for p in proxies:
        model_admin = get_proxy_admin(p, ResultsAdmin if issubclass(p, Results) else StudiesAdmin)
        admin_site.register(p, model_admin)

register_proxy_admins()

# Proxy models for data not approved - viewable by superusers only
def get_proxy_is_approved_admin(model, base_admin):
    """ create generic admin pages for different results/study groups """
    class UnapprovedProxyAdmin(base_admin):
        list_display = [
            x for x in base_admin.list_display if x not in {'get_study_group', 'Study_group'}
        ]
        list_filter = [
            x for x in base_admin.list_filter if x not in {'Study__Study_group', 'Study_group'}
        ]
        
        # don't confuse users by letting them add "specific group" results/studies,
        # since the proxy admin doesn't actually constrain which group the result belongs to.
        def has_module_permission(self, request):
            if not request.user.is_superuser:
                return False
            return True
        
        def has_add_permission(self, request):
            return False
            
    return UnapprovedProxyAdmin

def register_proxy_is_approved_admins():
    for p in is_approved_proxies:
        model_admin = get_proxy_is_approved_admin(p, ResultsAdmin if issubclass(p, Results) else StudiesAdmin)
        
        admin_site.register(p, model_admin)

register_proxy_is_approved_admins()
