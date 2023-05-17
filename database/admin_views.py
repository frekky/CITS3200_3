from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django import forms
import io
from database.models import ImportSource, StudiesModel, ResultsModel, Users
from database.importer import (
    load_studies_from_excel, import_results_row_dict, import_methods_row_dict, get_field_descriptions,
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

@user_passes_test(can_import_data)
def import_data_view(request):
    import_form_class = type('ImportFormForRequest', (ImportDataForm, ), {
        'Dataset': forms.ModelChoiceField(required=True, 
            queryset=request.user.Responsible_for_datasets.all(),
            empty_label=None)
    })
    form = import_form_class()
    res = None

    if request.method == 'POST':
        form = import_form_class(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()

            return redirect('admin:database_importsource_change', obj.id)

    return render(request, 'database/import_data.html', context={
        'form': form,
        'results': res,
        'studies_fields': get_field_descriptions(StudiesModel),
        'results_fields': get_field_descriptions(ResultsModel),
        'title': 'Import Methods/Results',
        **admin_site.each_context(request),
    })
