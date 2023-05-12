from django.contrib import admin
from admin_action_buttons.admin import ActionButtonsMixin
from django.template.loader import render_to_string
from django.utils.html import mark_safe

from database.models import Users

class MyModelAdmin(ActionButtonsMixin, admin.ModelAdmin):
    checkbox_template = None

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Store request hack: from https://stackoverflow.com/questions/727928/django-admin-how-to-access-the-request-object-in-admin-py-for-list-display-met
        self.request = request
        return qs

    @admin.display(description=mark_safe('<input type="checkbox" id="action-toggle">'))
    def action_checkbox(self, obj):
        """
        A list_display column containing a checkbox widget.
        """
        if self.checkbox_template is None:
            return super().action_checkbox(obj)

        return render_to_string(self.checkbox_template, context={
            'ACTION_CHECKBOX_NAME': admin.helpers.ACTION_CHECKBOX_NAME,
            'row': obj,
            'user': self.request.user,
            'model_name': obj._meta.model_name,
        })


class ViewModelAdmin(MyModelAdmin):
    """ Modeladmin with custom permissions based on simplified user access levels """
    perm_view_all = Users.ACCESS_READONLY
    perm_view_owner = Users.ACCESS_CONTRIB

    perm_add = Users.ACCESS_CONTRIB
    perm_edit_all = Users.ACCESS_ADMIN
    perm_edit_owner = Users.ACCESS_CONTRIB

    perm_delete_all = Users.ACCESS_ADMIN
    perm_delete_owner = Users.ACCESS_CONTRIB

    perm_super = Users.ACCESS_SUPER

    def _eval_perm(self, request, perm):
        return perm and request.user.access_level >= perm

    def _eval_owner_perm(self, request, perm, obj=None):
        if self._eval_perm(request, perm):
            if obj is not None:
                return obj.owner_id == request.user.id
            else:
                # permission granted for "generic" case so that the admin site renders actions/buttons correctly
                return True

    def _eval_super(self, request):
        return self.perm_super and request.user.access_level >= self.perm_super

    def has_view_permission(self, request, obj=None):
        return (
            self._eval_super(request)
            or self._eval_perm(request, self.perm_view_all)
            or self._eval_owner_perm(request, self.perm_view_owner, obj)
        )

    def has_add_permission(self, request, obj=None):
        return (
            self._eval_super(request)
            or self._eval_perm(request, self.perm_add)
        )
    
    def has_change_permission(self, request, obj=None):
        return (
            self._eval_super(request)
            or self._eval_perm(request, self.perm_edit_all)
            or self._eval_owner_perm(request, self.perm_edit_owner, obj)
        )

    def has_delete_permission(self, request, obj=None):
        return (
            self._eval_super(request)
            or self._eval_perm(request, self.perm_delete_all)
            or self._eval_owner_perm(request, self.perm_delete_owner, obj)
        )
