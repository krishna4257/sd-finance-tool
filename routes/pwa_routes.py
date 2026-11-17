"""
PWA Routes Module for SD Finance iOS / Mobile Progressive Web App.
Serves the self-contained PWA from 'pwa/' at /pwa/ and /ios/.
"""
import os
from flask import Blueprint, send_from_directory, redirect, make_response, abort

pwa_bp = Blueprint("pwa_bp", __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Resolves the PWA directory in production, local, or custom environments
POSSIBLE_DIRS = [
    os.path.join(BASE_DIR, "pwa"),
    os.path.abspath(os.path.join(BASE_DIR, "..", "sd_finance_pwa")),
    "/srv/sd-finance-tool/sd_finance_pwa",
    "/srv/sd-finance-tool/SD_Accounting_Tool/pwa",
]
PWA_DIR = next((d for d in POSSIBLE_DIRS if os.path.isdir(d)), None)


@pwa_bp.route("/pwa")
@pwa_bp.route("/pwa/")
def pwa_index():
    if not PWA_DIR:
        abort(404, description="PWA directory not found")
    resp = make_response(send_from_directory(PWA_DIR, "index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    return resp


@pwa_bp.route("/pwa/<path:filename>")
def pwa_assets(filename):
    if not PWA_DIR:
        abort(404, description="PWA directory not found")
    
    file_path = os.path.join(PWA_DIR, filename)
    if not os.path.exists(file_path):
        abort(404, description="Asset not found")

    resp = make_response(send_from_directory(PWA_DIR, filename))

    if filename == "sw.js":
        resp.headers["Service-Worker-Allowed"] = "/pwa/"
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Content-Type"] = "application/javascript"
    elif filename == "manifest.webmanifest":
        resp.headers["Content-Type"] = "application/manifest+json"
        resp.headers["Cache-Control"] = "public, max-age=3600"
    elif filename.endswith((".css", ".js")):
        resp.headers["Cache-Control"] = "public, max-age=3600"
    elif filename.endswith((".png", ".svg", ".jpg", ".ico")):
        resp.headers["Cache-Control"] = "public, max-age=86400"
    
    return resp


@pwa_bp.route("/ios")
@pwa_bp.route("/ios/")
def ios_redirect():
    return redirect("/pwa/", code=302)


@pwa_bp.route("/mobile")
@pwa_bp.route("/mobile/")
def mobile_redirect():
    return redirect("/pwa/", code=302)


@pwa_bp.route("/privacy")
@pwa_bp.route("/privacy/")
@pwa_bp.route("/privacy-policy")
@pwa_bp.route("/privacy-policy/")
def privacy_policy():
    static_dir = os.path.join(BASE_DIR, "static")
    return send_from_directory(static_dir, "privacy-policy.html")

