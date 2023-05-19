from django.contrib import admin
from admin_action_buttons.admin import ActionButtonsMixin
from django.contrib.auth.admin import UserAdmin
from django.urls import path

from database.actions import download_as_csv
from database.models import Users, ImportSource, Document, DataRequest, Dataset

from .base import ViewModelAdmin

# The Custom Admin user model
@admin.register(Users)
class AccountAdmin(ActionButtonsMixin, UserAdmin):
    list_display = ('email', 'email_verified', 'first_name', 'last_name', 'date_joined', 'access_level',
        'profession', 'institution', 'country')
    fields = ('email', 'email_verified', 'first_name', 'last_name', 'date_joined', 
        'profession', 'institution', 'country', 'access_level', 'Responsible_for_datasets')
    readonly_fields = ('id', 'date_joined')
    actions = [download_as_csv('Export selected accounts to CSV')]
    
    list_filter = []
    search_fields = []
    ordering = ['email']
    exclude = ()
    
    filter_horizontal = ()
    fieldsets = ()
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

@admin.register(Document)
class DocumentAdmin(ActionButtonsMixin, admin.ModelAdmin):
    list_display = ('title', 'upload_file', 'minimum_access_level')

@admin.register(DataRequest)
class RequestAdmin(ViewModelAdmin):
    perm_view_all = Users.ACCESS_ADMIN
    perm_view_owner = Users.ACCESS_READONLY

    perm_add = Users.ACCESS_READONLY
    perm_edit_all = Users.ACCESS_ADMIN
    perm_edit_owner = None

    perm_delete_all = Users.ACCESS_ADMIN
    perm_delete_owner = None

    readonly_fields = ['Created_by', 'Created_time', 'Updated_time']

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not request.user.access_level >= Users.ACCESS_ADMIN:
            for x in ('Request_user', 'Request_time'):
                if x in fields:
                    fields.remove(x)
        return fields

    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.Created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.access_level >= Users.ACCESS_ADMIN:
            return qs
        return qs.filter(Created_by=request.user)

@admin.register(Dataset)
class DatasetAdmin(ViewModelAdmin):
    perm_view_all = Users.ACCESS_ADMIN
    perm_view_owner = None

    perm_add = Users.ACCESS_SUPER
    perm_edit_all = Users.ACCESS_SUPER
    perm_edit_owner = None

    perm_delete_all = Users.ACCESS_SUPER
    perm_delete_owner = None