from django.urls import path
from PropertyServices.Controller import PropertyController

urlpatterns = [
    path('properties/', PropertyController.CreateListPropertyAPIView.as_view(), name='properties-list-create'),
    path('properties/<int:pk>/', PropertyController.RetrieveUpdateDeletePropertyAPIView.as_view(), name='retrieve-update-destroy-property'),
    path('properties/stats/', PropertyController.PropertyStatsAPIView.as_view(), name='property-stats'),
    path('properties/<int:property_id>/apartments/', PropertyController.ApartmentListByPropertyAPIView.as_view(), name='property-apartments'),
    path('properties/<int:property_id>/tasks/', PropertyController.TaskListByPropertyAPIView.as_view(), name='property-tasks'),
    path('properties/<int:property_id>/tasks-template/', PropertyController.TaskTemplateListByPropertyAPIView.as_view(), name='property-tasks-template'),
    path('properties/<int:property_id>/users/', PropertyController.UserListByPropertyAPIView.as_view(), name='property-users'),
    path('properties/<int:property_id>/staff/', PropertyController.StaffListByPropertyAPIView.as_view(), name='property-users'),
    path('properties/<int:property_id>/bookings/', PropertyController.BookingListByPropertyAPIView.as_view(), name='property-bookings'),
    path('properties/<int:property_id>/guests/', PropertyController.GuestListByPropertyAPIView.as_view(), name='property-guests'),
    path('properties/<int:property_id>/available-apartments/', PropertyController.AvailableApartmentListByPropertyAPIView.as_view(), name='property-available-apartments'),
    path('properties/<int:property_id>/refunds/', PropertyController.RefundListByPropertyAPIView.as_view(), name='property-refunds'),

]