# Generated by Django 4.1.5 on 2023-01-23 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('park', '0007_rename_enterprises_manager_enterprise'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manager',
            name='enterprise',
            field=models.ManyToManyField(blank=True, null=True, to='park.enterprise'),
        ),
    ]
