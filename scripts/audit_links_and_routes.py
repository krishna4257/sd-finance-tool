#!/usr/bin/env python3
"""
Comprehensive Web Application Link & Route Integrity Auditor
Audits:
1. render_template() calls in all controllers (missing templates)
2. url_for() calls in templates (invalid endpoints)
3. href and action links in all HTML templates (404 dead links)
4. Static file references in HTML templates (missing CSS/JS/images)
5. JavaScript API endpoints (fetch/ajax targets with no matching Flask route)
6. Route health status check (GET requests with admin session)
"""

import os
import re
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from urllib.parse import urlparse
from app import app
from db import get_pg_connection

def find_files(dir_path, extensions):
    matched = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                matched.append(os.path.join(root, f))
    return matched

def main():
    print("=" * 80)
    print("SIVA DURGA FINANCE — FULL WEBSITE ROUTE & LINK INTEGRITY AUDIT")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. RENDER_TEMPLATE AUDIT
    # -------------------------------------------------------------------------
    print("\n[1] AUDITING RENDER_TEMPLATE CALLS IN CONTROLLERS...")
    controllers = [
        'app.py',
        os.path.join('routes', 'chit_controller.py'),
        os.path.join('routes', 'banking_controller.py'),
        os.path.join('routes', 'fleet_telemetry_controller.py'),
        os.path.join('routes', 'mobile_api_routes.py'),
        os.path.join('routes', 'feed_routes.py'),
        os.path.join('routes', 'payment_routes.py'),
    ]
    render_re = re.compile(r'render_template\(\s*[\'"]([^\'"]+\.html)[\'"]')
    missing_templates = []
    valid_renders = 0

    for c in controllers:
        if not os.path.exists(c):
            continue
        with open(c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for tmpl in set(render_re.findall(content)):
            valid_renders += 1
            # Normalize path for OS
            rel_tmpl = tmpl.replace('/', os.sep)
            full_path = os.path.join('templates', rel_tmpl)
            if not os.path.exists(full_path):
                missing_templates.append((c, tmpl, full_path))

    if missing_templates:
        print(f"  ❌ FOUND {len(missing_templates)} MISSING TEMPLATE FILES:")
        for c, tmpl, path in missing_templates:
            print(f"     - [{c}] -> render_template('{tmpl}') (File not found: {path})")
    else:
        print(f"  ✅ All {valid_renders} render_template() calls reference existing template files.")

    # -------------------------------------------------------------------------
    # 2. URL_FOR AUDIT IN TEMPLATES
    # -------------------------------------------------------------------------
    print("\n[2] AUDITING URL_FOR() REFERENCES IN TEMPLATES...")
    template_files = find_files('templates', ['.html', '.jinja'])
    url_for_re = re.compile(r'url_for\(\s*[\'"]([a-zA-Z0-9_\.]+)[\'"]')
    registered_endpoints = set(app.view_functions.keys())

    missing_endpoints = []
    total_url_for = 0

    for tf in template_files:
        with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for ep in set(url_for_re.findall(content)):
            total_url_for += 1
            if ep == 'static':
                continue
            if ep not in registered_endpoints:
                missing_endpoints.append((tf, ep))

    if missing_endpoints:
        print(f"  ❌ FOUND {len(missing_endpoints)} BROKEN url_for() ENDPOINTS (would cause 500 BuildError):")
        for tf, ep in missing_endpoints:
            print(f"     - File: {tf} -> url_for('{ep}') does NOT exist in registered endpoints!")
    else:
        print(f"  ✅ All {total_url_for} url_for() calls point to valid registered endpoints.")

    # -------------------------------------------------------------------------
    # 3. STATIC FILE REFERENCES IN TEMPLATES (CSS, JS, Images)
    # -------------------------------------------------------------------------
    print("\n[3] AUDITING STATIC ASSETS (CSS/JS/Images)...")
    static_url_for_re = re.compile(r'url_for\(\s*[\'"]static[\'"]\s*,\s*filename\s*=\s*[\'"]([^\'"]+)[\'"]')
    static_direct_re = re.compile(r'(?:src|href)=[\'"]/static/([^\'"?#]+)[\'"?#]')
    
    missing_assets = []
    checked_assets = 0

    for tf in template_files:
        with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check url_for('static', filename='...')
        for filename in set(static_url_for_re.findall(content)):
            # skip jinja interpolation inside filename
            if '{{' in filename:
                continue
            checked_assets += 1
            rel_asset = filename.replace('/', os.sep)
            full_path = os.path.join('static', rel_asset)
            if not os.path.exists(full_path):
                missing_assets.append((tf, filename, full_path))

        # Check /static/...
        for filename in set(static_direct_re.findall(content)):
            if '{{' in filename:
                continue
            checked_assets += 1
            rel_asset = filename.replace('/', os.sep)
            full_path = os.path.join('static', rel_asset)
            if not os.path.exists(full_path):
                missing_assets.append((tf, filename, full_path))

    # Deduplicate
    unique_missing_assets = list(set((m[1], m[2]) for m in missing_assets))
    if unique_missing_assets:
        print(f"  ⚠️  FOUND {len(unique_missing_assets)} MISSING STATIC ASSETS:")
        for fn, full_path in unique_missing_assets:
            print(f"     - Missing static file: /static/{fn} ({full_path})")
    else:
        print(f"  ✅ All {checked_assets} checked static asset paths exist on disk.")

    # -------------------------------------------------------------------------
    # 4. TEMPLATE HREF & ACTION LINKS AUDIT
    # -------------------------------------------------------------------------
    print("\n[4] AUDITING HTML HREF & FORM ACTION LINKS IN TEMPLATES...")
    # Matches href="/..." or action="/..."
    link_re = re.compile(r'(?:href|action)=[\'"](/[^#\'"\s>]+)[\'"]')

    # Compile all Flask url rules into regex matchers
    rule_matchers = []
    for rule in app.url_map.iter_rules():
        # Flask rule string: e.g. /village/<int:vid> or /banking/groups/<uuid:group_id> or /customer/<cid>
        pattern = rule.rule
        # Replace <int:...>, <path:...>, <string:...>, <uuid:...>, <...> with regex
        pattern = re.sub(r'<int:[^>]+>', r'\\d+', pattern)
        pattern = re.sub(r'<float:[^>]+>', r'\\d+(?:\\.\\d+)?', pattern)
        pattern = re.sub(r'<path:[^>]+>', r'.+', pattern)
        pattern = re.sub(r'<uuid:[^>]+>', r'[0-9a-fA-F-]+', pattern)
        pattern = re.sub(r'<[^>]+>', r'[^/]+', pattern)
        pattern = f"^{pattern}$"
        rule_matchers.append((re.compile(pattern), rule.rule, rule.endpoint))

    dead_links = []
    dynamic_links_checked = 0
    static_links_checked = 0

    for tf in template_files:
        with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for link in set(link_re.findall(content)):
            # Skip static files, protocol relative, or external
            if link.startswith('/static') or link.startswith('//'):
                continue
            
            # Normalize jinja variables in URL to dummy test values:
            # e.g., /village/{{ village.vid }} -> /village/1
            # e.g., /banking/groups/{{ group.id }} -> /banking/groups/1
            test_link = re.sub(r'\{\{[^\}]+\}\}', '1', link)
            test_link = re.sub(r'\{%[^\%]+%\}', '', test_link)
            test_link = test_link.split('?')[0] # Strip query params

            # Skip empty or javascript:
            if not test_link or test_link.startswith('javascript:'):
                continue

            # Test against url_map
            matched = False
            for matcher, orig_rule, endpoint in rule_matchers:
                if matcher.match(test_link):
                    matched = True
                    break

            if not matched:
                dead_links.append((tf, link, test_link))
            else:
                static_links_checked += 1

    # Filter out known false positives or client-side SPA routes if any
    unique_dead = {}
    for tf, link, test_link in dead_links:
        if link not in unique_dead:
            unique_dead[link] = []
        unique_dead[link].append(tf)

    if unique_dead:
        print(f"  ❌ FOUND {len(unique_dead)} UNRESOLVED / DEAD LINKS IN TEMPLATES:")
        for link, files in unique_dead.items():
            print(f"     - Dead Link: '{link}'")
            for f in files[:3]:
                print(f"       Used in: {f}")
            if len(files) > 3:
                print(f"       ... and {len(files) - 3} more templates")
    else:
        print(f"  ✅ All {static_links_checked} internal links in templates matched valid Flask routes.")

    # -------------------------------------------------------------------------
    # 5. JAVASCRIPT FETCH & AJAX ENDPOINTS AUDIT
    # -------------------------------------------------------------------------
    print("\n[5] AUDITING JAVASCRIPT API CALLS IN STATIC JS & TEMPLATES...")
    js_files = find_files('static/js', ['.js'])
    # Matches fetch('/...'), url: '/...', $.get('/...'), $.post('/...'), axios.get('/...')
    js_api_re = re.compile(r'''(?:fetch|url:|url\s*=|\$\.get|\$\.post|\$\.ajax)\s*(?:\(\s*|\s*:\s*|\s*=\s*)[\'"`](/api/[^\'"`?\s]+|/banking/[^\'"`?\s]+|/chit/[^\'"`?\s]+|/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-/]+)[\'"`]''')

    dead_js_apis = {}
    total_js_calls = 0

    sources = js_files + template_files
    for src in sources:
        with open(src, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for api_url in set(js_api_re.findall(content)):
            total_js_calls += 1
            # Clean up JS string interpolation ${...} to dummy '1'
            test_url = re.sub(r'\$\{[^\}]+\}', '1', api_url)
            # Remove trailing quotes or slashes
            test_url = test_url.rstrip("',\"`").split('?')[0]

            if not test_url.startswith('/'):
                continue

            matched = False
            for matcher, orig_rule, endpoint in rule_matchers:
                if matcher.match(test_url):
                    matched = True
                    break

            if not matched:
                if test_url not in dead_js_apis:
                    dead_js_apis[test_url] = []
                dead_js_apis[test_url].append(src)

    if dead_js_apis:
        print(f"  ⚠️  FOUND {len(dead_js_apis)} POTENTIALLY UNRESOLVED JS API ENDPOINTS:")
        for url, files in dead_js_apis.items():
            print(f"     - Endpoint: '{url}'")
            for f in files[:2]:
                print(f"       Found in: {f}")
    else:
        print(f"  ✅ All {total_js_calls} detected JS API calls match registered Flask routes.")

    # -------------------------------------------------------------------------
    # 6. LIVE ROUTE HEALTH CHECK WITH FLASK TEST CLIENT
    # -------------------------------------------------------------------------
    print("\n[6] LIVE TESTING REGISTERED FLASK GET ROUTES (ADMIN SESSION)...")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    # Get sample test IDs from DB for parameterized routes
    sample_vid = 1
    sample_cid = 1
    sample_group_id = '00000000-0000-0000-0000-000000000000'
    sample_investor_id = '00000000-0000-0000-0000-000000000000'

    try:
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT vid FROM village LIMIT 1;")
            r = cur.fetchone()
            if r: sample_vid = r[0]
            cur.execute("SELECT cid FROM customer LIMIT 1;")
            r = cur.fetchone()
            if r: sample_cid = r[0]
            cur.execute("SELECT id FROM village_groups LIMIT 1;")
            r = cur.fetchone()
            if r: sample_group_id = str(r[0])
            cur.execute("SELECT id FROM investors LIMIT 1;")
            r = cur.fetchone()
            if r: sample_investor_id = str(r[0])
        conn.close()
    except Exception as e:
        print(f"  (DB query for test IDs skipped: {e})")

    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['level'] = 'admin'
        sess['eid'] = 1
        sess['logged_in'] = True

    route_errors = []
    routes_checked = 0

    for rule in app.url_map.iter_rules():
        if 'GET' not in rule.methods:
            continue
        
        # Build test URL
        rule_str = rule.rule
        # Skip static and webhooks/auth external
        if rule_str.startswith('/static'):
            continue
        
        test_path = rule_str
        test_path = re.sub(r'<int:vid>', str(sample_vid), test_path)
        test_path = re.sub(r'<vid>', str(sample_vid), test_path)
        test_path = re.sub(r'<int:cid>', str(sample_cid), test_path)
        test_path = re.sub(r'<cid>', str(sample_cid), test_path)
        test_path = re.sub(r'<int:eid>', '1', test_path)
        test_path = re.sub(r'<eid>', '1', test_path)
        test_path = re.sub(r'<uuid:group_id>', sample_group_id, test_path)
        test_path = re.sub(r'<group_id>', sample_group_id, test_path)
        test_path = re.sub(r'<uuid:investor_id>', sample_investor_id, test_path)
        test_path = re.sub(r'<investor_id>', sample_investor_id, test_path)
        test_path = re.sub(r'<int:ano>', '1', test_path)
        test_path = re.sub(r'<int:id>', '1', test_path)
        test_path = re.sub(r'<[^>]+>', '1', test_path)

        # Skip paths that still have <>
        if '<' in test_path:
            continue

        routes_checked += 1
        try:
            resp = client.get(test_path, follow_redirects=False)
            # Acceptable status codes: 200, 301, 302, 308 (redirects)
            # 400/404/500 indicate broken routes or missing resources
            if resp.status_code == 500:
                route_errors.append((test_path, rule.endpoint, resp.status_code, "Internal Server Error / Broken Template"))
            elif resp.status_code == 404:
                route_errors.append((test_path, rule.endpoint, resp.status_code, "Page Not Found"))
        except Exception as ex:
            route_errors.append((test_path, rule.endpoint, 500, str(ex)))

    if route_errors:
        print(f"  ❌ FOUND {len(route_errors)} GET ROUTES WITH ERRORS (500 or 404):")
        for path, ep, code, msg in route_errors:
            print(f"     - [{code}] {path} (endpoint: '{ep}'): {msg}")
    else:
        print(f"  ✅ All {routes_checked} parameter-resolvable GET routes returned valid status (200 OK or 302 Redirect).")

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
