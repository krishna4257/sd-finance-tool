import os
import re
import time
import requests
from urllib.parse import quote_plus
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_village_name(name):
    if not name:
        return ""
    # Remove all digits and trim dashes/spaces
    name = re.sub(r'\d+', '', name)
    name = re.sub(r'[-\s]+$', '', name)
    name = re.sub(r'^[-\s]+', '', name)
    return name.strip()

def geocode_query(q):
    url = f"https://nominatim.openstreetmap.org/search?q={quote_plus(str(q))}&format=jsonv2&limit=1&countrycodes=in"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if data:
                return (
                    float(data[0]["lat"]),
                    float(data[0]["lon"]),
                    data[0].get("display_name", "")
                )

        elif response.status_code == 403:
            print("Received HTTP 403 Forbidden. Check User-Agent or IP block.")

    except Exception as e:
        print(f"Network error geocoding query '{q}': {e}")

    return None


def geocode_pincode(pincode):
    url = f"https://nominatim.openstreetmap.org/search?postalcode={quote_plus(str(pincode))}&country=India&format=jsonv2&limit=1"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if data:
                return (
                    float(data[0]["lat"]),
                    float(data[0]["lon"]),
                    data[0].get("display_name", "")
                )
    except Exception as e:
        print(f"Pincode lookup failed for {pincode}: {e}")

    return None

def main():
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"].strip(),
        database=os.environ["DB_NAME"].strip(),
        user=os.environ["DB_USER"].strip(),
        password=os.environ["DB_PASSWORD"].strip(),
        port=os.environ.get("DB_PORT", "6432").strip(),
    )
    cur = conn.cursor()

    # Get list of all villages
    cur.execute("SELECT vid, village_name, district, state, pincode, latitude, longitude FROM village ORDER BY vid")
    villages = cur.fetchall()
    
    total = len(villages)
    print(f"Loaded {total} villages from the database.")
    
    geocoded_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, (vid, name, district, state, pincode, lat, lon) in enumerate(villages, 1):
        # Skip if already geocoded
        if lat is not None and lon is not None:
            skipped_count += 1
            continue

        print(f"[{idx}/{total}] Geocoding: {name} (District: {district}, State: {state}, Pincode: {pincode})...")
        clean_name = clean_village_name(name)
        
        coords = None
        
        # Step 1: name + pincode + district + state
        if clean_name and pincode and district and state:
            q = f"{clean_name}, {pincode}, {district}, {state}, India"
            print(f"  Attempt 1 (name+pincode+district+state): '{q}'")
            coords = geocode_query(q)
            time.sleep(1.2)
            
        # Step 2: name + pincode
        if not coords and clean_name and pincode:
            q = f"{clean_name}, {pincode}, India"
            print(f"  Attempt 2 (name+pincode): '{q}'")
            coords = geocode_query(q)
            time.sleep(1.2)
            
        # Step 3: name + district + state
        if not coords and clean_name and district and state:
            q = f"{clean_name}, {district}, {state}, India"
            print(f"  Attempt 3 (name+district+state): '{q}'")
            coords = geocode_query(q)
            time.sleep(1.2)
            
        # Step 4: name + state
        if not coords and clean_name and state:
            q = f"{clean_name}, {state}, India"
            print(f"  Attempt 4 (name+state): '{q}'")
            coords = geocode_query(q)
            time.sleep(1.2)
            
        # Step 5: Direct pincode lookup
        if not coords and pincode:
            print(f"  Attempt 5 (direct pincode lookup): '{pincode}'")
            coords = geocode_pincode(pincode)
            time.sleep(1.2)

        if coords:
            res_lat, res_lon, disp_name = coords
            print(f"  -> SUCCESS: Found coords {res_lat}, {res_lon} ({disp_name})")
            
            # Update database
            cur.execute("""
                UPDATE village 
                SET latitude = %s, longitude = %s 
                WHERE vid = %s
            """, (res_lat, res_lon, vid))
            conn.commit()
            geocoded_count += 1
        else:
            print(f"  -> FAILED: Could not geocode village.")
            failed_count += 1

    cur.close()
    conn.close()
    
    print("\n=== Geocoding Session Finished ===")
    print(f"Total processed: {total}")
    print(f"Skipped (already geocoded): {skipped_count}")
    print(f"Successfully geocoded this run: {geocoded_count}")
    print(f"Failed to geocode: {failed_count}")

if __name__ == "__main__":
    main()
