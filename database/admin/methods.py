from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.http import HttpResponseRedirect
from django.utils.html import format_html, mark_safe
from django.utils.http import urlencode
from django.utils import timezone
from django.template.loader import render_to_string
from django.urls import reverse
from django import forms
from rangefilter.filters import NumericRangeFilter
from admin_action_buttons.admin import ActionButtonsMixin

from database.models import *

from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, ChoiceDropdownFilter, RelatedDropdownFilter)
from django.db import models
from database.exporter import download_excel_worksheet

from database.filters import TwoNumbersInRangeFilter, ChoicesMultipleSelectFilter

from .base import ViewModelAdmin
from .results import ReadonlyResultsInline, ResultsSubmissionInline


SUBMIT_HIDE_FIELDS = [
    'Unique_identifier',
    'Created_by',
    'Approved_time',
    'Approved_by',
    'Import_source',
]

class StudiesForm(forms.ModelForm):
    class Meta:
        model = StudiesModel
        exclude = []

class BaseStudiesModelAdmin(ViewModelAdmin):
    inlines = [ReadonlyResultsInline]
    readonly_fields = (
        'Approved_by', 'Updated_time', 'Created_time', 'Created_by', 'Import_source', 'Approved_time',
        'Import_row_id', 'Import_row_number',
    )
    
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
        ('Urban_rural_coverage', ChoicesMultipleSelectFilter),
    )

    checkbox_template = 'database/data/study_row_header.html'

    ordering = ('Study_group', '-Paper_title')

    search_fields = (
        'Study_group',
        'Paper_title',
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
        'Limitations_identified',
        'Other_points',
    )
    search_help_text = 'Search keywords in all fields. Put quotes around search terms to find exact phrases only.'

    actions = ['export_selected', 'view_child_results', 'delete_selected']

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

    @admin.action(description='View Results for Selected')
    def view_child_results(self, request, queryset):
        study_ids = set()
        for obj in queryset:
            study_ids.add(obj.pk)

        return HttpResponseRedirect(self.model.get_view_study_results_url(study_ids))

    @admin.action(description='Export Selected to Excel')
    def export_selected(self, request, queryset):
        study_ids = queryset.values_list('pk', flat=True)
        my_results = ResultsModel.objects.filter(Study_id__in=study_ids).order_by('Study_id')
        my_studies = queryset.order_by('pk')
        return download_excel_worksheet(my_studies, my_results)
    
    def get_fields(self, request, obj=None):
        """ Get list of fields to view or edit in the object view/change page """
        fields = list(super().get_fields(request, obj))
        if request.user.access_level < Users.ACCESS_ADMIN:
            for x in ['Created_by', 'Approved_by']:
                if x in fields:
                    fields.remove(x)
        return fields

    def get_form(self, request, obj=None, change=False, **kwargs):
        datasets_qs = request.user.Responsible_for_datasets.all()
        form_class = type('MyStudiesForm', (StudiesForm, ), {
            'Dataset': forms.ModelChoiceField(
                required=True, 
                queryset=datasets_qs,
                empty_label=None),
        })
        kwargs['form'] = form_class
        return super().get_form(request, obj, change, **kwargs)
    
    # save email of user that's adding studies/results
    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.Created_by = request.user
        
        super().save_model(request, obj, form, change)


@admin.register(Studies)
class AllStudiesView(BaseStudiesModelAdmin):
    perm_view_all = Users.ACCESS_READONLY
    perm_view_owner = Users.ACCESS_READONLY

    perm_add = None
    perm_edit_all = Users.ACCESS_ADMIN
    perm_edit_owner = Users.ACCESS_CONTRIB

    perm_delete_all = Users.ACCESS_ADMIN
    perm_delete_owner = Users.ACCESS_CONTRIB

    perm_super = Users.ACCESS_SUPER

    actions = [*BaseStudiesModelAdmin.actions, 'revert_to_draft']

    @admin.action(description='Revert Selected to Draft', permissions=['change', 'delete'])
    def revert_to_draft(self, request, queryset):
        for study in queryset:
            if not self.has_change_permission(request, study):
                messages.warning(request, 'Not allowed to edit one or more of the selected studies. If they were imported, edit them in the spreadsheet. If not, submit a correction/addition request.')
                return
        num_rows = queryset.update(Approved_by=None, Approved_time=None, Import_source=None)
        self.message_user(request, '%d studies reverted to draft for editing' % num_rows)
        return HttpResponseRedirect(reverse('admin:database_my_drafts_changelist'))

    def has_delete_permission(self, request, obj=None):
        if obj and obj.Import_source:
            return False # prevent deletion of objects which are imported from somewhere
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.Import_source:
            return False
        return super().has_change_permission(request, obj)
    


@admin.register(My_Drafts)
class EditMyDrafts(BaseStudiesModelAdmin):
    perm_view_all = None
    perm_view_owner = Users.ACCESS_CONTRIB

    perm_add = Users.ACCESS_CONTRIB
    perm_edit_all = None
    perm_edit_owner = Users.ACCESS_CONTRIB

    perm_delete_all = None
    perm_delete_owner = Users.ACCESS_CONTRIB

    perm_super = None

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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(Created_by=request.user)

    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.Created_by = request.user
            obj.Submission_status = 'draft'
        
        if '_approve' in request.POST:
            obj.Submission_status = 'approved'
            obj.Approved_by = request.user
            obj.Approved_time = timezone.now()
        
        super().save_model(request, obj, form, change)

    @admin.action(description='Approve Selected')
    def approve_study(self, request, queryset):
        num_rows = queryset.update(Approved_by=request.user, Approved_time=timezone.now())
        self.message_user(request, '%d studies marked as approved.' % num_rows)
