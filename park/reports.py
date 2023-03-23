from enum import Enum
from django.db.models import Min, Max
from datetime import datetime, timedelta
from pprint import pprint
from geopy.distance import geodesic
from itertools import pairwise
import requests

from .models import Vehicle, Travel, RoutePoint


class Report:

    class ReportType(Enum):
        DAILY = 1
        MONTHLY = 2
        YEARLY = 3

    def __init__(self, report_type, begin_report_dt, finish_report_dt):
        self.type = self.ReportType(report_type)
        self.begin_report_dt = begin_report_dt
        self.finish_report_dt = finish_report_dt


class TrackReport(Report):

    def __init__(self, report_type, begin_report_dt, finish_report_dt):
        super().__init__(report_type, begin_report_dt, finish_report_dt)

    def generate_full_report(self):
        if self.type not in self.ReportType:
            self.stdout.write(self.style.ERROR('Illegal report type was sent. Change to daily.'))
            self.type = self.ReportType.DAILY

        # vehicle_id = Vehicle.objects.get(pk=vehicle_id)

        travels = Travel.objects.filter(
                begin__gt=self.begin_report_dt,
                end__lt=self.finish_report_dt
            )

        vehicles_with_dates = travels.values('vehicle_id').annotate(min_dt=Min('begin'), max_dt=Max('end'))

        route_points = RoutePoint.objects.filter(
            vehicle_id__in=vehicles_with_dates.values('vehicle_id'),
            datetime__gt=vehicles_with_dates.values('min_dt'),
            datetime__lt=vehicles_with_dates.values('max_dt')
        ).order_by('vehicle_id', 'datetime')

        report_data = {}
        for vehicle_with_dates in vehicles_with_dates:
            filtered_route_points = route_points.filter(vehicle_id=vehicle_with_dates['vehicle_id'])

            begining = vehicle_with_dates['min_dt']

            if self.type == self.ReportType.DAILY:
                ending = begining.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            # elif self.type == self.ReportType.WEEKLY:
            #     ending = begining.replace(day=, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                ending = begining.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

            while begining < vehicle_with_dates['max_dt']:
                points_for_period = filtered_route_points.filter(datetime__gt=begining, datetime__lt=ending).\
                    order_by('datetime').values_list('point')
                points_coords = [list(point[0].coords) for point in points_for_period]

                # if len(points_coords) > 1:
                #     url = "https://graphhopper.com/api/1/route"
                #
                #     query = {
                #         "key": "22e6c1f4-4d04-4492-bb0b-c4febde829a3"
                #     }
                #
                #     payload = {
                #         "points": [
                #             points_coords
                #         ],
                #         "vehicle": "car",
                #         "locale": "en",
                #         "instructions": True,
                #         "calc_points": True,
                #         "points_encoded": False
                #     }
                #
                #     headers = {"Content-Type": "application/json"}
                #
                #     response = requests.post(url, json=payload, headers=headers, params=query)
                #     data = response.json()
                #
                #     pprint(data)
                #
                #     begining = ending
                #     ending + timedelta(days=1)
                #
                #     report_data[vehicle_with_dates['vehicle_id']] = [begining, data]

        return report_data


    def generate_report(self, vehicle_id):
        if self.type not in self.ReportType:
            self.stdout.write(self.style.ERROR('Illegal report type was sent. Change to daily.'))
            self.type = self.ReportType.DAILY

        vehicle = Vehicle.objects.get(pk=vehicle_id)
        # print('Got vehicle: {0}!'.format(vehicle))

        travels = Travel.objects.filter(
                vehicle=vehicle,
                begin__gt=self.begin_report_dt,
                end__lt=self.finish_report_dt
            )
        # print('Got travels: {0}!'.format(travels))
        if len(travels) == 0:
            return {}

        vehicle_with_dates = travels.values('vehicle_id').annotate(min_dt=Min('begin'), max_dt=Max('end'))
        # print('Got vehicle with dates: {0}!'.format(vehicle_with_dates))

        route_points = RoutePoint.objects.filter(
            vehicle_id__in=vehicle_with_dates.values('vehicle_id'),
            datetime__gt=vehicle_with_dates.values('min_dt'),
            datetime__lt=vehicle_with_dates.values('max_dt')
        ).order_by('datetime')
        # print('Got route_points: {0}!'.format(route_points))

        report_data = {}
        begining = vehicle_with_dates[0]['min_dt']

        if self.type == self.ReportType.DAILY:
            time_delta = timedelta(days=1)
        elif self.type == self.ReportType.WEEKLY:
            time_delta = timedelta(days=7)
        else:
            time_delta = timedelta(days=30)

        ending = begining.replace(hour=0, minute=0, second=0, microsecond=0) + time_delta
        # print('Begin: ', begining)
        # print('End:', ending)

        while begining < vehicle_with_dates[0]['max_dt']:
            points_for_period = route_points.filter(datetime__gt=begining, datetime__lt=ending).order_by('datetime').\
                values_list('point')

            if len(points_for_period) >= 2:
                report_data[str(datetime.date(begining))] = round(sum(geodesic(point1, point2).km for point1, point2 in pairwise(points_for_period)), 2)
            begining = ending
            ending += timedelta(days=1)

        return report_data
