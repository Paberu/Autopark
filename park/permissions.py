from rest_framework.permissions import BasePermission

from park.models import Manager, Driver, Vehicle


class IsManagerPermission(BasePermission):

    def has_permission(self, request, view):
        return len(Manager.objects.filter(user=request.user)) > 0

    def has_object_permission(self, request, view, obj):
        manager = Manager.objects.filter(user=request.user)[0]
        enterprises = manager.enterprise.all()
        if obj.__class__.__name__ is 'Driver':
            drivers = Driver.objects.filter(enterprise__in=enterprises)
            if obj in drivers:
                return True
        elif obj.__class__.__name__ is 'Vehicle':
            vehicles = Vehicle.objects.filter(enterprise__in=enterprises)
            if obj in vehicles:
                return True
        return False


