from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator 
from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.utils import quote
from django.utils import timezone

from .users import Users

class Document(models.Model):
    class Meta:
        verbose_name = 'User Guide Document'
    
    title = models.CharField(max_length=100, help_text="Title of download button shown to users on website home screen")
    upload_file = models.FileField(
        upload_to = 'uploads/documents/',
    )
    minimum_access_level = models.CharField(max_length=30, 
        help_text="Only visible to users equal to or above the chosen access level",
        choices=Users._meta.get_field('access_level').choices)

    def __str__(self):
        return self.title
    
class Dataset(models.Model):
    Dataset_name = models.CharField(max_length=30, unique=True)
    Description = models.TextField(blank=True, 
        help_text='Optional description, such as the purpose or scope of the data set')

    @property
    def owner(self):
        return None

    def __str__(self):
        return self.Dataset_name

class ImportSource(models.Model):
    class Meta:
        verbose_name = 'Imported Excel Files'
        verbose_name_plural = 'Imported Excel Files'

    Dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    Source_file = models.FileField(upload_to='uploads/imports/%Y/%m/%d/')
    Original_filename = models.CharField(max_length=255, blank=True)
    Upload_time = models.DateTimeField(null=True, blank=True)
    Import_time = models.DateTimeField(null=True, blank=True)
    Imported_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True)
    Import_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.Original_filename

    @property
    def owner_id(self):
        return self.Imported_by_id

class DataRequest(models.Model):
    class Meta:
        verbose_name = 'Request for addition/correction'
        verbose_name_plural = 'Requests for addition/correction'
    Request_type = models.CharField(max_length=20, choices=(
        ('addition', 'Add a new study'),
        ('correction', 'Make a correction to existing data'),
        ('other', 'Other - please provide details'),
    ))

    First_author = models.CharField(max_length=100, help_text='Please enter the first author of the study')
    Year = models.CharField(max_length=100, verbose_name='Year of study', help_text='Please enter the publication year of the study')
    Journal_link = models.CharField(max_length=300, verbose_name='Link to journal article')
    Details = models.TextField(help_text="Please describe your request", blank=True)

    Created_by = models.ForeignKey(Users, on_delete=models.CASCADE)
    Created_time = models.DateTimeField(auto_now_add=True)
    Updated_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Request for %s by %s on %s' % (
            self.Request_type, str(self.Created_by), timezone.localdate(self.Created_time).strftime('%d/%m/%Y'))

    @property
    def owner_id(self):
        return self.Created_by_id

class FilteredManager(models.Manager):
    filter_args = None
    def __init__(self, filter_args=None, select_related=None):
        self.filter_args = filter_args or {}
        self.select_related = select_related or []
        super().__init__()
    
    def get_queryset(self):
        return super().get_queryset().select_related(*self.select_related).filter(**self.filter_args)
     