import pytz
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now

from django.contrib.gis.db import models as geo_models


class Manufacturer(models.Model):
    title = models.CharField(max_length=70, help_text='Название производителя', unique=True,
                             verbose_name='Название производителя')

    class Meta:
        ordering = ['title']
        verbose_name = 'Производитель'
        verbose_name_plural = 'Производители'

    def display_title(self):
        return self.title

    def __str__(self):
        return self.title


class Model(models.Model):
    title = models.CharField(max_length=70, help_text='Модель автомобиля', unique=True,
                             verbose_name='Модель автомобиля')
    body_type = models.CharField(max_length=70, help_text='Тип кузова', unique=True,
                                 verbose_name='Тип кузова', null=True)
    power = models.IntegerField(validators=[MinValueValidator(25)], verbose_name='Мощность',
                                help_text='В лошадиных силах', null=True)
    passengers = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(70)],
                                     help_text='Количество пассажиров', verbose_name='Вместимость', null=True)
    fuel_tank = models.DecimalField(max_digits=5, decimal_places=2, help_text='Объем топливного бака',
                                    verbose_name='Объем бака', null=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Модель автомобиля'
        verbose_name_plural = 'Модели автомобиля'

    def display_title(self):
        return self.title

    def __str__(self):
        return self.title


class Enterprise(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название предприятия')
    city = models.CharField(max_length=40, verbose_name='Город')
    country = models.CharField(max_length=40, verbose_name='Страна')

    TIMEZONES = tuple(zip(pytz.all_timezones, pytz.all_timezones))

    timezone = models.CharField(choices=TIMEZONES, max_length=32, default='UTC',
                                verbose_name='Часовой пояс предприятия')

    class Meta:
        ordering = ['name']
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.city)

    def get_absolute_url(self):
        return reverse('enterprise', args=[self.id])

    def get_timezone(self):
        return self.timezone


class Vehicle(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, null=True, related_name='vehicles',
                                     verbose_name='Производитель')
    model = models.ForeignKey(Model, on_delete=models.CASCADE, null=True,  related_name='vehicles',
                              verbose_name='Модель')
    cost = models.IntegerField(validators=[MinValueValidator(10000)],
                               verbose_name='Стоимость',
                               help_text='В рублях')
    odometer = models.IntegerField(validators=[MinValueValidator(0)],
                                   verbose_name='Пробег',
                                   help_text='В километрах')
    year = models.IntegerField(validators=[MinValueValidator(1900), MaxValueValidator(2023)],
                               verbose_name='Год выпуска')
    color = models.CharField(max_length=30, verbose_name='Цвет кузова')
    number_plate = models.CharField(max_length=10, verbose_name='Гос.номер')
    enterprise = models.ForeignKey(Enterprise, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='vehicles', verbose_name='Компания')
    active_driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name='"Активный" водитель')
    buy_datetime = models.DateTimeField(verbose_name='Дата и время покупки', default=now)

    class Meta:
        ordering = ['cost']
        verbose_name = 'Транспортное средство'
        verbose_name_plural = 'Транспортные средства'

    def display_manufacturer(self):
        return self.manufacturer.title

    def display_model(self):
        return self.model.title

    def __str__(self):
        return '{0} {1} ({2})'.format(self.manufacturer, self.model, self.year)

    def validate_active_driver(self):
        if self.active_driver:
            raise ValidationError('У данного транспортного средства есть активный водитель')

    def get_absolute_url(self):
        return reverse('vehicle', args=[self.id])


class Driver(models.Model):
    first_name = models.CharField(max_length=80, verbose_name='Имя')
    last_name = models.CharField(max_length=80, verbose_name='Фамилия')
    age = models.IntegerField(validators=[MinValueValidator(18), MaxValueValidator(80)], verbose_name='Возраст')
    salary = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Зарплата')
    enterprise = models.ForeignKey(Enterprise, on_delete=models.SET_NULL, null=True, blank=True, related_name='drivers',
                                   verbose_name='Компания')
    car = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='drivers',
                            verbose_name='Транспортное средство')

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Водитель'
        verbose_name_plural = 'Водители'

    def __str__(self):
        return '{0} {1}'.format(self.first_name, self.last_name)


class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    enterprise = models.ManyToManyField(Enterprise, blank=True)

    class Meta:
        ordering = ['user']
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'

    def __str__(self):
        return self.user.username


class RoutePoint(geo_models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=False, blank=False,
                                related_name='routepoints', verbose_name='Транспортное средство')
    point = geo_models.PointField(verbose_name='Точка на карте')
    datetime = models.DateTimeField(verbose_name='Время прохождения точки маршрута')

    class Meta:
        ordering = ['vehicle']
        verbose_name = 'Точка маршрута'
        verbose_name_plural = 'Точки маршрута'

    def __str__(self):
        return str(self.vehicle_id) + '' + str(self.point)

    def display_vehicle(self):
        return self.vehicle.name
