# app.py - GST Info API (Full Data Collector: M2HGamerz + Sandbox)
from flask import Flask, request, jsonify
import requests
import json
import time
import re
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# ==============================================
# 🏢 GST INFO API (FULL DATA)
# Made by @KINGFFAIAK47x · ANSH AFT
# ==============================================

VALID_KEYS = {
    "AK47ADF": "full_access",
    "FFAWD": "full_access"
}

# ==============================================
# 🔐 SANDBOX.CO.IN CREDENTIALS
# ==============================================
SANDBOX_API_KEY = os.getenv("SANDBOX_API_KEY", "key_live_e007ed09f013446ba825241be2495225")
SANDBOX_API_SECRET = os.getenv("SANDBOX_API_SECRET", "secret_live_dbeaa58100d444a7a5086a0c3019c3f2")

_sandbox_token_cache = {"token": None, "expiry": 0}

# ==============================================
# AUTH
# ==============================================

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.args.get('key', '').strip()
        if not api_key:
            return jsonify({
                "status": "error",
                "message": "API key required",
                "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
            }), 401
        if api_key not in VALID_KEYS:
            return jsonify({
                "status": "error",
                "message": "Invalid API key",
                "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# ==============================================
# VALIDATION
# ==============================================

def validate_gst(gst):
    if not gst:
        return False, "GST number required"
    gst = gst.strip().upper()
    pattern = r'^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}$'
    if re.match(pattern, gst):
        return True, gst
    return False, "Invalid GST number format. Example: 19BOKPS7056D1ZI"


# ==============================================
# 🌐 SOURCE 1: M2HGamerz
# ==============================================

def fetch_from_m2hgamerz(gstin):
    try:
        url = f"https://mediafire.m2hgamerz.workers.dev/api/gst?gstNumber={gstin}"
        r = requests.get(url, timeout=20, verify=False)
        if r.status_code != 200:
            return None
        data = r.json()
        if data and data.get('success') and data.get('data', {}).get('data'):
            return data.get('data', {}).get('data', {})
        return None
    except Exception:
        return None


# ==============================================
# 🌐 SOURCE 2: Sandbox.co.in
# ==============================================

def get_sandbox_token():
    now = time.time()
    if _sandbox_token_cache["token"] and _sandbox_token_cache["expiry"] > now:
        return _sandbox_token_cache["token"]
    url = "https://api.sandbox.co.in/authenticate"
    headers = {
        "x-api-key": SANDBOX_API_KEY,
        "x-api-secret": SANDBOX_API_SECRET,
        "x-api-version": "1.0",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(url, headers=headers, timeout=15)
        if r.status_code == 200:
            token = r.json().get("access_token")
            if token:
                _sandbox_token_cache["token"] = token
                _sandbox_token_cache["expiry"] = now + 23 * 3600
                return token
        return None
    except Exception:
        return None


def fetch_from_sandbox(gstin):
    token = get_sandbox_token()
    if not token:
        return None
    url = "https://api.sandbox.co.in/gst/compliance/public/gstin/search"
    headers = {
        "Authorization": token,
        "x-api-key": SANDBOX_API_KEY,
        "x-api-version": "1.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"gstin": gstin}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        def find_gst_obj(obj):
            if isinstance(obj, dict):
                keys_lower = [k.lower() for k in obj.keys()]
                if any(k in keys_lower for k in ["gstin", "lgnm", "trade_name", "tradename", "legal_name"]):
                    return obj
                for v in obj.values():
                    res = find_gst_obj(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_gst_obj(item)
                    if res:
                        return res
            return None
        return find_gst_obj(data)
    except Exception:
        return None


# ==============================================
# 🔀 FULL MERGE (कोई भी फील्ड न छूटे)
# ==============================================

def deep_merge(a, b):
    if not isinstance(a, dict):
        a = {}
    if not isinstance(b, dict):
        b = {}
    result = {}
    all_keys = set(a.keys()) | set(b.keys())
    for key in all_keys:
        av = a.get(key)
        bv = b.get(key)
        if isinstance(av, dict) and isinstance(bv, dict):
            result[key] = deep_merge(av, bv)
        elif isinstance(av, list) and isinstance(bv, list):
            merged_list = []
            for item in av + bv:
                if item not in merged_list:
                    merged_list.append(item)
            result[key] = merged_list
        else:
            def is_empty(v):
                return v is None or v == "" or v == 0 or v == "0" or v == "0000-00-00"
            if not is_empty(av):
                result[key] = av
            elif not is_empty(bv):
                result[key] = bv
            else:
                result[key] = av if av is not None else bv
    return result


def normalize_keys(raw):
    if not isinstance(raw, dict):
        return {}
    lower_map = {k.lower(): v for k, v in raw.items()}
    def get(*keys):
        for k in keys:
            if k in raw:
                return raw[k]
            if k.lower() in lower_map:
                return lower_map[k.lower()]
        return None
    standard = {
        "Gstin":            get("Gstin", "gstin", "gst_number", "gstin_no"),
        "TradeName":        get("TradeName", "trade_name", "tradename", "tradeNam", "business_name"),
        "LegalName":        get("LegalName", "legal_name", "legalname", "lgnm"),
        "BusinessType":     get("business_type", "BusinessType", "ctb", "constitution_of_business"),
        "NatureOfBusiness": get("nature_of_business", "NatureOfBusiness", "nob"),
        "Status":           get("Status", "status", "sts"),
        "BlkStatus":        get("BlkStatus", "blk_status", "block_status", "blkstatus"),
        "TxpType":          get("TxpType", "txp_type", "taxpayer_type", "dty", "taxpayerType"),
        "DtReg":            get("DtReg", "dt_reg", "registration_date", "rgdt"),
        "DtDReg":           get("DtDReg", "dt_dreg", "date_cancel", "cxdt", "de_registration_date"),
        "LastUpdated":      get("last_updated", "LastUpdated"),
        "Jurisdiction":     get("jurisdiction", "Jurisdiction"),
        "EinvoiceStatus":   get("einvoice_status", "EinvoiceStatus"),
        "District":         get("district", "District"),
        "State":            get("state", "State"),
        "Pincode":          get("pincode", "Pincode", "AddrPncd", "addr_pncd", "pncd"),
        "StateCode":        get("StateCode", "state_code", "statecode", "stcd"),
        "AddrBnm":          get("AddrBnm", "addr_bnm", "bnm", "building_name"),
        "AddrBno":          get("AddrBno", "addr_bno", "bno", "building_number"),
        "AddrFlno":         get("AddrFlno", "addr_flno", "flno", "floor_number"),
        "AddrSt":           get("AddrSt", "addr_st", "st", "street"),
        "AddrLoc":          get("AddrLoc", "addr_loc", "loc", "location", "locality"),
    }
    result = dict(raw)
    for k, v in standard.items():
        if v not in (None, "", 0, "0", [], {}):
            result[k] = v
    return result


# ==============================================
# 📦 MAIN FETCH
# ==============================================

def get_gst_info(gst):
    is_valid, result = validate_gst(gst)
    if not is_valid:
        return {"status": "error", "message": result, "gst": gst}
    gst_clean = result
    m2h_raw = fetch_from_m2hgamerz(gst_clean) or {}
    sandbox_raw = fetch_from_sandbox(gst_clean) or {}
    if not m2h_raw and not sandbox_raw:
        return {
            "status": "error",
            "message": "No data found from any source",
            "gst": gst_clean
        }
    m2h_norm = normalize_keys(m2h_raw)
    sandbox_norm = normalize_keys(sandbox_raw)
    merged = deep_merge(m2h_norm, sandbox_norm)
    return {
        "status": "success",
        "gst": gst_clean,
        "data": merged,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


# ==============================================
# 🎨 FORMAT (सारे फील्ड्स अच्छे से)
# ==============================================

def format_gst_response(data):
    if not data:
        return None
    raw = {k: v for k, v in data.items() if v not in (None, "", [], {})}
    address = data.get("address") or {}
    if not isinstance(address, dict):
        address = {}
    if not address:
        addr_parts = {}
        for std, orig in [
            ("bnm", "AddrBnm"), ("bno", "AddrBno"), ("flno", "AddrFlno"),
            ("st", "AddrSt"), ("loc", "AddrLoc"), ("dst", "District"),
            ("stcd", "StateCode"), ("pncd", "AddrPncd"), ("pincode", "Pincode")
        ]:
            v = data.get(orig)
            if v not in (None, "", 0, "0"):
                addr_parts[std] = v
        if addr_parts:
            address = addr_parts
    return {
        "raw": raw,
        "address": address or None,
        "nature_of_business": data.get("NatureOfBusiness") or data.get("nature_of_business") or None,
        "business_name": data.get("TradeName") or data.get("business_name"),
        "business_type": data.get("BusinessType") or data.get("business_type"),
        "gstin": data.get("Gstin") or data.get("gstin"),
        "legal_name": data.get("LegalName") or data.get("legal_name"),
        "status": data.get("Status") or data.get("status"),
        "taxpayer_type": data.get("TxpType") or data.get("taxpayer_type"),
        "registration_date": data.get("DtReg") or data.get("registration_date"),
        "de_registration_date": data.get("DtDReg") or data.get("de_registration_date"),
        "last_updated": data.get("LastUpdated") or data.get("last_updated"),
        "jurisdiction": data.get("Jurisdiction") or data.get("jurisdiction"),
        "einvoice_status": data.get("EinvoiceStatus") or data.get("einvoice_status"),
        "district": data.get("District") or data.get("district"),
        "state": data.get("State") or data.get("state"),
        "pincode": data.get("Pincode") or data.get("pincode") or data.get("AddrPncd")
    }


# ==============================================
# ENDPOINTS
# ==============================================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "🏢 GST Info API (Full Data Collector)",
        "version": "4.0.0",
        "description": "Get ALL GST information  (ACX)",
        "endpoint": {
            "/gst": {
                "method": "GET",
                "description": "Get full GST information",
                "example": "/gst?code=09AAYFK4129N1ZF&key=your_api_key"
            }
        },
        "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
    })


@app.route('/gst', methods=['GET'])
@require_api_key
def get_gst():
    gst = request.args.get('code', '').strip().upper()
    
    if not gst:
        return jsonify({
            "status": "error",
            "message": "GST number required",
            "usage": "/gst?code=09AAYFK4129N1ZF&key=AK47ADF",
            "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
        }), 400
    
    result = get_gst_info(gst)
    
    if result['status'] == 'success':
        formatted = format_gst_response(result['data'])
        return jsonify({
            "status": "success",
            "gst": gst,
            "data": formatted,
            "timestamp": result['timestamp'],
            "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
        })
    else:
        return jsonify({
            "status": "error",
            "message": result.get('message', 'Unknown error'),
            "gst": result.get('gst', gst),
            "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
        }), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Use /gst endpoint",
        "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "credit": {"username": "@KINGFFAIAK47x", "made_by": "ANSH AFT"}
    }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    print("=" * 60)
    print("🏢 GST INFO API (Full Data Collector v4.0)")
    print("=" * 60)
    print(f"🚀 Running on: http://localhost:{port}")
    print("\n🔑 Valid Keys: AK47ADF, FFAWD")
    print("\n📌 ENDPOINT:")
    print(f"  GET /gst?code=09AAYFK4129N1ZF&key=AK47ADF")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
