from django.db import models
from django.contrib.auth.models import AbstractUser
from PropertyServices.models import Property
from ApartmentServices.models import Booking

class User(AbstractUser):
    ROLES = (
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('receptionist', 'Receptionist'),
        ('cleaning', 'Cleaning Staff'),
        ('technical', 'Technical Staff'),
        ('guest', 'Guest'),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    properties_assigned = models.ManyToManyField(
        Property, related_name='assigned_users', blank=True
    )
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    added_by_user_id=models.ForeignKey('self',on_delete=models.SET_NULL,blank=True,null=True,related_name='added_by_user_id_user')
    department = models.CharField(max_length=50, blank=True, null=True, choices=(('FO', 'FO'), ('HK', 'HK'), ('TECHNICAL', 'TECHNICAL'), ('DG', 'DG'), ('HR', 'HR'), ('IT', 'IT'), ('SALE', 'SALE'), ('FINCANCE', 'FINCANCE')))
    currency=models.CharField(max_length=50, blank=True, null=True, default='EUR',choices=(('XAF','XAF'), ('USD','USD'),('INR','INR'),('EUR','EUR'),('GBP','GBP'),('AUD','AUD'),('CAD','CAD'),('JPY','JPY'),('CNY','CNY'),('RUB','RUB'),('BRL','BRL'),('ZAR','ZAR'),('NGN','NGN'),('MXN','MXN'),('ARS','ARS'),('CHF','CHF'),('SEK','SEK'),('NOK','NOK'),('DKK','DKK'),('PLN','PLN'),('CZK','CZK'),('TRY','TRY'),('UAH','UAH'),('HUF','HUF'),('RON','RON'),('BGN','BGN'),('HRK','HRK'),('SLO','SLO'),('SK','SK'),('LT','LT'),('LV','LV'),('EE','EE'),('IE','IE'),('SC','SC'),('WL','WL'),('NI','NI'),('NZ','NZ'),('SGD','SGD'),('MYR','MYR'),('THB','THB'),('IDR','IDR'),('PHP','PHP'),('VND','VND'),('KRW','KRW'),('KPW','KPW'),('TWD','TWD'),('HKD','HKD'),('MOP','MOP'),('BDT','BDT'),('PKR','PKR'),('LKR','LKR'),('NPR','NPR'),('BTN','BTN'),('MVR','MVR'),('AFN','AFN'),('IRR','IRR'),('IQD','IQD'),('SYP','SYP'),('LBN','LBN')))
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class Guest(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    idCard = models.JSONField(blank=True, null=True)
    def __str__(self):
        return f"{self.user.get_full_name() if self.user else 'Anonymous'}"

    def save(self, *args, **kwargs):
        if self.user and self.user.role != 'guest':
            raise ValueError("Only users with role 'guest' can be linked to a Guest.")
        super().save(*args, **kwargs)

    def num_of_bookings(self):
        return Booking.objects.filter(guest=self).count()

    def total_days_stayed(self):
        bookings = Booking.objects.filter(guest=self)
        return sum((b.endDate - b.startDate).days for b in bookings)

    def last_booking_days(self):
        booking = Booking.objects.filter(guest=self).order_by('-startDate').first()
        if booking:
            return (booking.endDate - booking.startDate).days
        return 0

    def current_apartment(self):
        booking = Booking.objects.filter(guest=self, apartments__inService=True).order_by('-startDate').first()
        if booking:
            return [
                f"{ap.number} - {ap.name} ({ap.property_assigned.name}-{ap.property_assigned.address})"
                for ap in booking.apartments.filter(inService=True)
            ]
        return []

class StaffSchedule(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules')
    day = models.CharField(max_length=50)
    hours = models.DecimalField(max_digits=4, decimal_places=1)
    week_number = models.PositiveIntegerField()
    date = models.DateField(null=True, blank=True)
    start_time = models.CharField(max_length=50, null=True, blank=True)
    end_time = models.CharField(max_length=50, null=True, blank=True)
    added_by_user_id=models.ForeignKey(User, on_delete=models.SET_NULL,blank=True,null=True,related_name='added_by_user_id_schedule')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['week_number', 'day']

    def __str__(self):
        return f"{self.staff.username} - {self.day} - {self.hours}h (Week {self.week_number})"

class PayRule(models.Model):
    PAY_TYPES = (
        ('hourly','Hourly'),
        ('salaried', 'Salaried'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payrules')
    payType = models.CharField(max_length=50, choices=PAY_TYPES)
    payRate = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at=models.DateTimeField(auto_now=True)

class Salary(models.Model):
    PAY_STATUS = (
        ('paid', 'Paid'),
        ('pending', 'Pending')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_salary')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_salary', blank=True, null=True)
    total_salary = models.FloatField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAY_STATUS, default='pending')
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at=models.DateTimeField(auto_now=True)

class Bill(models.Model):
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guest_bill')
    total_amount = models.IntegerField()
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at=models.DateTimeField(auto_now=True)


class ActivityLog(models.Model):
    id=models.AutoField(primary_key=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_activity_log')
    activity=models.TextField()
    activity_type=models.CharField(max_length=50,blank=True)
    activity_date=models.DateTimeField(auto_now_add=True)
    activity_ip=models.GenericIPAddressField()
    activity_device=models.CharField(max_length=50)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
