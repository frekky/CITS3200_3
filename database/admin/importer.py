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
    list_display = ('Original_filename', 'Imported_by', 'Upload_time', 'Import_time', 'import_status_short',)
    add_form_template = 'database/import_data_form.html'

    exclude = ('Import_data', 'Deleted')

    readonly_fields = (
        'Source_file', 'Original_filename', 'Dataset',
        'Imported_by', 'Import_time', 'Upload_time', 'import_status_short', 'import_log_html', 
        #'Import_data',
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
        state = obj.data_state
        if state == 'failed':
            return format_html('<span class="badge bg-warning text-black">Import not successful</span>')
        elif state == 'consistent':
            return format_html('<span class="badge bg-primary">Data OK: Not changed since imported</span>')
        elif state == 'inconsistent':
            return format_html('<span class="badge bg-danger">Data Has Changed: Make a backup first!</span>')
        elif state == 'overwritten':
            return format_html('<span class="badge bg-success">Overwritten by another import</span>')
        
    @admin.display(description='Imported data summary')
    def import_log_html(self, obj):
        try:
            methods_warnings = []
            results_warnings = []
            for meth_rowid, meth_row in obj.Import_data.items():
                if meth_row.get('warnings'):
                    methods_warnings.append(
                        (int(meth_rowid) + 2, meth_row.get('warnings'))
                    )
                if not 'results' in meth_row:
                    continue
                
                for rowid, row in meth_row['results'].items():
                    if row.get('warnings'):
                        results_warnings.append(
                            (int(rowid) + 2, row.get('warnings'))
                        )
        except Exception as e:
            logger.error('%s: %s' % (type(e).__name__, str(e)))
            results_warnings = None
            methods_warnings = None

        return render_to_string('database/data/import_log.html', {
            'obj': obj,
            'methods_warnings': sorted(methods_warnings, key=lambda x: x[0]),
            'results_warnings': sorted(results_warnings, key=lambda x: x[0]),
        })
