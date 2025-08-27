from django.db import models

class Property(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    distance = models.FloatField(blank=True, null=True, help_text="Min distance to Clock In or Clock Out")
    added_by_user_id=models.ForeignKey('UserServices.User',on_delete=models.SET_NULL,blank=True,null=True,related_name='added_by_user_id_property')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)