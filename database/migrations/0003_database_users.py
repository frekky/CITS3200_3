# Generated by Django 4.1 on 2022-09-02 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0002_users_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='database_users',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
            ],
        ),
    ]