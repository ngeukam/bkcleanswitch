from django.urls import path
from ApartmentServices.Controller import ApartmentController

urlpatterns = [
    path('apartments/', ApartmentController.CreateListApartmentAPIView.as_view(), name='apartments-list-create'),
    path('apartments/<int:pk>/', ApartmentController.RetrieveUpdateDeleteApartmentAPIView.as_view(), name='retrieve-update-destroy-apartments'),
    path('apartments/<int:pk>/users/', ApartmentController.RetrieveUsersInApartmentAPIView.as_view(), name='apartments-users'),
    path('apartments/bookings/', ApartmentController.BookingCreateAPIView.as_view(), name='apartments-bookings'),
    path('apartments/bookings/<int:pk>/', ApartmentController.BookingRetrieveUpdateDestroyAPIView.as_view(), name='apartments-bookings-retrieve-update-destroy'),
    path('available/apartments/', ApartmentController.ListAvailableApartmentAPIView.as_view(), name='available-apartments'),
    path('apartments/mixed-up/', ApartmentController.ListApartmentAPIView.as_view(), name='apartments-mixed-up'),
    path('bookings/', ApartmentController.BookingListAPIView.as_view(), name='bookings-list'),
    path('bookings/<int:pk>/process_refund/', ApartmentController.BookingRefundAPIView.as_view(), name='booking-process-refund'),
    path('refunds/', ApartmentController.RefundListUpdateAPIView.as_view(), name='refunds'),
    path('refunds/<int:pk>/', ApartmentController.RefundRetrieveUpdateDeleteAPIView.as_view(), name='refund-retrieve-update'),

]