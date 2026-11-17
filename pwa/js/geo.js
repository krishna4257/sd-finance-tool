/**
 * SD Finance PWA - Geolocation Service
 * Fast, non-blocking GPS capture for audit tagging.
 */
class GeoService {
  constructor() {
    this.cachedFix = null;
    this.cachedTimestamp = null;
  }

  async getPosition(timeoutMs = 4000) {
    // 1. Check if we have a fresh fix from within the last 30 seconds
    if (this.cachedFix && this.cachedTimestamp && (Date.now() - this.cachedTimestamp < 30000)) {
      return {
        ...this.cachedFix,
        gps_status: 'cached'
      };
    }

    if (!('geolocation' in navigator)) {
      return { latitude: null, longitude: null, accuracy: null, gps_status: 'unavailable' };
    }

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        // Fallback to cached fix if available, or unavailable on timeout
        if (this.cachedFix) {
          resolve({ ...this.cachedFix, gps_status: 'cached' });
        } else {
          resolve({ latitude: null, longitude: null, accuracy: null, gps_status: 'timeout' });
        }
      }, timeoutMs);

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          clearTimeout(timer);
          const fix = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: Math.round(pos.coords.accuracy),
            gps_status: 'active'
          };
          this.cachedFix = fix;
          this.cachedTimestamp = Date.now();
          resolve(fix);
        },
        (err) => {
          clearTimeout(timer);
          console.warn('Geolocation error:', err.message);
          if (this.cachedFix) {
            resolve({ ...this.cachedFix, gps_status: 'cached' });
          } else {
            resolve({ latitude: null, longitude: null, accuracy: null, gps_status: 'denied' });
          }
        },
        {
          enableHighAccuracy: true,
          timeout: timeoutMs,
          maximumAge: 15000
        }
      );
    });
  }
}

window.geoService = new GeoService();
