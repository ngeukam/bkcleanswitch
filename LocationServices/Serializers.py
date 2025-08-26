from rest_framework import serializers
from .models import StaffLocation

class StaffLocationSerializer(serializers.ModelSerializer):
    is_on_duty = serializers.BooleanField(source='isOnDuty')

    class Meta:
        model = StaffLocation
        fields = ['latitude', 'longitude', 'is_on_duty']
        read_only_fields = ['timestamp']

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
        
    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value