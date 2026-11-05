# ADR-001: Defer PostGIS to Phase 2

## Status
Accepted, temporary. Revisit at the start of Phase 2.

## Context
The GDAL native library could not be loaded on the Windows development
machine (Store Python 3.13, osgeo wheel contains bindings but no DLL).
Phase 1 deliverables — custom user model, location hierarchy, REST
baseline, CI, health check — do not require geospatial queries.

## Decision
Run plain PostgreSQL for Phase 1. Coordinates are stored as
`DecimalField(max_digits=9, decimal_places=6)` for latitude and
longitude rather than a `PointField`.

## Consequences
- No proximity, distance, or polygon search until Phase 2.
- `django.contrib.gis` is commented out in INSTALLED_APPS.
- The database engine is `django.db.backends.postgresql`.
- Every downstream model that wants geometry must wait.

## Reversal procedure (Phase 2)
1. Install OSGeo4W (Windows) or `apt install gdal-bin libgdal-dev` (Linux).
2. Uncomment `django.contrib.gis` in INSTALLED_APPS.
3. Switch engine back to `django.contrib.gis.db.backends.postgis`.
4. Add a migration that:
   a. Adds `centroid = PointField(srid=4326, null=True)`.
   b. Runs `Neighbourhood.objects.update(
          centroid=Func(
              F("longitude"), F("latitude"),
              function="ST_SetSRID",
              template="ST_SetSRID(ST_MakePoint(%(expressions)s), 4326)",
          )
      )` — or the equivalent `RunPython` step.
   c. Drops `latitude` and `longitude` once verified.
5. Swap `NeighbourhoodAdmin` back to `GISModelAdmin`.

Data loss: none. Lat/lng → geometry is a lossless conversion at
6-decimal precision.
