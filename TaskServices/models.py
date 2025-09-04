from django.db import models
from django.utils import timezone
from UserServices.models import User
from PropertyServices.models import Property
from django.core.validators import MaxValueValidator
from ApartmentServices.models import Apartment 

class TaskTemplate(models.Model):
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    duration = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Estimated duration needed per occurrence"
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    default_apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='apartment_task_template', blank=True, null=True)
    default_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_task_template', blank=True, null=True)
    active = models.BooleanField(default=True)
    default_assignees = models.ManyToManyField(User, blank=True)
    
    def __str__(self):
        return self.title

class Task(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    notes = models.CharField(max_length=200, blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    duration = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    assigned_to = models.ManyToManyField(User, related_name='user_tasks', blank=True)
    property_assigned = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_tasks', blank=True, null=True)
    apartment_assigned = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='apartment_tasks', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    added_by_user_id = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='added_by_user_id_task'
    )
    priority = models.CharField(max_length=20, choices=TaskTemplate.PRIORITY_CHOICES)
    active = models.BooleanField(default=True)
    template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='instances'
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    
    def save(self, *args, **kwargs):
        # If created from template, copy template values if not provided
        if self.template and not self.pk:
            if not self.title:
                self.title = self.template.title
            if not self.description:
                self.description = self.template.description
            if not self.duration:
                self.duration = self.template.duration
            if not self.priority:
                self.priority = self.template.priority
        super().save(*args, **kwargs)

class TaskGallerie(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="gallery_task")
    image = models.JSONField(blank=True, null=True)
    order = models.IntegerField(default=0, validators=[MaxValueValidator(7)])
    
    class Meta:
        ordering = ['order']
        unique_together = ('task', 'order')