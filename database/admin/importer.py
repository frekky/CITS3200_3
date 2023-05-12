from django.contrib import admin
from admin_action_buttons.admin import ActionButtonsMixin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin import helpers, widgets
from django.urls import path
from django import forms
from django.template.loader import render_to_string

from database.actions import download_as_csv
from database.models import Users, ImportSource, Document, DataRequest, StudiesModel, ResultsModel

from .base import ViewModelAdmin

from database.importer import (
    import_csv_file, import_results_row_dict, import_methods_row_dict, get_field_descriptions,
)

class ImportForm(forms.ModelForm):
    class Meta:
        model = ImportSource
        fields = ('Source_file', )

@admin.register(ImportSource)
class ImportAdmin(ViewModelAdmin):
    list_display = ('Original_filename', 'Row_count', 'Imported_by', 'Import_status', 'Import_log')
    add_form_template = 'database/import_data_form.html'
    
    readonly_fields = ('Original_filename', 'Row_count', 'Imported_by', 'Import_status', 'Import_log')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            #path('import/', self.admin_site.admin_view(import_data_view), name='import_data'),
        ]
        return my_urls + urls

    @admin.display(description='Import log')
    def import_log_html(self, obj):
        return render_to_string('database/data/import_log.html', {
            'lines': obj.Import_log.split('\n') if obj.Import_log else []
        })

    def add_view(self, request, form_url="", extra_context=None, **kwargs):
        extra_context = extra_context or {}
        extra_context.update({
            'studies_fields': get_field_descriptions(StudiesModel),
            'results_fields': get_field_descriptions(ResultsModel),
        })
        return super().add_view(request, form_url, extra_context, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            kwargs['form'] = ImportForm
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        if obj:
            return ['Import_source']
        else:
            return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return []
        else:
            return super().get_readonly_fields(request, obj)

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)

        # TODO: import the file here
        
        return super().save_model(request, obj, form, change)

