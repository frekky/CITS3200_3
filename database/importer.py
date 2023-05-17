import csv
import logging
import io
import math

from django.db import transaction
from django.db.models import fields
from django.core.exceptions import FieldDoesNotExist, ValidationError
from database.models import StudiesModel, ResultsModel, Dataset

import decimal
import pandas as pd

logger = logging.getLogger(__name__)

NULL_VALUES = ('n/a', 'not applicable', 'none', 'not defined', '', 'missing')
TRUE_VALUES = ('t', '1', 'yes', 'y', 'true')
FALSE_VALUES = ('f', '0', 'no', 'n', 'false')

def parse_bool(value):
    if value is None:
        return None

    if not isinstance(value, str):
        return bool(value)

    value = value.lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    else:
        return None

def format_bool_charfield(value):
    if value is None:
        return '?'
    if value == True:
        return 'Y'
    else:
        return 'F'

def get_field_descriptions(model):
    fdesc = []
    for field in model._meta.get_fields():
        if field.name in ('Created_time', 'Updated_time', 'Approved_time', 
            'Created_by', 'Approved_by', 'Submission_status'):
            continue

        if isinstance(field, fields.reverse_related.ManyToOneRel):
            continue
        if isinstance(field, fields.related.ForeignKey):
            continue
        
        if field.name == 'id':
            continue

        if isinstance(field, fields.CharField):
            field_type = 'Text (up to %d characters)' % field.max_length
        elif isinstance(field, fields.TextField):
            field_type = 'Text'
        elif isinstance(field, fields.DecimalField):
            field_type = 'Decimal'
        elif isinstance(field, (fields.PositiveSmallIntegerField, fields.PositiveIntegerField)):
            field_type = 'Number'
        elif isinstance(field, fields.BooleanField):
            field_type = 'Yes/No/Unknown'
        else:
            field_type = 'Other'

        fdesc.append({
            'djfield': field,
            'type': field_type,
        })
    return fdesc

def parse_django_field_value(model, field, value):
    try:
        djfield = model._meta.get_field(field)

        if isinstance(djfield, fields.CharField):
            value = str(value)
            if djfield.choices:
                lower = value.lower().strip()
                for c in djfield.choices:
                    if lower == c[1].lower().strip() or lower == c[0].lower().strip():
                        return (c[0], True)
                if lower in NULL_VALUES:
                    if djfield.null:
                        return None, True
                    else:
                        return 'missing', False
                return ('"%s" is not an allowed option' % (value), False)
            if value.lower().strip() in NULL_VALUES:
                if djfield.null:
                    return None, True
                else:
                    return 'missing', False
            if len(value) >= djfield.max_length:
                return ('"%s" is too long (max length %d)' % (
                    value, djfield.max_length
                ), False)
            return (value or '', True)
        elif isinstance(djfield, fields.TextField):
            return str(value), True

        if str(value).lower() in NULL_VALUES:
            return (None, True)
        elif isinstance(djfield, fields.DecimalField):
            value = float(value)
            if math.isnan(value):
                return ("Cannot parse decimal value %s (got NaN)" % value, False)

            if djfield.decimal_places:
                value = round(value, djfield.decimal_places)
            if djfield.max_digits:
                digits = djfield.max_digits - (djfield.decimal_places or 0)
                value = min(value, pow(10, digits) - 1)
        elif isinstance(djfield, (fields.PositiveSmallIntegerField, fields.PositiveIntegerField)):
            if isinstance(value, str):
                value = int(value.replace(',', ''))
            else:
                value = int(value)
        elif isinstance(djfield, fields.BooleanField):
            value = parse_bool(value)
            if not value and not djfield.null:
                value = False

        elif isinstance(djfield, fields.ForeignKey):
            return ("Can't import related field", False)

        return value, True

    except ValueError:
        return "Can't parse value '%s'" % value, False

    except decimal.InvalidOperation:
        return "Invalid decimal value '%s'" % value, False

    except FieldDoesNotExist:
        return "No such field exists", False

def import_csv_file(import_source, for_each_row):
    csv_text = import_source.Source_file.read().decode('utf-8', errors='replace')
    csv_stream = io.StringIO(csv_text)
    csv_reader = csv.DictReader(csv_stream)

    instances = []
    row_num = 1
    log = ''
    okay = True
    for csv_row in csv_reader:
        row_num += 1
        instance, msg = for_each_row(csv_row, import_source)
        id = csv_row.get('Unique_identifier') or csv_row.get('Results_ID') or csv_row.get('Study_ID') or ''
        if not instance:
            log += 'Row %d (%s): Error: %s\n' % (row_num, id, msg)
            okay = False
        elif msg:
            log += 'Row %d (%s): Warning: %s\n' % (row_num, id, msg)
        
        if instance:
            instances.append(instance)

    import_source.Import_log = log
    import_source.Import_status = okay
    import_source.Row_count = len(instances)
    import_source.save()

    return okay, instances
    
def import_methods_row_dict(row, import_source):
    study = StudiesModel(
        Import_source = import_source,
        Created_by = import_source.Imported_by,
        Approved_by = import_source.Imported_by,
        Approved_time = import_source.Import_time,
        Submission_status = 'approved',
    )

    field_errors = []

    for field, value in row.items():

        # skip foreign keys & auto fields
        if field in ('Approved_by', 'Created_by', 'Import_source', 'Approved_time', 'Created_time', 'Updated_time'):
            continue
        
        value, ok = parse_django_field_value(StudiesModel, field, value)
        if not ok:
            field_errors.append('%s: %s' % (field, value))
        else:
            setattr(study, field, value)

    return study, (', '.join(field_errors) if len(field_errors) > 0 else None)

def import_results_row_dict(row, import_source):
    result = ResultsModel(
        Import_source = import_source,
        Created_by = import_source.Imported_by,
        Approved_by = import_source.Imported_by,
        Approved_time = import_source.Import_time,
        Submission_status = 'approved',
    )

    field_errors = []

    for field, value in row.items():

        # skip foreign key & auto fields
        if field in ('Study_ID', 'Results_ID', 'Approved_by', 'Created_by',
            'Import_source', 'Approved_time', 'Created_time', 'Updated_time'):
            continue

        if field == 'Point_estimate':
            try:
                value = "%0.2f" % float(value)
            except ValueError:
                pass
        
        value, ok = parse_django_field_value(ResultsModel, field, value)
        if not ok:
            field_errors.append("%s: %s" % (field, value))
        else:
            setattr(result, field, value)

    # link to related study/methods row based on Unique_identifier = Study_ID
    if 'Study_ID' in row and (study_id := row['Study_ID']):
        # check Unique_identifier first
        studies = list(StudiesModel.objects.filter(Unique_identifier=study_id))
        if len(studies) == 0 and study_id:
            try:
                # nothing found: try searching by database ID instead (ie. for online-submitted studies/results)
                studies = list(StudiesModel.objects.filter(id=study_id))
            except:
                pass

        if len(studies) == 0:
            field_errors.append("Study not found (%s)" % study_id)
            result = None
        elif len(studies) > 1:
            field_errors.append("Multiple studies found (%s)" % study_id)
            result = None
        else:
            result.Study = studies[0]

    else:
        return None, 'Study_ID is missing or blank'

    return result, (', '.join(field_errors) if len(field_errors) > 0 else None)

def count_distinct(items_iter):
    """
    Counts number of each distinct values and returns dict of {value: [id1, id2, ...]}
    where item_dict is a dict of {id: value}
    """
    distinct_values = {}
    for key, value in items_iter:
        distinct_values.setdefault(value, []).append(key)
            
    return distinct_values

def validate_list_items(test_list, expected_items, item_name):
    """
    Use set logic to validate that the test list contains exactly the same items as in the expected items list
    with no items missing or duplicated.
    Raises ValidationError 
    """
    if not isinstance(expected_items, set):
        expected_items = set(expected_items)
    test_items = set(test_list)
    missing_items = expected_items - test_items
    if missing_items:
        raise ValidationError("Missing required %ss: %s" % (item_name, ', '.join(missing_items)))
    extra_items = test_items - expected_items
    if extra_items:
        raise ValidationError("Extra %ss not allowed: %s" % (item_name, ', '.join(extra_items)))
    
def process_db_import(request, import_source, dataset):
    """
    Translate the Import_source.Import_data JSON into actual database rows
    """
    
    
    


def load_studies_from_excel(source_file):
    """
    Loads Methods and Results rows from an Excel spreadsheet with the given filename.
    Modifies but doesn't save import_source. Raises ValidationError if anything goes wrong.
    """

    try:
        xls = pd.ExcelFile(source_file)
    except Exception as e:
        raise ValidationError("Error opening Excel spreadsheet. %s: %s" % (type(e).__name__, str(e)))
    try:
        validate_list_items(xls.sheet_names, ['Methods', 'Results'], 'worksheet')
    except ValidationError as e:
        raise ValidationError("Error loading Excel spreadsheet. %s" % str(e))

    meth = pd.read_excel(xls, "Methods")
    res = pd.read_excel(xls, "Results")

    # check for valid/required columns in each spreadsheet
    try:
        validate_list_items(meth.columns, StudiesModel.IMPORT_FIELDS, 'column')
    except ValidationError as e:
        raise ValidationError("Error in Methods worksheet. %s" % str(e))
    
    try:
        validate_list_items(res.columns, ResultsModel.IMPORT_FIELDS, 'column')
    except ValidationError as e:
        raise ValidationError("Error in Results worksheet. %s" % str(e))

    # Parse Methods data
    methods_data = {}
    for row_index, study_row in meth.iterrows():
        study_data = {}
        field_errors = []
        for field, value in study_row.items():
            if field == 'Unique_identifier':
                study_data['Unique_identifier'] = str(value)
                continue
            value, ok = parse_django_field_value(StudiesModel, field, value)
            if not ok:
                field_errors.append('%s: %s' % (field, value))
            else:
                study_data[field] = value

        if field_errors:
            study_data['warnings'] = ', '.join(field_errors)
        methods_data[row_index] = study_data
        
    # validate study Unique_identifier uniqueness
    study_dups = { 
        study_uid: row_ids 
        for study_uid, row_ids in count_distinct((
            # remember row_index is zero-based and we also need to account for the title row
            (str(row_index + 2), row['Unique_identifier'])
            for row_index, row in methods_data.items()
        )).items()
        if len(row_ids) > 1
    }
    if study_dups:
        raise ValidationError([
            "Study Unique_identifier %s is not unique in Methods sheet (rows %s)" % (
                itm, ', '.join(dup_rows)
            )
            for itm, dup_rows in study_dups.items()
        ])

    studies_by_uid = {
        str(row['Unique_identifier']).lower(): row
        for row in methods_data.values()
    }

    # parse Results data and link with methods data
    validation_errors = []
    results_data = {}
    for row_index, res_row in res.iterrows():
        field_errors = []

        res_study = studies_by_uid.get(str(res_row['Study_ID']).lower())
        if not res_study:
            validation_errors.append("Invalid Results row %d: Study with Unique_identifier = '%s' not found." % (
                row_index + 2, res_row['Study_ID']
            ))
            continue

        res_data = {}
        for field, value in res_row.items():
            if field == 'Study_ID':
                res_data['Study_ID'] = value
                continue

            if field == 'Point_estimate':
                try:
                    value = "%0.2f" % float(value)
                except ValueError:
                    pass
            
            value, ok = parse_django_field_value(ResultsModel, field, value)
            if not ok:
                field_errors.append("%s: %s" % (field, value))
                res_data[field] = None
            else:
                res_data[field] = value
        if field_errors:
            res_data['warnings'] = ', '.join(field_errors)

        results_data[row_index] = res_data
        res_study.setdefault('results', {})[row_index] = res_data
    if validation_errors:
        raise ValidationError(validation_errors)

    ## validate result uniqueness based on some arbitrary data
    #result_dups = {
    #    res_desc: row_ids 
    #    for res_desc, row_ids in count_distinct((
    #        (str(row_index + 2), ' - '.join(( str(row[field]) for field in ResultsModel.IMPORT_FIELDS )))
    #        for row_index, row in results_data.items()
    #    )).items()
    #    if len(row_ids) > 1
    #}
    #if result_dups:
    #    raise ValidationError([
    #        "Duplicate results rows [%s]: %s" % (', '.join(dup_rows), itm)
    #        for itm, dup_rows in result_dups.items()
    #    ])
    
    return methods_data