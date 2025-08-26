from django.urls import path

from LocationServices.Controller.LocationController import ClockInOutAPIView, CurrentStatusAPIView, StaffLocationListCreate


urlpatterns = [
    path('locations/', StaffLocationListCreate.as_view(), name='staff-locations'),
    path('locations/clock/', ClockInOutAPIView.as_view(), name='clock-in-out'),
    path('locations/status/', CurrentStatusAPIView.as_view(), name='current-status'),
]