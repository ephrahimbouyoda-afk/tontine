from django.contrib import admin
from .models import TontineGroup, Membership, Transaction

admin.site.register(TontineGroup)
admin.site.register(Membership)
admin.site.register(Transaction)