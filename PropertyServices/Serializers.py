from rest_framework import serializers
from cleanswitch.Helpers import createParsedCreatedAtUpdatedAt
from .models import Property

@createParsedCreatedAtUpdatedAt
class PropertySerializer(serializers.ModelSerializer):
    added_by_user_id = serializers.SerializerMethodField()
    class Meta:
        model = Property
        fields = ['id', 'name', 'address','latitude', 'longitude', 'distance', 'added_by_user_id', 'is_active', 'created_at', 'updated_at']
        
    def get_added_by_user_id(self, obj):
        if obj.added_by_user_id:
            return obj.added_by_user_id.username
        return None
    
class PropertySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'distance']