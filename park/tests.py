# from django.test import TestCase
#
# from park.models import Driver, Vehicle, Manufacturer, Model, Enterprise
#
# # Create your tests here.
# class TestCommand(TestCase):
#
#     @classmethod
#     def setUpTestData(cls):
#         ids=
#         enterprises = []
#         cars = []
#         drivers = []
#         models = list(Model.objects.all())
#         manufacturers = list(Manufacturer.objects.all())
#         num_of_companies = options['enterprise_id'].count()
#
#         for enterprise_id in options['enterprise_ids']:
#             try:
#                 enterprise = Enterprise.objects.get(pk=enterprise_id)
#                 enterprises.append(enterprise)
#             except enterprise.DoesNotExist:
#                 print('Enterprise "%s" does not exist' % enterprise_id)
#
#         # for _ in range(num_of_companies * 10):
#         for _ in range(num_of_companies * 2):
#             car = Vehicle.objects.create(
#                 manufacturer=sample(manufacturers, 1),
#                 model=sample(models, 1),
#                 cost=int(round(random() * 1000) * 10000),
#                 odometer=int(round(random() * 1000000)),
#                 year=int(round(random(), 2) * 50 + 1973),
#                 color=choice('черный', 'желтый', 'красный', 'серый', 'коричневый', 'зелёный'),
#                 number_plate=''.join(choice(string.ascii_uppercase + string.digits) for _ in range(8)),
#                 enterprise=choice(enterprises)
#             )
#             car.save()
#             cars.append(car)
#
#         # for i in range(num_of_companies * 5):
#         for i in range(num_of_companies):
#             driver = Driver.object.create(
#                 first_name=''.join(choice(string.ascii_uppercase) for _ in range(8)),
#                 last_name=''.join(choice(string.ascii_uppercase) for _ in range(10)),
#                 age=int(random.random() * 62) + 18,
#                 salary=int(random.random() * 100000) + 30000,
#                 enterprise=choice(enterprises),
#                 car=choice(choice(enterprises).vehicles) if i % 3 == 0 else None
#             )
#             driver.save()
#             drivers.append(driver)
#
#         for car in cars:
#             if len(car.drivers) > 1:
#                 car.active_driver = choice(car.drivers)
#                 car.save()
