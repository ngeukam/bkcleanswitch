from rest_framework import serializers
from PropertyServices.models import Property
from UserServices.models import User
from TaskServices.models import Task, TaskGallerie, TaskTemplate
from ApartmentServices.Serializers import ApartmentSimpleSerializer
from ApartmentServices.models import Apartment
from cleanswitch.Helpers import createParsedCreatedAtUpdatedAt
from PropertyServices.Serializers import PropertySimpleSerializer

class TaskSerializer(serializers.ModelSerializer):
    property_info = PropertySimpleSerializer(read_only=True, source='property_assigned')
    class Meta:
        model = Task
        fields = '__all__'
    
class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User  # Make sure to import your User model
        fields = ['id', 'username', 'first_name', 'last_name', 'department']  # Use actual User fields


class TaskTemplateSerializer(serializers.ModelSerializer):
    default_assignees = UserSimpleSerializer(many=True, read_only=True)
    default_property_name = serializers.SerializerMethodField()
    default_apartment_name = serializers.SerializerMethodField()
    class Meta:
        model = TaskTemplate
        fields = ['id', 'title', 'description', 'duration', 'priority', 'active', 'default_assignees', 'default_property', 'default_apartment', 'default_property_name', 'default_apartment_name']

    def get_default_property_name(self, obj):
        return f"{obj.default_property.name} - {obj.default_property.address}" if obj.default_property else None

    def get_default_apartment_name(self, obj):
        return f"{obj.default_apartment.number} - {obj.default_apartment.name}" if obj.default_apartment else None
    
class TaskGalleriSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskGallerie
        fields = ['image', 'order']

@createParsedCreatedAtUpdatedAt
class TaskSerializerWithFilters(serializers.ModelSerializer):
    gallery_images = TaskGalleriSerializer(many=True, read_only=True, source='gallery_task')
    due_date = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    assigned_to = UserSimpleSerializer(many=True, read_only=True)
    property_assigned = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    apartment_assigned = serializers.PrimaryKeyRelatedField(queryset=Apartment.objects.all())
    property_info = PropertySimpleSerializer(read_only=True, source='property_assigned')
    apartment_info = ApartmentSimpleSerializer(read_only=True, source='apartment_assigned')
    added_by_user_id = serializers.SerializerMethodField()
    assigned_to_names = serializers.SerializerMethodField()
    property_assigned_name = serializers.SerializerMethodField()
    apartment_assigned_name = serializers.SerializerMethodField()
    template = TaskTemplateSerializer(read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=TaskTemplate.objects.all(),
        source='template',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'due_date', 'duration', 'status', 'priority', 'notes', 
            'assigned_to', 'assigned_to_names', 'apartment_assigned', 'gallery_images', 'active',
            'apartment_assigned_name', 'apartment_info', 'added_by_user_id', 'created_at', 
            'updated_at', 'template', 'template_id', 'assigned_to_names',
            'property_assigned', 'property_assigned_name', 'property_info'
        ]

    def get_assigned_to_names(self, obj):
        return [f"{user.first_name} {user.last_name} ({user.department})" for user in obj.assigned_to.all()]

    def get_property_assigned_name(self, obj):
        return f"{obj.property_assigned.name} - {obj.property_assigned.address}" if obj.property_assigned else None
    
    def get_apartment_assigned_name(self, obj):
        return f"{obj.apartment_assigned.number} - {obj.apartment_assigned.name}" if obj.apartment_assigned else None

    def get_added_by_user_id(self, obj):
        if obj.added_by_user_id:
            return obj.added_by_user_id.username
        return None
