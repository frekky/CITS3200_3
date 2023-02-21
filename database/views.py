from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse

from django.contrib import messages #import for login messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import EmailMessage
from django.contrib import messages #import for login messages

from database.models import Users
from database.forms import CreateUserForm, AccountUpdateForm, StudiesForm #createrform imported from forms.py

# Prevent usage of browser back button
from django.views.decorators.cache import cache_control
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .tokens import account_activation_token
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.query_utils import Q
from django.contrib.auth.tokens import default_token_generator

import logging, time

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'database/home.html')

def get_base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)

@csrf_protect
def signup_create(request):
    if request.user.is_authenticated:
        return redirect('visitor')

    form = CreateUserForm() #createrform imported from forms.py
    if request.method == 'POST':
        form = CreateUserForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            
            try:
                user.save()
                # send activation email
                mail_subject = 'ASAVI Strep A Database: Activate your account'
                activate_url = get_base_url(request) + reverse('activate_confirm', args=[urlsafe_base64_encode(force_bytes(user.pk)), account_activation_token.make_token(user)])
                message = render_to_string('database/acc_active_email.html', {
                    'user': user,
                    'activate_url': activate_url,
                })
                email = EmailMessage(subject=mail_subject, body=message, to=[user.email])
                email.content_subtype = "html"
                email.send()
                return redirect(reverse('signup_done'))
            except Exception as e:
                logger.error('Account activation failed for new user %s: %s: %s' % (email, str(type(e)), str(e)))
                if user.pk:
                    user.delete() # remove half-activated user
                time.sleep(2)
                messages.error(request, 'Error sending account activation email: invalid email address, or an account is already registered with that email address. Please try again or contact the website administrator.' % str(e))
    
    context = {'form': form}
    return render(request, 'database/signup.html', context)

def signup_done(request):
    return render(request, 'database/signup_done.html')

@csrf_protect
# Activate account after receiving email confirmation
def activate_confirm(request, uidb64, token):
    User = get_user_model()
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        
        messages.success(request, f'Thank you for your email confirmation. Now you can login your account.')
        return redirect('login')
    else:
        messages.error(request, f'Activation link is invalid!')
    return redirect('home')

@csrf_protect
def loginPage(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect('visitor')
    else:
        if request.method == 'POST':
            email = request.POST.get('email')
            first_name = request.POST.get('first_name') 
            last_name = request.POST.get('last_name') 
            password = request.POST.get('password')
                                        
            user = authenticate(request, email=email, first_name=first_name, last_name=last_name, password=password)
            
            if user is not None:
                login(request, user)                
                return redirect('admin:database_studies_changelist')
            else:
                messages.info(request, 'Email OR Password is incorrect')
            
    return render(request, 'database/login.html')

# Handling of user logging out
def logoutUser(request):
    logout(request)
    return redirect('login')

# Visitor dashboard
# restrict page view to logged in users

@login_required(login_url='login')
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def visitor(request):
    return render(request, 'database/userprofile.html')

@login_required(login_url='login')
def database_search(request):
    return render(request, 'database/database_search.html')

# Update user profile properties
@login_required(login_url='login')
def edit_profile_page(request):
    context = {}
    if request.POST:
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save() #apply form save function
            new_email = form.cleaned_data['email']
            messages.success(request, f'Your profile has been successfully updated.')
            return redirect('visitor')
    else:
        # display user properties on edit page
        form = AccountUpdateForm(instance=request.user)
    context['form'] = form
    
    return render(request, 'database/edit_profile_page.html', context)

# password reset request
def password_reset_request(request):
    if request.method == 'POST':
        password_form = PasswordResetForm(request.POST)
        if password_form.is_valid():
            data = password_form.cleaned_data['email']
            to_email = list(Users.objects.filter(email=data))
            if len(to_email) > 0:
                for user in to_email:
                    reset_url = get_base_url(request) + reverse('password_reset_confirm', args=[urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)])
                    message = render_to_string('database/password/password_reset_email.html', {
                        'user': user,
                        'reset_url': reset_url,
                      })
                    email = EmailMessage(subject='ASAVI Strep A Database: Password Reset', body=message, to=[user.email])
                    email.content_subtype = "html"
                    try:
                        email.send()
                    except:
                        return HttpResponse('Invalid Header')
                    return redirect('password_reset_done')
            else:
                time.sleep(2)
                messages.error(request, f'Error sending email or no account found with that email address.')
                return redirect('password_reset')
    else:
        password_form = PasswordResetForm()
        
    context = {
        'password_form': password_form
    }
    return render(request, 'database/password/password_reset.html', context)
