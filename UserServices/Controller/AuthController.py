from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth import update_session_auth_hash
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError, transaction


class LoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            properties = user.properties_assigned.all().values('id', 'name')
            access['role'] = user.role
            access['username'] = user.username
            access['first_name'] = user.first_name
            access['last_name'] = user.last_name
            access['email'] = user.email
            access['phone'] = user.phone
            access['department'] = user.department
            access['user_id'] = user.id
            access['properties_assigned'] = list(properties)
            return Response({
                'refresh': str(refresh),
                'access': str(access),
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


# class ChangePasswordAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def patch(self, request):
#         user = request.user
#         current_password = request.data.get('current_password')
#         new_password = request.data.get('new_password')

#         if not user.check_password(current_password):
#             return Response(
#                 {'message': 'Current password is incorrect'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         user.set_password(new_password)
#         user.save()
#         update_session_auth_hash(request, user)  # Keep user logged in
        
#         return Response({'message': 'Password updated successfully'})
    
class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        data = request.data

        required_fields = ['current_password', 'new_password', 'confirm_password']
        if not all(field in data for field in required_fields):
            return Response(
                {'message': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )

        current_password = data['current_password']
        new_password = data['new_password']
        confirm_password = data['confirm_password']

        # Validate passwords
        if new_password != confirm_password:
            return Response(
                {'message': 'New passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'message': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify current password
        if not user.check_password(current_password):
            return Response(
                {'message': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                user.set_password(new_password)
                user.save()
                
                # Update session auth hash to prevent logout
                update_session_auth_hash(request, user)
                
                return Response(
                    {'message': 'Password updated successfully'},
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )