from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ApartmentServices.Serializers import ApartmentSerializer, BookingCalendarSerializer, BookingCreateSerializer, BookingListSerializer, BookingUpdateSerializer, RefundSerializer
from ApartmentServices.models import Apartment, Booking, Refund
from cleanswitch.Helpers import CustomPageNumberPagination, CommonListAPIMixin
from PropertyServices.models import Property
from UserServices.Serializers import UserSerializer
from cleanswitch.permissions import IsAdmin, IsAdminOrManager, IsReceptionist
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, Sum

class CreateListApartmentAPIView(ListCreateAPIView):
    serializer_class = ApartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_superuser:
            return Apartment.objects.all()
        else :
            return Apartment.objects.filter(is_active=True, property_assigned__in=user.properties_assigned.all())

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
            # Updated to use apartments ManyToMany field
            queryset = Booking.objects.filter(
                apartments__property_assigned__in=user.properties_assigned.all()
            ).distinct().order_by('-dateOfReservation')
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
        else:
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
        current_apartments = instance.apartments.all()  # Now ManyToMany
        new_apartment_ids = request.data.get('apartments', [])  # Expecting array of IDs
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
        
        # If trying to change apartments, check if new apartments are in service
        if new_apartment_ids:
            try:
                new_apartments = Apartment.objects.filter(id__in=new_apartment_ids)
                
                # Check if apartments are actually changing
                current_apartment_ids = set(current_apartments.values_list('id', flat=True))
                new_apartment_ids_set = set(new_apartment_ids)
                
                if current_apartment_ids != new_apartment_ids_set:
                    # Additional check: Cannot change apartments if already checked in
                    if current_status == 'checked_in':
                        return Response(
                            {"message": "Cannot change apartments for a checked-in booking"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Check if any new apartment is in service
                    in_service_apartments = new_apartments.filter(inService=True)
                    if in_service_apartments.exists():
                        apartment_numbers = [str(apt.number) for apt in in_service_apartments]
                        return Response(
                            {"message": f"Cannot assign apartments that are currently in service: {', '.join(apartment_numbers)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            except Apartment.DoesNotExist:
                return Response(
                    {"message": "One or more apartments not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Continue with the normal update process
        return super().update(request, *args, **kwargs)
    
class BookingListAPIView(ListAPIView):
    queryset = Booking.objects.all().order_by('-dateOfReservation')
    serializer_class = BookingListSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == 'receptionist':
            queryset = queryset.filter(
                apartments__property_assigned__in=user.properties_assigned.all()
            ).distinct().order_by('-dateOfReservation')        
        elif user.role in ['admin', 'manager'] or user.is_superuser:
            queryset
        return queryset
    @CommonListAPIMixin.common_list_decorator(BookingListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class BookingRefundAPIView(APIView):
    permission_classes = [IsAuthenticated, IsReceptionist]
    
    def get(self, request, pk):
        """
        GET bookings/{id}/process_refund/
        Retrieve all refunds for a specific booking
        """
        try:
            # Get the booking
            booking = get_object_or_404(Booking, pk=pk)
            
            # Check if user has permission to view this booking's refunds
            if not self.has_booking_permission(request.user, booking):
                return Response(
                    {"message": "You don't have permission to view refunds for this booking"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get all refunds for this booking
            refunds = Refund.objects.filter(reservation=booking).order_by('-created_at')
            
            # Serialize the refunds
            refund_data = []
            for refund in refunds:
                refund_data.append({
                    'id': refund.id,
                    'amount': float(refund.amount) if refund.amount else None,
                    'reason': refund.reason,
                    'status': refund.status,
                    'created_at': refund.created_at.isoformat() if refund.created_at else None,
                    'guest_name': f"{refund.guest.user.first_name} {refund.guest.user.last_name}" if refund.guest else None,
                    'guest_email': refund.guest.user.email if refund.guest else None
                })
            
            return Response(refund_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": "Error fetching refunds", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, pk):
        """
        POST /bookings/{id}/process_refund/
        Create a new refund for a booking
        """
        try:
            # Get the booking
            booking = get_object_or_404(Booking, pk=pk)
            user = request.user
            # Check if user has permission to create refunds for this booking
            if not self.has_booking_permission(request.user, booking):
                return Response(
                    {"message": "You don't have permission to create refunds for this booking"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate request data
            amount = request.data.get('amount')
            reason = request.data.get('reason', '')
            refund_status = request.data.get('status', 'pending')
            
            if user.role == 'receptionist' and refund_status == 'approved':
                return Response(
                    {"message": "You don't have permission to approve refunds"},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Validation
            if not amount:
                return Response(
                    {"message": "Refund amount is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                amount_decimal = float(str(amount))
                if amount_decimal <= 0:
                    return Response(
                        {"message": "Refund amount must be greater than 0"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {"message": "Invalid refund amount format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not reason.strip():
                return Response(
                    {"message": "Refund reason is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if booking can be refunded
            validation_error = self.validate_refund_eligibility(booking, amount_decimal)
            if validation_error:
                return Response(
                    {"message": validation_error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Calculate booking total price (same logic as in serializer)
            booking_total_price = self.calculate_booking_total_price(booking)
            # Calculate total already refunded
            total_refunded = Refund.objects.filter(
                reservation=booking, 
                status__in=['approved', 'pending']
            ).aggregate(total=Sum('amount'))['total'] or float('0')
            
            # Check if new refund would exceed booking total
            if total_refunded + amount_decimal > booking_total_price:
                max_refundable = booking_total_price - total_refunded
                return Response(
                    {"message": f"Refund amount exceeds available balance. Maximum refundable: {max_refundable:.2f}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the refund
            refund = Refund.objects.create(
                guest=booking.guest,
                reservation=booking,
                amount=amount_decimal,
                reason=reason,
                status=refund_status,
                processed_by=request.user
            )
            
            # If refund is created with status 'approved', update booking if needed
            if refund_status == 'approved':
                # Update processed timestamp
                refund.processed_at = datetime.now()
                refund.save()
                
                # You might want to update booking status here based on business logic
                # For example, if full refund, mark as cancelled
                if amount_decimal == booking_total_price and booking.status != 'cancelled':
                    booking.status = 'cancelled'
                    booking.save()

            # Serialize the created refund
            refund_data = {
                'id': refund.id,
                'amount': float(refund.amount),
                'reason': refund.reason,
                'status': refund.status,
                'created_at': refund.created_at.isoformat() if refund.created_at else None,
                'message': 'Refund created successfully'
            }
            
            return Response(refund_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"message": "Error creating refund", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def has_booking_permission(self, user, booking):
        """
        Check if user has permission to access this booking's refunds
        """
        if user.role == 'admin':
            return True
        
        if user.role in ['receptionist', 'manager']:
            # Receptionist can only access bookings for properties they're assigned to
            return booking.apartment.property_assigned in user.properties_assigned.all()
        
        return False
    
    def validate_refund_eligibility(self, booking, amount):
        """
        Validate if the booking is eligible for refund
        """
        # Check booking status
        if booking.status not in ['cancelled', 'checked_out', 'confirmed', 'upcoming']:
            return "Refunds can only be processed for cancelled, checked-out, confirmed, or upcoming bookings"
        
        # Check if booking has an apartment with price
        if not booking.apartment or not booking.apartment.price:
            return "Cannot process refund - booking apartment or price information is missing"
        
        # Check if booking has valid dates
        if not booking.startDate or not booking.endDate:
            return "Cannot process refund - booking dates are invalid"
        
        # Additional business logic can be added here
        return None
    
    
    def calculate_booking_total_price(self, booking):
        """
        Calculate total price using the same logic as in the serializer
        """
        try:
            if booking.apartment and booking.apartment.price and booking.startDate and booking.endDate:
                # Calculate total hours and round up to full days
                total_hours = (booking.endDate - booking.startDate).total_seconds() / 3600
                duration_days = math.ceil(total_hours / 24)
                total_price = duration_days * booking.apartment.price
                return float(str(round(total_price, 2)))
            return float('0')
        except (AttributeError, TypeError, ValueError):
            return Decimal('0')

class CalendarBookingsAPIView(APIView):
    """
    API endpoint to get bookings for calendar view
    """
    
    def get(self, request):
        try:
            # Get date range from query parameters (optional)
            start_date = request.GET.get('start')
            end_date = request.GET.get('end')
            
            queryset = Booking.objects.all()
            
            # Filter by date range if provided
            if start_date and end_date:
                queryset = queryset.filter(
                    Q(startDate__range=[start_date, end_date]) |
                    Q(endDate__range=[start_date, end_date])
                )
            
            # Apply user permissions
            user = request.user
            if user.role == 'receptionist':
                queryset = queryset.filter(
                    apartments__property_assigned__in=user.properties_assigned.all()
                ).distinct()
            elif user.role in ['technical', 'cleaning']:
                # Only show bookings for apartments they're assigned to (if applicable)
                pass
            
            serializer = BookingCalendarSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class RefundListAPIView(ListAPIView):
    queryset = Refund.objects.all().select_related(
        'guest', 'reservation', 'processed_by'
    ).order_by('-created_at')
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    @CommonListAPIMixin.common_list_decorator(RefundSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class RefundRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Refund.objects.all().select_related(
        'guest', 'reservation', 'processed_by'
    )
    serializer_class = RefundSerializer
    pagination_class = None
    
    def get_permissions(self):
            """
            Override to use different permissions for destroy operation.
            """
            if self.request.method == 'DELETE':
                # For DELETE, require manager or admin
                return [IsAuthenticated(), IsAdmin()]
            else:
                return [IsAuthenticated(), IsReceptionist()]
            
    def perform_update(self, serializer):
        # Set processed_by and processed_at when status changes to approved/rejected
        instance = serializer.instance
        new_status = serializer.validated_data.get('status')
        
        if new_status in ['approved', 'rejected'] and instance.status == 'pending':
            serializer.validated_data['processed_by'] = self.request.user
            serializer.validated_data['processed_at'] = datetime.now()
        if instance.status == "pending":
            serializer.validated_data['updated_by'] = self.request.user
        serializer.save()