from django import forms

from park.models import Vehicle


class VehicleForm(forms.ModelForm):

    class Meta:
        model = Vehicle
        fields = ['manufacturer', 'model', 'cost', 'odometer', 'year', 'color', 'number_plate',
                  'enterprise', 'active_driver', 'buy_datetime']


class EnterpriseForm(forms.Form):
    companies = forms.ChoiceField()
    vehicles = forms.ChoiceField()
    travels = forms.ChoiceField()
    # route_points = forms.ChoiceField()


class GenerateTrackForm(forms.Form):
    vehicles = forms.ChoiceField(label='Автомобили')
    track_length = forms.FloatField(label='Длина пути')
    max_speed = forms.FloatField(label='Максимальная скорость')
    max_acceleration = forms.FloatField(label='Максимальное ускорение')