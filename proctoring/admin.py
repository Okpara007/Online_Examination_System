from django.contrib import admin

from .models import ProctoringLog


@admin.register(ProctoringLog)
class ProctoringLogAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "event_type", "severity", "is_flagged", "created_at")
    list_filter = ("severity", "is_flagged")
