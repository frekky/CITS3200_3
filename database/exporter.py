import xlsxwriter, logging, io
from django.http import HttpResponse
from database.models import StudiesModel, ResultsModel
from database.importer import get_field_descriptions, get_field_type_description
from datetime import date
from django.db import models

logger = logging.getLogger(__name__)

EXTRA_ROWS = 10

def get_data_validation(djfield):
    if isinstance(djfield, models.CharField):
        if djfield.choices:
            # set up auto fill choices
            return {
                'validate': 'list',
                'source': [ choice[1] for choice in djfield.choices ],
            }
    elif isinstance(djfield, models.BooleanField):
        choices = ['Yes', 'No']
        if djfield.null:
            choices.append('N/A')
        return {
            'validate': 'list',
            'source': choices,
        }

def get_fields(model):
    return [
        (
            f.name,
            f.name,
            "%s - %s\n%s" % (
                f.verbose_name,
                get_field_type_description(f),
                f.help_text,
            ),
            f,
            get_data_validation(f)
        ) for f in (
            model._meta.get_field(field_name) 
            for field_name in model.IMPORT_FIELDS[1:]
        )
    ]

STUDY_FIELDS = [
    (
        'pk',
        'Unique_identifier',
        'Must be something different for every study in the spreadsheet',
        None,
        None,
    )
] + get_fields(StudiesModel)

RESULT_FIELDS = [
    (
        'Study_id',
        'Study_ID',
        'Must be an exact match of the corresponding study\'s Unique_identifier in the Methods sheet',
        None,
        None,
    )
] + get_fields(ResultsModel)

def write_model_row(sheet, inst, row, fields_spec):
    col = 0
    for spec in fields_spec:
        field_name, _, _, djfield, validation = spec
        value = getattr(inst, field_name)
        sheet.write(row, col, value)
        col += 1

def write_header_row(worksheet, fields_spec, fmt):
    col = 0
    row = 0
    for spec in fields_spec:
        _, col_name, comment, _, _ = spec
        worksheet.write_string(row, col, col_name, cell_format=fmt)
        worksheet.write_comment(row, col, comment)
        worksheet.set_column(col, col, width=len(col_name) + 2)
        col += 1

def write_worksheet(worksheet, instances, field_spec, header_format):
    write_header_row(worksheet, field_spec, header_format)
    row = 1
    for inst in instances:
        write_model_row(worksheet, inst, row, field_spec)
        row += 1

    # add validation dropdowns for choice and boolean fields
    col = 0
    for spec in field_spec:
        validation = spec[4]
        if validation:
            worksheet.data_validation(1, col, row + EXTRA_ROWS, col, validation)
        col += 1

    worksheet.autofilter(0, 0, row - 1, len(field_spec) - 1)

def write_excel_workbook(workbook, studies, results):
    header_format = workbook.add_format({'bold': True})
    methods_sheet = workbook.add_worksheet('Methods')
    write_worksheet(methods_sheet, studies, STUDY_FIELDS, header_format)
    results_sheet = workbook.add_worksheet('Results')
    write_worksheet(results_sheet, results, RESULT_FIELDS, header_format)

def download_excel_worksheet(studies_qs, results_qs):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    write_excel_workbook(workbook, studies_qs, results_qs)
    workbook.close()

    resp = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = 'attachment; filename=ASAVI-StrepA-Studies_%s.xlsx' % date.today().strftime('%d-%m-%Y')

    return resp
    