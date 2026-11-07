# SD Accounting Tool & Financial Management System

A high-performance accounting and field collection platform designed for multi-village microfinance, chit funds, banking networks, and telemetry-enabled field operations.

---

## 1. System Architecture

The application is structured into modular domain blueprints, services, and security layers:

```text
SD_Accounting_Tool/
│
├── app.py                          # Flask application factory, routes, and middleware
├── db.py                           # Dynamic, process-safe PostgreSQL connection pooling
├── extensions.py                   # Central Flask extensions (CSRF, Limiter)
│
├── routes/                         # Modular Flask Blueprints
│   ├── payment_routes.py           # Single/bulk payments, editing, deletion by PK (`pid`)
│   ├── feed_routes.py              # Mobile feed batch acceptance & multi-village mapping
│   ├── mobile_api_routes.py        # Authenticated mobile endpoints with IDOR & token guard
│   ├── banking_controller.py       # Central banking, investment folios, and loan engine
│   ├── chit_controller.py          # Chit fund groups, auctions, and dividend distributions
│   └── fleet_telemetry_controller.py # Real-time field staff GPS tracking & telemetry
│
├── services/                       # Business Logic & Math Calculation Engines
│   ├── audit_service.py            # Transaction-aware structured audit logging
│   ├── customer_service.py         # Customer ratings, balances, date utilities, cache invalidation
│   ├── mobile_service.py           # Queue envelopes, canonical HMAC, schema normalizers
│   ├── payment_service.py          # Payment validation and batch reconciliation
│   ├── banking_calc_engine.py      # Banking interest and EMI amortization engine
│   ├── chit_calc_engine.py         # Chit bidding math, commission, and prize pools
│   ├── interest_calc_engine.py     # Loan interest and daily cutting calculations
│   ├── telemetry_engine.py         # Geo-distance, speed, and trip computation
│   └── apk_signing.py              # OTA APK signing and release validation
│
├── security/                       # Security & Authentication Guards
│   ├── auth.py                     # Web session management, roles, and route decorators
│   └── mobile_auth.py              # Mobile JWT/token verification, IDOR village guard, HMAC
│
├── scripts/                        # Maintenance & Migration Scripts
│   ├── audit_links_and_routes.py   # Route auditing and link verification
│   ├── cron_cleanup_telemetry.py   # Background telemetry pruning
│   ├── migrate_cashbags.py         # Multi-cashbag structure migration
│   └── sync_db.py                  # Database synchronization helper
│
├── sql_scripts/                    # Idempotent DB Performance & Migration Scripts
│   └── phase3_performance_indexes.sql # Composite B-Tree indexes for fast query resolution
│
├── static/                         # CSS, JavaScript & Assets
│   ├── css/style.css               # Core UI design, dark mode, neumorphic styling, toasts
│   └── js/utils.js                 # Unified CSRF fetch, toast alerts, date/currency formatters
│
├── templates/                      # Jinja2 Server-Rendered HTML Templates
└── tests/                          # Automated PyUnit Test Suites (47+ Tests)
    ├── conftest.py                 # Test fixtures, mock environments, and isolated contexts
    ├── test_phase1_security.py     # Mobile auth, IDOR, token revocation, XSS
    ├── test_phase2_financial_integrity.py # Precise Decimal, delete by pid, batch acceptance
    ├── test_phase3_db_resilience.py # Connection pool sizing, audit transaction logging
    ├── test_phase4_modular_blueprints.py # Blueprint registration & routing isolation
    └── test_phase5_frontend_and_resilience.py # CSRF enforcement, utils.js, village context
```

---

## 2. Production Deployment Topology

```text
       Internet (HTTPS / Client Requests)
                     ↓
         Nginx Reverse Proxy (:80 / :443)
                     ↓
       Gunicorn WSGI (Workers = 8, Ports 8080)
                     ↓
 PostgreSQL Database (Connection Pool: 2–12 per worker)
```

---

## 3. Environment Configuration

Create a `.env` file in `SD_Accounting_Tool/` based on the following template:

```env
# Database Credentials
DB_HOST=127.0.0.1
DB_NAME=sd_finance
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_PORT=5432

# Connection Pool Tuning (Per-worker allocation)
DB_POOL_MIN=2
DB_POOL_MAX=12

# Application Secrets
SECRET_KEY=your_random_hex_secret_key_minimum_64_chars
MOBILE_QUEUE_HMAC_SECRET=your_production_hmac_secret_key

# Security Flags (Set to 0 or omit in production)
DISABLE_SECURE_COOKIE=0

# Operational Configuration
BANKING_ADMIN_PIN=1234
APK_KEYSTORE_PASSWORD=your_keystore_password
```

---

## 4. Key Security & Financial Hardening Features

- **Mobile Authorization Guard (`@mobile_auth_required`)**:
  Every mobile API endpoint validates token signatures, enforces user active status (`is_active = TRUE`), and checks village authorization against `user_village_access` or employee assignments (`emp1`/`emp2`) to prevent IDOR attacks.
- **Strict HMAC Request Signing**:
  Mobile sync envelopes enforce canonical JSON serialization and SHA-256 HMAC signature verification with strict timestamp drift guards (±15 minutes) and production startup assertion.
- **Accurate Primary Key Deletion**:
  Payment deletions strictly require and use the primary key (`pid`), preventing multi-payment deletion collisions.
- **Multi-Village Batch Acceptance**:
  Mobile collection feeds match records using composite `(vid, ano)` keys with `FOR UPDATE` row locking, processing only valid pending records idempotently.
- **Arbitrary-Precision Arithmetic**:
  All financial operations leverage Python's `Decimal` and PostgreSQL `NUMERIC` types to avoid binary floating-point drift.
- **Cross-Site Scripting (XSS) Sanitization**:
  Dynamic template renderings sanitize user inputs via `escapeHtml()`.
- **Database Connection Pool Resiliency**:
  Lazy process-safe `ThreadedConnectionPool` ensures pre-forked Gunicorn workers instantiate independent pools without cross-worker socket contention.

---

## 5. Development & Testing

### Running Tests Locally

Activate your virtual environment and execute the automated regression test suite:

```bash
cd SD_Accounting_Tool
source .venv/bin/activate
python -m unittest discover -s tests -p "test_phase*.py"
```

All 47 tests across Phases 1 through 5 run in under 1 second without modifying live database records.

### Running the Application

```bash
# Development server (with hot reload)
python app.py

# Production server via Gunicorn
gunicorn -w 8 -b 0.0.0.0:8080 app:app
```
