import math
from rest_framework import serializers
from ApartmentServices.models import Booking
from ApartmentServices.Serializers import ApartmentSerializer, BookingCreateSerializer
from cleanswitch.Helpers import createParsedCreatedAtUpdatedAt
from PropertyServices.Serializers import PropertySimpleSerializer
from .models import Guest, PayRule, Salary, StaffSchedule, User
from django.utils import timezone

class PayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayRule
        fields = '__all__'
        
        
class UserSerializer(serializers.ModelSerializer):
    properties_assigned = PropertySimpleSerializer(many=True, read_only=True)
    fullName = serializers.SerializerMethodField()
    payrules = PayRuleSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 
                  'fullName', 'email', 'role', 'phone', 
                  'properties_assigned', 'password', 'department', 
                  'is_active', 'created_at', 'currency', 'payrules',
                  ]
        read_only_fields = ['id', 'role']
    def get_fullName(self, obj):
        return obj.get_full_name()
    
@createParsedCreatedAtUpdatedAt
class UserSerializerWithFilters(serializers.ModelSerializer):
    date_joined=serializers.DateTimeField(format="%dth %B %Y, %H:%M", read_only=True)
    properties_assigned = PropertySimpleSerializer(many=True, read_only=True)
    added_by_user = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'department', 'phone', 'properties_assigned', 'date_joined', 'created_at', 'updated_at', 'added_by_user', 'is_active']

    def get_added_by_user(self, obj):
        if obj.added_by_user_id:
            return obj.added_by_user_id.username
        return None
    
class StaffScheduleSerializer(serializers.ModelSerializer):
    staff = UserSerializer(read_only=True)
    fullName = serializers.SerializerMethodField()
    class Meta:
        model = StaffSchedule
        fields = '__all__'
    def get_fullName(self, obj):
        return obj.staff.get_full_name()
    
class UserPlanningSerializer(serializers.ModelSerializer):
    fullName = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'fullName', 'department']
    
    def get_fullName(self, obj):
        return obj.get_full_name()

class SalarySerializer(serializers.ModelSerializer):
    user_role = serializers.SerializerMethodField()
    user_fullName = serializers.SerializerMethodField()
    user_property = serializers.SerializerMethodField()
    user_currency = serializers.SerializerMethodField()
    class Meta:
        model = Salary
        fields = '__all__'

    def get_user_fullName(self, obj):
        return obj.user.get_full_name()
    
    def get_user_role(self, obj):
        return f'{obj.user.role}'
    
    def get_user_property(self, obj):
        return f'{obj.property.name} - {obj.property.address}'
    
    def get_user_currency(self, obj):
        return f'{obj.user.currency}'

class SalaryStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salary
        fields = ["status"]

    def validate_status(self, value):
        instance = self.instance
        if instance.status == "paid":
            raise serializers.ValidationError("Salary is already paid. You cannot update it again.")
        if value != "paid":
            raise serializers.ValidationError("Status can only be updated to 'paid'.")
        return value

    def update(self, instance, validated_data):
        instance.status = "paid"
        instance.paid_at = timezone.now()
        instance.save()
        return instance
    

class GuestListSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    recent_bookings = serializers.SerializerMethodField()
    booking_count = serializers.SerializerMethodField()

    class Meta:
        model = Guest
        fields = ['id', 'user', 'recent_bookings', 'booking_count']
        read_only_fields = fields

    def get_recent_bookings(self, obj):
        recent_bookings = Booking.objects.filter(guest=obj).order_by('-startDate')[:5]
        return BookingSerializer(recent_bookings, many=True).data

    def get_booking_count(self, obj):
        return obj.num_of_bookings()

class BookingSerializer(serializers.ModelSerializer):
    apartments = ApartmentSerializer(many=True, read_only=True)
    added_by_user = UserSerializer(source='added_by_user_id', read_only=True)
    duration = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'apartments',  # Changed from apartment to apartments
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
        try:
            total_hours = (obj.endDate - obj.startDate).total_seconds() / 3600
            duration_days = math.ceil(total_hours / 24)
            return duration_days
        except (AttributeError, TypeError):
            return None
        
    def get_totalPrice(self, obj):
        try:
            # Calculate total price for all apartments
            total_price = 0
            for apartment in obj.apartments.all():
                if apartment and apartment.price:
                    total_hours = (obj.endDate - obj.startDate).total_seconds() / 3600
                    duration_days = math.ceil(total_hours / 24)
                    total_price += duration_days * apartment.price
            return round(total_price, 2) if total_price > 0 else None
        except (AttributeError, TypeError):
            return None
        
    
class GuestDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    id_card_url = serializers.SerializerMethodField()
    booking_stats = serializers.SerializerMethodField()
    recent_bookings = serializers.SerializerMethodField()
    booking_count = serializers.SerializerMethodField()

    class Meta:
        model = Guest
        fields = [
            'id', 'user', 'id_card_url', 'booking_stats', 'recent_bookings', 'booking_count'
        ]
        read_only_fields = fields

    def get_id_card_url(self, obj):
        if obj.idCard and isinstance(obj.idCard, dict):
            return obj.idCard.get('url')
        return None

    def get_booking_stats(self, obj):
        return {
            'total_bookings': obj.num_of_bookings(),
            'total_days_stayed': obj.total_days_stayed(),
            'last_booking_duration': obj.last_booking_days(),
        }

    def get_recent_bookings(self, obj):
        recent_bookings = Booking.objects.filter(guest=obj).order_by('-startDate')[:5]
        return BookingSerializer(recent_bookings, many=True).data
    
    def get_booking_count(self, obj):
        return obj.num_of_bookings()


class GuestCreateUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    phone = serializers.CharField(write_only=True)
    id_card = serializers.JSONField(write_only=True, required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Guest
        fields = [
            'first_name', 'last_name', 'email', 'phone', 
            'id_card', 'password'
        ]

    def validate_id_card(self, value):
        if len(value) == 0:
            return None
            
        if not isinstance(value, dict):
            raise serializers.ValidationError("idCard must be a JSON object.")
        url = value.get("url")
        if not url:
            raise serializers.ValidationError("idCard must contain a 'url' key.")
        if not url.startswith("https://") or "s3" not in url:
            raise serializers.ValidationError("Invalid S3 URL for idCard.")
        return value

    def create(self, validated_data):
        # Create User first
        user_data = {
            'username': f"{validated_data['first_name'].lower()}{validated_data['last_name'].lower()}",
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
            'email': validated_data['email'],
            'phone': validated_data['phone'],
            'role': 'guest',
        }

        # Set password if provided, otherwise use default
        password = validated_data.get('password', 
            f"{validated_data['first_name']}{validated_data['last_name']}")

        user = User.objects.create_user(**user_data, password=password, added_by_user_id=self.context['request'].user)

        # Create Guest
        guest = Guest.objects.create(
            user=user,
            idCard=validated_data.get('id_card')
        )

        return guest

    def update(self, instance, validated_data):
        user = instance.user

        # Update User fields
        user_fields = ['first_name', 'last_name', 'email', 'phone']
        for field in user_fields:
            if field in validated_data:
                setattr(user, field, validated_data[field])

        if 'password' in validated_data:
            user.set_password(validated_data['password'])

        user.save()

        # Update Guest fields
        if 'id_card' in validated_data:
            instance.idCard = validated_data['id_card']
            instance.save()

        return instance