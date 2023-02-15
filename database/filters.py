from django.contrib.admin.filters import ListFilter, ChoicesFieldListFilter
from django.contrib.admin.utils import prepare_lookup_value, quote, unquote
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.templatetags import admin_list
from django.utils.safestring import mark_safe 

class HierarchicalFilter(ListFilter):
    """ 
    Filter one or more fields in order of hierarchy, such that a 'parent' field must be filtered in order
    for the 'child' field filter to show up. The child filter only displays the values present in the database
    amongst rows which match the parent filter.
    """
    filter_spec = None # iterable of tuples containing field name and filter class
    template = "admin/hierarchical_filter.html"
    list_separator = ','

    def __init__(self, request, params, model, model_admin):
        self.request = request
        self.params = params
        self.model_admin = model_admin
        self.model = model
        # Note: don't call super().__init__ because it will raise error

        # from django.contrib.admin.filters.FieldListFilter
        self.used_parameters = {}
        for p in self.expected_parameters():
            if p in params:
                value = params.pop(p)
                self.used_parameters[p] = prepare_lookup_value(
                    p, value, self.list_separator
                )

    def has_output(self):
        return True

    def expected_parameters(self):
        params = []
        for field, _filter in self.filter_spec:
            for parm in _filter.expected_parameters():
                params.append(parm)
        return params

    def filters(self):
        # keep track cumulatively of filter params which are "consumed" by filters
        # from highest level to lowest level in hierarchy
        self_and_child_params = self.expected_parameters()
        
        for field, _filter in self.filter_spec:
            filter_applied = False
            for parm in _filter.expected_parameters():
                if parm in self_and_child_params:
                    # remove params from the list as we find them
                    self_and_child_params.remove(parm) 
                if parm self.params:
                    filter_applied = True
                
            yield {
                'html': mark_safe(admin_list.admin_list_filter(self.changelist, _filter)),
                'clear_filter': self.changelist.get_query_string()
            }

    def choices(self, changelist):
        self.changelist = changelist
        return # nothing to return - template uses spec.filters instead
    
    def queryset(self, request, queryset):
        # from django.contrib.admin.filters.FieldListFilter
        try:
            return queryset.filter(**self.used_parameters)
        except (ValueError, ValidationError) as e:
            raise IncorrectLookupParameters(e)

def hierarchical_data_filter_factory(*filter_specs):
    class MyFilter(HierarchicalDataFilter):
        filter_spec = filter_specs
    return MyFilter


class TwoNumbersInRangeFilter(ListFilter):
    """
    Range filter using two numeric fields (ie. Age_min, Age_max) which specify a range, where rows are filtered out
    which do not intersect the filter range.
    """

    pass



class ChoicesMultipleSelectFilter(FieldListFilter):
    """
    Choice-based multiple selection filter where rows are filtered out which do not match ANY of the selected values.
    """
    def __init__(self, field, request, params, model, model_admin, field_path):
        # adapted from django.contrib.admin.filters.ChoicesFieldListFilter 
        self.lookup_kwarg = "%s__exact" % field_path
        self.lookup_kwarg_isnull = "%s__isnull" % field_path
        self.lookup_val = params.get(self.lookup_kwarg)
        self.lookup_val_isnull = params.get(self.lookup_kwarg_isnull)
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def choices(self, changelist):
        self.changelist = changelist
        for lookup, title in self.field.flatchoices:
            # null value title not supported
            if lookup is None:
                continue
            yield {
                'code': lookup,
                'display': title,
            }

    def null_query_string(self):
        return self.changelist.get_query_string({self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg])

    def base_query_string(self):
        return self.changelist.get_query_string(remove=self.expected_parameters())

    
