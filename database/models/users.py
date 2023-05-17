from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.utils import quote
from django.utils import timezone
from django.utils.safestring import mark_safe

class CustomAccountManager(BaseUserManager):
    
    def create_superuser(self, email, first_name, last_name, password, **other_fields):
        other_fields['access_level'] = '40_superuser'
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, 
                          **other_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user

    def create_user(self, email, first_name, last_name, password, **other_fields):
        
        if not email:
            raise ValueError(_('You must provide an email address'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name,
                          **other_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user
             
class Users(AbstractBaseUser):
    class Meta:
        verbose_name_plural = 'Users'

    ACCESS_DISABLED = '00_disabled'
    ACCESS_READONLY = '10_readonly'
    ACCESS_CONTRIB = '20_contributor'
    ACCESS_ADMIN = '30_administrator'
    ACCESS_SUPER = '40_superuser'
    
    email = models.EmailField(_('email'), max_length=100, unique=True)
    email_verified = models.BooleanField(default=True, blank=False, help_text=_('True if the user has verified their email address.'))
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    profession = models.CharField(max_length=50, blank=False, default='')
    institution = models.CharField(max_length=50, blank=False, default='')
    country = models.CharField(max_length=50, blank=False, default='')
    access_level = models.CharField(max_length=30, blank=False, null=False, default='readonly',
        choices=(
            (ACCESS_DISABLED, 'Disabled'),
            (ACCESS_READONLY, 'Read-only'),
            (ACCESS_CONTRIB, 'Contributor'),
            (ACCESS_ADMIN, 'Administrator'),
            (ACCESS_SUPER, 'Superuser'),
        ),
        help_text=mark_safe(_(
        """<b>User level of access to the Online Database system.</b>
        <ul>
        <li>Disabled users cannot login or reset their passwords.</li>
        <li>Read-only users (default) have read-only access to 'approved' studies and results including search & filter functionality.</li>
        <li>Contributors can add studies/results online, or via Excel import, and can manage their own contributions.</li>
        <li>Administrators can add, edit, approve or delete any studies or results in the database.</li>
        <li>Superusers have the same access as Administrators, but can also view, add, edit and delete users.
        Superusers can change other user levels of access including promoting other users to Superusers.</li>
        </ul>
        """)))

    objects = CustomAccountManager()

    Responsible_for_datasets = models.ManyToManyField('Dataset', related_name='datasets')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    @property
    def is_active(self):
        return self.access_level > self.ACCESS_DISABLED and self.email_verified
    
    def __str__(self):
        return '%s %s <%s>' % (self.first_name, self.last_name, self.email)
    
    def has_perm(self, perm, obj=None):
        if self.access_level >= self.ACCESS_SUPER:
            return True
    
    def has_module_perms(self, app_label):
        return True
