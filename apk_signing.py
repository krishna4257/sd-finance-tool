"""
apk_signing.py — Android APK Digital Signing & Verification Engine
==================================================================
Manages cryptographic verification and signing of release APKs using
the SD Finance official keystore (sd-finance-key.jks) and credentials.
"""

import os
import re
import shutil
import hashlib
import logging
import subprocess
import zipfile
from pathlib import Path

logger = logging.getLogger("sd_finance.apk_signing")

BASE_DIR = Path(__file__).resolve().parent
CERTS_DIR = BASE_DIR / "certs"
KEY_PROPERTIES_PATH = CERTS_DIR / "key.properties"
KEYSTORE_PATH = CERTS_DIR / "sd-finance-key.jks"

# Expected SHA-256 fingerprint for official sd_finance signing key
OFFICIAL_CERT_SHA256 = "58a90643bbc0521953421835cf1394a2d9b66b530b2df45cf7644a9dc7403c5c"


def _load_key_properties():
    """Load keystore settings from key.properties."""
    props = {}
    if KEY_PROPERTIES_PATH.is_file():
        with open(KEY_PROPERTIES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    props[k.strip()] = v.strip()

    # Fallbacks / overrides
    keystore_pw = os.environ.get("APK_KEYSTORE_PASSWORD", "")
    props.setdefault("storePassword", keystore_pw)
    props.setdefault("keyPassword", keystore_pw)
    props.setdefault("keyAlias", "sd_finance")
    props.setdefault("storeFile", str(KEYSTORE_PATH))

    # Resolve storeFile relative to certs directory if needed
    sf = props["storeFile"]
    if not os.path.isabs(sf):
        candidate = CERTS_DIR / sf
        if candidate.is_file():
            props["storeFile"] = str(candidate)

    return props


def _find_tool(name: str):
    """Locate Android SDK tool (apksigner, zipalign, aapt) or JDK tool (jarsigner)."""
    # 1. Check in PATH
    tool_in_path = shutil.which(name)
    if tool_in_path:
        return tool_in_path

    # On Windows, check with .bat / .exe extensions
    if os.name == "nt":
        for ext in (".bat", ".exe", ".cmd"):
            t = shutil.which(f"{name}{ext}")
            if t:
                return t

    # 2. Check Android SDK directories
    possible_roots = []
    for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(env_var)
        if val and os.path.isdir(val):
            possible_roots.append(Path(val))

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        default_sdk = Path(local_app_data) / "Android" / "Sdk"
        if default_sdk.is_dir():
            possible_roots.append(default_sdk)

    # Search build-tools in descending version order
    for root in possible_roots:
        bt_dir = root / "build-tools"
        if bt_dir.is_dir():
            versions = sorted(bt_dir.iterdir(), reverse=True)
            for v_dir in versions:
                if v_dir.is_dir():
                    for candidate_name in (name, f"{name}.bat", f"{name}.exe"):
                        candidate = v_dir / candidate_name
                        if candidate.is_file():
                            return str(candidate)

    # 3. Check Adoptium / Oracle JDK for jarsigner
    if name == "jarsigner" and os.name == "nt":
        program_files = Path("C:/Program Files")
        if program_files.is_dir():
            for jdk_path in program_files.glob("**/jarsigner.exe"):
                if jdk_path.is_file():
                    return str(jdk_path)

    return None


def calculate_sha256(filepath: str) -> str:
    """Calculate the hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def get_keystore_vault_info():
    """Retrieve metadata about the active digital keystore."""
    props = _load_key_properties()
    keystore_file = Path(props.get("storeFile", str(KEYSTORE_PATH)))

    exists = keystore_file.is_file()
    size = keystore_file.stat().st_size if exists else 0

    return {
        "exists": exists,
        "path": str(keystore_file),
        "size_bytes": size,
        "alias": props.get("keyAlias", "sd_finance"),
        "expected_sha256": OFFICIAL_CERT_SHA256,
        "owner": "Jayakrishna Karri (sivadurga finance)",
        "valid_until": "Sep 2053",
        "algorithm": "SHA256withRSA 2048-bit",
        "tools_available": {
            "apksigner": bool(_find_tool("apksigner")),
            "zipalign": bool(_find_tool("zipalign")),
            "aapt": bool(_find_tool("aapt")),
            "jarsigner": bool(_find_tool("jarsigner")),
        }
    }


def extract_apk_metadata(apk_path: str) -> dict:
    """Extract versionName, versionCode, packageName, and SHA256 from an APK."""
    result = {
        "package_name": "com.sdfinance.mobile",
        "version_name": "",
        "version_code": 0,
        "size_bytes": 0,
        "sha256": "",
        "method": "unknown",
        "error": None
    }

    if not os.path.isfile(apk_path):
        result["error"] = "File not found"
        return result

    result["size_bytes"] = os.path.getsize(apk_path)
    result["sha256"] = calculate_sha256(apk_path)

    # 1. Try aapt if available
    aapt_tool = _find_tool("aapt")
    if aapt_tool:
        try:
            cmd = [aapt_tool, "dump", "badging", apk_path]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=15
            )
            if proc.returncode == 0:
                first_line = proc.stdout.splitlines()[0] if proc.stdout else ""
                pkg_match = re.search(r"package:\s+name='([^']+)'", proc.stdout)
                code_match = re.search(r"versionCode='([^']+)'", proc.stdout)
                name_match = re.search(r"versionName='([^']+)'", proc.stdout)

                if pkg_match:
                    result["package_name"] = pkg_match.group(1)
                if code_match and code_match.group(1).isdigit():
                    result["version_code"] = int(code_match.group(1))
                if name_match:
                    result["version_name"] = name_match.group(1)

                result["method"] = "aapt"
                return result
        except Exception as e:
            logger.warning("aapt dump failed: %s", e)

    # 2. Fallback: Parse AndroidManifest.xml string block from zip
    try:
        with zipfile.ZipFile(apk_path, "r") as zf:
            if "AndroidManifest.xml" in zf.namelist():
                manifest_data = zf.read("AndroidManifest.xml")
                # Look for readable UTF-8 strings or version patterns
                # Often formatted like '1.1.6' or '1.1.7'
                ver_matches = re.findall(rb"([0-9]+\.[0-9]+(\.[0-9]+)?)", manifest_data)
                if ver_matches:
                    for v in ver_matches:
                        v_str = v[0].decode("ascii", "ignore")
                        if len(v_str) >= 3 and not result["version_name"]:
                            result["version_name"] = v_str
                            break

                result["method"] = "binary_fallback"
    except Exception as e:
        logger.warning("Zip inspection failed: %s", e)

    return result


def verify_apk_signature(apk_path: str) -> dict:
    """Verify whether an APK is digitally signed and whether it matches the official sd_finance key."""
    result = {
        "is_signed": False,
        "is_official_key": False,
        "sha256_digest": None,
        "signer_dn": None,
        "tool_used": None,
        "details": "Signature not verified"
    }

    if not os.path.isfile(apk_path):
        result["details"] = "File does not exist"
        return result

    # 1. Use apksigner if available
    apksigner_tool = _find_tool("apksigner")
    if apksigner_tool:
        try:
            cmd = [apksigner_tool, "verify", "--print-certs", apk_path]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=20
            )
            output = proc.stdout + proc.stderr
            if proc.returncode == 0:
                result["is_signed"] = True
                result["tool_used"] = "apksigner"

                # Extract SHA-256 digest
                digest_match = re.search(
                    r"SHA-256 digest:\s*([0-9a-fA-F:]+)", output
                )
                if digest_match:
                    raw_digest = digest_match.group(1).replace(":", "").lower()
                    result["sha256_digest"] = raw_digest
                    if raw_digest == OFFICIAL_CERT_SHA256:
                        result["is_official_key"] = True
                        result["details"] = "Verified: Signed with official SD Finance production key"
                    else:
                        result["details"] = f"Signed with non-official certificate ({raw_digest[:16]}...)"

                dn_match = re.search(r"certificate DN:\s*(.+)", output)
                if dn_match:
                    result["signer_dn"] = dn_match.group(1).strip()

                return result
            else:
                result["details"] = "Unsigned or corrupted signature"
                return result
        except Exception as e:
            logger.warning("apksigner verify error: %s", e)

    # 2. Fallback to jarsigner
    jarsigner_tool = _find_tool("jarsigner")
    if jarsigner_tool:
        try:
            cmd = [jarsigner_tool, "-verify", "-verbose", "-certs", apk_path]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=20
            )
            output = proc.stdout + proc.stderr
            if "jar verified." in output or "smk" in output:
                result["is_signed"] = True
                result["tool_used"] = "jarsigner"
                if "sivadurga finance" in output or "sd_finance" in output:
                    result["is_official_key"] = True
                    result["details"] = "Verified with jarsigner (SD Finance certificate)"
                else:
                    result["details"] = "Signed with jarsigner"
                return result
        except Exception as e:
            logger.warning("jarsigner verify error: %s", e)

    # 3. Simple zip inspection: check for META-INF/*.RSA or *.SF
    try:
        with zipfile.ZipFile(apk_path, "r") as zf:
            meta_files = [n for n in zf.namelist() if n.startswith("META-INF/")]
            has_rsa = any(f.endswith(".RSA") or f.endswith(".DSA") or f.endswith(".EC") for f in meta_files)
            if has_rsa:
                result["is_signed"] = True
                result["tool_used"] = "meta_inf_inspect"
                result["details"] = "Contains signature block in META-INF"
    except Exception as e:
        logger.warning("Zip signature inspection error: %s", e)

    return result


def sign_apk(input_apk_path: str, output_apk_path: str = None) -> dict:
    """
    Digitally sign an APK with the official sd-finance-key.jks.
    Executes zipalign (if available) followed by apksigner.
    """
    props = _load_key_properties()
    keystore = props.get("storeFile", str(KEYSTORE_PATH))
    store_pass = props.get("storePassword", "Jaya@3579@1")
    key_pass = props.get("keyPassword", "Jaya@3579@1")
    alias = props.get("keyAlias", "sd_finance")

    if not os.path.isfile(keystore):
        return {
            "success": False,
            "error": f"Keystore file not found at {keystore}"
        }

    if not output_apk_path:
        output_apk_path = input_apk_path

    # Check tools
    apksigner_tool = _find_tool("apksigner")
    zipalign_tool = _find_tool("zipalign")
    jarsigner_tool = _find_tool("jarsigner")

    if not apksigner_tool and not jarsigner_tool:
        return {
            "success": False,
            "error": "Neither apksigner nor jarsigner found on server"
        }

    # Step 1: Zipalign if available and input/output are different or temp needed
    temp_aligned = None
    target_for_signing = input_apk_path

    if zipalign_tool:
        try:
            temp_aligned = input_apk_path + ".aligned.tmp"
            if os.path.exists(temp_aligned):
                os.remove(temp_aligned)

            align_cmd = [zipalign_tool, "-p", "-f", "4", input_apk_path, temp_aligned]
            proc = subprocess.run(
                align_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=45
            )
            if proc.returncode == 0 and os.path.isfile(temp_aligned):
                target_for_signing = temp_aligned
            else:
                logger.warning("zipalign warning: %s", proc.stderr)
        except Exception as e:
            logger.warning("zipalign failed: %s", e)

    # Step 2: Sign with apksigner (preferred for v2/v3 signatures)
    if apksigner_tool:
        try:
            sign_cmd = [
                apksigner_tool,
                "sign",
                "--ks", keystore,
                "--ks-key-alias", alias,
                "--ks-pass", f"pass:{store_pass}",
                "--key-pass", f"pass:{key_pass}",
                "--out", output_apk_path,
                target_for_signing
            ]
            proc = subprocess.run(
                sign_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=60
            )

            # Cleanup temporary aligned file
            if temp_aligned and os.path.exists(temp_aligned):
                try:
                    os.remove(temp_aligned)
                except Exception:
                    pass

            if proc.returncode == 0 and os.path.isfile(output_apk_path):
                # Verify newly signed file
                verification = verify_apk_signature(output_apk_path)
                sha256 = calculate_sha256(output_apk_path)
                return {
                    "success": True,
                    "output_path": output_apk_path,
                    "sha256": sha256,
                    "size_bytes": os.path.getsize(output_apk_path),
                    "tool": "apksigner",
                    "verification": verification
                }
            else:
                return {
                    "success": False,
                    "error": f"apksigner sign failed: {proc.stderr or proc.stdout}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"apksigner execution error: {str(e)}"
            }

    # Step 3: Fallback to jarsigner
    if jarsigner_tool:
        try:
            if input_apk_path != output_apk_path:
                shutil.copyfile(input_apk_path, output_apk_path)

            sign_cmd = [
                jarsigner_tool,
                "-keystore", keystore,
                "-storepass", store_pass,
                "-keypass", key_pass,
                "-digestalg", "SHA-256",
                "-sigalg", "SHA256withRSA",
                output_apk_path,
                alias
            ]
            proc = subprocess.run(
                sign_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=60
            )

            if proc.returncode == 0:
                sha256 = calculate_sha256(output_apk_path)
                return {
                    "success": True,
                    "output_path": output_apk_path,
                    "sha256": sha256,
                    "size_bytes": os.path.getsize(output_apk_path),
                    "tool": "jarsigner",
                    "verification": verify_apk_signature(output_apk_path)
                }
            else:
                return {
                    "success": False,
                    "error": f"jarsigner sign failed: {proc.stderr or proc.stdout}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"jarsigner error: {str(e)}"
            }

    return {"success": False, "error": "Signing operation incomplete"}
