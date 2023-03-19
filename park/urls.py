from django.urls import path, include, re_path
from rest_framework.authtoken.views import obtain_auth_token

from park import views


urlpatterns = [
    path('api/vehicles/', views.VehicleInfoView.as_view()),
    path('api/routepoints/', views.RoutePointsInfoView.as_view()),
    path('api/travels/', views.TravelInfoView.as_view()),
    path('api/get_token', obtain_auth_token),
    path('management', views.management, name='management'),
    # path('enterprise', views.enterprise, name='enterprise'),
    re_path(r'enterprise/(?P<id>\d+)$', views.enterprise, name='enterprise'),
    re_path(r'vehicle/(?P<id>\d+)$', views.vehicle, name='vehicle'),
    re_path(r'delete_vehicle/(?P<id>\d+)$', views.delete_vehicle, name='delete_vehicle'),
    path('enterprises', views.enterprises, name='enterprises'),
    path('create_vehicle', views.create_vehicle, name='create_vehicle'),
    path('generate_track', views.generate_track, name='generate_track'),
]
