from django.db import models
from UserServices.models import User

class StaffLocation(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locations')
    latitude = models.DecimalField(max_digits=12, decimal_places=8)
    longitude = models.DecimalField(max_digits=12, decimal_places=8)
    timestamp = models.DateTimeField(auto_now_add=True)
    isOnDuty = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['staff', 'isOnDuty', 'is_active']),
        ]

    def __str__(self):
        return f"{self.staff.username} - on duty:{self.isOnDuty} at {self.timestamp}"