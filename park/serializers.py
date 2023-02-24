import datetime

import pytz
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from autopark import settings
from park.models import Vehicle, Manufacturer, Model, Enterprise, RoutePoint


class ManufacturerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Manufacturer
        fields = ('id',)


class ModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Model
        fields = ('id', )


class EnterpriseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Enterprise
        fields = ('id', )


class VehicleSerializer(serializers.ModelSerializer):
    manufacturer = serializers.PrimaryKeyRelatedField(many=False, queryset=Manufacturer.objects.all())
    model = serializers.PrimaryKeyRelatedField(many=False, queryset=Model.objects.all())
    cost = serializers.IntegerField()
    odometer = serializers.IntegerField()
    year = serializers.IntegerField()
    color = serializers.CharField()
    number_plate = serializers.CharField()
    enterprise = serializers.PrimaryKeyRelatedField(many=False, queryset=Enterprise.objects.all(), required=False)
    active_driver = serializers.StringRelatedField(many=False)
    buy_datetime = serializers.DateTimeField()

    class Meta:
        model = Vehicle
        fields = ['manufacturer', 'model', 'cost', 'odometer', 'year', 'color', 'number_plate', 'enterprise',
                  'active_driver', 'buy_datetime']

    def create(self, validated_data):
        return Vehicle.objects.create(**validated_data)

    def update(self, vehicle, validated_data):
        vehicle.manufacturer = validated_data.get('manufacturer', vehicle.manufacturer)
        vehicle.model = validated_data.get('model', vehicle.model)
        vehicle.cost = validated_data.get('cost', vehicle.cost)
        vehicle.odometer = validated_data.get('manufacturer', vehicle.odometer)
        vehicle.year = validated_data.get('year', vehicle.year)
        vehicle.color = validated_data.get('color', vehicle.color)
        vehicle.number_plate = validated_data.get('number_plate', vehicle.number_plate)
        vehicle.enterprise = validated_data.get('enterprise', vehicle.enterprise)
        vehicle.active_driver = validated_data.get('active_driver', vehicle.active_driver)
        vehicle.buy_datetime = validated_data.get('buy_datetime', vehicle.buy_datetime)
        vehicle.save()
        return vehicle

    def to_representation(self, instance):
        ent_tz = pytz.timezone(instance.enterprise.timezone)
        buy_datetime = instance.buy_datetime.astimezone(ent_tz)
        ret = super().to_representation(instance)
        ret['buy_datetime'] = str(buy_datetime)
        return ret

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        local_tz = settings.TIME_ZONE
        if data['buy_datetime']:
            data['buy_datetime'] = data['buy_datetime'].astimezone(local_tz)
        return data


class RoutePointSerializer(serializers.ModelSerializer):

    class Meta:
        model = RoutePoint
        fields = ['point', 'datetime']

    def to_representation(self, instance):
        ent_tz = pytz.timezone(instance.vehicle.enterprise.timezone)
        point_datetime = instance.datetime.astimezone(ent_tz)
        ret = super().to_representation(instance)
        ret['datetime'] = str(point_datetime)
        return ret

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        local_tz = settings.TIME_ZONE
        if data['datetime']:
            data['datetime'] = data['datetime'].astimezone(local_tz)
        return data


class GeoRoutePointSerializer(GeoFeatureModelSerializer):

    class Meta:
        model = RoutePoint
        geo_field = 'point'
        fields = ['datetime',]

    def to_representation(self, instance):
        ent_tz = pytz.timezone(instance.vehicle.enterprise.timezone)
        point_datetime = instance.datetime.astimezone(ent_tz)
        ret = super().to_representation(instance)
        ret['datetime'] = str(point_datetime)
        return ret

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        local_tz = settings.TIME_ZONE
        if data['datetime']:
            data['datetime'] = data['datetime'].astimezone(local_tz)
        return data
