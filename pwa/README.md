# SD Finance - iOS Progressive Web App (Smart Counting)

This folder contains a **100% self-contained Progressive Web App (PWA)** for SD Finance. It is specifically designed to give iOS / iPhone users full mobile application capabilities without requiring a \$99/year Apple Developer account or 7-day SideStore/AltStore re-signing cycles.

Because this folder is completely isolated, you can test it risk-free. If you ever decide not to use it, you can delete it immediately:
```bash
rm -rf sd_finance_pwa
```
*(Nothing in `sd_finance_mobile` or `SD_Accounting_Tool` will be affected).*

---

## 📂 Folder Structure

```
sd_finance_pwa/
├── index.html            # Main PWA application shell with iOS viewport & meta tags
├── manifest.webmanifest  # PWA manifest for standalone home screen mode
├── sw.js                 # Service Worker (offline asset caching & background strategy)
├── serve.py              # Lightweight development server with API reverse proxy
├── icons/                # iOS and PWA application icons (192px, 512px, Apple Touch Icon)
│   ├── icon-192.png
│   ├── icon-512.png
│   ├── apple-touch-icon.png
│   └── favicon.png
├── css/
│   └── app.css           # Clean iOS-tailored responsive stylesheet with notch/safe-area support
└── js/
    ├── db.js             # IndexedDB engine (village cache, customer cache, offline queues)
    ├── api.js            # REST API client connecting to /api/mobile endpoints with X-Mobile-Token
    ├── geo.js            # Fast, non-blocking GPS location audit capture
    ├── camera.js         # Camera capture and canvas-based image compression (12MP -> ~400KB)
    ├── sync.js           # Offline synchronization manager with auto-flush on reconnect
    └── app.js            # Main application controller (view routing, payment modals, receipts)
```

---

## 🚀 How to Test on Your iPhone Right Now (Local Wi-Fi)

You can preview the app on your Mac and on your real iPhone immediately using the included `serve.py` proxy server:

1. **Start the local server**:
   ```bash
   cd sd_finance_pwa
   python3 serve.py
   ```
   *By default, this server listens on port `8080` and proxies all `/api/mobile/*` requests to your live server `https://sivadurga.in`.*

2. **Open on your Mac**:
   Visit [http://localhost:8080](http://localhost:8080) in your browser.

3. **Open on your iPhone**:
   - Ensure your iPhone and Mac are connected to the same Wi-Fi network.
   - The terminal will display your Mac's Wi-Fi IP address (e.g., `http://192.168.1.15:8080`).
   - Open Safari on your iPhone and visit that address.

4. **Install to iPhone Home Screen**:
   - In Safari, tap the **Share** button (box with an arrow pointing up at the bottom).
   - Scroll down and tap **Add to Home Screen**.
   - Tap **Add** in the top right corner.
   - An app icon named **Smart Counting** will now appear on your iPhone Home Screen.
   - Tap the icon to launch the app in **standalone mode** (no browser address bar or back buttons).

---

## ⚡ Core Features Implemented

1. **Standalone iOS App Experience**: Runs full-screen with native iOS notch and home-bar padding.
2. **Permanent Installation**: Stays on the device forever without 7-day expiration loops.
3. **Full Offline Collection (IndexedDB)**:
   - When employees collect money in remote villages with zero reception, payments are saved to local IndexedDB with unique UUIDs and client-side timestamps.
   - The customer's local balance decreases immediately so employees can see up-to-date balances.
   - Receipts are generated and can be shown to customers immediately.
4. **Auto-Synchronization Engine**:
   - Listens for network restoration (`window.addEventListener('online')`) and automatically flushes queued payments in batches to `/api/mobile/payment_feed_batch`.
   - Includes a manual **🔄 Sync Now** button and live pending counter badges.
5. **Instant Receipts & WhatsApp Sharing**:
   - Generates formatted payment receipts with receipt #, account #, customer name, date, payment mode (Cash/UPI), and remaining balance.
   - One-tap **💬 Share on WhatsApp** button pre-fills a professional payment slip message.
   - One-tap **🖨️ Print** button triggers AirPrint or system PDF creation.
6. **Customer Onboarding with Camera & Photo Compression**:
   - Allows capturing Aadhaar front/back and house photos via the iPhone camera.
   - Automatically compresses high-resolution 12MP/48MP camera photos down to ~300KB–600KB before storing/uploading to preserve bandwidth.
7. **GPS Audit Tagging**:
   - Captures high-accuracy GPS coordinates (`latitude`, `longitude`, `accuracy`) at the exact moment a collection or customer is recorded.

---

## 🌐 Production Deployment Options

When you are ready to make this accessible to your employees over the internet, you have two simple options:

### Option A: Nginx Subpath on Server (Recommended)
Add this alias to your Nginx configuration on `sivadurga.in`:
```nginx
location /m/ {
    alias /srv/sd-finance-tool/sd_finance_pwa/;
    index index.html;
    try_files $uri $uri/ /m/index.html;
}
```
Then tell employees to visit `https://sivadurga.in/m/` on their iPhones and tap **Add to Home Screen**.

### Option B: Flask Static Route (No Nginx Changes Needed)
If you prefer Flask to serve it directly from `SD_Accounting_Tool`, you can register a single route in `app.py`:
```python
from flask import send_from_directory

@app.route('/m/<path:path>')
@app.route('/m/')
def serve_pwa(path='index.html'):
    pwa_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sd_finance_pwa'))
    return send_from_directory(pwa_dir, path)
```

---

## 🗑️ How to Remove
If you decide you do not want this web app, simply run:
```bash
rm -rf sd_finance_pwa
```
No other project files or database configurations will be touched.
