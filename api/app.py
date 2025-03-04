from flask import Flask, request, jsonify
import threading
import ipaddress
import json
import os
from datetime import datetime
from functools import wraps
from modules.scanner import NetworkScanner
from modules.db import DatabaseManager

app = Flask(__name__)
db_manager = DatabaseManager()

# Security middleware for API key authentication
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = os.environ.get('API_KEY')
        # Skip authentication if no API key is set (development mode)
        if not api_key:
            return f(*args, **kwargs)
            
        # Check if the API key is provided in the request
        # Support both X-API-Key (standard) and x-api-key (lowercase, used by some tools like n8n)
        request_api_key = request.headers.get('X-API-Key') or request.headers.get('x-api-key')
        if not request_api_key or request_api_key != api_key:
            return jsonify({"error": "Unauthorized - Invalid API key"}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Add CORS support for integration with web applications and automation tools
@app.after_request
def add_cors_headers(response):
    # Check if automation friendly mode is enabled
    if os.environ.get('AUTOMATION_FRIENDLY', 'false').lower() == 'true':
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key, x-api-key'
    return response

# Handle OPTIONS requests for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 204

# Initialize database when the app starts
@app.before_first_request
def init_app():
    db_manager.init_db()

@app.route('/api/scan/ports', methods=['POST'])
@require_api_key
def scan_ports():
    data = request.json
    target_ip = data.get('target')
    ports_input = data.get('ports', [])
    scan_type = data.get('scan_type', 'stealth')
    timeout = data.get('timeout', 1)
    
    # Safety limits
    MAX_PORTS_PER_SCAN = 10000  # Maximum number of ports allowed in a single scan
    
    # Validate input
    try:
        ipaddress.ip_address(target_ip)
    except ValueError:
        return jsonify({"error": "Invalid IP address"}), 400
    
    # Parse port specifications (both individual ports and ranges)
    ports = []
    
    # Convert to list if it's not already
    if not isinstance(ports_input, list):
        ports_input = [ports_input]
    
    # Process each port specification in the list
    for port_spec in ports_input:
        # Handle integers (direct port numbers)
        if isinstance(port_spec, int):
            ports.append(port_spec)
            continue
            
        # Convert to string for further processing
        port_str = str(port_spec)
        
        # Check if it's a range with hyphen
        if '-' in port_str:
            try:
                start, end = map(int, port_str.split('-', 1))
                
                # Safety check for port range size
                range_size = end - start + 1
                if range_size > MAX_PORTS_PER_SCAN:
                    return jsonify({
                        "error": f"Port range {start}-{end} contains {range_size} ports, which exceeds the maximum of {MAX_PORTS_PER_SCAN} ports per scan. Please use a smaller range or multiple scans."
                    }), 400
                
                ports.extend(range(start, end + 1))  # +1 to include the end port
            except ValueError:
                return jsonify({"error": f"Invalid port range format: {port_str}"}), 400
        else:
            # Try to parse as a single port number
            try:
                ports.append(int(port_str))
            except ValueError:
                return jsonify({"error": f"Invalid port specification: {port_str}"}), 400
    
    # Validate ports
    if not ports:
        return jsonify({"error": "No valid ports specified"}), 400
    
    # Remove any duplicate ports and ensure they're all in valid range
    ports = sorted(list(set(ports)))
    
    # Safety check for total ports count after removing duplicates
    if len(ports) > MAX_PORTS_PER_SCAN:
        return jsonify({
            "error": f"Requested scan contains {len(ports)} ports, which exceeds the maximum of {MAX_PORTS_PER_SCAN} ports per scan. Please use a smaller range or multiple scans."
        }), 400
    
    invalid_ports = [p for p in ports if p < 1 or p > 65535]
    if invalid_ports:
        return jsonify({"error": f"Invalid port numbers: {invalid_ports}. Ports must be between 1 and 65535"}), 400
    
    # Create scan record in database
    scan_id = db_manager.create_scan(
        f"port_scan_{scan_type}", target_ip, {"ports": ports, "timeout": timeout}
    )
    
    # Start scanning in a separate thread
    scan_thread = threading.Thread(
        target=perform_port_scan,
        args=(scan_id, target_ip, ports, scan_type, timeout)
    )
    scan_thread.start()
    
    return jsonify({
        "message": "Scan started",
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat(),
        "target": target_ip,
        "ports": ports,
        "port_count": len(ports)
    })

def perform_port_scan(scan_id, target_ip, ports, scan_type, timeout):
    """Execute port scan in background thread and store results."""
    try:
        results = NetworkScanner.scan_ports_async(scan_type, target_ip, ports, timeout)
        db_manager.store_port_results(scan_id, target_ip, results, scan_type)
    except Exception as e:
        print(f"Error during port scan: {str(e)}")

@app.route('/api/scan/hosts', methods=['POST'])
@require_api_key
def scan_hosts():
    data = request.json
    network = data.get('network')  # CIDR notation (e.g., 192.168.1.0/24)
    
    # Validate input
    try:
        ipaddress.ip_network(network)
    except ValueError:
        return jsonify({"error": "Invalid network CIDR"}), 400
    
    # Create scan record
    scan_id = db_manager.create_scan("host_discovery", network, {})
    
    # Start scanning in a separate thread
    scan_thread = threading.Thread(
        target=perform_host_scan,
        args=(scan_id, network)
    )
    scan_thread.start()
    
    return jsonify({
        "message": "Host scan started",
        "scan_id": scan_id,
        "timestamp": datetime.now().isoformat()
    })

def perform_host_scan(scan_id, network):
    """Execute host discovery in background thread and store results."""
    try:
        active_hosts = NetworkScanner.discover_hosts(network)
        db_manager.store_host_results(scan_id, active_hosts)
    except Exception as e:
        print(f"Error during host scan: {str(e)}")

@app.route('/api/results', methods=['GET'])
@require_api_key
def get_results():
    """Get scan results with optional filtering."""
    scan_id = request.args.get('scan_id')
    target = request.args.get('target')
    
    results = db_manager.get_results(scan_id, target)
    
    # Convert datetime objects to ISO format strings for JSON serialization
    for result in results:
        if 'discovered_at' in result and result['discovered_at']:
            result['discovered_at'] = result['discovered_at'].isoformat()
    
    return jsonify(results)

@app.route('/api/scans', methods=['GET'])
@require_api_key
def get_scans():
    """Get information about previous scans."""
    limit = request.args.get('limit', 100, type=int)
    target = request.args.get('target')
    scans = db_manager.get_scans(limit, target)
    
    # Convert datetime objects to ISO format strings for JSON serialization
    for scan in scans:
        if 'created_at' in scan and scan['created_at']:
            scan['created_at'] = scan['created_at'].isoformat()
    
    return jsonify(scans)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "user": os.environ.get('CURRENT_USER', 'trinq')
    })

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('API_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)