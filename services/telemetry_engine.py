#!/usr/bin/env python3
"""
Telemetry Engine: Algorithmic & Spatial Utilities for SD Finance Fleet Telemetry
Includes:
  1. Haversine distance calculations
  2. Ramer-Douglas-Peucker (RDP) polyline simplification
  3. Stationary stop & trip segmentation (with centroid calculation)
  4. Nearest village spatial matching (with test/placeholder filtering)
"""
import math
from datetime import datetime, timezone
import pytz

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on Earth in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c

def perpendicular_distance(point, start, end):
    """
    Calculate the perpendicular distance of a point from the line segment (start, end).
    Coordinates in degrees. Returns approximate distance in degrees.
    """
    lat, lng = point[0], point[1]
    lat1, lng1 = start[0], start[1]
    lat2, lng2 = end[0], end[1]

    dx = lat2 - lat1
    dy = lng2 - lng1

    if dx == 0 and dy == 0:
        return math.hypot(lat - lat1, lng - lng1)

    # Calculate projection
    t = ((lat - lat1) * dx + (lng - lng1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_lat = lat1 + t * dx
    proj_lng = lng1 + t * dy

    return math.hypot(lat - proj_lat, lng - proj_lng)

def douglas_peucker(points, epsilon=0.00008):
    """
    Ramer-Douglas-Peucker polyline simplification algorithm.
    points: list of [lat, lng, speed, heading, timestamp, ...]
    epsilon: tolerance in degrees (~0.00008 deg is ~8.9 meters)
    Returns: subset of points retaining significant road curvature.
    """
    if len(points) <= 2:
        return points

    dmax = 0.0
    index = 0
    start = points[0]
    end = points[-1]

    for i in range(1, len(points) - 1):
        d = perpendicular_distance(points[i], start, end)
        if d > dmax:
            index = i
            dmax = d

    if dmax > epsilon:
        rec1 = douglas_peucker(points[:index + 1], epsilon)
        rec2 = douglas_peucker(points[index:], epsilon)
        return rec1[:-1] + rec2
    else:
        return [start, end]

def segment_trips_and_stops(points, min_stop_minutes=5, cluster_radius_km=0.08):
    """
    Analyzes chronological coordinates and segments them into:
      - Stops (stationary clusters >= min_stop_minutes within cluster_radius_km, centered at centroid)
      - Trips (moving segments between stops with attached path coordinates)
    points: list of dicts or tuples [lat, lng, speed, heading, timestamp, ...]
    """
    if not points:
        return [], []

    stops = []
    trips = []

    current_stop_start = None
    current_cluster_anchor = None
    cluster_points = []

    trip_points_acc = []
    trip_start_time = None

    for i, pt in enumerate(points):
        lat = pt[0]
        lng = pt[1]
        spd = pt[2] or 0.0
        t = pt[4]  # datetime

        if current_cluster_anchor is None:
            current_cluster_anchor = (lat, lng)
            current_stop_start = t
            cluster_points = [pt]
        else:
            dist_to_anchor = haversine_km(current_cluster_anchor[0], current_cluster_anchor[1], lat, lng)
            if dist_to_anchor <= cluster_radius_km:
                cluster_points.append(pt)
            else:
                # Agent moved outside cluster radius
                duration_mins = max(0, int((t - current_stop_start).total_seconds() // 60))
                if duration_mins >= min_stop_minutes:
                    # Valid stop identified! Compute centroid of the cluster
                    centroid_lat = sum(p[0] for p in cluster_points) / len(cluster_points)
                    centroid_lng = sum(p[1] for p in cluster_points) / len(cluster_points)

                    stops.append({
                        "latitude": round(centroid_lat, 6),
                        "longitude": round(centroid_lng, 6),
                        "arrival_time": current_stop_start,
                        "departure_time": t,
                        "duration_minutes": duration_mins
                    })
                    # Conclude any ongoing trip before this stop
                    if trip_points_acc and trip_start_time:
                        trip_dist = 0.0
                        for j in range(1, len(trip_points_acc)):
                            trip_dist += haversine_km(trip_points_acc[j-1][0], trip_points_acc[j-1][1],
                                                      trip_points_acc[j][0], trip_points_acc[j][1])
                        trip_duration = max(1, int((current_stop_start - trip_start_time).total_seconds() // 60))
                        trip_coords = [[round(p[0], 6), round(p[1], 6)] for p in trip_points_acc]

                        trips.append({
                            "trip_number": len(trips) + 1,
                            "start_time": trip_start_time,
                            "end_time": current_stop_start,
                            "distance_km": round(trip_dist, 2),
                            "duration_minutes": trip_duration,
                            "avg_speed_kmh": round((trip_dist / (trip_duration / 60.0)), 1) if trip_duration > 0 else 0.0,
                            "coords": trip_coords,
                            "start_lat": trip_coords[0][0] if trip_coords else None,
                            "start_lng": trip_coords[0][1] if trip_coords else None,
                            "end_lat": trip_coords[-1][0] if trip_coords else None,
                            "end_lng": trip_coords[-1][1] if trip_coords else None
                        })
                        trip_points_acc = []
                        trip_start_time = None
                else:
                    # Not a long enough stop, was part of a trip
                    if not trip_start_time:
                        trip_start_time = current_stop_start
                    trip_points_acc.extend(cluster_points)

                current_cluster_anchor = (lat, lng)
                current_stop_start = t
                cluster_points = [pt]

        if not trip_start_time:
            trip_start_time = t
        trip_points_acc.append(pt)

    # Final trailing cluster check
    if current_stop_start and cluster_points and current_cluster_anchor:
        final_time = cluster_points[-1][4]
        duration_mins = max(0, int((final_time - current_stop_start).total_seconds() // 60))
        if duration_mins >= min_stop_minutes:
            centroid_lat = sum(p[0] for p in cluster_points) / len(cluster_points)
            centroid_lng = sum(p[1] for p in cluster_points) / len(cluster_points)
            stops.append({
                "latitude": round(centroid_lat, 6),
                "longitude": round(centroid_lng, 6),
                "arrival_time": current_stop_start,
                "departure_time": final_time,
                "duration_minutes": duration_mins
            })

    # Final trailing trip check
    if trip_points_acc and trip_start_time:
        trip_dist = 0.0
        for j in range(1, len(trip_points_acc)):
            trip_dist += haversine_km(trip_points_acc[j-1][0], trip_points_acc[j-1][1],
                                      trip_points_acc[j][0], trip_points_acc[j][1])
        final_time = trip_points_acc[-1][4]
        trip_duration = max(1, int((final_time - trip_start_time).total_seconds() // 60))
        if trip_dist >= 0.3:
            trip_coords = [[round(p[0], 6), round(p[1], 6)] for p in trip_points_acc]
            trips.append({
                "trip_number": len(trips) + 1,
                "start_time": trip_start_time,
                "end_time": final_time,
                "distance_km": round(trip_dist, 2),
                "duration_minutes": trip_duration,
                "avg_speed_kmh": round((trip_dist / (trip_duration / 60.0)), 1) if trip_duration > 0 else 0.0,
                "coords": trip_coords,
                "start_lat": trip_coords[0][0] if trip_coords else None,
                "start_lng": trip_coords[0][1] if trip_coords else None,
                "end_lat": trip_coords[-1][0] if trip_coords else None,
                "end_lng": trip_coords[-1][1] if trip_coords else None
            })

    return trips, stops

def find_nearest_village(cur, lat, lng, max_distance_km=15.0):
    """
    Finds the nearest village from the village table within max_distance_km.
    Filters out non-village test placeholders like 'chit_fund_%' and 'test_%'.
    Returns (village_name, distance_km) or (None, None).
    """
    try:
        # Check if latitude and longitude columns exist on village table
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'village' AND column_name IN ('latitude', 'longitude');
        """)
        cols = [r[0] for r in cur.fetchall()]
        if 'latitude' in cols and 'longitude' in cols:
            cur.execute("""
                SELECT village_name, latitude, longitude
                FROM village
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND village_name NOT ILIKE 'chit_fund_%'
                  AND village_name NOT ILIKE 'test%';
            """)
            villages = cur.fetchall()
            closest = None
            min_dist = float("inf")
            for vname, vlat, vlng in villages:
                try:
                    d = haversine_km(lat, lng, float(vlat), float(vlng))
                    if d < min_dist:
                        min_dist = d
                        closest = vname
                except Exception:
                    continue
            if closest and min_dist <= max_distance_km:
                return closest, round(min_dist, 1)
    except Exception:
        pass
    return None, None
