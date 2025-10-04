from collections import defaultdict
from django.shortcuts import get_object_or_404
from UserServices.Serializers import GuestCreateUpdateSerializer, GuestDetailSerializer, GuestListSerializer, SalarySerializer, SalaryStatusUpdateSerializer, StaffScheduleSerializer, UserPlanningSerializer, UserSerializer, UserSerializerWithFilters
from UserServices.models import Guest, PayRule, Salary, StaffSchedule, User
from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView, RetrieveDestroyAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from LocationServices.models import StaffLocation
from django.utils import timezone
from django.db.models import Count
from TaskServices.models import Task
from cleanswitch.Helpers import CommonListAPIMixinWithFilter, CustomPageNumberPagination
from cleanswitch.permissions import IsAdmin, IsAdminOrManager, IsReceptionist
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from UserServices.models import User
from PropertyServices.models import Property
import traceback
from rest_framework.exceptions import PermissionDenied
from datetime import date as date_today
from django.utils.dateparse import parse_date
from django.db.models import Sum


class ListUserAPIView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializerWithFilters
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if(user.role == 'admin' or user.is_superuser == True):
            queryset = User.objects.exclude(role='guest')
        else:
             queryset = User.objects.filter(
                department=user.department
            ).exclude(role='guest')
        return queryset
    @CommonListAPIMixinWithFilter.common_list_decorator(UserSerializerWithFilters)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class CreateUserAPIView(APIView):
    permission_classes = [IsAdminOrManager, IsAuthenticated]
    
    def post(self, request):
        data = request.data
        username = data.get('username').lower().strip()
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email').lower().strip()
        password = data.get('password')
        role = data.get('role')
        phone = data.get('phone')
        department = data.get('department', '')
        properties_assigned = data.get('properties_assigned')
        payType = data.get('payType', '')
        payRate = data.get('payRate', 0)
        currency = data.get('currency', '')
        user = request.user
        if(user.role == 'manager' and role in ['admin', 'super admin']):
            return Response(
                {'message': 'You cannot create admin user'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        if not all([username, first_name, last_name, password, role, phone]):
            return Response(
                {'message': 'All fields are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        current_user = request.user
        
        try:
            with transaction.atomic():
                user = User.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=make_password(password),
                    role=role,
                    phone=phone,
                    added_by_user_id=current_user,
                    department=department,
                    currency=currency
                )
                
                # Ajout des propriétés assignées
                if len(properties_assigned)>0:
                    properties = Property.objects.filter(id__in=properties_assigned)
                    user.properties_assigned.set(properties)
                    
                PayRule.objects.create(
                    user = user,
                    payType = payType,
                    payRate = payRate
                )
                return Response({
                    'message': 'User created successfully',
                    'user_id': user.id
                }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            if 'username' in str(e):
                return Response(
                    {'message': 'Username already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif 'email' in str(e):
                return Response(
                    {'message': 'Email already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif 'phone' in str(e):
                return Response(
                    {'message': 'Phone number already exists'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'message': 'Some field already exists'},  # Correction de la faute de frappe
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except ValidationError as e:
            return Response(
                {'message': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UpdateUserAPIView(APIView):
    permission_classes = [IsAdminOrManager, IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None
    
    def put(self, request, pk):
        """Full update of user"""
        return self._update_user(request, pk, partial=False)
    
    def patch(self, request, pk):
        """Partial update of user"""
        return self._update_user(request, pk, partial=True)
    
    def _update_user(self, request, pk, partial=False):
        user = self.get_object(pk)
        if not user:
            return Response(
                {'message': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        data = request.data
        serializer = UserSerializerWithFilters(user, data=data, partial=partial)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Update basic fields
                if 'username' in data:
                    user.username = data['username'].lower().strip()
                if 'first_name' in data:
                    user.first_name = data['first_name']
                if 'last_name' in data:
                    user.last_name = data['last_name']
                if 'email' in data:
                    user.email = data['email'].lower().strip()
                if 'role' in data:
                    user.role = data['role']
                if 'phone' in data:
                    user.phone = data['phone']
                if 'department' in data:
                    user.department = data['department']
                if 'currency' in data:
                    user.currency = data['currency']
                if 'payrules' in data:
                    payRate = data['payrules']['payRate']
                    payType = data['payrules']['payType']
                
                # Handle is_active field
                if 'is_active' in data:
                    user.is_active = bool(data['is_active'])
                
                # Handle password change
                if user.password == data['password']:
                    pass
                else:
                    password = data['password']
                    if password and not user.check_password(password):
                        user.set_password(password)
                
                # Handle properties assignment
                if 'properties_assigned' in data:
                    properties_assigned = data.get('properties_assigned', [])
                    properties = Property.objects.filter(id__in=properties_assigned)
                    user.properties_assigned.set(properties)
                
                user.save()
                
                PayRule.objects.filter(user_id = user.id).update(payType = payType, payRate = payRate)
                
                return Response({
                    'message': 'User updated successfully',
                    'user_id': user.id,
                    'is_active': user.is_active
                }, status=status.HTTP_200_OK)
                
        except IntegrityError as e:
            return self.handle_integrity_error(e)
        except ValidationError as e:
            return Response(
                {'message': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f'Error {"patching" if partial else "updating"} user:', e)
            return Response(
                {'message': f'An error occurred while {"patching" if partial else "updating"} user'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def handle_integrity_error(self, e):
        """Utility method to handle IntegrityError"""
        if 'username' in str(e):
            return Response(
                {'message': 'Username already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        elif 'email' in str(e):
            return Response(
                {'message': 'Email already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        elif 'phone' in str(e):
            return Response(
                {'message': 'Phone number already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'message': 'Database integrity error - some field already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
        
class RetrieveDestroyUserAPIView(RetrieveDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_object(self):
        user = super().get_object()
        request_user = self.request.user

        # For retrieve/update - users can only access their own profile
        if self.request.method in ['GET']:
            if request_user.role in ['cleaning', 'technical', 'receptionist'] and user.id != request_user.id:
                raise PermissionDenied("You can only access your own profile")
            return user

        # For delete - check permissions
        if self.request.method == 'DELETE':
            # Prevent deleting superusers (even by admin)
            if user.is_superuser:
                raise PermissionDenied("Cannot delete superuser accounts")
            
            # Admin can delete anyone except superusers
            if request_user.role == 'admin':
                return user
            
            # Manager can only delete users they created
            elif request_user.role == 'manager' and user.added_by_user_id == request_user:
                return user
            
            else:
                raise PermissionDenied("You don't have permission to delete this user")

        return user
    def perform_destroy(self, instance):
        # Add any pre-delete logic here if needed
        instance.delete()
            
class MonthlyWorkHoursAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        try:
            # Get month and year from query params (default to current month)
            month = int(datetime.now().month)
            year = int(datetime.now().year)
            
            # Validate month/year
            if month < 1 or month > 12:
                return Response(
                    {'error': 'Invalid month (1-12)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate date range for the requested month
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
           
            # Get all clock-in/out records for the user in the requested month
            records = StaffLocation.objects.filter(
                staff=request.user,
                timestamp__gte=first_day,
                timestamp__lte=last_day,
                is_active=True
            ).order_by('timestamp')
            if not records.exists():
                return Response({
                    'month': month,
                    'year': year,
                    'total_hours': 0,
                    'details': []
                })
            
            total_seconds = 0
            sessions = []
            current_session = None
            
            # Process records to calculate work sessions
            for i, record in enumerate(records):
                if record.isOnDuty:
                    # Clock-in record
                    if current_session is None:
                        current_session = {
                            'clock_in': record.timestamp,
                            'clock_out': None,
                            'duration': None
                        }
                else:
                    # Clock-out record
                    if current_session is not None and current_session['clock_out'] is None:
                        current_session['clock_out'] = record.timestamp
                        duration = (current_session['clock_out'] - current_session['clock_in']).total_seconds()
                        current_session['duration'] = duration
                        total_seconds += duration
                        
                        sessions.append({
                            'clock_in': current_session['clock_in'],
                            'clock_out': current_session['clock_out'],
                            'duration_hours': round(duration / 3600, 2)
                        })
                        
                        current_session = None
            
            # Handle case where user is currently clocked in (last record is clock-in)
            if current_session is not None:
                sessions.append({
                    'clock_in': current_session['clock_in'],
                    'clock_out': None,
                    'duration_hours': None,
                    'status': 'Currently clocked in'
                })
            
            total_hours = round(total_seconds / 3600, 2)
            return Response({
                'month': month,
                'year': year,
                'total_hours': total_hours,
                'details': sessions
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CurrentMonthTaskCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        task_counts = Task.objects.filter(
            assigned_to=request.user,
            created_at__gte=first_day
        ).values('status').annotate(
            count=Count('id')
        ).order_by('status')

        # Convert to a more usable format
        result = {
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'cancelled': 0,
        }

        for item in task_counts:
            result[item['status']] = item['count']

        return Response(result)

class RecentTasksAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get last 5 updated tasks for the current user
        tasks = Task.objects.filter(
            Q(assigned_to=request.user)
        ).order_by('-created_at')[:5]

        # Format the response
        results = []
        for task in tasks:
            time_diff = timezone.now() - task.updated_at
            if time_diff.days > 0:
                time_text = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            else:
                hours = time_diff.seconds // 3600
                if hours > 0:
                    time_text = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    minutes = (time_diff.seconds // 60) % 60
                    time_text = f"{minutes} minute{'s' if minutes > 1 else ''} ago"

            results.append({
                'id': task.id,
                'title': task.title,
                'status': task.status,
                'time_text': time_text,
                'updated_at': task.updated_at
            })

        return Response(results)

class GenerateScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    
    def post(self, request):
        # Get input data
        user = request.user
        staff_usernames = request.data.get('staff_usernames', [])
        weeks = int(request.data.get('weeks', 1))
        working_days = request.data.get('working_days', [])
        daily_hours = float(request.data.get('daily_hours', 8))
        staff_per_day = int(request.data.get('staff_per_day', 1))
        start_date_str = request.data.get('start_date')  # Content date and time
        working_hour_ranges = request.data.get('working_hour_ranges', [])
        
        # Validate input
        if not staff_usernames or not working_days:
            return Response(
                {"error": "Staff usernames and working days are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Parse start date
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else datetime.now().date()
            
            # If no working hour ranges provided, create one based on daily_hours
            if not working_hour_ranges:
                working_hour_ranges = [["08:00", f"{int(8 + daily_hours):02d}:00"]]
            
            staff_members = list(User.objects.filter(username__in=staff_usernames))
            
            if len(staff_members) != len(staff_usernames):
                missing = set(staff_usernames) - set(u.username for u in staff_members)
                return Response(
                    {"error": f"Staff not found: {', '.join(missing)}"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Verify staff_per_day doesn't exceed available time ranges
            if staff_per_day > len(working_hour_ranges):
                return Response(
                    {"error": f"Cannot assign {staff_per_day} staff per day with only {len(working_hour_ranges)} time ranges available"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate total slots and verify perfect balance is possible
            total_days = len(working_days) * weeks
            total_slots = total_days * staff_per_day
            
            if total_slots % len(staff_members) != 0:
                return Response(
                    {
                        "error": "Cannot create perfectly balanced schedule with current parameters",
                        "message": f"Total available slots ({total_slots}) cannot be evenly divided among {len(staff_members)} staff members",
                        "suggestion": {
                            "adjust_weeks": f"Try generating {weeks + 1} weeks for better balance",
                            "adjust_staff": f"Try with {len(staff_members) + 1} staff members",
                            "adjust_staff_per_day": f"Try with {staff_per_day + 1} staff per day",
                            "required_slots_per_staff": total_slots / len(staff_members)
                        }
                    },
                    status=status.HTTP_200_OK
                )

            # Clear existing schedules
            StaffSchedule.objects.filter(
                staff__in=staff_members,
                week_number__in=range(1, weeks+1)
            ).delete()

            # Generate perfectly balanced schedule
            days_map = {
                "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                "Friday": 4, "Saturday": 5, "Sunday": 6
            }
            
            staff_assignments = {staff.username: 0 for staff in staff_members}
            schedule_data = []
            
            # Create a list of all days with their time ranges
            all_days = []
            for week in range(weeks):
                for day in working_days:
                    date = self._calculate_date(start_date, week, day, days_map)
                    all_days.append({
                        "date": date,
                        "day": day,
                        "week": week + 1,
                        "time_ranges": working_hour_ranges.copy()
                    })
            
            # Assign staff to each day's time ranges
            import random
            for day_info in all_days:
                # Mélanger le staff pour CHAQUE jour pour plus de random
                daily_staff_list = staff_members.copy()
                random.shuffle(daily_staff_list)
                
                # Trier par nombre d'assignments pour mieux équilibrer
                daily_staff_list.sort(key=lambda s: staff_assignments[s.username])
                
                # For each day, assign different staff to different time ranges
                day_staff = []
                
                # Try to assign unique staff for each time range
                for i in range(staff_per_day):
                    # Trouver le staff disponible qui n'est pas déjà assigné à ce jour
                    available_staff = [s for s in daily_staff_list if s not in day_staff]
                    
                    if not available_staff:
                        # Si tout le staff est déjà assigné à ce jour, prendre celui avec le moins d'assignments
                        available_staff = daily_staff_list
                    
                    # Prendre le staff avec le moins d'assignments
                    available_staff.sort(key=lambda s: staff_assignments[s.username])
                    staff = available_staff[0]
                    day_staff.append(staff)
                    
                    # Get the time range for this slot
                    time_range_index = i % len(working_hour_ranges)
                    time_range = working_hour_ranges[time_range_index]
                    
                    # Calculate hours from time range
                    start_time = datetime.strptime(time_range[0], "%H:%M")
                    end_time = datetime.strptime(time_range[1], "%H:%M")
                    hours = (end_time - start_time).seconds / 3600
                    
                    # Save to database
                    schedule = StaffSchedule.objects.create(
                        staff=staff,
                        day=day_info["day"],
                        hours=hours,
                        week_number=day_info["week"],
                        date=day_info["date"],
                        start_time=time_range[0],
                        end_time=time_range[1],
                        added_by_user_id=user
                    )
                    schedule_data.append(schedule)
                    staff_assignments[staff.username] += 1
            
            # Verify final distribution
            final_distribution = {
                username: {
                    "total_assignments": staff_assignments[username],
                    "total_hours": staff_assignments[username] * daily_hours
                }
                for username in staff_assignments.keys()
            }
            
            # Calculate distribution by time range
            range_distribution = {}
            for time_range in working_hour_ranges:
                range_key = f"{time_range[0]}-{time_range[1]}"
                range_distribution[range_key] = {
                    staff.username: 0 for staff in staff_members
                }
            
            for schedule in schedule_data:
                range_key = f"{schedule.start_time}-{schedule.end_time}"
                range_distribution[range_key][schedule.staff.username] += 1
            
            serializer = StaffScheduleSerializer(schedule_data, many=True)
            
            return Response({
                "message": "Perfectly balanced schedule generated",
                "start_date": start_date_str,
                "weeks": weeks,
                "time_ranges": working_hour_ranges,
                "total_assignments": len(schedule_data),
                "hours_distribution": final_distribution,
                "range_distribution": range_distribution,
                "schedule": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _calculate_date(self, start_date, week, day, days_map):
        # Calculate the specific date for a given week and day
        from datetime import timedelta
        
        # Find the first occurrence of the requested day after start_date
        start_weekday = start_date.weekday()
        target_weekday = days_map[day]
        
        days_diff = (target_weekday - start_weekday) % 7
        first_occurrence = start_date + timedelta(days=days_diff)
        
        # Add weeks
        return first_occurrence + timedelta(weeks=week)

class PreviewScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    
    def post(self, request):
        # Get input data
        staff_usernames = request.data.get('staff_usernames', [])
        weeks = int(request.data.get('weeks', 1))
        working_days = request.data.get('working_days', [])
        daily_hours = float(request.data.get('daily_hours', 8))
        staff_per_day = int(request.data.get('staff_per_day', 1))
        start_date_str = request.data.get('start_date')
        working_hour_ranges = request.data.get('working_hour_ranges', [])
        
        # Validate input
        if not staff_usernames or not working_days:
            return Response(
                {"error": "Staff usernames and working days are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Parse start date
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else datetime.now().date()
            
            # If no working hour ranges provided, create one based on daily_hours
            if not working_hour_ranges:
                working_hour_ranges = [["08:00", f"{int(8 + daily_hours):02d}:00"]]
            
            staff_members = list(User.objects.filter(username__in=staff_usernames))
            
            if len(staff_members) != len(staff_usernames):
                missing = set(staff_usernames) - set(u.username for u in staff_members)
                return Response(
                    {"error": f"Staff not found: {', '.join(missing)}"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Verify staff_per_day doesn't exceed available time ranges
            if staff_per_day > len(working_hour_ranges):
                return Response(
                    {"error": f"Cannot assign {staff_per_day} staff per day with only {len(working_hour_ranges)} time ranges available"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate total slots and verify perfect balance is possible
            total_days = len(working_days) * weeks
            total_slots = total_days * staff_per_day
            
            if total_slots % len(staff_members) != 0:
                return Response(
                    {
                        "error": "Cannot create perfectly balanced schedule with current parameters",
                        "message": f"Total available slots ({total_slots}) cannot be evenly divided among {len(staff_members)} staff members",
                        "suggestion": {
                            "adjust_weeks": f"Try generating {weeks + 1} weeks for better balance",
                            "adjust_staff": f"Try with {len(staff_members) + 1} staff members",
                            "adjust_staff_per_day": f"Try with {staff_per_day + 1} staff per day",
                            "required_slots_per_staff": total_slots / len(staff_members)
                        }
                    },
                    status=status.HTTP_200_OK
                )

            # Generate perfectly balanced schedule (preview only - no database save)
            days_map = {
                "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
                "Friday": 4, "Saturday": 5, "Sunday": 6
            }
            
            staff_assignments = {staff.username: 0 for staff in staff_members}
            preview_data = []
            
            # Create a list of all days with their time ranges
            all_days = []
            for week in range(weeks):
                for day in working_days:
                    date = self._calculate_date(start_date, week, day, days_map)
                    all_days.append({
                        "date": date,
                        "day": day,
                        "week": week + 1,
                        "time_ranges": working_hour_ranges.copy()
                    })
            
            # Create staff rotation list
            staff_list = staff_members.copy()
            import random
            random.shuffle(staff_list)
            
            # Assign staff to each day's time ranges (preview only)
            for day_info in all_days:
                # Shuffle staff for each day for better randomness
                daily_staff_list = staff_members.copy()
                random.shuffle(daily_staff_list)
                
                # Sort by assignment count for better balance
                daily_staff_list.sort(key=lambda s: staff_assignments[s.username])
                
                # For each day, assign different staff to different time ranges
                day_staff = []
                
                for i in range(staff_per_day):
                    # Find available staff not already assigned to this day
                    available_staff = [s for s in daily_staff_list if s not in day_staff]
                    
                    if not available_staff:
                        # If all staff are already assigned to this day, reuse someone
                        available_staff = daily_staff_list
                    
                    # Choose staff with least assignments first
                    available_staff.sort(key=lambda s: staff_assignments[s.username])
                    staff = available_staff[0]
                    day_staff.append(staff)
                    
                    # Get the time range for this slot
                    time_range_index = i % len(working_hour_ranges)
                    time_range = working_hour_ranges[time_range_index]
                    
                    # Calculate hours from time range
                    start_time = datetime.strptime(time_range[0], "%H:%M")
                    end_time = datetime.strptime(time_range[1], "%H:%M")
                    hours = (end_time - start_time).seconds / 3600
                    
                    # Create preview data (no database save)
                    preview_data.append({
                        "staff": {
                            "id": staff.id,
                            "username": staff.username,
                            "fullName": f"{staff.first_name} {staff.last_name}",
                            "department": getattr(staff, 'department', 'N/A')
                        },
                        "day": day_info["day"],
                        "hours": hours,
                        "week_number": day_info["week"],
                        "date": day_info["date"].isoformat(),
                        "start_time": time_range[0],
                        "end_time": time_range[1],
                    })
                    
                    staff_assignments[staff.username] += 1
            
            # Calculate final distribution for preview
            final_distribution = {
                username: {
                    "total_assignments": count,
                    "total_hours": count * daily_hours
                }
                for username, count in staff_assignments.items()
            }
            
            # Calculate distribution by time range
            range_distribution = {}
            for time_range in working_hour_ranges:
                range_key = f"{time_range[0]}-{time_range[1]}"
                range_distribution[range_key] = {
                    staff.username: 0 for staff in staff_members
                }
            
            for item in preview_data:
                range_key = f"{item['start_time']}-{item['end_time']}"
                range_distribution[range_key][item['staff']['username']] += 1
            
            return Response({
                "preview": preview_data,
                "total_assignments": len(preview_data),
                "hours_distribution": final_distribution,
                "range_distribution": range_distribution,
                "message": "Schedule preview generated successfully"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    def _calculate_date(self, start_date, week, day, days_map):
        # Calculate the specific date for a given week and day
        from datetime import timedelta
        
        # Find the first occurrence of the requested day after start_date
        start_weekday = start_date.weekday()
        target_weekday = days_map[day]
        
        days_diff = (target_weekday - start_weekday) % 7
        first_occurrence = start_date + timedelta(days=days_diff)
        
        # Add weeks
        return first_occurrence + timedelta(weeks=week)
            
class StaffScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = None
    def get(self, request, pk=None):
        try:
            if pk:
                # Get schedule for specific staff member
                user = User.objects.get(pk=pk)
                schedules = StaffSchedule.objects.filter(staff=user)
            else:
                # Get all schedules (admin view)
                if request.user.role not in ['admin', 'manager', 'super admin']:
                    return Response(
                        {"message": "Only admin can view all schedules"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                schedules = StaffSchedule.objects.all()
            
            # Filter by week if provided
            week = request.query_params.get('week')
            if week:
                schedules = schedules.filter(week_number=week)
            serializer = StaffScheduleSerializer(schedules, many=True)
            return Response(serializer.data)
        
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk=None):
        try:
            if not pk:
                return Response(
                    {"message": "Schedule ID is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check permissions
            schedule = StaffSchedule.objects.get(pk=pk)
            
            # Allow deletion if:
            # 1. User is admin/manager
            # 2. User is deleting their own schedule
            # 3. User created the schedule (added_by_user)
            if not (request.user.role in ['admin', 'manager', 'super admin'] or 
                    request.user == schedule.staff or 
                    request.user.id == schedule.added_by_user_id):
                return Response(
                    {"message": "You don't have permission to delete this schedule"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            schedule.delete()
            return Response(
                {"message": "Schedule deleted successfully"},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except StaffSchedule.DoesNotExist:
            return Response(
                {"message": "Schedule not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        try:
            data = request.data
            staff_id = data.get("staff")
            date_str = data.get("date")
            day = data.get("day")
            hours = data.get("hours")
            week_number = data.get("week_number")
            start_time = data.get("start_time")
            end_time = data.get("end_time")

            if not all([staff_id, day, hours, week_number, date_str]):
                return Response(
                    {"message": "All fields are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Conversion de la chaîne en objet date
            parsed_date = parse_date(date_str)
            if not parsed_date:
                return Response(
                    {"message": "Invalid date format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Vérification si la date est dans le futur
            if parsed_date < date_today.today() :
                return Response(
                    {"message": "Date cannot be in the past"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            staff = User.objects.get(pk=staff_id)

            schedule = StaffSchedule.objects.create(
                staff=staff,
                day=day,
                hours=hours,
                week_number=week_number,
                date=parsed_date,
                start_time=start_time,
                end_time=end_time,
                added_by_user_id=request.user
            )

            serializer = StaffScheduleSerializer(schedule)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {"message": "Staff user not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StaffUsersAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    
    def get(self, request):
        """
        Get all staff users created by the currently authenticated user
        """
        try:
            
            # Filter by staff roles (excluding 'guest')
            user = request.user
            staff_roles = ['cleaning', 'technical']
            if(user.role == 'admin'):
                staff_users = User.objects.filter(role__in=staff_roles)
            else: 
                staff_users = User.objects.filter(role__in=staff_roles, department=user.department)
            # Order by creation date (newest first)
            staff_users = staff_users.order_by('-created_at')
            
            serializer = UserPlanningSerializer(staff_users, many=True)
            return Response({
                'success': True,
                'users': serializer.data,
                'count': staff_users.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CompletedTaskSalaryPreviewAPIView(APIView):
    permission_classes = [IsAdmin, IsAuthenticated]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get("start")
        end_date_str = request.query_params.get("end")
        property_id = request.query_params.get("property_id")
        
        if not start_date_str or not end_date_str:
            return Response(
                {"message": "You must provide start and end query params in YYYY-MM-DD format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"message": "Invalid date format. Use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Base filter: users with completed tasks in date range
        user_filter = Q(
            user_tasks__status="completed",
            user_tasks__updated_at__date__range=(start_date, end_date)
        )
        property_obj = None
        if property_id:
            property_obj = get_object_or_404(Property, id=property_id)
            user_filter &= Q(properties_assigned__id=property_id) & Q(
                user_tasks__property_assigned_id=property_id
            )

        completed_users = User.objects.filter(user_filter).distinct()

        results = []
        
        for user in completed_users:
            total_salary = 0

            # Salaried calculation
            salaried_total = PayRule.objects.filter(
                user=user,
                payType="salaried"
            ).aggregate(total=Sum("payRate"))["total"] or 0

            total_salary += salaried_total

            # Hourly calculation
            hourly_rule = PayRule.objects.filter(
                user=user,
                payType="hourly"
            ).first()

            if hourly_rule:
                total_hours = Task.objects.filter(
                    assigned_to=user,
                    status="completed",
                    updated_at__date__range=(start_date, end_date)
                ).aggregate(total_hours=Sum("duration")/60)["total_hours"] or 0
                total_salary += float(hourly_rule.payRate) * float(total_hours)

            # Check if salary already exists for this period (overlap)
            overlap_exists = Salary.objects.filter(
                user=user,
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exists()

            results.append({
                "user_id": user.id,
                "propertyInfo": f"{property_obj.name} - {property_obj.address}" if property_obj else None,
                "fullName": user.get_full_name(),
                "role":user.role,
                "total_salary": round(total_salary, 2),
                "currency":user.currency,
                "start_date": start_date,
                "end_date": end_date,
                "period": f"{start_date} to {end_date}",
                "overlap": overlap_exists
            })


        return Response(results, status=status.HTTP_200_OK)
    
class CompletedTaskSalarySaveAPIView(APIView):
    permission_classes = [IsAdmin, IsAuthenticated]

    def post(self, request, *args, **kwargs):
        start_date_str = request.data.get("start_date")
        end_date_str = request.data.get("end_date")
        salaries_data = request.data.get("salaries", [])
        property_id = request.data.get("property_id")
        if property_id:
            property = get_object_or_404(Property, id=property_id)
        
        if not start_date_str or not end_date_str or not salaries_data:
            return Response(
                {"message": "start_date, end_date and salaries are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"message": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        saved_records = []
        errors = []

        for salary in salaries_data:
            user_id = salary.get("user_id")
            total_salary = salary.get("total_salary")

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                errors.append({"user_id": user_id, "message": "User not found"})
                continue

            # Check for overlapping salary period
            overlap_exists = Salary.objects.filter(
                user=user,
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exists()

            if overlap_exists:
                errors.append({
                    "user_id": user_id,
                    "message": f"Salary period overlaps with an existing record for {user.last_name} {user.first_name}"
                })
                continue

            salary_entry = Salary.objects.create(
                user=user,
                property=property,
                total_salary=total_salary,
                start_date=start_date,
                end_date=end_date,
                status="pending"
            )
            saved_records.append(salary_entry.id)

        return Response({
            "saved_ids": saved_records,
            "message": errors
        }, status=status.HTTP_201_CREATED if saved_records else status.HTTP_400_BAD_REQUEST)

class SalaryPeriodsAPIView(APIView):
    permission_classes = [IsAdmin, IsAuthenticated]
    
    def get(self, request):
        periods = (
            Salary.objects
            .values("start_date", "end_date")
            .annotate(count=Count("id"))
            .order_by("-start_date")
        )

        results = [
            {
                "start_date": p["start_date"],
                "end_date": p["end_date"],
                "label": f"{p['start_date']} to {p['end_date']}",
                "count": p["count"]
            }
            for p in periods
        ]
        return Response(results, status=status.HTTP_200_OK)

class SalariesByPeriodAPIView(ListAPIView):
    queryset = Salary.objects.all()
    serializer_class = SalarySerializer
    permission_classes = [IsAdmin, IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        return Salary.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related("user", "property")
        
    @CommonListAPIMixinWithFilter.common_list_decorator(SalarySerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
class SalaryUpdateDeleteAPIView(APIView):
    permission_classes = [IsAdmin, IsAuthenticated]
    def patch(self, request, pk):
        """Partially update an object"""
        instance = get_object_or_404(Salary, pk=pk)
        serializer = SalaryStatusUpdateSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete an object"""
        instance = get_object_or_404(Salary, pk=pk)
        instance.delete()
        return Response({"detail": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class GuestSearchViewAPIView(ListAPIView):
    serializer_class = GuestListSerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if len(query) < 3:
            return Guest.objects.none()
        
        return Guest.objects.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__phone__icontains=query)
        )[:10]  #
        
class GuestRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Guest.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return GuestCreateUpdateSerializer
        else:
            return GuestDetailSerializer
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            # For DELETE, require manager or admin
            return [IsAuthenticated(), IsAdminOrManager()]
        else:
            # For GET, PUT, PATCH, use the default permissions
            return [IsAuthenticated(), IsReceptionist()]
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == ['receptionist', 'manager']:
            queryset = Guest.objects.filter(user__role='guest', user__properties_assigned__in=user.properties_assigned.all())
        elif user.role in ['admin', 'manager']:
            queryset = Guest.objects.filter(user__role='guest')
        return queryset
    
class GuestListAPIView(ListAPIView):
    serializer_class = GuestListSerializer
    queryset = Guest.objects.all()
    permission_classes = [IsAuthenticated, IsReceptionist]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == 'receptionist':
            queryset = Guest.objects.filter(user__role='guest', user__properties_assigned__in=user.properties_assigned.all())
        elif user.role in ['admin', 'manager']:
            queryset = Guest.objects.filter(user__role='guest')
        return queryset
    @CommonListAPIMixinWithFilter.common_list_decorator(GuestListSerializer)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class GuestCreateAPIView(CreateAPIView):
    serializer_class = GuestCreateUpdateSerializer
    queryset = Guest.objects.filter(user__role='guest').all()
    permission_classes = [IsAuthenticated, IsReceptionist]
    pagination_class = None