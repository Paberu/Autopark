# Generated by Django 4.1.5 on 2023-01-11 15:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('park', '0005_rename_vehicle_driver_car_remove_driver_is_active_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='active_driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='park.driver', verbose_name='"Активный" водитель'),
        ),
        migrations.CreateModel(
            name='Manager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enterprises', models.ManyToManyField(to='park.enterprise')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Менеджер',
                'verbose_name_plural': 'Менеджеры',
                'ordering': ['user'],
            },
        ),
    ]
