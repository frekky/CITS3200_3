from django.contrib import admin
from .admin_views import import_data

class StrepAAdminSite(admin.AdminSite):
	site_header = 'Browse the Strep A Research Literature Database'
	site_title = 'Strep A DB'
	index_title = 'Database contents'

	login_template = 'database/login.html'
	enable_nav_sidebar = False
	final_catch_all_view = False # actually we add this in below, see get_urls()

	def has_permission(self, request):
		# all users have implicit permission to access the admin site (because it is not just for admins)
		# although non-admin users will not be able to simply view anything other than studies/results
		return request.user.is_active #and request.user.can_view_data

	def get_app_list(self, request, app_label=None):
		"""
		Return a sorted list of all the installed apps that have been
		registered in this site.
		"""
		ordering = {
			"Studies": '1',
			"Results": '2',
			"Studies (Draft)": '3',
			"Users": '4',
			"Imported Datasets": '5',
			"User Guide Documents": '6',
		}
		app_dict = self._build_app_dict(request)
		
		# Sort the apps alphabetically.
		app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())

		# Sort the models alphabetically within each app.
		for app in app_list:
			app['models'].sort(key=lambda x: ordering.get(x['name'], x['name']))

		return app_list

	def app_index(self, request, app_label, extra_context=None):
		extra_context = {
			'title': self.site_header,
			**(extra_context or {}),
		}
		return super().app_index(request, app_label, extra_context)

	def get_urls(self):
		from django.urls import path, re_path
		urls = super().get_urls()
		urls += [
			path('import/', self.admin_view(import_data), name='import_data'),
			re_path(r"(?P<url>.*)$", self.admin_view(self.catch_all_view)),
		]
		return urls


admin_site = StrepAAdminSite()
