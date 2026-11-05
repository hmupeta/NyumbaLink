#!/usr/bin/env python3
"""Close out Phase 2: fix the anonymous-create test and rewrite ADR-001."""
from pathlib import Path

ROOT = Path.cwd()

# ------------------------------------------------------------------ 1. test fix

TEST_FILE = ROOT / "apps" / "properties" / "tests" / "test_endpoints.py"
OLD = "        self.assertEqual(resp.status_code, 401)"
NEW = (
    "        # 403 not 401: SessionAuthentication declares no authenticate_header().\n"
    "        # This becomes 401 when token auth arrives in Phase 3.\n"
    "        self.assertEqual(resp.status_code, 403)"
)

if not TEST_FILE.exists():
    print(f"WARN  {TEST_FILE.relative_to(ROOT)} not found")
else:
    text = TEST_FILE.read_text(encoding="utf-8")
    if OLD in text:
        TEST_FILE.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
        print("PATCH  test_endpoints.py: assertEqual(401) -> assertEqual(403)")
    elif "resp.status_code, 403" in text:
        print("ok     test_endpoints.py (already 403)")
    else:
        print("WARN   test_endpoints.py: assertion pattern not matched, inspect by hand")

# ------------------------------------------------------------------ 2. ADR

ADR_CONTENT = """# ADR-001: No PostGIS (indefinite deferral with explicit triggers)

## Status
Accepted. Indefinite until a documented trigger fires.

## Context
Phase 1 attempted Django's `django.contrib.gis` stack on native Windows.
GDAL native library loading proved unreliable under Store Python 3.13
(empty osgeo DLL folder, wheel/bindings-only packages, antivirus blocks,
version-name drift between Django's search list and installed GDAL).

Two reversals were considered and rejected:
  - OSGeo4W on Windows — workable but fragile and platform-specific.
  - WSL2 — durable but a mid-Phase-1 workflow change.

Neither Phase 1 (accounts, locations) nor Phase 2 (properties, listings,
moderation, permissions) requires any spatial query. `DecimalField(9, 6)`
stores coordinates losslessly at ~11 cm precision, far beyond what any
property listing needs.

## Decision
Run plain PostgreSQL. Store coordinates as `latitude` / `longitude`
`DecimalField(max_digits=9, decimal_places=6)` with a DB-level CHECK
constraint enforcing that both are set or neither is.

`django.contrib.gis` remains commented out in `INSTALLED_APPS`.
The DB engine is `django.db.backends.postgresql`.
CI, docker-compose, and every settings file reflect non-GIS Postgres.

## Consequences
- No `ST_DWithin` / proximity search in the API.
- No polygon or draw-on-map search.
- No spatial index; distance filtering requires application-level
  haversine over the result set. Viable to roughly 10k listings per
  query; degrades beyond that.
- Neighbourhood hierarchy (`Province > District > Locality > Neighbourhood`)
  remains intact and drives location search today.
- Frontend map rendering is unaffected: WGS84 lat/lng in the API is
  what every map library expects.

## When to reverse
Reversal is warranted only when one of these is observed, not on a
schedule:

  1. Proximity search ("within X km") is a top-3 requested feature.
  2. p95 latency on the listings endpoint exceeds 200 ms under real
     production load.
  3. Neighbourhood polygon boundaries are required for draw-on-map
     search or geofenced notifications.
  4. A regulatory or partner requirement mandates polygon storage.

Absent those, this ADR stands. Adding PostGIS prematurely forces a
platform migration (WSL2/Linux, GDAL, engine swap, data migration)
for zero user-visible benefit.

## Reversal procedure
Outline (details to be written at reversal time):

  1. Move dev environment to WSL2 or Linux.
  2. `apt install gdal-bin libgdal-dev libgeos-dev postgresql-16-postgis-3`.
  3. Uncomment `django.contrib.gis`; switch DB engine to
     `django.contrib.gis.db.backends.postgis`.
  4. Enable PostGIS extension on the database.
  5. Data migration per app:
       a. Add `PointField(srid=4326, null=True)` alongside lat/lng.
       b. `RunPython` step backfilling from lat/lng via
          `ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)`.
       c. Verify; drop the old decimal columns.
  6. Add a spatial index and enable proximity filters.
  7. Update CI and docker-compose to `postgis/postgis`.

Data is preserved by construction. Estimated effort: ~20 minutes on
Linux once the environment is in place.

## History
- 2026-11-04: drafted as "defer to Phase 2".
- 2026-11-05: renamed to `001-no-postgis.md`; rewritten to reflect an
  indefinite deferral with explicit reversal triggers. Phase 2 shipped
  without PostGIS.
"""

ADR_DIR = ROOT / "docs" / "adr"
ADR_DIR.mkdir(parents=True, exist_ok=True)
OLD_ADR = ADR_DIR / "001-defer-postgis.md"
NEW_ADR = ADR_DIR / "001-no-postgis.md"

if OLD_ADR.exists() and not NEW_ADR.exists():
    OLD_ADR.unlink()
    print(f"REMOVE {OLD_ADR.relative_to(ROOT)} (superseded)")
NEW_ADR.write_text(ADR_CONTENT, encoding="utf-8")
print(f"WRITE  {NEW_ADR.relative_to(ROOT)}")

# ------------------------------------------------------------------ summary

print("""
Next:

  1.  .\\venv\\Scripts\\python.exe manage.py test apps
      expected: Ran 24 tests ... OK

  2.  git add -A
      git commit -m "Phase 2 closed: moderation, permissions, listings; ADR-001 settled"
      git tag phase-2

Phase 3 setup follows in the next message.
""")