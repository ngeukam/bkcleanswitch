from datetime import timedelta, timezone
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ApartmentServices.Serializers import ApartmentSerializer, BookingCreateSerializer, BookingListSerializer, BookingUpdateSerializer
from ApartmentServices.models import Apartment, Booking
from cleanswitch.Helpers import CustomPageNumberPagination, CommonListAPIMixin
from PropertyServices.models import Property
from UserServices.Serializers import UserSerializer
from cleanswitch.permissions import IsAdmin, IsAdminOrManager, IsReceptionist
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count, F, ExpressionWrapper, fields, Sum

class CreateListApartmentAPIView(ListCreateAPIView):
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Apartment.objects.all().order_by('-created_at')
        else :
            return Apartment.objects.filter(is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        if self.request.user.role != 'admin':
            raise PermissionDenied("Only admins can create properties.")
        serializer.save(added_by_user_id=self.request.user)

    @CommonListAPIMixin.common_list_decorator(ApartmentSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class ListAvailableApartmentAPIView(ListAPIView):
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]  # Fixed typo: should be permission_classes (plural)
    pagination_class = None
    
    def get_queryset(self):
        # Get the current user
        user = self.request.user
        
        # Filter apartments that:
        # 1. Are active and not in service
        # 2. Belong to properties assigned to the current user
        if user.role == "admin" or user.is_superuser:
            queryset = Apartment.objects.filter(
            is_active=True, 
        )
        else:
            queryset = Apartment.objects.filter(
                is_active=True, 
                inService=False,
                property_assigned__in=user.properties_assigned.all()
            )
        
        return queryset

class ListApartmentAPIView(ListAPIView):
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]  # Fixed typo: should be permission_classes (plural)
    pagination_class = None
    
    def get_queryset(self):
        # Get the current user
        user = self.request.user
        
        # Filter apartments that:
        # 1. Are active and not in service
        # 2. Belong to properties assigned to the current user
        if user.role == "admin":
            queryset = Apartment.objects.filter(
            is_active=True, 
        ).order_by('-created_at')
        else:
            queryset = Apartment.objects.filter(
                is_active=True, 
                property_assigned__in=user.properties_assigned.all()
            ).order_by('-created_at')
            
        return queryset

class RetrieveUpdateDeleteApartmentAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None

class RetrieveUsersInApartmentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    def get(self, request, pk):
        # Get the property or return 404
        apartment = get_object_or_404(Property, id=pk)
        
        # Get all users assigned to this property
        users = apartment.assigned_users.all()  # Using the related_name from your model
        
        # Serialize the users
        serializer = UserSerializer(users, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
class BookingCreateAPIView(CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]

class BookingRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.all()
    permission_classes = [IsAuthenticated, IsReceptionist]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == 'receptionist':
            queryset = Booking.objects.filter(apartment__property_assigned__in = user.properties_assigned.all()).order_by('-dateOfReservation')
        elif user.role in ['admin', 'manager']:
            queryset
        return queryset
    
    def get_permissions(self):
            """
            Override to use different permissions for destroy operation.
            """
            if self.request.method == 'DELETE':
                # For DELETE, require manager or admin
                return [IsAuthenticated(), IsAdminOrManager()]
            else:
                # For GET, PUT, PATCH, use the default permissions
                return [IsAuthenticated(), IsReceptionist()]
            
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BookingUpdateSerializer
        return BookingListSerializer

    def validate_status_transition(self, current_status, new_status):
        """Validate allowed status transitions"""
        allowed_transitions = {
            'confirmed': ['checked_in', 'cancelled', 'active', 'upcoming'],
            'upcoming': ['checked_in', 'cancelled', 'active', 'confirmed'],
            'active': ['checked_in', 'cancelled', 'confirmed', 'upcoming'],
            'checked_in': ['checked_out'],  # Only allowed transition: checked_in → checked_out
            'checked_out': [],  # No transitions allowed from checked_out
            'cancelled': ['confirmed', 'upcoming', 'active']  # Allow reactivation
        }
        
        if current_status == new_status:
            return True  # No change is always allowed
        
        if new_status not in allowed_transitions.get(current_status, []):
            return False
        
        return True

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Get current and new data
        current_apartment = instance.apartment
        new_apartment_id = request.data.get('apartment')
        current_status = instance.status
        new_status = request.data.get('status')
        
        # Validate status transition
        if new_status and not self.validate_status_transition(current_status, new_status):
            error_messages = {
                'checked_in': "Cannot change status from 'checked_in'. Only check-out is allowed.",
                'checked_out': "Cannot modify a checked-out booking.",
            }
            
            return Response(
                {"message": error_messages.get(current_status, f"Invalid status transition from {current_status} to {new_status}")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If trying to change apartment, check if new apartment is in service
        if new_apartment_id and str(current_apartment.id) != str(new_apartment_id):
            try:
                new_apartment = Apartment.objects.get(id=new_apartment_id)
                
                # Additional check: Cannot change apartment if already checked in
                if current_status == 'checked_in':
                    return Response(
                        {"message": "Cannot change apartment for a checked-in booking"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if new_apartment.inService:
                    return Response(
                        {"message": "Cannot change to an apartment that is currently in service"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            except Apartment.DoesNotExist:
                return Response(
                    {"message": "Apartment not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Continue with the normal update process
        return super().update(request, *args, **kwargs)
    
class BookingListAPIView(ListAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingListSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == 'receptionist':
            queryset = Booking.objects.filter(apartment__property_assigned__in = user.properties_assigned.all()).order_by('-dateOfReservation')
        elif user.role in ['admin', 'manager']:
            queryset
        return queryset
    @CommonListAPIMixin.common_list_decorator(BookingListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
