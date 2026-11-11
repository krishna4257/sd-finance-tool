#!/usr/bin/env python3
"""
Reverse Geocoding Service for SD Finance Fleet Telemetry.
Provides human-readable place, landmark, and road naming matching Google Maps Timeline.
Includes:
  1. PostgreSQL persistent geocache (telemetry_geocache)
  2. High-speed OpenStreetMap / Photon POI reverse geocoding
  3. BigDataCloud fallback reverse geocoding
  4. Local village database fallback
  5. High-concurrency batch geocoding with ThreadPoolExecutor
"""

import json
import logging
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

logger = logging.getLogger(__name__)

# In-memory LRU cache to avoid DB round-trips for the same session/batch
_MEMORY_CACHE = {}
_MAX_MEMORY_CACHE = 2000

def _get_cache_key(lat, lng):
    """Round coordinates to 4 decimal places (~11 meters resolution)."""
    return (round(float(lat), 4), round(float(lng), 4))

def init_geocache_table(conn):
    """Ensures telemetry_geocache table exists in PostgreSQL."""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_geocache (
                lat_round NUMERIC(8,4) NOT NULL,
                lng_round NUMERIC(8,4) NOT NULL,
                place_name TEXT NOT NULL,
                subtitle TEXT,
                road TEXT,
                city TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (lat_round, lng_round)
            );
        """)
        conn.commit()
        cur.close()
    except Exception as e:
        logger.warning(f"Could not initialize telemetry_geocache table: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

def lookup_cached_geocache(cur, lat_round, lng_round):
    """Checks DB cache for pre-geocoded location."""
    try:
        cur.execute("""
            SELECT place_name, subtitle, road, city
            FROM telemetry_geocache
            WHERE lat_round = %s AND lng_round = %s;
        """, (lat_round, lng_round))
        row = cur.fetchone()
        if row:
            return {
                "place_name": row[0],
                "subtitle": row[1] or "",
                "road": row[2] or "",
                "city": row[3] or ""
            }
    except Exception as e:
        logger.debug(f"DB cache lookup error: {e}")
    return None

def save_to_geocache(conn, lat_round, lng_round, place_name, subtitle="", road="", city=""):
    """Saves a resolved geocoding result into DB."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO telemetry_geocache (lat_round, lng_round, place_name, subtitle, road, city)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (lat_round, lng_round) DO UPDATE
            SET place_name = EXCLUDED.place_name,
                subtitle = EXCLUDED.subtitle,
                road = EXCLUDED.road,
                city = EXCLUDED.city;
        """, (lat_round, lng_round, place_name, subtitle, road, city))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.debug(f"DB cache save error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

def _fetch_photon_reverse(lat, lng):
    """
    Reverse geocodes using Photon (Komoot OSM).
    Extremely fast and provides rich POI names (hospitals, shops, markets, buildings).
    """
    url = f"https://photon.komoot.io/reverse?lat={lat}&lon={lng}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SD-Finance-Fleet/1.0"}
    )
    with urllib.request.urlopen(req, timeout=1.2) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        features = data.get("features", [])
        if not features:
            return None
        props = features[0].get("properties", {})
        if not props:
            return None

        # POI or business or street name
        name = props.get("name")
        housenumber = props.get("housenumber")
        street = props.get("street")
        locality = props.get("locality") or props.get("district")
        city = props.get("city") or props.get("town") or props.get("village") or props.get("county")
        state = props.get("state")

        # Clean locality (sometimes has semicolon delimiters like "Mydukuru Urban;S.Mydukur Urban")
        if locality and ";" in locality:
            locality = locality.split(";")[0].strip()

        place_name = None
        if name:
            place_name = name
        elif street:
            place_name = f"{housenumber + ' ' if housenumber else ''}{street}"
        elif locality:
            place_name = locality
        elif city:
            place_name = city

        sub_parts = []
        if street and street != place_name:
            sub_parts.append(street)
        if locality and locality != place_name:
            sub_parts.append(locality)
        if city and city != place_name:
            sub_parts.append(city)
        if state and state != place_name:
            sub_parts.append(state)

        subtitle = ", ".join(sub_parts[:2]) if sub_parts else (state or "India")
        return {
            "place_name": place_name or "Recorded Location",
            "subtitle": subtitle,
            "road": street or "",
            "city": city or locality or ""
        }

def _fetch_bigdatacloud_reverse(lat, lng):
    """Fallback reverse geocode via BigDataCloud client API."""
    url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lng}&localityLanguage=en"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 SD-Finance-Fleet/1.0"}
    )
    with urllib.request.urlopen(req, timeout=1.2) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        locality = data.get("locality") or data.get("city")
        subdivision = data.get("principalSubdivision")
        country = data.get("countryName")

        place_name = locality or subdivision or "Recorded Area"
        subtitle = ", ".join([p for p in [subdivision, country] if p and p != place_name])
        return {
            "place_name": place_name,
            "subtitle": subtitle,
            "road": "",
            "city": locality or ""
        }

def reverse_geocode(conn, cur, lat, lng, fallback_nearest_village_func=None):
    """
    High-level reverse geocoding with multi-tier resolution:
      1. Memory cache
      2. DB persistent cache
      3. Photon API
      4. BigDataCloud API
      5. Local village table (sanitized)
    Returns: dict {"place_name": str, "subtitle": str, "road": str, "city": str}
    """
    if lat is None or lng is None:
        return {"place_name": "Unknown Location", "subtitle": "", "road": "", "city": ""}

    lat_round, lng_round = _get_cache_key(lat, lng)

    # 1. Check memory cache
    if (lat_round, lng_round) in _MEMORY_CACHE:
        return _MEMORY_CACHE[(lat_round, lng_round)]

    # 2. Check PostgreSQL cache
    if cur:
        cached = lookup_cached_geocache(cur, lat_round, lng_round)
        if cached:
            if len(_MEMORY_CACHE) < _MAX_MEMORY_CACHE:
                _MEMORY_CACHE[(lat_round, lng_round)] = cached
            return cached

    # 3. Try Photon API
    resolved = None
    try:
        resolved = _fetch_photon_reverse(lat_round, lng_round)
    except Exception as e:
        logger.debug(f"Photon geocode attempt failed: {e}")

    # 4. Try BigDataCloud API fallback
    if not resolved:
        try:
            resolved = _fetch_bigdatacloud_reverse(lat_round, lng_round)
        except Exception as e:
            logger.debug(f"BigDataCloud geocode attempt failed: {e}")

    # 5. Local Village database fallback
    if not resolved and fallback_nearest_village_func and cur:
        try:
            vname, dist = fallback_nearest_village_func(cur, lat, lng)
            if vname:
                resolved = {
                    "place_name": vname,
                    "subtitle": f"{dist} km to center" if dist is not None else "Village Route",
                    "road": "",
                    "city": vname
                }
        except Exception:
            pass

    # Ultimate fallback if completely offline
    if not resolved:
        resolved = {
            "place_name": f"Location ({lat_round:.3f}, {lng_round:.3f})",
            "subtitle": "GPS Telemetry Point",
            "road": "",
            "city": ""
        }

    # Save to memory cache
    if len(_MEMORY_CACHE) < _MAX_MEMORY_CACHE:
        _MEMORY_CACHE[(lat_round, lng_round)] = resolved

    # Save to DB cache
    if conn and (resolved.get("place_name") and not resolved.get("place_name").startswith("Location (")):
        save_to_geocache(
            conn,
            lat_round,
            lng_round,
            resolved["place_name"],
            resolved.get("subtitle", ""),
            resolved.get("road", ""),
            resolved.get("city", "")
        )

    return resolved

def batch_reverse_geocode(conn, cur, coord_tuples, fallback_nearest_village_func=None):
    """
    Parallel reverse geocoding for a list of (lat, lng) tuples.
    Returns a dict mapping (lat_round, lng_round) -> resolved dict.
    """
    unique_coords = set()
    for lat, lng in coord_tuples:
        if lat is not None and lng is not None:
            unique_coords.add(_get_cache_key(lat, lng))

    results = {}
    uncached = []

    # 1. Check memory and DB cache first
    for key in unique_coords:
        if key in _MEMORY_CACHE:
            results[key] = _MEMORY_CACHE[key]
        elif cur:
            cached = lookup_cached_geocache(cur, key[0], key[1])
            if cached:
                _MEMORY_CACHE[key] = cached
                results[key] = cached
            else:
                uncached.append(key)
        else:
            uncached.append(key)

    # 2. Fetch uncached coordinates in parallel
    if uncached:
        def _fetch_one(key):
            lat, lng = key
            res = None
            try:
                res = _fetch_photon_reverse(lat, lng)
            except Exception:
                pass
            if not res:
                try:
                    res = _fetch_bigdatacloud_reverse(lat, lng)
                except Exception:
                    pass
            if not res and fallback_nearest_village_func and cur:
                try:
                    vname, dist = fallback_nearest_village_func(cur, lat, lng)
                    if vname:
                        res = {
                            "place_name": vname,
                            "subtitle": f"{dist} km to center" if dist is not None else "Village Route",
                            "road": "",
                            "city": vname
                        }
                except Exception:
                    pass
            if not res:
                res = {
                    "place_name": f"Location ({lat:.3f}, {lng:.3f})",
                    "subtitle": "GPS Telemetry Point",
                    "road": "",
                    "city": ""
                }
            return key, res

        with ThreadPoolExecutor(max_workers=min(6, len(uncached))) as executor:
            future_to_key = {executor.submit(_fetch_one, k): k for k in uncached}
            for future in as_completed(future_to_key):
                try:
                    k, resolved = future.result()
                    results[k] = resolved
                    _MEMORY_CACHE[k] = resolved
                    if conn and not resolved["place_name"].startswith("Location ("):
                        save_to_geocache(conn, k[0], k[1], resolved["place_name"], resolved.get("subtitle", ""), resolved.get("road", ""), resolved.get("city", ""))
                except Exception as e:
                    logger.debug(f"Parallel geocode worker error: {e}")

    return results
