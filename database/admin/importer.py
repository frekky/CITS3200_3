from django.contrib import admin
from admin_action_buttons.admin import ActionButtonsMixin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin import helpers, widgets
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django import forms
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from database.actions import download_as_csv
from database.models import (
    Users, ImportSource, Document, DataRequest, StudiesModel, ResultsModel,
)
from database.importer import load_studies_from_excel

from database.admin_views import import_data_view

import io, logging
from datetime import timedelta

from .base import ViewModelAdmin

logger = logging.getLogger(__name__)

@admin.register(ImportSource)
class ImportAdmin(ViewModelAdmin):
    list_display = ('Original_filename', 'Imported_by', 'Import_time', 'import_status_short',)
    add_form_template = 'database/import_data_form.html'

    exclude = ('Import_data', )

    readonly_fields = (
        'Source_file', 'Original_filename', 'Dataset',
        'Imported_by', 'Import_time', 'Upload_time', 'import_status_short', 'import_log_html', 
    )

    def get_urls(self):
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        my_urls = [
            path('add/', self.admin_site.admin_view(import_data_view), name='%s_%s_add' % info),
            #path('import/', self.admin_site.admin_view(import_data_view), name='import_data'),
        ]
        return my_urls + urls

    @admin.display(description='Imported data status')
    def import_status_short(self, obj):
        if not obj.Import_time:
            return "File uploaded but not yet imported"
        modified_time_cutoff = obj.Import_time + timedelta(seconds=10)
        studies = StudiesModel.objects.filter(
            Import_source=obj, Approved_by__isnull=False, Updated_time__lte=modified_time_cutoff
        ).count()
        results = ResultsModel.objects.filter(
            Study__Import_source=obj, Approved_by__isnull=False, Updated_time__lte=modified_time_cutoff
        ).count()

        try:
            imp_studies = len(obj.Import_data)
            imp_results = 0
            for meth in obj.Import_data.values():
                imp_results += len(meth['results']) if 'results' in meth else 0
        except Exception:
            imp_studies = 0
            imp_results = 0
        
        return format_html(
            '<b>{}</b>: <b>{}</b> Methods rows were imported and <b>{}</b> have not been altered<br>'
            '<b>{}</b>: <b>{}</b> Results rows were imported and <b>{}</b> have not been altered',
            'OK' if studies == imp_studies else 'Data Changed', imp_studies, studies,
            'OK' if results == imp_results else 'Data Changed', imp_results, results
        )

    @admin.display(description='Imported data summary')
    def import_log_html(self, obj):
        try:
            methods_warnings = []
            results_warnings = []
            for meth_row in obj.Import_data.values():
                if meth_row.get('warnings'):
                    methods_warnings.append(
                        'Row %s: %s' % (rowid, meth_row.get('warnings'))
                    )
                if not 'results' in meth_row:
                    continue
                for rowid, row in meth_row['results'].items():
                    if row.get('warnings'):
                        results_warnings.append(
                            'Row %s: %s' % (rowid, row.get('warnings'))
                        )
        except Exception as e:
            logger.error('%s: %s' % (type(e).__name__, str(e)))
            results_warnings = None
            methods_warnings = None

        #logger.error('%s\n%s' % (methods_rows, results_rows))

        return render_to_string('database/data/import_log.html', {
            'obj': obj,
            'methods_warnings': methods_warnings,
            'results_warnings': results_warnings,
            'studies_fields': StudiesModel.IMPORT_FIELDS,
            'studies_warning_colspan': len(StudiesModel.IMPORT_FIELDS) - 1,
            'results_fields': ResultsModel.IMPORT_FIELDS,
            'results_warning_colspan': len(ResultsModel.IMPORT_FIELDS) - 1,
        })
