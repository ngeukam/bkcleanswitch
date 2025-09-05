from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from PropertyServices.Serializers import PropertySerializer
from ApartmentServices.Serializers import ApartmentSerializer, BookingListSerializer, RefundSerializer
from ApartmentServices.models import Apartment, Booking, Refund
from cleanswitch.Helpers import CustomPageNumberPagination, CommonListAPIMixin
from PropertyServices.models import Property
from UserServices.models import Guest
from UserServices.Serializers import GuestListSerializer, UserSerializerWithFilters
from TaskServices.Serializers import TaskSerializerWithFilters, TaskTemplateSerializer
from TaskServices.models import Task
from cleanswitch.permissions import IsAdmin, IsReceptionist
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count, F, ExpressionWrapper, fields

class CreateListPropertyAPIView(ListCreateAPIView):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_superuser == True:
            return Property.objects.all()
        else :
            return user.properties_assigned.filter(is_active=True)

    def perform_create(self, serializer):
        if self.request.user.role != 'admin':
            raise PermissionDenied("Only admins can create properties.")
        serializer.save(added_by_user_id=self.request.user)

    @CommonListAPIMixin.common_list_decorator(PropertySerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class ApartmentListByPropertyAPIView(ListAPIView):
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property = get_object_or_404(Property, id=property_id)
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_id).exists():
                raise PermissionDenied("You don't have access to this property")
            
        if user.role == 'admin' or user.is_superuser == True:
            apartments = property.apartments.all().order_by('-created_at')
        else:
            apartments = property.apartments.filter(is_active=True).order_by('-created_at')
        return apartments
    @CommonListAPIMixin.common_list_decorator(ApartmentSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class TaskListByPropertyAPIView(ListAPIView):
    serializer_class = TaskSerializerWithFilters
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property = get_object_or_404(Property, id=property_id)
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_id).exists():
                raise PermissionDenied("You don't have access to this property")
        if user.role == "manager":
            tasks = property.property_tasks.filter(property_assigned__is_active=True, property_assigned__id=property.id)
        elif user.role == "admin" or user.is_superuser == True:
            tasks = property.property_tasks.filter(property_assigned__id=property.id,)
        elif user.role == "receptionist":
            tasks = property.property_tasks.filter(
                property_assigned__in=user.properties_assigned.all(),
                property_assigned__is_active=True,
                property_assigned__id=property.id,
                active=True,
            )
        else:
            tasks = tasks.none()

        return tasks.order_by('-created_at')
    
    @CommonListAPIMixin.common_list_decorator(TaskSerializerWithFilters)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class UserListByPropertyAPIView(ListAPIView):
    serializer_class = UserSerializerWithFilters
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_id).exists():
                raise PermissionDenied("You don't have access to this property")
        # Get all users assigned to this property
        users = property_obj.assigned_users.all()
        
        # Apply filters based on user role
        if user.role == 'admin' or user.is_superuser:
            # Exclude guests for admin users
            users = users.exclude(role='guest')
        else:
            # Filter for specific roles for non-admin users
            users = users.filter(
                role__in=["cleaning", "technical"],
                department =user.department
            )
        
        return users
    @CommonListAPIMixin.common_list_decorator(UserSerializerWithFilters)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class StaffListByPropertyAPIView(ListAPIView):
    serializer_class = UserSerializerWithFilters
    permission_classes = [IsAuthenticated]
    pagination_class = None
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_id).exists():
                raise PermissionDenied("You don't have access to this property")
        # Get all users assigned to this property
        users = property_obj.assigned_users.all()
        
        # Apply filters based on user role
        if user.role == 'admin' or user.is_superuser:
            # Exclude guests for admin users
            users = users.filter(
                role__in=["cleaning", "technical"],
            )
        else:
            # Filter for specific roles for non-admin users
            users = users.filter(
                role__in=["cleaning", "technical"],
                department =user.department
            )
        
        return users

class BookingListByPropertyAPIView(ListAPIView):
    serializer_class = BookingListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        # Check if user has access to this property
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_id).exists():
                raise PermissionDenied("You don't have access to this property")
        
        # Get bookings for apartments in this property
        return Booking.objects.filter(
            apartment__property_assigned=property_obj
        ).select_related('apartment', 'guest').order_by('-dateOfReservation')
    @CommonListAPIMixin.common_list_decorator(BookingListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class GuestListByPropertyAPIView(ListAPIView):
    serializer_class = GuestListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        # Check if user has access to this property
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_id).exists():
                raise PermissionDenied("You don't have access to this property")
        
        # Get Guests for this property
        users = property_obj.assigned_users.all()
        users = users.exclude(role__in=["cleaning", "technical", "receptionist", "manager", "admin", "super admin"])
        return Guest.objects.filter(user__in=users)
    @CommonListAPIMixin.common_list_decorator(GuestListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
class TaskTemplateListByPropertyAPIView(ListAPIView):
    serializer_class = TaskTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        # Check if user has access to this property
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_obj.id).exists():
                raise PermissionDenied("You don't have access to this property")     
        if user.role == "admin" or user.is_superuser == True:
            tasks_template = property_obj.property_task_template.all()
        else:
            tasks_template = property_obj.property_task_template.filter(active=True)
        return tasks_template
    
    @CommonListAPIMixin.common_list_decorator(TaskTemplateSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class AvailableApartmentListByPropertyAPIView(ListAPIView):
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_obj.id).exists():
                raise PermissionDenied("You don't have access to this property")
            
        if user.role == "admin" or user.is_superuser:
            queryset = property_obj.apartments.filter(is_active=True).order_by('-created_at')
        else:
            queryset = property_obj.apartments.filter(
                is_active=True, 
                inService=False,
                property_assigned__in=user.properties_assigned.all()
            ).order_by('-created_at')
        
        return queryset

class RefundListByPropertyAPIView(ListAPIView):
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        user = self.request.user
        property_id = self.kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        if user.role != 'admin' and not user.is_superuser:
            if not user.properties_assigned.filter(id=property_obj.id).exists():
                raise PermissionDenied("You don't have access to this property")
        guests = Guest.objects.filter(user__in = property_obj.assigned_users.all())
        queryset = Refund.objects.filter(guest__in = guests).select_related(
            'guest', 'reservation', 'processed_by'
        ).order_by('-created_at')
        return queryset
            
    @CommonListAPIMixin.common_list_decorator(RefundSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
        
class RetrieveUpdateDeletePropertyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    pagination_class = None
    
    def get_permissions(self):
            """
            Override to use different permissions for destroy operation.
            """
            if self.request.method == 'DELETE':
                # For DELETE, require or admin
                return [IsAuthenticated(), IsAdmin()]
            else:
                # For GET, PUT, PATCH, use the default permissions
                return [IsAuthenticated(), IsReceptionist()]
                
    def perform_update(self, serializer):
        user = self.request.user
        if user.role != 'admin':
            return Response(
                {"message": "Only admins can update property."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

class PropertyStatsAPIView(APIView):
    """
    A view to return key performance indicators (KPIs) for the dashboard.
    """
    permission_classes = [IsReceptionist]
    def get(self, request, *args, **kwargs):
        # Filter data for the current property if available
        # You'll need to pass the property ID in the request, e.g., in the URL or query params
        property_id = request.query_params.get('property_id')
        property = get_object_or_404(Property, id=property_id)
        
        # Get the current month and year
        today = timezone.now()
        current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_end = current_month_start + timedelta(days=32) # A safe bet
        # 1. Total Number of Guests
        total_guests = Guest.objects.filter(
            booking__apartment__property_assigned_id=property.id,
            user__date_joined__gte=current_month_start,
            user__date_joined__lte=current_month_end
        ).distinct().count()

        # Count total reservations for a given property
        total_month_reservations = Booking.objects.filter(
            dateOfReservation__gte=current_month_start,
            dateOfReservation__lte=current_month_end,
            apartment__property_assigned_id=property.id
        ).exclude(status__in = ['checked_in', 'checked_out']).count()
        
        # 3. Occupancy Rate
        # To calculate this, you need the total available room-nights
        total_apartments = Apartment.objects.filter(property_assigned__id=property.id).count()
        currency = Apartment.objects.filter(property_assigned__id=property.id).values_list('currency')
        today = timezone.now().date()
        
        # Count apartments with 'checked_in' status today
        occupied_apartments_today = Booking.objects.filter(
            status='checked_in',
            startDate__lte=today,
            endDate__gte=today,
            apartment__id=property.id
        ).count()
        
        occupancy_rate = (occupied_apartments_today / total_apartments) * 100 if total_apartments > 0 else 0
        
        # 4. Current Month's Income
        current_month = timezone.now().month
        current_year = timezone.now().year
        
        # Assumes price is stored on the Booking model or can be accessed from the Apartment
        # We'll calculate based on active bookings within the current month
        bookings_this_month = Booking.objects.filter(
            startDate__year=current_year,
            startDate__month=current_month,
            apartment__id=property.id,
            status='checked_in'
        ).select_related('apartment')
        
        total_income_this_month = sum(
            booking.apartment.price * (booking.endDate - booking.startDate).days
            for booking in bookings_this_month
        )

        # 5. Number of Today Check-ins
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        number_of_check_ins = Booking.objects.filter(
            status='checked_in',
            updated_at__gte=today_start,
            updated_at__lte=today_end,
            apartment__id=property.id
        ).count()
        
        # Monthly Check ins 
        total_check_ins = Booking.objects.filter(
            status='checked_in',
            updated_at__gte=current_month_start,
            updated_at__lte=current_month_end,
            apartment__id=property.id
        ).count()
        
        # 6. Number of Guests Registered per day in the current week
        today = timezone.now()
        start_of_week = today - timedelta(days=today.weekday())
        
        # 7. Total Pending Task
        total_pending_tasks = Task.objects.filter(
            status="pending",
            property_assigned__id=property.id,
            active=True
        ).count()
        # 8. Total Reservations
        total_reservations = Booking.objects.filter(
            apartment__property_assigned_id=property.id
        ).count()
        
         # 9. Total Guest
        total_register_guests = Guest.objects.filter(
            booking__apartment__property_assigned_id=property.id,
        ).distinct().count()
        
        # 10. Total Booking Refund
        total_pending_booking_refunds = Refund.objects.filter(
            reservation__apartment__property_assigned_id=property.id,
            status='pending'
        ).count()
        
        guests_registered_per_day = Guest.objects.filter(
            booking__apartment__property_assigned_id=property.id,
            user__date_joined__gte=start_of_week
        ).annotate(
            day_of_week=ExpressionWrapper(
                F('user__date_joined'), 
                output_field=fields.DateField()
            )
        ).values('day_of_week').annotate(
            count=Count('id')
        ).order_by('day_of_week')
        
        # Format the result to include all 7 days of the week, even with 0 guests
        formatted_guest_data = {
            (start_of_week + timedelta(days=i)).strftime('%Y-%m-%d'): 0 
            for i in range(7)
        }
        for entry in guests_registered_per_day:
            formatted_guest_data[entry['day_of_week'].strftime('%Y-%m-%d')] = entry['count']

        data = {
            "currency":currency,
            "total_checkin":total_check_ins,
            "number_of_guests": total_guests,
            "number_of_reservations": total_month_reservations,
            "occupancy_rate": round(occupancy_rate, 2),
            "current_month_income": round(total_income_this_month, 2),
            "number_of_check_ins": number_of_check_ins,
            "guests_registered_per_day_current_week": formatted_guest_data,
            "total_pending_tasks":total_pending_tasks,
            "total_register_guests":total_register_guests,
            "total_reservations":total_reservations,
            "total_pending_booking_refunds":total_pending_booking_refunds,
        }
        
        return Response(data)