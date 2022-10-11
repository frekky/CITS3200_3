# Generated by Django 4.1 on 2022-09-09 12:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0006_alter_customer_first_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='name',
            field=models.CharField(choices=[('L', 'Luka'), ('K', 'Kye'), ('A', 'Andre'), ('H', 'Hiroyo'), ('N', 'None')], default='N', max_length=1),
        ),
        migrations.AlterField(
            model_name='customer',
            name='first_name',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MaxValueValidator(150.0)]),
        ),
        migrations.AlterField(
            model_name='studies',
            name='Age_max',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MaxValueValidator(150.0)]),
        ),
        migrations.AlterField(
            model_name='studies',
            name='Age_min',
            field=models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MaxValueValidator(150.0)]),
        ),
    ]