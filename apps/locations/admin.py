from django.contrib import admin

from .models import District, Locality, Neighbourhood, Province


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug")
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "slug")
    list_filter = ("province",)
    search_fields = ("name",)
    autocomplete_fields = ("province",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "slug")
    list_filter = ("district__province",)
    search_fields = ("name",)
    autocomplete_fields = ("district",)


@admin.register(Neighbourhood)
class NeighbourhoodAdmin(admin.ModelAdmin):
    list_display = ("name", "locality", "slug")
    list_filter = ("locality__district__province",)
    search_fields = ("name",)
    autocomplete_fields = ("locality",)
