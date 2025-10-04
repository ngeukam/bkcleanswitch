from django.urls import path
from TaskServices.Controller import TaskController

urlpatterns = [
    path('tasks/', TaskController.TaskListCreateAPIView.as_view(), name='task-list-create'),
    path('tasks-templates/', TaskController.TaskTemplateListCreateAPIView.as_view(), name='tasks-templates-list-create'),
    path('tasks-templates/<int:pk>/', TaskController.TaskTemplateRetrieveUpdateDestroyAPIView.as_view(), name='tasks-templates-update-destroy'),
    path('tasks/<int:pk>/', TaskController.TaskRetrieveUpdateDestroyAPIView.as_view(), name='task-update-destroy'),
    path('tasks/<int:pk>/update-status/', TaskController.TaskStatusUpdateAPIView.as_view(), name='task-update-status'),
    path('calendar/tasks/', TaskController.CalendarTasksAPIView.as_view(), name='calendar-tasks'),

]
