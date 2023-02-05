import string
from random import random, sample, choice

from django.core.management import BaseCommand, CommandError, CommandParser

from park.models import Enterprise, Model, Manufacturer, Vehicle, Driver


class Command(BaseCommand):
    help = 'Generates vehicles and drivers for company/companies.'

    def add_arguments(self, parser):
        parser.add_argument('enterprise_id', nargs='+', type=int)

        # Optional arguments
        parser.add_argument('--car-number', type=int, help='Number of cars.')
        parser.add_argument('--driver-number', type=int, help='Number of drivers.')

    def handle(self, *args, **options):
        # enterprises = []
        # num_of_companies = len(options['enterprise_id'])
        print(options.keys())
        car_number = options['car_number']
        driver_number = options['driver_number']

        for enterprise_id in options['enterprise_id']:
            try:
                enterprise = Enterprise.objects.get(pk=enterprise_id)
                cars = []
                drivers = []

                for _ in range(car_number):
                    car = Vehicle.objects.create(
                        manufacturer=choice(list(Manufacturer.objects.all())),
                        model=choice(list(Model.objects.all())),
                        cost=int(round(random() * 1000) * 10000),
                        odometer=int(round(random() * 1000000)),
                        year=int(round(random(), 2)*50+1973),
                        color=choice(('черный','желтый','красный','серый','коричневый','зелёный')),
                        number_plate=''.join(choice(string.ascii_uppercase + string.digits) for _ in range(8)),
                        enterprise=enterprise
                    )
                    car.save()
                    cars.append(car)
                    self.stdout.write(self.style.SUCCESS('Car %s created successfully!' % car.number_plate))

                for i in range(driver_number):
                    cars = Vehicle.objects.filter(enterprise=enterprise)
                    driver = Driver.objects.create(
                        first_name=(''.join(choice(string.ascii_lowercase) for _ in range(8))).capitalize(),
                        last_name=(''.join(choice(string.ascii_lowercase) for _ in range(10))).capitalize(),
                        age=int(random()*62)+18,
                        salary=int(random()*100000)+30000,
                        enterprise=enterprise
                    )
                    if i % 10 != 0:
                        driver.car = choice(cars)
                    driver.save()
                    drivers.append(driver)
                    self.stdout.write(self.style.SUCCESS('Driver %s created successfully!' % driver.last_name))

                for car in cars:
                    drivers = Driver.objects.filter(car=car)
                    if len(drivers) > 0:
                        car.active_driver = choice(drivers)
                        car.save()

            except enterprise.DoesNotExist:
                raise CommandError('Enterprise "%s" does not exist' % enterprise_id)