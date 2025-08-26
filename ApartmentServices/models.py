from django.db import models
from django.utils import timezone
from PropertyServices.models import Property

class Apartment(models.Model):
    APARTMENT_TYPES = (
        ('king', 'King'),
        ('luxury', 'Luxury'),
        ('normal', 'Normal'),
        ('economic', 'Economic'),
    )
    number = models.IntegerField()
    name = models.CharField(max_length=50, blank=True, null=True)
    property_assigned = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='apartments', blank=True, null=True
    )
    capacity = models.SmallIntegerField(blank=True, null=True)
    numberOfBeds = models.SmallIntegerField(blank=True, null=True)
    apartmentType = models.CharField(max_length=20, choices=APARTMENT_TYPES)
    inService = models.BooleanField(default=False)
    cleaned = models.BooleanField(default=True)
    price = models.FloatField(blank=True, null=True)
    currency=models.CharField(max_length=50,blank=True,null=True,default='EUR',choices=(('XAF','XAF'), ('USD','USD'),('INR','INR'),('EUR','EUR'),('GBP','GBP'),('AUD','AUD'),('CAD','CAD'),('JPY','JPY'),('CNY','CNY'),('RUB','RUB'),('BRL','BRL'),('ZAR','ZAR'),('NGN','NGN'),('MXN','MXN'),('ARS','ARS'),('CHF','CHF'),('SEK','SEK'),('NOK','NOK'),('DKK','DKK'),('PLN','PLN'),('CZK','CZK'),('TRY','TRY'),('UAH','UAH'),('HUF','HUF'),('RON','RON'),('BGN','BGN'),('HRK','HRK'),('SLO','SLO'),('SK','SK'),('LT','LT'),('LV','LV'),('EE','EE'),('IE','IE'),('SC','SC'),('WL','WL'),('NI','NI'),('NZ','NZ'),('SGD','SGD'),('MYR','MYR'),('THB','THB'),('IDR','IDR'),('PHP','PHP'),('VND','VND'),('KRW','KRW'),('KPW','KPW'),('TWD','TWD'),('HKD','HKD'),('MOP','MOP'),('BDT','BDT'),('PKR','PKR'),('LKR','LKR'),('NPR','NPR'),('BTN','BTN'),('MVR','MVR'),('AFN','AFN'),('IRR','IRR'),('IQD','IQD'),('SYP','SYP'),('LBN','LBN')))
    image = models.JSONField(blank=True, null=True)
    added_by_user_id=models.ForeignKey('UserServices.User',on_delete=models.CASCADE,blank=True,null=True,related_name='added_by_user_id_apartment')
    is_active = models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.number)


class Booking(models.Model):
    STATUS_TYPES = (
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('upcoming', 'Upcoming'),
        ('active', 'Active')
    )
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, null=True, related_name='apartment_booking')
    guest = models.ForeignKey('UserServices.Guest', null=True, on_delete=models.CASCADE)
    dateOfReservation = models.DateTimeField(default=timezone.now)
    added_by_user_id = models.ForeignKey('UserServices.User', on_delete=models.CASCADE, blank=True, null=True, related_name='added_by_user_id_booking')
    check_in_by_user_id=models.ForeignKey('UserServices.User',on_delete=models.CASCADE,blank=True,null=True,related_name='check_in_by_user_id_booking')
    check_out_by_user_id=models.ForeignKey('UserServices.User',on_delete=models.CASCADE,blank=True,null=True,related_name='check_out_by_user_id_booking')
    status = models.CharField(max_length=50, choices=STATUS_TYPES, default='upcoming')
    startDate = models.DateTimeField()
    endDate = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    def numOfDep(self):
        return Dependees.objects.filter(booking=self).count()

    def __str__(self):
        return f"{self.apartment.number} - {self.apartment.name} {self.guest}"
    
    def save(self, *args, **kwargs):
        # Update status based on dates
        now = timezone.now()
        if self.startDate and self.startDate > now:
            self.status = 'upcoming'
        
        super().save(*args, **kwargs)
        
        # Update apartment status after saving
        if self.apartment:
            if self.status == 'checked_in':
                self.apartment.inService = True
            else:
                self.apartment.inService = False
            self.apartment.save(update_fields=['inService'])

class Dependees(models.Model):
    booking = models.ForeignKey(Booking, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def str(self):
        return str(self.booking) + " " + str(self.name)


class Refund(models.Model):
    guest = models.ForeignKey('UserServices.Guest', null=True, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Booking, on_delete=models.CASCADE)
    reason = models.TextField()

    def __str__(self):
        return str(self.guest)


class RoomServices(models.Model):
    SERVICES_TYPES = (
        ('cleaning', 'Cleaning'),
        ('technical', 'Technical'),
    )

    curBooking = models.ForeignKey(
        Booking,   null=True, on_delete=models.CASCADE)
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE)
    createdDate = models.DateField(default=timezone.now)
    servicesType = models.CharField(max_length=20, choices=SERVICES_TYPES)
    price = models.FloatField()

    def str(self):
        return str(self.curBooking) + " " + str(self.apartment) + " " + str(self.servicesType)
