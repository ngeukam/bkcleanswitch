from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from LocationServices.Serializers import StaffLocationSerializer
from LocationServices.models import StaffLocation
from UserServices.models import User

class StaffLocationListCreate(generics.ListCreateAPIView):
    serializer_class = StaffLocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = get_object_or_404(User, id=self.request.query_params.get('staff_id'))
        return StaffLocation.objects.filter(staff=user).order_by('-timestamp')
    
    def perform_create(self, serializer):
        serializer.save(staff=self.request.user)

class ClockInOutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        # Add the user to the data
        request.data['staff'] = request.user.id
        serializer = StaffLocationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        staff = request.user
        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']
        
        try:
            with transaction.atomic():
                last_status = StaffLocation.objects.filter(
                    staff=staff,
                    is_active=True
                ).order_by('-timestamp').first()
                
                # Handle first-time user (no existing records)
                if last_status is None:
                    # First time clocking in
                    new_status = True
                    message = 'First clock-in successful'
                elif last_status.isOnDuty:
                    # Clock out
                    new_status = False
                    message = 'Clocked out successfully'
                else:
                    # Clock in
                    new_status = True
                    message = 'Clocked in successfully'
                
                # Create new status record
                StaffLocation.objects.create(
                    staff=staff,
                    latitude=latitude,
                    longitude=longitude,
                    isOnDuty=new_status,
                    is_active=True
                )
                
                # Deactivate all previous records (if any exist)
                # StaffLocation.objects.filter(
                #     staff=staff,
                #     is_active=True
                # ).exclude(id=new_record.id).update(is_active=False)
                
                return Response({'status': message}, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# class ClockInOutAPIView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request, *args, **kwargs):
#         request.data['staff'] = request.user.id
#         serializer = StaffLocationSerializer(data=request.data)
        
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         staff = request.user
#         user_latitude = serializer.validated_data['latitude']
#         user_longitude = serializer.validated_data['longitude']
#         user_point = Point(user_longitude, user_latitude, srid=4326)
        
#         try:
#             with transaction.atomic():
#                 # Get the property associated with this user
#                 try:
#                     property = Property.objects.get(
#                         added_by_user_id=staff,
#                         is_active=True
#                     )
#                 except Property.DoesNotExist:
#                     return Response(
#                         {'error': 'No active property found for this user'},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
                
#                 # Calculate distance between user and property
#                 property_point = Point(property.longitude, property.latitude, srid=4326)
#                 distance_meters = user_point.distance(property_point) * 100000  # Convert to meters
                
#                 if distance_meters > property.distance:
#                     return Response(
#                         {
#                             'error': f'You are too far from the property. '
#                                     f'Maximum allowed distance: {property.distance}m, '
#                                     f'Your distance: {distance_meters:.2f}m'
#                         },
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
                
#                 last_status = StaffLocation.objects.filter(
#                     staff=staff,
#                     is_active=True
#                 ).order_by('-timestamp').first()
                
#                 if last_status is None:
#                     new_status = True
#                     message = 'First clock-in successful'
#                 elif last_status.isOnDuty:
#                     new_status = False
#                     message = 'Clocked out successfully'
#                 else:
#                     new_status = True
#                     message = 'Clocked in successfully'
                
#                 StaffLocation.objects.create(
#                     staff=staff,
#                     latitude=user_latitude,
#                     longitude=user_longitude,
#                     isOnDuty=new_status,
#                     is_active=True
#                 )
                
#                 return Response({
#                     'status': message,
#                     'distance_from_property': f'{distance_meters:.2f}m'
#                 }, status=status.HTTP_200_OK)
                
#         except Exception as e:
#             return Response(
#                 {'error': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class CurrentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, id=request.query_params.get('staff_id'))
        last_status = StaffLocation.objects.filter(
            staff=user,
            is_active=True
        ).order_by('-timestamp').first()
        if not last_status:
            return Response({'status': 'No active status found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = StaffLocationSerializer(last_status)
        return Response(serializer.data)