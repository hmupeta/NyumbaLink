from django.contrib import admin
from .models import Conversation, Message, ViewingRequest
admin.site.register([Conversation, Message, ViewingRequest])
