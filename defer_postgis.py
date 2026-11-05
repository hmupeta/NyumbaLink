#!/usr/bin/env python3
"""Apply Phase 1 PostGIS deferral. Re-runnable, idempotent."""
from pathlib import Path

ROOT = Path.cwd()

# (relative path, old snippet, new snippet, description)
PATCHES = [
    (
        "config/settings/base.py",
        '    "django.contrib.gis",\n',
        '    # "django.contrib.gis",  # DEFERRED until Phase 2 — see docs/adr/001-defer-postgis.md\n',
        "settings: comment out django.contrib.gis",
    ),
    (
        "config/settings/base.py",
        '"ENGINE": "django.contrib.gis.db.backends.postgis",',
        '"ENGINE": "django.db.backends.postgresql",  # was postgis — DEFERRED to Phase 2',
        "settings: switch DB engine to plain postgresql",
    ),
    (
        "apps/locations/models.py",
        "from django.contrib.gis.db import models\n",
        "from django.db import models\n",
        "models: use django.db instead of gis",
    ),
    (
        "apps/locations/models.py",
        '    centroid = models.PointField(srid=4326, null=True, blank=True)\n',
        '    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)\n'
        '    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)\n',
        "models: replace PointField with lat/lng decimals",
    ),
    (
        "apps/locations/admin.py",
        "from django.contrib.gis.admin import GISModelAdmin\n",
        "",
        "admin: drop GISModelAdmin import",
    ),
    (
        "apps/locations/admin.py",
        "class NeighbourhoodAdmin(GISModelAdmin):",
        "class NeighbourhoodAdmin(admin.ModelAdmin):",
        "admin: NeighbourhoodAdmin inherits ModelAdmin",
    ),
    (
        "apps/core/views.py",
        '    checks = {"database": "ok", "postgis": "ok"}\n',
        '    checks = {"database": "ok"}\n',
        "health: drop postgis key",
    ),
    (
        "apps/core/views.py",
        '            cursor.execute("SELECT PostGIS_Version()")\n'
        '            cursor.fetchone()\n',
        "",
        "health: drop PostGIS_Version probe",
    ),
    (
        "apps/core/views.py",
        '        checks["postgis"] = "error"\n',
        "",
        "health: drop postgis error key",
    ),
    (
        "docker-compose.yml",
        "image: postgis/postgis:16-3.4",
        "image: postgres:16  # was postgis — DEFERRED to Phase 2",
        "docker: plain postgres image",
    ),
    (
        ".github/workflows/ci.yml",
        "      - name: System deps\n"
        "        run: sudo apt-get update && sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev\n",
        "      # GDAL step removed — PostGIS deferred to Phase 2\n",
        "ci: drop GDAL install step",
    ),
    (
        ".github/workflows/ci.yml",
        "        image: postgis/postgis:16-3.4",
        "        image: postgres:16",
        "ci: plain postgres service",
    ),
]

ADR = """# ADR-001: Defer PostGIS to Phase 2

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
"""

ADR_PATH = ROOT / "docs" / "adr" / "001-defer-postgis.md"


def apply(relative, old, new, description):
    path = ROOT / relative
    if not path.exists():
        return f"  SKIP   {description}  (file missing: {relative})"
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new and new.split("\n")[0] in text:
            return f"  ok     {description}  (already applied)"
        return f"  WARN   {description}  (snippet not found in {relative})"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"  PATCH  {description}"


def main():
    print(f"Deferring PostGIS in {ROOT}\n")
    results = [apply(*p) for p in PATCHES]
    print("\n".join(results))

    ADR_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADR_PATH.write_text(ADR, encoding="utf-8")
    print(f"  WRITE  {ADR_PATH.relative_to(ROOT)}")

    if any(r.startswith("  WARN") for r in results):
        print("\nSome patches did not match. Inspect the files by hand "
              "before continuing — silent mismatches are how this round "
              "went wrong.")
    else:
        print("\nAll patches applied cleanly.")


if __name__ == "__main__":
    main()