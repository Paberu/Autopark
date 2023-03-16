import pytz
import geocoder
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers import serialize
from django.db.models import Q, F, Min, Max
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView
from rest_framework import status, exceptions
from rest_framework.parsers import JSONParser

from rest_framework.response import Response
from rest_framework.views import APIView
# from rest_framework_drilldown import DrillDownAPIView

from autopark import settings
from .forms import VehicleForm, EnterpriseForm
from .models import Vehicle, Manager, Enterprise, Driver, RoutePoint, Travel
from .permissions import IsManagerPermission
from .serializers import VehicleSerializer, RoutePointSerializer, GeoRoutePointSerializer, TravelSerializer


class VehicleInfoView(APIView):
    permission_classes = (IsManagerPermission,)
    parser_classes = (JSONParser,)

    def check_permissions(self, request):
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                self.permission_denied(request, message='Error code: 401', code=401)

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request, message='Error code: 403', code=403)

    def get(self, request):
        if request.user.is_superuser:
            vehicles = Vehicle.objects.all()
        elif Manager.objects.filter(user=request.user):
            mngr = Manager.objects.filter(user=request.user)[0]
            enterprises = mngr.enterprise.all()
            vehicles = Vehicle.objects.filter(enterprise__in=enterprises)
        else:
            print('Error in server logic, should have failed on "check_permissions" stage.')
            self.permission_denied(request, message='Error code: 401', code=401)

        page = request.GET.get('page', 1)
        paginator = Paginator(vehicles, 20)
        try:
            vehicles = paginator.page(page)
        except PageNotAnInteger:
            vehicles = paginator.page(1)
        except EmptyPage:
            vehicles = paginator.page(paginator.num_pages)
        serialized_vehicles = VehicleSerializer(instance=vehicles, many=True)
        return Response(serialized_vehicles.data)

    def post(self, request):
        recieved_data = request.data

        if 'id' not in recieved_data:
            raise exceptions.ValidationError(detail='Bad request. Error code: 400', code=400)
        try:
            vehicle = Vehicle.objects.get(pk=recieved_data['id'])
        except Vehicle.DoesNotExist:
            raise exceptions.ValidationError(detail='Bad request. Error code: 400', code=400)

        serializer = VehicleSerializer(vehicle)

        if request.user.is_superuser or (Manager.objects.filter(user=request.user) and request.user.is_staff):
            serializer.update(vehicle, recieved_data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        recieved_data = request.data
        serializer = VehicleSerializer(data=recieved_data)

        if request.user.is_superuser or (Manager.objects.filter(user=request.user) and request.user.is_staff):
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self,request):
        recieved_data = request.data
        if 'id' not in recieved_data:
            raise exceptions.ValidationError(detail='Bad request. Error code: 400', code=400)
        try:
            vehicle = Vehicle.objects.get(pk=recieved_data['id'])
            vehicle.delete()
            return Response(data='Code: 200', status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            raise exceptions.ValidationError(detail='Bad request. Error code: 400', code=400)


@login_required
def management(request):
    # result = set_timezone(request)
    # if result:
    #     return result
    request.session['django_timezone'] = request.COOKIES['django_timezone']

    if request.user.is_superuser:
        enterprises = Enterprise.objects.all()
    elif Manager.objects.filter(user=request.user):
        mngr = Manager.objects.filter(user=request.user)[0]
        enterprises = mngr.enterprise.all()
    else:
        enterprises = []
    context = {'enterprises': enterprises}
    return render(request, 'management.html', context=context)


@login_required
def enterprise(request, id):
    company = get_object_or_404(Enterprise, pk=id)
    vehicles = Vehicle.objects.filter(enterprise=company)
    page = request.GET.get('page', 1)
    paginator = Paginator(vehicles, 20)
    try:
        vehicles = paginator.page(page)
    except PageNotAnInteger:
        vehicles = paginator.page(1)
    except EmptyPage:
        vehicles = paginator.page(paginator.num_pages)
    context = {'vehicles': vehicles}
    return render(request, 'enterprise.html', context=context)


@login_required
def vehicle(request, id):
    context = {'message': 'Если Вы это читаете, что-то пошло не так'}
    if request.method == 'GET':
        vehicle = get_object_or_404(Vehicle, pk=id)
        vehicle_values = {}
        vehicle_values['manufacturer'] = vehicle.manufacturer
        vehicle_values['model'] = vehicle.model
        vehicle_values['cost'] = vehicle.cost
        vehicle_values['odometer'] = vehicle.odometer
        vehicle_values['year'] = vehicle.year
        vehicle_values['color'] = vehicle.color
        vehicle_values['number_plate'] = vehicle.number_plate
        vehicle_values['enterprise'] = vehicle.enterprise
        vehicle_values['active_driver'] = vehicle.active_driver
        vehicle_values['buy_datetime'] = vehicle.buy_datetime

        # print(vehicle_values)
        # ent_tz = pytz.timezone(vehicle.enterprise.timezone)
        # vehicle.buy_datetime = vehicle.buy_datetime.astimezone(ent_tz)
        # vehicle_values['buy_datetime'] = str(vehicle.buy_datetime)[:19]
        # print(str(vehicle.buy_datetime)[:19])

        form = VehicleForm(initial=vehicle_values)
        print(form)
        if request.user.is_superuser:
            enterprises = Enterprise.objects.all()
        elif Manager.objects.filter(user=request.user):
            mngr = Manager.objects.filter(user=request.user)[0]
            enterprises = mngr.enterprise.all()
        else:
            raise Http404()
        drivers = Driver.objects.filter(vehicle=vehicle)
        context = {'vehicle': vehicle, 'enterprises': enterprises, 'drivers': drivers, 'form': form}
    if request.method == 'POST':
        vehicle = get_object_or_404(Vehicle, pk=id)
        vehicle_form = VehicleForm(request.POST)
        if vehicle_form.is_valid():
            print(vehicle_form.data['manufacturer'])
            vehicle.manufacturer = vehicle_form.cleaned_data.get('manufacturer', vehicle.manufacturer)
            vehicle.model = vehicle_form.cleaned_data.get('model', vehicle.model)
            vehicle.cost = vehicle_form.cleaned_data.get('cost', vehicle.cost)
            vehicle.odometer = vehicle_form.cleaned_data.get('odometer', vehicle.odometer)
            vehicle.year = vehicle_form.cleaned_data.get('year', vehicle.year)
            vehicle.color = vehicle_form.cleaned_data.get('color', vehicle.color)
            vehicle.number_plate = vehicle_form.cleaned_data.get('number_plate', vehicle.number_plate)
            vehicle.enterprise = vehicle_form.cleaned_data.get('enterprise', vehicle.enterprise)
            vehicle.active_driver = vehicle_form.cleaned_data.get('active_driver', vehicle.active_driver)
            vehicle.buy_datetime = vehicle_form.cleaned_data.get('buy_datetime', vehicle.buy_datetime)
            vehicle.save()
            context = {'message': 'Транспортное средство ' + str(vehicle) + ' исправлено.'}
    return render(request, 'vehicle.html', context=context)


@login_required
def create_vehicle(request):
    if request.method == 'POST':
        vehicle_form = VehicleForm(request.POST)
        print(vehicle_form)
        if vehicle_form.is_valid():
            vehicle = Vehicle.objects.create(**vehicle_form.cleaned_data)
            vehicle.save()
            context = {'message': 'Транспортное средство ' + str(vehicle) + ' создано.'}
    else:
        if request.user.is_superuser:
            enterprises = Enterprise.objects.all()
        elif Manager.objects.filter(user=request.user):
            mngr = Manager.objects.filter(user=request.user)[0]
            enterprises = mngr.enterprise.all()
        else:
            raise Http404()
        vehicle_form = VehicleForm()
        context = {'enterprises': enterprises, 'form': vehicle_form}
    return render(request, 'vehicle.html', context=context)


@login_required
def delete_vehicle(request, id):
    if request.method == 'GET':
        vehicle = get_object_or_404(Vehicle, pk=id)
        vehicle.delete()
        context = {'message': 'Траспортное средство '+str(vehicle)+' удалено.'}
    return render(request, 'vehicle.html', context=context)


def set_timezone(request):
    if request.method == 'POST':
        request.session['django_timezone'] = request.COOKIES['django_timezone']
    else:
        return render(request, 'timezone.html', {'timezones': tuple(zip(pytz.common_timezones, pytz.common_timezones))})


class RoutePointsInfoView(APIView):
    permission_classes = (IsManagerPermission,)
    parser_classes = (JSONParser, )

    # def check_permissions(self, request):
    #     for permission in self.get_permissions():
    #         if not permission.has_permission(request, self):
    #             self.permission_denied(request, message='Error code: 401', code=401)
    #
    # def check_object_permissions(self, request, obj):
    #     for permission in self.get_permissions():
    #         if not permission.has_object_permission(request, self, obj):
    #             self.permission_denied(request, message='Error code: 403', code=403)


    def get(self, request):
        vehicle = get_object_or_404(Vehicle, pk=request.GET['id'])
        ent_tz = pytz.timezone(vehicle.enterprise.timezone)
        start_date = datetime.fromisoformat(request.GET['start'])
        end_date = datetime.fromisoformat(request.GET['end'])
        geojs = request.GET.get('geojson', False)

        if request.user.is_superuser or Manager.objects.filter(user=request.user):
            route_points = RoutePoint.objects.filter(
                Q(vehicle=vehicle) &
                Q(datetime__gt=start_date) &
                Q(datetime__lt=end_date)
            )
        else:
            print('Error in server logic, should have failed on "check_permissions" stage.')
            self.permission_denied(request, message='Error code: 401', code=401)

        # page = request.GET.get('page', 1)
        # paginator = Paginator(route_points, 20)
        # try:
        #     route_points = paginator.page(page)
        # except PageNotAnInteger:
        #     route_points = paginator.page(1)
        # except EmptyPage:
        #     route_points = paginator.page(paginator.num_pages)

        if not geojs:
            serialized_route_points = RoutePointSerializer(instance=route_points, many=True)
            # serialized_route_points = serialize('json', route_points,  fields=('point', 'datetime'))
        else:
            # serialized_route_points = serialize('geojson', route_points, geometry_field='point',
            #                                     fields=('point', 'datetime'))
            serialized_route_points = GeoRoutePointSerializer(instance=route_points, many=True)

        return Response(serialized_route_points.data)


class TravelInfoView(APIView):
    # permission_classes = (IsManagerPermission,)
    parser_classes = (JSONParser,)

    # def get(self, request):
    #     start_date = datetime.fromisoformat(request.GET['start'])
    #     end_date = datetime.fromisoformat(request.GET['end'])
    #     # route_points = RoutePoint.objects.filter(
    #     #     vehicle__travels__begin__lt=F('datetime'),
    #     #     vehicle__travels__end__gt=F('datetime')
    #     # )
    #     travels = Travel.objects.filter(
    #         Q(begin__gt=start_date) &
    #         Q(end__lt=end_date)
    #     )
    #
    #     vehicles_with_dates = travels.values('vehicle_id').annotate(min_dt=Min('begin'), max_dt=Max('end'))
    #     route_points = RoutePoint.objects.filter(
    #         vehicle_id__in=vehicles_with_dates.values('vehicle_id'),
    #         datetime__gt=vehicles_with_dates.values('min_dt'),
    #         datetime__lt=vehicles_with_dates.values('max_dt')
    #     )
    #
    #     #
    #     # serialized_travels = TravelSerializer(instance=travels, many=True)
    #     # return Response(serialized_travels.data)
    #     #
    #     # print(route_points)
    #     serialized_route_points = RoutePointSerializer(instance=route_points, many=True)
    #     return Response(serialized_route_points.data)

    def get(self, request):
        start_date = datetime.fromisoformat(request.GET['start'])
        end_date = datetime.fromisoformat(request.GET['end'])
        travels = Travel.objects.filter(
                Q(begin__gt=start_date) &
                Q(end__lt=end_date)
            )

        # for travel in travels:
        vehicles_with_dates = travels.values('vehicle_id').annotate(min_dt=Min('begin'), max_dt=Max('end'))

        route_points = RoutePoint.objects.filter(
                vehicle_id__in=vehicles_with_dates.values('vehicle_id'),
                datetime__gt=vehicles_with_dates.values('min_dt'),
                datetime__lt=vehicles_with_dates.values('max_dt')
            )

        for route_point in route_points:
            reversed_route_point = geocoder.geocodefarm(list(reversed(route_point.point.coords)), method='reverse')

        serialized_route_points = RoutePointSerializer(instance=route_points, many=True)
        return Response(serialized_route_points.data)


# class EnterpriseList(DrillDownAPIView):
#     # model = Enterprise
#     # drilldowns = ['vehicles__routepoints', ]
#
#     def get_base_query(self):
#         # Base query for your class, typically just '.objects.all()'
#         return Enterprise.objects.all()

@login_required
def enterprises(request):
    if request.user.is_superuser:
        companies = Enterprise.objects.all()
    elif Manager.objects.filter(user=request.user):
        mngr = Manager.objects.get(user=request.user)
        companies = mngr.enterprise.all()
    else:
        raise Http404()
    form = EnterpriseForm()
    context = {'companies': companies, 'form': form}
    # if request.method == 'GET':
    # initial_values = {}
    # initial_values['enterprises'] = companies
    # form = EnterpriseForm(initial=initial_values)
    # context = {'companies': companies, 'form': form}

    if request.method == 'POST':
        if request.POST.get('company') :
            company_id = int(request.POST['company'][1:-1])
            company = get_object_or_404(Enterprise, pk=company_id)
            context['company'] = company

            vehicles = Vehicle.objects.filter(enterprise=company)
            context['vehicles'] = vehicles
        else:
            raise Http404()

        if request.POST.get('vehicle'):
            vehicle_id = int(request.POST['vehicle'][1:-1])
            if vehicle_id:
                vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
                context['vehicle'] = vehicle

                travels = Travel.objects.filter(vehicle=vehicle)
                context['travels'] = travels

        if request.POST.get('travel'):
            travel_id = int(request.POST['travel'][1:-1])
            if travel_id:
                travel = get_object_or_404(Travel, pk=travel_id)
                context['travel'] = travel

                route_points = RoutePoint.objects.filter(
                    vehicle=vehicle,
                    datetime__gt=travel.begin,
                    datetime__lt=travel.end
                )

                reversed_route_points = []
                for route_point in route_points:
                    reversed_route_point = geocoder.geocodefarm(list(reversed(route_point.point.coords)),
                                                                method='reverse')
                    # print(reversed_route_point.location)
                    # print(reversed_route_point.country, reversed_route_point.city, reversed_route_point.street, reversed_route_point.housenumber,)
                    # print(dir(reversed_route_point))
                    reversed_route_points.append(reversed_route_point)

                context['route_points'] = reversed_route_points

                route_line = []
                for route_point in route_points:
                    route_line.append(list(reversed(route_point.point.coords)))

                context['route_line'] = route_line
    return render(request, 'enterprises.html', context=context)
