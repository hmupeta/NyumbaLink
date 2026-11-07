from django.contrib import admin
from django.utils import timezone
from .models import VerificationCase, VerificationDocument

class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    readonly_fields = ("file", "document_type")

@admin.register(VerificationCase)
class VerificationCaseAdmin(admin.ModelAdmin):
    list_display = ("user", "verification_type", "status", "created_at")
    list_filter = ("status", "verification_type")
    search_fields = ("user__email",)
    readonly_fields = ("user", "verification_type", "created_at", "updated_at")
    inlines = [VerificationDocumentInline]
    actions = ["approve_cases", "reject_cases"]

    @admin.action(description="Approve selected verifications")
    def approve_cases(self, request, queryset):
        queryset.update(status="APPROVED", reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} cases approved.")

    @admin.action(description="Reject selected verifications")
    def reject_cases(self, request, queryset):
        queryset.update(status="REJECTED", reviewed_by=request.user, reviewed_at=timezone.now(), rejection_reason="Rejected by admin.")
        self.message_user(request, f"{queryset.count()} cases rejected.")
