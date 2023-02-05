import pytz
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView
from rest_framework import status, exceptions
from rest_framework.parsers import JSONParser

from rest_framework.response import Response
from rest_framework.views import APIView

from autopark import settings
from .forms import VehicleForm
from .models import Vehicle, Manager, Enterprise, Driver
from .permissions import IsManagerPermission
from .serializers import VehicleSerializer


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
        print(vehicles)
        # for car in vehicles:
        #     print(car)
        #     print(car.buy_datetime)
        #     print(car.enterprise.timezone)
        #     ent_tz = pytz.timezone(car.enterprise.timezone)
        #     car.buy_datetime = car.buy_datetime.astimezone(ent_tz)
        #     print(car.buy_datetime)
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

        # print(vehicle.buy_datetime)
        # ent_tz = pytz.timezone(vehicle.enterprise.timezone)
        # vehicle.buy_datetime = vehicle.buy_datetime.astimezone(ent_tz)
        # vehicle_values['buy_datetime'] = str(vehicle.buy_datetime)[:19]
        # print(str(vehicle.buy_datetime)[:19])

        form = VehicleForm(initial=vehicle_values)
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