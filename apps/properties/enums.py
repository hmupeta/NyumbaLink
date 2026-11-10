from django.db import models


class PropertyType(models.TextChoices):
    HOUSE = "HOUSE", "House"
    APARTMENT = "APARTMENT", "Apartment"
    FLAT = "FLAT", "Flat"
    TOWNHOUSE = "TOWNHOUSE", "Townhouse"
    BOARDING_HOUSE = "BOARDING_HOUSE", "Boarding house"
    STUDENT_LODGE = "STUDENT_LODGE", "Student lodge"
    COMMERCIAL = "COMMERCIAL", "Commercial"
    LAND = "LAND", "Land"
    OTHER = "OTHER", "Other"


class TransactionType(models.TextChoices):
    RENT = "RENT", "For rent"
    SALE = "SALE", "For sale"
    SHORT_LET = "SHORT_LET", "Short let"


class PricePeriod(models.TextChoices):
    MONTH = "MONTH", "Per month"
    YEAR = "YEAR", "Per year"
    ONCE = "ONCE", "One-off"


class PropertyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    OCCUPIED = "OCCUPIED", "Occupied (Leased)"
    ARCHIVED = "ARCHIVED", "Archived"


class ListingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted for review"
    PUBLISHED = "PUBLISHED", "Published"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    EXPIRED = "EXPIRED", "Expired"
    ARCHIVED = "ARCHIVED", "Archived"


class MediaType(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"
    TOUR = "TOUR", "Virtual tour"


class ReportReason(models.TextChoices):
    FRAUD = "FRAUD", "Fraud or scam"
    DUPLICATE = "DUPLICATE", "Duplicate listing"
    WRONG_INFO = "WRONG_INFO", "Inaccurate information"
    UNAVAILABLE = "UNAVAILABLE", "Property no longer available"
    OFFENSIVE = "OFFENSIVE", "Offensive content"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    REVIEWING = "REVIEWING", "In review"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"
