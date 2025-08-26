from django.urls import path, include
from UserServices.Controller import AuthController
from UserServices.Controller import  UserController
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('users/', UserController.ListUserAPIView.as_view(), name='users-list'),
    path('user/<int:pk>/', UserController.RetrieveDestroyUserAPIView.as_view(), name='retrieve-destroy-user'),
    path('auth/login/', AuthController.LoginAPIView.as_view(), name='jwt-login'),
    path('user/create/', UserController.CreateUserAPIView.as_view(), name='create-user'),
    path('user/update/<int:pk>/', UserController.UpdateUserAPIView.as_view(), name='update-user'),
    
    path('user/work-hours/monthly/', UserController.MonthlyWorkHoursAPIView.as_view(), name='monthly-work-hours'),
    path('user/tasks/current-month-counts/', UserController.CurrentMonthTaskCountAPIView.as_view(), name='current-month-task-counts'),
    path('user/tasks/recent/', UserController.RecentTasksAPIView.as_view(), name='recent-tasks'),
    path('auth/change-password/', AuthController.ChangePasswordAPIView.as_view(), name='change-password'),
    
    path('user/generate-schedule/', UserController.GenerateScheduleAPIView.as_view(), name='generate-schedule'),
    path('user/schedules/', UserController.StaffScheduleAPIView.as_view(), name='all-schedules'),
    path('user/schedules/<int:pk>/', UserController.StaffScheduleAPIView.as_view(), name='staff-schedule'),
    path('user/staff/', UserController.StaffUsersAPIView.as_view(), name='users-staff'),
    
    path("salaries/completed-tasks/preview/", UserController.CompletedTaskSalaryPreviewAPIView.as_view(), name='salaries-preview'),
    path("salaries/completed-tasks/save/", UserController.CompletedTaskSalarySaveAPIView.as_view(), name='salaries-save'),
    path("salary/periods/", UserController.SalaryPeriodsAPIView.as_view(), name='salary-period'),
    path("salaries/by-period/", UserController.SalariesByPeriodAPIView.as_view(), name='salaries-period'),
    path("salary/<int:pk>/", UserController.SalaryUpdateDeleteAPIView.as_view(), name='salary-update'),
    
    path("guests/search", UserController.GuestSearchViewAPIView.as_view(), name='guest-search'),
    path("guests/<int:pk>/", UserController.GuestRetrieveUpdateDestroyAPIView.as_view(), name='guest-retrieve-update-destroy'),
    path("guests/", UserController.GuestListAPIView.as_view(), name='guests-list'),
    path("guests/create/", UserController.GuestCreateAPIView.as_view(), name='guests-create'),



    
]
urlpatterns+=[
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]