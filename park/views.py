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
from .forms import VehicleForm, EnterpriseForm, GenerateTrackForm
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
                ).order_by('datetime')

                route_line = []
                for route_point in route_points:
                    route_line.append(list(reversed(route_point.point.coords)))

                context['route_line'] = route_line
    return render(request, 'enterprises.html', context=context)

@login_required
def generate_track(request):
    if request.user.is_superuser:
        vehicles = Vehicle.objects.all()
    else:
        raise Http404()

    # map_request = "https://api-maps.yandex.ru/2.1/?lang=ru_RU&amp;apikey=e85c72cb-b9ca-4887-838f-b0cf38d74df9&ll={ll}&z={z}&l={type}".format(ll=mp.ll(), z=mp.zoom, type=mp.type)
    # response = requests.get(map_request)
    form = GenerateTrackForm()
    route_line = [[28.201305, 57.838777], [28.201182, 57.838392], [28.200765, 57.838257], [28.199336, 57.838405], [28.198704, 57.838566], [28.197439, 57.838647], [28.196908, 57.838647], [28.195846, 57.838546], [28.195466, 57.838311], [28.195525, 57.837663], [28.19581, 57.837268], [28.196188, 57.836979], [28.196535, 57.836124], [28.196841, 57.835548], [28.197457, 57.83477], [28.197405, 57.834572], [28.197252, 57.834285], [28.207619, 57.832383], [28.212307, 57.831801], [28.222576, 57.831617], [28.226861, 57.83126], [28.227109, 57.831265], [28.232329, 57.825541], [28.235206, 57.825537], [28.239501, 57.825577], [28.244206, 57.8256], [28.249099, 57.825641], [28.252976, 57.825707], [28.25326, 57.824888], [28.256183, 57.817777], [28.256343, 57.817146], [28.256595, 57.811142], [28.256723, 57.807373], [28.25689, 57.804727], [28.25694, 57.804631], [28.257078, 57.804516], [28.258479, 57.804879], [28.259979, 57.805229], [28.266937, 57.80706], [28.267466, 57.807151], [28.268911, 57.807519], [28.269472, 57.807772], [28.274871, 57.809184], [28.276432, 57.809571], [28.279171, 57.810333], [28.28414, 57.811644], [28.287783, 57.812567], [28.293573, 57.814072], [28.293728, 57.813867], [28.294168, 57.813465], [28.294766, 57.812958], [28.295208, 57.812627], [28.295822, 57.81228], [28.296271, 57.812072], [28.296505, 57.812047], [28.297148, 57.811826], [28.301197, 57.810698], [28.305058, 57.80959], [28.306321, 57.809245], [28.30829, 57.808745], [28.3142, 57.807106], [28.318314, 57.805751], [28.321974, 57.804666], [28.323924, 57.804091], [28.325715, 57.803592], [28.326188, 57.803386], [28.327617, 57.802888], [28.327869, 57.802819], [28.328134, 57.802767], [28.328589, 57.802726], [28.329062, 57.802733], [28.329355, 57.802763], [28.330103, 57.802906], [28.330776, 57.803085], [28.334762, 57.803966], [28.335382, 57.804026], [28.335785, 57.804038], [28.335893, 57.80401], [28.336133, 57.803847], [28.336393, 57.803559], [28.336658, 57.803048], [28.336982, 57.802538], [28.337527, 57.802002], [28.338696, 57.80102], [28.339679, 57.799961], [28.341534, 57.797103], [28.34174, 57.796921], [28.342292, 57.796592], [28.342948, 57.796371], [28.343685, 57.796298], [28.344394, 57.796254], [28.344855, 57.796201], [28.345174, 57.796101], [28.345452, 57.795942], [28.345969, 57.79549], [28.346138, 57.795244], [28.346207, 57.7951], [28.346615, 57.793405], [28.346747, 57.792987], [28.347204, 57.792452], [28.347779, 57.791833], [28.348937, 57.790479], [28.349278, 57.790202], [28.356117, 57.785205], [28.356783, 57.784686], [28.35779, 57.783753], [28.36063, 57.781006], [28.360893, 57.780693], [28.361072, 57.780338], [28.361121, 57.780017], [28.361121, 57.779056], [28.361984, 57.777084], [28.362491, 57.775824], [28.363184, 57.774205], [28.363265, 57.773867], [28.363282, 57.773625], [28.363207, 57.773325], [28.362421, 57.77112], [28.362453, 57.770869], [28.363347, 57.768954], [28.368367, 57.76327], [28.368793, 57.762741], [28.369159, 57.762189], [28.370742, 57.759318], [28.37097, 57.758971], [28.371262, 57.758711], [28.371502, 57.758566], [28.371815, 57.758417], [28.374011, 57.757573], [28.37748, 57.7561], [28.37802, 57.755917], [28.380361, 57.755269], [28.380532, 57.755151], [28.380584, 57.754956], [28.379246, 57.753562], [28.378293, 57.752764], [28.377675, 57.75206], [28.377379, 57.751632], [28.376514, 57.75017], [28.375942, 57.749454], [28.374482, 57.748406], [28.37135, 57.746043], [28.370908, 57.74548], [28.370768, 57.745255], [28.370175, 57.743884], [28.369973, 57.743555], [28.369809, 57.74337], [28.368547, 57.742549], [28.367163, 57.741551], [28.366242, 57.740611], [28.365538, 57.739733], [28.364018, 57.738076], [28.36113, 57.734859], [28.359757, 57.73333], [28.357123, 57.730347], [28.356213, 57.72922], [28.352891, 57.724641], [28.351047, 57.722051], [28.348079, 57.718073], [28.344314, 57.712823], [28.339192, 57.705825], [28.336451, 57.702038], [28.326916, 57.688982], [28.326087, 57.687817], [28.325735, 57.687237], [28.325505, 57.686811], [28.325262, 57.686189], [28.325136, 57.685519], [28.325027, 57.684003], [28.32457, 57.673338], [28.324326, 57.668294], [28.324134, 57.663723], [28.323969, 57.658925], [28.323903, 57.657741], [28.323685, 57.652722], [28.323611, 57.651559], [28.323525, 57.648812], [28.322906, 57.633341], [28.321816, 57.618459], [28.321378, 57.612826], [28.32115, 57.609299], [28.32031, 57.598482], [28.319669, 57.58942], [28.319326, 57.585271], [28.318241, 57.569933], [28.318122, 57.568551], [28.318189, 57.567863], [28.323117, 57.551188], [28.325499, 57.543218], [28.32626, 57.540832], [28.328209, 57.533921], [28.329551, 57.529518], [28.329955, 57.528033], [28.330606, 57.525954], [28.331173, 57.523996], [28.331428, 57.523015], [28.332071, 57.520938], [28.335432, 57.50944], [28.33616, 57.507016], [28.337909, 57.500976], [28.33863, 57.498586], [28.339452, 57.496246], [28.341043, 57.49096], [28.34163, 57.489162], [28.342471, 57.486262], [28.344112, 57.481013], [28.34479, 57.478602], [28.350392, 57.459827], [28.351852, 57.45502], [28.353518, 57.449307], [28.355313, 57.44302], [28.356302, 57.439451], [28.358346, 57.432368], [28.359047, 57.430062], [28.360727, 57.423991], [28.361586, 57.421172], [28.362909, 57.416267], [28.363038, 57.415042], [28.36377, 57.405444], [28.363967, 57.402176], [28.364344, 57.398119], [28.364454, 57.395994], [28.364712, 57.393034], [28.364756, 57.391646], [28.364627, 57.390259], [28.364348, 57.388893], [28.363425, 57.384939], [28.363052, 57.383593], [28.362476, 57.381367], [28.359529, 57.369444], [28.359481, 57.369149], [28.359471, 57.368866], [28.359544, 57.368242], [28.359654, 57.367596], [28.359724, 57.367347], [28.359803, 57.367113], [28.360316, 57.366055], [28.368882, 57.352564], [28.369305, 57.35177], [28.369606, 57.351089], [28.369741, 57.350702], [28.369846, 57.350297], [28.370085, 57.348619], [28.370202, 57.347474], [28.370425, 57.343914], [28.370553, 57.342295], [28.370756, 57.339272], [28.370774, 57.338016], [28.370726, 57.337139], [28.370664, 57.336579], [28.370466, 57.335366], [28.370196, 57.3344], [28.369704, 57.33311], [28.369136, 57.331778], [28.368607, 57.33065], [28.364145, 57.322003], [28.363706, 57.321119], [28.363367, 57.320341], [28.363134, 57.31962], [28.362975, 57.318999], [28.362813, 57.318123], [28.362712, 57.316866], [28.36272, 57.316341], [28.362869, 57.315219], [28.363022, 57.314569], [28.363343, 57.313559], [28.363684, 57.312656], [28.363937, 57.312118], [28.364454, 57.311311], [28.369947, 57.303931], [28.372416, 57.301886], [28.374041, 57.300479], [28.376394, 57.298482], [28.388978, 57.287676], [28.39222, 57.284785], [28.393706, 57.28353], [28.394521, 57.282795], [28.396962, 57.280734], [28.399248, 57.278758], [28.400403, 57.277825], [28.404401, 57.274277], [28.405885, 57.272547], [28.406608, 57.271606], [28.409801, 57.267778], [28.413579, 57.262967], [28.419464, 57.255633], [28.432976, 57.238743], [28.443258, 57.225881], [28.467547, 57.195512], [28.469643, 57.19289], [28.474074, 57.187347], [28.475036, 57.186205], [28.478829, 57.181384], [28.481319, 57.178286], [28.482071, 57.177272], [28.482749, 57.176413], [28.486113, 57.172298], [28.492181, 57.164666], [28.494459, 57.161844], [28.500769, 57.153819], [28.501662, 57.152771], [28.502844, 57.151312], [28.51043, 57.141741], [28.511823, 57.140084], [28.514995, 57.136033], [28.518716, 57.131327], [28.519604, 57.130246], [28.525244, 57.123159], [28.531408, 57.11541], [28.53316, 57.113208], [28.538133, 57.106826], [28.544495, 57.098822], [28.548316, 57.093951], [28.554703, 57.085951], [28.55484, 57.085742], [28.567197, 57.070072], [28.570461, 57.065867], [28.573843, 57.06168], [28.579447, 57.054532], [28.580601, 57.054334], [28.581448, 57.054221], [28.584714, 57.053891], [28.586799, 57.053655], [28.588762, 57.05341], [28.611837, 57.050244], [28.613201, 57.050082], [28.615919, 57.04986], [28.63591, 57.048416], [28.650656, 57.04736], [28.655632, 57.046954], [28.661851, 57.046531], [28.664556, 57.046412], [28.665988, 57.046378], [28.669111, 57.046376], [28.671368, 57.046518], [28.680747, 57.047736], [28.683373, 57.048002], [28.685284, 57.048053], [28.687596, 57.048047], [28.689375, 57.048001], [28.69119, 57.047919], [28.692632, 57.047824], [28.695886, 57.047575], [28.700399, 57.047281], [28.707906, 57.046741], [28.712673, 57.046461], [28.713737, 57.046429], [28.715814, 57.046442], [28.718635, 57.04657], [28.725865, 57.047236], [28.741366, 57.048716], [28.744109, 57.048958], [28.745123, 57.049009], [28.746012, 57.049035], [28.748715, 57.049044], [28.754272, 57.049], [28.780681, 57.048899], [28.783917, 57.048823], [28.78577, 57.048739], [28.788046, 57.048593], [28.790128, 57.048437], [28.791344, 57.048318], [28.797859, 57.047612], [28.804171, 57.046974], [28.806042, 57.046776], [28.8084, 57.046509], [28.812691, 57.046058], [28.813657, 57.045933], [28.814298, 57.045834], [28.815836, 57.045561], [28.816971, 57.045321], [28.818345, 57.044984], [28.820165, 57.044431], [28.821602, 57.043939], [28.822623, 57.043533], [28.822966, 57.043382], [28.823874, 57.042941], [28.824633, 57.042543], [28.825241, 57.0422], [28.825654, 57.041943], [28.826977, 57.041016], [28.828638, 57.039697], [28.83117, 57.037571], [28.833693, 57.035399], [28.834691, 57.034512], [28.83559, 57.033798], [28.836256, 57.033302], [28.837064, 57.032757], [28.838037, 57.032151], [28.838665, 57.031807], [28.839326, 57.031489], [28.839838, 57.031787], [28.842189, 57.033237], [28.844932, 57.034972], [28.847023, 57.036223], [28.849276, 57.037623], [28.852386, 57.036684], [28.852911, 57.036551], [28.853385, 57.036459], [28.853719, 57.036446], [28.854012, 57.036475], [28.854409, 57.03655], [28.857029, 57.037601], [28.859694, 57.038724], [28.862646, 57.039862], [28.865651, 57.040913], [28.867828, 57.041641], [28.872624, 57.043286], [28.873141, 57.043393], [28.873542, 57.043419], [28.874047, 57.043392], [28.874633, 57.043287], [28.875318, 57.04306], [28.877722, 57.042065], [28.880569, 57.040912], [28.880709, 57.040883], [28.880792, 57.040899], [28.880835, 57.040922], [28.880841, 57.041], [28.878709, 57.043273], [28.878481, 57.043543], [28.878244, 57.043925], [28.877762, 57.046812], [28.87697, 57.050351], [28.876807, 57.052962], [28.876843, 57.053226], [28.87692, 57.053411], [28.877101, 57.053586], [28.877368, 57.053763], [28.877738, 57.053886], [28.878949, 57.054116], [28.881992, 57.055461], [28.882785, 57.05579], [28.88359, 57.056082], [28.884086, 57.056209], [28.885625, 57.056544], [28.888872, 57.057162], [28.892839, 57.058048], [28.892116, 57.058886], [28.889772, 57.061485], [28.888542, 57.062989], [28.887531, 57.064133], [28.886154, 57.065563], [28.8864, 57.065626], [28.886837, 57.065638], [28.887058, 57.065603], [28.887205, 57.065522], [28.887839, 57.065003], [28.888187, 57.064898], [28.889335, 57.064871], [28.889671, 57.064899], [28.890081, 57.064981], [28.890698, 57.065141], [28.892923, 57.06579], [28.894096, 57.066109], [28.89468, 57.066311], [28.896148, 57.06691], [28.897032, 57.067194], [28.897733, 57.06739], [28.898528, 57.067462], [28.899186, 57.067424], [28.899613, 57.067475], [28.899862, 57.067551], [28.90008, 57.067806], [28.900112, 57.06848], [28.900238, 57.068694], [28.900549, 57.06891], [28.900979, 57.069111], [28.901415, 57.068923], [28.901598, 57.068786], [28.901886, 57.068337], [28.902178, 57.068193], [28.902364, 57.068139], [28.902603, 57.068073], [28.903068, 57.067985], [28.903325, 57.067979], [28.904376, 57.068151], [28.90566, 57.068397], [28.906298, 57.068374], [28.906788, 57.068408], [28.907924, 57.068563]]
    context = {'vehicles': vehicles, 'form': form, 'route_line': route_line}
    # if request.method == 'GET':
    # initial_values = {}
    # initial_values['enterprises'] = companies
    # form = EnterpriseForm(initial=initial_values)
    # context = {'companies': companies, 'form': form}

    print(context)
    if request.method == 'POST':
        pass

    return render(request, 'generate_track.html', context=context)
