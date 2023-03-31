from enum import Enum
from django.db.models import Min, Max
from datetime import datetime, timedelta
from dateutil import relativedelta
from pprint import pprint
from geopy.distance import geodesic
from itertools import pairwise
import requests

from .models import Vehicle, Travel, RoutePoint, Enterprise


class Report:

    class ReportType(Enum):
        DAILY = 0
        MONTHLY = 1
        YEARLY = 2

    def __init__(self, report_type, begin_report_dt, finish_report_dt):
        self.type = self.ReportType(report_type)
        self.begin_report_dt = begin_report_dt
        self.finish_report_dt = finish_report_dt


class TrackReport(Report):

    def __init__(self, report_type, begin_report_dt, finish_report_dt):
        super().__init__(report_type, begin_report_dt, finish_report_dt)

    def generate_full_enterprise_report(self, enterprise_id):

        enterprise = Enterprise.objects.get(pk=enterprise_id)
        vehicles = Vehicle.objects.filter(enterprise=enterprise)

        report_data = {}
        for vehicle in vehicles:
            data = self.generate_report(vehicle.id)
            if data:
                report_data[str(vehicle)] = data

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

        report_data = []
        begining = vehicle_with_dates[0]['min_dt']

        if self.type == self.ReportType.DAILY:
            time_delta = relativedelta.relativedelta(days=1)
            ending = begining.replace(hour=0, minute=0, second=0, microsecond=0) + time_delta
        elif self.type == self.ReportType.MONTHLY:
            time_delta = relativedelta.relativedelta(months=1)
            ending = begining.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + time_delta
        else:
            time_delta = relativedelta.relativedelta(years=1)
            ending = begining.replace(month=0, day=0, hour=0, minute=0, second=0, microsecond=0) + time_delta

        while begining < vehicle_with_dates[0]['max_dt']:
            points_for_period = route_points.filter(datetime__gt=begining, datetime__lt=ending).order_by('datetime').\
                values_list('point')

            if len(points_for_period) >= 2:
                report_data.append([str(begining), str(ending-relativedelta.relativedelta(seconds=1)),
                                    round(sum(geodesic(point1, point2).km for point1, point2 in
                                              pairwise(points_for_period)), 2)])
            begining = ending
            ending += time_delta

        return report_data
