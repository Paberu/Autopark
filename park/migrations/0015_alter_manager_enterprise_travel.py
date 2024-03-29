# Generated by Django 4.1.7 on 2023-03-09 03:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('park', '0014_routepoint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manager',
            name='enterprise',
            field=models.ManyToManyField(blank=True, to='park.enterprise'),
        ),
        migrations.CreateModel(
            name='Travel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('begin', models.DateTimeField(verbose_name='Начало поездки')),
                ('end', models.DateTimeField(verbose_name='Окончание поездки')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='travels', to='park.vehicle', verbose_name='Автомобиль, на котором произошла поездка')),
            ],
        ),
    ]
