from django.contrib import admin

from .models import AuditLog, HeroImage, Listing, ListingMedia, Property, PropertyAuthority, PropertyFeature, Report


class ListingMediaInline(admin.TabularInline):
    model = ListingMedia
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("id", "property_type", "neighbourhood", "submitted_by", "status", "created_at")
    list_filter = ("property_type", "status", "neighbourhood__locality__district__province")
    search_fields = ("address_line", "description", "submitted_by__email")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("features",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "transaction_type", "price", "currency", "status", "published_at")
    list_filter = ("status", "transaction_type", "currency")
    search_fields = ("title", "description", "created_by__email")
    readonly_fields = ("id", "published_at", "created_at", "updated_at")
    inlines = [ListingMediaInline]
    actions = ["publish_listings"]

    @admin.action(description="Publish selected submitted listings")
    def publish_listings(self, request, queryset):
        from . import services
        n = 0
        for listing in queryset.filter(status="SUBMITTED"):
            services.publish_listing(listing, actor=request.user)
            n += 1
        self.message_user(request, f"Published {n} listing(s).")


@admin.register(PropertyAuthority)
class PropertyAuthorityAdmin(admin.ModelAdmin):
    list_display = ("property", "granted_to", "granted_by", "can_list", "expires_at", "revoked_at")
    list_filter = ("can_list", "can_edit")
    search_fields = ("property__id", "granted_to__email")


@admin.register(PropertyFeature)
class PropertyFeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "status", "reporter", "target_listing", "target_user", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("description", "reporter__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "target_type", "target_id", "actor")
    list_filter = ("action", "target_type")
    search_fields = ("target_id",)
    readonly_fields = ("id", "created_at", "actor", "action", "target_type", "target_id", "payload")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HeroImage)
class HeroImageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
