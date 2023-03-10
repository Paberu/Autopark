from django import forms

from park.models import Vehicle


class VehicleForm(forms.ModelForm):

    class Meta:
        model = Vehicle
        fields = ['manufacturer', 'model', 'cost', 'odometer', 'year', 'color', 'number_plate',
                  'enterprise', 'active_driver', 'buy_datetime']
