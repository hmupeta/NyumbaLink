from django.contrib import admin
from .models import Lease, RentRecord
admin.site.register([Lease, RentRecord])
