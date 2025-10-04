from rest_framework import serializers
from PropertyServices.models import Property
from UserServices.models import User
from TaskServices.models import Task, TaskGallerie, TaskTemplate
from ApartmentServices.Serializers import ApartmentSimpleSerializer
from ApartmentServices.models import Apartment
from cleanswitch.Helpers import createParsedCreatedAtUpdatedAt
from PropertyServices.Serializers import PropertySimpleSerializer
from django.utils import timezone
from datetime import timedelta

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
    default_apartments = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Apartment.objects.all(), 
        required=False
    )
    default_apartment_names = serializers.SerializerMethodField()
    class Meta:
        model = TaskTemplate
        fields = ['id', 'title', 'description', 'duration', 'priority', 'active', 'default_assignees', 'default_property', 'default_apartments', 'default_property_name', 'default_apartment_names']

    def get_default_property_name(self, obj):
        return f"{obj.default_property.name} - {obj.default_property.address}" if obj.default_property else None

    def get_default_apartment_names(self, obj):
        # Return list of apartment names instead of single apartment name
        return [
            f"#{apartment.number} - {apartment.name}" 
            for apartment in obj.default_apartments.all()
        ] if obj.default_apartments.exists() else []
        
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
    property_info = PropertySimpleSerializer(read_only=True, source='property_assigned')

    # 🔹 Many-to-Many Apartments
    apartments_assigned = serializers.PrimaryKeyRelatedField(
        queryset=Apartment.objects.all(),
        many=True,
        required=False
    )
    apartments_info = ApartmentSimpleSerializer(read_only=True, many=True, source='apartments_assigned')

    added_by_user_id = serializers.SerializerMethodField()
    assigned_to_names = serializers.SerializerMethodField()
    property_assigned_name = serializers.SerializerMethodField()
    apartments_assigned_names = serializers.SerializerMethodField()

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
            'assigned_to', 'assigned_to_names',
            'apartments_assigned', 'apartments_assigned_names', 'apartments_info',
            'gallery_images', 'active',
            'property_assigned', 'property_assigned_name', 'property_info',
            'added_by_user_id', 'created_at', 'updated_at',
            'template', 'template_id',
        ]

    def get_assigned_to_names(self, obj):
        return [f"{user.first_name} {user.last_name} ({user.department})" for user in obj.assigned_to.all()]

    def get_property_assigned_name(self, obj):
        return f"{obj.property_assigned.name} - {obj.property_assigned.address}" if obj.property_assigned else None
    
    def get_apartments_assigned_names(self, obj):
        return [f"{apt.number} - {apt.name}" for apt in obj.apartments_assigned.all()]

    def get_added_by_user_id(self, obj):
        return obj.added_by_user_id.username if obj.added_by_user_id else None

class TaskCalendarSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    assignees_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'start', 'end', 'color', 'type',
            'status', 'priority', 'assignees_info', 'property_assigned'
        ]
    
    def get_title(self, obj):
        return f"Task: {obj.title}"
    
    def get_start(self, obj):
        # Use due_date for tasks, fallback to created_at
        # if obj.due_date:
        return obj.due_date.isoformat()
        # return obj.created_at.isoformat() if obj.created_at else timezone.now().isoformat()
    
    def get_end(self, obj):
        # For tasks, end time is start time + duration (if available)
        if obj.due_date and obj.duration:
            end_time = obj.due_date + timedelta(minutes=float(obj.duration))
            return end_time.isoformat()
        elif obj.due_date:
            end_time = obj.due_date
            return end_time.isoformat()
        return None
    
    def get_color(self, obj):
        priority_colors = {
            'high': '#f44336',    # Red
            'medium': '#ff9800',  # Orange
            'low': '#4caf50',     # Green
        }
        return priority_colors.get(obj.priority, '#757575')
    
    def get_type(self, obj):
        return 'task'
    
    def get_assignees_info(self, obj):
        return [{
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'department': user.department
        } for user in obj.assigned_to.all()]
