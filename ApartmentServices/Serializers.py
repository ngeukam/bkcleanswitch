import math
from rest_framework import serializers
from cleanswitch.Helpers import createParsedCreatedAtUpdatedAt
from UserServices.models import Guest, User
from PropertyServices.Serializers import PropertySimpleSerializer
from .models import Apartment, Booking
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db.models import Q


@createParsedCreatedAtUpdatedAt
class ApartmentSerializer(serializers.ModelSerializer):
    added_by_user_id = serializers.SerializerMethodField()
    property_assigned_name = serializers.SerializerMethodField()
    property_address = serializers.SerializerMethodField()
    class Meta:
        model = Apartment
        fields = '__all__'
        
    def get_added_by_user_id(self, obj):
        if obj.added_by_user_id:
            return obj.added_by_user_id.username
        return None
        
    def get_property_assigned_name(self, obj):
        return obj.property_assigned.name if obj.property_assigned else None
    
    def get_property_address(self, obj):
        return obj.property_assigned.address if obj.property_assigned else None

    def validate(self, data):
        instance = self.instance  # This is None during creation, existing instance during update
        number = data.get('number')
        property_assigned = data.get('property_assigned')
        
        # Skip validation if number isn't being changed
        if instance and number == instance.number and property_assigned == instance.property_assigned:
            return data
            
        # Check for duplicate apartment number in the same property
        qs = Apartment.objects.filter(
            number=number,
            property_assigned=property_assigned
        )
        
        # If updating, exclude current instance from the check
        if instance:
            qs = qs.exclude(pk=instance.pk)
            
        if qs.exists():
            raise serializers.ValidationError({
                'message': 'This apartment number already exists for the selected property'
            })
        return data

    def create(self, validated_data):
        # The create validation is now handled in the validate method
        return super().create(validated_data)
    
class ApartmentSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apartment
        fields = ['id', 'number', 'name', 'inService', 'cleaned', 'apartmentType', 'price', 'currency']

class UserSerializer(serializers.ModelSerializer):
    properties_assigned = PropertySimpleSerializer(many=True, read_only=True)
    fullName = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'fullName', 'email', 'role', 'phone', 'properties_assigned', 'password', 'department', 'is_active', 'created_at']
        read_only_fields = ['id', 'role']
    def get_fullName(self, obj):
        return f'{obj.first_name} {obj.last_name}'
     
class GuestSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    current_apartment = serializers.SerializerMethodField()
    booking_count = serializers.SerializerMethodField()

    class Meta:
        model = Guest
        fields = ['id', 'user', 'current_apartment', 'booking_count', 'idCard']
        read_only_fields = fields

    def get_current_apartment(self, obj):
        return obj.current_apartment()

    def get_booking_count(self, obj):
        return obj.num_of_bookings()

class BookingUpdateSerializer(serializers.ModelSerializer):
    # Guest fields (make them optional for updates)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    phone = serializers.CharField(write_only=True, required=False)
    idCard = serializers.JSONField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Booking
        fields = [
            "apartment", "startDate", "endDate", "status",
            "first_name", "last_name", "phone", "email", "idCard"
        ]
    
    def validate_idCard(self, value):
        if not value:  # Handle None or empty values
            return None
            
        if not isinstance(value, dict):
            raise serializers.ValidationError("idCard must be a JSON object.")
            
        url = value.get("url")
        if not url:
            raise serializers.ValidationError("idCard must contain a 'url' key.")
            
        if not url.startswith("https://") or "s3" not in url:
            raise serializers.ValidationError("Invalid S3 URL for idCard.")
            
        return value
    
    def validate(self, attrs):
        start_date = attrs.get("startDate")
        end_date = attrs.get("endDate")
        apartment = attrs.get("apartment")
        status = attrs.get("status")
        
        if status == "checked_in" and start_date > timezone.now():
            raise serializers.ValidationError("You cannont Check In when start date is in the future.")
        # Validate dates
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError("End date must be after start date.")
            
            # Check for overlapping bookings
            if apartment:
                overlapping_bookings = Booking.objects.filter(
                    apartment=apartment,
                    startDate__lt=end_date,
                    endDate__gt=start_date
                ).exclude(status__in = ['cancelled', 'active', 'checked_out'])  # Exclude cancelled bookings
                
                if self.instance:  # For updates, exclude current booking
                    overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)
                
                if overlapping_bookings.exists():
                    raise serializers.ValidationError(
                        f"This apartment is already booked from {start_date} to {end_date}."
                    )

        return attrs
    
    def update(self, instance, validated_data):
        request = self.context.get("request")
        
        # Track who checked out the booking
        if request and hasattr(request, "user"):
            new_status = validated_data.get("status")
            current_status = instance.status
            
            # If status is being changed to "checked_out", set the check_out user
            if new_status == "checked_out" and current_status != "checked_out":
                validated_data["check_out_by_user_id"] = request.user
            
            # If status is being changed from "checked_out" to something else, clear the check_out user
            elif new_status != "checked_out" and current_status == "checked_out":
                validated_data["check_out_by_user_id"] = None
        
        # Update booking fields
        instance.apartment = validated_data.get('apartment', instance.apartment)
        instance.startDate = validated_data.get('startDate', instance.startDate)
        instance.endDate = validated_data.get('endDate', instance.endDate)
        instance.status = validated_data.get('status', instance.status)
        instance.check_out_by_user_id = validated_data.get('check_out_by_user_id', instance.check_out_by_user_id)
        if  instance.apartment:
            result = Apartment.objects.get(id= instance.apartment.id)
            instance.guest.user.properties_assigned.set([result.property_assigned])
        # Handle guest data updates (only if provided)
        guest_data_provided = any(key in validated_data for key in ['first_name', 'last_name', 'phone', 'email', 'idCard'])
        
        if guest_data_provided:
            guest = instance.guest
            user = guest.user
            
            # Update user fields if provided
            if 'first_name' in validated_data:
                user.first_name = validated_data['first_name']
            if 'last_name' in validated_data:
                user.last_name = validated_data['last_name']
            if 'phone' in validated_data:
                user.phone = validated_data['phone']
            if 'email' in validated_data:
                user.email = validated_data['email']
            
            user.save()
            
            # Update guest ID card if provided
            if 'idCard' in validated_data:
                guest.idCard = validated_data['idCard']
                guest.save()
        
        instance.save()
        return instance

class BookingListSerializer(serializers.ModelSerializer):
    apartment = ApartmentSerializer(read_only=True)
    guest = GuestSerializer(read_only=True)
    added_by_user = UserSerializer(source='added_by_user_id', read_only=True)
    duration = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'apartment',
            'guest',
            'dateOfReservation',
            'startDate',
            'endDate',
            'duration',
            'added_by_user',
            'status',
            'totalPrice',
            'updated_at'
        ]
        read_only_fields = fields

    def get_duration(self, obj):
        """Calculate duration in days with safety checks"""
        try:
            total_hours = (obj.endDate - obj.startDate).total_seconds() / 3600
            duration_days = math.ceil(total_hours / 24)
            return duration_days
        except (AttributeError, TypeError):
            return None
        
    def get_totalPrice(self, obj):
        """Calculate total price with safety checks"""
        try:
            if obj.apartment and obj.apartment.price:
                # Calculate total hours and round up to full days
                total_hours = (obj.endDate - obj.startDate).total_seconds() / 3600
                duration_days = math.ceil(total_hours / 24)
                total_price = duration_days * obj.apartment.price
                return round(total_price, 2)
            return None
        except (AttributeError, TypeError):
            return None

class BookingCreateSerializer(serializers.ModelSerializer):
    # Guest fields
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    phone = serializers.CharField(write_only=True)
    idCard = serializers.JSONField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Booking
        fields = [
            "apartment", "startDate", "endDate", "dateOfReservation", "status", "added_by_user_id",
            "first_name", "last_name", "phone", "email", "idCard"
        ]
    
    def validate_idCard(self, value):
        if not value:  # Handle None or empty values
            return None
            
        if not isinstance(value, dict):
            raise serializers.ValidationError("idCard must be a JSON object.")
            
        url = value.get("url")
        if not url:
            raise serializers.ValidationError("idCard must contain a 'url' key.")
            
        if not url.startswith("https://") or "s3" not in url:
            raise serializers.ValidationError("Invalid S3 URL for idCard.")
            
        return value
    
    def validate(self, attrs):
        start_date = attrs.get("startDate")
        end_date = attrs.get("endDate")
        apartment = attrs.get("apartment")
        status = attrs.get("status")
        # Validate dates
        if status == "checked_in" and start_date > timezone.now():
            raise serializers.ValidationError("You cannont Check In when start date is in the future.")
        
        if status == "upcoming" and start_date < timezone.now():
            raise serializers.ValidationError("You cannont Upcoming when start date is in the past.")
        
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError("End date must be after start date.")
            
            # Check for overlapping bookings
            if apartment:
                overlapping_bookings = Booking.objects.filter(
                    apartment=apartment,
                    startDate__lt=end_date,
                    endDate__gt=start_date
                ).exclude(status__in = ['cancelled', 'active', 'checked_out'])  # Exclude cancelled bookings
                
                if self.instance:  # For updates, exclude current booking
                    overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)
                
                if overlapping_bookings.exists():
                    raise serializers.ValidationError(
                        f"This apartment is already booked from {start_date} to {end_date}."
                    )

        return attrs
    
    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["added_by_user_id"] = request.user
            if validated_data.get("status") == "checked_in":
                validated_data["check_in_by_user_id"] = request.user
            else:
                validated_data["check_in_by_user_id"] = None
                           
        # Extract guest data
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        phone = validated_data.pop("phone")
        id_card = validated_data.pop("idCard", None)  # Made optional with default None
        email = validated_data.pop("email")
        apartment = validated_data.get("apartment")

        # Generate username (handle potential duplicates)
        base_username = f"{first_name.lower()}{last_name.lower()}"
        
        try:
            # If we get here, either:
            # 1. User doesn't exist, or
            # 2. Phone and email match an existing user
            user = User.objects.get(Q(phone=phone) | Q(email=email) | Q(username=base_username))
            guest = Guest.objects.get(user=user)
            
            if id_card:  # Update ID card if provided
                guest.idCard = id_card
                guest.save()

        except User.DoesNotExist:
            # Create new user logic
            password = f"{first_name}{last_name}"
            user = User.objects.create(
                username=base_username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role="guest",
                is_active=True,
                password=make_password(password),
            )
            if apartment:
                result = Apartment.objects.get(id=apartment.id)
                user.properties_assigned.set([result.property_assigned])
            guest = Guest.objects.create(user=user, idCard=id_card)
            
        # Create booking
        booking = Booking.objects.create(
            guest=guest,
            **validated_data
        )

        return booking