from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.http import HttpResponseRedirect
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html, mark_safe
from django.utils.http import urlencode
from django.template.loader import render_to_string
from django.urls import reverse
from rangefilter.filters import NumericRangeFilter
from admin_action_buttons.admin import ActionButtonsMixin

from database.models import *

from .actions import download_as_csv
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, ChoiceDropdownFilter, RelatedDropdownFilter)
from django.db import models

from database.admin_site import admin_site # Custom admin site
from database.filters import TwoNumbersInRangeFilter, ChoicesMultipleSelectFilter

# Hide the groups from the admin site
admin_site.unregister(Group)

# The Custom Admin user model
@admin.register(Users)
class AccountAdmin(ActionButtonsMixin, UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'date_joined', 'is_superuser', 'profession', 'institution', 'country')
    fields = ('email', 'first_name', 'last_name', 'date_joined', 'profession', 'institution', 'country', 'is_superuser', 'is_active')
    readonly_fields = ('id', 'date_joined')
    actions = [download_as_csv('Export selected accounts to CSV')]
    
    list_filter = []
    search_fields = []
    ordering = ['email']
    exclude = ()
    
    filter_horizontal = ()
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

@admin.register(ImportSource)
class ImportAdmin(ActionButtonsMixin, ModelAdmin):
    list_display = ('Original_filename', 'Import_type', 'Row_count', 'Imported_by', 'Import_status')

@admin.register(Document)
class DocumentAdmin(ActionButtonsMixin, ModelAdmin):
    list_display = ('title', 'upload_file', 'all_users')

SUBMIT_HIDE_FIELDS = [
    'Unique_identifier',
    'Submission_status',
    'Created_by',
    'Approved_time',
    'Approved_by',
    'Import_source',
]

# override default behaviour to allow viewing by anyone
class ViewModelAdmin(ActionButtonsMixin, ModelAdmin):
    checkbox_template = None
    all_can_view = True
    owner_can_view = True
    all_can_add = False
    all_can_edit = False
    owner_can_edit = False
    no_add = False
    no_edit = False
    owner_can_delete = False
    no_delete = False

    def has_view_permission(self, request, obj=None):
        if self.all_can_view:
            return True
        if self.owner_can_view:
            if obj is not None:
                return request.user.pk == obj.Created_by_id
            else:
                return True

        return request.user.is_superuser

    def has_add_permission(self, request, obj=None):
        if self.no_add:
            return False
        return self.all_can_add or request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        if self.no_edit:
            return False
        if self.all_can_edit:
            return True
        if self.owner_can_edit:
            if obj is not None:
                return request.user.pk == obj.Created_by_id
            else:
                return True
            
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if self.no_delete:
            return False
        if self.owner_can_delete:
            if obj is not None:
                return request.user.pk == obj.Created_by_id
            else:
                return True
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Store request hack: from https://stackoverflow.com/questions/727928/django-admin-how-to-access-the-request-object-in-admin-py-for-list-display-met
        self.request = request
        return qs
    
    # save email of user that's adding studies/results
    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.Created_by = request.user
        
        super().save_model(request, obj, form, change)

    @admin.display(description=mark_safe('<input type="checkbox" id="action-toggle">'))
    def action_checkbox(self, obj):
        """
        A list_display column containing a checkbox widget.
        """
        if self.checkbox_template is None:
            return super().action_checkbox(obj)

        return render_to_string(self.checkbox_template, context={
            'ACTION_CHECKBOX_NAME': admin.helpers.ACTION_CHECKBOX_NAME,
            'row': obj,
            'user': self.request.user,
            'model_name': obj._meta.model_name,
        })

class ResultsAdminMixin:
    @admin.display(description='Study details')
    def get_study_info_html(self, obj):
        return render_to_string('database/data/result_study_info.html', context={'row': obj})

    @admin.display(description='Method details')
    def get_method_info_html(self, obj):
        return render_to_string('database/data/result_method_info.html', context={'row': obj})

    @admin.display(description='Population')
    def get_population_html(self, obj):
        return render_to_string('database/data/result_population_info.html', context={'row': obj})

    @admin.display(description='Geographic Info')
    def get_location_html(self, obj):
        return render_to_string('database/data/result_location_info.html', context={'row': obj})

    @admin.display(description='Flags')
    def get_flags_html(self, obj):
        return render_to_string('database/data/row_flags.html', context={'row': obj})

    @admin.display(description='Point Estimate')
    def get_point_estimate_html(self, obj):
        return render_to_string('database/data/result_point_estimate.html', context={'row': obj})
    
    @admin.action(description='Goto Studies for Selection')
    def view_parent_studies(self, request, queryset):
        study_ids = set()
        for result in queryset:
            study_ids.add(result.Study_id)

        return HttpResponseRedirect(self.model.get_view_results_studies_url(study_ids))

class ReadonlyResultsInline(ResultsAdminMixin, admin.TabularInline):
    model = ResultsModel
    can_delete = False
    fields = readonly_fields = (
        'get_population_html',
        'get_location_html',
        'get_flags_html',
        'get_point_estimate_html',
    )
    max_num = 0

class BaseStudiesModelAdmin(ViewModelAdmin):
    inlines = [ReadonlyResultsInline]
    readonly_fields = ('Approved_by', 'Updated_time', 'Created_time', 'Created_by', 'Import_source', 'Approved_time')
    
    list_display = (
        'get_publication_html',
        'get_method_html',
        'get_location_html',
        'get_notes_html',
    )

    list_display_links = None

    list_filter = (
        ('Study_group', ChoiceDropdownFilter), 
        ('Disease', ChoicesMultipleSelectFilter),
        ('Year', NumericRangeFilter),
        ('Study_design', ChoiceDropdownFilter),
        ('Diagnosis_method', ChoicesMultipleSelectFilter),
        ('Data_source', ChoicesMultipleSelectFilter),
        ('Surveillance_setting', ChoicesMultipleSelectFilter),
        ('Clinical_definition_category', ChoicesMultipleSelectFilter),
        ('Coverage', ChoicesMultipleSelectFilter),
        ('Climate', ChoicesMultipleSelectFilter),
        ('Aria_remote', ChoicesMultipleSelectFilter),
    )

    checkbox_template = 'database/data/study_row_header.html'

    ordering = ('Study_group', '-Paper_title')

    search_fields = ('Paper_title', 'Study_description', 'Data_source_name', 'Specific_region', 'Method_limitations', 'Other_points')
    search_help_text = 'Match keywords in any of the following fields: paper title, study description, data source name, specific location, method limitations, other points. Put quotes around search terms to find exact phrases only.'

    actions = ['view_child_results', 'export_csv', 'export_backup_csv', 'delete_selected']

    @admin.display(description='Study Details')
    def get_publication_html(self, obj):
        return render_to_string('database/data/study_publication_info.html', context={'row': obj})

    @admin.display(description='Geography')
    def get_location_html(self, obj):
        return render_to_string('database/data/study_geography_info.html', context={'row': obj})

    @admin.display(description='Method Details')
    def get_method_html(self, obj):
        return render_to_string('database/data/study_method_info.html', context={'row': obj})

    @admin.display(description='Notes')
    def get_notes_html(self, obj):
        return render_to_string('database/data/study_notes.html', context={'row': obj})

    @admin.action(description='Goto Results for Selected')
    def view_child_results(self, request, queryset):
        study_ids = set()
        for obj in queryset:
            study_ids.add(obj.pk)

        return HttpResponseRedirect(self.model.get_view_study_results_url(study_ids))

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not request.user.is_superuser:
            for x in SUBMIT_HIDE_FIELDS:
                if x in fields:
                    fields.remove(x)
        return fields

    @admin.action(description='Export Selected to CSV')
    def export_csv(self, request, queryset):
        return download_as_csv(self, request, queryset,
            fields = [
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
                'Aria_remote',
                'Limitations_identified',
                'Other_points',
                'Created_by_name',
                'Approved_by_name',
            ],
            verbose_names = True,
            filename = 'StrepA-Methods-export',
        )

    @admin.action(description='Admin: Backup Selected to Methods CSV', permissions=['change'])
    def export_backup_csv(self, request, queryset):
        return download_as_csv(self, request, queryset,
            fields = [
                ('get_export_id', 'Unique_identifier'),
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
                'Aria_remote',
                'Limitations_identified',
                'Other_points',
                'Created_time',
                'Created_by_name',
                'Updated_time',
                'Approved_time',
                'Approved_by_name',
            ],
            verbose_names = False,
            filename = 'StrepA-Methods-Backup'
        )

    

class BaseResultsModelAdmin(ResultsAdminMixin, ViewModelAdmin):
    readonly_fields = ('Approved_by', 'Updated_time', 'Created_time', 'Created_by', 'Import_source', 'Approved_time')
    
    list_display = (
        'get_study_info_html',
        'get_method_info_html',
        'get_population_html',
        'get_location_html',
        'get_flags_html',
        'get_point_estimate_html',
    )

    list_display_links = None

    list_filter = (
        # Methods-related filters
        ('Study__Study_group', ChoiceDropdownFilter), # hierarchy Study_group -> Disease as sub-category
        ('Study__Disease', ChoicesMultipleSelectFilter), # multiple select within Study_group options
        ('Study__Year', NumericRangeFilter), # standard number range (inclusive)
        ('Study__Study_design', ChoiceDropdownFilter), # single select
        ('Study__Diagnosis_method', ChoicesMultipleSelectFilter), # multiple select
        ('Study__Data_source', ChoicesMultipleSelectFilter), # multiple select
        ('Study__Surveillance_setting', ChoicesMultipleSelectFilter), # multiple select
        ('Study__Clinical_definition_category', ChoicesMultipleSelectFilter), # multiple select
        ('Study__Coverage', ChoicesMultipleSelectFilter), # multiple select
        ('Study__Climate', ChoicesMultipleSelectFilter), # multiple select
        ('Study__Aria_remote', ChoicesMultipleSelectFilter), # multiple select

        # Result-specific filters
        ('Age_general', ChoicesMultipleSelectFilter), # multiple select
        ('Population_gender', ChoicesMultipleSelectFilter), # multiple select
        ('Indigenous_population', ChoicesMultipleSelectFilter), # multiple select
        ('Country', DropdownFilter), # single select hierarchy Country -> Jurisdiction
        ('Jurisdiction', DropdownFilter), # multiple select from distinct values only with matching Country
        (TwoNumbersInRangeFilter.create('Observation dates (year)', ('Year_start', 'Year_stop'))), # single filter for entire start/stop range (inclusive of partial range overlaps)
        #('Year_stop', NumericRangeFilter),
        ('Proportion', DropdownFilter), # single select
        ('StrepA_attributable_fraction', DropdownFilter), # single select
    )

    actions = ['view_parent_studies', 'export_merged_csv', 'export_backup_csv', 'delete_selected']

    ordering = ('Study__Study_group', '-Study__Paper_title', )    

    search_fields = ('Study__Paper_title', 'Measure', 'Specific_location')
    search_help_text = 'Match keywords in the following fields: Paper title, Measure, Specific location. Put quotes around search terms to find exact phrases only.'

    checkbox_template = 'database/data/result_row_header.html'

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not request.user.is_superuser:
            for x in SUBMIT_HIDE_FIELDS:
                if x in fields:
                    fields.remove(x)
        return fields

    @admin.action(description='Export Selected to CSV')
    def export_merged_csv(self, request, queryset):
        return download_as_csv(self, request, queryset,
            fields = [
                # Study fields
                'Study__Study_group',
                'Study__Paper_title',
                'Study__Paper_link',
                'Study__Year',
                'Study__Study_description',
                'Study__Disease',
                'Study__Study_design',
                'Study__Diagnosis_method',
                'Study__Data_source',
                'Study__Data_source_name',
                'Study__Surveillance_setting',
                'Study__Clinical_definition_category',
                'Study__Coverage',
                'Study__Climate',
                'Study__Aria_remote',
                'Study__Limitations_identified',
                'Study__Other_points',

                # Result fields
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
                'Created_by_name',
                'Approved_by_name',
            ],
            verbose_names = True,
            filename = 'StrepA-Methods-Results-export-merged'
        )

    @admin.action(description='Admin: Backup Selected to Results CSV', permissions=['change'])
    def export_backup_csv(self, request, queryset):
        return download_as_csv(self, request, queryset,
            fields = [
                ('Study__get_export_id', 'Results_ID'),
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
                'Created_time',
                'Created_by_name',
                'Updated_time',
                'Approved_time',
                'Approved_by_name',
            ],
            verbose_names = False,
            filename = 'StrepA-Results-Backup',
        )

@admin.register(Studies)
class AllStudiesView(BaseStudiesModelAdmin):
    all_can_view = True
    no_add = True
    no_edit = True

@admin.register(Results)
class AllResultsView(BaseResultsModelAdmin):
    all_can_view = True
    no_add = True

class ResultsSubmissionInline(admin.StackedInline):
    model = ResultsModel
    extra = 1

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        for x in SUBMIT_HIDE_FIELDS:
            if x in fields:
                fields.remove(x)
        fields.remove('Submission_notes')
        return fields

@admin.register(My_Drafts)
class EditMyDrafts(BaseStudiesModelAdmin):
    all_can_add = True
    owner_can_view = True
    owner_can_edit = True
    owner_can_delete = True

    inlines = [ResultsSubmissionInline]

    list_display = (
        'get_submission_html',
        'get_publication_html',
        'get_method_html',
        'get_location_html',
        'get_notes_html',
    )

    @admin.display(ordering='Created_time', description='Submission Details')
    def get_submission_html(self, obj):
        return render_to_string('database/data/study_submission_info.html', context={'row': obj})

    actions = [*BaseStudiesModelAdmin.actions, 'approve_study']
    
    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        for x in SUBMIT_HIDE_FIELDS:
            if x in fields:
                fields.remove(x)
        fields.remove('Submission_notes')
        return fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # don't filter by user
        return qs
        #return qs.filter(Created_by__exact=request.user)

    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.Created_by = request.user
            obj.Submission_status = 'draft'
        
        if '_approve' in request.POST:
            obj.Submission_status = 'approved'
            obj.Approved_by = request.user
        
        super().save_model(request, obj, form, change)

    @admin.action(description='Publish Selected Submissions')
    def approve_study(self, request, queryset):
        num_rows = queryset.update(Submission_status='approved', Approved_by=request.user, Approved_time=timezone.now())
        self.message_user(request, '%d studies marked as approved.' % num_rows)
