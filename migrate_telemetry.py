#!/usr/bin/env python3
"""
Database Migration: Telemetry & Location Tracking Engine
Applies:
  1. user_locations (Standard B-Tree table, non-partitioned, 10-day retention)
  2. user_daily_trips (Permanent daily historical rollups)
  3. user_devices telemetry extensions (latest coordinates, speed, heading, battery, gps status)
"""
import sys
import os

# Ensure current directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db import get_pool

def run_migration():
    print("[MIGRATION] Starting Telemetry Database Migration...")
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            # 1. user_locations table
            print("[MIGRATION] Creating user_locations table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_locations (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    device_id VARCHAR(64) NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    accuracy REAL,
                    speed REAL DEFAULT 0.0,
                    heading REAL DEFAULT 0.0,
                    battery_pct SMALLINT,
                    is_charging BOOLEAN DEFAULT FALSE,
                    activity_type VARCHAR(20) DEFAULT 'unknown',
                    recorded_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Composite index for fast user date-range filtering
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_locations_user_recorded 
                ON user_locations (user_id, recorded_at DESC);
            """)

            # Timestamp index for the 10-day purge query
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_locations_recorded_at 
                ON user_locations (recorded_at);
            """)

            # 2. user_daily_trips table
            print("[MIGRATION] Creating user_daily_trips table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_daily_trips (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    trip_date DATE NOT NULL,
                    total_distance_km NUMERIC(8, 2) DEFAULT 0.00,
                    travel_minutes INTEGER DEFAULT 0,
                    stop_minutes INTEGER DEFAULT 0,
                    stop_count INTEGER DEFAULT 0,
                    first_ping_at TIMESTAMPTZ,
                    last_ping_at TIMESTAMPTZ,
                    battery_start_pct SMALLINT,
                    battery_end_pct SMALLINT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE (user_id, trip_date)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_daily_trips_user_date 
                ON user_daily_trips (user_id, trip_date DESC);
            """)

            # 3. user_devices telemetry column enhancements
            print("[MIGRATION] Enhancing user_devices with telemetry columns...")
            cur.execute("""
                ALTER TABLE user_devices 
                    ADD COLUMN IF NOT EXISTS latest_latitude DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS latest_longitude DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS latest_speed REAL DEFAULT 0.0,
                    ADD COLUMN IF NOT EXISTS latest_heading REAL DEFAULT 0.0,
                    ADD COLUMN IF NOT EXISTS latest_accuracy REAL,
                    ADD COLUMN IF NOT EXISTS latest_battery_pct SMALLINT,
                    ADD COLUMN IF NOT EXISTS is_charging BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS gps_status VARCHAR(20) DEFAULT 'active';
            """)

            conn.commit()
            print("[MIGRATION] SUCCESS: Telemetry schema migration committed.")
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION] ERROR: Migration failed: {e}", file=sys.stderr)
        raise
    finally:
        pool.putconn(conn)

if __name__ == "__main__":
    run_migration()
