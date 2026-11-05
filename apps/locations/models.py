from django.db import models

from apps.core.models import TimeStampedModel


class Province(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    code = models.CharField(max_length=4, unique=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "province"
        verbose_name_plural = "provinces"

    def __str__(self):
        return self.name


class District(TimeStampedModel):
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name="districts")
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "district"
        verbose_name_plural = "districts"
        constraints = [
            models.UniqueConstraint(fields=["province", "slug"], name="uniq_district_slug_per_province"),
        ]

    def __str__(self):
        return f"{self.name}, {self.province.name}"


class Locality(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="localities")
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "locality"
        verbose_name_plural = "localities"
        constraints = [
            models.UniqueConstraint(fields=["district", "slug"], name="uniq_locality_slug_per_district"),
        ]

    def __str__(self):
        return f"{self.name}, {self.district.name}"


class Neighbourhood(TimeStampedModel):
    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="neighbourhoods")
    name = models.CharField(max_length=96)
    slug = models.SlugField(max_length=96)
    aliases = models.JSONField(default=list, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "neighbourhood"
        verbose_name_plural = "neighbourhoods"
        constraints = [
            models.UniqueConstraint(fields=["locality", "slug"], name="uniq_neighbourhood_slug_per_locality"),
        ]

    def __str__(self):
        return f"{self.name}, {self.locality.name}"
