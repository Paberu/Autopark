import string
from random import random, sample, choice

from django.core.management import BaseCommand, CommandError, CommandParser
from django.contrib.gis.geos import Point

from park.models import Enterprise, Model, Manufacturer, Vehicle, Driver, RoutePoint

import requests
import json
from pprint import pprint
from datetime import datetime, timedelta


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
        coord_from = [28.33485326156282, 57.81664162349827]
        coord_to = [28.92072549439952, 57.02270904191284]
        length = options['length']
        speed = options['speed']
        acceleration = options['acceleration']
        start = options['start']

        url = "https://graphhopper.com/api/1/route"

        query = {
          "key": "22e6c1f4-4d04-4492-bb0b-c4febde829a3"
        }

        payload = {
          "points": [
              coord_from,
              coord_to
          ],
          # "point_hints": [
          #   "Lindenschmitstraße",
          #   "Thalkirchener Str."
          # ],
          # "snap_preventions": [
          #   "motorway",
          #   "ferry",
          #   "tunnel"
          # ],
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
        # pprint(coordinates)
        # pprint(times)

        vehicle = Vehicle.objects.get(pk=vehicle_id)

        start_dt = datetime.fromisoformat(start)
        route_time = data['paths'][0]['time']
        end_dt = start_dt + timedelta(seconds=int(route_time/1000))

        print(start_dt, end_dt)

        null_point = RoutePoint.objects.create(
            vehicle=vehicle, datetime=start_dt, point=Point(coord_from)
        )
        null_point.save()
        self.stdout.write(self.style.SUCCESS('Begin from: %s!' % null_point))
        # print(null_point)
        previous_point = null_point
        # sum_time_delta = 0

        for point_time in times:
            prev_point_number, current_point_number, time_delta = point_time
            # потом подправить для более умной обработки time-delta меньше 10 секунд
            # if time_delta < 10000 and sum_time_delta < 10000:  # 10 секунд
            #     sum_time_delta += time_delta
            #     continue
            # elif time_delta < 10000 and sum_time_delta >= 10000:
            #     current_coordinates = coordinates[current_point_number]
            #     current_dt = previous_point.datetime + timedelta(seconds=int(sum_time_delta / 1000))
            # else:
            #     current_coordinates = coordinates[current_point_number]
            #     current_dt = previous_point.datetime + timedelta(seconds=int(time_delta/1000))
            current_coordinates = coordinates[current_point_number]
            current_dt = previous_point.datetime + timedelta(seconds=int(time_delta/1000))

            current_point = RoutePoint.objects.create(
                vehicle=vehicle,
                datetime=current_dt,
                point=Point(current_coordinates)
            )
            # print(current_point)
            current_point.save()
            self.stdout.write(self.style.SUCCESS('Next point: %s!' % current_point))
            previous_point = current_point
