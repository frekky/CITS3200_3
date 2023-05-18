from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.auth.decorators import user_passes_test
from django import forms
from django.contrib import messages
import io
from database.models import ImportSource, StudiesModel, ResultsModel, Users
from database.importer import (
    load_studies_from_excel, process_db_import, get_field_descriptions,
)
from .admin_site import admin_site

class ImportDataForm(forms.ModelForm):
    class Meta:
        model = ImportSource
        fields = ('Source_file', 'Dataset')
        widgets = {
            'Source_file': forms.FileInput(attrs={
                'accept': '.xls, .xlsx, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel'
            }),
        }

    def clean(self):
        data = super().clean()
        # validate uploaded file
        upload_file = data['Source_file']
        filestream = io.BytesIO(upload_file.read())
        data['Import_data'] = load_studies_from_excel(filestream)
        data['Original_filename'] = upload_file.name
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.Import_data = self.cleaned_data['Import_data']
        obj.Original_filename = self.cleaned_data['Original_filename']
        obj.Upload_time = timezone.now()
        if commit:
            obj.save()
        return obj


def can_import_data(user):
    return user.access_level >= Users.ACCESS_CONTRIB

def get_import_overwrite_flag(state):
    if state is None:
        return ''
    elif state:
        return format_html('<span class="badge bg-primary">Imported data has not been changed since import</span>')
    else:
        return format_html('<span class="badge bg-danger">Imported data has been changed: make a backup before overwriting!</span>')

@user_passes_test(can_import_data)
def import_data_view(request):
    datasets_qs = request.user.Responsible_for_datasets.all()
    existing_objs = ImportSource.objects.filter(
        Import_time__isnull=False, Dataset_id__in=datasets_qs.values_list('id', flat=True),
        Deleted=False,
    )
    if request.user.access_level <= Users.ACCESS_CONTRIB:
        # for contributors: limit replacement of imported files to just those owned by this user
        existing_objs = existing_objs.filter(Imported_by=request.user)

    from database.admin.importer import ImportAdmin

    # have selectable fields to replace previously imported files
    overwrite_objs = {}
    overwrite_fields = {}
    for obj in existing_objs:
        key = 'importsource_%d' % obj.pk
        overwrite_objs[key] = obj
        overwrite_fields[key] = forms.BooleanField(
            required=False, label='Overwrite %s?' % str(obj), 
            help_text=get_import_overwrite_flag(obj.data_state),
        )

    import_form_class = type('ImportFormForRequest', (ImportDataForm, ), {
        **overwrite_fields,
        'Dataset': forms.ModelChoiceField(required=True, 
            queryset=datasets_qs,
            empty_label=None),
    })

    if request.method == 'POST':
        form = import_form_class(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.Imported_by = request.user
            obj.save()
            if process_db_import(request, obj):
                # delete rows for importsources selected for overwriting
                for key, to_clear in overwrite_objs.items():
                    if form.cleaned_data[key]:
                        to_clear.clear_rows()
                messages.success(request, 'The import was successful.')
            else:
                messages.error(request, 'Import was not successful, please check the Excel spreadsheet is in the correct format.')
            return redirect('admin:database_importsource_change', obj.id)
    else:
        form = import_form_class()


    return render(request, 'database/import_data.html', context={
        'form': form,
        'studies_fields': get_field_descriptions(StudiesModel),
        'results_fields': get_field_descriptions(ResultsModel),
        'title': 'Import Methods/Results',
        **admin_site.each_context(request),
    })
