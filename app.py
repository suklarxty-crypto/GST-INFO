# app.py - GST Info API
from flask import Flask, request, jsonify
import requests
import json
import time
from functools import wraps
import re
import os
from datetime import datetime

app = Flask(__name__)

# ==============================================
# 🏢 GST INFO API
# Made by @KINGFFAIAK47x · ANSH AFT
# ==============================================

# ONLY 2 KEYS
VALID_KEYS = {
    "AK47ADF": "full_access",
    "FFAWD": "full_access"
}

# ==============================================
# AUTHENTICATION
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
# GST FUNCTIONS
# ==============================================

def validate_gst(gst):
    """Validate GST number"""
    if not gst:
        return False, "GST number required"
    
    gst = gst.strip().upper()
    
    # GST format: 2 digits + 10 chars + 3 chars = 15 chars
    pattern = r'^[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}$'
    
    if re.match(pattern, gst):
        return True, gst
    else:
        return False, "Invalid GST number format. Example: 19BOKPS7056D1ZI"

def get_gst_info(gst):
    """Get GST information"""
    is_valid, result = validate_gst(gst)
    
    if not is_valid:
        return {
            "status": "error",
            "message": result,
            "gst": gst
        }
    
    gst_clean = result
    
    try:
        url = f"https://mediafire.m2hgamerz.workers.dev/api/gst?gstNumber={gst_clean}"
        
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('success') and data.get('data', {}).get('data'):
            return {
                "status": "success",
                "data": data.get('data', {}).get('data', {}),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                "status": "error",
                "message": "No data found for this GST",
                "gst": gst_clean
            }
            
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Request timeout",
            "gst": gst_clean
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Connection error",
            "gst": gst_clean
        }
    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "message": f"HTTP error: {str(e)}",
            "gst": gst_clean
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "gst": gst_clean
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Invalid response format",
            "gst": gst_clean
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "gst": gst_clean
        }

def format_gst_response(data):
    """Format GST data"""
    if not data:
        return None
    
    gst_data = data.get('data', {})
    
    # Basic Details
    basic = {}
    if gst_data.get('Gstin'):
        basic['gstin'] = gst_data.get('Gstin')
    if gst_data.get('TradeName'):
        basic['trade_name'] = gst_data.get('TradeName')
    if gst_data.get('LegalName'):
        basic['legal_name'] = gst_data.get('LegalName')
    if gst_data.get('TxpType'):
        txp_type = gst_data.get('TxpType')
        basic['taxpayer_type'] = 'Regular Taxpayer' if txp_type == 'REG' else txp_type
    if gst_data.get('Status'):
        status = gst_data.get('Status')
        if status == 'ACT':
            basic['status'] = 'Active ✅'
        elif status == 'SUS':
            basic['status'] = 'Suspended ⚠️'
        else:
            basic['status'] = status
    if gst_data.get('BlkStatus'):
        basic['block_status'] = 'Not Blocked' if gst_data.get('BlkStatus') == 'U' else 'Blocked 🔒'
    
    # Address
    address = {}
    address_parts = []
    if gst_data.get('AddrBno') and gst_data.get('AddrBno') != '0':
        address_parts.append(gst_data.get('AddrBno'))
    if gst_data.get('AddrFlno'):
        address_parts.append(gst_data.get('AddrFlno'))
    if gst_data.get('AddrSt'):
        address_parts.append(gst_data.get('AddrSt'))
    if gst_data.get('AddrLoc'):
        address_parts.append(gst_data.get('AddrLoc'))
    
    if address_parts:
        address['full_address'] = ', '.join(address_parts)
    if gst_data.get('StateCode'):
        address['state_code'] = gst_data.get('StateCode')
    if gst_data.get('AddrPncd'):
        address['pincode'] = gst_data.get('AddrPncd')
    
    # Dates
    dates = {}
    if gst_data.get('DtReg'):
        try:
            dates['registration_date'] = datetime.strptime(gst_data.get('DtReg'), '%Y-%m-%d').strftime('%d-%m-%Y')
        except:
            dates['registration_date'] = gst_data.get('DtReg')
    
    if gst_data.get('DtDReg') and gst_data.get('DtDReg') != '0000-00-00':
        try:
            dates['de_registration_date'] = datetime.strptime(gst_data.get('DtDReg'), '%Y-%m-%d').strftime('%d-%m-%Y')
        except:
            dates['de_registration_date'] = gst_data.get('DtDReg')
    
    return {
        "basic": basic if basic else None,
        "address": address if address else None,
        "dates": dates if dates else None
    }

# ==============================================
# ONLY 1 ENDPOINT
# ==============================================

@app.route('/', methods=['GET'])
def home():
    """API Info"""
    return jsonify({
        "service": "🏢 GST Info API",
        "version": "2.0.0",
        "description": "Get detailed GST information",
        "endpoint": {
            "/gst": {
                "method": "GET",
                "description": "Get GST information",
                "example": "/gst?code=19BOKPS7056D1ZI&key=your_api_key"
            }
        },
        "credit": {
            "username": "@KINGFFAIAK47x",
            "made_by": "ANSH AFT"
        }
    })

@app.route('/gst', methods=['GET'])
@require_api_key
def get_gst():
    """
    Get GST information
    Example: /gst?code=19BOKPS7056D1ZI&key=your_api_key
    """
    gst = request.args.get('code', '').strip()
    gst = gst.upper()
    
    if not gst:
        return jsonify({
            "status": "error",
            "message": "GST number required",
            "usage": "/gst?code=19BOKPS7056D1ZI&key=your_api_key",
            "credit": {
                "username": "@KINGFFAIAK47x",
                "made_by": "ANSH AFT"
            }
        }), 400
    
    result = get_gst_info(gst)
    
    if result['status'] == 'success':
        formatted_data = format_gst_response(result)
        
        return jsonify({
            "status": "success",
            "gst": gst,
            "data": formatted_data,
            "timestamp": result['timestamp'],
            "credit": {
                "username": "@KINGFFAIAK47x",
                "made_by": "ANSH AFT"
            }
        })
    else:
        return jsonify({
            "status": "error",
            "message": result.get('message', 'Unknown error'),
            "gst": result.get('gst', 'N/A'),
            "credit": {
                "username": "@KINGFFAIAK47x",
                "made_by": "ANSH AFT"
            }
        }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Use /gst endpoint",
        "credit": {
            "username": "@KINGFFAIAK47x",
            "made_by": "ANSH AFT"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "credit": {
            "username": "@KINGFFAIAK47x",
            "made_by": "ANSH AFT"
        }
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    print("=" * 50)
    print("🏢 GST INFO API")
    print("=" * 50)
    print("🚀 Running on: http://localhost:5000")
    print("\n🔑 Keys: AK47, FF")
    print("\n📌 ONLY 1 ENDPOINT:")
    print("  GET /gst?code=19BOKPS7056D1ZI&key=your_api_key")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=True)
