from django.contrib.admin.filters import (
    ListFilter, ChoicesFieldListFilter, AllValuesFieldListFilter,
    FieldListFilter)
from django.contrib.admin.utils import prepare_lookup_value, quote, unquote
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.templatetags import admin_list
from django.utils.safestring import mark_safe 
from django.core.exceptions import ValidationError

class MyListFilter(ListFilter):
    field_spec = None
    title = None
    list_separator = ','

    def __init__(self, request, params, model, model_admin):
        self.request = request
        self.params = params
        self.model_admin = model_admin
        self.model = model
        # Note: don't call super().__init__ because it will raise error

        # from django.contrib.admin.filters.FieldListFilter
        # load the filter data from the query string params
        self.used_parameters = {}
        for p in self.expected_parameters():
            if p in params:
                value = params.pop(p)
                self.used_parameters[p] = prepare_lookup_value(
                    p, value, self.list_separator
                )
    
    def has_output(self):
        return True

    def choices(self, changelist):
        self.changelist = changelist
        return [] # nothing to return - template uses spec.filters instead

    def base_query_string(self):
        return self.changelist.get_query_string(remove=self.expected_parameters())
    
    @classmethod
    def create(cls, title, field_spec):
        """ return filter class for ModelAdmin's list_filter with field spec provided """
        return type(cls.__name__, (cls, ), {
            'title': title,
            'field_spec': field_spec,
        })

class HierarchicalFilter(MyListFilter):
    """ 
    Single or multiple select filters from 'top level' to 'bottom level' ie for fields
    which contain dependent or redundant data (eg. broad category -> specific category).
    Records with null values in specified fields will not appear except when this 
    filter is unset.
    """
    field_spec = None
    template = "admin/hierarchical_filter.html"

    def expected_parameters(self):
        return [ field for field, _ in self.field_spec ]

    def filters(self):
        # keep track cumulatively of filter params which are "consumed" by filters
        # from highest level to lowest level in hierarchy
        self_and_child_params = self.expected_parameters()
        
        for field, _filter in self.field_spec:
            pass
            #filter_applied = False
            #for parm in _filter.expected_parameters():
            #    if parm in self_and_child_params:
            #        # remove params from the list as we find them
            #        self_and_child_params.remove(parm) 
            #    if parm self.params:
            #        filter_applied = True
            #    
            #yield {
            #    'html': mark_safe(admin_list.admin_list_filter(self.changelist, _filter)),
            #    'clear_filter': self.changelist.get_query_string()
            #}

    
    def queryset(self, request, queryset):
        # from django.contrib.admin.filters.FieldListFilter
        try:
            return queryset.filter(**self.used_parameters)
        except (ValueError, ValidationError) as e:
            raise IncorrectLookupParameters(e)

class HierarchicalFilterFilter:
    pass

class HierarchicalSingleFilter(HierarchicalFilterFilter):
    pass

class HierarchicalMultipleFilter(HierarchicalFilterFilter):
    pass

class TwoNumbersInRangeFilter(MyListFilter):
    """
    Range filter using two numeric fields (ie. Age_min, Age_max) which specify a
    range, where rows are filtered out which do not intersect the filter range.
    Adapted in parts from rangefilter.NumericRangeFilter
    (https://github.com/Danycraft98/django-rangefilter under MIT license)
    """
    field_spec = None # must be tuple (field_gte, field_lte)
    field_name_gte = None
    field_name_lte = None
    template = "admin/numeric_range_filter.html"

    def __init__(self, request, params, model, model_admin):
        self.field_name_gte, self.field_name_lte = self.field_spec
        self.lookup_kwarg_gte = "%s__range__gte" % self.field_name_gte
        self.lookup_kwarg_lte = "%s__range__lte" % self.field_name_lte
        super().__init__(request, params, model, model_admin)
        self.lookup_val_gte = self.used_parameters.get(self.lookup_kwarg_gte)
        self.lookup_val_lte = self.used_parameters.get(self.lookup_kwarg_lte)

    def expected_parameters(self):
        return [self.lookup_kwarg_gte, self.lookup_kwarg_lte]

    def queryset(self, request, queryset):
        filter_args = {}
        if self.lookup_val_gte is not None:
            filter_args['%s__gte' % self.field_name_gte] = self.lookup_val_gte
        if self.lookup_val_lte is not None:
            filter_args['%s__lte' % self.field_name_lte] = self.lookup_val_lte
        return queryset.filter(**filter_args)

class ChoicesMultipleSelectFilter(FieldListFilter):
    """
    Choice-based multiple selection filter where rows are filtered out which
    do not match ANY of the selected values.
    """
    template = 'admin/multiple_filter.html'
    def __init__(self, field, request, params, model, model_admin, field_path):
        # adapted from django.contrib.admin.filters.ChoicesFieldListFilter 
        self.lookup_kwarg = "%s__in" % field_path
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
                'code': quote(lookup),
                'display': title,
            }

    def queryset(self, request, queryset):
        try:
            if self.lookup_kwarg in self.used_parameters:
                filter_selection = [
                    unquote(item) for item in self.used_parameters[self.lookup_kwarg]
                ]
                queryset = queryset.filter(**{self.lookup_kwarg: filter_selection})
            if self.lookup_kwarg_isnull in self.used_parameters:
                queryset = queryset.filter(**{self.lookup_kwarg_isnull: self.used_parameters[self.lookup_kwarg_isnull]})
            return queryset
        except (ValueError, ValidationError) as e:
            # Fields may raise a ValueError or ValidationError when converting
            # the parameters to the correct type.
            raise IncorrectLookupParameters(e)

    def null_query_string(self):
        return self.changelist.get_query_string({self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg])

    def base_query_string(self):
        return self.changelist.get_query_string(remove=self.expected_parameters())

    @property
    def selected(self):
        selected_items = self.used_parameters.get(self.lookup_kwarg)
        isnull = self.used_parameters.get(self.lookup_kwarg_isnull)

        if isnull:
            return set()

        sel_actual = set()
        for lookup, title in self.field.flatchoices:
            if lookup is None:
                continue
            lookup = quote(lookup)
            if selected_items is None or lookup in selected_items:
                sel_actual.add(lookup)
        return sel_actual
