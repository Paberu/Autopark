import string
from random import random, sample, choice

from django.core.management import BaseCommand, CommandError, CommandParser
from django.contrib.gis.geos import Point

from park.models import Enterprise, Model, Manufacturer, Vehicle, Driver, RoutePoint, Travel

import requests
import json
from pprint import pprint
from datetime import datetime, timedelta
import geocoder


class Command(BaseCommand):
    help = 'Generates track for vehicle'

    def add_arguments(self, parser):
        parser.add_argument('vehicle_id', nargs='+', type=int)

        # Optional arguments
        parser.add_argument('--length', type=int, help='Length of the track.')
        parser.add_argument('--speed', type=int, help='Max speed of the car.')
        parser.add_argument('--acceleration', type=int, help='Max acceleration of the car.')
        parser.add_argument('--start', type=str, help='Date/time of the beginning of the journey.')

    def handle(self, *args, **options):
        vehicle_id = options['vehicle_id'][0]
        vehicle = Vehicle.objects.get(pk=vehicle_id)

        coord_from_list = [
            [28.332460, 57.819274],
            [27.609352, 57.813756],
            [30.515671, 56.343703],
            [28.916437, 57.021432],
            [27.819594, 58.744398],
            [28.484823, 56.277403]
        ]
        coord_to_list = [
            [65.541227, 57.152985],
            [60.597474, 56.838011],
            [39.200296, 51.660781],
            [32.045287, 54.782635],
            [38.975313, 45.035470],
            [48.030178, 46.347614]
        ]
        # coord_from = [28.33485326156282, 57.81664162349827]
        # coord_to = [60.902996, 58.232520]
        coord_from = choice(coord_from_list)
        coord_to = choice(coord_to_list)
        length = options['length']
        speed = options['speed']
        acceleration = options['acceleration']
        start = options['start']
        forward = True  # из какого списка выбирать пункт назначения

        start_dt = datetime.fromisoformat(start)
        end_dt = start_dt
        url = "https://graphhopper.com/api/1/route"

        query = {
          "key": "22e6c1f4-4d04-4492-bb0b-c4febde829a3"
        }

        while end_dt < datetime.fromisoformat('2023-03-21 21:00:00+03:00'):
            # print('From {0} to {1} begins {2}, Forward = {3}'.format(
            #     geocoder.yandex(coord_from, apikey='e85c72cb-b9ca-4887-838f-b0cf38d74df9', method='reverse', sco='latlong'),
            #     geocoder.yandex(coord_to, apikey='e85c72cb-b9ca-4887-838f-b0cf38d74df9', method='reverse',  sco='latlong'),
            #     start_dt, forward))

            # print('From {0} to {1} begins {2}, Forward = {3}'.format(coord_from, coord_to, start_dt, forward))

            payload = {
              "points": [
                  coord_from,
                  coord_to
              ],
              "details": [
                "road_class",
                "surface",
                'time',
              ],
              "vehicle": "car",
              "locale": "en",
              "instructions": True,
              "calc_points": True,
              "points_encoded": False
            }

            headers = {"Content-Type": "application/json"}

            response = requests.post(url, json=payload, headers=headers, params=query)

            data = response.json()
            coordinates = data['paths'][0]['points']['coordinates']
            times = data['paths'][0]['details']['time']

            route_time = data['paths'][0]['time']
            end_dt = start_dt + timedelta(seconds=int(route_time / 1000))

            null_point = RoutePoint.objects.create(
                vehicle=vehicle, datetime=start_dt, point=Point(coord_from)
            )
            null_point.save()
            previous_point = null_point

            time_buffer = 0
            for point_time in times:
                prev_point_number, current_point_number, time_delta = point_time
                if time_delta + time_buffer < 30000:  # 30 секунд
                    time_buffer += time_delta
                    continue
                else:
                    time_delta += time_buffer
                    time_buffer = 0
                current_coordinates = coordinates[current_point_number]
                current_dt = previous_point.datetime + timedelta(seconds=int(time_delta/1000))

                current_point = RoutePoint.objects.create(
                    vehicle=vehicle,
                    datetime=current_dt,
                    point=Point(current_coordinates)
                )
                current_point.save()
                previous_point = current_point

            travel = Travel.objects.create(
                vehicle=vehicle,
                begin=start_dt,
                end=end_dt
            )
            travel.save()

            start_dt = end_dt + timedelta(hours=12)  # перерыв между поездками 12 часов
            forward = not forward  # едем обратно
            coord_from = coord_to
            if forward:
                coord_to = choice(coord_to_list)
            else:
                coord_to = choice(coord_from_list)


