from django.urls import path, include
from  . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('visitor/', views.visitor, name='visitor'),
    path('edit_profile_page/', views.edit_profile_page, name='edit_profile_page'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    
    # Sign up & email confirmation
    path('signup/', views.signup_create, name='signup'),
	path('signup/next/', views.signup_done, name='signup_done'),
	path('activate/<uidb64>/<token>/', views.activate_confirm, name='activate_confirm'),
 
	# Password change
	path('password_change/', auth_views.PasswordChangeView.as_view(template_name='database/password/password_change.html'), name='password_change'),
	path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='database/password/password_change_done.html'), name='password_change_done'),
	
	# Password reset
	path('reset/', views.password_reset_request, name='password_reset'),
	path('reset/sent/', auth_views.PasswordResetDoneView.as_view(template_name='database/password/password_reset_done.html'), name='password_reset_done'),
	path('reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='database/password/password_reset_change.html'), name='password_reset_confirm'),  
	path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='database/password/password_reset_complete.html'), name='password_reset_complete'),
]
