from django.urls import path, include
from UserServices.Controller import AuthController
from UserServices.Controller import  UserController
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('users/', UserController.ListUserAPIView.as_view(), name='users-list'),
    path('users/<int:pk>/', UserController.RetrieveDestroyUserAPIView.as_view(), name='retrieve-destroy-user'),
    path('auth/login/', AuthController.LoginAPIView.as_view(), name='jwt-login'),
    path('users/create/', UserController.CreateUserAPIView.as_view(), name='create-user'),
    path('users/update/<int:pk>/', UserController.UpdateUserAPIView.as_view(), name='update-user'),
    
    path('users/work-hours/monthly/', UserController.MonthlyWorkHoursAPIView.as_view(), name='monthly-work-hours'),
    path('users/tasks/current-month-counts/', UserController.CurrentMonthTaskCountAPIView.as_view(), name='current-month-task-counts'),
    path('users/tasks/recent/', UserController.RecentTasksAPIView.as_view(), name='recent-tasks'),
    path('auth/change-password/', AuthController.ChangePasswordAPIView.as_view(), name='change-password'),
    
    path('users/generate-schedule/', UserController.GenerateScheduleAPIView.as_view(), name='generate-schedule'),
    path('users/schedules/', UserController.StaffScheduleAPIView.as_view(), name='all-schedules'),
    path('users/schedules/<int:pk>/', UserController.StaffScheduleAPIView.as_view(), name='staff-schedule'),
    path('users/staff/', UserController.StaffUsersAPIView.as_view(), name='users-staff'),
    path('users/preview-schedule/', UserController.PreviewScheduleAPIView.as_view(), name='preview-schedule'),
    
    path("salaries/completed-tasks/preview/", UserController.CompletedTaskSalaryPreviewAPIView.as_view(), name='salaries-preview'),
    path("salaries/completed-tasks/save/", UserController.CompletedTaskSalarySaveAPIView.as_view(), name='salaries-save'),
    path("salaries/periods/", UserController.SalaryPeriodsAPIView.as_view(), name='salary-period'),
    path("salaries/by-period/", UserController.SalariesByPeriodAPIView.as_view(), name='salaries-period'),
    path("salaries/<int:pk>/", UserController.SalaryUpdateDeleteAPIView.as_view(), name='salary-update'),
    
    path("guests/search", UserController.GuestSearchViewAPIView.as_view(), name='guest-search'),
    path("guests/<int:pk>/", UserController.GuestRetrieveUpdateDestroyAPIView.as_view(), name='guest-retrieve-update-destroy'),
    path("guests/", UserController.GuestListAPIView.as_view(), name='guests-list'),
    path("guests/create/", UserController.GuestCreateAPIView.as_view(), name='guests-create'),



    
]
urlpatterns+=[
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]