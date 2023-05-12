from database.admin_site import admin_site # Custom admin site
from django.contrib.auth.models import Group


from . import admin
from . import base
from . import methods
from . import results
from . import importer
# Hide the groups from the admin site
admin_site.unregister(Group)
