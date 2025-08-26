# views.py
from rest_framework import exceptions 
from TaskServices.Serializers import TaskSerializer, TaskSerializerWithFilters, TaskTemplateSerializer
from rest_framework import permissions
from rest_framework.response import Response
from TaskServices.models import Task, TaskGallerie, TaskTemplate
from rest_framework import status, generics
from rest_framework.views import APIView
from ApartmentServices.models import Apartment
from cleanswitch.Helpers import CommonListAPIMixinWithFilter, CustomPageNumberPagination
from cleanswitch.permissions import IsAdminOrManager

class TaskListCreateAPIView(generics.ListCreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializerWithFilters
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        assigned_to = self.request.query_params.get('assigned_to')
        
        # Filter by template if needed
        template_id = self.request.query_params.get('template_id')
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        
        if assigned_to and user.role in ["technical", "cleaning"]:
            queryset = queryset.filter(assigned_to__id=assigned_to, property_assigned__is_active=True, active=True)
        elif user.role == "manager":
            queryset = queryset.filter(property_assigned__is_active=True)
        elif user.role == "admin" or user.is_superuser == True:
            queryset = queryset.all()
        elif user.role == "receptionist":
            queryset = queryset.filter(
                property_assigned__in=user.properties_assigned.all(),
                property_assigned__is_active=True,
                active=True,
            )
        else:
            queryset = queryset.none()

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ["admin", "manager", "receptionist"]:
            return Response(
                {"message": "Only admins and managers can create tasks."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        template_id = self.request.data.get('template_id')
        template = TaskTemplate.objects.filter(id=template_id).first() if template_id else None
        
        # Save the task first
        task = serializer.save(
            added_by_user_id=user,
            template=template
        )
        
        # Handle assigned_to - use template's default assignees if none provided
        assigned_to_ids = self.request.data.get('assigned_to', [])
        if not assigned_to_ids and template:
            assigned_to_ids = list(template.default_assignees.values_list('id', flat=True))
        
        if assigned_to_ids:
            task.assigned_to.set(assigned_to_ids)
        
        apartmentId = self.request.data.get('apartment_assigned')
        if(apartmentId):
            Apartment.objects.filter(id=apartmentId).update(cleaned=False)
    
    @CommonListAPIMixinWithFilter.common_list_decorator(TaskSerializerWithFilters)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class TaskTemplateListCreateAPIView(generics.ListCreateAPIView):
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user        
        if user.role == "manager":
            queryset = queryset.filter(active=True)
        elif user.role == "admin":
            queryset = queryset = queryset.all()
        return queryset
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ["admin", "manager"]:
            return Response(
                {"message": "Only admins and managers can create task templates."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        template = serializer.save()
        
        # Handle default assignees
        default_assignees_ids = self.request.data.get('default_assignees', [])
        if default_assignees_ids:
            template.default_assignees.set(default_assignees_ids)
    
    @CommonListAPIMixinWithFilter.common_list_decorator(TaskTemplateSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
            
class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializerWithFilters
    pagination_class = None
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), IsAdminOrManager(),]
        else:
            return [permissions.IsAuthenticated()]
        
    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        
        # Permission checks (keep your existing ones)
        if not (request.user in task.assigned_to.all() or request.user == task.added_by_user_id):
            return Response({'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        if task.status == 'completed':
            return Response({'message': 'Completed tasks cannot be modified.'}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get('status')
        if task.status == 'pending' and new_status == 'completed':
            return Response({'message': 'Cannot complete a pending task without progress.'},
                            status=status.HTTP_400_BAD_REQUEST)

        taskStatus = self.request.data.get('status')
        apartmentId = self.request.data.get('apartment_assigned')
        if(taskStatus == 'completed' and apartmentId):
            Apartment.objects.filter(id=apartmentId).update(cleaned=True)
        # Handle gallery images separately
        gallery_images = request.data.pop('gallery_images', None)
        
        # Perform the standard update first
        
        response = super().partial_update(request, *args, **kwargs)
        # If there are gallery images to process
        if gallery_images and response.status_code == status.HTTP_200_OK:
            try:
                # Clear existing gallery images if needed
                # task.gallery_task.all().delete()
                
                # Create new gallery images
                for img_data in gallery_images:
                    TaskGallerie.objects.create(
                        task=task,
                        image=img_data['image'],
                        order=img_data.get('order', 0)
                    )
                
                # Get the updated task with new gallery images
                serializer = self.get_serializer(task)
                response.data = serializer.data
            except Exception as e:
                return Response(
                    {'message': f'Error saving gallery images: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return response

            
    def perform_destroy(self, instance):
        # if instance.status == 'completed':
        #     raise exceptions.PermissionDenied("Completed tasks cannot be deleted.")
        
        if not (self.request.user.role == 'admin' or 
            (self.request.user.role == 'manager' and 
                instance.property_assigned.added_by_user_id == self.request.user)):
            raise exceptions.PermissionDenied("You don't have permission to delete this task.")
        instance.delete()

class TaskTemplateRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer
    pagination_class = None
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), IsAdminOrManager(),]
        else:
            return [permissions.IsAuthenticated()]
    
    def perform_destroy(self, instance):
        if not (self.request.user.role == 'admin' or self.request.user.role == 'manager'):
            raise exceptions.PermissionDenied("You don't have permission to delete this task template.")
        instance.delete()

class TaskStatusUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'message': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user is assigned to task or is creator
        if not (request.user in task.assigned_to.all() or request.user == task.added_by_user_id):
            return Response({'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        if task.status == 'completed':
            return Response({'message': 'Completed tasks cannot be modified'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Prevent direct jumps from pending to completed
        if (task.status == 'pending' and 
            request.data.get('status') == 'completed'):
            return Response({'message': 'Cannot complete a pending task without progress'},
                          status=status.HTTP_400_BAD_REQUEST)

        serializer = TaskSerializer(task, data=request.data, partial=True, 
                                  context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)