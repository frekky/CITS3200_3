from django.db import transaction
from django.shortcuts import render, redirect
import io

from database.models import ImportSource, StudiesModel, ResultsModel
from database.forms import ImportDataForm
from database.importer import import_csv_file, import_results_row_dict, import_methods_row_dict, get_field_descriptions
from .admin_site import admin_site

def import_data_view(request):
    form = ImportDataForm()
    res = None

    if request.method == 'POST':
        form = ImportDataForm(request.POST, request.FILES)
        if form.is_valid():

            # import data
            study_src = ImportSource(
                Source_file = form.cleaned_data['studies_file'],
                Original_filename = form.cleaned_data['studies_file'].name,
                Import_type = 'studies',
                Imported_by = request.user,
            )

            result_src = ImportSource(
                Source_file = form.cleaned_data['results_file'],
                Original_filename = form.cleaned_data['results_file'].name,
                Import_type = 'results',
                Imported_by = request.user,
            )

            with transaction.atomic():
                # clear old data
                ImportSource.objects.all().delete()

                # create & save studies
                studies_ok, studies = import_csv_file(study_src, import_methods_row_dict)
                for inst in studies:
                    inst.save()

                # create & save results
                if studies_ok:
                    results_ok, results = import_csv_file(result_src, import_results_row_dict)
                    for inst in results:
                        inst.save()
                else:
                    results_ok = False
                    result_src.Import_log += 'Studies required to import results'
                    result_src.save()
                
                res = [
                    {
                         'title': ('Studies/methods imported successfully (%d rows)' % study_src.Row_count) if studies_ok else 'Error importing studies',
                         'items': study_src.Import_log.strip().split('\n'),
                    },
                    {
                        'title': ('Results imported successfully (%d rows)' % result_src.Row_count) if results_ok else 'Error importing results',
                        'items': result_src.Import_log.strip().split('\n'),
                    }
                ]

    return render(request, 'database/import_data.html', context={
        'form': form,
        'results': res,
        'studies_fields': get_field_descriptions(StudiesModel),
        'results_fields': get_field_descriptions(ResultsModel),
        'title': 'Import Methods/Results',
        **admin_site.each_context(request),
    })
