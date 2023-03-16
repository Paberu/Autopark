from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin

from park.models import Vehicle, Manufacturer, Model, Enterprise, Driver, Manager, RoutePoint, Travel

admin.site.register(Manufacturer)
admin.site.register(Manager)


# В каждой функции проверяется, не Manager ли в админке, не надо ли отфильтровать по Enterprise'ам.
# Вынес в отдельную функцию после того, как пришлось везде filter на get менять.
def get_manager_enterprises(request):
    if Manager.objects.filter(user=request.user):
        mngr = Manager.objects.get(user=request.user)
        return mngr.enterprise.all()


@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'city', 'country', 'timezone')
    actions_on_bottom = True
    actions_on_top = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        enterprises = get_manager_enterprises(request)
        if enterprises:
            return qs.filter(id__in=enterprises)
        return qs


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'age', 'salary', 'enterprise', 'car')
    actions_on_bottom = True
    actions_on_top = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        enterprises = get_manager_enterprises(request)
        if enterprises:
            return qs.filter(enterprise__in=enterprises)
        # if request.user.is_superuser:
        return qs

    def get_field_queryset(self, db, db_field, request):
        enterprises = get_manager_enterprises(request)
        if enterprises:
            if db_field.name == 'enterprise':
                return Enterprise.objects.filter(id__in=enterprises)
            if db_field.name == 'car' and Manager.objects.filter(user=request.user):
                return Vehicle.objects.filter(enterprise__in=enterprises)
        return super().get_field_queryset(db, db_field, request)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_manufacturer', 'display_model', 'cost', 'odometer', 'year', 'color', 'number_plate',
                    'enterprise', 'active_driver')
    actions_on_bottom = True
    actions_on_top = False

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.active_driver:
            return ['enterprise']
        return []

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        enterprises = get_manager_enterprises(request)
        if enterprises:
            return qs.filter(enterprise__in=enterprises)
        # if request.user.is_superuser:
        return qs

    def get_field_queryset(self, db, db_field, request):
        enterprises = get_manager_enterprises(request)
        if enterprises:
            if db_field.name == 'enterprise':
                return Enterprise.objects.filter(id__in=enterprises)
            if db_field.name == 'active_driver' and Manager.objects.filter(user=request.user):
                return Driver.objects.filter(enterprise__in=enterprises)
        return super().get_field_queryset(db, db_field, request)


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'body_type', 'power', 'passengers', 'fuel_tank')
    actions_on_bottom = True
    actions_on_top = False


@admin.register(RoutePoint)
class RoutePointAdmin(OSMGeoAdmin):
    list_display = ('id', 'vehicle', 'point', 'datetime')
    actions_on_bottom = True
    actions_on_top = False


@admin.register(Travel)
class TravelAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'begin', 'end')
    actions_on_bottom = True
    actions_on_top = False
