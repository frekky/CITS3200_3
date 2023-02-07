import csv
import logging
import io

from django.db import transaction
from django.db.models import fields
from django.core.exceptions import FieldDoesNotExist
from database.models import Studies, Results
import decimal

logger = logging.getLogger(__name__)

NULL_VALUES = ('n/a', 'not applicable', 'none', 'not defined', '', 'missing')
TRUE_VALUES = ('t', '1', 'yes', 'y', 'true')
FALSE_VALUES = ('f', '0', 'no', 'n', 'false')

def parse_bool(value):
    if value is None:
        return None

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
        if field.name in ('Created_time', 'Updated_time', 'Approved_time', 'Created_by', 'Approved_by'):
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
            return value, True

        if value.lower() in NULL_VALUES:
            return (None, True)
        elif isinstance(djfield, fields.DecimalField):
            value = float(value)
            if djfield.decimal_places:
                value = round(value, djfield.decimal_places)
            if djfield.max_digits:
                digits = djfield.max_digits - (djfield.decimal_places or 0)
                value = min(value, pow(10, digits) - 1)
        elif isinstance(djfield, (fields.PositiveSmallIntegerField, fields.PositiveIntegerField)):
            value = int(value.replace(',', ''))
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
        id = csv_row.get('Unique_identifier') or csv_row.get('Results_ID') or ''
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
    
def import_csv_studies_row(row, import_source):
    study = Studies(Import_source=import_source, Approved_by=import_source.Imported_by, Approved_time=import_source.Import_time)
    field_errors = []

    for field, value in row.items():

        # skip foreign keys & auto fields
        if field in ('Approved_by', 'Created_by', 'Import_source', 'Approved_time', 'Created_time', 'Updated_time'):
            continue
        
        value, ok = parse_django_field_value(Studies, field, value)
        if not ok:
            field_errors.append('%s: %s' % (field, value))
        else:
            setattr(study, field, value)

    return study, (', '.join(field_errors) if len(field_errors) > 0 else None)

def import_csv_results_row(row, import_source):
    result = Results(Import_source=import_source, Approved_by=import_source.Imported_by, Approved_time=import_source.Import_time)
    field_errors = []

    for field, value in row.items():

        # skip foreign key & auto fields
        if field in ('Results_ID', 'Approved_by', 'Created_by', 'Import_source', 'Approved_time', 'Created_time', 'Updated_time'):
            continue
        
        value, ok = parse_django_field_value(Results, field, value)
        if not ok:
            field_errors.append("%s: %s" % (field, value))
        else:
            setattr(result, field, value)

    # link to related study/methods row based on Unique_identifier = Results_ID
    if 'Results_ID' in row and (study_id := row['Results_ID']):
        # check Unique_identifier first
        studies = list(Studies.objects.filter(Unique_identifier=study_id))
        if len(studies) == 0 and study_id:
            try:
                # nothing found: try searching by database ID instead (ie. for online-submitted studies/results)
                studies = list(Studies.objects.filter(id=study_id))
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
        return None, 'Results_ID is missing or blank'

    return result, (', '.join(field_errors) if len(field_errors) > 0 else None)