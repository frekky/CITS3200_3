
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.http import HttpResponseRedirect
from django.utils.html import format_html, mark_safe
from django.utils.http import urlencode
from django.template.loader import render_to_string
from django.urls import reverse
from rangefilter.filters import NumericRangeFilter
from admin_action_buttons.admin import ActionButtonsMixin

from database.models import *

from database.actions import download_as_csv
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, ChoiceDropdownFilter, RelatedDropdownFilter)
from django.db import models

from database.filters import TwoNumbersInRangeFilter, ChoicesMultipleSelectFilter
from .base import ViewModelAdmin

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

    def has_view_permission(self, request, obj=None):
        return True


class BaseResultsModelAdmin(ResultsAdminMixin, ViewModelAdmin):
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
        ('Study__Urban_rural_coverage', ChoicesMultipleSelectFilter), # multiple select

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

    search_fields = (
        # Study fields
        'Study__Study_group',
        'Study__Paper_title',
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
        'Study__Urban_rural_coverage',
        'Study__Limitations_identified',
        'Study__Other_points',

        # Result fields
        'Age_general',
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
        'Point_estimate',
        'Measure',
    )
    search_help_text = 'Search keywords in all fields. Put quotes around search terms to find exact phrases only.'

    checkbox_template = 'database/data/result_row_header.html'

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
                'Study__Urban_rural_coverage',
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
            ],
            verbose_names = True,
            filename = 'StrepA-Methods-Results-export-merged'
        )

    @admin.action(description='Admin: Backup Selected to Results CSV', permissions=['change'])
    def export_backup_csv(self, request, queryset):
        return download_as_csv(self, request, queryset,
            fields = [
                ('Study__get_export_id', 'Study_ID'),
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
            ],
            verbose_names = False,
            filename = 'StrepA-Results-Backup',
        )

@admin.register(Results)
class AllResultsView(BaseResultsModelAdmin):
    perm_view_all = Users.ACCESS_READONLY
    perm_view_owner = Users.ACCESS_READONLY

    perm_add = None
    perm_edit_all = Users.ACCESS_ADMIN
    perm_edit_owner = Users.ACCESS_CONTRIB

    perm_delete_all = Users.ACCESS_ADMIN
    perm_delete_owner = Users.ACCESS_CONTRIB

    perm_super = Users.ACCESS_SUPER

class ResultsSubmissionInline(admin.StackedInline):
    model = ResultsModel
    extra = 1